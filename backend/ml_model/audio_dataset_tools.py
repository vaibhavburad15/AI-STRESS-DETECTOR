from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd

try:
    from .audio_features import AUDIO_FEATURE_COLUMNS, extract_audio_features
except ImportError:
    from audio_features import AUDIO_FEATURE_COLUMNS, extract_audio_features

STRESS_LEVELS = {
    "low": 0,
    "medium": 1,
    "moderate": 1,
    "high": 2,
    "severe": 2,
}

CANONICAL_STRESS_LABELS = {
    0: "Low",
    1: "Medium",
    2: "High",
}

EMOTION_TO_STRESS = {
    "calm": "Low",
    "neutral": "Low",
    "happy": "Low",
    "sad": "Medium",
    "angry": "High",
    "fearful": "High",
    "fear": "High",
    "disgust": "High",
}

RAVDESS_EMOTIONS = {
    "01": "neutral",
    "02": "calm",
    "03": "happy",
    "04": "sad",
    "05": "angry",
    "06": "fearful",
    "07": "disgust",
    "08": "surprised",
}

CREMAD_EMOTIONS = {
    "ANG": "angry",
    "DIS": "disgust",
    "FEA": "fearful",
    "HAP": "happy",
    "NEU": "neutral",
    "SAD": "sad",
}

TESS_EMOTIONS = {
    "angry": "angry",
    "disgust": "disgust",
    "fear": "fearful",
    "happy": "happy",
    "neutral": "neutral",
    "sad": "sad",
    "ps": "pleasant_surprise",
}

REQUIRED_MANIFEST_COLUMNS = [
    "sample_id",
    "audio_path",
    "stress_label",
    "stress_level",
    "speaker_id",
]

MANIFEST_COLUMNS = [
    "sample_id",
    "audio_path",
    "stress_label",
    "stress_level",
    "speaker_id",
    "dataset",
    "emotion_label",
    "split",
    "language",
    "assignment_id",
    "recording_device",
    "environment",
    "transcript",
    "notes",
]


def _canonicalize_stress_label(label: str) -> str:
    normalized = str(label).strip().lower()
    if normalized not in STRESS_LEVELS:
        raise ValueError(
            f"Unsupported stress label '{label}'. Expected one of: {', '.join(sorted(STRESS_LEVELS))}."
        )
    return CANONICAL_STRESS_LABELS[STRESS_LEVELS[normalized]]


def _canonicalize_emotion_label(label: str) -> str:
    return str(label).strip().lower().replace("fear", "fearful") if str(label).strip().lower() == "fear" else str(label).strip().lower()


def _stress_level_from_label(label: str) -> int:
    normalized = str(label).strip().lower()
    if normalized not in STRESS_LEVELS:
        raise ValueError(f"Unsupported stress label '{label}'")
    return STRESS_LEVELS[normalized]


def _stress_from_emotion(emotion_label: str) -> tuple[str, int] | None:
    normalized_emotion = _canonicalize_emotion_label(emotion_label)
    stress_label = EMOTION_TO_STRESS.get(normalized_emotion)
    if stress_label is None:
        return None
    return stress_label, _stress_level_from_label(stress_label)


def infer_speaker_id(audio_path: Path, label_root: Path) -> str:
    relative_parts = audio_path.relative_to(label_root).parts
    if len(relative_parts) > 1:
        return relative_parts[0]
    stem = audio_path.stem
    if "_" in stem:
        return stem.split("_")[0]
    return stem


def create_manifest_from_labeled_audio(
    dataset_root: str | Path,
    output_csv: str | Path,
) -> pd.DataFrame:
    dataset_root = Path(dataset_root)
    rows: List[Dict[str, object]] = []

    for label_dir in sorted(dataset_root.iterdir() if dataset_root.exists() else []):
        if not label_dir.is_dir():
            continue

        try:
            canonical_label = _canonicalize_stress_label(label_dir.name)
        except ValueError:
            continue

        stress_level = _stress_level_from_label(canonical_label)
        for audio_path in sorted(label_dir.rglob("*.wav")):
            rows.append(
                {
                    "sample_id": audio_path.stem,
                    "audio_path": audio_path.relative_to(dataset_root).as_posix(),
                    "stress_label": canonical_label,
                    "stress_level": stress_level,
                    "speaker_id": infer_speaker_id(audio_path, label_dir),
                    "dataset": "custom",
                    "emotion_label": "",
                    "split": "",
                    "language": "",
                    "assignment_id": "",
                    "recording_device": "",
                    "environment": "",
                    "transcript": "",
                    "notes": "",
                }
            )

    if not rows:
        raise ValueError(
            f"No labeled WAV files found under {dataset_root}. "
            "Expected folders named low/medium/high or compatible synonyms."
        )

    manifest = pd.DataFrame(rows, columns=MANIFEST_COLUMNS)
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(output_path, index=False)
    return manifest


