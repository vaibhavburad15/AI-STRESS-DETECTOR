from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from ..appointment_access import (
    add_access_state,
    build_slot_reservation_key,
    get_appointment_by_id,
    require_doctor_appointment_data_access,
    require_doctor_owned_appointment,
)
from ..auth import require_role
from ..database import (
    appointments_collection,
    medical_records_collection,
    tests_collection,
    users_collection,
)
from ..email_service import email_service
from ..models import AppointmentUpdate
from ..sms_service import sms_service

router = APIRouter(prefix="/api/doctor", tags=["Doctor"])


def _build_email_context(appointment: Mapping[str, Any]) -> tuple[str | None, str, str, str]:
    user_email_raw = appointment.get("user_email")
    user_email = user_email_raw if isinstance(user_email_raw, str) and user_email_raw else None
    user_name = str(appointment.get("user_name") or "User")
    doctor_name = str(appointment.get("doctor_name") or "Doctor")
    time_slot = str(appointment.get("slot_label") or appointment.get("time_slot") or "Scheduled time")
    return user_email, user_name, doctor_name, time_slot


def _get_user_phone(appointment: Mapping[str, Any]) -> str | None:
    user_id = str(appointment.get("user_id") or "").strip()
    if not user_id:
        return None

    try:
        from bson import ObjectId as _ObjectId

        user = users_collection.find_one({"_id": _ObjectId(user_id)})
        phone = user.get("phone_number") if user else None
        return phone if isinstance(phone, str) and phone else None
    except Exception as exc:
        print(f"Warning: could not fetch user phone: {exc}")
        return None


def _serialize_test(test: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(test["_id"]),
        "user_id": test.get("user_id"),
        "stress_level": test["stress_level"],
        "stress_label": test["stress_label"],
        "confidence_score": test["confidence_score"],
        "responses": test.get("responses", []),
        "recommendations": test.get("recommendations", []),
        "timestamp": test["timestamp"],
    }


def _serialize_record(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(record["_id"]),
        "record_name": record.get("record_name"),
        "record_type": record.get("record_type"),
        "file_name": record.get("file_name"),
        "file_size": record.get("file_size", 0),
        "file_format": record.get("file_format"),
        "description": record.get("description"),
        "record_date": record.get("record_date"),
        "doctor_name": record.get("doctor_name"),
        "hospital_name": record.get("hospital_name"),
        "notes": record.get("notes"),
        "tags": record.get("tags", []),
        "uploaded_at": record.get("uploaded_at"),
        "updated_at": record.get("updated_at"),
        "download_count": record.get("download_count", 0),
        "is_linked_to_stress_test": record.get("is_linked_to_stress_test", False),
        "linked_test_id": record.get("linked_test_id"),
    }


def _build_sharing_window_note(appointment: Mapping[str, Any]) -> str | None:
    slot_label = str(appointment.get("slot_label") or "").strip()
    access_deadline = str(appointment.get("access_deadline_label") or "").strip()
    if not slot_label or not access_deadline:
        return None

    return (
        "In your dashboard, enable 'Share details with doctor' for this appointment. "
        f"Once enabled, the doctor can view your profile, stress assessments, and medical records "
        f"during {slot_label} and until {access_deadline}."
    )


def _get_recent_tests_for_user(user_id: str, limit: int = 5) -> list[dict[str, Any]]:
    tests = list(tests_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(limit))
    return [_serialize_test(test) for test in tests]


def _serialize_appointment_for_dashboard(appointment: Mapping[str, Any]) -> dict[str, Any]:
    enriched = add_access_state(appointment)
    test_history = _get_recent_tests_for_user(enriched["user_id"], limit=5) if enriched.get("data_access_active") else []
    latest_test = test_history[0] if test_history else None

    return {
        "id": str(enriched["_id"]),
        "user_id": enriched["user_id"],
        "user_name": enriched["user_name"],
        "user_email": enriched.get("user_email"),
        "doctor_id": enriched["doctor_id"],
        "doctor_name": enriched["doctor_name"],
        "time_slot": enriched["time_slot"],
        "slot_label": enriched.get("slot_label"),
        "status": enriched["status"],
        "notes": enriched.get("notes", ""),
        "doctor_notes": enriched.get("doctor_notes", ""),
        "created_at": enriched["created_at"],
        "updated_at": enriched.get("updated_at"),
        "slot_start_at": enriched.get("slot_start_at"),
        "slot_end_at": enriched.get("slot_end_at"),
        "access_expires_at": enriched.get("access_expires_at"),
        "records_shared_with_doctor": enriched.get("records_shared_with_doctor", False),
        "data_access_active": enriched.get("data_access_active", False),
        "data_access_message": enriched.get("data_access_message"),
        "access_deadline_label": enriched.get("access_deadline_label"),
        "test_history": test_history,
        "latest_test": latest_test,
    }


