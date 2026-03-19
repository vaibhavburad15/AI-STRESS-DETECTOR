from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import json as _json
import re as _re
from pydantic import BaseModel
from ..models import (
    TestSubmission, TestResponse, AppointmentCreate, AppointmentResponse,
    GetEnhancedRecommendationsRequest, RecommendationProgressCreate,
    RecommendationProgressComplete, UserAchievementsResponse, ProgressUpdate,
    ChatbotMessage, ChatbotResponse, ProfileUpdate, AppointmentShareUpdate
)
from ..database import (
    users_collection, tests_collection, appointments_collection, doctors_collection,
    achievements_collection, progress_collection
)
from ..appointment_access import (
    add_access_state,
    format_slot_window,
    parse_time_slot_window,
    require_doctor_user_access,
)
from ..auth import require_role
from ml_model.predictor import predictor
from ml_model.verbal_nn_scorer import verbal_nn_scorer
from ml_model.multimodal_pipeline import multimodal_pipeline
from ..recommendation_engine import enhanced_engine
from ..progress_tracker import ProgressTracker
from ..email_service import email_service
from ..sms_service import sms_service
from ..nmc_verification import build_nmc_profile
from ..report_generator import report_generator
from ..analytics_engine import create_analytics_engine
import logging
import groq
import os
router = APIRouter(prefix="/api/user", tags=["User"])

# Initialize progress tracker
tracker = ProgressTracker(progress_collection)
logger = logging.getLogger(__name__)

# Initialize analytics engine
analytics = create_analytics_engine(tests_collection, users_collection, appointments_collection, doctors_collection)

# ============================================
# USER PROFILE
# ============================================

@router.get("/profile/{user_id}")
async def get_profile(user_id: str, current_user: dict = Depends(require_role(["user", "doctor", "admin"]))):
    """Get user profile by ID"""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if current_user["role"] == "user" and current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this profile")
    if current_user["role"] == "doctor":
        require_doctor_user_access(current_user, user_id)

    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user["_id"]),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "age": user.get("age", 0),
        "gender": user.get("gender", ""),
        "location": user.get("location", ""),
        "has_previous_stress_issues": user.get("has_previous_stress_issues", False),
        "created_at": user.get("created_at", ""),
        "is_email_verified": user.get("email_verified", False),
    }


@router.put("/profile/{user_id}")
async def update_profile(
    user_id: str,
    data: ProfileUpdate,
    current_user: dict = Depends(require_role(["user", "admin"])),
):
    """Update user profile"""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if current_user["role"] != "admin" and current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this profile")

    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_fields = {}
    if data.name is not None:
        update_fields["name"] = data.name.strip()
    if data.age is not None:
        update_fields["age"] = data.age
    if data.gender is not None:
        if data.gender not in ["Male", "Female", "Other", "Prefer not to say"]:
            raise HTTPException(status_code=400, detail="Invalid gender value")
        update_fields["gender"] = data.gender
    if data.location is not None:
        update_fields["location"] = data.location.strip()
    if data.has_previous_stress_issues is not None:
        update_fields["has_previous_stress_issues"] = data.has_previous_stress_issues

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_fields["updated_at"] = datetime.utcnow()
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_fields}
    )

    updated = users_collection.find_one({"_id": ObjectId(user_id)})
    if not updated:
        raise HTTPException(status_code=404, detail="User not found after update")
    return {
        "id": str(updated["_id"]),
        "name": updated.get("name", ""),
        "email": updated.get("email", ""),
        "age": updated.get("age", 0),
        "gender": updated.get("gender", ""),
        "location": updated.get("location", ""),
        "has_previous_stress_issues": updated.get("has_previous_stress_issues", False),
        "created_at": updated.get("created_at", ""),
        "is_email_verified": updated.get("email_verified", False),
    }

DEFAULT_GROQ_CHAT_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant"
]


def _groq_model_candidates() -> List[str]:
    """Build an ordered, de-duplicated list of Groq models to try."""
    configured_primary = os.getenv("GROQ_CHAT_MODEL", "").strip()
    configured_fallbacks = [
        model.strip()
        for model in (os.getenv("GROQ_CHAT_FALLBACK_MODELS") or "").split(",")
        if model.strip()
    ]

    candidates: List[str] = []
    for model_name in [configured_primary, *configured_fallbacks, *DEFAULT_GROQ_CHAT_MODELS]:
        if model_name and model_name not in candidates:
            candidates.append(model_name)
    return candidates


