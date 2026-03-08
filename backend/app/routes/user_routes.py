from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from datetime import datetime
from typing import List
from ..models import (
    TestSubmission, TestResponse, AppointmentCreate, AppointmentResponse,
    GetEnhancedRecommendationsRequest, RecommendationProgressCreate,
    RecommendationProgressComplete, UserAchievementsResponse, ProgressUpdate,
    ChatbotMessage, ChatbotResponse
)
from ..database import (
    users_collection, tests_collection, appointments_collection, doctors_collection,
    achievements_collection, progress_collection
)
from ..auth import require_role
from ml_model.predictor import predictor
from ..recommendation_engine import enhanced_engine
from ..progress_tracker import ProgressTracker
from ..email_service import email_service
from ..sms_service import sms_service
from ..nmc_verification import build_nmc_profile
import logging
import groq
import os
router = APIRouter(prefix="/api/user", tags=["User"])

# Initialize progress tracker
tracker = ProgressTracker(progress_collection)
logger = logging.getLogger(__name__)

DEFAULT_GROQ_CHAT_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant"
]


def _groq_model_candidates() -> List[str]:
    """Build an ordered, de-duplicated list of Groq models to try."""
    configured_primary = os.getenv("GROQ_CHAT_MODEL", "").strip()
    configured_fallbacks = [
        model.strip()
        for model in os.getenv("GROQ_CHAT_FALLBACK_MODELS", "").split(",")
        if model.strip()
    ]

    candidates: List[str] = []
    for model_name in [configured_primary, *configured_fallbacks, *DEFAULT_GROQ_CHAT_MODELS]:
        if model_name and model_name not in candidates:
            candidates.append(model_name)
    return candidates

# ============================================
# QUESTIONNAIRE
# ============================================

QUESTIONNAIRE = [
    {"id": 1, "question": "How often do you feel nervous or anxious?", "category": "emotional"},
    {"id": 2, "question": "How often do you feel sad or depressed?", "category": "emotional"},
    {"id": 3, "question": "How often do you feel irritable or angry?", "category": "emotional"},
    {"id": 4, "question": "How often do you experience headaches or body pain?", "category": "physical"},
    {"id": 5, "question": "How often do you feel physically fatigued or exhausted?", "category": "physical"},
    {"id": 6, "question": "How often do you have trouble falling or staying asleep?", "category": "physical"},
    {"id": 7, "question": "How often do you experience rapid heartbeat or chest tightness?", "category": "physical"},
    {"id": 8, "question": "How often do you have difficulty concentrating?", "category": "cognitive"},
    {"id": 9, "question": "How often do you have negative or intrusive thoughts?", "category": "cognitive"},
    {"id": 10, "question": "How often do you worry excessively about the future?", "category": "cognitive"},
    {"id": 11, "question": "How often do you have difficulty making decisions?", "category": "cognitive"},
    {"id": 12, "question": "How often have you experienced changes in appetite?", "category": "behavioral"},
    {"id": 13, "question": "How often do you avoid social interactions?", "category": "behavioral"},
    {"id": 14, "question": "How often do you feel overwhelmed by daily tasks?", "category": "behavioral"},
    {"id": 15, "question": "How satisfied are you with your work-life balance?", "category": "stressors"},
    {"id": 16, "question": "How much stress do you experience from work or studies?", "category": "stressors"},
    {"id": 17, "question": "How much stress do you experience from relationships?", "category": "stressors"},
    {"id": 18, "question": "How much stress do you experience from financial concerns?", "category": "stressors"}
]

@router.get("/questionnaire")
async def get_questionnaire():
    """Get the CBT-based stress assessment questionnaire"""
    return {
        "questions": QUESTIONNAIRE,
        "instructions": "Please answer each question on a scale of 1-5:",
        "scale": {
            "1": "Never/Not at all",
            "2": "Rarely/Slightly",
            "3": "Sometimes/Moderately",
            "4": "Often/Very",
            "5": "Always/Extremely"
        }
    }

# ============================================
# STRESS TEST ENDPOINTS (ORIGINAL)
# ============================================

