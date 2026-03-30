# ML Models Used in This Project

This file explains:

- which ML/AI model is used
- which algorithm is behind it
- why that algorithm is used
- where it is used in the project

## 1. Main Stress Prediction Model

| Item | Details |
|---|---|
| Model name | Main questionnaire stress predictor |
| Algorithm used | Soft-voting ensemble of `RandomForestClassifier`, `GradientBoostingClassifier`, and `LogisticRegression`, with `CalibratedClassifierCV` for probability calibration |
| Why we use it | The questionnaire data is structured tabular data with 18 fixed inputs. Random Forest and Gradient Boosting handle non-linear relationships well, while Logistic Regression adds a simpler linear view. Soft voting combines their strengths. Calibration makes confidence scores more reliable. |
| Where it is used | Final stress prediction for the normal questionnaire flow and also for the video assessment flow after verbal/audio signals are converted into 18 scores |
| Main files | `backend/ml_model/train_model.py`, `backend/ml_model/predictor.py`, `backend/app/routes/user_dashboard_routes.py` |
| Input | 18 questionnaire responses (`q1` to `q18`) |
| Output | `Low`, `Moderate`, `High`, or `Severe` stress with confidence, continuous score, recommendations, category analysis, and explanation |

### Notes

- This is the most important prediction model in the project.
- Even in the video assessment flow, the final stored result is still produced by this model.

## 2. Explainability Model

| Item | Details |
|---|---|
| Model name | SHAP-compatible explanation model |
| Algorithm used | `RandomForestClassifier` + `SHAP TreeExplainer` |
| Why we use it | The project should not behave like a black box. SHAP helps explain which questions influenced the result the most. |
| Where it is used | In test explanation, top stress factors, feature impact, and explainability output |
| Main files | `backend/ml_model/predictor.py`, `data/runtime_models/stress_model_shap.pkl` |
| Input | Weighted questionnaire features |
| Output | Top contributing questions and their impact direction |

### Notes

- This model is used for explanation, not as the main final predictor.

## 3. Verbal Response Scorer

| Item | Details |
|---|---|
| Model name | Verbal response neural scorer |
| Algorithm used | `TfidfVectorizer` + `MLPClassifier` |
| Why we use it | In the video assessment, users answer in natural language, not just numbers. This model converts free-text answers into 1-5 stress scores that match the questionnaire format. TF-IDF converts text into numeric vectors, and MLP learns patterns such as "often", "always", "not at all", "overwhelmed", etc. |
| Where it is used | Video assessment flow before multimodal fusion |
| Main files | `backend/ml_model/verbal_nn_scorer.py`, `backend/ml_model/multimodal_pipeline.py` |
| Input | 18 spoken or typed verbal responses |
| Output | 18 numeric scores from 1 to 5, plus average confidence |

### Notes

- This is not the final stress classifier.
- It acts like a converter from natural language to questionnaire-style scores.

## 4. Voice Stress Model

| Item | Details |
|---|---|
| Model name | Audio stress predictor |
| Algorithm used | Current saved model: `XGBClassifier` (XGBoost). Training code also evaluates `RandomForestClassifier` as a candidate. |
| Why we use it | Audio features are complex and non-linear. XGBoost works well on tabular feature vectors and can capture stronger decision boundaries than simple rules. It is also effective for structured acoustic features like MFCCs, RMS, chroma, and spectral contrast. |
| Where it is used | Direct voice upload prediction and as an audio signal source in the video assessment pipeline |
| Main files | `backend/ml_model/train_audio_stress_model.py`, `backend/ml_model/audio_stress_predictor.py`, `backend/ml_model/audio_features.py`, `backend/ml_model/audio_stress_model_meta.json` |
| Input | Extracted audio feature vector from voice/audio clip |
| Output | Voice-based stress level, confidence, and normalized stress signal |

### Notes

