"""
FIXED models.py file  
Location: backend/app/models.py
Action: REPLACE your existing backend/app/models.py with this entire file
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# ============================================
# USER MODELS
# ============================================

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    age: int = Field(..., ge=13, le=120, description="Age must be between 13 and 120")
    gender: str = Field(..., description="Gender (Male/Female/Other)")
    location: str = Field(..., min_length=2, description="City or location")
    has_previous_stress_issues: bool = Field(default=False)
    phone_number: Optional[str] = Field(None, description="SMS-enabled phone number in E.164 format e.g. +919876543210")
    
    @validator('gender')
    def validate_gender(cls, v):
        allowed = ['Male', 'Female', 'Other', 'Prefer not to say']
        if v not in allowed:
            raise ValueError(f'Gender must be one of: {", ".join(allowed)}')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    age: int
    gender: str
    location: str
    email_verified: bool
    created_at: datetime

# ============================================
# DOCTOR MODELS
# ============================================

class DoctorRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    license_number: str
    state_medical_council: str
    specialization: str
    available_slots: List[str] = []
    phone_number: Optional[str] = Field(None, description="SMS-enabled phone number in E.164 format e.g. +919876543210")

class DoctorResponse(BaseModel):
    id: str
    name: str
    email: str
    license_number: str
    state_medical_council: str
    specialization: str
    available_slots: List[str]
    is_verified: bool
    email_verified: bool
    created_at: datetime

# ============================================
# TEST MODELS
# ============================================

class TestSubmission(BaseModel):
    user_id: str
    responses: List[int]

class TestResponse(BaseModel):
    id: str
    user_id: str
    responses: List[int]
    stress_level: int
    stress_label: str
    confidence_score: float
    recommendations: List[str]
    timestamp: datetime

# ============================================
# APPOINTMENT MODELS
# ============================================

class AppointmentCreate(BaseModel):
    user_id: str
    doctor_id: str
    time_slot: str
    notes: Optional[str] = ""

class AppointmentResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    doctor_id: str
    doctor_name: str
    time_slot: str
    status: str
    notes: Optional[str]
    created_at: datetime

class AppointmentUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

# ============================================
# AUTH MODELS
# ============================================

class TokenResponse(BaseModel):
    user: dict
    message: Optional[str] = None

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")

class ResendOTPRequest(BaseModel):
    email: EmailStr

# ============================================
# ENHANCED RECOMMENDATION MODELS
# ============================================

class EnhancedRecommendation(BaseModel):
    """Enhanced recommendation with full details"""
    id: str
    category: str  # immediate/daily/weekly/lifestyle/professional
    title: str
    description: str
    action: str
    duration: str
    difficulty: str  # easy/medium/hard
    effectiveness: int  # 0-100
    icon: str
    resource_type: str  # video/audio/article/exercise/app/course/guide/tool
    resource_url: str
    priority: int
    instructions: Optional[List[str]] = None
    schedule: Optional[str] = None
    frequency: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    urgent: Optional[bool] = False

class GetEnhancedRecommendationsRequest(BaseModel):
    """Request for enhanced recommendations"""
    test_id: str
    user_id: str

class RecommendationProgressCreate(BaseModel):
    """Start tracking a recommendation"""
    user_id: str
    recommendation_id: str
    set_reminder: bool = False
    reminder_time: Optional[str] = None
    reminder_frequency: Optional[str] = "daily"

class RecommendationProgressComplete(BaseModel):
    """Mark recommendation as completed"""
    user_id: str
    recommendation_id: str
    effectiveness_rating: Optional[int] = Field(None, ge=1, le=5)  # 1-5 stars
    notes: Optional[str] = None
    minutes_spent: Optional[int] = None
    activity_type: Optional[str] = None  # meditation/exercise/journal/therapy

class RecommendationProgress(BaseModel):
    """Recommendation progress tracking"""
    id: str
    user_id: str
    recommendation_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    effectiveness_rating: Optional[int] = None
    notes: Optional[str] = None
    reminder_set: bool = False
    reminder_time: Optional[str] = None
    reminder_frequency: Optional[str] = None
    status: str  # in_progress/completed
    completion_streak: int = 0

# ============================================
# GAMIFICATION MODELS
# ============================================

class UserAchievementsResponse(BaseModel):
    """User achievements and progress"""
    user_id: str
    badges: List[str] = []
    total_recommendations_completed: int = 0
    total_recommendations_started: int = 0
    streak_days: int = 0
    longest_streak: int = 0
    points: int = 0
    level: int = 1
    level_name: str = "Beginner"
    points_to_next_level: int = 100
    meditation_minutes: int = 0
    exercise_minutes: int = 0
    journal_entries: int = 0
    therapist_sessions: int = 0
    last_activity_date: Optional[datetime] = None

class ProgressUpdate(BaseModel):
    """Update progress metrics"""
    user_id: str
    activity_type: str  # meditation/exercise/journal/therapy
    minutes: Optional[int] = None
    count: Optional[int] = None

class BadgeAward(BaseModel):
    """Badge award notification"""
    badge_name: str
    badge_description: str
    earned_at: datetime

class LevelUp(BaseModel):
    """Level up notification"""
    new_level: int
    level_name: str
    points: int

# ============================================
# RESOURCE MODELS
# ============================================

class ResourceItem(BaseModel):
    """External resource recommendation"""
    id: str
    name: str
    type: str  # app/therapy/book/course/video
    description: str
    rating: Optional[float] = None
    price: Optional[str] = None
    icon: str
    url: Optional[str] = None
    deeplink: Optional[str] = None
    recommended_for: str

class QuickWin(BaseModel):
    """Quick relief technique"""
    id: str
    title: str
    description: str
    duration: str
    icon: str
    instructions: Optional[List[str]] = None

# ============================================
# MEDICAL RECORD ENUMS (NEW)
# ============================================

class MedicalRecordType(str, Enum):
    """Types of medical records"""
    PRESCRIPTION = "prescription"
    LAB_REPORT = "lab_report"
    IMAGING = "imaging"
    DIAGNOSIS = "diagnosis"
    STRESS_TEST = "stress_test"
    THERAPY_NOTES = "therapy_notes"
    INSURANCE = "insurance"
    OTHER = "other"

class FileFormat(str, Enum):
    """Supported file formats"""
    PDF = "pdf"
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    DOC = "doc"
    DOCX = "docx"

# ============================================
# MEDICAL RECORD MODELS (NEW)
# ============================================

class MedicalRecordUpload(BaseModel):
    """Medical record upload request"""
    user_id: str
    record_name: str = Field(..., min_length=1, max_length=200)
    record_type: MedicalRecordType
    description: Optional[str] = Field(None, max_length=1000)
    record_date: Optional[str] = None  # Date of the medical record (e.g., test date)
    doctor_name: Optional[str] = None
    hospital_name: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = []

class MedicalRecordResponse(BaseModel):
    """Medical record response"""
    id: str
    user_id: str
    record_name: str
    record_type: str
    file_name: str
    file_path: str
    file_size: int
    file_format: str
    description: Optional[str]
    record_date: Optional[datetime]
    doctor_name: Optional[str]
    hospital_name: Optional[str]
    notes: Optional[str]
    tags: List[str]
    uploaded_at: datetime
    updated_at: Optional[datetime]
    download_count: int
    is_linked_to_stress_test: bool
    linked_test_id: Optional[str]

class MedicalRecordUpdate(BaseModel):
    """Update medical record metadata"""
    record_name: Optional[str] = Field(None, min_length=1, max_length=200)
    record_type: Optional[MedicalRecordType] = None
    description: Optional[str] = Field(None, max_length=1000)
    record_date: Optional[str] = None
    doctor_name: Optional[str] = None
    hospital_name: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class MedicalRecordFilter(BaseModel):
    """Filter medical records"""
    record_type: Optional[MedicalRecordType] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    search_query: Optional[str] = None
    tags: Optional[List[str]] = None

# ============================================
# TEST RESULT MODELS (NEW)
# ============================================

class TestResultAdd(BaseModel):
    """Add test result to medical record"""
    user_id: str
    stress_test_id: str  # ID of the stress test from tests_collection
    add_to_medical_records: bool = True
    record_name: Optional[str] = None  # Custom name, defaults to "Stress Test - {date}"
    notes: Optional[str] = None

class TestResultResponse(BaseModel):
    """Test result response"""
    id: str
    user_id: str
    stress_test_id: str
    medical_record_id: Optional[str]
    test_date: datetime
    stress_level: int
    stress_label: str
    confidence_score: float
    responses: List[int]
    recommendations: List[str]
    notes: Optional[str]
    created_at: datetime

# ============================================
# DOWNLOAD MODELS (NEW)
# ============================================

class DownloadRequest(BaseModel):
    """Request to download a medical record"""
    user_id: str
    record_id: str

class DownloadResponse(BaseModel):
    """Download response with secure URL"""
    record_id: str
    record_name: str
    download_url: str
    expires_at: datetime
    file_size: int
    file_format: str

class BulkDownloadRequest(BaseModel):
    """Request to download multiple records as ZIP"""
    user_id: str
    record_ids: List[str] = Field(..., min_length=1, max_length=50)  # Fixed: removed min_items

# ============================================
# ANALYTICS MODELS (NEW)
# ============================================

class MedicalRecordStats(BaseModel):
    """Medical records statistics"""
    total_records: int
    total_size_mb: float
    records_by_type: dict
    recent_uploads: int  # Last 30 days
    stress_tests_linked: int
    most_recent_upload: Optional[datetime]
    storage_limit_mb: float
    storage_used_mb: float
    storage_percentage: float

class RecordActivity(BaseModel):
    """Record activity log"""
    record_id: str
    action: str  # uploaded/downloaded/updated/deleted/linked
    timestamp: datetime
    details: Optional[str]
