import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import pickle
import os

def generate_training_data(n_samples=1000):
    """
    Generate synthetic training data for stress detection
    Based on 18 CBT questions with responses 1-5
    """
    np.random.seed(42)
    
    data = []
    
    for _ in range(n_samples):
        # Generate responses (1-5) for 18 questions
        # Simulate patterns for different stress levels
        stress_level = np.random.choice([0, 1, 2, 3], p=[0.25, 0.35, 0.25, 0.15])
        
        if stress_level == 0:  # Low stress
            responses = np.random.randint(1, 3, size=18).tolist()
        elif stress_level == 1:  # Moderate stress
            responses = np.random.randint(2, 4, size=18).tolist()
        elif stress_level == 2:  # High stress
            responses = np.random.randint(3, 5, size=18).tolist()
        else:  # Severe stress
            responses = np.random.randint(4, 6, size=18).tolist()
        
        # Add some randomness
        responses = [min(5, max(1, r + np.random.randint(-1, 2))) for r in responses]
        
        data.append(responses + [stress_level])
    
    columns = [f'q{i+1}' for i in range(18)] + ['stress_level']
    df = pd.DataFrame(data, columns=columns)
    
    return df

def train_stress_model():
    """Train Random Forest model for stress detection"""
    print("🤖 Generating training data...")
    df = generate_training_data(n_samples=1000)
    
    # Features and target
    X = df.drop('stress_level', axis=1)
    y = df['stress_level']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print("🎯 Training Random Forest model...")
    # Train Random Forest
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced'
    )
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\n✅ Model Training Complete!")
    print(f"📊 Accuracy: {accuracy:.4f}")
    print("\n📈 Classification Report:")
    print(classification_report(y_test, y_pred, 
                                target_names=['Low', 'Moderate', 'High', 'Severe']))
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': [f'Question {i+1}' for i in range(18)],
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n🔍 Top 5 Most Important Questions:")
    print(feature_importance.head())
    
    # Save model
    model_dir = os.path.dirname(__file__)
    model_path = os.path.join(model_dir, 'stress_model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    print(f"\n💾 Model saved to: {model_path}")
    
    return model

if __name__ == "__main__":
    train_stress_model()