- The direct voice endpoint uses this model.
- The multimodal video flow may also use this model through `predict_from_features(...)`.
- The current saved metadata shows `XGBClassifier` as the selected audio model.

## 5. Audio Feature Extraction Pipeline

| Item | Details |
|---|---|
| Model name | Hand-crafted audio feature pipeline |
| Algorithm used | Signal preprocessing + feature engineering, not a trained ML model by itself |
| Why we use it | Raw audio cannot be fed directly into classical ML models used here. The system first converts the waveform into numerical acoustic features such as MFCC, MFCC delta, MFCC delta2, RMS, ZCR, chroma, and spectral contrast. |
| Where it is used | Audio training and audio inference |
| Main files | `backend/ml_model/audio_features.py` |
| Input | Audio waveform |
| Output | Numeric feature vector for the audio classifier |

### Notes

- This is a preprocessing and feature-extraction stage, not the final classifier.

## 6. Multimodal Video Assessment Logic

| Item | Details |
|---|---|
| Model name | Multimodal stress fusion pipeline |
| Algorithm used | Deterministic weighted signal fusion, not a trained deep multimodal neural network |
| Why we use it | It is lightweight, explainable, and works even when some signals are weak or missing. It combines text score, audio stress signal, sentiment signal, and face stress signal in a controlled way. |
| Where it is used | Video assessment endpoint |
| Main files | `backend/ml_model/multimodal_pipeline.py`, `backend/app/routes/user_dashboard_routes.py` |
| Input | Verbal responses, audio features, facial features, sentiment features |
| Output | Fused signal, fused confidence, adjusted questionnaire-style scores |

### Notes

- This pipeline does not directly replace the final questionnaire model.
- It prepares or adjusts the scores before they are sent into the main predictor.

## 7. Chatbot AI Model

| Item | Details |
|---|---|
| Model name | AI stress counselor chatbot |
| Algorithm used | Groq-hosted LLaMA family language model, with configured model fallback |
| Why we use it | It supports free conversation, empathy, and rough conversational stress estimation. This is useful when the user wants help beyond the structured questionnaire. |
| Where it is used | Chatbot route |
| Main files | `backend/app/routes/user_dashboard_routes.py` |
| Input | User chat message |
| Output | Supportive chatbot response and optional detected stress estimate |

### Notes

- This is separate from the main questionnaire ML pipeline.
- It is more for interactive support than for the core formal stress test.

## 8. Quick Summary Table

| Project part | Model / algorithm | Why used | Where used |
|---|---|---|---|
| Main stress test | RF + GBM + LR soft-voting ensemble + calibration | Strong for tabular questionnaire data, balanced and reliable confidence | Questionnaire submit flow and final prediction in video flow |
| Explainability | Random Forest + SHAP | To show why the prediction happened | Test explanation and factor analysis |
| Verbal answer scoring | TF-IDF + MLP | To convert free-text answers into 1-5 scores | Video assessment |
| Voice stress prediction | XGBoost classifier on audio features | Good for non-linear acoustic feature patterns | Audio upload and multimodal audio signal |
| Audio preprocessing | MFCC/RMS/ZCR/chroma/spectral contrast extraction | To convert sound into numbers | Audio model training and inference |
| Multimodal fusion | Weighted signal fusion | Lightweight and explainable signal combination | Video assessment |
| Chatbot | LLaMA-based LLM via Groq | Conversational support and stress-aware chat | Chatbot feature |

## 9. Most Important Viva Point

If someone asks, "What is the main ML model of your project?", the best answer is:

> The main stress prediction model is a calibrated soft-voting ensemble of Random Forest, Gradient Boosting, and Logistic Regression, used on the 18-question CBT questionnaire. The project also includes a verbal-response scorer, an audio stress model based on XGBoost, and a weighted multimodal fusion pipeline for the video assessment flow.

## 10. Important Clarification

Some older project descriptions mention only Random Forest, but the current codebase uses a stronger ensemble for the main questionnaire prediction.
