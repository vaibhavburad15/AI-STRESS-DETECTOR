from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from datetime import datetime
from bson import ObjectId
from typing import Optional
from ..models import (
    UserRegister, UserLogin, DoctorRegister, TokenResponse,
    OTPVerify, ResendOTPRequest, ChangePassword
)
from ..database import users_collection, doctors_collection, admin_collection
from ..auth import verify_password, get_password_hash, require_role, create_access_token
from ..email_service import email_service
from ..sms_service import sms_service
from ..otp_utils import generate_otp, store_otp, verify_otp, otp_storage
from hmac import compare_digest as _compare_digest
from ..nmc_verification import (
    build_nmc_profile,
    get_state_medical_councils,
    verify_doctor_registration,
)
from pydantic import BaseModel, EmailStr
import re
import os
import shutil
from pathlib import Path

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads/medical_documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def validate_license_number(license_number: str) -> bool:
    """Validate doctor registration/license number format"""
    pattern = r"^[A-Za-z0-9/\-]{4,30}$"
    return bool(re.match(pattern, license_number.strip()))


# ── Forgot Password Request Models ───────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyResetOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


# ─────────────────────────────────────────────────────────────────────────────
# EXISTING ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/doctor/state-medical-councils")
async def get_doctor_state_medical_councils():
    """List supported state medical councils for NMC verification"""
    return {"state_medical_councils": get_state_medical_councils()}

@router.post("/register/user", response_model=TokenResponse)
async def register_user(user: UserRegister):
    """Register a new user - sends OTP for verification"""
    
    existing_user = users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_doctor = doctors_collection.find_one({"email": user.email})
    if existing_doctor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered as a doctor account"
        )
    
    existing_admin = admin_collection.find_one({"email": user.email})
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user_dict = {
        "name": user.name,
        "email": user.email,
        "password": get_password_hash(user.password),
        "age": user.age,
        "gender": user.gender,
        "location": user.location,
        "has_previous_stress_issues": user.has_previous_stress_issues,
        "phone_number": user.phone_number or "",
        "medical_document_path": None,
        "role": "user",
        "email_verified": False,
        "created_at": datetime.utcnow(),
        "test_history": []
    }
    
    result = users_collection.insert_one(user_dict)
    user_id = str(result.inserted_id)
    
    otp = generate_otp()
    store_otp(user.email, otp, "user")
    email_service.send_otp_email(user.email, otp, "user")
    if user.phone_number:
        sms_service.send_otp_sms(user.phone_number, otp, "user")
    
    return {
        "user": {
            "id": user_id,
            "name": user.name,
            "email": user.email,
            "role": "user",
            "age": user.age,
            "gender": user.gender,
            "location": user.location,
            "email_verified": False
        },
        "message": "Registration successful! Please check your email for the verification code.",
        "access_token": "",
        "token_type": "bearer"
    }

@router.post("/register/doctor", response_model=TokenResponse)
async def register_doctor(doctor: DoctorRegister):
    """Register a new doctor with NMC verification and admin approval workflow"""
    
    existing_doctor = doctors_collection.find_one({"email": doctor.email})
    if existing_doctor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_user = users_collection.find_one({"email": doctor.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered as a user account"
        )
    
    existing_admin = admin_collection.find_one({"email": doctor.email})
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    if not validate_license_number(doctor.license_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid registration/license number format."
        )
    
    existing_license = doctors_collection.find_one({
        "license_number": doctor.license_number.strip().upper()
    })
    if existing_license:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License number already registered"
        )

    nmc_verification = verify_doctor_registration(
        registration_number=doctor.license_number,
        state_medical_council=doctor.state_medical_council,
    )
    if not nmc_verification["verified"]:
        error_detail = nmc_verification["error"] or "Doctor verification failed."
        error_status = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if "unavailable" in error_detail.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=error_status, detail=error_detail)
    
    nmc_profile = build_nmc_profile(nmc_verification["details"])
    doctor_dict = {
        "name": doctor.name,
        "email": doctor.email,
        "password": get_password_hash(doctor.password),
        "license_number": doctor.license_number.strip().upper(),
        "state_medical_council": doctor.state_medical_council,
        "specialization": doctor.specialization,
        "available_slots": doctor.available_slots,
        "phone_number": doctor.phone_number or "",
        "role": "doctor",
        "is_verified": False,
        "nmc_verified": True,
        "nmc_verification": nmc_verification["details"],
        "nmc_profile": nmc_profile,
        "email_verified": False,
        "created_at": datetime.utcnow()
    }
    
    result = doctors_collection.insert_one(doctor_dict)
    doctor_id = str(result.inserted_id)
    
    otp = generate_otp()
    store_otp(doctor.email, otp, "doctor")
    email_service.send_otp_email(doctor.email, otp, "doctor")
    if doctor.phone_number:
        sms_service.send_otp_sms(doctor.phone_number, otp, "doctor")
    
    return {
        "user": {
            "id": doctor_id,
            "name": doctor.name,
            "email": doctor.email,
            "role": "doctor",
            "is_verified": False,
            "nmc_verified": True,
            "state_medical_council": doctor.state_medical_council,
            "nmc_profile": nmc_profile,
            "nmc_verification": nmc_verification["details"],
            "email_verified": False
        },
        "message": (
            "Registration successful! NMC profile verified. "
            "Please verify your email for login; account will be activated after admin approval."
        ),
        "access_token": "",
        "token_type": "bearer"
    }

