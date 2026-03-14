from typing import Any, Dict, List

import numpy as np
from sklearn.neural_network import MLPRegressor


class StressForecasterNN:
    """Autoregressive NN forecaster for short-term stress trajectories."""

    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.model = self._train_synthetic_forecaster()

    def _train_synthetic_forecaster(self) -> MLPRegressor:
        rng = np.random.default_rng(42)
        X = []
        y = []

        for _ in range(3500):
            base = rng.uniform(0.2, 2.8)
            drift = rng.uniform(-0.12, 0.12)
            noise = rng.normal(0, 0.22, size=14)
            seq = []
            current = base
            for t in range(14):
                current = np.clip(current + drift + noise[t], 0.0, 3.0)
                seq.append(current)

            for i in range(self.window_size, len(seq)):
                X.append(seq[i - self.window_size:i])
                y.append(seq[i])

        X_arr = np.array(X, dtype=float)
        y_arr = np.array(y, dtype=float)

        model = MLPRegressor(
            hidden_layer_sizes=(64, 32),
            random_state=42,
            max_iter=500,
            learning_rate_init=1e-3,
        )
        model.fit(X_arr, y_arr)
        return model

    def forecast_levels(self, levels: List[float], horizon: int = 3) -> Dict[str, Any]:
        clean = [float(np.clip(x, 0.0, 3.0)) for x in levels]
        if len(clean) < 2:
            return {
                "method": "nn_autoregressive",
                "status": "insufficient_data",
                "required_min_points": 2,
                "predictions": [],
            }

        history = clean[:]
        padded = history[-self.window_size:]
        while len(padded) < self.window_size:
            padded.insert(0, padded[0])

        preds = []
        for step in range(max(1, int(horizon))):
            x = np.array([padded[-self.window_size:]], dtype=float)
            next_val = float(np.clip(self.model.predict(x)[0], 0.0, 3.0))
            preds.append(
                {
                    "step": step + 1,
                    "predicted_level": round(next_val, 3),
                    "predicted_label": self._label_for_level(next_val),
                }
            )
            padded.append(next_val)

        variance = float(np.var(history[-min(8, len(history)) :]))
        confidence = float(np.clip(1.0 - min(variance / 2.5, 0.8), 0.2, 0.95))

        return {
            "method": "nn_autoregressive",
            "status": "ok",
            "horizon": int(horizon),
            "confidence": round(confidence, 3),
            "predictions": preds,
        }

    @staticmethod
    def _label_for_level(level: float) -> str:
        if level < 0.75:
            return "Low"
        if level < 1.75:
            return "Moderate"
        if level < 2.5:
            return "High"
        return "Severe"


stress_forecaster = StressForecasterNN()
