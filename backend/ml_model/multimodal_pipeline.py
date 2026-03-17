from typing import Any, Dict, List, Optional

import numpy as np

from .audio_stress_predictor import audio_stress_predictor
from .verbal_nn_scorer import verbal_nn_scorer

FUSION_THRESHOLDS = (0.3, 0.55, 0.8)


class MultimodalStressPipeline:
    """Fuse text, audio, and weak auxiliary signals into a stable stress score."""

    @staticmethod
    def _normalized_text_signal(text_avg: float) -> float:
        return float(np.clip((text_avg - 1.0) / 4.0, 0.0, 1.0))

    @staticmethod
    def _speaking_rate_signal(speaking_rate_wpm: float) -> float:
        return float(np.clip(abs(speaking_rate_wpm - 140.0) / 80.0, 0.0, 1.0))

    @staticmethod
    def _determine_stress_level(fused_signal: float) -> int:
        if fused_signal < FUSION_THRESHOLDS[0]:
            return 0
        if fused_signal < FUSION_THRESHOLDS[1]:
            return 1
        if fused_signal < FUSION_THRESHOLDS[2]:
            return 2
        return 3

    @staticmethod
    def _fusion_margin(fused_signal: float) -> float:
        threshold_distances = [abs(fused_signal - threshold) for threshold in FUSION_THRESHOLDS]
        return float(min(threshold_distances)) if threshold_distances else 0.0

    def _resolve_weights(
        self,
        audio_prediction: Optional[Dict[str, Any]],
        audio_features: Dict[str, float],
    ) -> Dict[str, float]:
        if audio_prediction is not None:
            prediction_confidence = float(np.clip(audio_prediction.get("confidence", 0.0), 0.0, 1.0))
            used_imputation = bool(audio_prediction.get("used_imputation", False))
            if prediction_confidence >= 0.7 and not used_imputation:
                return {
                    "text": 0.55,
                    "audio": 0.3,
                    "sentiment": 0.1,
                    "face": 0.05,
                }
            return {
                "text": 0.62,
                "audio": 0.23,
                "sentiment": 0.1,
                "face": 0.05,
            }

        if audio_features:
            return {
                "text": 0.68,
                "audio": 0.17,
                "sentiment": 0.1,
                "face": 0.05,
            }

        return {
            "text": 0.8,
            "audio": 0.05,
            "sentiment": 0.1,
            "face": 0.05,
        }

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
        text_signal = self._normalized_text_signal(text_avg)
        text_confidence = float(np.clip(text_result.get("avg_confidence", 0.5), 0.0, 1.0))

        audio_features = audio_features or {}
        facial_features = facial_features or {}
        sentiment_features = sentiment_features or {}

        audio_prediction = audio_stress_predictor.predict_from_features(audio_features)
        audio_source = "heuristic_payload"
        audio_signal = float(np.clip(audio_features.get("stress", 0.5), 0.0, 1.0))
        if audio_prediction is not None:
            audio_signal = float(np.clip(audio_prediction["normalized_stress"], 0.0, 1.0))
            audio_source = "trained_audio_model"

        face_stress = float(np.clip(facial_features.get("stress", 0.5), 0.0, 1.0))
        sentiment_neg = float(np.clip(sentiment_features.get("negative", 0.5), 0.0, 1.0))
        speaking_rate_wpm = float(np.clip(audio_features.get("speaking_rate_wpm", 140.0), 60.0, 260.0))
        speaking_rate_signal = self._speaking_rate_signal(speaking_rate_wpm)
        composite_audio_signal = float(np.clip(0.75 * audio_signal + 0.25 * speaking_rate_signal, 0.0, 1.0))

        weights = self._resolve_weights(audio_prediction=audio_prediction, audio_features=audio_features)
        fused_signal = float(
            np.clip(
                weights["text"] * text_signal
                + weights["audio"] * composite_audio_signal
                + weights["sentiment"] * sentiment_neg
                + weights["face"] * face_stress,
                0.0,
                1.0,
            )
        )
        stress_level = self._determine_stress_level(fused_signal)

        audio_confidence = (
            float(np.clip(audio_prediction.get("confidence", 0.0), 0.0, 1.0))
            if audio_prediction is not None
            else (0.35 if audio_features else 0.0)
        )
        margin_confidence = float(np.clip(self._fusion_margin(fused_signal) / 0.2, 0.0, 1.0))
        confidence = float(
            np.clip(
                0.55 * text_confidence
                + 0.25 * audio_confidence
                + 0.2 * margin_confidence,
                0.0,
                1.0,
            )
        )

        adjusted_scores = text_scores[:]
        if confidence >= 0.68 and stress_level >= 2:
            adjusted_scores = [
                int(np.clip(score + (2 if stress_level == 3 else 1), 1, 5))
                for score in adjusted_scores
            ]

        if (
            audio_prediction is not None
            and audio_prediction.get("confidence", 0.0) >= 0.7
            and int(audio_prediction["stress_level"]) >= 2
        ):
            audio_boost = 2 if int(audio_prediction["stress_level"]) == 3 else 1
            adjusted_scores = [int(np.clip(score + audio_boost, 1, 5)) for score in adjusted_scores]
            stress_level = max(stress_level, int(audio_prediction["stress_level"]))

        return {
            "scores": adjusted_scores,
            "multimodal": {
                "enabled": True,
                "method": "weighted_signal_fusion",
                "fused_stress_level": stress_level,
                "fused_confidence": round(confidence, 4),
                "fused_signal": round(fused_signal, 4),
                "text_avg_score": round(text_avg, 3),
                "weights": {name: round(value, 3) for name, value in weights.items()},
                "input_signals": {
                    "text_signal": round(text_signal, 3),
                    "audio_stress": round(audio_signal, 3),
                    "composite_audio_signal": round(composite_audio_signal, 3),
                    "face_stress": round(face_stress, 3),
                    "sentiment_negative": round(sentiment_neg, 3),
                    "speaking_rate_wpm": round(speaking_rate_wpm, 1),
                    "speaking_rate_signal": round(speaking_rate_signal, 3),
                },
                "audio_model": {
                    "available": audio_stress_predictor.is_available(),
                    "used": audio_prediction is not None,
                    "source": audio_source,
                    "feature_coverage": audio_stress_predictor.available_feature_count(audio_features),
                    "required_feature_count": len(audio_stress_predictor.required_features()),
                    "prediction": audio_prediction,
                },
                "text_model": text_result.get("model", "nn_text_mlp"),
                "text_avg_confidence": text_result.get("avg_confidence", 0.0),
            },
        }


multimodal_pipeline = MultimodalStressPipeline()