def _first_existing_path(candidates: List[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def discover_public_dataset_roots(base_dir: str | Path | None = None) -> Dict[str, Path | None]:
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[2] / "data" / "public"
    base_path = Path(base_dir)

    ravdess_root = _first_existing_path(
        [
            base_path / "ravdess_16k" / "Audio_Speech_Actors_01-24_16k",
            base_path / "ravdess" / "Audio_Speech_Actors_01-24",
            base_path / "RAVDESS" / "Audio_Speech_Actors_01-24",
        ]
    )
    cremad_root = _first_existing_path(
        [
            base_path / "crema_d" / "AudioWAV",
            base_path / "CREMA-D" / "AudioWAV",
            base_path / "crema-d" / "AudioWAV",
            base_path / "crema_d",
            base_path / "CREMA-D",
            base_path / "crema-d",
        ]
    )
    tess_root = _first_existing_path(
        [
            base_path / "tess",
            base_path / "TESS",
            base_path / "TESS Toronto emotional speech set data",
        ]
    )

    return {
        "ravdess": ravdess_root,
        "cremad": cremad_root,
        "tess": tess_root,
    }


def _build_ravdess_rows(dataset_root: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for audio_path in sorted(dataset_root.rglob("*.wav")):
        parts = audio_path.stem.split("-")
        if len(parts) != 7:
            continue

        emotion_label = RAVDESS_EMOTIONS.get(parts[2])
        if not emotion_label:
            continue

        stress_mapping = _stress_from_emotion(emotion_label)
        if stress_mapping is None:
            continue

        stress_label, stress_level = stress_mapping
        actor_id = parts[6]
        rows.append(
            {
                "sample_id": audio_path.stem,
                "audio_path": audio_path.resolve().as_posix(),
                "stress_label": stress_label,
                "stress_level": stress_level,
                "speaker_id": f"ravdess_actor_{actor_id}",
                "dataset": "RAVDESS",
                "emotion_label": emotion_label,
                "split": "",
                "language": "en",
                "assignment_id": f"statement_{parts[4]}",
                "recording_device": "studio",
                "environment": "controlled",
                "transcript": "",
                "notes": f"intensity={parts[3]}; repetition={parts[5]}",
            }
        )
    return rows


def _build_cremad_rows(dataset_root: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for audio_path in sorted(dataset_root.rglob("*.wav")):
        parts = audio_path.stem.split("_")
        if len(parts) < 4:
            continue

        speaker_id, sentence_code, emotion_code, intensity_code = parts[:4]
        emotion_label = CREMAD_EMOTIONS.get(emotion_code.upper())
        if not emotion_label:
            continue

        stress_mapping = _stress_from_emotion(emotion_label)
        if stress_mapping is None:
            continue

        stress_label, stress_level = stress_mapping
        rows.append(
            {
                "sample_id": audio_path.stem,
                "audio_path": audio_path.resolve().as_posix(),
                "stress_label": stress_label,
                "stress_level": stress_level,
                "speaker_id": f"cremad_actor_{speaker_id}",
                "dataset": "CREMA-D",
                "emotion_label": emotion_label,
                "split": "",
                "language": "en",
                "assignment_id": sentence_code,
                "recording_device": "studio",
                "environment": "controlled",
                "transcript": "",
                "notes": f"intensity={intensity_code}",
            }
        )
    return rows


def _build_tess_rows(dataset_root: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for audio_path in sorted(dataset_root.rglob("*.wav")):
        folder_parts = audio_path.parent.name.split("_")
        speaker_token = folder_parts[0] if folder_parts else audio_path.stem.split("_")[0]

        emotion_token = audio_path.stem.split("_")[-1].lower()
        emotion_label = TESS_EMOTIONS.get(emotion_token)
        if emotion_label is None:
            emotion_label = TESS_EMOTIONS.get(audio_path.parent.name.split("_")[-1].lower(), "")
        if not emotion_label:
            continue

        stress_mapping = _stress_from_emotion(emotion_label)
        if stress_mapping is None:
            continue

        stress_label, stress_level = stress_mapping
        rows.append(
            {
                "sample_id": audio_path.stem,
                "audio_path": audio_path.resolve().as_posix(),
                "stress_label": stress_label,
                "stress_level": stress_level,
                "speaker_id": f"tess_speaker_{speaker_token}",
                "dataset": "TESS",
                "emotion_label": emotion_label,
                "split": "",
                "language": "en",
                "assignment_id": "_".join(audio_path.stem.split("_")[1:-1]),
                "recording_device": "studio",
                "environment": "controlled",
                "transcript": "",
                "notes": "",
            }
        )
    return rows


def build_public_emotion_manifest(
    ravdess_root: str | Path | None = None,
    cremad_root: str | Path | None = None,
    tess_root: str | Path | None = None,
    output_csv: str | Path | None = None,
    base_dir: str | Path | None = None,
    skip_missing: bool = True,
) -> pd.DataFrame:
    discovered_roots = discover_public_dataset_roots(base_dir=base_dir)
    dataset_roots = {
        "ravdess": Path(ravdess_root) if ravdess_root else discovered_roots["ravdess"],
        "cremad": Path(cremad_root) if cremad_root else discovered_roots["cremad"],
        "tess": Path(tess_root) if tess_root else discovered_roots["tess"],
    }

    dataset_builders = {
        "ravdess": _build_ravdess_rows,
        "cremad": _build_cremad_rows,
        "tess": _build_tess_rows,
    }

    rows: List[Dict[str, object]] = []
    missing_datasets: List[str] = []
    for dataset_name, dataset_root in dataset_roots.items():
        if dataset_root is None or not dataset_root.exists():
            missing_datasets.append(dataset_name)
            if skip_missing:
                continue
            raise ValueError(f"Dataset root not found for {dataset_name}: {dataset_root}")

        rows.extend(dataset_builders[dataset_name](dataset_root))

    if not rows:
        message = "No dataset rows were generated from the requested public emotion datasets."
        if missing_datasets:
            message = f"{message} Missing datasets: {', '.join(missing_datasets)}."
        raise ValueError(message)

    manifest = pd.DataFrame(rows, columns=MANIFEST_COLUMNS)
    manifest["stress_label"] = manifest["stress_label"].map(_canonicalize_stress_label)
    manifest["stress_level"] = manifest["stress_label"].map(lambda value: _stress_level_from_label(value))

    if output_csv:
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        manifest.to_csv(output_path, index=False)

    return manifest


def load_manifest(manifest_csv: str | Path) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_csv)
    missing_columns = [column for column in REQUIRED_MANIFEST_COLUMNS if column not in manifest.columns]
    if missing_columns:
        raise ValueError(
            f"Manifest is missing required columns: {missing_columns}. "
            f"Expected at least: {REQUIRED_MANIFEST_COLUMNS}"
        )

    manifest["stress_label"] = manifest["stress_label"].astype(str).map(_canonicalize_stress_label)
    manifest["stress_level"] = manifest["stress_label"].map(lambda value: _stress_level_from_label(value))

    for column in MANIFEST_COLUMNS:
        if column not in manifest.columns:
            manifest[column] = ""

    return manifest


def resolve_audio_path(
    audio_path: str,
    manifest_csv: str | Path,
    dataset_root: str | Path | None = None,
) -> Path:
    path = Path(audio_path)
    if path.is_absolute():
        return path

    if dataset_root:
        candidate = Path(dataset_root) / path
        if candidate.exists():
            return candidate.resolve()

    manifest_parent = Path(manifest_csv).resolve().parent
    candidate = manifest_parent / path
    if candidate.exists():
        return candidate.resolve()

    if dataset_root:
        return (Path(dataset_root) / path).resolve()
    return candidate.resolve()


def build_feature_dataset_from_manifest(
    manifest_csv: str | Path,
    output_csv: str | Path | None = None,
    dataset_root: str | Path | None = None,
    skip_failed: bool = False,
) -> pd.DataFrame:
    manifest = load_manifest(manifest_csv)
    rows: List[Dict[str, object]] = []
    failed_samples: List[str] = []

    for _, record in manifest.iterrows():
        resolved_audio = resolve_audio_path(
            str(record["audio_path"]),
            manifest_csv=manifest_csv,
            dataset_root=dataset_root,
        )

        try:
            features = extract_audio_features(resolved_audio)
        except Exception as exc:
            message = f"{record['sample_id']} -> {resolved_audio}: {exc}"
            if not skip_failed:
                raise RuntimeError(f"Failed to extract features for {message}") from exc
            failed_samples.append(message)
            continue

        rows.append(
            {
                "sample_id": record["sample_id"],
                "audio_path": str(record["audio_path"]),
                "resolved_audio_path": str(resolved_audio),
                "stress_label": str(record["stress_label"]),
                "stress_level": int(record["stress_level"]),
                "speaker_id": str(record["speaker_id"]),
                "dataset": str(record.get("dataset", "") or ""),
                "emotion_label": str(record.get("emotion_label", "") or ""),
                "split": str(record.get("split", "") or ""),
                "language": str(record.get("language", "") or ""),
                "assignment_id": str(record.get("assignment_id", "") or ""),
                "recording_device": str(record.get("recording_device", "") or ""),
                "environment": str(record.get("environment", "") or ""),
                "transcript": str(record.get("transcript", "") or ""),
                "notes": str(record.get("notes", "") or ""),
                **features,
            }
        )

    if not rows:
        raise ValueError("No feature rows were created. Check the manifest and audio files.")

    dataset = pd.DataFrame(rows)
    ordered_columns = [
        "sample_id",
        "audio_path",
        "resolved_audio_path",
        "stress_label",
        "stress_level",
        "speaker_id",
        "dataset",
        "emotion_label",
        "split",
        "language",
        "assignment_id",
        "recording_device",
        "environment",
        "transcript",
        "notes",
        *AUDIO_FEATURE_COLUMNS,
    ]
    dataset = dataset[ordered_columns]

    if output_csv:
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dataset.to_csv(output_path, index=False)

    if failed_samples:
        print("Skipped samples:")
        for failed in failed_samples:
            print(f"  - {failed}")

    return dataset


def _scan_command(args: argparse.Namespace) -> None:
    manifest = create_manifest_from_labeled_audio(args.input_root, args.output_csv)
    print(f"Saved manifest with {len(manifest)} rows to {args.output_csv}")


def _combine_public_command(args: argparse.Namespace) -> None:
    manifest = build_public_emotion_manifest(
        ravdess_root=args.ravdess_root,
        cremad_root=args.cremad_root,
        tess_root=args.tess_root,
        output_csv=args.output_csv,
        base_dir=args.base_dir,
        skip_missing=args.skip_missing,
    )
    label_counts = manifest["stress_label"].value_counts().sort_index().to_dict()
    dataset_counts = manifest["dataset"].value_counts().sort_index().to_dict()
    print(f"Saved manifest with {len(manifest)} rows to {args.output_csv}")
    print(f"Dataset distribution: {dataset_counts}")
    print(f"Stress distribution: {label_counts}")


def _featurize_command(args: argparse.Namespace) -> None:
    dataset = build_feature_dataset_from_manifest(
        manifest_csv=args.manifest,
        output_csv=args.output_csv,
        dataset_root=args.dataset_root,
        skip_failed=args.skip_failed,
    )
    print(f"Saved feature dataset with {len(dataset)} rows to {args.output_csv}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Utilities for voice stress dataset preparation.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan labeled WAV folders and create a manifest CSV.",
    )
    scan_parser.add_argument("--input-root", required=True, help="Folder containing low/medium/high directories.")
    scan_parser.add_argument("--output-csv", required=True, help="Path to write the manifest CSV.")
    scan_parser.set_defaults(func=_scan_command)

    public_parser = subparsers.add_parser(
        "combine-public",
        help="Build a combined manifest from RAVDESS, CREMA-D, and TESS.",
    )
    public_parser.add_argument("--output-csv", required=True, help="Path to write the manifest CSV.")
    public_parser.add_argument("--base-dir", help="Optional parent directory containing public emotion datasets.")
    public_parser.add_argument("--ravdess-root", help="Optional explicit RAVDESS root.")
    public_parser.add_argument("--cremad-root", help="Optional explicit CREMA-D root.")
    public_parser.add_argument("--tess-root", help="Optional explicit TESS root.")
    public_parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Skip datasets that are not present instead of failing.",
    )
    public_parser.set_defaults(func=_combine_public_command)

    feature_parser = subparsers.add_parser(
        "featurize",
        help="Turn a manifest CSV into a tabular audio-feature dataset.",
    )
    feature_parser.add_argument("--manifest", required=True, help="Path to the manifest CSV.")
    feature_parser.add_argument("--output-csv", required=True, help="Path to write the feature dataset CSV.")
    feature_parser.add_argument("--dataset-root", help="Optional root directory used to resolve relative audio paths.")
    feature_parser.add_argument(
        "--skip-failed",
        action="store_true",
        help="Skip corrupt or unsupported files instead of stopping.",
    )
    feature_parser.set_defaults(func=_featurize_command)

    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
