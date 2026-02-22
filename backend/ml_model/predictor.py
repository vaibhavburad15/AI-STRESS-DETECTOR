import pickle
import os
import numpy as np
from typing import List, Tuple

class StressPredictor:
    def __init__(self):
        self.model = None
        self.stress_labels = {
            0: "Low",
            1: "Moderate",
            2: "High",
            3: "Severe"
        }
        self.load_model()
    
    def load_model(self):
        """Load the trained model"""
        model_path = os.path.join(os.path.dirname(__file__), 'stress_model.pkl')
        if os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            print("✅ ML Model loaded successfully")
        else:
            print("⚠️ Model not found. Please train the model first.")
    
    def predict(self, responses: List[int]) -> Tuple[int, str, float, List[str]]:
        """
        Predict stress level from questionnaire responses
        
        Args:
            responses: List of 18 integers (1-5)
        
        Returns:
            Tuple of (stress_level, stress_label, confidence, recommendations)
        """
        if self.model is None:
            raise Exception("Model not loaded. Please train the model first.")
        
        if len(responses) != 18:
            raise ValueError(f"Expected 18 responses, got {len(responses)}")
        
        # Validate responses
        if not all(1 <= r <= 5 for r in responses):
            raise ValueError("All responses must be between 1 and 5")
        
        # Prepare input
        X = np.array(responses).reshape(1, -1)
        
        # Predict
        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]
        confidence = float(probabilities[prediction])
        
        stress_label = self.stress_labels[prediction]
        recommendations = self.get_recommendations(prediction, responses)
        
        return prediction, stress_label, confidence, recommendations
    
    def get_recommendations(self, stress_level: int, responses: List[int]) -> List[str]:
        """Generate personalized recommendations based on stress level"""
        recommendations = []
        
        if stress_level == 0:  # Low
            recommendations = [
                "✅ Your stress levels are well managed. Continue your current self-care practices.",
                "💪 Maintain regular exercise and healthy eating habits.",
                "😊 Keep engaging in activities you enjoy.",
                "🧘 Consider preventive stress management techniques like meditation."
            ]
        
        elif stress_level == 1:  # Moderate
            recommendations = [
                "⚠️ You're experiencing moderate stress. It's important to take proactive steps.",
                "🧘‍♀️ Practice daily relaxation techniques (deep breathing, meditation).",
                "💤 Ensure you get 7-8 hours of quality sleep.",
                "🏃‍♂️ Engage in regular physical activity (30 minutes daily).",
                "👥 Talk to friends, family, or a counselor about your concerns."
            ]
        
        elif stress_level == 2:  # High
            recommendations = [
                "🚨 You're experiencing high stress levels. Professional support is recommended.",
                "🩺 Consider scheduling an appointment with a mental health professional.",
                "🧘 Practice stress-reduction techniques multiple times daily.",
                "⏰ Prioritize and organize tasks to reduce overwhelm.",
                "🚫 Limit caffeine and alcohol consumption.",
                "💬 Reach out to your support network immediately."
            ]
        
        else:  # Severe
            recommendations = [
                "⛑️ URGENT: You're experiencing severe stress. Seek professional help immediately.",
                "🏥 Book an appointment with a doctor or mental health professional today.",
                "☎️ Contact a crisis helpline if you're in immediate distress.",
                "👨‍⚕️ Consider speaking with a psychiatrist about your symptoms.",
                "👨‍👩‍👧 Inform trusted family members or friends about how you're feeling.",
                "🛑 Take a break from stressful activities if possible."
            ]
        
        # Add specific recommendations based on high-scoring questions
        if responses[7] >= 4:  # Sleep issues (q8)
            recommendations.append("💤 Focus on improving sleep hygiene - maintain regular sleep schedule.")
        
        if responses[2] >= 4:  # Anxiety (q3)
            recommendations.append("🫁 Practice deep breathing exercises (4-7-8 technique).")
        
        if responses[14] >= 4:  # Social withdrawal (q15)
            recommendations.append("👥 Try to maintain social connections, even briefly.")
        
        return recommendations
    
    def retrain_with_new_data(self, new_responses: List[List[int]], new_labels: List[int]):
        """Retrain model with accumulated user data (for future implementation)"""
        # This would be implemented for continuous learning
        # Currently just a placeholder
        pass

# Global predictor instance
predictor = StressPredictor()
