import os
import pickle
import hashlib
from typing import Any, Dict, List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline


class VerbalResponseNNScorer:
    """Convert natural-language answers into 1-5 stress scores using a lightweight NN."""

    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), "verbal_scorer_nn.pkl")
        self.model: Pipeline | None = None
        self._load_or_train()

    @staticmethod
    def _sha256_file(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _load_pickle_with_integrity(self, path: str):
        expected_hash = os.getenv("VERBAL_SCORER_SHA256", "").strip()
        actual_hash = self._sha256_file(path)
        if expected_hash and actual_hash.lower() != expected_hash.lower():
            raise ValueError("Integrity check failed for verbal scorer model")

        with open(path, "rb") as model_file:
            return pickle.load(model_file)

    def _load_or_train(self) -> None:
        if os.path.exists(self.model_path):
            try:
                self.model = self._load_pickle_with_integrity(self.model_path)
                return
            except Exception:
                self.model = None

        self.model = self._train_model()
        with open(self.model_path, "wb") as f:
            pickle.dump(self.model, f)

    def _train_model(self) -> Pipeline:
        phrases = {
            1: [
                "never", "not at all", "none", "zero", "no stress", "very calm", "very satisfied",
                "i feel fine", "rarely happens", "i am okay",
            ],
            2: [
                "rarely", "slightly", "a little", "not much", "small amount", "once in a while",
                "mild", "hardly", "infrequently", "a bit",
            ],
            3: [
                "sometimes", "moderately", "average", "neutral", "from time to time", "depends",
                "some days", "medium", "mixed", "not sure",
            ],
            4: [
                "often", "frequently", "quite a lot", "regularly", "most days", "usually",
                "very", "high", "it affects me", "many times",
            ],
            5: [
                "always", "extremely", "all the time", "severely", "overwhelming", "constant",
                "unbearable", "very high", "every day", "cannot cope",
            ],
        }

        X: List[str] = []
        y: List[int] = []
        for label, group in phrases.items():
            for phrase in group:
                X.append(phrase)
                y.append(label)

        # Build a larger synthetic set by combining intensifiers and stress terms.
        terms = [
            "anxious", "sad", "irritable", "pain", "fatigue", "sleep", "heartbeat", "focus",
            "negative thoughts", "future", "decisions", "appetite", "social", "overwhelmed",
            "work", "study", "relationship", "financial",
        ]
        intensifiers = {
            1: ["never", "not", "none"],
            2: ["rarely", "slightly"],
            3: ["sometimes", "moderately"],
            4: ["often", "very"],
            5: ["always", "extremely"],
        }
        for label, words in intensifiers.items():
            for w in words:
                for t in terms:
                    X.append(f"{w} {t}")
                    y.append(label)
                    X.append(f"i feel {w} {t}")
                    y.append(label)

        model = Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=3000)),
                (
                    "mlp",
                    MLPClassifier(
                        hidden_layer_sizes=(64, 32),
                        activation="relu",
                        solver="adam",
                        alpha=1e-4,
                        learning_rate_init=1e-3,
                        max_iter=300,
                        random_state=42,
                    ),
                ),
            ]
        )
        model.fit(X, y)
        return model

    def score_responses(self, verbal_responses: List[str]) -> Dict[str, Any]:
        if self.model is None:
            raise RuntimeError("Verbal NN scorer model is not available")

        if len(verbal_responses) != 18:
            raise ValueError(f"Expected 18 responses, got {len(verbal_responses)}")

        texts = [str(r or "").strip().lower() for r in verbal_responses]
        preds = self.model.predict(texts)
        probs = self.model.predict_proba(texts)

        scores: List[int] = []
        confidences: List[float] = []
        for i, pred in enumerate(preds):
            score = int(np.clip(pred, 1, 5))
            # Q15 asks satisfaction. Invert model output for stress direction.
            if i == 14:
                score = 6 - score
            scores.append(score)
            confidences.append(float(np.max(probs[i])))

        return {
            "scores": scores,
            "avg_confidence": round(float(np.mean(confidences)), 4),
            "min_confidence": round(float(np.min(confidences)), 4),
            "model": "nn_text_mlp",
        }


verbal_nn_scorer = VerbalResponseNNScorer()
