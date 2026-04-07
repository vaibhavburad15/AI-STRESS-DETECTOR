"""
OPTIMIZED database.py - WITH CONNECTION POOLING
Location: backend/app/database.py
Action: REPLACE your existing file with this one

KEY CHANGES:
1. Connection pooling (maxPoolSize=50)
2. Optimized timeouts
3. All indexes created properly
Result: Faster DB queries, better concurrency
"""

from typing import Any, cast

from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError
from datetime import datetime, timedelta
from bson import ObjectId
import os
from dotenv import load_dotenv

from .nmc_verification import get_verified_doctors_filter

load_dotenv()

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/aistressdetector")
client: MongoClient | None = None

# ✅ OPTIMIZED: Create client with connection pooling and timeouts
try:
    client = MongoClient(
        MONGODB_URL,
        maxPoolSize=50,  # Connection pool (handles concurrent requests)
        minPoolSize=10,  # Minimum connections kept alive
        serverSelectionTimeoutMS=5000,  # 5s timeout for server selection
        connectTimeoutMS=5000,  # 5s timeout for initial connection
        socketTimeoutMS=10000,  # 10s timeout for socket operations
        retryWrites=True,  # Retry write operations on failure
        w='majority'  # Write concern (wait for majority of replicas)
    )
    
    # Test connection
    client.admin.command('ping')
    db: Database[Any] | None = client.get_database()
    print(f"✅ Connected to MongoDB: {MONGODB_URL}")
    
except ServerSelectionTimeoutError as e:
    if client is not None:
        client.close()
        client = None
    print(f"❌ Failed to connect to MongoDB: {e}")
    print("⚠️ Starting server without database connection...")
    db = None


class _MissingCollection:
    """Fallback object used when database connection is unavailable."""

    def __init__(self, collection_name: str) -> None:
        self.collection_name = collection_name

    def __getattr__(self, method_name: str) -> Any:
        raise RuntimeError(
            f"MongoDB is unavailable; cannot call '{method_name}' on "
            f"collection '{self.collection_name}'."
        )


def close_mongo_connection() -> None:
    """Close MongoDB client gracefully on app shutdown."""
    global client
    if client is None:
        return

    try:
        client.close()
        print("MongoDB connection closed")
    except Exception as e:
        print(f"Warning: Could not close MongoDB connection cleanly: {e}")
    finally:
        client = None

# ============================================
# COLLECTIONS
# ============================================

# User collections
users_collection: Collection[dict[str, Any]] = (
    db["users"]
    if db is not None
    else cast(Collection[dict[str, Any]], _MissingCollection("users"))
)
doctors_collection: Collection[dict[str, Any]] = (
    db["doctors"]
    if db is not None
    else cast(Collection[dict[str, Any]], _MissingCollection("doctors"))
)
admin_collection: Collection[dict[str, Any]] = (
    db["admins"]
    if db is not None
    else cast(Collection[dict[str, Any]], _MissingCollection("admins"))
)

# Test and appointment collections
tests_collection: Collection[dict[str, Any]] = (
    db["tests"]
    if db is not None
    else cast(Collection[dict[str, Any]], _MissingCollection("tests"))
)
appointments_collection: Collection[dict[str, Any]] = (
    db["appointments"]
    if db is not None
    else cast(Collection[dict[str, Any]], _MissingCollection("appointments"))
)

# Enhanced recommendation tracking
progress_collection: Collection[dict[str, Any]] = (
    db["recommendation_progress"]
    if db is not None
    else cast(Collection[dict[str, Any]], _MissingCollection("recommendation_progress"))
)
achievements_collection: Collection[dict[str, Any]] = (
    db["user_achievements"]
    if db is not None
    else cast(Collection[dict[str, Any]], _MissingCollection("user_achievements"))
)

# Resource library
resources_collection: Collection[dict[str, Any]] = (
    db["resources"]
    if db is not None
    else cast(Collection[dict[str, Any]], _MissingCollection("resources"))
)
reminders_collection: Collection[dict[str, Any]] = (
    db["reminders"]
    if db is not None
    else cast(Collection[dict[str, Any]], _MissingCollection("reminders"))
)

# OTP collection (persistent with TTL)
otp_collection: Collection[dict[str, Any]] = (
    db["otps"]
    if db is not None
    else cast(Collection[dict[str, Any]], _MissingCollection("otps"))
)