@router.post("/verify-otp")
async def verify_email_with_otp(request: OTPVerify):
    """Verify email using OTP"""
    
    verification_result = verify_otp(request.email, request.otp)
    
    if not verification_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP. Please request a new code."
        )
    
    user_type = verification_result["user_type"]
    
    if user_type == "user":
        result = users_collection.update_one(
            {"email": request.email},
            {"$set": {"email_verified": True, "verified_at": datetime.utcnow()}}
        )
        collection = users_collection
    elif user_type == "doctor":
        result = doctors_collection.update_one(
            {"email": request.email},
            {"$set": {"email_verified": True, "verified_at": datetime.utcnow()}}
        )
        collection = doctors_collection
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user type"
        )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = collection.find_one({"email": request.email})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    email_service.send_welcome_email(request.email, user["name"], user_type)
    if user.get("phone_number"):
        sms_service.send_welcome_sms(user["phone_number"], user["name"], user_type)
    
    message = "Email verified successfully! You can now log in."
    if user_type == "doctor" and not user.get("is_verified", False):
        message = (
            "Email verified successfully! Your NMC profile is verified and "
            "your account is pending admin approval."
        )

    return {
        "message": message,
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user_type,
            "email_verified": True,
            "is_verified": user.get("is_verified", False if user_type == "doctor" else True),
            "nmc_verified": user.get("nmc_verified", bool(user.get("nmc_verification")))
        }
    }

@router.post("/resend-otp")
async def resend_otp(request: ResendOTPRequest):
    """Resend OTP to email"""
    
    user = users_collection.find_one({"email": request.email})
    user_type = "user"
    
    if not user:
        user = doctors_collection.find_one({"email": request.email})
        user_type = "doctor"
    
    if user and not user.get("email_verified", False):
        otp = generate_otp()
        store_otp(request.email, otp, user_type)
        email_service.send_otp_email(request.email, otp, user_type)
    
    return {"message": "If this email is registered and not yet verified, check your email for the verification code."}

