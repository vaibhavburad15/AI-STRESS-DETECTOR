from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from .audio_features import (
    AUDIO_FEATURE_COLUMNS,
    STRESS_LEVEL_LABELS,
    aggregate_predictions,
    apply_feature_weights,
    predict_chunks,
    preprocess_audio,
)
from .sklearn_pickle import load_sklearn_joblib


class AudioStressPredictor:
    """Load the trained voice stress model and run weighted chunked inference."""

    def __init__(self) -> None:
        model_dir = Path(__file__).resolve().parent
        self.model_path = model_dir / "audio_stress_model.pkl"
        self.scaler_path = model_dir / "audio_stress_scaler.pkl"
        self.meta_path = model_dir / "audio_stress_model_meta.json"
        self.model = None
        self.scaler = None
        self.metadata: Dict[str, Any] = {}
        self._loaded_model_mtime: float | None = None
        self._loaded_scaler_mtime: float | None = None
        self._load_warning_logged = False
        self.load_model()

    def required_features(self) -> list[str]:
        configured = self.metadata.get("features")
        if isinstance(configured, list) and configured:
            return [str(feature_name) for feature_name in configured]
        return list(AUDIO_FEATURE_COLUMNS)

    def fill_values(self) -> Dict[str, float]:
        configured = self.metadata.get("feature_fill_values")
        if isinstance(configured, dict):
            return {str(key): float(value) for key, value in configured.items()}
        return {feature_name: 0.0 for feature_name in self.required_features()}

    def classes(self) -> list[int]:
        configured = self.metadata.get("classes")
        if isinstance(configured, list) and configured:
            return [int(class_id) for class_id in configured]
        return [0, 1, 2]

    def load_model(self) -> None:
        if not self.model_path.exists() or not self.scaler_path.exists():
            self.model = None
            self.scaler = None
            self.metadata = {}
            self._loaded_model_mtime = None
            self._loaded_scaler_mtime = None
            return

        try:
            self.model = load_sklearn_joblib(self.model_path)
            self.scaler = load_sklearn_joblib(self.scaler_path)
            self._loaded_model_mtime = self.model_path.stat().st_mtime
            self._loaded_scaler_mtime = self.scaler_path.stat().st_mtime
            self._load_warning_logged = False
        except Exception as exc:
            if exc.__class__.__name__ == "InconsistentVersionWarning":
                if not self._load_warning_logged:
                    print(
                        "Audio stress model assets were trained with a different "
                        "scikit-learn version; using heuristic audio fallback."
                    )
                    self._load_warning_logged = True
            else:
                print(f"Failed to load audio stress model assets: {exc}")
            self.model = None
            self.scaler = None
            self._loaded_model_mtime = None
            self._loaded_scaler_mtime = None

        if self.meta_path.exists():
            try:
                self.metadata = json.loads(self.meta_path.read_text(encoding="utf-8"))
            except Exception:
                self.metadata = {}

    def refresh_if_needed(self) -> None:
        if not self.model_path.exists() or not self.scaler_path.exists():
            if self.model is not None or self.scaler is not None:
                self.model = None
                self.scaler = None
                self.metadata = {}
                self._loaded_model_mtime = None
                self._loaded_scaler_mtime = None
            return

        current_model_mtime = self.model_path.stat().st_mtime
        current_scaler_mtime = self.scaler_path.stat().st_mtime
        if (
            self.model is None
            or self.scaler is None
            or self._loaded_model_mtime != current_model_mtime
            or self._loaded_scaler_mtime != current_scaler_mtime
        ):
            self.load_model()

    def is_available(self) -> bool:
        self.refresh_if_needed()
        return self.model is not None and self.scaler is not None

    def available_feature_count(self, audio_features: Optional[Dict[str, float]]) -> int:
        if not audio_features:
            return 0
        required = self.required_features()
        return sum(1 for feature_name in required if feature_name in audio_features)

    def has_required_features(self, audio_features: Optional[Dict[str, float]]) -> bool:
        return self.available_feature_count(audio_features) == len(self.required_features())

    def _prepare_feature_row(self, audio_features: Dict[str, float]) -> tuple[np.ndarray, list[str]]:
        required = self.required_features()
        fill_values = self.fill_values()
        missing = [feature_name for feature_name in required if feature_name not in audio_features]
        row = np.asarray(
            [
                float(audio_features.get(feature_name, fill_values.get(feature_name, 0.0)))
                for feature_name in required
            ],
            dtype=np.float32,
        )
        return row.reshape(1, -1), missing

    def predict_from_features(self, audio_features: Optional[Dict[str, float]]) -> Optional[Dict[str, Any]]:
        self.refresh_if_needed()
        if self.model is None or self.scaler is None or not audio_features:
            return None

        try:
            raw_row, missing_features = self._prepare_feature_row(audio_features)
            scaled_row = self.scaler.transform(raw_row)
            weighted_row = apply_feature_weights(scaled_row, self.required_features())

            probabilities = self.model.predict_proba(weighted_row)[0]
            class_ids = self.classes()
            predicted_class = int(class_ids[int(np.argmax(probabilities))])
            coverage = 1.0 - (len(missing_features) / max(len(self.required_features()), 1))
            base_confidence = float(np.max(probabilities))
            adjusted_confidence = float(base_confidence * (0.55 + (0.45 * coverage)))
            max_class = max(class_ids) if class_ids else 1
            normalized_stress = float(
                np.sum(
                    [
                        int(class_id) * float(probability)
                        for class_id, probability in zip(class_ids, probabilities)
                    ]
                )
                / max(max_class, 1)
            )

            return {
                "source": "feature_payload",
                "stress_level": predicted_class,
                "stress_label": STRESS_LEVEL_LABELS.get(predicted_class, "Unknown"),
                "confidence": round(adjusted_confidence, 4),
                "normalized_stress": round(normalized_stress, 4),
                "probabilities": {
                    STRESS_LEVEL_LABELS.get(int(class_id), str(int(class_id))): round(float(probability), 4)
                    for class_id, probability in zip(class_ids, probabilities)
                },
                "feature_count": len(self.required_features()),
                "available_feature_count": len(self.required_features()) - len(missing_features),
                "missing_feature_count": len(missing_features),
                "used_imputation": bool(missing_features),
                "model_type": self.metadata.get("model_type", "voice_stress_classifier"),
                "selected_model_name": self.metadata.get("selected_model_name"),
            }
        except Exception as exc:
            print(f"Audio stress prediction from features failed: {exc}")
            return None

    def predict_from_wav(self, audio_path: str | Path) -> Optional[Dict[str, Any]]:
        self.refresh_if_needed()
        if self.model is None or self.scaler is None:
            return None

        try:
            signal, sample_rate = preprocess_audio(audio_path)
            chunk_predictions = predict_chunks(
                signal=signal,
                sample_rate=sample_rate,
                model=self.model,
                scaler=self.scaler,
                feature_columns=self.required_features(),
                model_classes=self.classes(),
                fill_values=self.fill_values(),
            )
            aggregated_prediction = aggregate_predictions(
                chunk_predictions=chunk_predictions,
                model_classes=self.classes(),
            )

            class_ids = self.classes()
            max_class = max(class_ids) if class_ids else 1
            probability_values = [
                float(aggregated_prediction["probabilities"][STRESS_LEVEL_LABELS[int(class_id)]])
                for class_id in class_ids
            ]
            normalized_stress = float(
                np.sum(
                    [
                        int(class_id) * probability
                        for class_id, probability in zip(class_ids, probability_values)
                    ]
                )
                / max(max_class, 1)
            )

            aggregated_prediction["source"] = "chunk_weighted_audio_model"
            aggregated_prediction["normalized_stress"] = round(normalized_stress, 4)
            aggregated_prediction["model_type"] = self.metadata.get("model_type", "voice_stress_classifier")
            aggregated_prediction["selected_model_name"] = self.metadata.get("selected_model_name")
            aggregated_prediction["details"]["sampling_rate"] = sample_rate
            aggregated_prediction["details"]["chunk_duration_seconds"] = 2.5
            aggregated_prediction["details"]["feature_count"] = len(self.required_features())
            return aggregated_prediction
        except Exception as exc:
            print(f"Audio stress prediction from wav failed for {audio_path}: {exc}")
            return None


audio_stress_predictor = AudioStressPredictor()
