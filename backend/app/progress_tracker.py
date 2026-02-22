"""
Progress Tracking & Gamification System
Tracks user progress, awards badges, manages streaks, and calculates achievements
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

class RecommendationProgress(BaseModel):
    """Track individual recommendation completion"""
    id: str
    user_id: str
    recommendation_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    effectiveness_rating: Optional[int] = None  # 1-5 stars
    notes: Optional[str] = None
    reminder_set: bool = False
    reminder_time: Optional[str] = None
    reminder_frequency: Optional[str] = None
    completion_streak: int = 0
    last_completed: Optional[datetime] = None

class UserAchievements(BaseModel):
    """User achievement and gamification data"""
    user_id: str
    badges: List[str] = []
    total_recommendations_completed: int = 0
    total_recommendations_started: int = 0
    streak_days: int = 0
    longest_streak: int = 0
    points: int = 0
    level: int = 1
    meditation_minutes: int = 0
    exercise_minutes: int = 0
    journal_entries: int = 0
    therapist_sessions: int = 0
    last_activity_date: Optional[datetime] = None


class ProgressTracker:
    """Main progress tracking and gamification engine"""
    
    # Badge definitions
    BADGES = {
        "first_step": {
            "name": "🎯 First Step",
            "description": "Completed your first recommendation",
            "requirement": "total_completed >= 1"
        },
        "getting_started": {
            "name": "🌱 Getting Started",
            "description": "Completed 5 recommendations",
            "requirement": "total_completed >= 5"
        },
        "week_warrior": {
            "name": "🔥 Week Warrior",
            "description": "7-day streak",
            "requirement": "streak_days >= 7"
        },
        "month_master": {
            "name": "💪 Month Master",
            "description": "30-day streak",
            "requirement": "streak_days >= 30"
        },
        "stress_crusher": {
            "name": "⚡ Stress Crusher",
            "description": "Completed 20 recommendations",
            "requirement": "total_completed >= 20"
        },
        "zen_master": {
            "name": "🧘 Zen Master",
            "description": "100 minutes of meditation",
            "requirement": "meditation_minutes >= 100"
        },
        "fitness_fan": {
            "name": "🏃 Fitness Fan",
            "description": "200 minutes of exercise",
            "requirement": "exercise_minutes >= 200"
        },
        "journal_enthusiast": {
            "name": "📝 Journal Enthusiast",
            "description": "30 journal entries",
            "requirement": "journal_entries >= 30"
        },
        "therapy_champion": {
            "name": "👨‍⚕️ Therapy Champion",
            "description": "Attended 5 therapy sessions",
            "requirement": "therapist_sessions >= 5"
        },
        "perfectionist": {
            "name": "⭐ Perfectionist",
            "description": "Completed 10 recommendations with 5-star rating",
            "requirement": "perfect_ratings >= 10"
        }
    }
    
    # Points system
    POINTS = {
        "complete_recommendation": 10,
        "complete_daily_goal": 25,
        "maintain_streak": 5,
        "rate_recommendation": 2,
        "add_notes": 3,
        "set_reminder": 2,
        "meditation_minute": 1,
        "exercise_minute": 1,
        "journal_entry": 15,
        "therapy_session": 50
    }
    
    # Level thresholds
    LEVELS = [
        {"level": 1, "name": "Beginner", "min_points": 0},
        {"level": 2, "name": "Explorer", "min_points": 100},
        {"level": 3, "name": "Practitioner", "min_points": 300},
        {"level": 4, "name": "Dedicated", "min_points": 600},
        {"level": 5, "name": "Advanced", "min_points": 1000},
        {"level": 6, "name": "Expert", "min_points": 1500},
        {"level": 7, "name": "Master", "min_points": 2500},
        {"level": 8, "name": "Zen Master", "min_points": 4000}
    ]
    
    def __init__(self, database_collection):
        """Initialize with database connection"""
        self.progress_collection = database_collection
    
    def mark_started(
        self, 
        user_id: str, 
        recommendation_id: str,
        set_reminder: bool = False,
        reminder_time: Optional[str] = None,
        reminder_frequency: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark a recommendation as started"""
        
        progress = {
            "user_id": user_id,
            "recommendation_id": recommendation_id,
            "started_at": datetime.utcnow(),
            "completed_at": None,
            "reminder_set": set_reminder,
            "reminder_time": reminder_time,
            "reminder_frequency": reminder_frequency,
            "status": "in_progress"
        }
        
        result = self.progress_collection.insert_one(progress)
        
        # Award points for starting
        self.add_points(user_id, self.POINTS["complete_recommendation"] // 2)
        
        return {
            "id": str(result.inserted_id),
            "message": "Recommendation started! You've earned 5 points.",
            "points_earned": 5
        }
    
    def mark_completed(
        self,
        user_id: str,
        recommendation_id: str,
        effectiveness_rating: Optional[int] = None,
        notes: Optional[str] = None,
        minutes_spent: Optional[int] = None,
        activity_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark a recommendation as completed and award points/badges"""
        
        # Update progress
        self.progress_collection.update_one(
            {"user_id": user_id, "recommendation_id": recommendation_id},
            {
                "$set": {
                    "completed_at": datetime.utcnow(),
                    "effectiveness_rating": effectiveness_rating,
                    "notes": notes,
                    "status": "completed"
                }
            }
        )
        
        # Calculate points
        points_earned = self.POINTS["complete_recommendation"]
        
        if effectiveness_rating:
            points_earned += self.POINTS["rate_recommendation"]
        
        if notes:
            points_earned += self.POINTS["add_notes"]
        
        # Activity-specific tracking
        if activity_type and minutes_spent:
            if activity_type == "meditation":
                self.add_meditation_minutes(user_id, minutes_spent)
                points_earned += minutes_spent * self.POINTS["meditation_minute"]
            elif activity_type == "exercise":
                self.add_exercise_minutes(user_id, minutes_spent)
                points_earned += minutes_spent * self.POINTS["exercise_minute"]
            elif activity_type == "journal":
                self.increment_journal_entries(user_id)
                points_earned += self.POINTS["journal_entry"]
            elif activity_type == "therapy":
                self.increment_therapy_sessions(user_id)
                points_earned += self.POINTS["therapy_session"]
        
        # Update streak
        streak_bonus = self.update_streak(user_id)
        points_earned += streak_bonus
        
        # Add total points
        self.add_points(user_id, points_earned)
        
        # Check for new badges
        new_badges = self.check_and_award_badges(user_id)
        
        # Get updated achievements
        achievements = self.get_user_achievements(user_id)
        
        return {
            "message": "Congratulations! Recommendation completed!",
            "points_earned": points_earned,
            "new_badges": new_badges,
            "current_level": achievements["level"],
            "current_streak": achievements["streak_days"],
            "total_points": achievements["points"]
        }
    
    def update_streak(self, user_id: str) -> int:
        """Update user's completion streak and return bonus points"""
        achievements = self.get_user_achievements(user_id)
        last_activity = achievements.get("last_activity_date")
        
        today = datetime.utcnow().date()
        streak_days = achievements.get("streak_days", 0)
        
        if last_activity:
            last_date = last_activity.date()
            days_diff = (today - last_date).days
            
            if days_diff == 0:
                # Same day, no streak change
                return 0
            elif days_diff == 1:
                # Consecutive day, increment streak
                streak_days += 1
                bonus = self.POINTS["maintain_streak"] * streak_days
            else:
                # Streak broken
                streak_days = 1
                bonus = 0
        else:
            # First activity
            streak_days = 1
            bonus = 0
        
        # Update achievements
        self._update_achievement_field(user_id, "streak_days", streak_days)
        self._update_achievement_field(user_id, "last_activity_date", datetime.utcnow())
        
        # Update longest streak if applicable
        longest = achievements.get("longest_streak", 0)
        if streak_days > longest:
            self._update_achievement_field(user_id, "longest_streak", streak_days)
        
        return bonus
    
    def add_points(self, user_id: str, points: int) -> int:
        """Add points to user and check for level up"""
        achievements = self.get_user_achievements(user_id)
        new_total = achievements.get("points", 0) + points
        
        self._update_achievement_field(user_id, "points", new_total)
        
        # Check for level up
        new_level = self.calculate_level(new_total)
        current_level = achievements.get("level", 1)
        
        if new_level > current_level:
            self._update_achievement_field(user_id, "level", new_level)
        
        return new_total
    
    def calculate_level(self, points: int) -> int:
        """Calculate level based on points"""
        level = 1
        for level_info in reversed(self.LEVELS):
            if points >= level_info["min_points"]:
                level = level_info["level"]
                break
        return level
    
    def get_level_name(self, level: int) -> str:
        """Get level name"""
        for level_info in self.LEVELS:
            if level_info["level"] == level:
                return level_info["name"]
        return "Beginner"
    
    def points_to_next_level(self, current_points: int) -> int:
        """Calculate points needed for next level"""
        current_level = self.calculate_level(current_points)
        
        for level_info in self.LEVELS:
            if level_info["level"] == current_level + 1:
                return level_info["min_points"] - current_points
        
        return 0  # Max level reached
    
    def check_and_award_badges(self, user_id: str) -> List[str]:
        """Check eligibility and award new badges"""
        achievements = self.get_user_achievements(user_id)
        current_badges = set(achievements.get("badges", []))
        new_badges = []
        
        stats = {
            "total_completed": achievements.get("total_recommendations_completed", 0),
            "streak_days": achievements.get("streak_days", 0),
            "meditation_minutes": achievements.get("meditation_minutes", 0),
            "exercise_minutes": achievements.get("exercise_minutes", 0),
            "journal_entries": achievements.get("journal_entries", 0),
            "therapist_sessions": achievements.get("therapist_sessions", 0)
        }
        
        for badge_id, badge_info in self.BADGES.items():
            if badge_info["name"] not in current_badges:
                # Check requirement
                if self._check_badge_requirement(badge_info["requirement"], stats):
                    current_badges.add(badge_info["name"])
                    new_badges.append(badge_info["name"])
        
        # Update badges
        if new_badges:
            self._update_achievement_field(user_id, "badges", list(current_badges))
        
        return new_badges
    
    def _check_badge_requirement(self, requirement: str, stats: Dict) -> bool:
        """Check if badge requirement is met"""
        try:
            return eval(requirement, {"__builtins__": {}}, stats)
        except:
            return False
    
    def add_meditation_minutes(self, user_id: str, minutes: int):
        """Add meditation minutes"""
        achievements = self.get_user_achievements(user_id)
        new_total = achievements.get("meditation_minutes", 0) + minutes
        self._update_achievement_field(user_id, "meditation_minutes", new_total)
    
    def add_exercise_minutes(self, user_id: str, minutes: int):
        """Add exercise minutes"""
        achievements = self.get_user_achievements(user_id)
        new_total = achievements.get("exercise_minutes", 0) + minutes
        self._update_achievement_field(user_id, "exercise_minutes", new_total)
    
    def increment_journal_entries(self, user_id: str):
        """Increment journal entries count"""
        achievements = self.get_user_achievements(user_id)
        new_total = achievements.get("journal_entries", 0) + 1
        self._update_achievement_field(user_id, "journal_entries", new_total)
    
    def increment_therapy_sessions(self, user_id: str):
        """Increment therapy sessions count"""
        achievements = self.get_user_achievements(user_id)
        new_total = achievements.get("therapist_sessions", 0) + 1
        self._update_achievement_field(user_id, "therapist_sessions", new_total)
    
    def get_user_achievements(self, user_id: str) -> Dict[str, Any]:
        """Get user's achievement data"""
        # This would query from database
        # Placeholder implementation
        return {
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
            "therapist_sessions": 0
        }
    
    def _update_achievement_field(self, user_id: str, field: str, value: Any):
        """Update a specific achievement field"""
        # This would update database
        pass
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top users by points (optional feature)"""
        # Placeholder for future implementation
        return []