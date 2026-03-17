# Voice Stress Training Guide

## Current repo status

Your current project predicts stress mainly from the 18-question questionnaire. The video path adds `audio_features` and `facial_features`, but the fusion model is trained on synthetic/random data, not on real labeled voice samples.

That means the project is good for a demo, but it is not yet a true production voice-stress model.

## What improves the model most

1. Use real labeled audio instead of synthetic scores.
2. Split train/test by `speaker_id`, not by clip, so the model is tested on new people.
3. Balance the dataset across `low`, `moderate`, `high`, and `severe`.
4. Keep recording conditions diverse: phone, laptop, quiet room, noisy room, different genders, ages, accents, and speaking styles.
5. Use labels from a questionnaire score or clinician review collected at the same time as the recording.

## Realistic accuracy target

`90%` can be possible only when:

- labels are high quality
- speakers are balanced across classes
- train/test split is speaker-independent
- the dataset is large enough

For real-world voice-only stress detection, `90%` is ambitious. Many teams get inflated numbers because the same speaker appears in both train and test, or because they test on synthetic data. If you want a believable `90%`, measure it on unseen speakers.

## Recommended dataset

Aim for this minimum:

- `150+` speakers
- `20-40` clips per speaker
- `4,000-8,000` total clips
- `20-60` seconds per clip
- same stress label recorded near the same time as the clip

Recommended manifest fields:

- `sample_id`
- `audio_path`
- `stress_label`
- `stress_level`
- `speaker_id`
- `split`
- `language`
- `assignment_id`
- `recording_device`
- `environment`
- `transcript`

## Clinical dataset path now supported

This repo now includes a DAIC-WOZ preparation script:

- [prepare_daic_woz_manifest.py](/c:/Project/AI-STRESS-DETECTOR/backend/ml_model/prepare_daic_woz_manifest.py)

What it does:

1. reads licensed DAIC-WOZ split CSV files with participant ids and PHQ scores
2. finds `*_AUDIO.wav` interviews under the dataset root
3. uses `*_TRANSCRIPT.csv` files when available to cut participant-only speech segments
4. maps PHQ score ranges into your app's `low/moderate/high/severe` classes
5. writes a training manifest compatible with the existing audio trainer

Important caveat:

- this is much stronger than emotion-to-stress proxy mapping, but it is still an inference from clinical questionnaire severity to your 4 stress classes
- if you collect your own in-app questionnaire labels at recording time, that is still the cleanest label source

### DAIC-WOZ workflow

```powershell
python backend/ml_model/prepare_daic_woz_manifest.py `
  --dataset-root data/private/daic_woz `
  --output-csv backend/ml_model/daic_woz_stress_manifest.csv `
  --segments-root data/private/daic_woz_segments
```

Then train directly from that manifest:

```powershell
python backend/ml_model/train_audio_stress_model.py `
  --manifest backend/ml_model/daic_woz_stress_manifest.csv
```

Use the template here:

- [audio_stress_manifest_template.csv](/c:/Project/AI-STRESS-DETECTOR/backend/ml_model/audio_stress_manifest_template.csv)

## Recommended folder layout

```text
data/
  audio/
    low/
      speaker_01/
        clip_01.wav
    moderate/
      speaker_02/
        clip_01.wav
    high/
      speaker_03/
        clip_01.wav
    severe/
      speaker_04/
        clip_01.wav
```

Use PCM WAV files when possible. The included extractor reads `.wav` files directly.

## Workflow added to this repo

### 1. Build a manifest

If your audio is already arranged by label folders:

```powershell
python backend/ml_model/audio_dataset_tools.py scan `
  --input-root data/audio `
  --output-csv backend/ml_model/audio_stress_manifest.csv
```

### 2. Build tabular audio features

```powershell
python backend/ml_model/audio_dataset_tools.py featurize `
  --manifest backend/ml_model/audio_stress_manifest.csv `
  --dataset-root data/audio `
  --output-csv backend/ml_model/audio_stress_features.csv
```

### 3. Train the audio model

```powershell
python backend/ml_model/train_audio_stress_model.py `
  --features-csv backend/ml_model/audio_stress_features.csv
```

You can also train directly from the manifest:

```powershell
python backend/ml_model/train_audio_stress_model.py `
  --manifest backend/ml_model/audio_stress_manifest.csv `
  --dataset-root data/audio
```

## Features used by the new training script

The new baseline extracts hand-crafted voice features such as:

- energy / RMS
- zero-crossing rate
- spectral centroid and bandwidth
- rolloff and spectral flatness
- pitch mean and pitch variation
- jitter and shimmer proxies
- pause ratio and voiced ratio
- speaking-turn density

This is a solid baseline for a classical ML model. Later, you can improve it further with:

1. wav2vec2 / HuBERT embeddings
2. transcript sentiment and speech disfluency features
3. face-expression features from the same video
4. calibration on your own users

## Best labeling strategy

For each submitted video assignment:

1. collect the user's recorded answer
2. ask the user to complete the questionnaire immediately after recording
3. convert the questionnaire total or class into `stress_level`
4. store the `speaker_id`, timestamp, and recording context
5. review uncertain samples manually

That gives you a real supervised dataset tied to your own app.

## Important warning

Do not claim `90%` unless:

- test speakers are never seen during training
- the class distribution is balanced
- you report confusion matrix and balanced accuracy, not only raw accuracy

The new trainer already prefers speaker-aware evaluation when `speaker_id` is available.