# Medical Records Management
medical_records_collection: Collection[dict[str, Any]] = (
    db["medical_records"]
    if db is not None
    else cast(Collection[dict[str, Any]], _MissingCollection("medical_records"))
)
medical_record_activities_collection: Collection[dict[str, Any]] = (
    db["medical_record_activities"]
    if db is not None
    else cast(Collection[dict[str, Any]], _MissingCollection("medical_record_activities"))
)

# ============================================
# INDEXES FOR PERFORMANCE (OPTIMIZED)
# ============================================

def _ensure_unique_progress_index() -> None:
    """Upgrade the legacy progress compound index to unique when safe."""

    index_name = "user_id_1_recommendation_id_1"
    index_keys = [
        ("user_id", ASCENDING),
        ("recommendation_id", ASCENDING),
    ]
    existing_index = progress_collection.index_information().get(index_name)

    if existing_index and existing_index.get("key") == index_keys:
        if existing_index.get("unique"):
            return

        duplicate_progress = next(
            progress_collection.aggregate(
                [
                    {
                        "$group": {
                            "_id": {
                                "user_id": "$user_id",
                                "recommendation_id": "$recommendation_id",
                            },
                            "count": {"$sum": 1},
                        }
                    },
                    {"$match": {"count": {"$gt": 1}}},
                    {"$limit": 1},
                ]
            ),
            None,
        )
        if duplicate_progress is not None:
            print(
                "  ⚠ Skipping unique progress index upgrade because duplicate "
                "user/recommendation records already exist."
            )
            return

        progress_collection.drop_index(index_name)
        print("  ↺ Replaced legacy progress index with a unique constraint")

    try:
        progress_collection.create_index(
            index_keys,
            name=index_name,
            unique=True,
            background=True,
        )
    except OperationFailure as exc:
        print(f"  ⚠ Could not enforce unique progress index: {exc}")