def _send_status_notifications(appointment: Mapping[str, Any], update: AppointmentUpdate) -> None:
    enriched = add_access_state(appointment)
    user_email, user_name, doctor_name, time_slot = _build_email_context(enriched)
    sharing_window_note = _build_sharing_window_note(enriched)

    if user_email:
        if update.status == "approved":
            email_service.send_appointment_approved_email(
                user_email=user_email,
                user_name=user_name,
                doctor_name=doctor_name,
                appointment_time=time_slot,
                sharing_window_note=sharing_window_note,
            )
        elif update.status == "rejected":
            email_service.send_appointment_rejected_email(
                user_email=user_email,
                user_name=user_name,
                doctor_name=doctor_name,
                appointment_time=time_slot,
                rejection_reason=update.notes or "Time slot no longer available",
            )
        elif update.status == "completed":
            email_service.send_appointment_completed_email(
                user_email=user_email,
                user_name=user_name,
                doctor_name=doctor_name,
                appointment_time=time_slot,
            )

    user_phone = _get_user_phone(appointment)
    if not user_phone:
        return

    if update.status == "approved":
        sms_service.send_appointment_approved_sms(
            phone=user_phone,
            user_name=user_name,
            doctor_name=doctor_name,
            appointment_time=time_slot,
            sharing_window_note=sharing_window_note,
        )
    elif update.status == "rejected":
        sms_service.send_appointment_rejected_sms(
            phone=user_phone,
            user_name=user_name,
            doctor_name=doctor_name,
            appointment_time=time_slot,
            rejection_reason=update.notes or "Time slot no longer available",
        )
    elif update.status == "completed":
        sms_service.send_appointment_completed_sms(
            phone=user_phone,
            user_name=user_name,
            doctor_name=doctor_name,
            appointment_time=time_slot,
        )


def _update_appointment_status_impl(
    appointment_id: str,
    update: AppointmentUpdate,
    current_user: Mapping[str, Any],
) -> dict[str, Any]:
    appointment = add_access_state(get_appointment_by_id(appointment_id))
    require_doctor_owned_appointment(current_user, appointment)

    valid_statuses = ["pending", "approved", "rejected", "completed"]
    if update.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )

    update_data: dict[str, Any] = {
        "status": update.status,
        "updated_at": datetime.utcnow(),
    }
    if update.notes:
        update_data["doctor_notes"] = update.notes

    update_document: dict[str, Any] = {"$set": update_data}
    slot_reservation_key = build_slot_reservation_key(
        str(appointment.get("doctor_id") or ""),
        appointment.get("slot_start_at"),
    )
    if update.status in {"pending", "approved"} and slot_reservation_key:
        update_data["slot_reservation_key"] = slot_reservation_key
    elif update.status == "rejected":
        update_document["$unset"] = {"slot_reservation_key": ""}

    try:
        appointments_collection.update_one(
            {"_id": appointment["_id"]},
            update_document,
        )
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This time slot is already reserved by another active appointment.",
        ) from exc

    updated_appointment = dict(appointment)
    updated_appointment.update(update_data)
    if update.status == "rejected":
        updated_appointment.pop("slot_reservation_key", None)
    _send_status_notifications(updated_appointment, update)

    return {
        "message": f"Appointment status updated to {update.status}",
        "appointment_id": appointment_id,
        "status": update.status,
    }


