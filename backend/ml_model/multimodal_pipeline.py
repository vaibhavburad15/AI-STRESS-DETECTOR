from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.neural_network import MLPClassifier

from .verbal_nn_scorer import verbal_nn_scorer


class MultimodalStressPipeline:
    """Fuse text, audio, and facial features into robust stress scoring for video endpoint."""

    def __init__(self):
        self.fusion_model = self._train_fusion_model()

    def _train_fusion_model(self) -> MLPClassifier:
        rng = np.random.default_rng(42)
        X = []
        y = []

        for _ in range(5000):
            text_avg = rng.uniform(1.0, 5.0)
            audio_stress = rng.uniform(0.0, 1.0)
            face_stress = rng.uniform(0.0, 1.0)
            sentiment_neg = rng.uniform(0.0, 1.0)
            speaking_rate = rng.uniform(80, 220) / 220.0

            signal = (
                (text_avg - 1.0) * 0.45
                + audio_stress * 0.20
                + face_stress * 0.20
                + sentiment_neg * 0.10
                + speaking_rate * 0.05
            )
            stress_class = int(np.clip(round(signal / 0.75), 0, 3))

            X.append([text_avg, audio_stress, face_stress, sentiment_neg, speaking_rate])
            y.append(stress_class)

        model = MLPClassifier(
            hidden_layer_sizes=(32, 16),
            random_state=42,
            max_iter=400,
            learning_rate_init=1e-3,
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
