from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import joblib
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, VotingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit, StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

try:
    from sklearn.model_selection import StratifiedGroupKFold
except ImportError:
    StratifiedGroupKFold = None

try:
    from .audio_dataset_tools import build_feature_dataset_from_manifest
    from .audio_features import AUDIO_FEATURE_COLUMNS
except ImportError:
    from audio_dataset_tools import build_feature_dataset_from_manifest
    from audio_features import AUDIO_FEATURE_COLUMNS


def build_audio_classifier(random_state: int = 42) -> VotingClassifier:
    rf = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=300,
                    max_depth=18,
                    min_samples_leaf=2,
                    class_weight="balanced_subsample",
                    random_state=random_state,
                ),
            ),
        ]
    )
    et = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "clf",
                ExtraTreesClassifier(
                    n_estimators=300,
                    max_depth=18,
                    min_samples_leaf=2,
                    class_weight="balanced",
                    random_state=random_state,
                ),
            ),
        ]
    )
    lr = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=3000,
                    class_weight="balanced",
                    random_state=random_state,
                ),
            ),
        ]
    )

    return VotingClassifier(
        estimators=[("rf", rf), ("et", et), ("lr", lr)],
        voting="soft",
        weights=[3, 2, 1],
    )


def build_candidate_models(random_state: int = 42) -> Dict[str, object]:
    return {
        "ensemble_v1": build_audio_classifier(random_state=random_state),
        "svc_rbf_v1": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "clf",
                    SVC(
                        C=3.0,
                        gamma="scale",
                        class_weight="balanced",
                        probability=True,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "extra_trees_v1": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "clf",
                    ExtraTreesClassifier(
                        n_estimators=500,
                        max_depth=None,
                        min_samples_leaf=1,
                        class_weight="balanced",
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "logreg_v1": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=4000,
                        class_weight="balanced",
                        random_state=random_state,
                    ),
                ),
            ]
        ),
    }


def _has_explicit_split(feature_df: pd.DataFrame) -> bool:
    if "split" not in feature_df.columns:
        return False
    normalized = feature_df["split"].fillna("").astype(str).str.lower().str.strip()
    return normalized.isin({"train", "training"}).any() and normalized.isin(
        {"test", "testing", "eval", "evaluation", "val", "validation"}
    ).any()


