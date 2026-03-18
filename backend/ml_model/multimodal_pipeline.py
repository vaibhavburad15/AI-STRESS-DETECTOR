import hashlib
import os
import pickle
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier

from .verbal_nn_scorer import verbal_nn_scorer


class MultimodalStressPipeline:
    """Fuse text, audio, and facial features into robust stress scoring for video endpoint."""

    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), "multimodal_fusion_nn.pkl")
        self.fusion_model = self._load_or_train_model()

    @staticmethod
    def _sha256_file(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _load_pickle_with_integrity(self, path: str):
        expected_hash = os.getenv("MULTIMODAL_FUSION_SHA256", "").strip()
        actual_hash = self._sha256_file(path)
        if expected_hash and actual_hash.lower() != expected_hash.lower():
            raise ValueError("Integrity check failed for multimodal fusion model")

        with open(path, "rb") as model_file:
            return pickle.load(model_file)

    def _load_or_train_model(self) -> Pipeline:
        if os.path.exists(self.model_path):
            try:
                return self._load_pickle_with_integrity(self.model_path)
            except Exception:
                pass

        model = self._train_fusion_model()
        with open(self.model_path, "wb") as model_file:
            pickle.dump(model, model_file)
        return model

    def _train_fusion_model(self) -> Pipeline:
        rng = np.random.default_rng(42)
        X = []
        y = []

        for _ in range(9000):
            text_avg = rng.uniform(1.0, 5.0)
            audio_stress = rng.uniform(0.0, 1.0)
            face_stress = rng.uniform(0.0, 1.0)
            sentiment_neg = rng.uniform(0.0, 1.0)
            speaking_rate = rng.uniform(80, 220) / 220.0
            # Model occasional uncertainty/noisy channels to prevent overfitting.
            channel_noise = rng.normal(0.0, 0.06)

            signal = (
                (text_avg - 1.0) * 0.45
                + audio_stress * 0.20
                + face_stress * 0.20
                + sentiment_neg * 0.10
                + speaking_rate * 0.05
                + channel_noise
            )
            stress_class = int(np.clip(round(signal / 0.75), 0, 3))

            X.append([text_avg, audio_stress, face_stress, sentiment_neg, speaking_rate])
            y.append(stress_class)

        model = Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "mlp",
                    MLPClassifier(
                        hidden_layer_sizes=(64, 32),
                        activation="relu",
                        alpha=5e-4,
                        random_state=42,
                        max_iter=700,
                        learning_rate_init=8e-4,
                        early_stopping=True,
                        validation_fraction=0.15,
                        n_iter_no_change=18,
                    ),
                ),
            ]
        )
        model.fit(np.array(X, dtype=float), np.array(y, dtype=int))
        return model

    def assess(
        self,
        verbal_responses: List[str],
        audio_features: Optional[Dict[str, float]] = None,
        facial_features: Optional[Dict[str, float]] = None,
        sentiment_features: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        text_result = verbal_nn_scorer.score_responses(verbal_responses)
        text_scores = text_result["scores"]
        text_avg = float(np.mean(text_scores))

        audio_features = audio_features or {}
        facial_features = facial_features or {}
        sentiment_features = sentiment_features or {}

        audio_stress = float(np.clip(audio_features.get("stress", 0.5), 0.0, 1.0))
        face_stress = float(np.clip(facial_features.get("stress", 0.5), 0.0, 1.0))
        sentiment_neg = float(np.clip(sentiment_features.get("negative", 0.5), 0.0, 1.0))
        speaking_rate = float(np.clip(audio_features.get("speaking_rate_wpm", 140.0), 60.0, 260.0)) / 220.0

        x = np.array([[text_avg, audio_stress, face_stress, sentiment_neg, speaking_rate]], dtype=float)
        stress_level = int(self.fusion_model.predict(x)[0])
        confidence = float(np.max(self.fusion_model.predict_proba(x)[0]))

        # Keep questionnaire compatibility by deriving 1-5 item scores and shifting by fused class when high certainty.
        adjusted_scores = text_scores[:]
        if confidence >= 0.7 and stress_level >= 2:
            adjusted_scores = [int(np.clip(s + 1, 1, 5)) for s in adjusted_scores]

        return {
            "scores": adjusted_scores,
            "multimodal": {
                "enabled": True,
                "fused_stress_level": stress_level,
                "fused_confidence": round(confidence, 4),
                "text_avg_score": round(text_avg, 3),
                "input_signals": {
                    "audio_stress": round(audio_stress, 3),
                    "face_stress": round(face_stress, 3),
                    "sentiment_negative": round(sentiment_neg, 3),
                    "speaking_rate_norm": round(speaking_rate, 3),
                },
                "text_model": text_result.get("model", "nn_text_mlp"),
                "text_avg_confidence": text_result.get("avg_confidence", 0.0),
            },
        }


multimodal_pipeline = MultimodalStressPipeline()