@router.post("/test/submit", response_model=TestResponse)
async def submit_test(test: TestSubmission, current_user: dict = Depends(require_role(["user"]))):
    """Submit stress test and get ML-based prediction"""
    # Validate responses
    if len(test.responses) != 18:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expected 18 responses"
        )
    
    if not all(1 <= r <= 5 for r in test.responses):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All responses must be between 1 and 5"
        )
    
    # Get ML prediction
    try:
        stress_level, stress_label, confidence, recommendations = predictor.predict(test.responses)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction error: {str(e)}"
        )
    
    # Save test result
    test_dict = {
        "user_id": test.user_id,
        "responses": test.responses,
        "stress_level": int(stress_level),
        "stress_label": stress_label,
        "confidence_score": confidence,
        "recommendations": recommendations,
        "timestamp": datetime.utcnow()
    }
    
    result = tests_collection.insert_one(test_dict)
    test_id = str(result.inserted_id)
    
    # Update user's test history
    users_collection.update_one(
        {"_id": ObjectId(test.user_id)},
        {"$push": {"test_history": test_id}}
    )
    
    # ✅ SEND SMS STRESS RESULT
    try:
        submitting_user = users_collection.find_one({"_id": ObjectId(test.user_id)})
        if submitting_user and submitting_user.get("phone_number"):
            sms_service.send_stress_result_sms(
                phone=submitting_user["phone_number"],
                user_name=submitting_user["name"],
                stress_label=stress_label,
                confidence=confidence,
                top_recommendations=recommendations[:3] if recommendations else []
            )
    except Exception as e:
        print(f"⚠️ Failed to send stress result SMS: {e}")

    return {
        "id": test_id,
        "user_id": test.user_id,
        "responses": test.responses,
        "stress_level": int(stress_level),
        "stress_label": stress_label,
        "confidence_score": confidence,
        "recommendations": recommendations,
        "timestamp": test_dict["timestamp"]
    }

@router.get("/test/history/{user_id}")
async def get_test_history(user_id: str, current_user: dict = Depends(require_role(["user", "admin"]))):
    """Get user's test history"""
    tests = list(tests_collection.find({"user_id": user_id}).sort("timestamp", -1))
    
    return [
        {
            "id": str(test["_id"]),
            "stress_level": test["stress_level"],
            "stress_label": test["stress_label"],
            "confidence_score": test["confidence_score"],
            "timestamp": test["timestamp"]
        }
        for test in tests
    ]

@router.get("/test/{test_id}")
async def get_test_details(test_id: str, current_user: dict = Depends(require_role(["user", "doctor", "admin"]))):
    """Get detailed test results"""
    test = tests_collection.find_one({"_id": ObjectId(test_id)})
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return {
        "id": str(test["_id"]),
        "user_id": test["user_id"],
        "responses": test["responses"],
        "stress_level": test["stress_level"],
        "stress_label": test["stress_label"],
        "confidence_score": test["confidence_score"],
        "recommendations": test["recommendations"],
        "timestamp": test["timestamp"],
        "questions": QUESTIONNAIRE
    }

# ============================================
# ENHANCED RECOMMENDATIONS ENDPOINTS (NEW)
# ============================================

@router.post("/recommendations/enhanced")
async def get_enhanced_recommendations(
    test_id: str,
    current_user: dict = Depends(require_role(["user"]))
):
    """Get enhanced, personalized recommendations based on test results"""
    user_id = current_user.get('user_id') or current_user.get('id')
    
    # Get user data
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get test result
    test = tests_collection.find_one({"_id": ObjectId(test_id)})
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Get test history for trend analysis
    test_history = list(tests_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(10))
    
    # Generate enhanced recommendations
    try:
        recommendations = enhanced_engine.generate_personalized_recommendations(
            user_data={
                "age": user.get("age"),
                "gender": user.get("gender"),
                "location": user.get("location"),
                "name": user.get("name"),
                "previous_stress_issues": user.get("has_previous_stress_issues", False),
                "test_history": [
                    {
                        "stress_level": t["stress_level"],
                        "timestamp": t["timestamp"]
                    }
                    for t in test_history
                ]
            },
            stress_result={
                "stress_level": test["stress_level"],
                "stress_label": test["stress_label"],
                "responses": test.get("responses", []),
                "confidence_score": test["confidence_score"]
            }
        )
        
        return recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )

@router.post("/recommendations/start")
async def start_recommendation(
    progress: RecommendationProgressCreate,
    current_user: dict = Depends(require_role(["user"]))
):
    """Mark a recommendation as started"""
    try:
        result = tracker.mark_started(
            user_id=progress.user_id,
            recommendation_id=progress.recommendation_id,
            set_reminder=progress.set_reminder,
            reminder_time=progress.reminder_time,
            reminder_frequency=progress.reminder_frequency
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start recommendation: {str(e)}"
        )

@router.post("/recommendations/complete")
async def complete_recommendation(
    progress: RecommendationProgressComplete,
    current_user: dict = Depends(require_role(["user"]))
):
    """Mark a recommendation as completed and award points/badges"""
    try:
        result = tracker.mark_completed(
            user_id=progress.user_id,
            recommendation_id=progress.recommendation_id,
            effectiveness_rating=progress.effectiveness_rating,
            notes=progress.notes,
            minutes_spent=progress.minutes_spent,
            activity_type=progress.activity_type
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete recommendation: {str(e)}"
        )

@router.delete("/recommendations/{user_id}/{recommendation_id}")
async def dismiss_recommendation(
    user_id: str,
    recommendation_id: str,
    current_user: dict = Depends(require_role(["user"]))
):
    """Dismiss a recommendation as not helpful"""
    try:
        progress_collection.update_one(
            {"user_id": user_id, "recommendation_id": recommendation_id},
            {"$set": {"status": "dismissed", "dismissed_at": datetime.utcnow()}}
        )
        return {"message": "Recommendation dismissed"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dismiss recommendation: {str(e)}"
        )

@router.post("/recommendations/save")
async def save_for_later(
    user_id: str,
    recommendation_id: str,
    current_user: dict = Depends(require_role(["user"]))
):
    """Save a recommendation for later"""
    try:
        progress_collection.update_one(
            {"user_id": user_id, "recommendation_id": recommendation_id},
            {"$set": {"saved_for_later": True, "saved_at": datetime.utcnow()}},
            upsert=True
        )
        return {"message": "Recommendation saved for later"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save recommendation: {str(e)}"
        )

# ============================================
# GAMIFICATION & ACHIEVEMENTS ENDPOINTS (NEW)
# ============================================

@router.get("/achievements/{user_id}")
async def get_achievements(
    user_id: str,
    current_user: dict = Depends(require_role(["user"]))
):
    """Get user achievements, badges, points, and level"""
    try:
        # Get or create achievements
        achievements = achievements_collection.find_one({"user_id": user_id})
        
        if not achievements:
            # Initialize new achievements
            achievements = {
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
            }
            achievements_collection.insert_one(achievements)
        
        # Calculate level info
        level = tracker.calculate_level(achievements.get("points", 0))
        level_name = tracker.get_level_name(level)
        points_to_next = tracker.points_to_next_level(achievements.get("points", 0))
        
        return {
            "user_id": user_id,
            "badges": achievements.get("badges", []),
            "total_recommendations_completed": achievements.get("total_recommendations_completed", 0),
            "total_recommendations_started": achievements.get("total_recommendations_started", 0),
            "streak_days": achievements.get("streak_days", 0),
            "longest_streak": achievements.get("longest_streak", 0),
            "points": achievements.get("points", 0),
            "level": level,
            "level_name": level_name,
            "points_to_next_level": points_to_next,
            "meditation_minutes": achievements.get("meditation_minutes", 0),
            "exercise_minutes": achievements.get("exercise_minutes", 0),
            "journal_entries": achievements.get("journal_entries", 0),
            "therapist_sessions": achievements.get("therapist_sessions", 0),
            "last_activity_date": achievements.get("last_activity_date")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get achievements: {str(e)}"
        )

