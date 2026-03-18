from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd

try:
    from .audio_features import AUDIO_FEATURE_COLUMNS, extract_audio_features
except ImportError:
    from audio_features import AUDIO_FEATURE_COLUMNS, extract_audio_features

LABEL_TO_LEVEL = {
    "low": 0,
    "moderate": 1,
    "high": 2,
    "severe": 3,
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
    "split",
    "language",
    "assignment_id",
    "recording_device",
    "environment",
    "transcript",
    "notes",
]


def _normalize_label(label: str) -> str:
    clean = label.strip().lower()
    if clean not in LABEL_TO_LEVEL:
        raise ValueError(
            f"Unsupported label '{label}'. Expected one of: {', '.join(LABEL_TO_LEVEL)}."
        )
    return clean


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
    """
    Scan a folder like:
    data/audio/low/speaker_01/*.wav
    data/audio/high/speaker_02/*.wav
    and build a training manifest.
    """
    dataset_root = Path(dataset_root)
    rows: List[Dict[str, object]] = []

    for label, level in LABEL_TO_LEVEL.items():
        label_root = dataset_root / label
        if not label_root.exists():
            continue

        for audio_path in sorted(label_root.rglob("*.wav")):
            rows.append(
                {
                    "sample_id": audio_path.stem,
                    "audio_path": audio_path.relative_to(dataset_root).as_posix(),
                    "stress_label": label,
                    "stress_level": level,
                    "speaker_id": infer_speaker_id(audio_path, label_root),
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
            f"No WAV files found under {dataset_root}. Expected label folders: {', '.join(LABEL_TO_LEVEL)}"
        )

    manifest = pd.DataFrame(rows, columns=MANIFEST_COLUMNS)
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

    manifest["stress_label"] = manifest["stress_label"].astype(str).map(_normalize_label)
    manifest["stress_level"] = manifest["stress_level"].astype(int)

    for label, level in LABEL_TO_LEVEL.items():
        inconsistent = manifest.loc[
            (manifest["stress_label"] == label) & (manifest["stress_level"] != level)
        ]
        if not inconsistent.empty:
            raise ValueError(
                f"Manifest contains mismatched stress_level values for label '{label}'. Expected {level}."
            )

    for column in MANIFEST_COLUMNS:
        if column not in manifest.columns:
            manifest[column] = ""

    return manifest


def resolve_audio_path(audio_path: str, manifest_csv: str | Path, dataset_root: str | Path | None = None) -> Path:
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
                "stress_label": record["stress_label"],
                "stress_level": int(record["stress_level"]),
                "speaker_id": str(record["speaker_id"]),
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


def _featurize_command(args: argparse.Namespace) -> None:
    dataset = build_feature_dataset_from_manifest(
        manifest_csv=args.manifest,
        output_csv=args.output_csv,
        dataset_root=args.dataset_root,
        skip_failed=args.skip_failed,
    )
    print(f"Saved feature dataset with {len(dataset)} rows to {args.output_csv}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Utilities for audio stress dataset preparation.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan labeled WAV folders and create a manifest CSV.",
    )
    scan_parser.add_argument("--input-root", required=True, help="Folder containing low/moderate/high/severe directories.")
    scan_parser.add_argument("--output-csv", required=True, help="Path to write the manifest CSV.")
    scan_parser.set_defaults(func=_scan_command)

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
