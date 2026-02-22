from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from typing import List
from ..database import users_collection, doctors_collection, tests_collection, appointments_collection
from ..auth import require_role
from ..nmc_verification import build_nmc_profile

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.get("/stats")
async def get_admin_stats(current_user: dict = Depends(require_role(["admin"]))):
    """Get comprehensive admin statistics"""
    
    # Count totals
    total_users = users_collection.count_documents({})
    total_doctors = doctors_collection.count_documents({})
    verified_doctors = doctors_collection.count_documents({"is_verified": True})
    unverified_doctors = doctors_collection.count_documents({"is_verified": False})
    total_tests = tests_collection.count_documents({})
    total_appointments = appointments_collection.count_documents({})
    
    # Appointment status breakdown
    pending_appointments = appointments_collection.count_documents({"status": "pending"})
    approved_appointments = appointments_collection.count_documents({"status": "approved"})
    completed_appointments = appointments_collection.count_documents({"status": "completed"})
    rejected_appointments = appointments_collection.count_documents({"status": "rejected"})
    
    # Stress level distribution
    stress_distribution = {
        "low": tests_collection.count_documents({"stress_level": 0}),
        "moderate": tests_collection.count_documents({"stress_level": 1}),
        "high": tests_collection.count_documents({"stress_level": 2}),
        "severe": tests_collection.count_documents({"stress_level": 3})
    }
    
    # Recent activity
    recent_users = list(users_collection.find().sort("created_at", -1).limit(5))
    recent_tests = list(tests_collection.find().sort("timestamp", -1).limit(10))
    
    return {
        "overview": {
            "total_users": total_users,
            "total_doctors": total_doctors,
            "verified_doctors": verified_doctors,
            "unverified_doctors": unverified_doctors,
            "total_tests": total_tests,
            "total_appointments": total_appointments
        },
        "appointments": {
            "pending": pending_appointments,
            "approved": approved_appointments,
            "completed": completed_appointments,
            "rejected": rejected_appointments
        },
        "stress_distribution": stress_distribution,
        "recent_users_count": len(recent_users),
        "recent_tests_count": len(recent_tests)
    }

@router.get("/users")
async def get_all_users(current_user: dict = Depends(require_role(["admin"]))):
    """Get all users with their test history"""
    users = list(users_collection.find())
    
    detailed_users = []
    for user in users:
        test_count = tests_collection.count_documents({"user_id": str(user["_id"])})
        appointment_count = appointments_collection.count_documents({"user_id": str(user["_id"])})
        
        # Get latest test
        latest_test = tests_collection.find_one(
            {"user_id": str(user["_id"])},
            sort=[("timestamp", -1)]
        )
        
        latest_stress = None
        if latest_test:
            latest_stress = {
                "level": latest_test["stress_level"],
                "label": latest_test["stress_label"],
                "date": latest_test["timestamp"]
            }
        
        detailed_users.append({
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "created_at": user["created_at"],
            "test_count": test_count,
            "appointment_count": appointment_count,
            "latest_stress": latest_stress
        })
    
    return detailed_users

@router.get("/doctors")
async def get_all_doctors(current_user: dict = Depends(require_role(["admin"]))):
    """Get all doctors with verification status"""
    doctors = list(doctors_collection.find())
    
    detailed_doctors = []
    for doctor in doctors:
        appointment_count = appointments_collection.count_documents({"doctor_id": str(doctor["_id"])})
        
        detailed_doctors.append({
            "id": str(doctor["_id"]),
            "name": doctor["name"],
            "email": doctor["email"],
            "license_number": doctor["license_number"],
            "state_medical_council": doctor.get("state_medical_council"),
            "specialization": doctor["specialization"],
            "is_verified": doctor.get("is_verified", False),
            "nmc_verified": doctor.get("nmc_verified", bool(doctor.get("nmc_verification"))),
            "nmc_profile": doctor.get("nmc_profile") or build_nmc_profile(doctor.get("nmc_verification")),
            "nmc_verification": doctor.get("nmc_verification"),
            "available_slots": doctor.get("available_slots", []),
            "created_at": doctor["created_at"],
            "appointment_count": appointment_count
        })
    
    return detailed_doctors

@router.put("/doctor/{doctor_id}/verify")
async def verify_doctor(doctor_id: str, verified: bool, current_user: dict = Depends(require_role(["admin"]))):
    """Verify or unverify a doctor"""
    doctor = doctors_collection.find_one({"_id": ObjectId(doctor_id)})
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    doctors_collection.update_one(
        {"_id": ObjectId(doctor_id)},
        {"$set": {"is_verified": verified}}
    )
    
    return {"message": f"Doctor {'verified' if verified else 'unverified'} successfully"}

@router.get("/appointments")
async def get_all_appointments(current_user: dict = Depends(require_role(["admin"]))):
    """Get all appointments"""
    appointments = list(appointments_collection.find().sort("created_at", -1))
    
    return [
        {
            "id": str(apt["_id"]),
            "user_name": apt["user_name"],
            "user_email": apt["user_email"],
            "doctor_name": apt["doctor_name"],
            "time_slot": apt["time_slot"],
            "status": apt["status"],
            "created_at": apt["created_at"]
        }
        for apt in appointments
    ]

@router.get("/tests/recent")
async def get_recent_tests(limit: int = 20, current_user: dict = Depends(require_role(["admin"]))):
    """Get recent tests with user information"""
    tests = list(tests_collection.find().sort("timestamp", -1).limit(limit))
    
    detailed_tests = []
    for test in tests:
        user = users_collection.find_one({"_id": ObjectId(test["user_id"])})
        
        detailed_tests.append({
            "id": str(test["_id"]),
            "user_name": user["name"] if user else "Unknown",
            "user_email": user["email"] if user else "Unknown",
            "stress_level": test["stress_level"],
            "stress_label": test["stress_label"],
            "confidence_score": test["confidence_score"],
            "timestamp": test["timestamp"]
        })
    
    return detailed_tests

@router.delete("/user/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(require_role(["admin"]))):
    """Delete a user and their associated data"""
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete user's tests
    tests_collection.delete_many({"user_id": user_id})
    
    # Delete user's appointments
    appointments_collection.delete_many({"user_id": user_id})
    
    # Delete user
    users_collection.delete_one({"_id": ObjectId(user_id)})
    
    return {"message": "User and associated data deleted successfully"}

@router.delete("/doctor/{doctor_id}")
async def delete_doctor(doctor_id: str, current_user: dict = Depends(require_role(["admin"]))):
    """Delete a doctor and their associated appointments"""
    doctor = doctors_collection.find_one({"_id": ObjectId(doctor_id)})
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Delete doctor's appointments
    appointments_collection.delete_many({"doctor_id": doctor_id})
    
    # Delete doctor
    doctors_collection.delete_one({"_id": ObjectId(doctor_id)})
    
    return {"message": "Doctor and associated appointments deleted successfully"}
