"""
Advanced Analytics Engine.
Provides population-level insights, doctor effectiveness, and predictive analytics.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import Counter

from .nmc_verification import get_active_verified_doctors_filter


class AnalyticsEngine:
    """Compute advanced analytics from stress platform data."""

    def __init__(self, tests_collection, users_collection, appointments_collection, doctors_collection):
        self.tests = tests_collection
        self.users = users_collection
        self.appointments = appointments_collection
        self.doctors = doctors_collection

    def get_advanced_stats(self) -> Dict[str, Any]:
        """Compute comprehensive platform analytics."""
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Time-based test counts
        tests_this_week = self.tests.count_documents({"timestamp": {"$gte": week_ago}})
        tests_this_month = self.tests.count_documents({"timestamp": {"$gte": month_ago}})
        total_tests = self.tests.count_documents({})

        # Average stress level
        pipeline_avg = [
            {"$group": {"_id": None, "avg_stress": {"$avg": "$stress_level"}}}
        ]
        avg_result = list(self.tests.aggregate(pipeline_avg))
        avg_stress = avg_result[0]["avg_stress"] if avg_result else 0

        # Stress distribution over time (last 30 days, grouped by day)
        daily_pipeline = [
            {"$match": {"timestamp": {"$gte": month_ago}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                "count": {"$sum": 1},
                "avg_stress": {"$avg": "$stress_level"},
                "severe_count": {"$sum": {"$cond": [{"$gte": ["$stress_level", 3]}, 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
        ]
        daily_stats = list(self.tests.aggregate(daily_pipeline))

        # Stress by location
        location_pipeline = [
            {"$lookup": {
                "from": "users",
                "let": {"uid": "$user_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$eq": [
                                    "$_id",
                                    {
                                        "$convert": {
                                            "input": "$$uid",
                                            "to": "objectId",
                                            "onError": None,
                                            "onNull": None,
                                        }
                                    },
                                ]
                            }
                        }
                    },
                    {"$project": {"location": 1}},
                ],
                "as": "user_info",
            }},
            {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
            {"$group": {
                "_id": "$user_info.location",
                "count": {"$sum": 1},
                "avg_stress": {"$avg": "$stress_level"},
            }},
            {"$sort": {"count": -1}},
            {"$limit": 20},
        ]
        location_stats = list(self.tests.aggregate(location_pipeline))

        # Peak hours (hour of day when tests are taken most)
        hour_pipeline = [
            {"$group": {
                "_id": {"$hour": "$timestamp"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"count": -1}},
        ]
        peak_hours = list(self.tests.aggregate(hour_pipeline))

        # Age group analysis
        age_pipeline = [
            {"$lookup": {
                "from": "users",
                "let": {"uid": "$user_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$eq": [
                                    "$_id",
                                    {
                                        "$convert": {
                                            "input": "$$uid",
                                            "to": "objectId",
                                            "onError": None,
                                            "onNull": None,
                                        }
                                    },
                                ]
                            }
                        }
                    },
                    {"$project": {"age": 1}},
                ],
                "as": "user_info",
            }},
            {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
            {"$bucket": {
                "groupBy": "$user_info.age",
                "boundaries": [0, 18, 25, 35, 50, 65, 120],
                "default": "unknown",
                "output": {
                    "count": {"$sum": 1},
                    "avg_stress": {"$avg": "$stress_level"},
                },
            }},
        ]
        try:
            age_stats = list(self.tests.aggregate(age_pipeline))
        except Exception:
            age_stats = []

        # Active users (took test in last 7 days)
        active_users_pipeline = [
            {"$match": {"timestamp": {"$gte": week_ago}}},
            {"$group": {"_id": "$user_id"}},
            {"$count": "active"},
        ]
        active_result = list(self.tests.aggregate(active_users_pipeline))
        active_users = active_result[0]["active"] if active_result else 0

        # Doctor effectiveness (avg stress change before/after appointment)
        doctor_effectiveness = self._compute_doctor_effectiveness()

        # Crisis count (severe in last 7 days)
        crisis_count = self.tests.count_documents({
            "stress_level": 3,
            "timestamp": {"$gte": week_ago},
        })

        return {
            "overview": {
                "total_tests": total_tests,
                "tests_this_week": tests_this_week,
                "tests_this_month": tests_this_month,
                "average_stress_level": round(avg_stress, 2),
                "active_users_this_week": active_users,
                "crisis_alerts_this_week": crisis_count,
            },
            "daily_trend": [
                {
                    "date": d["_id"],
                    "count": d["count"],
                    "avg_stress": round(d["avg_stress"], 2),
                    "severe_count": d.get("severe_count", 0),
                }
                for d in daily_stats
            ],
            "by_location": [
                {
                    "location": d["_id"] or "Unknown",
                    "count": d["count"],
                    "avg_stress": round(d["avg_stress"], 2),
                }
                for d in location_stats
            ],
            "peak_hours": [
                {"hour": d["_id"], "count": d["count"]}
                for d in peak_hours
            ],
            "by_age_group": [
                {
                    "age_range": str(d["_id"]),
                    "count": d["count"],
                    "avg_stress": round(d["avg_stress"], 2),
                }
                for d in age_stats
            ],
            "doctor_effectiveness": doctor_effectiveness,
        }

    def _compute_doctor_effectiveness(self) -> List[Dict[str, Any]]:
        """
        For each doctor, compute the average improvement in stress for their patients
        (comparing stress before and after completed appointments).
        """
        completed = list(self.appointments.find({"status": "completed"}))
        if not completed:
            return []

        doctor_scores: Dict[str, List[float]] = {}

        for apt in completed:
            user_id = apt.get("user_id")
            doctor_id = apt.get("doctor_id")
            apt_time = apt.get("created_at") or apt.get("updated_at")
            if not (user_id and doctor_id and apt_time):
                continue

            # Find test before appointment
            before = self.tests.find_one(
                {"user_id": user_id, "timestamp": {"$lte": apt_time}},
                sort=[("timestamp", -1)],
            )
            # Find test after appointment
            after = self.tests.find_one(
                {"user_id": user_id, "timestamp": {"$gt": apt_time}},
                sort=[("timestamp", 1)],
            )

            if before and after:
                improvement = before["stress_level"] - after["stress_level"]
                doctor_scores.setdefault(doctor_id, []).append(improvement)

        results = []
        for doc_id, improvements in doctor_scores.items():
            doc = self.doctors.find_one({"_id": __import__("bson").ObjectId(doc_id)})
            results.append({
                "doctor_id": doc_id,
                "doctor_name": doc.get("name", "Unknown") if doc else "Unknown",
                "patients_treated": len(improvements),
                "avg_improvement": round(sum(improvements) / len(improvements), 2),
                "positive_outcomes": sum(1 for x in improvements if x > 0),
            })

        return sorted(results, key=lambda x: x["avg_improvement"], reverse=True)

    def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Compute personal analytics for a user."""
        tests = list(self.tests.find({"user_id": user_id}).sort("timestamp", 1))
        if not tests:
            return {"message": "No tests found", "tests_count": 0}

        levels = [t["stress_level"] for t in tests]
        timestamps = [t["timestamp"] for t in tests]

        # Time between tests
        if len(timestamps) >= 2:
            gaps = [(timestamps[i+1] - timestamps[i]).days for i in range(len(timestamps)-1)]
            avg_gap = sum(gaps) / len(gaps)
        else:
            avg_gap = 0

        # Personal best / worst
        best_level = min(levels)
        worst_level = max(levels)

        # Category trends
        category_trends = {}
        if tests[-1].get("responses") and len(tests) >= 2 and tests[0].get("responses"):
            first_r = tests[0]["responses"]
            last_r = tests[-1]["responses"]
            categories = {
                "emotional": [0, 1, 2],
                "physical": [3, 4, 5, 6],
                "cognitive": [7, 8, 9, 10],
                "behavioral": [11, 12, 13],
                "stressors": [14, 15, 16, 17],
            }
            for cat, indices in categories.items():
                first_avg = sum(first_r[i] for i in indices) / len(indices)
                last_avg = sum(last_r[i] for i in indices) / len(indices)
                diff = last_avg - first_avg
                category_trends[cat] = {
                    "first_avg": round(first_avg, 2),
                    "latest_avg": round(last_avg, 2),
                    "change": round(diff, 2),
                    "direction": "improved" if diff < -0.3 else "worsened" if diff > 0.3 else "stable",
                }

        return {
            "tests_count": len(tests),
            "average_stress": round(sum(levels) / len(levels), 2),
            "best_level": best_level,
            "worst_level": worst_level,
            "current_level": levels[-1],
            "avg_days_between_tests": round(avg_gap, 1),
            "category_trends": category_trends,
            "history": [
                {
                    "stress_level": t["stress_level"],
                    "stress_label": t.get("stress_label", ""),
                    "confidence": t.get("confidence_score", 0),
                    "timestamp": t["timestamp"].isoformat() if isinstance(t["timestamp"], datetime) else str(t["timestamp"]),
                }
                for t in tests
            ],
        }

    def smart_doctor_match(self, user_id: str, stress_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Match user to the best doctor based on:
        1. Doctor specialization matching stress profile
        2. Doctor effectiveness scores
        3. Availability
        """
        stress_level = stress_result.get("stress_level", 0)
        category_scores = stress_result.get("category_scores", {})

        # Determine primary stress domain
        if category_scores:
            worst_cat = max(category_scores.items(), key=lambda x: x[1].get("average", 0))[0]
        else:
            worst_cat = "emotional"

        # Map category to specialization preference
        specialization_map = {
            "emotional": ["Psychiatrist", "Clinical Psychologist", "Counselor"],
            "physical": ["General Physician", "Neurologist", "Psychiatrist"],
            "cognitive": ["Clinical Psychologist", "Psychiatrist", "Neurologist"],
            "behavioral": ["Clinical Psychologist", "Counselor", "Psychiatrist"],
            "stressors": ["Counselor", "Clinical Psychologist", "Occupational Therapist"],
        }
        preferred = specialization_map.get(worst_cat, ["Psychiatrist"])

        # Get verified doctors
        doctors = list(self.doctors.find(get_active_verified_doctors_filter()))
        if not doctors:
            return []

        # Doctor effectiveness cache
        effectiveness = self._compute_doctor_effectiveness()
        eff_map = {e["doctor_id"]: e for e in effectiveness}

        scored = []
        for doc in doctors:
            doc_id = str(doc["_id"])
            score = 0.0

            # Specialization match
            spec = doc.get("specialization", "").strip()
            if spec in preferred:
                score += 30 - (preferred.index(spec) * 10)

            # Effectiveness bonus
            eff = eff_map.get(doc_id, {})
            score += eff.get("avg_improvement", 0) * 10
            if eff.get("positive_outcomes", 0) > 3:
                score += 10

            # Availability
            slots = doc.get("available_slots", [])
            score += min(len(slots), 5) * 2

            # Urgency boost for psychiatrists on severe stress
            if stress_level >= 3 and "Psychiatrist" in spec:
                score += 20

            scored.append({
                "doctor_id": doc_id,
                "name": doc.get("name", "Unknown"),
                "specialization": spec,
                "available_slots": slots[:5],
                "match_score": round(score, 1),
                "effectiveness": eff if eff else None,
                "match_reason": f"Best match for {worst_cat} stress" if spec in preferred else "Available",
            })

        return sorted(scored, key=lambda x: x["match_score"], reverse=True)[:5]


def create_analytics_engine(tests_col, users_col, appointments_col, doctors_col):
    """Factory to create an AnalyticsEngine with all collections."""
    return AnalyticsEngine(tests_col, users_col, appointments_col, doctors_col)
