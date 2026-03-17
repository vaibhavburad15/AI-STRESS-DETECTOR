from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import pandas as pd

from .audio_features import AUDIO_FEATURE_COLUMNS, extract_audio_features


class AudioStressPredictor:
    """Load a trained audio stress model and score extracted voice features."""

    def __init__(self) -> None:
        model_dir = Path(__file__).resolve().parent
        self.model_path = model_dir / "audio_stress_model.pkl"
        self.meta_path = model_dir / "audio_stress_model_meta.json"
        self.model = None
        self.metadata: Dict[str, Any] = {}
        self._loaded_mtime: float | None = None
        self.stress_labels = {
            0: "Low",
            1: "Moderate",
            2: "High",
            3: "Severe",
        }
        self.load_model()

    def required_features(self) -> list[str]:
        configured = self.metadata.get("features")
        if isinstance(configured, list) and configured:
            return [str(feature_name) for feature_name in configured]
        return list(AUDIO_FEATURE_COLUMNS)

    def load_model(self) -> None:
        if not self.model_path.exists():
            self.model = None
            self.metadata = {}
            self._loaded_mtime = None
            return

        try:
            self.model = joblib.load(self.model_path)
            self._loaded_mtime = self.model_path.stat().st_mtime
        except Exception as exc:
            print(f"Failed to load audio stress model from {self.model_path}: {exc}")
            self.model = None
            self._loaded_mtime = None

        if self.meta_path.exists():
            try:
                self.metadata = json.loads(self.meta_path.read_text(encoding="utf-8"))
            except Exception:
                self.metadata = {}

    def refresh_if_needed(self) -> None:
        if not self.model_path.exists():
            if self.model is not None:
                self.model = None
                self.metadata = {}
                self._loaded_mtime = None
            return

        current_mtime = self.model_path.stat().st_mtime
        if self.model is None or self._loaded_mtime != current_mtime:
            self.load_model()

    def is_available(self) -> bool:
        self.refresh_if_needed()
        return self.model is not None

    def available_feature_count(self, audio_features: Optional[Dict[str, float]]) -> int:
        if not audio_features:
            return 0
        required = self.required_features()
        return sum(1 for feature_name in required if feature_name in audio_features)

    def has_required_features(self, audio_features: Optional[Dict[str, float]]) -> bool:
        return self.available_feature_count(audio_features) == len(self.required_features())

    def _prepare_row(self, audio_features: Dict[str, float]) -> tuple[pd.DataFrame, list[str]]:
        required = self.required_features()
        missing = [feature_name for feature_name in required if feature_name not in audio_features]

        row = {
            feature_name: (
                float(audio_features[feature_name])
                if feature_name in audio_features
                else float("nan")
            )
            for feature_name in required
        }
        return pd.DataFrame([row], columns=required), missing

    def predict_from_features(self, audio_features: Optional[Dict[str, float]]) -> Optional[Dict[str, Any]]:
        self.refresh_if_needed()
        if self.model is None or not audio_features:
            return None

        try:
            X, missing_features = self._prepare_row(audio_features)
            prediction = int(self.model.predict(X)[0])

            probabilities = None
            confidence = 0.0
            if hasattr(self.model, "predict_proba"):
                probabilities = self.model.predict_proba(X)[0]
                confidence = float(max(probabilities))

            return {
                "source": "trained_audio_model",
                "stress_level": prediction,
                "stress_label": self.stress_labels.get(prediction, "Unknown"),
                "confidence": confidence,
                "normalized_stress": round(prediction / 3.0, 4),
                "probabilities": (
                    {
                        self.stress_labels[index]: round(float(probability), 4)
                        for index, probability in enumerate(probabilities)
                    }
                    if probabilities is not None
                    else {}
                ),
                "feature_count": len(self.required_features()),
                "available_feature_count": len(self.required_features()) - len(missing_features),
                "missing_feature_count": len(missing_features),
                "used_imputation": bool(missing_features),
                "model_type": self.metadata.get("model_type", "audio_stress_classifier"),
                "split_method": self.metadata.get("split_method"),
            }
        except Exception as exc:
            print(f"Audio stress prediction failed: {exc}")
            return None

    def predict_from_wav(self, audio_path: str | Path) -> Optional[Dict[str, Any]]:
        self.refresh_if_needed()
        if self.model is None:
            return None

        try:
            features = extract_audio_features(audio_path)
        except Exception as exc:
            print(f"Audio feature extraction failed for {audio_path}: {exc}")
            return None

        result = self.predict_from_features(features)
        if result is None:
            return None

        result["audio_features"] = features
        return result


audio_stress_predictor = AudioStressPredictor()
