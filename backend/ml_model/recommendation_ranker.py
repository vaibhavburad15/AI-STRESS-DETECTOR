import hashlib
import os
import pickle
from typing import Any, Dict, List

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline


class RecommendationNNRanker:
    """NN ranker for personalized recommendation ordering."""

    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), "recommendation_ranker_nn.pkl")
        self.model = self._load_or_train_model()

    @staticmethod
    def _sha256_file(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _load_pickle_with_integrity(self, path: str):
        expected_hash = os.getenv("RECOMMENDATION_RANKER_SHA256", "").strip()
        actual_hash = self._sha256_file(path)
        if expected_hash and actual_hash.lower() != expected_hash.lower():
            raise ValueError("Integrity check failed for recommendation ranker model")

        with open(path, "rb") as model_file:
            return pickle.load(model_file)

    def _load_or_train_model(self) -> Pipeline:
        if os.path.exists(self.model_path):
            try:
                return self._load_pickle_with_integrity(self.model_path)
            except Exception:
                pass

        model = self._train_on_synthetic_data()
        with open(self.model_path, "wb") as model_file:
            pickle.dump(model, model_file)
        return model

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
                ("scale", StandardScaler()),
                (
                    "mlp",
                    MLPRegressor(
                        hidden_layer_sizes=(80, 40),
                        activation="relu",
                        alpha=8e-4,
                        random_state=42,
                        max_iter=700,
                        learning_rate_init=8e-4,
                        early_stopping=True,
                        validation_fraction=0.15,
                        n_iter_no_change=20,
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
