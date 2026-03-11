import json
import os
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

EXPECTED_FEATURE_COLUMNS = [f"q{i+1}" for i in range(18)]
TARGET_COLUMN = "stress_level"


def generate_training_data(n_samples=1000):
    """
    Generate synthetic training data for stress detection.
    Based on 18 CBT questions with responses 1-5.
    """
    np.random.seed(42)

    data = []

    for _ in range(n_samples):
        # Generate responses (1-5) for 18 questions.
        # Simulate patterns for different stress levels.
        stress_level = np.random.choice([0, 1, 2, 3], p=[0.25, 0.35, 0.25, 0.15])

        if stress_level == 0:  # Low stress
            responses = np.random.randint(1, 3, size=18).tolist()
        elif stress_level == 1:  # Moderate stress
            responses = np.random.randint(2, 4, size=18).tolist()
        elif stress_level == 2:  # High stress
            responses = np.random.randint(3, 5, size=18).tolist()
        else:  # Severe stress
            responses = np.random.randint(4, 6, size=18).tolist()

        # Add small randomness while keeping answers in range 1..5.
        responses = [min(5, max(1, r + np.random.randint(-1, 2))) for r in responses]

        data.append(responses + [stress_level])

    columns = EXPECTED_FEATURE_COLUMNS + [TARGET_COLUMN]
    return pd.DataFrame(data, columns=columns)


def load_training_data(dataset_path=None, fallback_samples=1000):
    """
    Load training data from CSV when available.
    Fallback to synthetic data only if dataset is missing.
    """
    if dataset_path and os.path.exists(dataset_path):
        print(f"Loading training data from CSV: {dataset_path}")
        df = pd.read_csv(dataset_path)

        expected_columns = EXPECTED_FEATURE_COLUMNS + [TARGET_COLUMN]
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Dataset is missing required columns: {missing_columns}")

        df = df[expected_columns]
        print(f"Loaded {len(df)} rows from dataset.")
        return df

    print(
        "Dataset file not found. Falling back to synthetic training data "
        f"({fallback_samples} rows)."
    )
    return generate_training_data(n_samples=fallback_samples)


def train_stress_model(dataset_filename="stress_training_dataset_100k.csv"):
    """Train Random Forest model for stress detection."""
    model_dir = os.path.dirname(__file__)
    dataset_path = os.path.join(model_dir, dataset_filename) if dataset_filename else None
    df = load_training_data(dataset_path=dataset_path, fallback_samples=1000)

    # Features and target
    X = df.drop(TARGET_COLUMN, axis=1)
    y = df[TARGET_COLUMN]

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training rows: {len(X_train)}, Test rows: {len(X_test)}")
    print("Training Random Forest model...")

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print("\nModel training complete.")
    print(f"Accuracy: {accuracy:.4f}")
    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            y_pred,
            target_names=["Low", "Moderate", "High", "Severe"],
        )
    )

    feature_importance = pd.DataFrame(
        {
            "feature": [f"Question {i+1}" for i in range(18)],
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)

    print("\nTop 5 most important questions:")
    print(feature_importance.head())

    model_path = os.path.join(model_dir, "stress_model.pkl")
    with open(model_path, "wb") as file:
        pickle.dump(model, file)

    metadata = {
        "dataset_path": dataset_path if dataset_path and os.path.exists(dataset_path) else None,
        "total_rows": int(len(df)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "features": EXPECTED_FEATURE_COLUMNS,
        "target": TARGET_COLUMN,
        "model_type": type(model).__name__,
        "n_estimators": int(model.n_estimators),
        "random_state": 42,
        "accuracy": float(accuracy),
    }

    metadata_path = os.path.join(model_dir, "stress_model_meta.json")
    with open(metadata_path, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    print(f"\nModel saved to: {model_path}")
    print(f"Training metadata saved to: {metadata_path}")

    return model


if __name__ == "__main__":
    train_stress_model()