def _build_recommendation_context(
    user: Dict[str, Any],
    stress_result: Dict[str, Any],
    test_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    history_payload = []
    for item in test_history or []:
        if not isinstance(item, dict):
            continue
        history_payload.append(
            {
                "stress_level": item.get("stress_level"),
                "timestamp": item.get("timestamp"),
            }
        )

    return {
        "user_data": {
            "age": user.get("age"),
            "gender": user.get("gender"),
            "location": user.get("location"),
            "name": user.get("name"),
            "previous_stress_issues": user.get("has_previous_stress_issues", False),
            "test_history": history_payload,
        },
        "stress_result": {
            "stress_level": stress_result.get("stress_level"),
            "stress_label": stress_result.get("stress_label"),
            "responses": stress_result.get("responses", []),
            "confidence_score": stress_result.get("confidence_score"),
            "category_scores": stress_result.get("category_scores", {}),
            "risk_factors": stress_result.get("risk_factors", []),
            "trend": stress_result.get("trend"),
            "crisis": stress_result.get("crisis"),
        },
    }


async def _generate_and_store_enhanced_recommendations(
    test_id: str,
    user: Dict[str, Any],
    stress_result: Dict[str, Any],
    test_history: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    try:
        context = _build_recommendation_context(user, stress_result, test_history)
        recommendations = await enhanced_engine.generate_personalized_recommendations_with_llm(
            user_data=context["user_data"],
            stress_result=context["stress_result"],
        )
        tests_collection.update_one(
            {"_id": ObjectId(test_id)},
            {
                "$set": {
                    "enhanced_recommendations": recommendations,
                    "enhanced_recommendations_generated_at": datetime.utcnow(),
                }
            },
        )
        return recommendations
    except Exception as exc:
        logger.warning("Failed to generate enhanced recommendations for test %s: %s", test_id, exc)
        return None


def _send_stress_result_sms_safe(
    phone: str,
    user_name: str,
    stress_label: str,
    confidence: float,
    top_recommendations: List[str],
) -> None:
    try:
        sms_service.send_stress_result_sms(
            phone=phone,
            user_name=user_name,
            stress_label=stress_label,
            confidence=confidence,
            top_recommendations=top_recommendations,
        )
    except Exception as exc:
        logger.warning("Failed to send stress result SMS: %s", exc)


def _send_crisis_alert_email_safe(
    user_email: str,
    user_name: str,
    crisis_reasons: List[str],
) -> None:
    try:
        email_service.send_crisis_alert_email(
            user_email=user_email,
            user_name=user_name,
            crisis_reasons=crisis_reasons,
        )
    except Exception as exc:
        logger.warning("Failed to send crisis alert email: %s", exc)


def _schedule_post_submit_tasks(
    background_tasks: BackgroundTasks,
    test_id: str,
    submitting_user: Optional[Dict[str, Any]],
    stress_result: Dict[str, Any],
    test_history: Optional[List[Dict[str, Any]]] = None,
    top_recommendations: Optional[List[str]] = None,
    send_crisis_email: bool = False,
) -> None:
    if not submitting_user:
        return

    background_tasks.add_task(
        _generate_and_store_enhanced_recommendations,
        test_id=test_id,
        user=submitting_user,
        stress_result=stress_result,
        test_history=test_history,
    )

    phone_number = str(submitting_user.get("phone_number") or "").strip()
    if phone_number:
        background_tasks.add_task(
            _send_stress_result_sms_safe,
            phone=phone_number,
            user_name=submitting_user.get("name", "User"),
            stress_label=str(stress_result.get("stress_label", "")),
            confidence=float(stress_result.get("confidence_score", 0.0) or 0.0),
            top_recommendations=list(top_recommendations or []),
        )

    if send_crisis_email and (stress_result.get("crisis") or {}).get("is_crisis"):
        user_email = str(submitting_user.get("email") or "").strip()
        if user_email:
            background_tasks.add_task(
                _send_crisis_alert_email_safe,
                user_email=user_email,
                user_name=submitting_user.get("name", "User"),
                crisis_reasons=list((stress_result.get("crisis") or {}).get("reasons") or []),
            )

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
# VIDEO ASSESSMENT — helpers & endpoint
# ============================================

class VideoTestSubmission(BaseModel):
    verbal_responses: List[str]   # 18 natural-language answers
    audio_features: Optional[Dict[str, float]] = None
    facial_features: Optional[Dict[str, float]] = None
    sentiment_features: Optional[Dict[str, float]] = None


def _keyword_score(answer: str, question_index: int) -> int:
    """
    Map a verbal answer to a 1-5 stress score using keyword matching.
    Q15 (index 14) is inverted because it asks about *satisfaction*
    (high satisfaction = low stress).
    """
    a = answer.lower()

    if any(w in a for w in ['always', 'constantly', 'extremely', 'very much',
                             'all the time', 'severely', 'completely', 'totally',
                             'absolutely', 'overwhelmingly', 'unbearable']):
        raw = 5
    elif any(w in a for w in ['often', 'frequently', 'quite', 'usually', 'a lot',
                               'regularly', 'most of the time', 'mostly', 'generally',
                               'very often', 'quite often']):
        raw = 4
    elif any(w in a for w in ['sometimes', 'occasionally', 'moderate', 'a bit',
                               'somewhat', 'neutral', 'average', 'now and then',
                               'from time to time', 'moderately']):
        raw = 3
    elif any(w in a for w in ['rarely', 'seldom', 'almost never', 'barely',
                               'not much', 'a little', 'slightly', 'minimal',
                               'not really', 'hardly']):
        raw = 2
    elif any(w in a for w in ['never', 'not at all', 'nope', 'none', 'zero',
                               'no ', 'not ever', 'absolutely not']):
        raw = 1
    else:
        raw = 3  # default to moderate

    # Q15 → invert: "very satisfied" (raw=1 from "never stressed") → score 1 (low stress)
    if question_index == 14:
        raw = 6 - raw   # 1↔5, 2↔4, 3↔3

    return raw


async def _convert_with_groq(verbal_responses: List[str]) -> List[int]:
    """
    Use the Groq LLM to convert 18 verbal answers into 1-5 numeric stress scores.
    Raises an exception if every model fails so the caller can fall back to keywords.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY not set or empty")

    client = groq.AsyncGroq(api_key=api_key)

    # Build the conversation prompt
    qa_lines = "\n".join(
        f"Q{i+1}: {QUESTIONNAIRE[i]['question']}\nA{i+1}: {verbal_responses[i]}"
        for i in range(18)
    )

    prompt = (
        "You are rating stress-assessment questionnaire responses.\n"
        "For each question-answer pair, assign a score from 1 to 5:\n"
        "  1 = Never / Not at all (lowest stress)\n"
        "  2 = Rarely / Slightly\n"
        "  3 = Sometimes / Moderately\n"
        "  4 = Often / Very\n"
        "  5 = Always / Extremely (highest stress)\n"
        "Special rule — Q15 asks about work-life balance *satisfaction* (not frequency of stress):\n"
        "  1 = Very satisfied (low stress), 5 = Very unsatisfied (high stress).\n\n"
        f"{qa_lines}\n\n"
        'Return ONLY a valid JSON object with exactly 18 integers, e.g.:\n'
        '{"scores": [1, 3, 2, 4, 5, 2, 1, 3, 4, 5, 2, 3, 1, 4, 2, 3, 4, 5]}'
    )

    for model in _groq_model_candidates():
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.1,
            )
            content = response.choices[0].message.content or ""
            match = _re.search(r'\{.*?\}', content, _re.DOTALL)
            if match:
                data = _json.loads(match.group())
                scores = data.get("scores", [])
                if len(scores) == 18 and all(isinstance(s, (int, float)) for s in scores):
                    clamped = [max(1, min(5, int(round(s)))) for s in scores]
                    return clamped
        except Exception as exc:
            logger.warning("Groq model %s failed for video scoring: %s", model, exc)
            continue

    raise RuntimeError("All Groq models failed for verbal-to-score conversion")


async def convert_verbal_to_scores(verbal_responses: List[str]) -> List[int]:
    """
    Convert 18 verbal answers to 1-5 scores.
    Tries local NN first; then Groq; falls back to keyword matching.
    """
    try:
        nn_result = verbal_nn_scorer.score_responses(verbal_responses)
        if nn_result.get("avg_confidence", 0) >= 0.45:
            return nn_result["scores"]
    except Exception as exc:
        logger.info("NN verbal scorer unavailable, using fallback chain: %s", exc)

    try:
        return await _convert_with_groq(verbal_responses)
    except Exception as exc:
        logger.info("Falling back to keyword scoring: %s", exc)
        return [_keyword_score(ans, i) for i, ans in enumerate(verbal_responses)]


@router.post("/video-test/submit")
async def submit_video_test(
    video_test: VideoTestSubmission,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_role(["user"])),
):
    """Submit video-based stress assessment with full explainability."""
    user_id = current_user["user_id"]

    if len(video_test.verbal_responses) != 18:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expected exactly 18 verbal responses")

    multimodal_meta = {
        "enabled": False,
        "method": "fallback",
    }
    try:
        mm_result = multimodal_pipeline.assess(
            verbal_responses=video_test.verbal_responses,
            audio_features=video_test.audio_features,
            facial_features=video_test.facial_features,
            sentiment_features=video_test.sentiment_features,
        )
        scores = mm_result["scores"]
        multimodal_meta = mm_result.get("multimodal", multimodal_meta)
    except Exception as exc:
        logger.info("Multimodal pipeline unavailable, falling back to verbal scoring: %s", exc)
        scores = await convert_verbal_to_scores(video_test.verbal_responses)

    try:
        result = predictor.predict_with_explanation(scores)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Prediction error: {str(exc)}")

    history = list(tests_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(10))
    trend_data = predictor.get_stress_trend(history)
    crisis_data = predictor.check_crisis(user_id, history, result)

    test_dict = {
        "user_id": user_id,
        "responses": scores,
        "verbal_responses": video_test.verbal_responses,
        "assessment_type": "video",
        "stress_level": int(result["stress_level"]),
        "stress_label": result["stress_label"],
        "confidence_score": result["confidence"],
        "continuous_score": result["continuous_score"],
        "recommendations": result["recommendations"],
        "explanation": result["explanation"],
        "category_scores": result["category_scores"],
        "risk_factors": result["risk_factors"],
        "probabilities": result["probabilities"],
        "trend": trend_data,
        "crisis": crisis_data,
        "multimodal": multimodal_meta,
        "timestamp": datetime.utcnow(),
    }

    db_result = tests_collection.insert_one(test_dict)
    test_id = str(db_result.inserted_id)

    users_collection.update_one({"_id": ObjectId(user_id)}, {"$push": {"test_history": test_id}})

    submitting_user = users_collection.find_one({"_id": ObjectId(user_id)})
    recommendation_history = [
        {
            "stress_level": int(result["stress_level"]),
            "timestamp": test_dict["timestamp"],
        },
        *[
            {
                "stress_level": item.get("stress_level"),
                "timestamp": item.get("timestamp"),
            }
            for item in history
        ],
    ]
    _schedule_post_submit_tasks(
        background_tasks=background_tasks,
        test_id=test_id,
        submitting_user=submitting_user,
        stress_result={
            "stress_level": int(result["stress_level"]),
            "stress_label": result["stress_label"],
            "responses": scores,
            "confidence_score": result["confidence"],
            "category_scores": result["category_scores"],
            "risk_factors": result["risk_factors"],
            "trend": trend_data,
            "crisis": crisis_data,
        },
        test_history=recommendation_history,
        top_recommendations=result["recommendations"][:3] if result["recommendations"] else [],
    )

    return {
        "id": test_id,
        "user_id": user_id,
        "responses": scores,
        "stress_level": int(result["stress_level"]),
        "stress_label": result["stress_label"],
        "confidence_score": result["confidence"],
        "continuous_score": result["continuous_score"],
        "probabilities": result["probabilities"],
        "recommendations": result["recommendations"],
        "explanation": result["explanation"],
        "category_scores": result["category_scores"],
        "risk_factors": result["risk_factors"],
        "trend": trend_data,
        "crisis": crisis_data,
        "multimodal": multimodal_meta,
        "timestamp": test_dict["timestamp"],
    }


# ============================================
# STRESS TEST ENDPOINTS (ORIGINAL)
# ============================================

@router.post("/test/submit")
async def submit_test(
    test: TestSubmission,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_role(["user"])),
):
    """Submit stress test and get ML-based prediction with SHAP explanation"""
    user_id = current_user["user_id"]
    
    if len(test.responses) != 18:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expected 18 responses")
    
    if not all(1 <= r <= 5 for r in test.responses):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All responses must be between 1 and 5")
    
    # Get ML prediction with full explanation
    try:
        result = predictor.predict_with_explanation(test.responses)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Prediction error: {str(e)}")
    
    # Get test history for trend & crisis
    history = list(tests_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(10))
    trend_data = predictor.get_stress_trend(history)
    crisis_data = predictor.check_crisis(user_id, history, result)
    
    # Save test result with enhanced data
    test_dict = {
        "user_id": user_id,
        "responses": test.responses,
        "stress_level": int(result["stress_level"]),
        "stress_label": result["stress_label"],
        "confidence_score": result["confidence"],
        "continuous_score": result["continuous_score"],
        "recommendations": result["recommendations"],
        "explanation": result["explanation"],
        "category_scores": result["category_scores"],
        "risk_factors": result["risk_factors"],
        "probabilities": result["probabilities"],
        "trend": trend_data,
        "crisis": crisis_data,
        "timestamp": datetime.utcnow()
    }
    
    db_result = tests_collection.insert_one(test_dict)
    test_id = str(db_result.inserted_id)
    
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$push": {"test_history": test_id}}
    )
    
    # Fetch user for notifications
    submitting_user = users_collection.find_one({"_id": ObjectId(user_id)})
    recommendation_history = [
        {
            "stress_level": int(result["stress_level"]),
            "timestamp": test_dict["timestamp"],
        },
        *[
            {
                "stress_level": item.get("stress_level"),
                "timestamp": item.get("timestamp"),
            }
            for item in history
        ],
    ]
    _schedule_post_submit_tasks(
        background_tasks=background_tasks,
        test_id=test_id,
        submitting_user=submitting_user,
        stress_result={
            "stress_level": int(result["stress_level"]),
            "stress_label": result["stress_label"],
            "responses": test.responses,
            "confidence_score": result["confidence"],
            "category_scores": result["category_scores"],
            "risk_factors": result["risk_factors"],
            "trend": trend_data,
            "crisis": crisis_data,
        },
        test_history=recommendation_history,
        top_recommendations=result["recommendations"][:3] if result["recommendations"] else [],
        send_crisis_email=True,
    )

    return {
        "id": test_id,
        "user_id": user_id,
        "responses": test.responses,
        "stress_level": int(result["stress_level"]),
        "stress_label": result["stress_label"],
        "confidence_score": result["confidence"],
        "continuous_score": result["continuous_score"],
        "probabilities": result["probabilities"],
        "recommendations": result["recommendations"],
        "explanation": result["explanation"],
        "category_scores": result["category_scores"],
        "risk_factors": result["risk_factors"],
        "trend": trend_data,
        "crisis": crisis_data,
        "timestamp": test_dict["timestamp"]
    }

@router.get("/test/history/{user_id}")
async def get_test_history(user_id: str, current_user: dict = Depends(require_role(["user", "admin", "doctor"]))):
    """Get user's test history - users can only access their own, doctors/admins can access patients"""
    # ✅ CRITICAL FIX: Add object-level authorization
    # Only allow users to see their own history, admins/doctors can see all
    if current_user["role"] == "user" and current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own test history"
        )
    
    # Validate user_id is valid ObjectId
    try:
        ObjectId(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
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
    """Get detailed test results - users can only access their own tests"""
    # ✅ CRITICAL FIX: Validate ID format and add object-level authorization
    try:
        ObjectId(test_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid test ID format"
        )
    
    test = tests_collection.find_one({"_id": ObjectId(test_id)})
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Check authorization
    test_user_id = test["user_id"]
    if current_user["role"] == "user" and current_user["user_id"] != test_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own test results"
        )
    
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
    """Get enhanced, personalized recommendations based on test results
    
    Expects: query parameter test_id
    """
    # ✅ FIX: Accept test_id as query parameter (contract fix)
    user_id = current_user.get('user_id') or current_user.get('id')
    
    # Validate test_id format
    try:
        ObjectId(test_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid test ID format"
        )
    
    # Get user data
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get test result
    test = tests_collection.find_one({"_id": ObjectId(test_id)})
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # ✅ CRITICAL FIX: Add object-level authorization  
    if test["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only get recommendations for your own tests"
        )

    cached_recommendations = test.get("enhanced_recommendations")
    if isinstance(cached_recommendations, dict) and cached_recommendations:
        return cached_recommendations
    
    # Get test history for trend analysis
    test_history = list(tests_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(10))
    
    # Generate enhanced recommendations
    try:
        recommendations = await _generate_and_store_enhanced_recommendations(
            test_id=test_id,
            user=user,
            stress_result={
                "stress_level": test["stress_level"],
                "stress_label": test["stress_label"],
                "responses": test.get("responses", []),
                "confidence_score": test["confidence_score"],
                "category_scores": test.get("category_scores", {}),
                "risk_factors": test.get("risk_factors", []),
                "trend": test.get("trend"),
                "crisis": test.get("crisis"),
            },
            test_history=test_history,
        )

        if not recommendations:
            raise RuntimeError("Recommendation generation returned no data")
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
    # ✅ CRITICAL FIX: Add object-level authorization
    if current_user["user_id"] != progress.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own recommendations"
        )
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
    # ✅ CRITICAL FIX: Add object-level authorization
    if current_user["user_id"] != progress.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own recommendations"
        )
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
    # ✅ CRITICAL FIX: Add object-level authorization
    if current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own recommendations"
        )
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
    # ✅ CRITICAL FIX: Add object-level authorization
    if current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own recommendations"
        )
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
    # ✅ CRITICAL FIX: Add object-level authorization
    if current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own achievements"
        )
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
    # ✅ CRITICAL FIX: Add object-level authorization
    if current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own progress"
        )
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
    """Get user's appointments - users can only access their own"""
    # ✅ CRITICAL FIX: Add object-level authorization
    if current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own appointments"
        )
    
    # Validate user_id format
    try:
        ObjectId(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    appointments = list(appointments_collection.find({"user_id": user_id}).sort("created_at", -1))

    response: list[dict[str, Any]] = []
    for appointment in appointments:
        enriched = add_access_state(appointment)
        response.append(
            {
                "id": str(enriched["_id"]),
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
                "can_manage_record_sharing": enriched.get("can_manage_record_sharing", False),
                "data_access_active": enriched.get("data_access_active", False),
                "data_access_message": enriched.get("data_access_message"),
                "access_deadline_label": enriched.get("access_deadline_label"),
            }
        )

    return response

@router.post("/appointment/book", response_model=AppointmentResponse)
async def book_appointment(appointment: AppointmentCreate, current_user: dict = Depends(require_role(["user"]))):
    """Book an appointment with a doctor"""
    # ✅ CRITICAL FIX: Use authenticated user_id, not client-provided
    user_id = current_user["user_id"]
    
    # Validate doctor_id format
    try:
        ObjectId(appointment.doctor_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid doctor ID format"
        )
    
    # Verify doctor exists and is verified
    doctor = doctors_collection.find_one({"_id": ObjectId(appointment.doctor_id)})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    if not doctor.get("is_verified", False):
        raise HTTPException(status_code=400, detail="Doctor is not verified")
    
    # ✅ FIX: Check for double-booking - ensure slot isn't already booked with correct statuses
    try:
        slot_start_at, slot_end_at = parse_time_slot_window(
            appointment.time_slot,
            reference=datetime.utcnow(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time slot format: {appointment.time_slot}",
        ) from exc

    access_expires_at = slot_end_at + timedelta(hours=1)
    slot_label = format_slot_window(slot_start_at, slot_end_at)

    existing_booking = appointments_collection.find_one(
        {
            "doctor_id": appointment.doctor_id,
            "status": {"$in": ["pending", "approved", "confirmed"]},
            "$or": [
                {"slot_start_at": slot_start_at},
                {
                    "$and": [
                        {"slot_start_at": {"$exists": False}},
                        {"time_slot": appointment.time_slot},
                    ]
                },
            ],
        }
    )
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This time slot is already booked"
        )
    
    # Verify time slot is available
    if appointment.time_slot not in doctor.get("available_slots", []):
        raise HTTPException(status_code=400, detail="Time slot not available")
    
    # Get user info
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create appointment
    appointment_dict = {
        "user_id": user_id,  # Use authenticated user, not appointment.user_id
        "user_name": user["name"],
        "user_email": user["email"],
        "doctor_id": appointment.doctor_id,
        "doctor_name": doctor["name"],
        "time_slot": appointment.time_slot,
        "slot_start_at": slot_start_at,
        "slot_end_at": slot_end_at,
        "access_expires_at": access_expires_at,
        "status": "pending",
        "notes": appointment.notes,
        "records_shared_with_doctor": False,
        "shared_with_doctor_at": None,
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
            appointment_time=slot_label,
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
                appointment_time=slot_label,
                notes=appointment.notes or ""
            )
    except Exception as e:
        print(f"⚠️ Failed to send booking SMS: {e}")
        # Don't fail the request if SMS fails
    
    return {
        "id": appointment_id,
        "user_id": user_id,
        "user_name": user["name"],
        "doctor_id": appointment.doctor_id,
        "doctor_name": doctor["name"],
        "time_slot": appointment.time_slot,
        "slot_start_at": slot_start_at,
        "slot_end_at": slot_end_at,
        "access_expires_at": access_expires_at,
        "status": "pending",
        "notes": appointment.notes,
        "records_shared_with_doctor": False,
        "created_at": appointment_dict["created_at"]
    }


@router.put("/appointment/{appointment_id}/share-access")
async def update_appointment_share_access(
    appointment_id: str,
    share_update: AppointmentShareUpdate,
    current_user: dict = Depends(require_role(["user"])),
):
    """Allow a user to share appointment-scoped data access with their doctor."""
    try:
        appointment_object_id = ObjectId(appointment_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid appointment ID format",
        ) from exc

    appointment = appointments_collection.find_one({"_id": appointment_object_id})
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    if appointment.get("user_id") != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage sharing for your own appointments.",
        )

    enriched = add_access_state(appointment)
    if appointment.get("status") not in {"approved", "completed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can share details only after the doctor confirms the appointment.",
        )

    if (
        share_update.share_with_doctor
        and enriched.get("access_expires_at") is not None
        and datetime.utcnow() > enriched["access_expires_at"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The sharing window has already ended for this appointment.",
        )

    update_payload: dict[str, Any] = {
        "records_shared_with_doctor": share_update.share_with_doctor,
        "shared_with_doctor_at": datetime.utcnow() if share_update.share_with_doctor else None,
        "updated_at": datetime.utcnow(),
    }
    appointments_collection.update_one(
        {"_id": appointment_object_id},
        {"$set": update_payload},
    )

    updated_appointment = appointments_collection.find_one({"_id": appointment_object_id})
    if not updated_appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    enriched_updated = add_access_state(updated_appointment)
    return {
        "message": (
            "Doctor access enabled for this appointment."
            if share_update.share_with_doctor
            else "Doctor access disabled for this appointment."
        ),
        "appointment": {
            "id": str(enriched_updated["_id"]),
            "records_shared_with_doctor": enriched_updated.get("records_shared_with_doctor", False),
            "can_manage_record_sharing": enriched_updated.get("can_manage_record_sharing", False),
            "data_access_active": enriched_updated.get("data_access_active", False),
            "data_access_message": enriched_updated.get("data_access_message"),
            "slot_start_at": enriched_updated.get("slot_start_at"),
            "slot_end_at": enriched_updated.get("slot_end_at"),
            "access_expires_at": enriched_updated.get("access_expires_at"),
            "slot_label": enriched_updated.get("slot_label"),
            "access_deadline_label": enriched_updated.get("access_deadline_label"),
        },
    }

# ============================================
# CHATBOT
# ============================================

@router.post("/chatbot/chat", response_model=ChatbotResponse)
async def chatbot_chat(chat_request: ChatbotMessage, current_user: dict = Depends(require_role(["user"]))):
    """Chat with AI stress counselor that auto-detects stress levels"""
    try:
        # Initialize Groq client
        api_key = os.getenv("GROQ_API_KEY", "").strip()
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
            except (IndexError, ValueError, TypeError):
                pass
        
        # Extract confidence
        if "confidence:" in response_lower:
            try:
                conf_text = full_response.split("CONFIDENCE:")[1].split()[0].strip()
                confidence = float(conf_text)
            except (IndexError, ValueError, TypeError):
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


# ============================================
# EXPLAINABILITY & ADVANCED ML ENDPOINTS
# ============================================

@router.get("/test/{test_id}/explanation")
async def get_test_explanation(test_id: str, current_user: dict = Depends(require_role(["user", "doctor", "admin"]))):
    """Get SHAP explanation, category scores, and risk factors for a specific test"""
    try:
        ObjectId(test_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid test ID format")

    test = tests_collection.find_one({"_id": ObjectId(test_id)})
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if current_user["role"] == "user" and current_user["user_id"] != test["user_id"]:
        raise HTTPException(status_code=403, detail="You can only access your own test results")
    if current_user["role"] == "doctor":
        require_doctor_user_access(current_user, test["user_id"])

    # Return stored explanation if present, otherwise recompute
    if test.get("explanation"):
        return {
            "test_id": test_id,
            "explanation": test["explanation"],
            "category_scores": test.get("category_scores", {}),
            "risk_factors": test.get("risk_factors", []),
            "continuous_score": test.get("continuous_score"),
            "probabilities": test.get("probabilities", {}),
        }

    # Recompute for older tests
    try:
        result = predictor.predict_with_explanation(test["responses"])
        tests_collection.update_one(
            {"_id": ObjectId(test_id)},
            {"$set": {
                "explanation": result["explanation"],
                "category_scores": result["category_scores"],
                "risk_factors": result["risk_factors"],
                "continuous_score": result["continuous_score"],
                "probabilities": result["probabilities"],
            }},
        )
        return {
            "test_id": test_id,
            "explanation": result["explanation"],
            "category_scores": result["category_scores"],
            "risk_factors": result["risk_factors"],
            "continuous_score": result["continuous_score"],
            "probabilities": result["probabilities"],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute explanation: {str(exc)}")


@router.get("/test/{test_id}/report")
async def get_test_report(test_id: str, current_user: dict = Depends(require_role(["user", "doctor"]))):
    """Generate and return a PDF report for a specific test"""
    from fastapi.responses import Response

    try:
        ObjectId(test_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid test ID format")

    test = tests_collection.find_one({"_id": ObjectId(test_id)})
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if current_user["role"] == "user" and current_user["user_id"] != test["user_id"]:
        raise HTTPException(status_code=403, detail="You can only access your own test results")
    if current_user["role"] == "doctor":
        require_doctor_user_access(current_user, test["user_id"])

    user = users_collection.find_one({"_id": ObjectId(test["user_id"])})
    user_name = user.get("name", "User") if user else "User"

    try:
        pdf_bytes = report_generator.generate_user_report(
            user_data={"name": user_name},
            test_result=test,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="stress_report_{test_id}.pdf"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(exc)}")


@router.get("/stress-trend/{user_id}")
async def get_stress_trend(user_id: str, current_user: dict = Depends(require_role(["user", "doctor", "admin"]))):
    """Get stress trend analysis for a user"""
    if current_user["role"] == "user" and current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="You can only access your own trends")
    if current_user["role"] == "doctor":
        require_doctor_user_access(current_user, user_id)

    try:
        ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    history = list(tests_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(20))
    trend = predictor.get_stress_trend(history)
    return {"user_id": user_id, "trend": trend}


@router.get("/analytics/{user_id}")
async def get_user_analytics(user_id: str, current_user: dict = Depends(require_role(["user"]))):
    """Get personal analytics for a user"""
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="You can only access your own analytics")

    try:
        ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    try:
        result = analytics.get_user_analytics(user_id)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute analytics: {str(exc)}")


@router.get("/doctor-match/{user_id}")
async def get_doctor_match(user_id: str, current_user: dict = Depends(require_role(["user"]))):
    """Get smart doctor recommendations based on stress profile"""
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="You can only access your own doctor matches")

    try:
        ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    latest_test = tests_collection.find_one({"user_id": user_id}, sort=[("timestamp", -1)])
    if not latest_test:
        raise HTTPException(status_code=404, detail="No test results found. Take a test first.")

    try:
        matches = analytics.smart_doctor_match(user_id, latest_test)
        return {"user_id": user_id, "recommended_doctors": matches}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute doctor matches: {str(exc)}")
