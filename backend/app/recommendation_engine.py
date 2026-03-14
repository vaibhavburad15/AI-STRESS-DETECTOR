"""
Enhanced Recommendation Engine with AI-Powered Personalization
Generates personalized, actionable recommendations based on user profile and stress history
"""

from typing import List, Dict, Any
from datetime import datetime
import random
from ml_model.recommendation_ranker import recommendation_ranker

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
        for key in ["immediate", "daily", "weekly", "lifestyle", "professional", "personalized"]:
            recommendations[key] = recommendation_ranker.rank(
                recommendations.get(key, []),
                user_data=user_data,
                stress_result=stress_result,
                category=key,
            )
        
        return recommendations
    
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