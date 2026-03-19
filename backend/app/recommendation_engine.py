"""
Enhanced Recommendation Engine with AI-Powered Personalization
Generates personalized, actionable recommendations based on user profile and stress history
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json as _json
import logging
import os
import random
import re as _re

import groq
from ml_model.recommendation_ranker import recommendation_ranker

logger = logging.getLogger(__name__)

DEFAULT_GROQ_RECOMMENDATION_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

ACTIONABLE_CATEGORIES = ["immediate", "daily", "weekly", "lifestyle", "professional", "personalized"]
LLM_CATEGORIES = ["immediate", "daily", "weekly", "lifestyle", "personalized"]

CATEGORY_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "immediate": {
        "icon": "Calm",
        "duration": "5 minutes",
        "difficulty": "easy",
        "effectiveness": 84,
        "resource_type": "exercise",
        "resource_url": "/exercises/breathing-478",
    },
    "daily": {
        "icon": "Routine",
        "duration": "20 minutes",
        "difficulty": "medium",
        "effectiveness": 82,
        "resource_type": "guide",
        "resource_url": "/guides/morning-routine",
    },
    "weekly": {
        "icon": "Plan",
        "duration": "1 hour",
        "difficulty": "medium",
        "effectiveness": 80,
        "resource_type": "guide",
        "resource_url": "/guides/nature-therapy",
    },
    "lifestyle": {
        "icon": "Balance",
        "duration": "Ongoing",
        "difficulty": "medium",
        "effectiveness": 78,
        "resource_type": "guide",
        "resource_url": "/guides/nutrition-stress",
    },
    "personalized": {
        "icon": "Focus",
        "duration": "10 minutes",
        "difficulty": "easy",
        "effectiveness": 76,
        "resource_type": "guide",
        "resource_url": "/guides/student-stress",
    },
}

class EnhancedRecommendationEngine:
    """Generate personalized, categorized, and actionable recommendations"""
    
    def __init__(self):
        self.resource_library = ResourceLibrary()
    
    def generate_personalized_recommendations(
        self, 
        user_data: Dict[str, Any],
        stress_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive personalized recommendations
        
        Args:
            user_data: User profile (age, gender, location, history, etc.)
            stress_result: Latest stress test result
        
        Returns:
            Categorized recommendations with resources and tracking
        """
        
        stress_level = stress_result['stress_level']
        stress_label = stress_result['stress_label']
        responses = stress_result.get('responses', [])
        
        recommendations = {
            "summary": self._generate_summary(stress_level, stress_label, user_data),
            "immediate": self._get_immediate_relief(stress_level, user_data),
            "daily": self._get_daily_habits(stress_level, user_data),
            "weekly": self._get_weekly_goals(stress_level, user_data),
            "lifestyle": self._get_lifestyle_changes(stress_level, user_data),
            "professional": self._get_professional_help(stress_level, user_data),
            "personalized": self._get_personalized_tips(user_data, responses),
            "resources": self._get_curated_resources(stress_level, user_data),
            "quick_wins": self._get_quick_wins(stress_level)
        }

        # Re-rank actionable lists with NN personalization.
        for key in ACTIONABLE_CATEGORIES:
            recommendations[key] = recommendation_ranker.rank(
                recommendations.get(key, []),
                user_data=user_data,
                stress_result=stress_result,
                category=key,
            )
        
        return recommendations

    async def generate_personalized_recommendations_with_llm(
        self,
        user_data: Dict[str, Any],
        stress_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate recommendations with an LLM overlay and safe rule-based fallback."""
        recommendations = self.generate_personalized_recommendations(user_data, stress_result)
        generated_at = self._generated_at()

        self._annotate_payload(
            recommendations,
            source="rule_based",
            source_label="Rule-based fallback",
            provider="system",
            model=None,
            generated_at=generated_at,
            stress_result=stress_result,
        )

        llm_payload, llm_meta = await self._generate_llm_overlay(user_data, stress_result, recommendations)
        if not llm_payload:
            recommendations["meta"] = self._build_meta(
                strategy="rule_based_fallback",
                primary_source="rule_based",
                source_label="Rule-based fallback recommendations",
                is_llm_generated=False,
                provider="system",
                model=None,
                generated_at=generated_at,
                categories_from_llm=[],
                fallback_reason=llm_meta.get("error"),
            )
            recommendations["summary"] = self._merge_summary(
                recommendations.get("summary", {}),
                llm_summary=None,
                source="rule_based",
                source_label="Rule-based fallback",
                provider="system",
                model=None,
                generated_at=generated_at,
                fallback_body=self._build_fallback_summary_body(stress_result),
            )
            return recommendations

        categories_from_llm: List[str] = []
        for category in LLM_CATEGORIES:
            normalized_items = self._normalize_llm_items(
                category=category,
                items=llm_payload.get(category, []),
                model=llm_meta.get("model"),
                generated_at=generated_at,
            )
            if not normalized_items:
                continue

            recommendations[category] = recommendation_ranker.rank(
                normalized_items,
                user_data=user_data,
                stress_result=stress_result,
                category=category,
            )
            categories_from_llm.append(category)

        summary_source = "llm" if categories_from_llm else "rule_based"
        summary_label = "LLM-personalized summary" if categories_from_llm else "Rule-based fallback"
        recommendations["summary"] = self._merge_summary(
            recommendations.get("summary", {}),
            llm_summary=llm_payload.get("summary"),
            source=summary_source,
            source_label=summary_label,
            provider="groq" if categories_from_llm else "system",
            model=llm_meta.get("model") if categories_from_llm else None,
            generated_at=generated_at,
            fallback_body=self._build_fallback_summary_body(stress_result),
        )
        recommendations["meta"] = self._build_meta(
            strategy="hybrid_llm" if categories_from_llm else "rule_based_fallback",
            primary_source="llm" if categories_from_llm else "rule_based",
            source_label=(
                "Hybrid recommendations: LLM-personalized guidance with safety fallback"
                if categories_from_llm
                else "Rule-based fallback recommendations"
            ),
            is_llm_generated=bool(categories_from_llm),
            provider="groq" if categories_from_llm else "system",
            model=llm_meta.get("model") if categories_from_llm else None,
            generated_at=generated_at,
            categories_from_llm=categories_from_llm,
            fallback_reason=llm_meta.get("error") if not categories_from_llm else None,
        )
        return recommendations

    def _build_meta(
        self,
        strategy: str,
        primary_source: str,
        source_label: str,
        is_llm_generated: bool,
        provider: str,
        model: Optional[str],
        generated_at: str,
        categories_from_llm: List[str],
        fallback_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "strategy": strategy,
            "primary_source": primary_source,
            "source_label": source_label,
            "is_llm_generated": is_llm_generated,
            "provider": provider,
            "model": model,
            "generated_at": generated_at,
            "categories_from_llm": categories_from_llm,
            "fallback_reason": fallback_reason,
        }

    def _annotate_payload(
        self,
        recommendations: Dict[str, Any],
        source: str,
        source_label: str,
        provider: str,
        model: Optional[str],
        generated_at: str,
        stress_result: Dict[str, Any],
    ) -> None:
        recommendations["summary"] = self._merge_summary(
            recommendations.get("summary", {}),
            llm_summary=None,
            source=source,
            source_label=source_label,
            provider=provider,
            model=model,
            generated_at=generated_at,
            fallback_body=self._build_fallback_summary_body(stress_result),
        )

        for key, value in list(recommendations.items()):
            if not isinstance(value, list):
                continue
            updated_items: List[Any] = []
            for item in value:
                if not isinstance(item, dict):
                    updated_items.append(item)
                    continue
                updated = dict(item)
                updated["source"] = source
                updated["source_label"] = source_label
                updated["generated_by"] = provider
                updated["model"] = model
                updated["generated_at"] = generated_at
                updated_items.append(updated)
            recommendations[key] = updated_items

    async def _generate_llm_overlay(
        self,
        user_data: Dict[str, Any],
        stress_result: Dict[str, Any],
        rule_based_recommendations: Dict[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            return None, {"error": "GROQ_API_KEY is not configured"}

        prompt = self._build_llm_prompt(user_data, stress_result, rule_based_recommendations)
        client = groq.AsyncGroq(api_key=api_key)
        last_error: Optional[str] = None

        for model in self._groq_model_candidates():
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are generating supportive wellness recommendations for a stress assessment app. "
                                "Be practical, calm, and specific. Do not diagnose. Do not prescribe medication. "
                                "Do not override emergency or professional-help guidance."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.35,
                    max_tokens=1800,
                )
                content = response.choices[0].message.content or ""
                data = self._extract_json_object(content)
                if isinstance(data, dict):
                    return data, {"model": model}
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Groq model %s failed for recommendations: %s", model, exc)

        return None, {"error": last_error or "All Groq models failed for recommendations"}

    def _build_llm_prompt(
        self,
        user_data: Dict[str, Any],
        stress_result: Dict[str, Any],
        rule_based_recommendations: Dict[str, Any],
    ) -> str:
        prompt_payload = {
            "user_profile": {
                "name": user_data.get("name"),
                "age": user_data.get("age"),
                "gender": user_data.get("gender"),
                "location": user_data.get("location"),
                "previous_stress_issues": user_data.get("previous_stress_issues"),
                "focus_areas": self._focus_areas(stress_result),
            },
            "stress_result": {
                "stress_level": stress_result.get("stress_level"),
                "stress_label": stress_result.get("stress_label"),
                "confidence_score": stress_result.get("confidence_score"),
                "category_scores": stress_result.get("category_scores"),
                "risk_factors": stress_result.get("risk_factors"),
                "trend": stress_result.get("trend"),
            },
            "existing_recommendation_titles": {
                category: [
                    item.get("title")
                    for item in rule_based_recommendations.get(category, [])[:3]
                    if isinstance(item, dict)
                ]
                for category in LLM_CATEGORIES
            },
        }

        return (
            "Create personalized post-assessment wellness recommendations.\n"
            "The ML model already predicted the stress level. Your job is to turn that result into practical lifestyle guidance.\n"
            "Focus on recommendations such as yoga, meditation, better sleep routine, diet, movement, and work or study balance.\n"
            "If the stress level is high or severe, keep suggestions supportive and do not weaken the need for professional help.\n"
            "Return ONLY valid JSON using this schema:\n"
            "{\n"
            '  "summary": {"title": "string", "body": "string"},\n'
            '  "immediate": [Recommendation, Recommendation],\n'
            '  "daily": [Recommendation, Recommendation],\n'
            '  "weekly": [Recommendation, Recommendation],\n'
            '  "lifestyle": [Recommendation, Recommendation],\n'
            '  "personalized": [Recommendation, Recommendation]\n'
            "}\n"
            "Each Recommendation object must use:\n"
            "{\n"
            '  "title": "string",\n'
            '  "description": "string",\n'
            '  "action": "string",\n'
            '  "duration": "string",\n'
            '  "difficulty": "easy|medium|hard",\n'
            '  "effectiveness": 70,\n'
            '  "priority": 1,\n'
            '  "instructions": ["step 1", "step 2"],\n'
            '  "frequency": "optional string",\n'
            '  "schedule": "optional string"\n'
            "}\n"
            "Keep it concise and app-friendly.\n"
            f"Context JSON:\n{_json.dumps(prompt_payload, ensure_ascii=True)}"
        )

    def _groq_model_candidates(self) -> List[str]:
        configured_primary = os.getenv("GROQ_RECOMMENDATION_MODEL", "").strip()
        configured_fallbacks = [
            model.strip()
            for model in (os.getenv("GROQ_RECOMMENDATION_FALLBACK_MODELS") or "").split(",")
            if model.strip()
        ]
        chat_primary = os.getenv("GROQ_CHAT_MODEL", "").strip()
        chat_fallbacks = [
            model.strip()
            for model in (os.getenv("GROQ_CHAT_FALLBACK_MODELS") or "").split(",")
            if model.strip()
        ]

        candidates: List[str] = []
        for model_name in [
            configured_primary,
            *configured_fallbacks,
            chat_primary,
            *chat_fallbacks,
            *DEFAULT_GROQ_RECOMMENDATION_MODELS,
        ]:
            if model_name and model_name not in candidates:
                candidates.append(model_name)
        return candidates

    def _extract_json_object(self, content: str) -> Optional[Dict[str, Any]]:
        cleaned = content.strip()
        fenced_match = _re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, _re.DOTALL)
        if fenced_match:
            cleaned = fenced_match.group(1)
        else:
            object_match = _re.search(r"\{.*\}", cleaned, _re.DOTALL)
            if object_match:
                cleaned = object_match.group(0)

        try:
            parsed = _json.loads(cleaned)
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _merge_summary(
        self,
        base_summary: Dict[str, Any],
        llm_summary: Optional[Dict[str, Any]],
        source: str,
        source_label: str,
        provider: str,
        model: Optional[str],
        generated_at: str,
        fallback_body: str,
    ) -> Dict[str, Any]:
        summary = dict(base_summary or {})
        if isinstance(llm_summary, dict):
            llm_title = str(llm_summary.get("title") or "").strip()
            llm_body = str(llm_summary.get("body") or "").strip()
            if llm_title:
                summary["title"] = llm_title
            if llm_body:
                summary["body"] = llm_body

        summary.setdefault("body", fallback_body)
        summary["source"] = source
        summary["source_label"] = source_label
        summary["generated_by"] = provider
        summary["model"] = model
        summary["generated_at"] = generated_at
        return summary

    def _normalize_llm_items(
        self,
        category: str,
        items: Any,
        model: Optional[str],
        generated_at: str,
    ) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            return []

        normalized: List[Dict[str, Any]] = []
        defaults = CATEGORY_DEFAULTS.get(category, CATEGORY_DEFAULTS["daily"])

        for index, item in enumerate(items[:3]):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            description = str(item.get("description") or "").strip()
            if not title or not description:
                continue

            difficulty = str(item.get("difficulty") or defaults["difficulty"]).lower()
            if difficulty not in {"easy", "medium", "hard"}:
                difficulty = defaults["difficulty"]

            instructions = item.get("instructions")
            if isinstance(instructions, list):
                cleaned_instructions = [str(step).strip() for step in instructions if str(step).strip()]
            else:
                cleaned_instructions = []

            normalized.append(
                {
                    "id": f"{category}_{self._slugify(title) or index + 1}",
                    "category": category,
                    "title": title,
                    "description": description,
                    "action": str(item.get("action") or "Start now").strip(),
                    "duration": str(item.get("duration") or defaults["duration"]).strip(),
                    "difficulty": difficulty,
                    "effectiveness": self._clamp_int(item.get("effectiveness"), defaults["effectiveness"], 50, 100),
                    "icon": str(item.get("icon") or defaults["icon"]).strip(),
                    "resource_type": str(item.get("resource_type") or defaults["resource_type"]).strip(),
                    "resource_url": str(item.get("resource_url") or defaults["resource_url"]).strip(),
                    "priority": self._clamp_int(item.get("priority"), index + 1, 1, 4),
                    "instructions": cleaned_instructions or None,
                    "schedule": str(item.get("schedule") or "").strip() or None,
                    "frequency": str(item.get("frequency") or "").strip() or None,
                    "source": "llm",
                    "source_label": "LLM-personalized",
                    "generated_by": "groq",
                    "model": model,
                    "generated_at": generated_at,
                }
            )

        return normalized

    def _build_fallback_summary_body(self, stress_result: Dict[str, Any]) -> str:
        focus_areas = self._focus_areas(stress_result)
        if focus_areas:
            return f"Current focus areas: {', '.join(focus_areas[:3])}. Start with the first one or two actions and build consistency."
        return "These recommendations are tailored to the current stress result and will fall back to safe rule-based guidance when AI is unavailable."

    def _focus_areas(self, stress_result: Dict[str, Any]) -> List[str]:
        focus_areas: List[str] = []

        category_scores = stress_result.get("category_scores") or {}
        if isinstance(category_scores, dict):
            for category, payload in category_scores.items():
                if not isinstance(payload, dict):
                    continue
                if str(payload.get("severity") or "").lower() in {"high", "severe", "critical"}:
                    focus_areas.append(str(category).replace("_", " "))

        risk_factors = stress_result.get("risk_factors") or []
        if isinstance(risk_factors, list):
            for factor in risk_factors[:4]:
                if not isinstance(factor, dict):
                    continue
                label = str(factor.get("label") or factor.get("factor") or "").strip()
                if label and label.lower() not in {item.lower() for item in focus_areas}:
                    focus_areas.append(label)

        if not focus_areas:
            responses = stress_result.get("responses") or []
            if len(responses) >= 18:
                if responses[5] >= 4:
                    focus_areas.append("sleep routine")
                if responses[13] >= 4:
                    focus_areas.append("daily overwhelm")
                if responses[15] >= 4:
                    focus_areas.append("work or study pressure")
                if responses[17] >= 4:
                    focus_areas.append("financial stress")

        return focus_areas[:5]

    def _generated_at(self) -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _slugify(self, value: str) -> str:
        return _re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")

    def _clamp_int(self, value: Any, default: int, low: int, high: int) -> int:
        try:
            numeric = int(round(float(value)))
        except Exception:
            numeric = default
        return max(low, min(high, numeric))

    def extract_recommendation_lines(self, payload: Optional[Dict[str, Any]]) -> List[str]:
        """Flatten saved enhanced recommendations into concise report-friendly lines."""
        if not isinstance(payload, dict):
            return []

        lines: List[str] = []
        summary = payload.get("summary")
        if isinstance(summary, dict):
            body = str(summary.get("body") or "").strip()
            if body:
                lines.append(body)

        for category in [*ACTIONABLE_CATEGORIES, "quick_wins"]:
            items = payload.get(category)
            if not isinstance(items, list):
                continue
            category_label = category.replace("_", " ").title()
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or "").strip()
                description = str(item.get("description") or "").strip()
                action = str(item.get("action") or "").strip()
                if not title and not description:
                    continue

                line = f"{category_label}: {title or description}"
                if title and description:
                    line = f"{category_label}: {title} - {description}"
                if action:
                    line = f"{line} (Action: {action})"
                lines.append(line)

        return lines
    
    def _generate_summary(self, stress_level: int, stress_label: str, user_data: Dict) -> Dict:
        """Generate personalized summary"""
        age = user_data.get('age', 30)
        name = user_data.get('name', 'there')
        
        summaries = {
            0: f"Great news, {name}! Your stress is well-managed. Let's keep it that way.",
            1: f"{name}, you're experiencing moderate stress. Let's address it proactively.",
            2: f"{name}, your stress level is high. Professional support is recommended.",
            3: f"⚠️ URGENT: {name}, you need immediate professional help for severe stress."
        }
        
        return {
            "title": summaries[stress_level],
            "stress_level": stress_level,
            "stress_label": stress_label,
            "priority": "high" if stress_level >= 2 else "medium" if stress_level == 1 else "low",
            "action_required": stress_level >= 2
        }
    
    def _get_immediate_relief(self, stress_level: int, user_data: Dict) -> List[Dict]:
        """Get 0-5 minute immediate relief techniques"""
        immediate = [
            {
                "id": "breathing_478",
                "category": "immediate",
                "title": "4-7-8 Breathing Technique",
                "description": "Quick anxiety relief in 2 minutes",
                "action": "Start breathing exercise",
                "duration": "2 minutes",
                "difficulty": "easy",
                "effectiveness": 87,
                "icon": "🫁",
                "resource_type": "interactive",
                "resource_url": "/exercises/breathing-478",
                "instructions": [
                    "Breathe in for 4 counts",
                    "Hold for 7 counts",
                    "Exhale for 8 counts",
                    "Repeat 4 times"
                ],
                "priority": 1
            },
            {
                "id": "grounding_54321",
                "category": "immediate",
                "title": "5-4-3-2-1 Grounding Technique",
                "description": "Reconnect with present moment",
                "action": "Start grounding exercise",
                "duration": "3 minutes",
                "difficulty": "easy",
                "effectiveness": 82,
                "icon": "🌍",
                "resource_type": "interactive",
                "resource_url": "/exercises/grounding",
                "instructions": [
                    "Name 5 things you can see",
                    "Name 4 things you can touch",
                    "Name 3 things you can hear",
                    "Name 2 things you can smell",
                    "Name 1 thing you can taste"
                ],
                "priority": 2
            },
            {
                "id": "meditation_5min",
                "category": "immediate",
                "title": "5-Minute Guided Meditation",
                "description": "Calm your mind instantly",
                "action": "Play meditation",
                "duration": "5 minutes",
                "difficulty": "easy",
                "effectiveness": 85,
                "icon": "🧘",
                "resource_type": "audio",
                "resource_url": "/audio/5min-meditation",
                "priority": 3
            }
        ]
        
        return immediate[:3] if stress_level < 2 else immediate
    
    def _get_daily_habits(self, stress_level: int, user_data: Dict) -> List[Dict]:
        """Get 15-30 minute daily habits"""
        age = user_data.get('age', 30)
        
        daily = [
            {
                "id": "morning_routine",
                "category": "daily",
                "title": "Morning Mindfulness Routine",
                "description": "Start your day with intention and calm",
                "action": "Create morning routine",
                "duration": "15 minutes",
                "difficulty": "medium",
                "effectiveness": 78,
                "icon": "🌅",
                "resource_type": "guide",
                "resource_url": "/guides/morning-routine",
                "schedule": "6:00 AM - 6:15 AM",
                "frequency": "daily",
                "priority": 1
            },
            {
                "id": "exercise_30min",
                "category": "daily",
                "title": "Daily Physical Activity",
                "description": f"{'Gentle yoga' if age > 50 else '30-minute workout'} to reduce stress",
                "action": "Start exercise plan",
                "duration": "30 minutes",
                "difficulty": "medium",
                "effectiveness": 92,
                "icon": "🏃",
                "resource_type": "video",
                "resource_url": f"/videos/{'senior-yoga' if age > 50 else 'stress-relief-workout'}",
                "schedule": "Any time",
                "frequency": "daily",
                "priority": 2
            },
            {
                "id": "journaling",
                "category": "daily",
                "title": "Stress Journal",
                "description": "Track and process your emotions",
                "action": "Start journaling",
                "duration": "10 minutes",
                "difficulty": "easy",
                "effectiveness": 75,
                "icon": "📝",
                "resource_type": "tool",
                "resource_url": "/tools/journal",
                "schedule": "Evening",
                "frequency": "daily",
                "priority": 3
            },
            {
                "id": "sleep_routine",
                "category": "daily",
                "title": "Evening Wind-Down Routine",
                "description": "Better sleep, lower stress",
                "action": "Setup bedtime routine",
                "duration": "20 minutes",
                "difficulty": "easy",
                "effectiveness": 88,
                "icon": "🌙",
                "resource_type": "guide",
                "resource_url": "/guides/sleep-routine",
                "schedule": "9:00 PM - 9:20 PM",
                "frequency": "daily",
                "priority": 4
            }
        ]
        
        return daily
    
    def _get_weekly_goals(self, stress_level: int, user_data: Dict) -> List[Dict]:
        """Get 1-2 hour per week goals"""
        location = user_data.get('location', 'your area')
        
        weekly = [
            {
                "id": "support_group",
                "category": "weekly",
                "title": "Join a Support Group",
                "description": "Connect with others facing similar challenges",
                "action": "Find group near you",
                "duration": "1 hour",
                "difficulty": "medium",
                "effectiveness": 84,
                "icon": "👥",
                "resource_type": "community",
                "resource_url": f"/community/support-groups?location={location}",
                "frequency": "weekly",
                "next_session": "Check local listings",
                "priority": 1 if stress_level >= 2 else 2
            },
            {
                "id": "therapy_session",
                "category": "weekly",
                "title": "Professional Therapy",
                "description": "One-on-one counseling sessions",
                "action": "Book appointment",
                "duration": "1 hour",
                "difficulty": "medium",
                "effectiveness": 95,
                "icon": "👨‍⚕️",
                "resource_type": "appointment",
                "resource_url": "/book-appointment",
                "frequency": "weekly",
                "priority": 1 if stress_level >= 2 else 3,
                "urgent": stress_level >= 2
            },
            {
                "id": "nature_time",
                "category": "weekly",
                "title": "Nature Therapy",
                "description": "2 hours in nature weekly reduces stress by 40%",
                "action": "Plan outdoor activity",
                "duration": "2 hours",
                "difficulty": "easy",
                "effectiveness": 79,
                "icon": "🌳",
                "resource_type": "guide",
                "resource_url": "/guides/nature-therapy",
                "frequency": "weekly",
                "priority": 3
            }
        ]
        
        return weekly
    
    def _get_lifestyle_changes(self, stress_level: int, user_data: Dict) -> List[Dict]:
        """Get long-term lifestyle recommendations"""
        lifestyle = [
            {
                "id": "exercise_program",
                "category": "lifestyle",
                "title": "12-Week Exercise Program",
                "description": "Build lasting stress resilience through fitness",
                "action": "Start program",
                "duration": "12 weeks",
                "difficulty": "medium",
                "effectiveness": 91,
                "icon": "💪",
                "resource_type": "program",
                "resource_url": "/programs/exercise-12week",
                "commitment": "3x per week, 30 minutes",
                "priority": 2
            },
            {
                "id": "nutrition",
                "category": "lifestyle",
                "title": "Stress-Reducing Nutrition Plan",
                "description": "Foods that naturally lower cortisol",
                "action": "Get meal plan",
                "duration": "Ongoing",
                "difficulty": "medium",
                "effectiveness": 76,
                "icon": "🥗",
                "resource_type": "guide",
                "resource_url": "/guides/nutrition-stress",
                "includes_recipes": True,
                "priority": 3
            },
            {
                "id": "mindfulness_course",
                "category": "lifestyle",
                "title": "8-Week Mindfulness Course",
                "description": "Evidence-based MBSR program",
                "action": "Enroll now",
                "duration": "8 weeks",
                "difficulty": "medium",
                "effectiveness": 89,
                "icon": "🧘‍♀️",
                "resource_type": "course",
                "resource_url": "/courses/mbsr",
                "evidence": {
                    "study": "Harvard Medical School MBSR Study",
                    "effectiveness_rate": 89,
                    "year": 2023
                },
                "priority": 1 if stress_level >= 1 else 2
            }
        ]
        
        return lifestyle
    
    def _get_professional_help(self, stress_level: int, user_data: Dict) -> List[Dict]:
        """Get professional support recommendations"""
        location = user_data.get('location', 'your area')
        
        professional = []
        
        if stress_level >= 2:
            professional.append({
                "id": "urgent_consultation",
                "category": "professional",
                "title": "⚠️ Urgent: Book Therapist",
                "description": "Your stress level requires professional support",
                "action": "Find therapist now",
                "duration": "Ongoing",
                "difficulty": "medium",
                "effectiveness": 96,
                "icon": "👨‍⚕️",
                "resource_type": "urgent_appointment",
                "resource_url": "/urgent-booking",
                "urgent": True,
                "priority": 1,
                "local_resources": f"Therapists in {location}",
                "insurance_check": True
            })
        
        if stress_level >= 3:
            professional.append({
                "id": "crisis_hotline",
                "category": "professional",
                "title": "🆘 Crisis Support Hotline",
                "description": "24/7 immediate help available",
                "action": "Call now",
                "duration": "Immediate",
                "difficulty": "easy",
                "effectiveness": 100,
                "icon": "📞",
                "resource_type": "crisis",
                "hotline": "988 (Suicide & Crisis Lifeline)",
                "urgent": True,
                "priority": 1
            })
        
        professional.append({
            "id": "psychiatrist",
            "category": "professional",
            "title": "Psychiatric Evaluation",
            "description": "Discuss medication and treatment options",
            "action": "Book evaluation",
            "duration": "1-2 hours",
            "difficulty": "medium",
            "effectiveness": 94,
            "icon": "💊",
            "resource_type": "appointment",
            "resource_url": "/book-psychiatrist",
            "wait_time": "2-3 weeks",
            "priority": 2 if stress_level >= 2 else 4
        })
        
        return professional
    
    def _get_personalized_tips(self, user_data: Dict, responses: List[int]) -> List[Dict]:
        """Generate tips based on user demographics and responses"""
        tips = []
        age = user_data.get('age', 30)
        gender = user_data.get('gender', '')
        
        # Age-specific
        if age < 25:
            tips.append({
                "id": "student_stress",
                "title": "Student Stress Management",
                "description": "Techniques for academic pressure",
                "action": "Learn student strategies",
                "icon": "🎓",
                "resource_url": "/guides/student-stress",
                "priority": 1
            })
        elif age > 50:
            tips.append({
                "id": "senior_wellness",
                "title": "Wellness for Mature Adults",
                "description": "Age-appropriate stress relief",
                "action": "Explore senior programs",
                "icon": "🧓",
                "resource_url": "/programs/senior-wellness",
                "priority": 1
            })
        
        # Gender-specific
        if gender == 'Female':
            tips.append({
                "id": "womens_health",
                "title": "Women's Stress & Hormones",
                "description": "Address hormonal stress factors",
                "action": "Learn more",
                "icon": "🌸",
                "resource_url": "/guides/womens-stress",
                "priority": 2
            })
        
        # Response-based (if available)
        if len(responses) >= 18:
            if responses[5] >= 4:  # Sleep issues
                tips.append({
                    "id": "sleep_specialist",
                    "title": "Sleep Disorder Screening",
                    "description": "Your responses suggest sleep problems",
                    "action": "Take sleep assessment",
                    "icon": "😴",
                    "resource_url": "/assessments/sleep",
                    "priority": 1
                })
            
            if responses[12] >= 4:  # Social withdrawal
                tips.append({
                    "id": "social_anxiety",
                    "title": "Social Connection Strategies",
                    "description": "Overcome social withdrawal",
                    "action": "View strategies",
                    "icon": "🤝",
                    "resource_url": "/guides/social-connection",
                    "priority": 2
                })
        
        return tips
    
    def _get_curated_resources(self, stress_level: int, user_data: Dict) -> List[Dict]:
        """Get curated external resources"""
        return [
            {
                "id": "headspace",
                "name": "Headspace",
                "type": "app",
                "description": "Guided meditation and mindfulness",
                "rating": 4.8,
                "price": "Free trial, then $12.99/month",
                "icon": "📱",
                "deeplink": "headspace://meditation/stress-relief",
                "recommended_for": "Daily meditation practice"
            },
            {
                "id": "calm",
                "name": "Calm",
                "type": "app",
                "description": "Sleep stories and relaxation",
                "rating": 4.7,
                "price": "$14.99/month",
                "icon": "📱",
                "deeplink": "calm://sleep-stories",
                "recommended_for": "Better sleep"
            },
            {
                "id": "betterhelp",
                "name": "BetterHelp",
                "type": "therapy",
                "description": "Online therapy platform",
                "rating": 4.5,
                "price": "$60-90/week",
                "icon": "💬",
                "url": "https://www.betterhelp.com",
                "recommended_for": "Professional counseling"
            }
        ]
    
    def _get_quick_wins(self, stress_level: int) -> List[Dict]:
        """Get quick 30-second to 1-minute wins"""
        return [
            {
                "id": "box_breathing",
                "title": "Box Breathing (60 seconds)",
                "description": "In 4, hold 4, out 4, hold 4",
                "duration": "1 minute",
                "icon": "📦"
            },
            {
                "id": "cold_water",
                "title": "Cold Water Face Splash",
                "description": "Activates dive reflex, calms instantly",
                "duration": "30 seconds",
                "icon": "💧"
            },
            {
                "id": "progressive_relaxation",
                "title": "Quick Muscle Relaxation",
                "description": "Tense and release major muscle groups",
                "duration": "2 minutes",
                "icon": "💪"
            }
        ]


class ResourceLibrary:
    """Library of all available resources"""
    
    def __init__(self):
        self.videos = self._load_videos()
        self.articles = self._load_articles()
        self.exercises = self._load_exercises()
        self.apps = self._load_apps()
    
    def _load_videos(self):
        return [
            {"id": "meditation_beginner", "title": "Meditation for Beginners", "duration": "10 min"},
            {"id": "yoga_stress", "title": "Yoga for Stress Relief", "duration": "20 min"},
            {"id": "breathing_techniques", "title": "Breathing Techniques", "duration": "15 min"}
        ]
    
    def _load_articles(self):
        return [
            {"id": "cbt_basics", "title": "CBT Techniques for Stress", "read_time": "8 min"},
            {"id": "sleep_hygiene", "title": "Sleep Hygiene Guide", "read_time": "5 min"}
        ]
    
    def _load_exercises(self):
        return [
            {"id": "breathing_478", "title": "4-7-8 Breathing"},
            {"id": "grounding", "title": "5-4-3-2-1 Grounding"}
        ]
    
    def _load_apps(self):
        return [
            {"id": "headspace", "name": "Headspace", "category": "Meditation"},
            {"id": "calm", "name": "Calm", "category": "Sleep"}
        ]


# Global instance
enhanced_engine = EnhancedRecommendationEngine()
