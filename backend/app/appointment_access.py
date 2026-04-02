from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Mapping

from bson import ObjectId
from fastapi import HTTPException, status

from .database import appointments_collection

WEEKDAY_LOOKUP = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

RECURRING_SLOT_PATTERN = re.compile(
    r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})$",
    re.IGNORECASE,
)

ACCESSIBLE_APPOINTMENT_STATUSES = {"approved", "completed"}


def normalize_datetime(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None

    if value.tzinfo is not None:
        return value.astimezone().replace(tzinfo=None)

    return value


def format_slot_window(slot_start_at: datetime | None, slot_end_at: datetime | None) -> str:
    if not slot_start_at or not slot_end_at:
        return "Scheduled slot"

    return (
        f"{slot_start_at.strftime('%a, %b %d %Y, %I:%M %p')} - "
        f"{slot_end_at.strftime('%I:%M %p')}"
    )


def format_access_deadline(access_expires_at: datetime | None) -> str:
    if not access_expires_at:
        return "Unknown"

    return access_expires_at.strftime("%a, %b %d %Y, %I:%M %p")


def build_slot_reservation_key(doctor_id: str, slot_start_at: datetime | None) -> str | None:
    normalized_slot_start = normalize_datetime(slot_start_at)
    normalized_doctor_id = doctor_id.strip()
    if not normalized_doctor_id or normalized_slot_start is None:
        return None

    return f"{normalized_doctor_id}:{normalized_slot_start.isoformat()}"


def parse_time_slot_window(
    time_slot: str,
    reference: datetime | None = None,
) -> tuple[datetime, datetime]:
    slot_text = time_slot.strip()
    if not slot_text:
        raise ValueError("Empty time slot")

    match = RECURRING_SLOT_PATTERN.fullmatch(slot_text)
    if match:
        weekday_key, start_hour, start_minute, end_hour, end_minute = match.groups()
        current = normalize_datetime(reference) or datetime.now()
        target_weekday = WEEKDAY_LOOKUP[weekday_key.lower()]

        slot_start = current.replace(
            hour=int(start_hour),
            minute=int(start_minute),
            second=0,
            microsecond=0,
        )
        days_ahead = target_weekday - current.weekday()
        if days_ahead < 0 or (days_ahead == 0 and slot_start <= current):
            days_ahead += 7

        slot_start += timedelta(days=days_ahead)
        slot_end = slot_start.replace(
            hour=int(end_hour),
            minute=int(end_minute),
            second=0,
            microsecond=0,
        )
        if slot_end <= slot_start:
            slot_end += timedelta(days=1)

        return slot_start, slot_end

    parsed = datetime.fromisoformat(slot_text.replace("Z", "+00:00"))
    slot_start = normalize_datetime(parsed)
    if slot_start is None:
        raise ValueError("Invalid time slot")

    return slot_start, slot_start + timedelta(hours=1)


def ensure_appointment_schedule(
    appointment: Mapping[str, Any],
    *,
    persist: bool = True,
) -> dict[str, Any]:
    normalized = dict(appointment)
    slot_start_at = normalize_datetime(normalized.get("slot_start_at"))
    slot_end_at = normalize_datetime(normalized.get("slot_end_at"))
    access_expires_at = normalize_datetime(normalized.get("access_expires_at"))

    if slot_start_at and slot_end_at:
        if access_expires_at is None:
            access_expires_at = slot_end_at + timedelta(hours=1)
            if persist and normalized.get("_id"):
                appointments_collection.update_one(
                    {"_id": normalized["_id"]},
                    {"$set": {"access_expires_at": access_expires_at}},
                )

        normalized["slot_start_at"] = slot_start_at
        normalized["slot_end_at"] = slot_end_at
        normalized["access_expires_at"] = access_expires_at
        return normalized

    time_slot = str(normalized.get("time_slot") or "").strip()
    if not time_slot:
        return normalized

    reference = normalize_datetime(normalized.get("created_at")) or datetime.now()
    slot_start_at, slot_end_at = parse_time_slot_window(time_slot, reference=reference)
    access_expires_at = slot_end_at + timedelta(hours=1)

    normalized["slot_start_at"] = slot_start_at
    normalized["slot_end_at"] = slot_end_at
    normalized["access_expires_at"] = access_expires_at

    if persist and normalized.get("_id"):
        appointments_collection.update_one(
            {"_id": normalized["_id"]},
            {
                "$set": {
                    "slot_start_at": slot_start_at,
                    "slot_end_at": slot_end_at,
                    "access_expires_at": access_expires_at,
                }
            },
        )

    return normalized


def get_appointment_access_state(
    appointment: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    normalized = ensure_appointment_schedule(appointment)
    slot_start_at = normalize_datetime(normalized.get("slot_start_at"))
    slot_end_at = normalize_datetime(normalized.get("slot_end_at"))
    access_expires_at = normalize_datetime(normalized.get("access_expires_at"))
    shared_with_doctor_at = normalize_datetime(normalized.get("shared_with_doctor_at"))
    current_time = normalize_datetime(now) or datetime.now()
    records_shared = bool(normalized.get("records_shared_with_doctor", False))
    status_name = str(normalized.get("status") or "")

    can_manage_sharing = (
        status_name in ACCESSIBLE_APPOINTMENT_STATUSES
        and access_expires_at is not None
        and current_time <= access_expires_at
    )

    if status_name not in ACCESSIBLE_APPOINTMENT_STATUSES:
        message = "Sharing becomes available after the doctor confirms the appointment."
        active = False
    elif not records_shared:
        message = "User has not shared records and stress details with the doctor yet."
        active = False
    elif slot_start_at is None or slot_end_at is None or access_expires_at is None:
        message = "Appointment schedule is unavailable."
        active = False
    elif shared_with_doctor_at is not None and current_time < shared_with_doctor_at:
        message = "Doctor access will be available once sharing is enabled."
        active = False
    elif current_time > access_expires_at:
        message = "Access closed 1 hour after the appointment slot ended."
        active = False
    elif slot_start_at is not None and current_time < slot_start_at:
        message = (
            "Doctor access is active for this appointment and remains available until "
            "1 hour after the slot ends."
        )
        active = True
    else:
        message = "Doctor access is active for this appointment."
        active = True

    return {
        "slot_start_at": slot_start_at,
        "slot_end_at": slot_end_at,
        "access_expires_at": access_expires_at,
        "shared_with_doctor_at": shared_with_doctor_at,
        "records_shared_with_doctor": records_shared,
        "can_manage_record_sharing": can_manage_sharing,
        "data_access_active": active,
        "data_access_message": message,
        "slot_label": format_slot_window(slot_start_at, slot_end_at)
        if slot_start_at and slot_end_at
        else str(normalized.get("time_slot") or ""),
        "access_deadline_label": format_access_deadline(access_expires_at),
    }


def add_access_state(appointment: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    normalized = ensure_appointment_schedule(appointment)
    normalized.update(get_appointment_access_state(normalized, now=now))
    return normalized


def get_active_shared_appointment(
    doctor_id: str,
    user_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    current_time = normalize_datetime(now) or datetime.now()
    appointments = list(
        appointments_collection.find(
            {
                "doctor_id": doctor_id,
                "user_id": user_id,
                "status": {"$in": list(ACCESSIBLE_APPOINTMENT_STATUSES)},
            }
        ).sort("slot_start_at", -1)
    )

    for appointment in appointments:
        normalized = add_access_state(appointment, now=current_time)
        if normalized.get("data_access_active"):
            return normalized

    return None


def require_doctor_owned_appointment(current_user: Mapping[str, Any], appointment: Mapping[str, Any]) -> None:
    doctor_id = str(current_user.get("user_id") or "")
    if not doctor_id or str(appointment.get("doctor_id") or "") != doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own appointments.",
        )


def require_doctor_user_access(current_user: Mapping[str, Any], user_id: str) -> dict[str, Any] | None:
    if current_user.get("role") != "doctor":
        return None

    doctor_id = str(current_user.get("user_id") or "")
    appointment = get_active_shared_appointment(doctor_id, user_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You can view this user's records only during an approved appointment slot "
                "when the user has shared their details, and until 1 hour after the slot ends."
            ),
        )

    return appointment


def require_doctor_appointment_data_access(
    current_user: Mapping[str, Any],
    appointment: Mapping[str, Any],
) -> dict[str, Any]:
    require_doctor_owned_appointment(current_user, appointment)
    normalized = add_access_state(appointment)

    if not normalized.get("data_access_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(normalized.get("data_access_message") or "Doctor data access is not active."),
        )

    return normalized


def get_appointment_by_id(appointment_id: str) -> dict[str, Any]:
    try:
        object_id = ObjectId(appointment_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid appointment ID format",
        ) from exc

    appointment = appointments_collection.find_one({"_id": object_id})
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    return appointment