def create_indexes():
    """Create database indexes for better query performance"""
    
    if db is None:
        print("⚠️ No database connection - skipping index creation")
        return
    
    try:
        print("🔧 Creating database indexes...")
        
        # ============================================
        # USER INDEXES
        # ============================================
        users_collection.create_index([("email", ASCENDING)], unique=True, background=True)
        users_collection.create_index([("created_at", DESCENDING)], background=True)
        users_collection.create_index([("email_verified", ASCENDING)], background=True)
        print("  ✅ User indexes created")
        
        # ============================================
        # DOCTOR INDEXES
        # ============================================
        doctors_collection.create_index([("email", ASCENDING)], unique=True, background=True)
        doctors_collection.create_index([("license_number", ASCENDING)], unique=True, background=True)
        doctors_collection.create_index([("is_verified", ASCENDING)], background=True)
        doctors_collection.create_index([("nmc_verified", ASCENDING)], background=True)
        doctors_collection.create_index([("state_medical_council", ASCENDING)], background=True)
        doctors_collection.create_index([("email_verified", ASCENDING)], background=True)
        print("  ✅ Doctor indexes created")
        
        # ============================================
        # TEST INDEXES (CRITICAL FOR PERFORMANCE)
        # ============================================
        tests_collection.create_index([("user_id", ASCENDING)], background=True)
        tests_collection.create_index([("timestamp", DESCENDING)], background=True)
        # Compound index for user's test history (MOST IMPORTANT!)
        tests_collection.create_index([
            ("user_id", ASCENDING),
            ("timestamp", DESCENDING)
        ], background=True)
        print("  ✅ Test indexes created")
        
        # ============================================
        # APPOINTMENT INDEXES (CRITICAL FOR PERFORMANCE)
        # ============================================
        appointments_collection.create_index([("user_id", ASCENDING)], background=True)
        appointments_collection.create_index([("doctor_id", ASCENDING)], background=True)
        appointments_collection.create_index([("status", ASCENDING)], background=True)
        appointments_collection.create_index([("created_at", DESCENDING)], background=True)
        # Compound indexes for common queries
        appointments_collection.create_index([
            ("doctor_id", ASCENDING),
            ("created_at", DESCENDING)
        ], background=True)
        appointments_collection.create_index([
            ("doctor_id", ASCENDING),
            ("status", ASCENDING)
        ], background=True)
        appointments_collection.create_index(
            [("slot_reservation_key", ASCENDING)],
            unique=True,
            sparse=True,
            background=True,
        )
        print("  ✅ Appointment indexes created")
        
        # ============================================
        # PROGRESS TRACKING INDEXES
        # ============================================
        _ensure_unique_progress_index()
        progress_collection.create_index([("user_id", ASCENDING)], background=True)
        progress_collection.create_index([("status", ASCENDING)], background=True)
        progress_collection.create_index([("started_at", DESCENDING)], background=True)
        progress_collection.create_index([("completed_at", DESCENDING)], background=True)
        print("  ✅ Progress tracking indexes created")
        
        # ============================================
        # ACHIEVEMENT INDEXES
        # ============================================
        achievements_collection.create_index([("user_id", ASCENDING)], unique=True, background=True)
        achievements_collection.create_index([("points", DESCENDING)], background=True)
        achievements_collection.create_index([("level", DESCENDING)], background=True)
        achievements_collection.create_index([("streak_days", DESCENDING)], background=True)
        print("  ✅ Achievement indexes created")

        # ============================================
        # OTP INDEXES
        # ============================================
        otp_collection.create_index([("email", ASCENDING)], unique=True, background=True)
        otp_collection.create_index([("created_at", DESCENDING)], background=True)
        otp_collection.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0, background=True)
        print("  ✅ OTP indexes created")
        
        # ============================================
        # MEDICAL RECORDS INDEXES (CRITICAL FOR PERFORMANCE)
        # ============================================
        medical_records_collection.create_index([("user_id", ASCENDING)], background=True)
        medical_records_collection.create_index([("record_type", ASCENDING)], background=True)
        medical_records_collection.create_index([("uploaded_at", DESCENDING)], background=True)
        medical_records_collection.create_index([("deleted", ASCENDING)], background=True)
        
        # Compound indexes for common queries
        medical_records_collection.create_index([
            ("user_id", ASCENDING),
            ("uploaded_at", DESCENDING)
        ], background=True)
        medical_records_collection.create_index([
            ("user_id", ASCENDING),
            ("record_type", ASCENDING)
        ], background=True)
        medical_records_collection.create_index([
            ("user_id", ASCENDING),
            ("deleted", ASCENDING),
            ("uploaded_at", DESCENDING)
        ], background=True)
        
        medical_records_collection.create_index([("is_linked_to_stress_test", ASCENDING)], background=True)
        medical_records_collection.create_index([("linked_test_id", ASCENDING)], background=True)
        medical_records_collection.create_index([("file_hash", ASCENDING)], background=True)
        
        # Text search index for searching
        medical_records_collection.create_index([
            ("record_name", TEXT),
            ("description", TEXT),
            ("notes", TEXT)
        ], background=True)
        print("  ✅ Medical records indexes created")
        
        # ============================================
        # ACTIVITY LOGS INDEXES
        # ============================================
        medical_record_activities_collection.create_index([("record_id", ASCENDING)], background=True)
        medical_record_activities_collection.create_index([("timestamp", DESCENDING)], background=True)
        medical_record_activities_collection.create_index([
            ("record_id", ASCENDING),
            ("timestamp", DESCENDING)
        ], background=True)
        print("  ✅ Activity log indexes created")
        
        print("✅ All database indexes created successfully!")
    except Exception as e:
        print(f"⚠️ Warning: Could not create indexes: {e}")

# ============================================
# ADMIN INITIALIZATION
# ============================================

def init_admin():
    """Initialize default admin user (password from environment variable)"""
    if db is None:
        print("⚠️ No database connection - skipping admin initialization")
        return
        
    try:
        # Import here to avoid circular import
        from .auth import get_password_hash
        
        # Check if admin already exists
        existing_admin = admin_collection.find_one({"username": "admin"})
        
        if not existing_admin:
            # ✅ CRITICAL FIX: Load admin password from environment, not hardcoded
            admin_password = os.getenv("ADMIN_PASSWORD")
            if not admin_password:
                print("⚠️ WARNING: ADMIN_PASSWORD not set in environment variables!")
                print("⚠️ Create admin with secure password by setting ADMIN_PASSWORD env var")
                return
            
            admin_collection.insert_one({
                "username": "admin",
                "email": "admin@stressanalyzer.com",
                "password": get_password_hash(admin_password),
                "role": "admin"
            })
            print("✅ Default admin created (email: admin@stressanalyzer.com)")
            print("⚠️ IMPORTANT: Change the default admin password after first login!")
        
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize admin: {e}")

# ============================================
# DATABASE HELPER FUNCTIONS
# ============================================

def get_user_by_email(email: str):
    """Get user by email from any collection"""
    if db is None:
        return None
        
    user = users_collection.find_one({"email": email})
    if user:
        user['role'] = 'user'
        return user
    
    doctor = doctors_collection.find_one({"email": email})
    if doctor:
        doctor['role'] = 'doctor'
        return doctor
    
    admin = admin_collection.find_one({"email": email})
    if admin:
        admin['role'] = 'admin'
        return admin
    
    return None

