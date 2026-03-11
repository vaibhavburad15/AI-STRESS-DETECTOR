from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from datetime import datetime
from bson import ObjectId
from typing import Optional
from ..models import (
    UserRegister, UserLogin, DoctorRegister, TokenResponse,
    OTPVerify, ResendOTPRequest
)
from ..database import users_collection, doctors_collection, admin_collection
from ..auth import verify_password, get_password_hash, require_role, create_access_token
from ..email_service import email_service
from ..sms_service import sms_service
from ..otp_utils import generate_otp, store_otp, verify_otp
from ..nmc_verification import (
    build_nmc_profile,
    get_state_medical_councils,
    verify_doctor_registration,
)
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


@router.get("/doctor/state-medical-councils")
async def get_doctor_state_medical_councils():
    """List supported state medical councils for NMC verification"""
    return {"state_medical_councils": get_state_medical_councils()}

@router.post("/register/user", response_model=TokenResponse)
async def register_user(user: UserRegister):
    """Register a new user - sends OTP for verification"""
    
    # ✅ HIGH FIX: Check email uniqueness across ALL collections, not just users
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
    
    # Create user document
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
    
    # Insert user into database
    result = users_collection.insert_one(user_dict)
    user_id = str(result.inserted_id)
    
    # Generate and send OTP
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
        "access_token": "",  # Placeholder, not issued until email verified
        "token_type": "bearer"
    }

@router.post("/register/doctor", response_model=TokenResponse)
async def register_doctor(doctor: DoctorRegister):
    """Register a new doctor with NMC verification and admin approval workflow"""
    
    # ✅ HIGH FIX: Check email uniqueness across ALL collections
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
    
    # Validate license number format
    if not validate_license_number(doctor.license_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid registration/license number format."
        )
    
    # Check if license number already exists
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
        raise HTTPException(
            status_code=error_status,
            detail=error_detail,
        )
    
    # Create doctor document
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
        "is_verified": False,  # Admin approval is still required
        "nmc_verified": True,
        "nmc_verification": nmc_verification["details"],
        "nmc_profile": nmc_profile,
        "email_verified": False,
        "created_at": datetime.utcnow()
    }
    
    # Insert doctor into database
    result = doctors_collection.insert_one(doctor_dict)
    doctor_id = str(result.inserted_id)
    
    # Generate and send OTP
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
        "access_token": "",  # Placeholder, not issued until email verified and admin approval
        "token_type": "bearer"
    }

@router.post("/verify-otp")
async def verify_email_with_otp(request: OTPVerify):
    """Verify email using OTP"""
    
    # Verify the OTP
    verification_result = verify_otp(request.email, request.otp)
    
    if not verification_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP. Please request a new code."
        )
    
    user_type = verification_result["user_type"]
    
    # Update user's email_verified status
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
    
    # Get updated user data
    user = collection.find_one({"email": request.email})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Send welcome email + SMS
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
    # ✅ LOW/MEDIUM FIX: Prevent email enumeration by always returning same response
    
    # Check in users collection
    user = users_collection.find_one({"email": request.email})
    user_type = "user"
    
    if not user:
        # Check in doctors collection
        user = doctors_collection.find_one({"email": request.email})
        user_type = "doctor"
    
    # Always return same response regardless of whether email exists or is verified
    # This prevents attackers from enumerating valid email addresses
    if user and not user.get("email_verified", False):
        # Generate new OTP and send email
        otp = generate_otp()
        store_otp(request.email, otp, user_type)
        email_service.send_otp_email(request.email, otp, user_type)
    
    # Always give same response to avoid enumeration
    return {"message": "If this email is registered and not yet verified, check your email for the verification code."}

@router.post("/upload-medical-document")
async def upload_medical_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(["user"]))
):
    """Upload medical document for authenticated user (can only upload for themselves)"""
    
    # ✅ CRITICAL FIX: Authenticate user and ensure they can only upload for themselves
    user_id = current_user["user_id"]
    
    # Get filename safely
    filename = file.filename if file.filename else "document"
    
    # Validate file type
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 10MB limit"
        )
    
    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{user_id}_{timestamp}{file_ext}"
    file_path = UPLOAD_DIR / safe_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Update user document with file path
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"medical_document_path": safe_filename}}  # Store only filename, not full path
    )
    
    return {
        "message": "Medical document uploaded successfully",
        "filename": safe_filename
    }

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login user (email must be verified) and return JWT token"""
    
    # Try to find user in different collections
    user = users_collection.find_one({"email": credentials.email})
    role: Optional[str] = "user" if user else None
    
    if not user:
        user = doctors_collection.find_one({"email": credentials.email})
        role = "doctor" if user else None
    
    if not user:
        user = admin_collection.find_one({"email": credentials.email})
        role = "admin" if user else None
    
    # Check credentials
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if email is verified (skip for admin)
    if role != "admin" and not user.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in. Check your inbox for the verification code."
        )
    
    # ✅ HIGH FIX: Check if doctor is approved by admin before allowing login
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
    
    # Create JWT token
    access_token = create_access_token(user_id, role, credentials.email)
    
    # Prepare user response
    user_response = {
        "id": user_id,
        "name": user.get("name", user.get("username")),
        "email": user["email"],
        "role": role,
        "email_verified": user.get("email_verified", True)
    }
    
    # Add role-specific fields
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
