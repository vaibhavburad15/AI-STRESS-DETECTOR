from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Sequence, Tuple

import librosa
import numpy as np
import soundfile as sf

TARGET_SAMPLE_RATE = 16000
FRAME_MS = 25
HOP_MS = 10
N_MELS = 40
N_MFCC = 20
N_CHROMA = 12
N_SPECTRAL_CONTRAST = 7
CHUNK_DURATION_SECONDS = 2.5
MIN_CHUNK_DURATION_SECONDS = 0.75

STRESS_LEVEL_LABELS = {
    0: "Low",
    1: "Medium",
    2: "High",
}

FEATURE_GROUP_WEIGHTS = {
    "mfcc": 2.0,
    "mfcc_delta": 2.0,
    "mfcc_delta2": 2.0,
    "rms": 1.8,
    "spectral_contrast": 1.6,
    "chroma": 1.4,
    "zcr": 1.2,
}

MFCC_MEAN_COLUMNS = [f"mfcc_{index:02d}_mean" for index in range(1, N_MFCC + 1)]
MFCC_STD_COLUMNS = [f"mfcc_{index:02d}_std" for index in range(1, N_MFCC + 1)]
MFCC_DELTA_MEAN_COLUMNS = [f"mfcc_delta_{index:02d}_mean" for index in range(1, N_MFCC + 1)]
MFCC_DELTA_STD_COLUMNS = [f"mfcc_delta_{index:02d}_std" for index in range(1, N_MFCC + 1)]
MFCC_DELTA2_MEAN_COLUMNS = [f"mfcc_delta2_{index:02d}_mean" for index in range(1, N_MFCC + 1)]
MFCC_DELTA2_STD_COLUMNS = [f"mfcc_delta2_{index:02d}_std" for index in range(1, N_MFCC + 1)]
CHROMA_MEAN_COLUMNS = [f"chroma_{index:02d}_mean" for index in range(1, N_CHROMA + 1)]
CHROMA_STD_COLUMNS = [f"chroma_{index:02d}_std" for index in range(1, N_CHROMA + 1)]
SPECTRAL_CONTRAST_MEAN_COLUMNS = [
    f"spectral_contrast_{index:02d}_mean" for index in range(1, N_SPECTRAL_CONTRAST + 1)
]
SPECTRAL_CONTRAST_STD_COLUMNS = [
    f"spectral_contrast_{index:02d}_std" for index in range(1, N_SPECTRAL_CONTRAST + 1)
]

AUDIO_FEATURE_COLUMNS = [
    *MFCC_MEAN_COLUMNS,
    *MFCC_STD_COLUMNS,
    *MFCC_DELTA_MEAN_COLUMNS,
    *MFCC_DELTA_STD_COLUMNS,
    *MFCC_DELTA2_MEAN_COLUMNS,
    *MFCC_DELTA2_STD_COLUMNS,
    "zcr_mean",
    "zcr_std",
    "rms_mean",
    "rms_std",
    *CHROMA_MEAN_COLUMNS,
    *CHROMA_STD_COLUMNS,
    *SPECTRAL_CONTRAST_MEAN_COLUMNS,
    *SPECTRAL_CONTRAST_STD_COLUMNS,
]

MEL_FILTERBANK_CACHE: dict[tuple[int, int, int], np.ndarray] = {}
DCT_BASIS_CACHE: dict[tuple[int, int], np.ndarray] = {}
CHROMA_FILTERBANK_CACHE: dict[tuple[int, int, int], np.ndarray] = {}


def _safe_load_audio(audio_source: str | Path, target_sample_rate: int) -> Tuple[np.ndarray, int]:
    signal, sample_rate = sf.read(str(audio_source), always_2d=False)
    signal = np.asarray(signal, dtype=np.float32)
    if signal.ndim > 1:
        signal = np.mean(signal, axis=1)

    if sample_rate != target_sample_rate:
        signal = librosa.resample(
            signal,
            orig_sr=sample_rate,
            target_sr=target_sample_rate,
            res_type="soxr_hq",
        )
        sample_rate = target_sample_rate

    signal = np.nan_to_num(signal, nan=0.0, posinf=0.0, neginf=0.0)
    if signal.size == 0:
        raise ValueError(f"Audio file is empty: {audio_source}")

    return signal.astype(np.float32), int(sample_rate)


