"""
SMS notification service using Fast2SMS API.

Required environment variables in backend/.env:
  SMS_PROVIDER=fast2sms
  FAST2SMS_API_KEY=your_fast2sms_api_key

Optional:
  FAST2SMS_ROUTE=q
  FAST2SMS_LANGUAGE=english
  FAST2SMS_COUNTRY_CODE=91
  FAST2SMS_SENDER_ID=
  FAST2SMS_URL=https://www.fast2sms.com/dev/bulkV2
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import requests

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


class SMSService:
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
        self.route = os.getenv("FAST2SMS_ROUTE", "q")
        self.language = os.getenv("FAST2SMS_LANGUAGE", "english")
        self.country_code = os.getenv("FAST2SMS_COUNTRY_CODE", "91").strip()
        self.sender_id = os.getenv("FAST2SMS_SENDER_ID", "").strip()
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

    def _send_text_sync(self, to_phone: str, message: str) -> bool:
        if not self.enabled:
            print(f"WARN: SMS disabled - skipping send to {to_phone}")
            return False

        target_number = self._to_fast2sms_number(to_phone)
        if not target_number:
            print(f"ERROR: Invalid SMS number format for Fast2SMS: {to_phone}")
            return False

        try:
            payload = {
                "route": self.route,
                "message": message,
                "language": self.language,
                "flash": "0",
                "numbers": target_number,
            }
            if self.sender_id:
                payload["sender_id"] = self.sender_id

            headers = {
                "authorization": self.api_key,
                "cache-control": "no-cache",
                "content-type": "application/x-www-form-urlencoded",
            }

            resp = requests.post(self.api_url, data=payload, headers=headers, timeout=10)

            try:
                data = resp.json()
            except ValueError:
                data = {"raw_response": resp.text}

            is_success = (
                resp.status_code == 200
                and isinstance(data, dict)
                and bool(data.get("return", True))
            )
            if is_success:
                print(f"INFO: SMS sent to {to_phone}")
                return True

            print(f"ERROR: SMS failed [{resp.status_code}] for {to_phone}: {data}")
            return False
        except Exception as ex:
            print(f"ERROR: SMS send exception for {to_phone}: {ex}")
            return False

    def _fire(self, fn, *args):
        if not args or not args[0]:
            return
        threading.Thread(target=fn, args=args, daemon=True).start()
        print(f"INFO: SMS queued for {args[0]}")

    def send_otp_sms(self, phone: str, otp: str, user_type: str = "user"):
        _ = user_type  # Reserved for future user-type-specific templates.
        self._fire(
            self._send_text_sync,
            phone,
            f"AI Stress Analyzer verification code: {otp}. Expires in 10 minutes.",
        )

    def send_welcome_sms(self, phone: str, name: str, user_type: str = "user"):
        if user_type == "doctor":
            extra = "Your NMC profile is verified and your doctor account is active."
        else:
            extra = "Take your first stress assessment to get personalized recommendations."
        self._fire(
            self._send_text_sync,
            phone,
            f"Welcome {name}! Your AI Stress Analyzer account is verified. {extra}",
        )

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
            self._send_text_sync,
            phone,
            (
                f"Hi {user_name}, your appointment request with Dr. {doctor_name} at "
                f"{appointment_time} is submitted and pending approval.{notes_text}"
            ),
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
            self._send_text_sync,
            phone,
            (
                f"Great news {user_name}. Your appointment with Dr. {doctor_name} at "
                f"{appointment_time} is confirmed.{note}"
            ),
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
            self._send_text_sync,
            phone,
            (
                f"Hi {user_name}, your appointment with Dr. {doctor_name} at "
                f"{appointment_time} could not be confirmed.{reason}"
            ),
        )

    def send_appointment_completed_sms(
        self,
        phone: str,
        user_name: str,
        doctor_name: str,
        appointment_time: str,
    ):
        self._fire(
            self._send_text_sync,
            phone,
            (
                f"Thank you {user_name}. Your session with Dr. {doctor_name} on "
                f"{appointment_time} is marked complete."
            ),
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
            self._send_text_sync,
            phone,
            (
                f"Hi {user_name}, your stress assessment result is {stress_label} "
                f"(confidence {confidence * 100:.1f}%).{rec_text} Open the app for full details."
            ),
        )

    def send_custom_sms(self, phone: str, message: str):
        self._fire(self._send_text_sync, phone, message)


sms_service = SMSService()