@router.post("/upload-medical-document")
async def upload_medical_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(["user"]))
):
    """Upload medical document for authenticated user"""
    
    user_id = current_user["user_id"]
    filename = file.filename if file.filename else "document"
    
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    max_size = 10 * 1024 * 1024
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 10MB limit"
        )
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{user_id}_{timestamp}{file_ext}"
    file_path = UPLOAD_DIR / safe_filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"medical_document_path": safe_filename}}
    )
    
    return {
        "message": "Medical document uploaded successfully",
        "filename": safe_filename
    }

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login user and return JWT token"""
    
    user = users_collection.find_one({"email": credentials.email})
    role: Optional[str] = "user" if user else None
    
    if not user:
        user = doctors_collection.find_one({"email": credentials.email})
        role = "doctor" if user else None
    
    if not user:
        user = admin_collection.find_one({"email": credentials.email})
        role = "admin" if user else None
    
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if role != "admin" and not user.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in. Check your inbox for the verification code."
        )
    
    if role == "doctor" and not user.get("is_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is awaiting admin approval. Please check back later."
        )
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user role"
        )
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, role, credentials.email)
    
    user_response = {
        "id": user_id,
        "name": user.get("name", user.get("username")),
        "email": user["email"],
        "role": role,
        "email_verified": user.get("email_verified", True)
    }
    
    if role == "user":
        user_response.update({
            "age": user.get("age"),
            "gender": user.get("gender"),
            "location": user.get("location")
        })
    elif role == "doctor":
        user_response["is_verified"] = user.get("is_verified", False)
        user_response["nmc_verified"] = user.get("nmc_verified", bool(user.get("nmc_verification")))
        user_response["state_medical_council"] = user.get("state_medical_council")
        user_response["nmc_profile"] = user.get("nmc_profile")

    return {"user": user_response, "access_token": access_token, "token_type": "bearer"}


@router.post("/change-password")
async def change_password(data: ChangePassword):
    """Change user password after verifying current password"""
    user = users_collection.find_one({"email": data.email})
    collection = users_collection

    if not user:
        user = doctors_collection.find_one({"email": data.email})
        collection = doctors_collection

    if not user:
        user = admin_collection.find_one({"email": data.email})
        collection = admin_collection

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not verify_password(data.current_password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    hashed_new = get_password_hash(data.new_password)
    collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"password": hashed_new, "updated_at": datetime.utcnow()}}
    )

    return {"message": "Password changed successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# FORGOT PASSWORD ENDPOINTS (3 steps)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Step 1 — User submits their email.
    Finds account, generates OTP, sends reset email.
    """
    email = request.email.lower().strip()

    # Search users first, then doctors
    user = users_collection.find_one({"email": email})
    user_type = "user"

    if not user:
        user = doctors_collection.find_one({"email": email})
        user_type = "doctor"

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address."
        )

    # Generate OTP with 10-minute expiry (matches frontend countdown)
    otp_code = generate_otp()
    store_otp(email, otp_code, user_type)

    # Send reset email (non-blocking)
    email_service.send_reset_otp_email(email, otp_code, user.get("name", "User"))

    # Dev fallback — prints OTP to terminal so you can test without email
    print(f"🔑 PASSWORD RESET OTP for {email}: {otp_code}")

    return {
        "message": "Reset code sent successfully. Please check your email.",
        "email": email
    }


@router.post("/verify-reset-otp")
async def verify_reset_otp(request: VerifyResetOTPRequest):
    """
    Step 2 — User submits the 6-digit OTP.
    Validates it and marks as verified.
    NOTE: Does NOT delete OTP — step 3 needs to confirm it was verified.
    """
    email = request.email.lower().strip()
    stored = otp_storage.get(email)

    if not stored:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not found or expired. Please request a new one."
        )

    # Check expiry
    if datetime.utcnow() > stored["expires_at"]:
        del otp_storage[email]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one."
        )

    # Check attempt limit
    if stored.get("attempts", 0) >= 3:
        del otp_storage[email]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many failed attempts. Please request a new OTP."
        )

    # Check OTP value (constant-time comparison to prevent timing attacks)
    if not _compare_digest(stored["otp"], request.otp):
        stored["attempts"] = stored.get("attempts", 0) + 1
        remaining = 3 - stored["attempts"]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP. {remaining} attempt(s) remaining."
        )

    # Mark as verified — keep in storage for step 3
    stored["verified"] = True

    return {"message": "OTP verified successfully.", "email": email}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Step 3 — User submits new password.
    Confirms OTP was verified, then updates password in DB.
    """
    email = request.email.lower().strip()

    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )

    # Confirm OTP was verified in step 2
    stored = otp_storage.get(email)
    if not stored or not stored.get("verified"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not verified. Please complete the verification step first."
        )

    # Hash new password
    hashed = get_password_hash(request.new_password)

    # Update in correct collection
    collection = users_collection if stored.get("user_type") == "user" else doctors_collection
    result = collection.update_one(
        {"email": email},
        {"$set": {
            "password": hashed,
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