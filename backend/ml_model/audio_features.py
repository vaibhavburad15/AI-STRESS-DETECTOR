from __future__ import annotations

import wave
from pathlib import Path
from typing import Dict, Tuple

import numpy as np

FRAME_MS = 25
HOP_MS = 10
MIN_F0_HZ = 70
MAX_F0_HZ = 350
N_MELS = 26
N_MFCC = 13

MFCC_MEAN_COLUMNS = [f"mfcc_{index:02d}_mean" for index in range(1, N_MFCC + 1)]
MFCC_STD_COLUMNS = [f"mfcc_{index:02d}_std" for index in range(1, N_MFCC + 1)]
MFCC_DELTA_MEAN_COLUMNS = [f"mfcc_delta_{index:02d}_mean" for index in range(1, N_MFCC + 1)]
MFCC_DELTA_STD_COLUMNS = [f"mfcc_delta_{index:02d}_std" for index in range(1, N_MFCC + 1)]
MFCC_FEATURE_COLUMNS = [
    *MFCC_MEAN_COLUMNS,
    *MFCC_STD_COLUMNS,
    *MFCC_DELTA_MEAN_COLUMNS,
    *MFCC_DELTA_STD_COLUMNS,
]
MEL_FILTERBANK_CACHE: dict[tuple[int, int, int], np.ndarray] = {}
DCT_BASIS_CACHE: dict[tuple[int, int], np.ndarray] = {}

AUDIO_FEATURE_COLUMNS = [
    "duration_sec",
    "rms_mean",
    "rms_std",
    "rms_p90",
    "zcr_mean",
    "zcr_std",
    "centroid_mean",
    "centroid_std",
    "bandwidth_mean",
    "bandwidth_std",
    "rolloff_mean",
    "rolloff_std",
    "flatness_mean",
    "flatness_std",
    *MFCC_FEATURE_COLUMNS,
    "pitch_mean",
    "pitch_std",
    "pitch_range",
    "pitched_frame_ratio",
    "jitter_local",
    "shimmer_local",
    "pause_ratio",
    "voiced_ratio",
    "voiced_rms_mean",
    "voiced_rms_std",
    "speech_turns_per_sec",
    "energy_drift",
]


