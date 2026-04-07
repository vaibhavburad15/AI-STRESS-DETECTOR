"""
SMS notification service using Fast2SMS API.

Required environment variables in backend/.env:
  SMS_PROVIDER=fast2sms
  FAST2SMS_API_KEY=your_fast2sms_api_key

Optional:
  FAST2SMS_ENABLE_NON_OTP_SMS=true
  FAST2SMS_ROUTE=q
  FAST2SMS_OTP_ROUTE=otp
  FAST2SMS_NOTIFICATION_ROUTE=q
  FAST2SMS_WELCOME_ROUTE=q
  FAST2SMS_LANGUAGE=english
  FAST2SMS_COUNTRY_CODE=91
  FAST2SMS_SENDER_ID=
  FAST2SMS_NOTIFICATION_SENDER_ID=
  FAST2SMS_NOTIFICATION_ENTITY_ID=
  FAST2SMS_WELCOME_SENDER_ID=
  FAST2SMS_WELCOME_TEMPLATE_ID=
  FAST2SMS_WELCOME_ENTITY_ID=
  FAST2SMS_WELCOME_MESSAGE=
  FAST2SMS_TEMPLATE_APPOINTMENT_BOOKED_ID=
  FAST2SMS_TEMPLATE_APPOINTMENT_APPROVED_ID=
  FAST2SMS_TEMPLATE_APPOINTMENT_REJECTED_ID=
  FAST2SMS_TEMPLATE_APPOINTMENT_COMPLETED_ID=
  FAST2SMS_TEMPLATE_STRESS_RESULT_ID=
  FAST2SMS_URL=https://www.fast2sms.com/dev/bulkV2
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
import requests

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


class SMSService:
    @staticmethod
    def _env_flag(name: str, default: bool = False) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _is_placeholder_config(value: str) -> bool:
        cleaned = value.strip()
        if not cleaned:
            return True

        lowered = cleaned.lower()
        placeholder_markers = ("your_", "replace_", "example", "sample", "dummy", "xxxx")
        return any(marker in lowered for marker in placeholder_markers)

    def __init__(self):
        self.provider = os.getenv("SMS_PROVIDER", "fast2sms").strip().lower()
        self.api_key = os.getenv("FAST2SMS_API_KEY", "")
        self.enable_non_otp_sms = self._env_flag("FAST2SMS_ENABLE_NON_OTP_SMS", True)
        self.default_route = os.getenv("FAST2SMS_ROUTE", "q").strip().lower()
        self.route = self.default_route  # Backward-compatible alias for existing code.
        self.otp_route = os.getenv("FAST2SMS_OTP_ROUTE", "otp").strip().lower() or self.default_route
        self.notification_route = (
            os.getenv("FAST2SMS_NOTIFICATION_ROUTE", self.default_route).strip().lower()
            or self.default_route
        )
        self.welcome_route = (
            os.getenv("FAST2SMS_WELCOME_ROUTE", self.notification_route).strip().lower()
            or self.notification_route
        )
        self.language = os.getenv("FAST2SMS_LANGUAGE", "english")
        self.country_code = os.getenv("FAST2SMS_COUNTRY_CODE", "91").strip()
        self.sender_id = os.getenv("FAST2SMS_SENDER_ID", "").strip()
        self.notification_sender_id = os.getenv(
            "FAST2SMS_NOTIFICATION_SENDER_ID",
            self.sender_id,
        ).strip()
        self.notification_entity_id = os.getenv("FAST2SMS_NOTIFICATION_ENTITY_ID", "").strip()
        self.welcome_sender_id = os.getenv(
            "FAST2SMS_WELCOME_SENDER_ID",
            self.notification_sender_id,
        ).strip()
        self.welcome_template_id = os.getenv("FAST2SMS_WELCOME_TEMPLATE_ID", "").strip()
        self.welcome_entity_id = os.getenv(
            "FAST2SMS_WELCOME_ENTITY_ID",
            self.notification_entity_id,
        ).strip()
        self.welcome_message_override = os.getenv("FAST2SMS_WELCOME_MESSAGE", "").strip()
        self.api_url = os.getenv("FAST2SMS_URL", "https://www.fast2sms.com/dev/bulkV2").strip()

        self.enabled = (
            self.provider in ("fast2sms", "fast2sms_api")
            and not self._is_placeholder_config(self.api_key)
        )

        if not self.enabled:
            print("WARN: SMS disabled. Set valid Fast2SMS settings in backend/.env.")
        else:
            print(f"INFO: SMS service ready ({self.provider})")

    def _normalize_phone(self, phone: str) -> str:
        cleaned = phone.strip()
        cleaned = cleaned.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if cleaned.startswith("+"):
            cleaned = cleaned[1:]
        return "".join(ch for ch in cleaned if ch.isdigit())

    def _to_fast2sms_number(self, to_phone: str) -> Optional[str]:
        phone = self._normalize_phone(to_phone)
        if not phone:
            return None

        # Fast2SMS typically expects a 10-digit Indian mobile number.
        if len(phone) > 10 and self.country_code and phone.startswith(self.country_code):
            phone = phone[len(self.country_code):]

        if len(phone) != 10:
            return None

        return phone

    def _submit_payload(self, to_phone: str, payload: dict[str, Any]) -> bool:
        if not self.enabled:
            print(f"WARN: SMS disabled - skipping send to {to_phone}")
            return False

        target_number = self._to_fast2sms_number(to_phone)
        if not target_number:
            print(f"ERROR: Invalid SMS number format for Fast2SMS: {to_phone}")
            return False

        try:
            clean_payload = {
                key: value
                for key, value in payload.items()
                if value not in ("", None)
            }
            clean_payload["numbers"] = target_number

            headers = {
                "authorization": self.api_key,
                "cache-control": "no-cache",
                "content-type": "application/x-www-form-urlencoded",
            }

            resp = requests.post(self.api_url, data=clean_payload, headers=headers, timeout=10)

            try:
                data = resp.json()
            except ValueError:
                data = {"raw_response": resp.text}

            route = str(clean_payload.get("route", self.default_route))
            is_success = (
                resp.status_code == 200
                and isinstance(data, dict)
                and bool(data.get("return", True))
            )
            if is_success:
                request_id = ""
                if isinstance(data, dict):
                    request_id = (
                        str(data.get("request_id", "")).strip()
                        or str(data.get("request-id", "")).strip()
                    )
                request_text = f" request_id={request_id}" if request_id else ""
                print(
                    f"INFO: SMS submitted to Fast2SMS route={route}{request_text} for {to_phone}"
                )
                return True

            print(
                f"ERROR: SMS submission failed [{resp.status_code}] route={route} "
                f"for {to_phone}: {data}"
            )
            return False
        except Exception as ex:
            print(f"ERROR: SMS send exception for {to_phone}: {ex}")
            return False

    def _send_text_sync(
        self,
        to_phone: str,
        message: str,
        *,
        route: Optional[str] = None,
        sender_id: Optional[str] = None,
    ) -> bool:
        selected_route = (route or self.default_route).strip().lower()
        payload: dict[str, Any] = {
            "route": selected_route,
            "message": message,
            "flash": "0",
        }

        if selected_route not in {"otp", "dlt", "dlt_manual"}:
            payload["language"] = self.language

        chosen_sender_id = (sender_id if sender_id is not None else self.sender_id).strip()
        if chosen_sender_id:
            payload["sender_id"] = chosen_sender_id

        return self._submit_payload(to_phone, payload)

    def _build_welcome_message(
        self,
        name: str,
        user_type: str = "user",
        doctor_verified: bool = True,
    ) -> str:
        if user_type == "doctor" and doctor_verified:
            extra = "Your NMC profile is verified and your doctor account is active."
        elif user_type == "doctor":
            extra = (
                "Your email is verified. An admin must verify your doctor "
                "account before login is enabled."
            )
        else:
            extra = "Take your first stress assessment to get personalized recommendations."
        return f"Welcome {name}! Your AI Stress Analyzer account is verified. {extra}"

    def _get_notification_template_id(self, notification_key: str) -> str:
        env_key = f"FAST2SMS_TEMPLATE_{notification_key.upper()}_ID"
        return os.getenv(env_key, "").strip()

    def _send_notification_sync(
        self,
        to_phone: str,
        message: str,
        *,
        notification_key: str,
        route: Optional[str] = None,
        sender_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> bool:
        if not self.enable_non_otp_sms:
            print(
                f"INFO: Non-OTP SMS disabled. Skipping {notification_key} SMS for {to_phone}."
            )
            return False

        selected_route = (route or self.notification_route).strip().lower()
        selected_sender_id = (
            sender_id if sender_id is not None else self.notification_sender_id
        ).strip()
        selected_entity_id = (
            entity_id if entity_id is not None else self.notification_entity_id
        ).strip()
        selected_template_id = (
            template_id if template_id is not None else self._get_notification_template_id(notification_key)
        ).strip()

        if selected_route == "dlt_manual":
            missing_fields = []
            if not selected_sender_id:
                missing_fields.append("sender_id")
            if not selected_template_id:
                missing_fields.append(
                    f"FAST2SMS_TEMPLATE_{notification_key.upper()}_ID"
                )
            if not selected_entity_id:
                missing_fields.append("FAST2SMS_NOTIFICATION_ENTITY_ID")

            if missing_fields:
                fallback_route = self.default_route if self.default_route != "dlt_manual" else "q"
                print(
                    f"WARN: {notification_key} SMS DLT config missing "
                    f"{', '.join(missing_fields)}. Falling back to route={fallback_route}."
                )
                return self._send_text_sync(
                    to_phone,
                    message,
                    route=fallback_route,
                    sender_id=self.sender_id,
                )

            return self._submit_payload(
                to_phone,
                {
                    "route": "dlt_manual",
                    "sender_id": selected_sender_id,
                    "message": message,
                    "template_id": selected_template_id,
                    "entity_id": selected_entity_id,
                    "flash": "0",
                },
            )

        return self._send_text_sync(
            to_phone,
            message,
            route=selected_route,
            sender_id=selected_sender_id,
        )

    def _send_otp_sync(self, to_phone: str, otp: str) -> bool:
        otp_value = "".join(ch for ch in str(otp) if ch.isdigit())
        text_message = (
            f"AI Stress Analyzer verification code: {otp_value}. Expires in 10 minutes."
        )

        if not otp_value:
            print(f"WARN: OTP SMS skipped for {to_phone} because the OTP is empty.")
            return False

        if self.otp_route == "otp":
            sent = self._submit_payload(
                to_phone,
                {
                    "route": "otp",
                    "variables_values": otp_value,
                    "flash": "0",
                },
            )
            if sent or self.default_route == "otp":
                return sent

            print(
                f"WARN: OTP route submission failed for {to_phone}. "
                f"Falling back to route={self.default_route}."
            )
            return self._send_text_sync(to_phone, text_message, route=self.default_route)

        return self._send_text_sync(to_phone, text_message, route=self.otp_route)

    def _send_welcome_sync(
        self,
        to_phone: str,
        name: str,
        user_type: str = "user",
        doctor_verified: bool = True,
    ) -> bool:
        message = self.welcome_message_override or self._build_welcome_message(
            name,
            user_type,
            doctor_verified,
        )
        return self._send_notification_sync(
            to_phone,
            message,
            notification_key="welcome",
            route=self.welcome_route,
            sender_id=self.welcome_sender_id,
            entity_id=self.welcome_entity_id,
            template_id=self.welcome_template_id,
        )

    def _fire(self, fn, phone: Optional[str], *args, **kwargs):
        if not phone:
            return
        threading.Thread(target=fn, args=(phone, *args), kwargs=kwargs, daemon=True).start()
        print(f"INFO: SMS queued for {phone}")

    def send_otp_sms(self, phone: str, otp: str, user_type: str = "user"):
        _ = user_type  # Reserved for future user-type-specific templates.
        self._fire(self._send_otp_sync, phone, otp)

    def send_welcome_sms(
        self,
        phone: str,
        name: str,
        user_type: str = "user",
        doctor_verified: bool = True,
    ):
        self._fire(self._send_welcome_sync, phone, name, user_type, doctor_verified)

    def send_appointment_booked_sms(
        self,
        phone: str,
        user_name: str,
        doctor_name: str,
        appointment_time: str,
        notes: Optional[str] = None,
    ):
        notes_text = f" Notes: {notes}" if notes else ""
        self._fire(
            self._send_notification_sync,
            phone,
            (
                f"Hi {user_name}, your appointment request with Dr. {doctor_name} at "
                f"{appointment_time} is submitted and pending approval.{notes_text}"
            ),
            notification_key="appointment_booked",
        )

    def send_appointment_approved_sms(
        self,
        phone: str,
        user_name: str,
        doctor_name: str,
        appointment_time: str,
        sharing_window_note: Optional[str] = None,
    ):
        note = (
            " Enable sharing in your dashboard if you want the doctor to review your "
            "stress history and medical records."
            if sharing_window_note
            else ""
        )
        self._fire(
            self._send_notification_sync,
            phone,
            (
                f"Great news {user_name}. Your appointment with Dr. {doctor_name} at "
                f"{appointment_time} is confirmed.{note}"
            ),
            notification_key="appointment_approved",
        )

    def send_appointment_rejected_sms(
        self,
        phone: str,
        user_name: str,
        doctor_name: str,
        appointment_time: str,
        rejection_reason: Optional[str] = None,
    ):
        reason = f" Reason: {rejection_reason}." if rejection_reason else ""
        self._fire(
            self._send_notification_sync,
            phone,
            (
                f"Hi {user_name}, your appointment with Dr. {doctor_name} at "
                f"{appointment_time} could not be confirmed.{reason}"
            ),
            notification_key="appointment_rejected",
        )

    def send_appointment_completed_sms(
        self,
        phone: str,
        user_name: str,
        doctor_name: str,
        appointment_time: str,
    ):
        self._fire(
            self._send_notification_sync,
            phone,
            (
                f"Thank you {user_name}. Your session with Dr. {doctor_name} on "
                f"{appointment_time} is marked complete."
            ),
            notification_key="appointment_completed",
        )

    def send_stress_result_sms(
        self,
        phone: str,
        user_name: str,
        stress_label: str,
        confidence: float,
        top_recommendations: Optional[list] = None,
    ):
        rec_text = ""
        if top_recommendations:
            short = ", ".join(str(item) for item in top_recommendations[:3])
            rec_text = f" Top tips: {short}."

        self._fire(
            self._send_notification_sync,
            phone,
            (
                f"Hi {user_name}, your stress assessment result is {stress_label} "
                f"(confidence {confidence * 100:.1f}%).{rec_text} Open the app for full details."
            ),
            notification_key="stress_result",
        )

    def send_custom_sms(self, phone: str, message: str):
        self._fire(self._send_text_sync, phone, message)


sms_service = SMSService()
