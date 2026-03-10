import os
import pickle
from typing import List, Tuple

import numpy as np


class StressPredictor:
    def __init__(self):
        self.model = None
        self.model_path = os.path.join(os.path.dirname(__file__), "stress_model.pkl")
        self.stress_labels = {
            0: "Low",
            1: "Moderate",
            2: "High",
            3: "Severe",
        }
        self.load_model()

    def load_model(self):
        """Load the trained model, retraining automatically if the pickle is invalid."""
        if not os.path.exists(self.model_path):
            print("ML model file not found. Training a new model.")
            self._retrain_model()
            return

        try:
            with open(self.model_path, "rb") as file:
                self.model = pickle.load(file)
            print("ML model loaded successfully")
        except Exception as exc:
            print(f"Failed to load ML model from {self.model_path}: {exc}")
            print("Attempting to retrain and replace the invalid model file.")
            self._retrain_model()

    def _retrain_model(self):
        """Retrain the model from the training dataset and persist a fresh pickle."""
        from .train_model import train_stress_model

        self.model = train_stress_model()

    def predict(self, responses: List[int]) -> Tuple[int, str, float, List[str]]:
        """
        Predict stress level from questionnaire responses.

        Args:
            responses: List of 18 integers (1-5)

        Returns:
            Tuple of (stress_level, stress_label, confidence, recommendations)
        """
        if self.model is None:
            raise Exception("Model not loaded. Please train the model first.")

        if len(responses) != 18:
            raise ValueError(f"Expected 18 responses, got {len(responses)}")

        if not all(1 <= r <= 5 for r in responses):
            raise ValueError("All responses must be between 1 and 5")

        X = np.array(responses).reshape(1, -1)

        prediction = int(self.model.predict(X)[0])
        probabilities = self.model.predict_proba(X)[0]
        confidence = float(probabilities[prediction])

        stress_label = self.stress_labels[prediction]
        recommendations = self.get_recommendations(prediction, responses)

        return prediction, stress_label, confidence, recommendations

    def get_recommendations(self, stress_level: int, responses: List[int]) -> List[str]:
        """Generate personalized recommendations based on stress level."""
        if stress_level == 0:
            recommendations = [
                "Your stress levels appear well managed. Keep your current self-care routine.",
                "Maintain regular exercise and healthy eating habits.",
                "Keep spending time on activities you enjoy.",
                "Use preventive stress-management techniques such as meditation.",
            ]
        elif stress_level == 1:
            recommendations = [
                "You are experiencing moderate stress. Take early action now.",
                "Practice daily relaxation techniques such as breathing or meditation.",
                "Aim for 7 to 8 hours of quality sleep.",
                "Try regular physical activity for at least 30 minutes a day.",
                "Talk with friends, family, or a counselor about your concerns.",
            ]
        elif stress_level == 2:
            recommendations = [
                "You are experiencing high stress. Professional support is recommended.",
                "Consider scheduling an appointment with a mental health professional.",
                "Practice stress-reduction techniques multiple times a day.",
                "Prioritize and organize tasks to reduce overwhelm.",
                "Limit caffeine and alcohol intake.",
                "Reach out to your support network promptly.",
            ]
        else:
            recommendations = [
                "Urgent: you are experiencing severe stress. Seek professional help immediately.",
                "Book an appointment with a doctor or mental health professional today.",
                "Contact a crisis helpline if you are in immediate distress.",
                "Consider speaking with a psychiatrist about your symptoms.",
                "Tell trusted family members or friends how you are feeling.",
                "Step away from stressful activities if possible.",
            ]

        # Questionnaire mapping is zero-based here:
        # 5  -> sleep issues
        # 2  -> irritability/anger
        # 12 -> avoiding social interactions
        # 15 -> work/study stress
        if responses[5] >= 4:
            recommendations.append(
                "Focus on improving sleep hygiene and keeping a regular sleep schedule."
            )

        if responses[2] >= 4:
            recommendations.append(
                "Practice relaxation techniques when you feel irritable or angry."
            )

        if responses[12] >= 4:
            recommendations.append(
                "Try to maintain social connection, even if only briefly."
            )

        if responses[15] >= 4:
            recommendations.append(
                "Review your work-life balance and set healthier boundaries."
            )

        return recommendations

    def retrain_with_new_data(self, new_responses: List[List[int]], new_labels: List[int]):
        """Placeholder for future continuous-learning support."""
        _ = (new_responses, new_labels)
        pass


predictor = StressPredictor()