def _split_dataset(
    feature_df: pd.DataFrame,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    if _has_explicit_split(feature_df):
        normalized = feature_df["split"].fillna("").astype(str).str.lower().str.strip()
        train_df = feature_df.loc[normalized.isin({"train", "training"})].copy()
        test_df = feature_df.loc[
            normalized.isin({"test", "testing", "eval", "evaluation", "val", "validation"})
        ].copy()
        if not train_df.empty and not test_df.empty:
            return train_df, test_df, "manifest_split"

    speaker_ids = feature_df["speaker_id"].fillna("").astype(str).str.strip()
    unique_speakers = speaker_ids[speaker_ids != ""].nunique()
    if unique_speakers >= 8:
        all_classes = set(feature_df["stress_level"].astype(int).tolist())
        for seed_offset in range(10):
            splitter = GroupShuffleSplit(
                n_splits=1,
                test_size=0.2,
                random_state=random_state + seed_offset,
            )
            train_idx, test_idx = next(
                splitter.split(feature_df, feature_df["stress_level"], groups=speaker_ids)
            )
            train_df = feature_df.iloc[train_idx].copy()
            test_df = feature_df.iloc[test_idx].copy()
            if set(train_df["stress_level"].astype(int).tolist()) == all_classes and set(
                test_df["stress_level"].astype(int).tolist()
            ) == all_classes:
                return train_df, test_df, "group_shuffle_split"

    train_df, test_df = train_test_split(
        feature_df,
        test_size=0.2,
        stratify=feature_df["stress_level"],
        random_state=random_state,
    )
    return train_df.copy(), test_df.copy(), "stratified_random_split"


def _compute_cv_scores(
    model: object,
    X: pd.DataFrame,
    y: pd.Series,
    groups: Optional[pd.Series],
    random_state: int = 42,
) -> Dict[str, object]:
    class_counts = y.value_counts()
    min_class_count = int(class_counts.min()) if not class_counts.empty else 0

    if groups is not None:
        non_empty_groups = groups.fillna("").astype(str).str.strip()
        unique_groups = non_empty_groups[non_empty_groups != ""].nunique()
        if unique_groups >= 6 and StratifiedGroupKFold is not None:
            n_splits = min(5, unique_groups)
            if n_splits >= 3:
                try:
                    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
                    scores = cross_val_score(model, X, y, cv=cv, groups=non_empty_groups, scoring="accuracy")
                    return {
                        "method": "stratified_group_kfold",
                        "scores": [float(score) for score in scores],
                        "mean": float(scores.mean()),
                        "std": float(scores.std()),
                    }
                except Exception:
                    pass

    if min_class_count >= 3:
        n_splits = min(5, min_class_count)
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
        scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
        return {
            "method": "stratified_kfold",
            "scores": [float(score) for score in scores],
            "mean": float(scores.mean()),
            "std": float(scores.std()),
        }

    return {
        "method": "not_run",
        "scores": [],
        "mean": None,
        "std": None,
    }


def _extract_feature_importance(
    model: object,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    random_state: int = 42,
) -> Dict[str, float]:
    feature_names = list(X_test.columns)
    try:
        result = permutation_importance(
            model,
            X_test,
            y_test,
            n_repeats=10,
            random_state=random_state,
            scoring="balanced_accuracy",
        )
        ranked = sorted(
            zip(feature_names, result.importances_mean),
            key=lambda item: item[1],
            reverse=True,
        )
        return {name: float(value) for name, value in ranked}
    except Exception:
        return {name: 0.0 for name in feature_names}


def train_audio_stress_model(
    manifest_csv: str | Path | None = None,
    dataset_root: str | Path | None = None,
    cached_features_csv: str | Path | None = None,
    model_out: str | Path | None = None,
    metadata_out: str | Path | None = None,
    skip_failed: bool = False,
    random_state: int = 42,
) -> object:
    model_dir = Path(__file__).resolve().parent
    model_out = Path(model_out or model_dir / "audio_stress_model.pkl")
    metadata_out = Path(metadata_out or model_dir / "audio_stress_model_meta.json")

    if cached_features_csv:
        feature_df = pd.read_csv(cached_features_csv)
        feature_source = str(Path(cached_features_csv).resolve())
    elif manifest_csv:
        feature_df = build_feature_dataset_from_manifest(
            manifest_csv=manifest_csv,
            output_csv=None,
            dataset_root=dataset_root,
            skip_failed=skip_failed,
        )
        feature_source = str(Path(manifest_csv).resolve())
    else:
        raise ValueError("Provide either --features-csv or --manifest to train the audio model.")

    missing_features = [column for column in AUDIO_FEATURE_COLUMNS if column not in feature_df.columns]
    if missing_features:
        raise ValueError(f"Feature dataset is missing audio columns: {missing_features}")

    train_df, test_df, split_method = _split_dataset(feature_df, random_state=random_state)

    X_train = train_df[AUDIO_FEATURE_COLUMNS]
    y_train = train_df["stress_level"].astype(int)
    X_test = test_df[AUDIO_FEATURE_COLUMNS]
    y_test = test_df["stress_level"].astype(int)

    candidate_models = build_candidate_models(random_state=random_state)
    candidate_results: Dict[str, Dict[str, float]] = {}
    fitted_models: Dict[str, object] = {}

    best_name = ""
    best_model: object | None = None
    best_accuracy = -1.0
    best_balanced_accuracy = -1.0
    best_predictions = None

    for model_name, candidate in candidate_models.items():
        candidate.fit(X_train, y_train)
        y_pred = candidate.predict(X_test)
        accuracy = float(accuracy_score(y_test, y_pred))
        balanced_accuracy = float(balanced_accuracy_score(y_test, y_pred))

        candidate_results[model_name] = {
            "accuracy": accuracy,
            "balanced_accuracy": balanced_accuracy,
        }
        fitted_models[model_name] = candidate

        if (
            balanced_accuracy > best_balanced_accuracy
            or (
                balanced_accuracy == best_balanced_accuracy
                and accuracy > best_accuracy
            )
        ):
            best_name = model_name
            best_model = candidate
            best_accuracy = accuracy
            best_balanced_accuracy = balanced_accuracy
            best_predictions = y_pred

    if best_model is None or best_predictions is None:
        raise RuntimeError("Failed to train any audio model candidate.")

    model = best_model
    y_pred = best_predictions
    accuracy = best_accuracy
    balanced_accuracy = best_balanced_accuracy
    report = classification_report(
        y_test,
        y_pred,
        labels=[0, 1, 2, 3],
        output_dict=True,
        zero_division=0,
        target_names=["Low", "Moderate", "High", "Severe"],
    )
    confusion = confusion_matrix(y_test, y_pred, labels=[0, 1, 2, 3]).tolist()
    importance = _extract_feature_importance(
        model=model,
        X_test=X_test,
        y_test=y_test,
        random_state=random_state,
    )

    groups = feature_df["speaker_id"] if "speaker_id" in feature_df.columns else None
    cv_metrics = _compute_cv_scores(
        model=build_candidate_models(random_state=random_state)[best_name],
        X=feature_df[AUDIO_FEATURE_COLUMNS],
        y=feature_df["stress_level"].astype(int),
        groups=groups,
        random_state=random_state,
    )

    model_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_out)

    metadata = {
        "feature_source": feature_source,
        "dataset_root": str(Path(dataset_root).resolve()) if dataset_root else None,
        "total_rows": int(len(feature_df)),
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "split_method": split_method,
        "features": list(X_train.columns),
        "model_type": type(model).__name__,
        "selected_model_name": best_name,
        "candidate_results": candidate_results,
        "random_state": random_state,
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "cross_validation": cv_metrics,
        "class_distribution": {
            label: int(count)
            for label, count in feature_df["stress_label"].value_counts().sort_index().items()
        },
        "speaker_count": int(
            feature_df["speaker_id"].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().nunique()
        ),
        "top_feature_importance": dict(list(importance.items())[:10]),
        "classification_report": report,
        "confusion_matrix": confusion,
        "accuracy_note": (
            "Speaker-independent accuracy is the meaningful metric for voice stress detection. "
            "If this score is far below 0.90, collect more speakers before tuning the model."
        ),
    }

    metadata_out.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Model saved to: {model_out}")
    print(f"Metadata saved to: {metadata_out}")
    print(f"Selected model: {best_name}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Balanced accuracy: {balanced_accuracy:.4f}")
    if cv_metrics["mean"] is not None:
        print(
            f"Cross-validation ({cv_metrics['method']}): "
            f"{cv_metrics['mean']:.4f} +/- {cv_metrics['std']:.4f}"
        )
    else:
        print("Cross-validation: not run")

    return model


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a speaker-aware audio stress classifier.")
    parser.add_argument("--manifest", help="Manifest CSV with sample_id, audio_path, stress_label, stress_level, speaker_id.")
    parser.add_argument("--dataset-root", help="Root folder used to resolve relative audio paths in the manifest.")
    parser.add_argument("--features-csv", help="Precomputed feature CSV. Skips audio feature extraction if provided.")
    parser.add_argument("--model-out", help="Path to save the trained model pickle.")
    parser.add_argument("--metadata-out", help="Path to save JSON training metadata.")
    parser.add_argument(
        "--skip-failed",
        action="store_true",
        help="Skip unreadable audio files during feature extraction.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    train_audio_stress_model(
        manifest_csv=args.manifest,
        dataset_root=args.dataset_root,
        cached_features_csv=args.features_csv,
        model_out=args.model_out,
        metadata_out=args.metadata_out,
        skip_failed=args.skip_failed,
    )


if __name__ == "__main__":
    main()
