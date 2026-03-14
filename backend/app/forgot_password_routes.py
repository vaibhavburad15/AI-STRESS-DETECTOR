"""
Add these 3 endpoints to your existing auth_routes.py file.

ALSO make sure your otp_service.py has the store_otp function using 10-minute expiry
(the frontend shows a 10-minute countdown timer).
"""

# ─── PASTE THESE IMPORTS at the top of auth_routes.py if not already there ───
# from ..otp_service import generate_otp, store_otp, verify_otp
# from ..sms_service import sms_service   # only if you want SMS; for email use email_service
# from ..database import users_collection, doctors_collection
# from pydantic import BaseModel, EmailStr

# ─── ADD THESE MODELS (or add to your existing models file) ──────────────────

from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, HTTPException, status
from ..otp_utils import generate_otp, store_otp, verify_otp_for_reset, consume_verified_reset_otp
from ..database import users_collection, doctors_collection
from .auth_routes import router  # re-use the existing router
from ..email_service import email_service

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
    email_service.send_reset_otp_email(email, otp_code, user.get("name", "User"))

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

    verify_result = verify_otp_for_reset(email, request.otp)
    if not verify_result.get("ok"):
        reason = verify_result.get("reason")
        if reason == "expired":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one.",
            )
        if reason == "too_many_attempts":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many failed attempts. Please request a new OTP.",
            )
        if reason == "invalid":
            remaining = int(verify_result.get("remaining", 0))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OTP. {remaining} attempt(s) remaining.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not found or expired. Please request a new one.",
        )

    return {"message": "OTP verified successfully.", "email": email}


# ─── ENDPOINT 3: Reset Password ──────────────────────────────────────────────
@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Step 3: User submits new password.
    We re-check the OTP is still marked as verified, then update the password.
    """
    from ..auth import get_password_hash
    from bson import ObjectId

    email = request.email.lower().strip()

    # Validate password strength
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )

    # Check that OTP was verified in step 2 and consume it atomically
    otp_payload = consume_verified_reset_otp(email)
    if not otp_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not verified. Please complete the verification step first."
        )

    # Hash new password
    hashed_password = get_password_hash(request.new_password)

    # Update password in the correct collection based on user_type
    user_type = otp_payload.get("user_type", "user")
    collection = users_collection if user_type == "user" else doctors_collection

    result = collection.update_one(
        {"email": email},
        {"$set": {
            "password": hashed_password,
            "password_updated_at": __import__('datetime').datetime.utcnow()
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    return {"message": "Password reset successfully. You can now log in with your new password."}