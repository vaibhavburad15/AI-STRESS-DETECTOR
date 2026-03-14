"""
Add these 3 endpoints to your existing auth_routes.py file.

ALSO make sure your otp_service.py has the store_otp function using 10-minute expiry
(the frontend shows a 10-minute countdown timer).
"""

# ─── PASTE THESE IMPORTS at the top of auth_routes.py if not already there ───
# from ..otp_utils import generate_otp, store_otp, verify_otp
# from ..sms_service import sms_service   # only if you want SMS; for email use email_service
# from ..database import users_collection, doctors_collection
# from pydantic import BaseModel, EmailStr

# ─── ADD THESE MODELS (or add to your existing models file) ──────────────────

from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, HTTPException, status
from datetime import datetime
from ..otp_utils import generate_otp, store_otp, verify_otp
from ..database import users_collection, doctors_collection
from .auth_routes import router  # re-use the existing router

# If you have a separate models file, add these classes there instead:
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyResetOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


# ─── ENDPOINT 1: Send Reset OTP ──────────────────────────────────────────────
@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Step 1: User submits email → look up in DB → send OTP via email/SMS.
    Always return 200 even if email not found (security best practice prevents
    user enumeration), BUT your frontend shows "Not Found" so we raise 404.
    """
    email = request.email.lower().strip()

    # Check users collection
    user = users_collection.find_one({"email": email})
    user_type = "user"

    # Check doctors collection if not found in users
    if not user:
        user = doctors_collection.find_one({"email": email})
        user_type = "doctor"

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address."
        )

    # Generate OTP — use 10-minute expiry to match frontend countdown
    otp_code = generate_otp(6)
    store_otp(email, otp_code, user_type=user_type, expires_in_minutes=10)

    # ── Send the OTP ──────────────────────────────────────────────────────────
    # Option A: Email (recommended)
    try:
        from ..email_service import send_reset_otp_email  # create this if needed
        await send_reset_otp_email(email, otp_code, user.get("name", "User"))
    except ImportError:
        # Option B: SMS fallback (if you have sms_service)
        try:
            from ..sms_service import sms_service
            phone = user.get("phone") or user.get("phone_number")
            if phone:
                sms_service.send_otp(phone, otp_code)
        except Exception as sms_err:
            print(f"SMS failed: {sms_err}")

        # Option C: Just print to console during development
        print(f"🔑 RESET OTP for {email}: {otp_code}")

    return {
        "message": "Reset code sent successfully. Please check your email.",
        "email": email
    }


# ─── ENDPOINT 2: Verify Reset OTP ────────────────────────────────────────────
@router.post("/verify-reset-otp")
async def verify_reset_otp(request: VerifyResetOTPRequest):
    """
    Step 2: User submits the 6-digit OTP.
    We verify it but DON'T delete it yet — we need it again in step 3 to
    authenticate the password reset (store a verified flag instead).
    """
    email = request.email.lower().strip()

    from ..otp_utils import otp_storage  # direct access to mark as verified

    if email not in otp_storage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not found or expired. Please request a new one."
        )

    stored = otp_storage[email]

    # Check expiry
    from datetime import datetime
    if datetime.utcnow() > stored["expires_at"]:
        del otp_storage[email]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one."
        )

    # Check attempts
    if stored.get("attempts", 0) >= 3:
        del otp_storage[email]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many failed attempts. Please request a new OTP."
        )

    # Check OTP value (constant-time comparison to prevent timing attacks)
    from hmac import compare_digest
    if not compare_digest(stored["otp"], request.otp):
        stored["attempts"] = stored.get("attempts", 0) + 1
        remaining = 3 - stored["attempts"]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP. {remaining} attempt(s) remaining."
        )

    # Mark as verified (keep in storage so step 3 can use it)
    stored["verified"] = True

    return {"message": "OTP verified successfully.", "email": email}


# ─── ENDPOINT 3: Reset Password ──────────────────────────────────────────────
@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Step 3: User submits new password.
    We re-check the OTP is still marked as verified, then update the password.
    """
    from ..otp_utils import otp_storage
    from ..auth import get_password_hash
    from bson import ObjectId

    email = request.email.lower().strip()

    # Validate password strength
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )

    # Check that OTP was verified in step 2
    stored = otp_storage.get(email)
    if not stored or not stored.get("verified"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not verified. Please complete the verification step first."
        )

    # Hash new password
    hashed_password = get_password_hash(request.new_password)

    # Update password in the correct collection based on user_type
    user_type = stored.get("user_type", "user")
    collection = users_collection if user_type == "user" else doctors_collection

    result = collection.update_one(
        {"email": email},
        {"$set": {
            "password": hashed_password,
            "password_updated_at": datetime.utcnow()
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Clean up OTP storage
    if email in otp_storage:
        del otp_storage[email]

    return {"message": "Password reset successfully. You can now log in with your new password."}