@router.get("/progress/{user_id}")
async def get_user_progress(
    user_id: str,
    current_user: dict = Depends(require_role(["user"]))
):
    """Get user's recommendation progress"""
    try:
        progress_items = list(progress_collection.find({"user_id": user_id}))
        
        return {
            "total_started": len([p for p in progress_items if p.get("status") == "in_progress"]),
            "total_completed": len([p for p in progress_items if p.get("status") == "completed"]),
            "saved_for_later": len([p for p in progress_items if p.get("saved_for_later", False)]),
            "items": [
                {
                    "recommendation_id": p["recommendation_id"],
                    "started_at": p.get("started_at"),
                    "completed_at": p.get("completed_at"),
                    "status": p.get("status"),
                    "effectiveness_rating": p.get("effectiveness_rating"),
                    "notes": p.get("notes"),
                    "saved_for_later": p.get("saved_for_later", False)
                }
                for p in progress_items
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get progress: {str(e)}"
        )

@router.get("/leaderboard")
async def get_leaderboard(
    limit: int = 10,
    current_user: dict = Depends(require_role(["user"]))
):
    """Get top users by points (optional feature)"""
    try:
        top_users = list(
            achievements_collection.find()
            .sort("points", -1)
            .limit(limit)
        )
        
        leaderboard = []
        for idx, achievement in enumerate(top_users, 1):
            user = users_collection.find_one({"_id": ObjectId(achievement["user_id"])})
            if user:
                leaderboard.append({
                    "rank": idx,
                    "name": user.get("name", "Anonymous"),
                    "points": achievement.get("points", 0),
                    "level": tracker.calculate_level(achievement.get("points", 0)),
                    "badges": len(achievement.get("badges", []))
                })
        
        return {"leaderboard": leaderboard}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get leaderboard: {str(e)}"
        )

# ============================================
# DOCTOR & APPOINTMENT ENDPOINTS (ORIGINAL)
# ============================================

@router.get("/doctors")
async def get_doctors(current_user: dict = Depends(require_role(["user"]))):
    """Get list of admin-approved doctors with full NMC profile"""
    doctors = list(doctors_collection.find({"is_verified": True}))
    
    return [
        {
            "id": str(doctor["_id"]),
            "name": doctor["name"],
            "email": doctor.get("email"),
            "license_number": doctor.get("license_number"),
            "state_medical_council": doctor.get("state_medical_council"),
            "specialization": doctor["specialization"],
            "available_slots": doctor.get("available_slots", []),
            "is_verified": doctor.get("is_verified", False),
            "nmc_verified": doctor.get("nmc_verified", bool(doctor.get("nmc_verification"))),
            "nmc_profile": doctor.get("nmc_profile") or build_nmc_profile(doctor.get("nmc_verification")),
        }
        for doctor in doctors
    ]

@router.get("/appointments/{user_id}")
async def get_user_appointments(user_id: str, current_user: dict = Depends(require_role(["user"]))):
    """Get user's appointments"""
    appointments = list(appointments_collection.find({"user_id": user_id}).sort("created_at", -1))
    
    return [
        {
            "id": str(apt["_id"]),
            "doctor_id": apt["doctor_id"],
            "doctor_name": apt["doctor_name"],
            "time_slot": apt["time_slot"],
            "status": apt["status"],
            "notes": apt.get("notes", ""),
            "doctor_notes": apt.get("doctor_notes", ""),
            "created_at": apt["created_at"],
            "updated_at": apt.get("updated_at")
        }
        for apt in appointments
    ]