def _reduce_noise(signal: np.ndarray) -> np.ndarray:
    if signal.size < 128:
        return signal

    absolute_signal = np.abs(signal)
    noise_floor = float(np.percentile(absolute_signal, 20))
    threshold = max(noise_floor * 1.5, 1e-4)
    gated_signal = np.where(absolute_signal < threshold, signal * 0.15, signal)
    return np.asarray(gated_signal, dtype=np.float32)


def _trim_silence(signal: np.ndarray, sample_rate: int, top_db: float = 25.0) -> np.ndarray:
    if signal.size < 512:
        return signal

    frame_length = min(2048, max(512, int(0.08 * sample_rate)))
    hop_length = max(frame_length // 4, 1)
    frames = _frame_signal(signal, frame_length, hop_length)
    frame_rms = np.sqrt(np.mean(np.square(frames), axis=1))
    reference = float(np.max(frame_rms))
    if reference <= 0:
        return signal

    threshold = reference * (10.0 ** (-top_db / 20.0))
    active_indices = np.flatnonzero(frame_rms >= threshold)
    if active_indices.size == 0:
        return signal

    start_sample = int(active_indices[0] * hop_length)
    end_sample = int(min(signal.size, (active_indices[-1] * hop_length) + frame_length))
    return signal[start_sample:end_sample]


def preprocess_audio(
    audio_source: str | Path,
    target_sample_rate: int = TARGET_SAMPLE_RATE,
) -> Tuple[np.ndarray, int]:
    signal, sample_rate = _safe_load_audio(audio_source, target_sample_rate)
    signal = _reduce_noise(signal)
    signal = _trim_silence(signal, sample_rate, top_db=25)
    signal = np.nan_to_num(signal, nan=0.0, posinf=0.0, neginf=0.0)

    peak = float(np.max(np.abs(signal))) if signal.size else 0.0
    if peak > 0:
        signal = signal / peak

    if signal.size == 0:
        raise ValueError(f"Audio preprocessing removed all usable signal for {audio_source}")

    return signal.astype(np.float32), sample_rate


def _pad_for_analysis(signal: np.ndarray, sample_rate: int) -> np.ndarray:
    minimum_length = max(int(0.5 * sample_rate), 512)
    if signal.size >= minimum_length:
        return signal
    return np.pad(signal, (0, minimum_length - signal.size), mode="constant")


def _frame_signal(signal: np.ndarray, frame_length: int, hop_length: int) -> np.ndarray:
    if signal.size < frame_length:
        signal = np.pad(signal, (0, frame_length - signal.size), mode="constant")

    starts = np.arange(0, signal.size - frame_length + 1, hop_length, dtype=int)
    return np.stack([signal[start : start + frame_length] for start in starts]).astype(np.float32)


def _safe_mean(values: np.ndarray) -> float:
    return float(np.mean(values)) if values.size else 0.0


def _safe_std(values: np.ndarray) -> float:
    return float(np.std(values)) if values.size else 0.0


def _hz_to_mel(values_hz: np.ndarray) -> np.ndarray:
    return 2595.0 * np.log10(1.0 + (values_hz / 700.0))


def _mel_to_hz(values_mel: np.ndarray) -> np.ndarray:
    return 700.0 * (10.0 ** (values_mel / 2595.0) - 1.0)


def _build_mel_filterbank(
    sample_rate: int,
    frame_length: int,
    n_mels: int = N_MELS,
) -> np.ndarray:
    cache_key = (sample_rate, frame_length, n_mels)
    cached = MEL_FILTERBANK_CACHE.get(cache_key)
    if cached is not None:
        return cached

    fft_freqs = np.fft.rfftfreq(frame_length, d=1.0 / sample_rate)
    mel_points = np.linspace(
        _hz_to_mel(np.array([0.0], dtype=float))[0],
        _hz_to_mel(np.array([sample_rate / 2.0], dtype=float))[0],
        num=n_mels + 2,
        dtype=float,
    )
    hz_points = _mel_to_hz(mel_points)
    bin_indices = np.clip(
        np.searchsorted(fft_freqs, hz_points, side="left"),
        0,
        len(fft_freqs) - 1,
    )

    filters = np.zeros((n_mels, len(fft_freqs)), dtype=np.float32)
    for mel_index in range(n_mels):
        start = int(bin_indices[mel_index])
        center = int(bin_indices[mel_index + 1])
        end = int(bin_indices[mel_index + 2])

        if center <= start:
            center = min(start + 1, len(fft_freqs) - 1)
        if end <= center:
            end = min(center + 1, len(fft_freqs))

        for freq_index in range(start, center):
            filters[mel_index, freq_index] = (freq_index - start) / max(center - start, 1)
        for freq_index in range(center, end):
            filters[mel_index, freq_index] = (end - freq_index) / max(end - center, 1)

    normalizer = np.sum(filters, axis=1, keepdims=True)
    normalizer[normalizer == 0.0] = 1.0
    normalized = filters / normalizer
    MEL_FILTERBANK_CACHE[cache_key] = normalized
    return normalized


def _build_dct_basis(input_size: int, output_size: int = N_MFCC) -> np.ndarray:
    cache_key = (input_size, output_size)
    cached = DCT_BASIS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    indices = np.arange(input_size, dtype=float)
    basis = np.zeros((output_size, input_size), dtype=np.float32)
    scale = np.sqrt(2.0 / input_size)

    for row_index in range(output_size):
        basis[row_index] = scale * np.cos((np.pi / input_size) * (indices + 0.5) * row_index)

    basis[0] *= 1.0 / np.sqrt(2.0)
    DCT_BASIS_CACHE[cache_key] = basis
    return basis


def _build_chroma_filterbank(
    sample_rate: int,
    frame_length: int,
    n_chroma: int = N_CHROMA,
) -> np.ndarray:
    cache_key = (sample_rate, frame_length, n_chroma)
    cached = CHROMA_FILTERBANK_CACHE.get(cache_key)
    if cached is not None:
        return cached

    freqs = np.fft.rfftfreq(frame_length, d=1.0 / sample_rate)
    filterbank = np.zeros((n_chroma, len(freqs)), dtype=np.float32)

    for bin_index, frequency in enumerate(freqs):
        if frequency <= 0:
            continue
        midi_value = 69.0 + (12.0 * np.log2(frequency / 440.0))
        chroma_index = int(np.round(midi_value)) % n_chroma
        filterbank[chroma_index, bin_index] = 1.0

    normalizer = np.sum(filterbank, axis=1, keepdims=True)
    normalizer[normalizer == 0.0] = 1.0
    normalized = filterbank / normalizer
    CHROMA_FILTERBANK_CACHE[cache_key] = normalized
    return normalized


def _matrix_statistics(
    matrix: np.ndarray,
    mean_columns: Sequence[str],
    std_columns: Sequence[str],
) -> Dict[str, float]:
    matrix = np.asarray(matrix, dtype=np.float32)
    if matrix.ndim != 2:
        raise ValueError("Expected a 2D feature matrix")

    features: Dict[str, float] = {}
    feature_count = max(len(mean_columns), len(std_columns))
    for feature_index in range(feature_count):
        values = matrix[:, feature_index] if feature_index < matrix.shape[1] else np.zeros(1, dtype=np.float32)
        values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
        if feature_index < len(mean_columns):
            features[mean_columns[feature_index]] = _safe_mean(values)
        if feature_index < len(std_columns):
            features[std_columns[feature_index]] = _safe_std(values)

    return features


def _compute_mfcc_matrices(
    power_spectrum: np.ndarray,
    sample_rate: int,
    frame_length: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mel_filterbank = _build_mel_filterbank(sample_rate=sample_rate, frame_length=frame_length)
    mel_energy = np.maximum(power_spectrum @ mel_filterbank.T, 1e-10)
    log_mel_energy = np.log(mel_energy)
    dct_basis = _build_dct_basis(input_size=mel_filterbank.shape[0], output_size=N_MFCC)
    mfcc_matrix = log_mel_energy @ dct_basis.T
    delta_matrix = np.gradient(mfcc_matrix, axis=0) if len(mfcc_matrix) > 1 else np.zeros_like(mfcc_matrix)
    delta2_matrix = np.gradient(delta_matrix, axis=0) if len(delta_matrix) > 1 else np.zeros_like(delta_matrix)
    return mfcc_matrix, delta_matrix, delta2_matrix


def _compute_chroma_matrix(
    spectrum: np.ndarray,
    sample_rate: int,
    frame_length: int,
) -> np.ndarray:
    filterbank = _build_chroma_filterbank(sample_rate=sample_rate, frame_length=frame_length)
    chroma = spectrum @ filterbank.T
    row_sums = np.sum(chroma, axis=1, keepdims=True)
    row_sums[row_sums == 0.0] = 1.0
    return chroma / row_sums


def _compute_spectral_contrast_matrix(
    spectrum: np.ndarray,
    sample_rate: int,
    frame_length: int,
) -> np.ndarray:
    freqs = np.fft.rfftfreq(frame_length, d=1.0 / sample_rate)
    nyquist = sample_rate / 2.0
    band_edges = [0.0, 200.0, 400.0, 800.0, 1600.0, 3200.0, 6400.0, nyquist]
    band_edges = [min(edge, nyquist) for edge in band_edges]

    contrast_bands = []
    for band_index in range(N_SPECTRAL_CONTRAST):
        low = band_edges[band_index]
        high = band_edges[band_index + 1] if band_index + 1 < len(band_edges) else nyquist
        if band_index == N_SPECTRAL_CONTRAST - 1:
            frequency_mask = (freqs >= low) & (freqs <= high)
        else:
            frequency_mask = (freqs >= low) & (freqs < high)

        if not np.any(frequency_mask):
            contrast_bands.append(np.zeros(spectrum.shape[0], dtype=np.float32))
            continue

        band_values = spectrum[:, frequency_mask]
        peaks = np.percentile(band_values, 90, axis=1)
        valleys = np.percentile(band_values, 10, axis=1)
        contrast = np.log1p(peaks) - np.log1p(valleys)
        contrast_bands.append(contrast.astype(np.float32))

    return np.stack(contrast_bands, axis=1)


def extract_features(signal: np.ndarray, sample_rate: int) -> Dict[str, float]:
    signal = _pad_for_analysis(np.asarray(signal, dtype=np.float32), sample_rate)

    frame_length = max(1, int(sample_rate * FRAME_MS / 1000))
    hop_length = max(1, int(sample_rate * HOP_MS / 1000))
    frames = _frame_signal(signal, frame_length=frame_length, hop_length=hop_length)

    window = np.hanning(frame_length).astype(np.float32)
    windowed = frames * window
    spectrum = np.abs(np.fft.rfft(windowed, axis=1)) + 1e-8
    power_spectrum = np.square(spectrum)

    mfcc_matrix, delta_matrix, delta2_matrix = _compute_mfcc_matrices(
        power_spectrum=power_spectrum,
        sample_rate=sample_rate,
        frame_length=frame_length,
    )
    chroma_matrix = _compute_chroma_matrix(
        spectrum=spectrum,
        sample_rate=sample_rate,
        frame_length=frame_length,
    )
    spectral_contrast_matrix = _compute_spectral_contrast_matrix(
        spectrum=spectrum,
        sample_rate=sample_rate,
        frame_length=frame_length,
    )
    zcr = np.mean(np.diff(np.signbit(frames), axis=1) != 0, axis=1, keepdims=True)
    rms = np.sqrt(np.mean(np.square(frames), axis=1, keepdims=True))

    features: Dict[str, float] = {}
    features.update(_matrix_statistics(mfcc_matrix, MFCC_MEAN_COLUMNS, MFCC_STD_COLUMNS))
    features.update(_matrix_statistics(delta_matrix, MFCC_DELTA_MEAN_COLUMNS, MFCC_DELTA_STD_COLUMNS))
    features.update(_matrix_statistics(delta2_matrix, MFCC_DELTA2_MEAN_COLUMNS, MFCC_DELTA2_STD_COLUMNS))
    features.update(_matrix_statistics(zcr, ["zcr_mean"], ["zcr_std"]))
    features.update(_matrix_statistics(rms, ["rms_mean"], ["rms_std"]))
    features.update(_matrix_statistics(chroma_matrix, CHROMA_MEAN_COLUMNS, CHROMA_STD_COLUMNS))
    features.update(
        _matrix_statistics(
            spectral_contrast_matrix,
            SPECTRAL_CONTRAST_MEAN_COLUMNS,
            SPECTRAL_CONTRAST_STD_COLUMNS,
        )
    )

    return features


def extract_feature_bundle(signal: np.ndarray, sample_rate: int) -> Dict[str, Any]:
    signal = _pad_for_analysis(np.asarray(signal, dtype=np.float32), sample_rate)
    frame_length = max(1, int(sample_rate * FRAME_MS / 1000))
    hop_length = max(1, int(sample_rate * HOP_MS / 1000))
    frames = _frame_signal(signal, frame_length=frame_length, hop_length=hop_length)
    window = np.hanning(frame_length).astype(np.float32)
    windowed = frames * window
    spectrum = np.abs(np.fft.rfft(windowed, axis=1)) + 1e-8
    power_spectrum = np.square(spectrum)
    mfcc_matrix, _, _ = _compute_mfcc_matrices(power_spectrum, sample_rate, frame_length)
    zcr = np.mean(np.diff(np.signbit(frames), axis=1) != 0, axis=1)
    rms = np.sqrt(np.mean(np.square(frames), axis=1))

    return {
        "features": extract_features(signal, sample_rate),
        "diagnostics": {
            "rms_mean": _safe_mean(rms),
            "mfcc_variance": float(np.mean(np.var(mfcc_matrix, axis=1))),
            "zcr_mean": _safe_mean(zcr),
        },
    }


def extract_audio_features(audio_path: str | Path) -> Dict[str, float]:
    signal, sample_rate = preprocess_audio(audio_path)
    return extract_features(signal, sample_rate)


def _feature_group_for_name(feature_name: str) -> str | None:
    if feature_name.startswith("mfcc_delta2_"):
        return "mfcc_delta2"
    if feature_name.startswith("mfcc_delta_"):
        return "mfcc_delta"
    if feature_name.startswith("mfcc_"):
        return "mfcc"
    if feature_name.startswith("rms_"):
        return "rms"
    if feature_name.startswith("spectral_contrast_"):
        return "spectral_contrast"
    if feature_name.startswith("chroma_"):
        return "chroma"
    if feature_name.startswith("zcr_"):
        return "zcr"
    return None


def apply_feature_weights(
    features: Dict[str, float] | np.ndarray,
    feature_names: Sequence[str] | None = None,
) -> Dict[str, float] | np.ndarray:
    if isinstance(features, dict):
        weighted: Dict[str, float] = {}
        for name, value in features.items():
            weight = FEATURE_GROUP_WEIGHTS.get(_feature_group_for_name(name) or "", 1.0)
            weighted[name] = float(value) * weight
        return weighted

    if feature_names is None:
        raise ValueError("feature_names are required when weighting numpy arrays")

    matrix = np.asarray(features, dtype=np.float32)
    squeeze_output = matrix.ndim == 1
    if squeeze_output:
        matrix = matrix.reshape(1, -1)

    weighted_matrix = matrix.copy()
    for index, feature_name in enumerate(feature_names):
        weight = FEATURE_GROUP_WEIGHTS.get(_feature_group_for_name(feature_name) or "", 1.0)
        weighted_matrix[:, index] = weighted_matrix[:, index] * weight

    return weighted_matrix[0] if squeeze_output else weighted_matrix


def _normalize_metric(values: Iterable[float], fallback_scale: float | None = None) -> np.ndarray:
    array = np.asarray(list(values), dtype=np.float32)
    if array.size == 0:
        return array

    value_range = float(np.max(array) - np.min(array))
    if value_range > 1e-8:
        return (array - np.min(array)) / value_range

    if fallback_scale and fallback_scale > 0:
        return np.clip(array / fallback_scale, 0.0, 1.0)

    return np.ones_like(array)


def split_audio_chunks(
    signal: np.ndarray,
    sample_rate: int,
    chunk_duration_seconds: float = CHUNK_DURATION_SECONDS,
    hop_duration_seconds: float | None = None,
) -> list[tuple[float, float, np.ndarray]]:
    if hop_duration_seconds is None:
        hop_duration_seconds = chunk_duration_seconds

    chunk_length = max(int(chunk_duration_seconds * sample_rate), 1)
    hop_length = max(int(hop_duration_seconds * sample_rate), 1)
    minimum_length = max(int(MIN_CHUNK_DURATION_SECONDS * sample_rate), 1)

    if signal.size <= chunk_length:
        chunk = signal
        if chunk.size < minimum_length:
            chunk = np.pad(chunk, (0, minimum_length - chunk.size), mode="constant")
        return [(0.0, round(signal.size / sample_rate, 3), chunk)]

    chunks: list[tuple[float, float, np.ndarray]] = []
    for start in range(0, signal.size, hop_length):
        end = min(start + chunk_length, signal.size)
        chunk = signal[start:end]
        if chunk.size < minimum_length and chunks:
            break
        if chunk.size < minimum_length:
            chunk = np.pad(chunk, (0, minimum_length - chunk.size), mode="constant")

        chunks.append((start / sample_rate, end / sample_rate, chunk))
        if end >= signal.size:
            break

    return chunks


def predict_chunks(
    signal: np.ndarray,
    sample_rate: int,
    model: Any,
    scaler: Any,
    feature_columns: Sequence[str],
    model_classes: Sequence[int] | None = None,
    fill_values: Dict[str, float] | None = None,
    chunk_duration_seconds: float = CHUNK_DURATION_SECONDS,
) -> list[Dict[str, Any]]:
    fill_values = fill_values or {}
    chunk_windows = split_audio_chunks(
        signal=signal,
        sample_rate=sample_rate,
        chunk_duration_seconds=chunk_duration_seconds,
    )
    if not chunk_windows:
        raise ValueError("No valid chunks were produced from the audio signal")

    chunk_bundles = [extract_feature_bundle(chunk_signal, sample_rate) for _, _, chunk_signal in chunk_windows]
    raw_matrix = np.asarray(
        [
            [bundle["features"].get(column, fill_values.get(column, 0.0)) for column in feature_columns]
            for bundle in chunk_bundles
        ],
        dtype=np.float32,
    )

    scaled_matrix = scaler.transform(raw_matrix)
    weighted_matrix = apply_feature_weights(scaled_matrix, feature_columns)
    probabilities = model.predict_proba(weighted_matrix)

    classes = np.asarray(
        list(model_classes) if model_classes is not None else getattr(model, "classes_", [0, 1, 2]),
        dtype=int,
    )

    rms_values = [bundle["diagnostics"]["rms_mean"] for bundle in chunk_bundles]
    mfcc_variances = [bundle["diagnostics"]["mfcc_variance"] for bundle in chunk_bundles]
    normalized_energy = _normalize_metric(rms_values, fallback_scale=0.15)
    normalized_mfcc_variance = _normalize_metric(mfcc_variances, fallback_scale=250.0)
    chunk_weights = (0.6 * normalized_energy) + (0.4 * normalized_mfcc_variance)
    if float(np.sum(chunk_weights)) <= 0:
        chunk_weights = np.ones(len(chunk_windows), dtype=np.float32)

    results: list[Dict[str, Any]] = []
    for index, ((start_sec, end_sec, _), bundle, probability_vector) in enumerate(
        zip(chunk_windows, chunk_bundles, probabilities)
    ):
        predicted_class = int(classes[int(np.argmax(probability_vector))])
        class_probabilities = {
            STRESS_LEVEL_LABELS.get(int(class_id), str(int(class_id))): round(float(probability), 4)
            for class_id, probability in zip(classes, probability_vector)
        }

        results.append(
            {
                "chunk_index": index,
                "start_sec": round(float(start_sec), 3),
                "end_sec": round(float(end_sec), 3),
                "stress_level": predicted_class,
                "stress_label": STRESS_LEVEL_LABELS.get(predicted_class, "Unknown"),
                "confidence": round(float(np.max(probability_vector)), 4),
                "chunk_weight": float(chunk_weights[index]),
                "normalized_energy": round(float(normalized_energy[index]), 4),
                "normalized_mfcc_variance": round(float(normalized_mfcc_variance[index]), 4),
                "diagnostics": {
                    "rms_mean": round(float(bundle["diagnostics"]["rms_mean"]), 4),
                    "mfcc_variance": round(float(bundle["diagnostics"]["mfcc_variance"]), 4),
                    "zcr_mean": round(float(bundle["diagnostics"]["zcr_mean"]), 4),
                },
                "probabilities": class_probabilities,
                "probability_vector": [float(value) for value in probability_vector],
            }
        )

    return results


def _weighted_average(values: Sequence[float], weights: Sequence[float]) -> float:
    values_array = np.asarray(values, dtype=np.float32)
    weights_array = np.asarray(weights, dtype=np.float32)
    weight_sum = float(np.sum(weights_array))
    if weight_sum <= 0:
        return float(np.mean(values_array)) if values_array.size else 0.0
    return float(np.sum(values_array * weights_array) / weight_sum)


def _human_join(items: Sequence[str]) -> str:
    items = [item for item in items if item]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def generate_explanation(chunk_predictions: Sequence[Dict[str, Any]]) -> str:
    if not chunk_predictions:
        return "No usable speech segments were detected."

    weights = [float(chunk["chunk_weight"]) for chunk in chunk_predictions]
    energy_score = _weighted_average(
        [float(chunk.get("normalized_energy", 0.0)) for chunk in chunk_predictions],
        weights,
    )
    mfcc_score = _weighted_average(
        [float(chunk.get("normalized_mfcc_variance", 0.0)) for chunk in chunk_predictions],
        weights,
    )
    zcr_score = _weighted_average(
        [
            min(float(chunk.get("diagnostics", {}).get("zcr_mean", 0.0)) / 0.15, 1.0)
            for chunk in chunk_predictions
        ],
        weights,
    )

    signals: list[str] = []
    if energy_score >= 0.55:
        signals.append("high energy voice")
    if mfcc_score >= 0.55:
        signals.append("unstable vocal pattern")
    if zcr_score >= 0.55:
        signals.append("rapid fluctuations in speech")

    if not signals:
        return "The voice pattern remained comparatively steady across the analyzed chunks."

    return f"Detected {_human_join(signals)}."


def aggregate_predictions(
    chunk_predictions: Sequence[Dict[str, Any]],
    model_classes: Sequence[int] | None = None,
) -> Dict[str, Any]:
    if not chunk_predictions:
        raise ValueError("chunk_predictions cannot be empty")

    probability_matrix = np.asarray(
        [chunk["probability_vector"] for chunk in chunk_predictions],
        dtype=np.float32,
    )
    normalized_weights = np.asarray(
        [float(chunk["chunk_weight"]) for chunk in chunk_predictions],
        dtype=np.float32,
    )
    if float(np.sum(normalized_weights)) <= 0:
        normalized_weights = np.ones(len(chunk_predictions), dtype=np.float32)
    normalized_weights = normalized_weights / np.sum(normalized_weights)

    aggregated_probabilities = np.sum(probability_matrix * normalized_weights[:, None], axis=0)
    classes = np.asarray(list(model_classes) if model_classes is not None else [0, 1, 2], dtype=int)
    predicted_class = int(classes[int(np.argmax(aggregated_probabilities))])

    cleaned_chunk_predictions = []
    for chunk in chunk_predictions:
        cleaned_chunk = dict(chunk)
        cleaned_chunk.pop("probability_vector", None)
        cleaned_chunk["chunk_weight"] = round(float(cleaned_chunk["chunk_weight"]), 4)
        cleaned_chunk_predictions.append(cleaned_chunk)

    return {
        "stress_level": STRESS_LEVEL_LABELS.get(predicted_class, "Unknown"),
        "stress_level_id": predicted_class,
        "confidence": round(float(np.max(aggregated_probabilities)), 4),
        "probabilities": {
            STRESS_LEVEL_LABELS.get(int(class_id), str(int(class_id))): round(float(probability), 4)
            for class_id, probability in zip(classes, aggregated_probabilities)
        },
        "details": {
            "chunk_predictions": cleaned_chunk_predictions,
            "explanation": generate_explanation(chunk_predictions),
        },
    }