def initialize_user_achievements(user_id: str):
    """Initialize achievements for a new user"""
    if db is None:
        return
        
    existing = achievements_collection.find_one({"user_id": user_id})
    
    if not existing:
        achievements_collection.insert_one({
            "user_id": user_id,
            "badges": [],
            "total_recommendations_completed": 0,
            "total_recommendations_started": 0,
            "streak_days": 0,
            "longest_streak": 0,
            "points": 0,
            "level": 1,
            "meditation_minutes": 0,
            "exercise_minutes": 0,
            "journal_entries": 0,
            "therapist_sessions": 0,
            "last_activity_date": None
        })
        print(f"✅ Initialized achievements for user {user_id}")

def get_database_stats():
    """Get database statistics"""
    if db is None:
        return {
            "error": "No database connection",
            "total_users": 0,
            "total_doctors": 0,
            "verified_doctors": 0,
            "total_tests": 0,
            "total_appointments": 0,
            "total_achievements": 0,
            "active_progress": 0,
            "total_medical_records": 0
        }
        
    return {
        "total_users": users_collection.count_documents({}),
        "total_doctors": doctors_collection.count_documents({}),
        "verified_doctors": doctors_collection.count_documents(get_verified_doctors_filter()),
        "total_tests": tests_collection.count_documents({}),
        "total_appointments": appointments_collection.count_documents({}),
        "total_achievements": achievements_collection.count_documents({}),
        "active_progress": progress_collection.count_documents({"status": "in_progress"}),
        "total_medical_records": medical_records_collection.count_documents({"deleted": False})
    }

# ============================================
# MEDICAL RECORDS HELPER FUNCTIONS
# ============================================

def get_user_medical_records_summary(user_id: str):
    """Get summary of user's medical records"""
    if db is None:
        return None
        
    records = list(medical_records_collection.find({"user_id": user_id, "deleted": False}))
    
    total_size = sum(r.get("file_size", 0) for r in records)
    
    # Count by type
    records_by_type = {}
    for record in records:
        rtype = record.get("record_type", "other")
        records_by_type[rtype] = records_by_type.get(rtype, 0) + 1
    
    # Recent uploads (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_uploads = len([r for r in records if r["uploaded_at"] >= thirty_days_ago])
    
    return {
        "total_records": len(records),
        "total_size_mb": total_size / (1024 * 1024),
        "records_by_type": records_by_type,
        "recent_uploads": recent_uploads
    }

def link_stress_test_to_medical_record(user_id: str, test_id: str, record_name: str = "", notes: str = ""):
    """Link a stress test to medical records"""
    if db is None:
        return None
        
    # Get the stress test
    test = tests_collection.find_one({"_id": ObjectId(test_id)})
    if not test:
        return None
    
    # Create a medical record entry for the test
    test_date = test["timestamp"].strftime("%Y-%m-%d")
    default_record_name = f"Stress Test - {test_date}"
    
    record_dict = {
        "user_id": user_id,
        "record_name": record_name if record_name else default_record_name,
        "record_type": "stress_test",
        "file_name": f"stress_test_{test_id}.json",
        "file_path": "",  # No physical file
        "file_size": 0,
        "file_format": "json",
        "file_hash": "",
        "description": f"Stress Level: {test['stress_label']} (Confidence: {test['confidence_score']:.2%})",
        "record_date": test["timestamp"],
        "doctor_name": None,
        "hospital_name": None,
        "notes": notes if notes else "",
        "tags": ["stress-test", test["stress_label"].lower()],
        "uploaded_at": datetime.utcnow(),
        "updated_at": None,
        "download_count": 0,
        "is_linked_to_stress_test": True,
        "linked_test_id": test_id,
        "deleted": False,
        "stress_test_data": {
            "stress_level": test["stress_level"],
            "stress_label": test["stress_label"],
            "confidence_score": test["confidence_score"],
            "responses": test["responses"],
            "recommendations": test.get("recommendations", [])
        }
    }
    
    result = medical_records_collection.insert_one(record_dict)
    return str(result.inserted_id)

def get_user_storage_used(user_id: str) -> float:
    """Get total storage used by user in MB"""
    if db is None:
        return 0.0
        
    records = list(medical_records_collection.find({"user_id": user_id, "deleted": False}))
    total_bytes = sum(record.get("file_size", 0) for record in records)
    return total_bytes / (1024 * 1024)  # Convert to MB


# Create indexes on startup
create_indexes()

# Print database stats
print(f"📊 Database stats: {get_database_stats()}")