@router.post("/appointment/book", response_model=AppointmentResponse)
async def book_appointment(appointment: AppointmentCreate, current_user: dict = Depends(require_role(["user"]))):
    """Book an appointment with a doctor"""
    # Verify doctor exists and is verified
    doctor = doctors_collection.find_one({"_id": ObjectId(appointment.doctor_id)})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    if not doctor.get("is_verified", False):
        raise HTTPException(status_code=400, detail="Doctor is not verified")
    
    # Verify time slot is available
    if appointment.time_slot not in doctor.get("available_slots", []):
        raise HTTPException(status_code=400, detail="Time slot not available")
    
    # Get user info
    user = users_collection.find_one({"_id": ObjectId(appointment.user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create appointment
    appointment_dict = {
        "user_id": appointment.user_id,
        "user_name": user["name"],
        "user_email": user["email"],
        "doctor_id": appointment.doctor_id,
        "doctor_name": doctor["name"],
        "time_slot": appointment.time_slot,
        "status": "pending",
        "notes": appointment.notes,
        "created_at": datetime.utcnow()
    }
    
    result = appointments_collection.insert_one(appointment_dict)
    appointment_id = str(result.inserted_id)
    
    # ✅ SEND EMAIL + SMS TO USER
    try:
        email_service.send_appointment_booked_email(
            user_email=user["email"],
            user_name=user["name"],
            doctor_name=doctor["name"],
            appointment_time=appointment.time_slot,
            notes=appointment.notes or ""
        )
        print(f"✅ Appointment booking email sent to {user['email']}")
    except Exception as e:
        print(f"⚠️ Failed to send booking email: {e}")

    try:
        if user.get("phone_number"):
            sms_service.send_appointment_booked_sms(
                phone=user["phone_number"],
                user_name=user["name"],
                doctor_name=doctor["name"],
                appointment_time=appointment.time_slot,
                notes=appointment.notes or ""
            )
    except Exception as e:
        print(f"⚠️ Failed to send booking SMS: {e}")
        # Don't fail the request if SMS fails
    
    return {
        "id": appointment_id,
        "user_id": appointment.user_id,
        "user_name": user["name"],
        "doctor_id": appointment.doctor_id,
        "doctor_name": doctor["name"],
        "time_slot": appointment.time_slot,
        "status": "pending",
        "notes": appointment.notes,
        "created_at": appointment_dict["created_at"]
    }

# ============================================
# CHATBOT
# ============================================

@router.post("/chatbot/chat", response_model=ChatbotResponse)
async def chatbot_chat(chat_request: ChatbotMessage, current_user: dict = Depends(require_role(["user"]))):
    """Chat with AI stress counselor that auto-detects stress levels"""
    try:
        # Initialize Groq client
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY environment variable not set")
        
        client = groq.Groq(api_key=api_key)
        
        # Always use the authenticated user id from the header.
        # Ignore the body user_id to prevent cross-user data access.
        user_id = current_user["user_id"]

        # Get user's recent test history for context
        recent_tests = list(tests_collection.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(3))
        
        context = ""
        if recent_tests:
            latest_test = recent_tests[0]
            context = f"User's latest stress assessment: {latest_test.get('stress_label', 'Unknown')} stress level (score: {latest_test.get('stress_level', 'N/A')}) from {latest_test.get('timestamp', 'recently')}."
        
        # Prompt for Groq
        system_prompt = f"""You are a compassionate AI stress counselor. Help users manage their stress through CBT principles and supportive conversation.

{context}

Guidelines:
- Be empathetic and supportive
- Use CBT techniques when appropriate
- Suggest practical coping strategies
- Encourage professional help for severe stress
- Keep responses conversational but helpful

After your response, provide a stress level assessment in this exact format:
STRESS_LEVEL: [0-3] (0=Low, 1=Moderate, 2=High, 3=Severe)
CONFIDENCE: [0.0-1.0]"""

        # Call Groq API with model fallback (to handle model deprecations cleanly)
        chat_completion = None
        provider_error = None
        for model_name in _groq_model_candidates():
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": chat_request.message}
                    ],
                    model=model_name,
                    temperature=0.7,
                    max_tokens=1000
                )
                break
            except Exception as model_error:
                provider_error = model_error
                logger.warning(f"Groq model attempt failed for {model_name}: {model_error}")

        if chat_completion is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "No available Groq model for chatbot. "
                    "Set GROQ_CHAT_MODEL to an active model."
                )
            ) from provider_error
        
        full_response = (chat_completion.choices[0].message.content or "").strip()
        
        # Parse the response
        response_part = full_response
        stress_level = None
        stress_label = None
        confidence = None
        
        # Look for stress level markers in the response
        response_lower = full_response.lower()
        
        # Extract stress level
        if "stress_level:" in response_lower:
            try:
                level_text = full_response.split("STRESS_LEVEL:")[1].split()[0].strip()
                stress_level = int(level_text)
                # Map level to label
                labels = {0: "Low", 1: "Moderate", 2: "High", 3: "Severe"}
                stress_label = labels.get(stress_level, "Unknown")
            except:
                pass
        
        # Extract confidence
        if "confidence:" in response_lower:
            try:
                conf_text = full_response.split("CONFIDENCE:")[1].split()[0].strip()
                confidence = float(conf_text)
            except:
                pass
        
        # Remove the stress assessment markers from the response
        if "STRESS_LEVEL:" in full_response:
            response_part = full_response.split("STRESS_LEVEL:")[0].strip()
        if "CONFIDENCE:" in response_part:
            response_part = response_part.split("CONFIDENCE:")[0].strip()
        
        return ChatbotResponse(
            response=response_part,
            detected_stress_level=stress_level,
            detected_stress_label=stress_label,
            confidence=confidence
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected chatbot error for user_id={current_user.get('user_id')}")
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}")
