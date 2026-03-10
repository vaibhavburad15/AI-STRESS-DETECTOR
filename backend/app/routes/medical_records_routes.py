"""
COMPLETE FIXED medical_records_routes.py
Location: backend/app/routes/medical_records_routes.py
Action: REPLACE your existing file with this entire content
ALL PYLANCE ERRORS FIXED ✅
"""

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional, Any
import os
import shutil
import hashlib
import mimetypes
from pathlib import Path
import zipfile
import io

from ..models import (
    MedicalRecordUpload, MedicalRecordResponse, MedicalRecordUpdate,
    MedicalRecordFilter, TestResultAdd, DownloadRequest, 
    BulkDownloadRequest, MedicalRecordStats
)
from ..database import (
    users_collection, tests_collection, medical_records_collection,
    medical_record_activities_collection
)
from ..auth import require_role

router = APIRouter(prefix="/api/medical-records", tags=["Medical Records"])

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

@router.post("/upload", response_model=MedicalRecordResponse)
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
    
    # Verify user
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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
    safe_filename = f"{user_id}_{timestamp}_{hashlib.md5(filename_for_hash.encode()).hexdigest()[:8]}{file_ext}"
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
        except:
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]
    
    # Parse record date
    parsed_record_date = None
    if record_date:
        try:
            parsed_record_date = datetime.fromisoformat(record_date.replace('Z', '+00:00'))
        except:
            pass
    
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

@router.get("/user/{user_id}", response_model=List[MedicalRecordResponse])
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

@router.get("/{record_id}", response_model=MedicalRecordResponse)
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

@router.put("/{record_id}", response_model=MedicalRecordResponse)
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
        except:
            pass
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

@router.delete("/{record_id}")
async def delete_medical_record(
    record_id: str,
    permanent: bool = False,
    current_user: dict = Depends(require_role(["user"]))
):
    """Delete a medical record (soft delete by default)"""
    
    record = medical_records_collection.find_one({"_id": ObjectId(record_id)})
    
    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")
    
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
    recs: list = list(stress_data.get("recommendations") or [])
    if recs:
        story += [
            Spacer(1, 0.3*cm),
            Paragraph("Personalized Recommendations",
                       ps("rh", fontName="Helvetica-Bold", fontSize=13,
                          textColor=colors.HexColor("#1e3a8a"), spaceAfter=6)),
        ]
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


@router.get("/download/{record_id}")
async def download_medical_record(
    record_id: str,
    current_user: dict = Depends(require_role(["user", "doctor"]))
):
    """Download a medical record file (auto-generates PDF for stress test records)"""

    record = medical_records_collection.find_one({"_id": ObjectId(record_id), "deleted": False})

    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")

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

@router.post("/download/bulk")
async def download_bulk_medical_records(
    request: BulkDownloadRequest,
    current_user: dict = Depends(require_role(["user"]))
):
    """Download multiple medical records as a ZIP file"""
    
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

@router.post("/link-stress-test")
async def link_stress_test_to_medical_record(
    test_add: TestResultAdd,
    current_user: dict = Depends(require_role(["user"]))
):
    """Add a stress test to medical records"""
    
    # Get stress test
    stress_test = tests_collection.find_one({"_id": ObjectId(test_add.stress_test_id)})
    
    if not stress_test:
        raise HTTPException(status_code=404, detail="Stress test not found")
    
    if not test_add.add_to_medical_records:
        return {"message": "Test not added to medical records"}
    
    # Generate record name
    test_date = stress_test["timestamp"].strftime("%Y-%m-%d")
    record_name = test_add.record_name or f"Stress Test - {test_date}"
    
    # Create medical record entry
    record_dict = {
        "user_id": test_add.user_id,
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
            "recommendations": stress_test.get("recommendations", [])
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

@router.get("/stats/{user_id}", response_model=MedicalRecordStats)
async def get_medical_records_stats(
    user_id: str,
    current_user: dict = Depends(require_role(["user"]))
):
    """Get medical records statistics for a user"""
    
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