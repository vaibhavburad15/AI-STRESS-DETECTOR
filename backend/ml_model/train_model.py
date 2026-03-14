import json
import os
import pickle
import hashlib

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.calibration import CalibratedClassifierCV

EXPECTED_FEATURE_COLUMNS = [f"q{i+1}" for i in range(18)]
TARGET_COLUMN = "stress_level"


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_training_data(n_samples=1000):
    """
    Generate synthetic training data for stress detection.
    Based on 18 CBT questions with responses 1-5.
    """
    np.random.seed(42)

    data = []

    for _ in range(n_samples):
        stress_level = np.random.choice([0, 1, 2, 3], p=[0.25, 0.35, 0.25, 0.15])

        if stress_level == 0:
            responses = np.random.randint(1, 3, size=18).tolist()
        elif stress_level == 1:
            responses = np.random.randint(2, 4, size=18).tolist()
        elif stress_level == 2:
            responses = np.random.randint(3, 5, size=18).tolist()
        else:
            responses = np.random.randint(4, 6, size=18).tolist()

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
    """Train an ensemble model (RF + GBM + LR stacking) for stress detection."""
    model_dir = os.path.dirname(__file__)
    dataset_path = os.path.join(model_dir, dataset_filename) if dataset_filename else None
    df = load_training_data(dataset_path=dataset_path, fallback_samples=1000)

    X = df.drop(TARGET_COLUMN, axis=1)
    y = df[TARGET_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training rows: {len(X_train)}, Test rows: {len(X_test)}")

    # --- Individual models ---
    rf = RandomForestClassifier(
        n_estimators=150, max_depth=12, random_state=42, class_weight="balanced",
    )
    gbm = GradientBoostingClassifier(
        n_estimators=150, max_depth=6, learning_rate=0.1, random_state=42,
    )
    lr = LogisticRegression(
        max_iter=1000, random_state=42, class_weight="balanced", multi_class="multinomial",
    )

    # --- Ensemble via soft voting ---
    print("Training ensemble model (RF + GBM + LR)...")
    ensemble = VotingClassifier(
        estimators=[("rf", rf), ("gbm", gbm), ("lr", lr)],
        voting="soft",
        weights=[2, 2, 1],
    )
    ensemble.fit(X_train, y_train)

    # --- Calibrate probabilities ---
    print("Calibrating probabilities...")
    calibrated = CalibratedClassifierCV(ensemble, cv=3, method="isotonic")
    calibrated.fit(X_train, y_train)

    y_pred = calibrated.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    # Cross-validation on the base ensemble
    cv_scores = cross_val_score(ensemble, X, y, cv=5, scoring="accuracy")

    print("\nModel training complete.")
    print(f"Test Accuracy: {accuracy:.4f}")
    print(f"5-Fold CV Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
    print("\nClassification report:")
    print(
        classification_report(
            y_test, y_pred, target_names=["Low", "Moderate", "High", "Severe"],
        )
    )

    # Feature importance from the RF sub-model
    rf_model = ensemble.named_estimators_["rf"]
    feature_importance = pd.DataFrame(
        {
            "feature": [f"Question {i+1}" for i in range(18)],
            "importance": rf_model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)

    print("\nTop 5 most important questions:")
    print(feature_importance.head())

    # --- Save the calibrated ensemble ---
    model_path = os.path.join(model_dir, "stress_model.pkl")
    with open(model_path, "wb") as file:
        pickle.dump(calibrated, file)

    # --- Save the bare RF for SHAP (TreeExplainer needs a tree model) ---
    shap_model_path = os.path.join(model_dir, "stress_model_shap.pkl")
    with open(shap_model_path, "wb") as file:
        pickle.dump(rf_model, file)

    model_sha256 = _sha256_file(model_path)
    shap_model_sha256 = _sha256_file(shap_model_path)

    metadata = {
        "dataset_path": dataset_path if dataset_path and os.path.exists(dataset_path) else None,
        "total_rows": int(len(df)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "features": EXPECTED_FEATURE_COLUMNS,
        "target": TARGET_COLUMN,
        "model_type": "CalibratedEnsemble(RF+GBM+LR)",
        "ensemble_weights": [2, 2, 1],
        "rf_n_estimators": 150,
        "gbm_n_estimators": 150,
        "random_state": 42,
        "accuracy": float(accuracy),
        "cv_accuracy_mean": float(cv_scores.mean()),
        "cv_accuracy_std": float(cv_scores.std()),
        "model_sha256": model_sha256,
        "shap_model_sha256": shap_model_sha256,
        "feature_importance": {
            f"q{i+1}": float(rf_model.feature_importances_[i]) for i in range(18)
        },
    }

    metadata_path = os.path.join(model_dir, "stress_model_meta.json")
    with open(metadata_path, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    print(f"\nEnsemble model saved to: {model_path}")
    print(f"SHAP-compatible RF saved to: {shap_model_path}")
    print(f"Training metadata saved to: {metadata_path}")

    return calibrated


if __name__ == "__main__":
    train_stress_model()
