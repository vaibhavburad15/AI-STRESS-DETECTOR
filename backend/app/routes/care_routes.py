"""Care-facing route groups for doctors and medical records."""

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional, Any, Mapping
import os
import shutil
import hashlib
import mimetypes
import logging
import re
import unicodedata
from pathlib import Path
import zipfile
import io
from pymongo.errors import DuplicateKeyError

try:
    import magic  # type: ignore
except ImportError:
    magic = None

from ..models import (
    MedicalRecordUpload, MedicalRecordResponse, MedicalRecordUpdate,
    MedicalRecordFilter, TestResultAdd, DownloadRequest,
    BulkDownloadRequest, MedicalRecordStats, AppointmentUpdate
)
from ..database import (
    appointments_collection, users_collection, tests_collection,
    medical_records_collection, medical_record_activities_collection
)
from ..appointment_access import (
    add_access_state,
    build_slot_reservation_key,
    get_appointment_by_id,
    require_doctor_appointment_data_access,
    require_doctor_owned_appointment,
    require_doctor_user_access,
)
from ..auth import require_role
from ..email_service import email_service
from ..recommendation_engine import enhanced_engine
from ..sms_service import sms_service

router = APIRouter()
medical_records_router = APIRouter(prefix="/api/medical-records", tags=["Medical Records"])
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_DIR = Path("uploads/medical_records")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
STORAGE_LIMIT_MB = 100  # Per user storage limit

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_file_hash(file_path: str) -> str:
    """Generate SHA-256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_user_storage_used(user_id: str) -> float:
    """Get total storage used by user in MB"""
    records = list(medical_records_collection.find({"user_id": user_id, "deleted": False}))
    total_bytes = sum(record.get("file_size", 0) for record in records)
    return total_bytes / (1024 * 1024)  # Convert to MB

def validate_file(file: UploadFile) -> tuple:
    """Validate uploaded file"""
    # Check filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Validate content with MIME detection when python-magic is available.
    header = file.file.read(8)
    file.file.seek(0)
    sample = file.file.read(2048)
    file.file.seek(0)
    mime_type = None

    if magic is not None:
        try:
            mime_type = magic.Magic(mime=True).from_buffer(sample)
        except Exception as exc:
            logger.warning("python-magic failed, using signature fallback: %s", exc)

    allowed_mimes = {
        ".pdf": {"application/pdf"},
        ".jpg": {"image/jpeg"},
        ".jpeg": {"image/jpeg"},
        ".png": {"image/png"},
        ".doc": {"application/msword", "application/octet-stream"},
        ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"},
    }

    if mime_type and mime_type not in allowed_mimes.get(file_ext, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid MIME type '{mime_type}' for {file_ext} file",
        )

    # Fallback signature checks for environments without libmagic.
    if file_ext == ".pdf" and not header.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF content")
    if file_ext in {".jpg", ".jpeg"} and not header.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=400, detail="Invalid JPEG content")
    if file_ext == ".png" and header != b"\x89PNG\r\n\x1a\n":
        raise HTTPException(status_code=400, detail="Invalid PNG content")
    if file_ext == ".docx" and not header.startswith(b"PK"):
        raise HTTPException(status_code=400, detail="Invalid DOCX content")
    
    # Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    return file_ext, file_size

def log_activity(record_id: str, action: str, details: str = ""):
    """Log medical record activity"""
    try:
        medical_record_activities_collection.insert_one({
            "record_id": record_id,
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        print(f"⚠️ Failed to log activity: {e}")

# ============================================
# UPLOAD ENDPOINTS
# ============================================

@medical_records_router.post("/upload", response_model=MedicalRecordResponse)
async def upload_medical_record(
    user_id: str = Form(...),
    record_name: str = Form(...),
    record_type: str = Form(...),
    description: Optional[str] = Form(None),
    record_date: Optional[str] = Form(None),
    doctor_name: Optional[str] = Form(None),
    hospital_name: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON string of tags
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(["user"]))
):
    """Upload a medical record"""
    # ✅ CRITICAL FIX: Verify authenticated user matches user_id
    if current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only upload records for yourself"
        )
    
    # Check storage limit
    storage_used = get_user_storage_used(user_id)
    if storage_used >= STORAGE_LIMIT_MB:
        raise HTTPException(
            status_code=400,
            detail=f"Storage limit exceeded. Maximum: {STORAGE_LIMIT_MB}MB"
        )
    
    # Validate file
    file_ext, file_size = validate_file(file)
    
    # Check if adding this file exceeds limit
    if storage_used + (file_size / (1024 * 1024)) > STORAGE_LIMIT_MB:
        raise HTTPException(
            status_code=400,
            detail=f"Adding this file would exceed storage limit"
        )
    
    # Generate unique filename - FIXED: Handle None filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename_for_hash = file.filename if file.filename else "unnamed_file"
    normalized_name = unicodedata.normalize("NFKD", filename_for_hash)
    ascii_name = normalized_name.encode("ascii", "ignore").decode("ascii")
    clean_name = re.sub(r"[^A-Za-z0-9._-]", "_", ascii_name).strip("._") or "unnamed_file"
    safe_filename = f"{user_id}_{timestamp}_{hashlib.md5(clean_name.encode()).hexdigest()[:8]}{file_ext}"
    file_path = UPLOAD_DIR / safe_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Get file hash for integrity
    file_hash = get_file_hash(str(file_path))
    
    # Parse tags
    tags_list = []
    if tags:
        try:
            import json
            tags_list = json.loads(tags)
        except (ValueError, TypeError, AttributeError):
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]
    
    # Parse record date
    parsed_record_date = None
    if record_date:
        try:
            parsed_record_date = datetime.fromisoformat(record_date.replace('Z', '+00:00'))
        except ValueError:
            logger.warning("Invalid record_date format received: %s", record_date)
    
    # Create medical record document
    record_dict = {
        "user_id": user_id,
        "record_name": record_name,
        "record_type": record_type,
        "file_name": file.filename,
        "file_path": str(file_path),
        "file_size": file_size,
        "file_format": file_ext.replace(".", ""),
        "file_hash": file_hash,
        "description": description,
        "record_date": parsed_record_date,
        "doctor_name": doctor_name,
        "hospital_name": hospital_name,
        "notes": notes,
        "tags": tags_list,
        "uploaded_at": datetime.utcnow(),
        "updated_at": None,
        "download_count": 0,
        "is_linked_to_stress_test": False,
        "linked_test_id": None,
        "deleted": False
    }
    
    result = medical_records_collection.insert_one(record_dict)
    record_id = str(result.inserted_id)
    
    # Log activity
    log_activity(record_id, "uploaded", f"File: {file.filename}")
    
    return {
        "id": record_id,
        "user_id": user_id,
        "record_name": record_name,
        "record_type": record_type,
        "file_name": file.filename or "unnamed",
        "file_path": str(file_path),
        "file_size": file_size,
        "file_format": file_ext.replace(".", ""),
        "description": description,
        "record_date": parsed_record_date,
        "doctor_name": doctor_name,
        "hospital_name": hospital_name,
        "notes": notes,
        "tags": tags_list,
        "uploaded_at": record_dict["uploaded_at"],
        "updated_at": None,
        "download_count": 0,
        "is_linked_to_stress_test": False,
        "linked_test_id": None
    }

# ============================================
# READ/LIST ENDPOINTS
# ============================================

@medical_records_router.get("/user/{user_id}", response_model=List[MedicalRecordResponse])
async def get_user_medical_records(
    user_id: str,
    record_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(require_role(["user", "doctor"]))
):
    """Get all medical records for a user with optional filters"""
    
    # ✅ CRITICAL FIX: Add object-level authorization and validate user_id
    try:
        ObjectId(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    if current_user["role"] == "user" and current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own medical records"
        )
    if current_user["role"] == "doctor":
        require_doctor_user_access(current_user, user_id)
    
    # Build query
    query = {"user_id": user_id, "deleted": False}
    
    if record_type:
        query["record_type"] = record_type
    
    if from_date or to_date:
        date_query = {}
        if from_date:
            date_query["$gte"] = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
        if to_date:
            date_query["$lte"] = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
        query["uploaded_at"] = date_query
    
    if search:
        query["$or"] = [
            {"record_name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"notes": {"$regex": search, "$options": "i"}},
            {"tags": {"$in": [search]}}
        ]
    
    records = list(medical_records_collection.find(query).sort("uploaded_at", -1))
    
    return [
        {
            "id": str(record["_id"]),
            "user_id": record["user_id"],
            "record_name": record["record_name"],
            "record_type": record["record_type"],
            "file_name": record["file_name"],
            # ✅ FIX: Don't return file_path that leaks filesystem layout
            "file_size": record["file_size"],
            "file_format": record["file_format"],
            "description": record.get("description"),
            "record_date": record.get("record_date"),
            "doctor_name": record.get("doctor_name"),
            "hospital_name": record.get("hospital_name"),
            "notes": record.get("notes"),
            "tags": record.get("tags", []),
            "uploaded_at": record["uploaded_at"],
            "updated_at": record.get("updated_at"),
            "download_count": record.get("download_count", 0),
            "is_linked_to_stress_test": record.get("is_linked_to_stress_test", False),
            "linked_test_id": record.get("linked_test_id")
        }
        for record in records
    ]

@medical_records_router.get("/{record_id}", response_model=MedicalRecordResponse)
async def get_medical_record(
    record_id: str,
    current_user: dict = Depends(require_role(["user", "doctor"]))
):
    """Get a specific medical record - users can only access their own"""
    
    # ✅ CRITICAL FIX: Validate ID format
    try:
        ObjectId(record_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid record ID format"
        )
    
    record = medical_records_collection.find_one({"_id": ObjectId(record_id), "deleted": False})
    
    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")
    
    # ✅ CRITICAL FIX: Add object-level authorization
    if current_user["role"] == "user" and current_user["user_id"] != record["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own medical records"
        )
    if current_user["role"] == "doctor":
        require_doctor_user_access(current_user, record["user_id"])
    
    return {
        "id": str(record["_id"]),
        "user_id": record["user_id"],
        "record_name": record["record_name"],
        "record_type": record["record_type"],
        "file_name": record["file_name"],
        # ✅ FIX: Don't return full file_path that leaks filesystem layout
        "file_size": record["file_size"],
        "file_format": record["file_format"],
        "description": record.get("description"),
        "record_date": record.get("record_date"),
        "doctor_name": record.get("doctor_name"),
        "hospital_name": record.get("hospital_name"),
        "notes": record.get("notes"),
        "tags": record.get("tags", []),
        "uploaded_at": record["uploaded_at"],
        "updated_at": record.get("updated_at"),
        "download_count": record.get("download_count", 0),
        "is_linked_to_stress_test": record.get("is_linked_to_stress_test", False),
        "linked_test_id": record.get("linked_test_id")
    }

# ============================================
# UPDATE ENDPOINTS
# ============================================

@medical_records_router.put("/{record_id}", response_model=MedicalRecordResponse)
async def update_medical_record(
    record_id: str,
    update: MedicalRecordUpdate,
    current_user: dict = Depends(require_role(["user"]))
):
    """Update medical record metadata (not the file) - users can only update their own"""
    
    # ✅ FIX: Validate ID format
    try:
        ObjectId(record_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid record ID format"
        )
    
    record = medical_records_collection.find_one({"_id": ObjectId(record_id), "deleted": False})
    
    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")
    
    # ✅ CRITICAL FIX: Add object-level authorization
    if current_user["user_id"] != record["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own medical records"
        )
    
    # Build update dict - FIXED: Explicit typing to prevent type errors
    update_dict: dict[str, Any] = {"updated_at": datetime.utcnow()}
    
    if update.record_name:
        update_dict["record_name"] = update.record_name
    if update.record_type:
        update_dict["record_type"] = update.record_type.value  # FIXED: Extract string from enum
    if update.description is not None:
        update_dict["description"] = update.description
    if update.record_date:
        try:
            update_dict["record_date"] = datetime.fromisoformat(update.record_date.replace('Z', '+00:00'))
        except ValueError:
            logger.warning("Invalid update.record_date format received: %s", update.record_date)
    if update.doctor_name is not None:
        update_dict["doctor_name"] = update.doctor_name
    if update.hospital_name is not None:
        update_dict["hospital_name"] = update.hospital_name
    if update.notes is not None:
        update_dict["notes"] = update.notes
    if update.tags is not None:
        update_dict["tags"] = update.tags
    
    medical_records_collection.update_one(
        {"_id": ObjectId(record_id)},
        {"$set": update_dict}
    )
    
    # Log activity
    log_activity(record_id, "updated", "Metadata updated")
    
    # Get updated record
    updated_record = medical_records_collection.find_one({"_id": ObjectId(record_id)})
    
    # FIXED: Add null check to prevent subscript errors
    if not updated_record:
        raise HTTPException(status_code=404, detail="Record not found after update")
    
    return {
        "id": str(updated_record["_id"]),
        "user_id": updated_record["user_id"],
        "record_name": updated_record["record_name"],
        "record_type": updated_record["record_type"],
        "file_name": updated_record["file_name"],
        "file_path": updated_record["file_path"],
        "file_size": updated_record["file_size"],
        "file_format": updated_record["file_format"],
        "description": updated_record.get("description"),
        "record_date": updated_record.get("record_date"),
        "doctor_name": updated_record.get("doctor_name"),
        "hospital_name": updated_record.get("hospital_name"),
        "notes": updated_record.get("notes"),
        "tags": updated_record.get("tags", []),
        "uploaded_at": updated_record["uploaded_at"],
        "updated_at": updated_record.get("updated_at"),
        "download_count": updated_record.get("download_count", 0),
        "is_linked_to_stress_test": updated_record.get("is_linked_to_stress_test", False),
        "linked_test_id": updated_record.get("linked_test_id")
    }

# ============================================
# DELETE ENDPOINTS
# ============================================

@medical_records_router.delete("/{record_id}")
async def delete_medical_record(
    record_id: str,
    permanent: bool = False,
    current_user: dict = Depends(require_role(["user"]))
):
    """Delete a medical record (soft delete by default)"""
    
    record = medical_records_collection.find_one({"_id": ObjectId(record_id)})
    
    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")
    
    # ✅ CRITICAL FIX: Add object-level authorization
    if current_user["user_id"] != record["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own medical records"
        )
    
    if permanent:
        # Permanent delete - remove file and database record
        try:
            if os.path.exists(record["file_path"]):
                os.remove(record["file_path"])
        except Exception as e:
            print(f"⚠️ Failed to delete file: {e}")
        
        medical_records_collection.delete_one({"_id": ObjectId(record_id)})
        log_activity(record_id, "deleted_permanently", "File and record removed")
        
        return {"message": "Medical record permanently deleted"}
    else:
        # Soft delete - mark as deleted
        medical_records_collection.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": {"deleted": True, "deleted_at": datetime.utcnow()}}
        )
        log_activity(record_id, "deleted", "Soft delete")
        
        return {"message": "Medical record deleted"}

# ============================================
# DOWNLOAD ENDPOINTS
# ============================================

# ─────────────────────────────────────────────────────────────
# PDF GENERATOR for stress test records
# ─────────────────────────────────────────────────────────────

def _generate_stress_pdf(record: dict, stress_data: dict) -> "io.BytesIO":
    """Build a professional PDF report for a stress-test medical record."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from datetime import datetime as _dt

    QUESTIONNAIRE = [
        {"id":  1, "question": "How often do you feel nervous or anxious?",                       "category": "Emotional"},
        {"id":  2, "question": "How often do you feel sad or depressed?",                          "category": "Emotional"},
        {"id":  3, "question": "How often do you feel irritable or angry?",                        "category": "Emotional"},
        {"id":  4, "question": "How often do you experience headaches or body pain?",              "category": "Physical"},
        {"id":  5, "question": "How often do you feel physically fatigued or exhausted?",          "category": "Physical"},
        {"id":  6, "question": "How often do you have trouble falling or staying asleep?",         "category": "Physical"},
        {"id":  7, "question": "How often do you experience rapid heartbeat or chest tightness?",  "category": "Physical"},
        {"id":  8, "question": "How often do you have difficulty concentrating?",                  "category": "Cognitive"},
        {"id":  9, "question": "How often do you have negative or intrusive thoughts?",            "category": "Cognitive"},
        {"id": 10, "question": "How often do you worry excessively about the future?",             "category": "Cognitive"},
        {"id": 11, "question": "How often do you have difficulty making decisions?",               "category": "Cognitive"},
        {"id": 12, "question": "How often have you experienced changes in appetite?",              "category": "Behavioral"},
        {"id": 13, "question": "How often do you avoid social interactions?",                      "category": "Behavioral"},
        {"id": 14, "question": "How often do you feel overwhelmed by daily tasks?",                "category": "Behavioral"},
        {"id": 15, "question": "How satisfied are you with your work-life balance?",               "category": "Stressors"},
        {"id": 16, "question": "How much stress do you experience from work or studies?",          "category": "Stressors"},
        {"id": 17, "question": "How much stress do you experience from relationships?",            "category": "Stressors"},
        {"id": 18, "question": "How much stress do you experience from financial concerns?",       "category": "Stressors"},
    ]
    SCALE: dict = {1: "Never / Not at all", 2: "Rarely / Slightly",
                   3: "Sometimes / Moderately", 4: "Often / Very", 5: "Always / Extremely"}
    STRESS_CLR: dict = {"Low": "#16a34a", "Moderate": "#d97706",
                        "High": "#ea580c", "Severe": "#dc2626"}
    CAT_CLR: dict = {"Emotional": "#8b5cf6", "Physical": "#0ea5e9",
                     "Cognitive": "#f59e0b", "Behavioral": "#10b981", "Stressors": "#ef4444"}

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    def ps(name: str, **kw) -> ParagraphStyle:          # quick helper
        return ParagraphStyle(name, **kw)

    story: list = []

    # Header banner
    hdr_data: list = [[
        Paragraph("AI Stress Level Analyzer",
                  ps("hl", fontName="Helvetica-Bold", fontSize=16,
                     textColor=colors.white, alignment=TA_LEFT)),
        Paragraph("Mental Health Assessment Report",
                  ps("hr", fontName="Helvetica", fontSize=10,
                     textColor=colors.whitesmoke, alignment=TA_RIGHT)),
    ]]
    hdr_tbl = Table(hdr_data, colWidths=["60%", "40%"])
    hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#1d4ed8")),
        ("TOPPADDING",    (0,0), (-1,-1), 14), ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING",   (0,0), (-1,-1), 14), ("RIGHTPADDING",  (0,0), (-1,-1), 14),
    ]))
    story += [hdr_tbl, Spacer(1, 0.5*cm)]

    # Title
    story.append(Paragraph(
        record.get("record_name") or "Stress Assessment Report",
        ps("t", fontName="Helvetica-Bold", fontSize=18, spaceAfter=4, alignment=TA_CENTER)
    ))

    raw: Any = record.get("record_date") or record.get("uploaded_at")
    if isinstance(raw, _dt):
        date_str = raw.strftime("%B %d, %Y at %I:%M %p")
    else:
        date_str = str(raw) if raw else "Unknown Date"

    story += [
        Paragraph(f"Assessment Date: {date_str}",
                  ps("sub", fontName="Helvetica", fontSize=10,
                     textColor=colors.grey, alignment=TA_CENTER)),
        Spacer(1, 0.4*cm),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")),
        Spacer(1, 0.5*cm),
    ]

    # Summary box
    slabel = str(stress_data.get("stress_label") or "Unknown")
    slevel = int(stress_data.get("stress_level") or 0)
    sconf  = float(stress_data.get("confidence_score") or 0)
    sclr   = colors.HexColor(STRESS_CLR.get(slabel, "#6b7280"))

    lbl_s = ps("lbl", fontName="Helvetica-Bold", fontSize=9,
                textColor=colors.HexColor("#6b7280"), alignment=TA_CENTER)
    val_s = ps("val", fontName="Helvetica-Bold", fontSize=22, alignment=TA_CENTER)

    sum_data: list = [
        [Paragraph("Stress Level", lbl_s), Paragraph("Severity Score", lbl_s), Paragraph("Confidence", lbl_s)],
        [Paragraph(slabel, val_s),          Paragraph(f"{slevel} / 3", val_s),  Paragraph(f"{sconf*100:.1f}%", val_s)],
    ]
    sum_tbl = Table(sum_data, colWidths=["33%", "33%", "34%"])
    sum_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#f0f9ff")),
        ("BOX",           (0,0), (-1,-1), 1,   colors.HexColor("#bae6fd")),
        ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor("#e0f2fe")),
        ("TOPPADDING",    (0,0), (-1,-1), 10), ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TEXTCOLOR",     (0,1), (0,1),   sclr),
    ]))
    story += [sum_tbl, Spacer(1, 0.6*cm)]

    if record.get("notes"):
        story += [
            Paragraph("<b>Notes:</b>", ps("nh", fontName="Helvetica-Bold", fontSize=10)),
            Paragraph(str(record["notes"]),
                      ps("nb", fontName="Helvetica", fontSize=9, leftIndent=10,
                         textColor=colors.HexColor("#374151"))),
            Spacer(1, 0.4*cm),
        ]

    # Q&A
    story += [
        Paragraph("Assessment Responses",
                  ps("sec", fontName="Helvetica-Bold", fontSize=13,
                     textColor=colors.HexColor("#1e3a8a"), spaceAfter=6)),
        Paragraph(
            "Scale: 1=Never/Not at all  |  2=Rarely/Slightly  |  3=Sometimes/Moderately  "
            "|  4=Often/Very  |  5=Always/Extremely",
            ps("sc", fontName="Helvetica-Oblique", fontSize=8,
               textColor=colors.grey, spaceAfter=8)),
    ]

    responses: list = list(stress_data.get("responses") or [])
    grouped: dict = {c: [] for c in ["Emotional", "Physical", "Cognitive", "Behavioral", "Stressors"]}
    for q in QUESTIONNAIRE:
        idx = q["id"] - 1
        ans = responses[idx] if idx < len(responses) else None
        grouped[q["category"]].append((q["id"], q["question"], ans))

    qn = ps("qn", fontName="Helvetica",        fontSize=8, alignment=TA_CENTER)
    qq = ps("qq", fontName="Helvetica",        fontSize=8)
    qs = ps("qs", fontName="Helvetica-Bold",   fontSize=9, alignment=TA_CENTER)
    ql = ps("ql", fontName="Helvetica-Oblique",fontSize=8, textColor=colors.HexColor("#6b7280"))
    qh = ps("qh", fontName="Helvetica-Bold",   fontSize=8)

    no_responses = len(responses) == 0

    for cat in ["Emotional", "Physical", "Cognitive", "Behavioral", "Stressors"]:
        items = grouped.get(cat, [])
        if not items:
            continue

        cat_clr = colors.HexColor(CAT_CLR.get(cat, "#6b7280"))
        cat_hdr: list = [[Paragraph(cat, ps("ch", fontName="Helvetica-Bold",
                                             fontSize=10, textColor=colors.white))]]
        ct = Table(cat_hdr, colWidths=["100%"])
        ct.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), cat_clr),
            ("TOPPADDING",    (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ]))
        story.append(ct)

        q_data: list = [[Paragraph("#", qh), Paragraph("Question", qh),
                         Paragraph("Score", qh), Paragraph("Label", qh)]]
        for qid, question, ans in items:
            score_label = SCALE.get(int(ans), "N/A") if ans is not None else ("N/A" if no_responses else "-")
            score_str   = str(ans) if ans is not None else ("-" if not no_responses else "N/A")
            q_data.append([
                Paragraph(str(qid), qn),
                Paragraph(question, qq),
                Paragraph(score_str, qs),
                Paragraph(score_label, ql),
            ])

        qt = Table(q_data, colWidths=[1*cm, 10*cm, 1.5*cm, 4.5*cm])
        qt.setStyle(TableStyle([
            ("BACKGROUND",     (0,0), (-1,0),  colors.HexColor("#f3f4f6")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f9fafb")]),
            ("GRID",           (0,0), (-1,-1), 0.3, colors.HexColor("#e5e7eb")),
            ("ALIGN",          (0,0), (0,-1),  "CENTER"),
            ("ALIGN",          (2,0), (2,-1),  "CENTER"),
            ("TOPPADDING",     (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",    (0,0), (-1,-1), 6),
        ]))
        story += [qt, Spacer(1, 0.3*cm)]

    # Recommendations
    recs: list = enhanced_engine.extract_recommendation_lines(stress_data.get("enhanced_recommendations"))
    if not recs:
        recs = list(stress_data.get("recommendations") or [])
    if recs:
        story += [
            Spacer(1, 0.3*cm),
            Paragraph("Personalized Recommendations",
                       ps("rh", fontName="Helvetica-Bold", fontSize=13,
                          textColor=colors.HexColor("#1e3a8a"), spaceAfter=6)),
        ]
        meta = stress_data.get("enhanced_recommendations", {}).get("meta", {}) if isinstance(stress_data.get("enhanced_recommendations"), dict) else {}
        primary_source = str(meta.get("primary_source") or "").strip()
        if primary_source:
            source_label = "AI-powered recommendations" if primary_source == "llm" else "Rule-based recommendations"
            story.append(Paragraph(
                source_label,
                ps("rmeta", fontName="Helvetica-Oblique", fontSize=8,
                   leftIndent=10, spaceAfter=5, textColor=colors.HexColor("#64748b"))
            ))
        for i, rec in enumerate(recs, 1):
            story.append(Paragraph(f"{i}. {rec}",
                                   ps("ri", fontName="Helvetica", fontSize=9,
                                      leftIndent=10, spaceAfter=4,
                                      textColor=colors.HexColor("#374151"))))
    elif no_responses:
        story += [
            Spacer(1, 0.3*cm),
            Paragraph(
                "Note: Detailed question responses were not available for this record. "
                "The summary above reflects the overall assessment result.",
                ps("note", fontName="Helvetica-Oblique", fontSize=9,
                   textColor=colors.HexColor("#6b7280"))),
        ]

    # Footer
    story += [
        Spacer(1, 0.8*cm),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb")),
        Spacer(1, 0.2*cm),
        Paragraph(
            "This report was generated by the AI Stress Level Analyzer. "
            "It is for informational purposes only and does not replace professional medical advice. "
            "Please consult a qualified healthcare provider for diagnosis and treatment.",
            ps("ft", fontName="Helvetica-Oblique", fontSize=7,
               textColor=colors.grey, alignment=TA_CENTER)),
    ]

    doc.build(story)
    buf.seek(0)
    return buf


@medical_records_router.get("/download/{record_id}")
async def download_medical_record(
    record_id: str,
    current_user: dict = Depends(require_role(["user", "doctor"]))
):
    """Download a medical record file (auto-generates PDF for stress test records)"""

    record = medical_records_collection.find_one({"_id": ObjectId(record_id), "deleted": False})

    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")
    
    # ✅ CRITICAL FIX: Add object-level authorization
    if current_user["role"] == "user" and current_user["user_id"] != record["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only download your own medical records"
        )
    if current_user["role"] == "doctor":
        require_doctor_user_access(current_user, record["user_id"])

    # ── Stress test: generate PDF regardless of how it was stored ─
    is_stress = (
        record.get("is_linked_to_stress_test") is True
        or record.get("record_type") == "stress_test"
    )
    if is_stress:
        stress_data: Optional[dict] = None

        # 1) Embedded stress_test_data on the record (most records)
        embedded = record.get("stress_test_data")
        if isinstance(embedded, dict) and embedded:
            stress_data = embedded

        # 2) Fetch from tests collection via linked_test_id
        if not stress_data:
            linked_id = record.get("linked_test_id")
            if linked_id:
                try:
                    test_doc = tests_collection.find_one({"_id": ObjectId(str(linked_id))})
                    if test_doc:
                        stress_data = {
                            "stress_level":     test_doc.get("stress_level", 0),
                            "stress_label":     test_doc.get("stress_label", "Unknown"),
                            "confidence_score": test_doc.get("confidence_score", 0),
                            "responses":        test_doc.get("responses", []),
                            "recommendations":  test_doc.get("recommendations", []),
                            "enhanced_recommendations": test_doc.get("enhanced_recommendations"),
                        }
                        print(f"✅ Fetched stress data from tests_collection for {record_id}")
                except Exception as ex:
                    print(f"⚠️ tests_collection lookup failed: {ex}")

        # 3) Build from description field (handles pre-fix records)
        if not stress_data:
            description = str(record.get("description") or "")
            slabel, sconf = "Unknown", 0.0
            try:
                if "Stress Level:" in description:
                    slabel = description.split("Stress Level:")[-1].split("(")[0].strip()
                if "Confidence:" in description:
                    sconf = float(
                        description.split("Confidence:")[-1]
                        .replace("%", "").replace(")", "").strip()
                    ) / 100
            except Exception:
                pass
            stress_data = {
                "stress_level": 0, "stress_label": slabel,
                "confidence_score": sconf,
                "responses": [], "recommendations": [],
                "enhanced_recommendations": None,
            }
            print(f"⚠️ Using description fallback for stress PDF: {record_id}")

        try:
            pdf_buf = _generate_stress_pdf(record, stress_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

        medical_records_collection.update_one(
            {"_id": ObjectId(record_id)}, {"$inc": {"download_count": 1}}
        )
        log_activity(record_id, "downloaded", "Stress test PDF generated")

        safe_name = str(record.get("record_name") or "stress_report").replace(" ", "_")
        return StreamingResponse(
            pdf_buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'}
        )

    # ── Regular file records ───────────────────────────────────
    file_path: str = record.get("file_path") or ""
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    medical_records_collection.update_one(
        {"_id": ObjectId(record_id)}, {"$inc": {"download_count": 1}}
    )
    log_activity(record_id, "downloaded", f"File: {record['file_name']}")

    media_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    return FileResponse(path=file_path, filename=record["file_name"], media_type=media_type)

@medical_records_router.post("/download/bulk")
async def download_bulk_medical_records(
    request: BulkDownloadRequest,
    current_user: dict = Depends(require_role(["user"]))
):
    """Download multiple medical records as a ZIP file"""
    # ✅ CRITICAL FIX: Add object-level authorization
    if current_user["user_id"] != request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only download your own medical records"
        )
    
    # Get all records
    records = list(medical_records_collection.find({
        "_id": {"$in": [ObjectId(rid) for rid in request.record_ids]},
        "user_id": request.user_id,
        "deleted": False
    }))
    
    if not records:
        raise HTTPException(status_code=404, detail="No records found")
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for record in records:
            file_path = record["file_path"]
            if os.path.exists(file_path):
                zip_file.write(file_path, record["file_name"])
                
                # Increment download count
                medical_records_collection.update_one(
                    {"_id": record["_id"]},
                    {"$inc": {"download_count": 1}}
                )
    
    zip_buffer.seek(0)
    
    # Log activity
    for record in records:
        log_activity(str(record["_id"]), "downloaded_bulk", "Downloaded in ZIP")
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=medical_records_{datetime.now().strftime('%Y%m%d')}.zip"}
    )

# ============================================
# STRESS TEST LINKING ENDPOINTS
# ============================================

@medical_records_router.post("/link-stress-test")
async def link_stress_test_to_medical_record(
    test_add: TestResultAdd,
    current_user: dict = Depends(require_role(["user"]))
):
    """Add a stress test to medical records"""
    # ✅ CRITICAL FIX: Use authenticated user_id, not client-provided
    user_id = current_user["user_id"]
    
    # Get stress test
    stress_test = tests_collection.find_one({"_id": ObjectId(test_add.stress_test_id), "user_id": user_id})
    
    if not stress_test:
        raise HTTPException(status_code=404, detail="Stress test not found")
    
    if not test_add.add_to_medical_records:
        return {"message": "Test not added to medical records"}
    
    # Generate record name
    test_date = stress_test["timestamp"].strftime("%Y-%m-%d")
    record_name = test_add.record_name or f"Stress Test - {test_date}"
    
    # Create medical record entry
    record_dict = {
        "user_id": user_id,
        "record_name": record_name,
        "record_type": "stress_test",
        "file_name": f"stress_test_{test_add.stress_test_id}.json",
        "file_path": "",  # No file, data is in database
        "file_size": 0,
        "file_format": "json",
        "file_hash": "",
        "description": f"Stress Level: {stress_test['stress_label']} (Confidence: {stress_test['confidence_score']:.2%})",
        "record_date": stress_test["timestamp"],
        "doctor_name": None,
        "hospital_name": None,
        "notes": test_add.notes or "",
        "tags": ["stress-test", stress_test["stress_label"].lower()],
        "uploaded_at": datetime.utcnow(),
        "updated_at": None,
        "download_count": 0,
        "is_linked_to_stress_test": True,
        "linked_test_id": test_add.stress_test_id,
        "deleted": False,
        "stress_test_data": {
            "stress_level": stress_test["stress_level"],
            "stress_label": stress_test["stress_label"],
            "confidence_score": stress_test["confidence_score"],
            "responses": stress_test["responses"],
            "recommendations": stress_test.get("recommendations", []),
            "enhanced_recommendations": stress_test.get("enhanced_recommendations"),
        }
    }
    
    result = medical_records_collection.insert_one(record_dict)
    record_id = str(result.inserted_id)
    
    # Log activity
    log_activity(record_id, "linked", f"Linked to stress test {test_add.stress_test_id}")
    
    return {
        "message": "Stress test added to medical records",
        "record_id": record_id,
        "stress_test_id": test_add.stress_test_id
    }

# ============================================
# STATISTICS ENDPOINTS
# ============================================

@medical_records_router.get("/stats/{user_id}", response_model=MedicalRecordStats)
async def get_medical_records_stats(
    user_id: str,
    current_user: dict = Depends(require_role(["user"]))
):
    """Get medical records statistics for a user"""
    # ✅ CRITICAL FIX: Add object-level authorization
    if current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own statistics"
        )
    
    records = list(medical_records_collection.find({"user_id": user_id, "deleted": False}))
    
    total_size = sum(r.get("file_size", 0) for r in records)
    total_size_mb = total_size / (1024 * 1024)
    
    # Count by type
    records_by_type = {}
    for record in records:
        rtype = record.get("record_type", "other")
        records_by_type[rtype] = records_by_type.get(rtype, 0) + 1
    
    # Recent uploads (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_uploads = len([r for r in records if r["uploaded_at"] >= thirty_days_ago])
    
    # Stress tests linked
    stress_tests_linked = len([r for r in records if r.get("is_linked_to_stress_test", False)])
    
    # Most recent upload
    most_recent = max([r["uploaded_at"] for r in records]) if records else None
    
    return {
        "total_records": len(records),
        "total_size_mb": round(total_size_mb, 2),
        "records_by_type": records_by_type,
        "recent_uploads": recent_uploads,
        "stress_tests_linked": stress_tests_linked,
        "most_recent_upload": most_recent,
        "storage_limit_mb": STORAGE_LIMIT_MB,
        "storage_used_mb": round(total_size_mb, 2),
        "storage_percentage": round((total_size_mb / STORAGE_LIMIT_MB) * 100, 1)
    }

# Doctor appointment routes
doctor_router = APIRouter(prefix="/api/doctor", tags=["Doctor"])


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


@doctor_router.get("/appointments/{doctor_id}")
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


@doctor_router.get("/appointment/{appointment_id}/patient-tests")
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


@doctor_router.get("/appointment/{appointment_id}/shared-details")
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


@doctor_router.put("/appointment/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    update: AppointmentUpdate,
    current_user: dict = Depends(require_role(["doctor"])),
):
    """Update appointment status and notes."""
    return _update_appointment_status_impl(appointment_id, update, current_user)


@doctor_router.put("/appointment/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: str,
    update: AppointmentUpdate,
    current_user: dict = Depends(require_role(["doctor"])),
):
    """Update appointment status through the alternative status endpoint."""
    return _update_appointment_status_impl(appointment_id, update, current_user)


@doctor_router.get("/stats/{doctor_id}")
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

router.include_router(doctor_router)
router.include_router(medical_records_router)

