import random
import string
from datetime import datetime, timedelta
from typing import Optional

# In-memory storage for OTPs (use Redis in production)
otp_storage = {}

def generate_otp(length: int = 6) -> str:
    """Generate a random 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=length))

def store_otp(email: str, otp: str, user_type: str, expires_in_minutes: int = 5) -> bool:
    """Store OTP with expiration"""
    try:
        otp_storage[email] = {
            "otp": otp,
            "user_type": user_type,
            "expires_at": datetime.utcnow() + timedelta(minutes=expires_in_minutes),
            "created_at": datetime.utcnow(),
            "attempts": 0
        }
        return True
    except Exception as e:
        print(f"Failed to store OTP: {e}")
        return False

def verify_otp(email: str, otp: str) -> Optional[dict]:
    """Verify OTP and return user_type if valid"""
    if email not in otp_storage:
        return None
    
    stored_data = otp_storage[email]
    
    # Check if OTP expired
    if datetime.utcnow() > stored_data["expires_at"]:
        del otp_storage[email]
        return None
    
    # Check if too many attempts (max 3)
    if stored_data["attempts"] >= 3:
        del otp_storage[email]
        return None
    
    # Check if OTP matches
    if stored_data["otp"] != otp:
        stored_data["attempts"] += 1
        return None
    
    # OTP is valid
    user_type = stored_data["user_type"]
    
    # Remove OTP after successful verification (one-time use)
    del otp_storage[email]
    
    return {"user_type": user_type, "email": email}

def cleanup_expired_otps():
    """Remove expired OTPs (call this periodically)"""
    current_time = datetime.utcnow()
    expired_emails = [
        email for email, data in otp_storage.items()
        if current_time > data["expires_at"]
    ]
    
    for email in expired_emails:
        del otp_storage[email]
    
    if expired_emails:
        print(f"Cleaned up {len(expired_emails)} expired OTPs")