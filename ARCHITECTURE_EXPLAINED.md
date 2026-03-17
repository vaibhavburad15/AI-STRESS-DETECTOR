# AI Stress Level Analyzer — Architecture & Machine Learning Explained
### A Complete Guide for College Presentation & Viva

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Backend Workflow — Step by Step](#2-backend-workflow--step-by-step)
3. [How User Input is Collected (Frontend)](#3-how-user-input-is-collected-frontend)
4. [How Data is Sent to the Backend (API Calls)](#4-how-data-is-sent-to-the-backend-api-calls)
5. [How the Backend Processes Data](#5-how-the-backend-processes-data)
6. [How the ML Model Integrates and Returns Predictions](#6-how-the-ml-model-integrates-and-returns-predictions)
7. [The Dataset Used](#7-the-dataset-used)
8. [Audio Dataset for Voice Stress Detection](#8-audio-dataset-for-voice-stress-detection)
9. [Audio Preprocessing Steps](#9-audio-preprocessing-steps)
10. [How the Machine Learning Models Work](#10-how-the-machine-learning-models-work)
11. [Algorithm Justification & Comparison](#11-algorithm-justification--comparison)
12. [Multimodal Fusion Pipeline](#12-multimodal-fusion-pipeline)
13. [Summary Diagram](#13-summary-diagram)

---

## 1. System Overview

The **AI Stress Level Analyzer** is a full-stack application that detects a user's stress level using:

- A **CBT (Cognitive Behavioral Therapy) questionnaire** — 18 questions answered on a 1–5 scale
- **Voice/audio analysis** — vocal features extracted from recorded speech
- **AI chatbot** — powered by Groq's LLaMA 70B large language model

The system outputs one of four stress classes: **Low, Moderate, High, or Severe**.

Think of it like a digital doctor's assistant that listens to what you say, reads your answers, and uses data science to understand how stressed you are.

---

## 2. Backend Workflow — Step by Step

```
User (Browser)
     │
     │  1. Fills CBT questionnaire (18 questions) or records voice
     ▼
Frontend (React + TypeScript)
     │
     │  2. Sends HTTP POST request with JSON data
     ▼
FastAPI Backend (Python)
     │
     │  3. Validates input, runs ML model / audio extractor
     ▼
ML Model (Ensemble: Random Forest + GBM + Logistic Regression)
     │
     │  4. Returns prediction: stress level + confidence + SHAP explanation
     ▼
FastAPI Backend
     │
     │  5. Saves result to MongoDB, returns JSON response
     ▼
Frontend
     │
     │  6. Displays result, recommendations, charts
     ▼
User sees stress level + personalized advice
```

---

## 3. How User Input is Collected (Frontend)

### 3.1 CBT Questionnaire (Text Input)

The user answers **18 questions** covering five categories:

| Category      | Questions                                                         |
|---------------|-------------------------------------------------------------------|
| Emotional     | Feeling nervous/anxious, sad/depressed, irritable/angry           |
| Physical      | Headaches, fatigue, sleep trouble, rapid heartbeat                |
| Cognitive     | Difficulty concentrating, negative thoughts, worry about future   |
| Behavioral    | Appetite changes, avoiding social interactions, feeling overwhelmed|
| Stressors     | Work-life balance, work/study stress, relationship, financial stress|

Each question is rated **1 (never) to 5 (always)**.

> **Analogy:** It's like a health survey a doctor gives you before an appointment — the answers paint a picture of your mental state.

### 3.2 Voice Input

The user can record their voice. The browser captures audio in WAV format and sends it to the backend. The system then extracts **vocal stress biomarkers** from the recording.

---

## 4. How Data is Sent to the Backend (API Calls)

The frontend (React) sends data using **HTTP POST** requests via the **Axios** library to the FastAPI backend.

### Questionnaire Submission Example

```
POST /api/user/submit-test
Authorization: Bearer <JWT Token>
Content-Type: application/json

{
  "responses": [3, 4, 2, 5, 3, 4, 2, 3, 4, 3, 2, 1, 4, 3, 5, 4, 3, 2]
}
```

### Voice Submission Example

```
POST /api/user/submit-audio
Authorization: Bearer <JWT Token>
Content-Type: multipart/form-data

audio_file: <recorded.wav>
```

- The backend is secured with **JWT (JSON Web Token)** authentication.
- Every request must include a valid token in the `Authorization` header.
- FastAPI validates the token before processing any data.

---

## 5. How the Backend Processes Data

The backend is built with **FastAPI** (a modern Python web framework). Here is what happens when a request arrives:

### Step 1 — Authentication Check
FastAPI checks the JWT token. If invalid → returns HTTP 401 Unauthorized.

### Step 2 — Input Validation (Pydantic)
FastAPI uses **Pydantic models** to validate the incoming data:
- Exactly 18 integer responses?
- Each value between 1 and 5?
- Valid audio file format?

If not → returns HTTP 422 Unprocessable Entity.

### Step 3 — ML Prediction
The validated data is passed to the appropriate predictor:
- `StressPredictor.predict_with_explanation(responses)` — for questionnaire
- `AudioStressPredictor.predict_from_wav(audio_path)` — for voice

### Step 4 — Save to Database
The result (stress level, score, timestamp) is stored in **MongoDB**.

### Step 5 — Return Response
A structured JSON response is returned:

```json
{
  "stress_level": 2,
  "stress_label": "High",
  "confidence": 0.87,
  "continuous_score": 66.5,
  "probabilities": { "Low": 0.05, "Moderate": 0.08, "High": 0.87, "Severe": 0.00 },
  "recommendations": ["Consider scheduling an appointment with a mental health professional..."],
  "category_scores": { "emotional": {"average": 4.0, "severity": "severe"}, ... },
  "risk_factors": [{"factor": "sleep_disruption", "severity": "high", ...}]
}
```

---

## 6. How the ML Model Integrates and Returns Predictions

### Model Loading at Startup

When the FastAPI server starts, the model is **loaded from disk** once into memory:

```python
# predictor.py
predictor = StressPredictor()  # loads stress_model.pkl at import time
```

This means predictions are near-instant — no reloading for each request.

### Auto-Retraining Safety

If the model file is missing or corrupted, the system **automatically retrains** itself from the training CSV dataset.

### SHAP Explainability

After prediction, the system uses **SHAP (SHapley Additive exPlanations)** — a technique from game theory — to explain *why* the model made that prediction:

> "Your stress is High mainly because of your responses to Sleep trouble (q6) and Overwhelmed by tasks (q14)."

This makes the AI **transparent and explainable** — not a black box.

---

## 7. The Dataset Used

### 7.1 CBT Questionnaire Dataset

- **File:** `stress_training_dataset_100k.csv`
- **Size:** 100,000 synthetic samples (plus real user data added over time)
- **Format:** 18 feature columns (`q1` to `q18`) + 1 label column (`stress_level`)
- **Labels:** 0 = Low, 1 = Moderate, 2 = High, 3 = Severe

**Example Row:**
```
q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11, q12, q13, q14, q15, q16, q17, q18, stress_level
 3,  4,  2,  5,  3,  4,  2,  3,  4,   3,   2,   1,   4,   3,   5,   4,   3,   2,          2
```

**How synthetic data is generated:**
- Low stress (0): responses randomly between 1–2
- Moderate stress (1): responses randomly between 2–3
- High stress (2): responses randomly between 3–4
- Severe stress (3): responses randomly between 4–5
- Small random noise (±1) is added to make it realistic

### 7.2 Train/Test Split

The dataset is split **80% training / 20% testing** using stratified sampling:

```python
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
```

> **Stratified** means each stress class (Low/Moderate/High/Severe) is proportionally represented in both train and test sets. This prevents the model from being biased toward the majority class.

---

## 8. Audio Dataset for Voice Stress Detection

The project uses **two public emotional speech datasets** to train the audio stress model:

### 8.1 EmoDB (Berlin Emotional Speech Database)

- **Origin:** Technical University of Berlin, Germany
- **Speakers:** 10 actors (5 male, 5 female)
- **Files:** ~535 WAV audio recordings
- **Language:** German
- **Emotions:** Anger, Boredom, Disgust, Fear, Happiness, Sadness, Neutral
- **Mapped to Stress:** Anger + Fear → High/Severe stress; Neutral/Happiness → Low stress
- **Location in project:** `data/public/emodb/wav/`

### 8.2 RAVDESS (Ryerson Audio-Visual Database of Emotional Speech and Song)

- **Origin:** Ryerson University, Canada
- **Speakers:** 24 professional actors (12 male, 12 female)
- **Files:** 60 files per actor × 24 = ~1,440 WAV recordings (16kHz versions used)
- **Emotions:** Neutral, Calm, Happy, Sad, Angry, Fearful, Disgust, Surprised
- **Mapped to Stress:** Angry + Fearful → High stress; Calm + Neutral → Low stress
- **Location in project:** `data/public/ravdess_16k/Audio_Speech_Actors_01-24_16k/`

### 8.3 Why Use Emotion Datasets for Stress?

Stress in voice is closely related to emotional state. Emotions like **anger, fear, and anxiety** produce measurable physiological changes in speech — faster rate, higher pitch, trembling voice. By mapping these emotions to stress levels, we can train a stress-specific classifier.

---

## 9. Audio Preprocessing Steps

### Step 1 — Load and Normalize WAV File

The audio file is loaded as a raw PCM waveform and converted to mono (single channel). The amplitude is normalized to a range of –1.0 to +1.0.

```
Stereo WAV → Mix to Mono → Normalize Amplitude → Float32 Array
```

### Step 2 — Frame the Signal

The continuous audio is split into small overlapping **frames**:
- Frame size: **25 ms**
- Hop size (step between frames): **10 ms**

> **Analogy:** Imagine reading a long text by looking through a sliding window — each window shows only 25 characters, and you slide it 10 characters forward each time.

### Step 3 — Feature Extraction

For each frame, the following **acoustic features** are extracted:

#### a) Energy Features (How loud/intense?)
| Feature        | Meaning                                          |
|----------------|--------------------------------------------------|
| `rms_mean`     | Average energy (loudness) across frames          |
| `rms_std`      | Variation in loudness                            |
| `rms_p90`      | 90th percentile energy (peak loudness)           |

#### b) Zero-Crossing Rate (How noisy?)
- `zcr_mean` / `zcr_std`: How often the signal crosses zero (indicates breathiness/noise)

#### c) Spectral Features (What frequencies dominate?)
| Feature            | Meaning                                                 |
|--------------------|---------------------------------------------------------|
| `centroid_mean`    | "Center of gravity" of frequency spectrum (brightness)  |
| `bandwidth_mean`   | Spread of frequencies                                   |
| `rolloff_mean`     | Frequency below which 85% of energy is concentrated    |
| `flatness_mean`    | How noise-like vs. tonal the voice sounds               |

#### d) MFCC — Mel-Frequency Cepstral Coefficients (The Gold Standard)

MFCCs are the **most important features** in speech/stress analysis.

**How MFCCs are computed:**

```
Audio Frame
    ↓
Apply Hanning Window (reduces edge effects)
    ↓
Compute FFT (convert time domain → frequency domain)
    ↓
Apply Mel Filterbank (26 filters, matches human hearing perception)
    ↓
Take Log of filter energies
    ↓
Apply DCT (compress to 13 coefficients)
    ↓
13 MFCC values per frame
```

The system computes:
- **13 MFCC mean values** (average shape of voice spectrum)
- **13 MFCC standard deviations** (how much the spectrum varies)
- **13 MFCC delta means** (rate of change — captures dynamics)
- **13 MFCC delta std** (variation in rate of change)

> **Why Mel scale?** Human hearing is not linear — we are more sensitive to differences at low frequencies. The Mel scale maps frequencies to match human perception.

#### e) Pitch Features (Voice Tone)
| Feature               | Meaning                                       |
|-----------------------|-----------------------------------------------|
| `pitch_mean`          | Average fundamental frequency (Hz) of voice  |
| `pitch_std`           | Pitch variation (monotone vs. expressive)     |
| `pitch_range`         | Max – Min pitch (emotional range)             |
| `jitter_local`        | Cycle-to-cycle pitch irregularity             |
| `shimmer_local`       | Cycle-to-cycle amplitude irregularity         |

Stressed voices typically show **higher pitch, more pitch variation, and increased jitter**.

#### f) Temporal / Speech Pattern Features
| Feature                | Meaning                                           |
|------------------------|---------------------------------------------------|
| `pause_ratio`          | Proportion of silence (stressed = more pauses)   |
| `voiced_ratio`         | Proportion of speech vs. silence                 |
| `speech_turns_per_sec` | How frequently new speech segments begin         |
| `energy_drift`         | Whether energy increases or decreases over time  |

**Total features extracted per audio sample: ~83 numerical values**

### Step 4 — Feature Aggregation

All per-frame features are summarized into a **single row** (mean, std, percentile) to represent the entire audio clip as one fixed-length feature vector.

### Step 5 — Train/Test Split (Speaker-Independent)

To prevent the model from "memorizing" specific speakers, a **Group Shuffle Split** is used:
- All recordings from a speaker go entirely into train OR test — never both
- This tests true generalization to new, unseen voices

---

## 10. How the Machine Learning Models Work

### 10.1 Questionnaire Model — Calibrated Ensemble

The final questionnaire model is a **soft-voting ensemble** of three algorithms:

```
Input: 18 answers (q1 to q18), each between 1 and 5
          ↓
┌──────────────────────────────────────────────────────┐
│           Ensemble (Soft Voting)                     │
│                                                      │
│  [Random Forest × 150 trees] ──── weight 2          │
│  [Gradient Boosting × 150 trees] ── weight 2        │
│  [Logistic Regression] ──────────── weight 1        │
└──────────────────────────────────────────────────────┘
          ↓
   Probability Calibration (Isotonic Regression)
          ↓
Output: Probabilities for Low / Moderate / High / Severe
          ↓
   Highest probability → Predicted Stress Level
```

**Continuous score calculation:**
```python
weights = [0, 33.3, 66.6, 100.0]
continuous_score = probabilities[0]*0 + probabilities[1]*33.3 + probabilities[2]*66.6 + probabilities[3]*100
# Example: [0.05, 0.08, 0.87, 0.00] → score = 58.7 / 100
```

### 10.2 Audio Model — Competition Between 4 Candidates

The system trains **4 candidate models** and automatically picks the best:

| Candidate         | Algorithm                                          |
|-------------------|----------------------------------------------------|
| `ensemble_v1`     | Random Forest + Extra Trees + Logistic Regression  |
| `svc_rbf_v1`      | Support Vector Machine (RBF kernel) + Scaler       |
| `extra_trees_v1`  | Extra Trees Classifier (500 trees)                 |
| `logreg_v1`       | Logistic Regression + StandardScaler               |

The model with the **highest balanced accuracy** (accounts for class imbalance) is saved as the production model.

### 10.3 What Happens During Prediction

```python
# 1. Input arrives as 18 integers
responses = [3, 4, 2, 5, 3, 4, 2, 3, 4, 3, 2, 1, 4, 3, 5, 4, 3, 2]

# 2. Model predicts class probabilities
probabilities = [0.05, 0.08, 0.87, 0.00]
# → Low=5%, Moderate=8%, High=87%, Severe=0%

# 3. Pick highest → class 2 → "High"
prediction = 2
confidence = 0.87

# 4. Continuous score
continuous_score = 66.5  # out of 100

# 5. SHAP explanation
# "Sleep trouble (q6) and Overwhelmed by tasks (q14) are your top stress drivers"
```

---

## 11. Algorithm Justification & Comparison

### Why Use an Ensemble (Random Forest + GBM + Logistic Regression)?

Here is a comparison of the main algorithms considered:

| Algorithm            | Accuracy | Handles Small Data | Interpretability | Speed       | Notes                                   |
|----------------------|----------|--------------------|------------------|-------------|-----------------------------------------|
| **Random Forest**    | ★★★★★   | ★★★★★             | ★★★☆☆           | ★★★★☆      | Best overall for tabular data           |
| **Gradient Boosting**| ★★★★★   | ★★★★☆             | ★★★☆☆           | ★★★☆☆      | Sequential; great at fixing errors      |
| **Logistic Regression** | ★★★☆☆ | ★★★★★           | ★★★★★           | ★★★★★      | Simple, fast, good baseline             |
| **SVM (RBF)**        | ★★★★☆   | ★★★★★             | ★★☆☆☆           | ★★★☆☆      | Great for audio features with scaling   |
| **Neural Networks**  | ★★★★★   | ★★☆☆☆             | ★☆☆☆☆           | ★★☆☆☆      | Needs huge data; overkill for 18 features |
| **Decision Tree**    | ★★★☆☆   | ★★★★☆             | ★★★★★           | ★★★★★      | Overfits; not robust alone              |
| **KNN (K-Nearest Neighbors)** | ★★★☆☆ | ★★★☆☆    | ★★★★☆           | ★★☆☆☆      | Slow at inference; no model stored      |

### Detailed Comparison

#### Random Forest vs. Decision Tree
A Decision Tree is like asking a series of yes/no questions:
> "Is q6 (sleep trouble) ≥ 4? Yes → Is q1 (anxious) ≥ 3? Yes → Severe"

The problem: A single tree **overfits** — it memorizes training data but fails on new data.

A **Random Forest** grows **150 independent trees**, each trained on a random subset of data and features, then votes:
> "100 trees say High, 30 say Severe, 20 say Moderate → predict High"

This dramatically reduces overfitting and improves accuracy.

#### Random Forest vs. Neural Networks
- Neural Networks need **thousands to millions of samples** to learn effectively.
- With only 18 input features and even 100,000 rows, a simple neural net would not significantly outperform Random Forest.
- Random Forest is also **faster to train, easier to debug**, and produces **feature importances** for interpretability.
- Neural Networks are black boxes — hard to explain. SHAP works natively with tree models.

#### Random Forest vs. KNN
- KNN stores all training data and classifies new points by finding the K nearest neighbors.
- Problem: **Slow at inference** (must compare against all training points), and **sensitive to irrelevant features**.
- Random Forest stores only the trained model, making prediction near-instant.

#### SVM vs. Others (for Audio Features)
SVM with an RBF (Radial Basis Function) kernel is excellent for audio because:
- Audio features (MFCC, pitch) need **normalization** — SVM + StandardScaler handles this well.
- Works effectively on **medium-sized datasets** (hundreds to a few thousand samples).
- The RBF kernel can find non-linear decision boundaries in high-dimensional feature space.

#### Why Use an Ensemble?
> "Don't put all your eggs in one basket."

Each algorithm has different strengths and weaknesses. By combining them with **soft voting** (averaging their probability outputs), the ensemble:
- Is more **robust** to noisy inputs
- Reduces the risk of one algorithm's mistakes dominating
- Achieves higher accuracy than any single model alone

The weights are: **Random Forest ×2, GBM ×2, Logistic Regression ×1** — tree models are trusted more for this tabular problem.

---

## 12. Multimodal Fusion Pipeline

When voice data is also available, the system fuses **text + audio + sentiment** signals:

```
Text (questionnaire avg)     → normalized to 0–1 signal
Audio (trained model)        → normalized stress score 0–1
Sentiment (chat messages)    → positive/negative score 0–1
Facial expression (optional) → stress signal 0–1

         ↓ Weighted Average ↓

Fusion Weights (when audio confidence ≥ 70%):
  Text:      55%
  Audio:     30%
  Sentiment: 10%
  Face:       5%

         ↓

Fused Signal → Thresholds → Stress Level
  0.00–0.30 → Low
  0.30–0.55 → Moderate
  0.55–0.80 → High
  0.80–1.00 → Severe
```

If audio confidence is lower, the text signal is weighted higher (up to 80%), making the system **adaptive and fault-tolerant**.

---

## 13. Summary Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER (Browser)                           │
│  ┌──────────────┐   ┌───────────────┐   ┌──────────────────┐  │
│  │ 18-Question  │   │  Voice Record │   │   AI Chatbot     │  │
│  │ CBT Survey   │   │  (WAV file)   │   │ (LLaMA 70B)      │  │
│  └──────┬───────┘   └──────┬────────┘   └────────┬─────────┘  │
└─────────┼──────────────────┼─────────────────────┼─────────────┘
          │ POST /submit-test │ POST /submit-audio  │ POST /chat
          ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Python)                       │
│  JWT Auth → Pydantic Validation → Route Handler                 │
│                                                                  │
│  ┌─────────────────┐     ┌──────────────────────────────────┐   │
│  │  StressPredictor│     │     AudioStressPredictor         │   │
│  │  (Ensemble ML)  │     │  extract_audio_features() →      │   │
│  │  18 features    │     │  83 MFCC/pitch/energy features   │   │
│  │  → Low/Mod/High │     │  → predict stress level          │   │
│  │  /Severe + SHAP │     │                                  │   │
│  └────────┬────────┘     └──────────────┬───────────────────┘   │
│           └──────────────┬──────────────┘                        │
│                          ▼                                        │
│               MultimodalPipeline.assess()                        │
│          (Fuse text + audio + sentiment)                         │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
                     MongoDB Database
                  (store result + history)
                           ▼
              JSON Response → Frontend Charts,
              Recommendations, Risk Alerts
```

---

## Key Technical Terms Glossary

| Term                  | Simple Explanation                                                          |
|-----------------------|-----------------------------------------------------------------------------|
| **FastAPI**           | A fast Python web framework for building APIs                               |
| **JWT**               | JSON Web Token — a secure digital "ID card" for API authentication          |
| **Pydantic**          | A Python library that validates data types automatically                    |
| **Random Forest**     | Many decision trees voting together for a better prediction                 |
| **Gradient Boosting** | Trees trained sequentially, each one fixing the previous one's mistakes     |
| **MFCC**              | Compact numerical representation of voice spectrum (13 coefficients)        |
| **SHAP**              | A method to explain why the model made a specific prediction                |
| **Ensemble**          | Combining multiple ML models to get better results than any single model    |
| **Stratified Split**  | Train/test split that keeps class proportions balanced                      |
| **Mel Filterbank**    | A set of frequency filters that mimic how humans hear                       |
| **Jitter / Shimmer**  | Micro-variations in pitch / loudness — indicators of vocal stress           |
| **MongoDB**           | A NoSQL database that stores data as flexible JSON-like documents           |
| **CBT**               | Cognitive Behavioral Therapy — a structured psychological assessment method |

---

*This document covers the complete architecture and ML methodology of the AI Stress Level Analyzer project, suitable for academic viva, college presentations, and technical reviews.*