@router.get("/appointments/{doctor_id}")
async def get_doctor_appointments(
    doctor_id: str,
    current_user: dict = Depends(require_role(["doctor"])),
):
    """Get the authenticated doctor's appointments with scoped access metadata."""
    authenticated_doctor_id = str(current_user.get("user_id") or "")
    if doctor_id != authenticated_doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own appointments.",
        )

    appointments = list(
        appointments_collection.find({"doctor_id": authenticated_doctor_id}).sort("created_at", -1)
    )
    return [_serialize_appointment_for_dashboard(appointment) for appointment in appointments]


@router.get("/appointment/{appointment_id}/patient-tests")
async def get_patient_tests_for_appointment(
    appointment_id: str,
    current_user: dict = Depends(require_role(["doctor"])),
):
    """Get detailed patient test information for an appointment during the active access window."""
    appointment = get_appointment_by_id(appointment_id)
    enriched = require_doctor_appointment_data_access(current_user, appointment)
    user_tests = list(tests_collection.find({"user_id": enriched["user_id"]}).sort("timestamp", -1))

    return {
        "patient_name": enriched["user_name"],
        "patient_email": enriched.get("user_email"),
        "appointment_time": enriched.get("slot_label") or enriched["time_slot"],
        "access_expires_at": enriched.get("access_expires_at"),
        "tests": [_serialize_test(test) for test in user_tests],
    }


@router.get("/appointment/{appointment_id}/shared-details")
async def get_appointment_shared_details(
    appointment_id: str,
    current_user: dict = Depends(require_role(["doctor"])),
):
    """Return profile, test, and medical-record data for the active shared appointment window."""
    appointment = get_appointment_by_id(appointment_id)
    enriched = require_doctor_appointment_data_access(current_user, appointment)

    user = users_collection.find_one({"_id": ObjectId(enriched["user_id"])})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    tests = list(tests_collection.find({"user_id": enriched["user_id"]}).sort("timestamp", -1))
    records = list(
        medical_records_collection.find(
            {"user_id": enriched["user_id"], "deleted": False}
        ).sort("uploaded_at", -1)
    )

    return {
        "appointment": {
            "id": str(enriched["_id"]),
            "status": enriched["status"],
            "time_slot": enriched["time_slot"],
            "slot_label": enriched.get("slot_label"),
            "slot_start_at": enriched.get("slot_start_at"),
            "slot_end_at": enriched.get("slot_end_at"),
            "access_expires_at": enriched.get("access_expires_at"),
            "data_access_message": enriched.get("data_access_message"),
        },
        "patient": {
            "id": str(user["_id"]),
            "name": user.get("name"),
            "email": user.get("email"),
            "age": user.get("age"),
            "gender": user.get("gender"),
            "location": user.get("location"),
            "phone_number": user.get("phone_number"),
            "has_previous_stress_issues": user.get("has_previous_stress_issues", False),
            "created_at": user.get("created_at"),
        },
        "tests": [_serialize_test(test) for test in tests],
        "medical_records": [_serialize_record(record) for record in records],
    }


@router.put("/appointment/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    update: AppointmentUpdate,
    current_user: dict = Depends(require_role(["doctor"])),
):
    """Update appointment status and notes."""
    return _update_appointment_status_impl(appointment_id, update, current_user)


@router.put("/appointment/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: str,
    update: AppointmentUpdate,
    current_user: dict = Depends(require_role(["doctor"])),
):
    """Update appointment status through the alternative status endpoint."""
    return _update_appointment_status_impl(appointment_id, update, current_user)


@router.get("/stats/{doctor_id}")
async def get_doctor_stats(
    doctor_id: str,
    current_user: dict = Depends(require_role(["doctor"])),
):
    """Get appointment stats for the authenticated doctor."""
    authenticated_doctor_id = str(current_user.get("user_id") or "")
    if doctor_id != authenticated_doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own statistics.",
        )

    pipeline = [
        {"$match": {"doctor_id": authenticated_doctor_id}},
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
            }
        },
    ]

    results = list(appointments_collection.aggregate(pipeline))
    stats = {
        "total_appointments": 0,
        "pending": 0,
        "approved": 0,
        "completed": 0,
        "rejected": 0,
    }

    for result in results:
        status_name = result["_id"]
        count = result["count"]
        if status_name in stats:
            stats[status_name] = count
        stats["total_appointments"] += count

    return stats
