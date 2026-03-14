import random
import string
import threading
from datetime import datetime, timedelta
from secrets import compare_digest
from typing import Optional

from .database import db, otp_collection

# In-memory storage for OTPs (use Redis in production)
otp_storage = {}
otp_lock = threading.RLock()


def _use_db_storage() -> bool:
    return db is not None


def _load_otp_record(email: str) -> Optional[dict]:
    if _use_db_storage():
        return otp_collection.find_one({"email": email})
    return otp_storage.get(email)


def _save_otp_record(email: str, data: dict) -> None:
    if _use_db_storage():
        otp_collection.update_one({"email": email}, {"$set": data}, upsert=True)
    else:
        otp_storage[email] = data


def _delete_otp_record(email: str) -> None:
    if _use_db_storage():
        otp_collection.delete_one({"email": email})
    else:
        otp_storage.pop(email, None)

def generate_otp(length: int = 6) -> str:
    """Generate a random 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=length))

def store_otp(email: str, otp: str, user_type: str, expires_in_minutes: int = 5) -> bool:
    """Store OTP with expiration"""
    try:
        with otp_lock:
            payload = {
                "otp": otp,
                "email": email,
                "user_type": user_type,
                "expires_at": datetime.utcnow() + timedelta(minutes=expires_in_minutes),
                "created_at": datetime.utcnow(),
                "attempts": 0,
                "verified": False,
            }
            _save_otp_record(email, payload)
        return True
    except Exception as e:
        print(f"Failed to store OTP: {e}")
        return False

def verify_otp(email: str, otp: str) -> Optional[dict]:
    """Verify OTP and return user_type if valid"""
    with otp_lock:
        stored_data = _load_otp_record(email)
        if not stored_data:
            return None

        # Check if OTP expired
        if datetime.utcnow() > stored_data["expires_at"]:
            _delete_otp_record(email)
            return None

        # Check if too many attempts (max 3)
        if stored_data["attempts"] >= 3:
            _delete_otp_record(email)
            return None

        # Check if OTP matches using constant-time comparison
        if not compare_digest(str(stored_data["otp"]), str(otp)):
            stored_data["attempts"] += 1
            _save_otp_record(email, stored_data)
            return None

        # OTP is valid
        user_type = stored_data["user_type"]

        # Remove OTP after successful verification (one-time use)
        _delete_otp_record(email)

        return {"user_type": user_type, "email": email}


def verify_otp_for_reset(email: str, otp: str, max_attempts: int = 3) -> dict:
    """Verify reset OTP without consuming it, then mark it verified for password reset."""
    with otp_lock:
        stored_data = _load_otp_record(email)
        if not stored_data:
            return {"ok": False, "reason": "not_found"}

        if datetime.utcnow() > stored_data["expires_at"]:
            _delete_otp_record(email)
            return {"ok": False, "reason": "expired"}

        attempts = int(stored_data.get("attempts", 0))
        if attempts >= max_attempts:
            _delete_otp_record(email)
            return {"ok": False, "reason": "too_many_attempts"}

        if not compare_digest(str(stored_data.get("otp", "")), str(otp)):
            stored_data["attempts"] = attempts + 1
            remaining = max(0, max_attempts - stored_data["attempts"])
            if stored_data["attempts"] >= max_attempts:
                _delete_otp_record(email)
            else:
                _save_otp_record(email, stored_data)
            return {"ok": False, "reason": "invalid", "remaining": remaining}

        stored_data["verified"] = True
        _save_otp_record(email, stored_data)
        return {"ok": True}


def consume_verified_reset_otp(email: str) -> Optional[dict]:
    """Consume a previously verified reset OTP and return its payload."""
    with otp_lock:
        stored_data = _load_otp_record(email)
        if not stored_data:
            return None

        if datetime.utcnow() > stored_data["expires_at"]:
            _delete_otp_record(email)
            return None

        if not stored_data.get("verified", False):
            return None

        payload = {
            "user_type": stored_data.get("user_type", "user"),
            "email": email,
        }
        _delete_otp_record(email)
        return payload

def cleanup_expired_otps():
    """Remove expired OTPs (call this periodically)"""
    with otp_lock:
        current_time = datetime.utcnow()
        if _use_db_storage():
            result = otp_collection.delete_many({"expires_at": {"$lte": current_time}})
            expired_count = int(result.deleted_count)
        else:
            expired_emails = [
                email for email, data in otp_storage.items()
                if current_time > data["expires_at"]
            ]

            for email in expired_emails:
                del otp_storage[email]
            expired_count = len(expired_emails)
    
    if expired_count:
        print(f"Cleaned up {expired_count} expired OTPs")