def load_wav_mono(audio_path: str | Path) -> Tuple[np.ndarray, int]:
    """Load a PCM WAV file, convert to mono, and normalize peak amplitude."""
    path = Path(audio_path)
    with wave.open(str(path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        channels = wav_file.getnchannels()
        frame_count = wav_file.getnframes()
        raw_audio = wav_file.readframes(frame_count)

    if sample_width == 1:
        signal = np.frombuffer(raw_audio, dtype=np.uint8).astype(np.float32)
        signal = (signal - 128.0) / 128.0
    elif sample_width == 2:
        signal = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        signal = np.frombuffer(raw_audio, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(
            f"Unsupported WAV sample width for {path.name}: {sample_width} bytes. "
            "Use PCM WAV files."
        )

    if signal.size == 0:
        raise ValueError(f"Audio file is empty: {path}")

    if channels > 1:
        signal = signal.reshape(-1, channels).mean(axis=1)

    signal = signal - float(np.mean(signal))
    peak = float(np.max(np.abs(signal)))
    if peak > 0:
        signal = signal / peak

    return signal.astype(np.float32), int(sample_rate)


def _frame_signal(signal: np.ndarray, frame_length: int, hop_length: int) -> np.ndarray:
    if signal.size < frame_length:
        signal = np.pad(signal, (0, frame_length - signal.size), mode="constant")

    starts = np.arange(0, signal.size - frame_length + 1, hop_length, dtype=int)
    return np.stack([signal[start : start + frame_length] for start in starts]).astype(np.float32)


def _safe_mean(values: np.ndarray) -> float:
    return float(np.mean(values)) if values.size else 0.0


def _safe_std(values: np.ndarray) -> float:
    return float(np.std(values)) if values.size else 0.0


def _safe_percentile(values: np.ndarray, percentile: float) -> float:
    return float(np.percentile(values, percentile)) if values.size else 0.0


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


def _compute_mfcc_statistics(
    power_spectrum: np.ndarray,
    sample_rate: int,
    frame_length: int,
) -> Dict[str, float]:
    if power_spectrum.size == 0:
        return {feature_name: 0.0 for feature_name in MFCC_FEATURE_COLUMNS}

    mel_filterbank = _build_mel_filterbank(sample_rate=sample_rate, frame_length=frame_length)
    mel_energy = np.maximum(power_spectrum @ mel_filterbank.T, 1e-10)
    log_mel_energy = np.log(mel_energy)
    dct_basis = _build_dct_basis(input_size=mel_filterbank.shape[0], output_size=N_MFCC)
    mfcc_matrix = log_mel_energy @ dct_basis.T
    delta_matrix = np.gradient(mfcc_matrix, axis=0) if len(mfcc_matrix) > 1 else np.zeros_like(mfcc_matrix)

    features: Dict[str, float] = {}
    for coeff_index in range(N_MFCC):
        coefficient = mfcc_matrix[:, coeff_index]
        delta = delta_matrix[:, coeff_index]
        column_index = coeff_index + 1
        features[f"mfcc_{column_index:02d}_mean"] = _safe_mean(coefficient)
        features[f"mfcc_{column_index:02d}_std"] = _safe_std(coefficient)
        features[f"mfcc_delta_{column_index:02d}_mean"] = _safe_mean(delta)
        features[f"mfcc_delta_{column_index:02d}_std"] = _safe_std(delta)

    return features


def _estimate_pitch_track(
    frames: np.ndarray,
    sample_rate: int,
    rms: np.ndarray,
    energy_threshold: float,
) -> np.ndarray:
    window = np.hanning(frames.shape[1]).astype(np.float32)
    min_lag = max(1, int(sample_rate / MAX_F0_HZ))
    max_lag = min(frames.shape[1] - 1, int(sample_rate / MIN_F0_HZ))

    pitches = []
    for index, frame in enumerate(frames):
        if rms[index] < energy_threshold:
            pitches.append(np.nan)
            continue

        centered = (frame - float(np.mean(frame))) * window
        if np.max(np.abs(centered)) < 1e-5:
            pitches.append(np.nan)
            continue

        autocorr = np.correlate(centered, centered, mode="full")[centered.size - 1 :]
        reference = float(autocorr[0])
        if reference <= 0:
            pitches.append(np.nan)
            continue

        search_region = autocorr[min_lag : max_lag + 1]
        if search_region.size == 0:
            pitches.append(np.nan)
            continue

        lag = min_lag + int(np.argmax(search_region))
        peak_value = float(autocorr[lag])
        if peak_value / (reference + 1e-8) < 0.3:
            pitches.append(np.nan)
            continue

        pitches.append(float(sample_rate / lag))

    return np.asarray(pitches, dtype=float)


def extract_audio_features(audio_path: str | Path) -> Dict[str, float]:
    """Extract a compact set of hand-crafted stress-related voice features."""
    signal, sample_rate = load_wav_mono(audio_path)

    frame_length = max(1, int(sample_rate * FRAME_MS / 1000))
    hop_length = max(1, int(sample_rate * HOP_MS / 1000))
    frames = _frame_signal(signal, frame_length=frame_length, hop_length=hop_length)
    duration_sec = max(signal.size / sample_rate, 1e-6)

    rms = np.sqrt(np.mean(np.square(frames), axis=1))
    zcr = np.mean(np.diff(np.signbit(frames), axis=1) != 0, axis=1)

    window = np.hanning(frame_length).astype(np.float32)
    windowed = frames * window
    spectrum = np.abs(np.fft.rfft(windowed, axis=1)) + 1e-8
    power_spectrum = np.square(spectrum)
    freqs = np.fft.rfftfreq(frame_length, d=1.0 / sample_rate)
    spectral_sum = np.sum(spectrum, axis=1)

    centroid = np.sum(spectrum * freqs, axis=1) / spectral_sum
    bandwidth = np.sqrt(
        np.sum(((freqs[None, :] - centroid[:, None]) ** 2) * spectrum, axis=1) / spectral_sum
    )

    cumulative_energy = np.cumsum(spectrum, axis=1)
    rolloff_threshold = 0.85 * cumulative_energy[:, -1]
    rolloff_idx = (cumulative_energy >= rolloff_threshold[:, None]).argmax(axis=1)
    rolloff = freqs[rolloff_idx]

    flatness = np.exp(np.mean(np.log(spectrum), axis=1)) / np.mean(spectrum, axis=1)

    positive_rms = rms[rms > 0]
    median_rms = float(np.median(positive_rms)) if positive_rms.size else 0.0
    energy_threshold = max(0.02, 0.35 * median_rms)
    voiced_mask = rms >= energy_threshold

    pitch = _estimate_pitch_track(frames, sample_rate, rms, energy_threshold)
    valid_pitch = pitch[np.isfinite(pitch)]
    voiced_rms = rms[voiced_mask]

    speech_starts = np.flatnonzero(np.diff(np.r_[0, voiced_mask.astype(int)]) == 1)
    first_half = rms[: max(1, len(rms) // 2)]
    second_half = rms[len(rms) // 2 :]

    pitch_delta = np.abs(np.diff(valid_pitch))
    rms_delta = np.abs(np.diff(voiced_rms))
    mfcc_features = _compute_mfcc_statistics(
        power_spectrum=power_spectrum,
        sample_rate=sample_rate,
        frame_length=frame_length,
    )

    features = {
        "duration_sec": float(duration_sec),
        "rms_mean": _safe_mean(rms),
        "rms_std": _safe_std(rms),
        "rms_p90": _safe_percentile(rms, 90),
        "zcr_mean": _safe_mean(zcr),
        "zcr_std": _safe_std(zcr),
        "centroid_mean": _safe_mean(centroid),
        "centroid_std": _safe_std(centroid),
        "bandwidth_mean": _safe_mean(bandwidth),
        "bandwidth_std": _safe_std(bandwidth),
        "rolloff_mean": _safe_mean(rolloff),
        "rolloff_std": _safe_std(rolloff),
        "flatness_mean": _safe_mean(flatness),
        "flatness_std": _safe_std(flatness),
        **mfcc_features,
        "pitch_mean": _safe_mean(valid_pitch),
        "pitch_std": _safe_std(valid_pitch),
        "pitch_range": (float(np.max(valid_pitch) - np.min(valid_pitch)) if valid_pitch.size else 0.0),
        "pitched_frame_ratio": float(valid_pitch.size / len(frames)),
        "jitter_local": (
            float(np.mean(pitch_delta / np.maximum(valid_pitch[:-1], 1e-6)))
            if valid_pitch.size > 1
            else 0.0
        ),
        "shimmer_local": (
            float(np.mean(rms_delta / np.maximum(voiced_rms[:-1], 1e-6)))
            if voiced_rms.size > 1
            else 0.0
        ),
        "pause_ratio": float(1.0 - np.mean(voiced_mask)),
        "voiced_ratio": float(np.mean(voiced_mask)),
        "voiced_rms_mean": _safe_mean(voiced_rms),
        "voiced_rms_std": _safe_std(voiced_rms),
        "speech_turns_per_sec": float(len(speech_starts) / duration_sec),
        "energy_drift": float(_safe_mean(second_half) - _safe_mean(first_half)),
    }

    return features
