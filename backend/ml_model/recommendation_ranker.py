from typing import Any, Dict, List

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline


class RecommendationNNRanker:
    """NN ranker for personalized recommendation ordering."""

    def __init__(self):
        self.model = self._train_on_synthetic_data()

    def _train_on_synthetic_data(self) -> Pipeline:
        rows: List[Dict[str, Any]] = []
        y: List[float] = []

        for stress_level in range(4):
            for category in ["immediate", "daily", "weekly", "lifestyle", "professional", "personalized"]:
                for difficulty in ["easy", "medium", "hard"]:
                    for effectiveness in [60, 75, 85, 95]:
                        for age in [18, 30, 45, 60]:
                            for priority in [1, 2, 3, 4]:
                                row = {
                                    "stress_level": stress_level,
                                    "category": category,
                                    "difficulty": difficulty,
                                    "effectiveness": effectiveness,
                                    "age": age,
                                    "priority": priority,
                                }
                                rows.append(row)

                                score = 0.0
                                score += effectiveness * 0.4
                                score += (5 - priority) * 7
                                score += stress_level * 8
                                if category == "professional" and stress_level >= 2:
                                    score += 18
                                if category == "immediate" and stress_level >= 2:
                                    score += 12
                                if category == "lifestyle" and stress_level <= 1:
                                    score += 8
                                if difficulty == "easy":
                                    score += 4
                                if difficulty == "hard" and stress_level == 3:
                                    score -= 10
                                if age >= 50 and difficulty == "hard":
                                    score -= 6
                                y.append(score)

        model = Pipeline(
            [
                ("vec", DictVectorizer(sparse=False)),
                (
                    "mlp",
                    MLPRegressor(
                        hidden_layer_sizes=(48, 24),
                        random_state=42,
                        max_iter=400,
                        learning_rate_init=1e-3,
                    ),
                ),
            ]
        )
        model.fit(rows, y)
        return model

    def rank(
        self,
        items: List[Dict[str, Any]],
        user_data: Dict[str, Any],
        stress_result: Dict[str, Any],
        category: str,
    ) -> List[Dict[str, Any]]:
        if not items:
            return []

        stress_level = int(stress_result.get("stress_level", 0))
        age = int(user_data.get("age") or 30)

        features: List[Dict[str, Any]] = []
        for item in items:
            features.append(
                {
                    "stress_level": stress_level,
                    "category": category,
                    "difficulty": str(item.get("difficulty", "medium")),
                    "effectiveness": float(item.get("effectiveness", 70)),
                    "age": age,
                    "priority": int(item.get("priority", 3)),
                }
            )

        preds = self.model.predict(features)
        ranked = []
        for item, score in zip(items, preds):
            updated = dict(item)
            updated["nn_rank_score"] = round(float(score), 3)
            ranked.append(updated)

        ranked.sort(key=lambda x: x.get("nn_rank_score", 0.0), reverse=True)
        return ranked


recommendation_ranker = RecommendationNNRanker()
