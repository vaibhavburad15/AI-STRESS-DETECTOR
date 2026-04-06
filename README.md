# AI Stress Level Analyzer

A comprehensive full-stack web application for **AI-powered stress detection** using **Cognitive Behavioral Therapy (CBT) principles** and **Machine Learning**. The system collects user responses to an 18-question CBT-based questionnaire, feeds them into a trained Random Forest Classifier, and predicts one of four stress levels with confidence scoring and personalized recommendations.

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Machine Learning: In-Depth](#machine-learning-in-depth)
  - [What is Machine Learning?](#what-is-machine-learning)
  - [Types of Machine Learning](#types-of-machine-learning)
  - [Algorithm Used: Random Forest Classifier](#algorithm-used-random-forest-classifier)
  - [How the Stress Prediction Pipeline Works](#how-the-stress-prediction-pipeline-works)
  - [Training Data and Feature Engineering](#training-data-and-feature-engineering)
  - [Model Performance](#model-performance)
  - [Feature Importance Analysis](#feature-importance-analysis)
  - [AI Chatbot: Real-Time Stress Detection](#ai-chatbot-real-time-stress-detection)
  - [Continuous Learning Strategy](#continuous-learning-strategy)
- [CBT Questionnaire Design](#cbt-questionnaire-design)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Database Configuration](#database-configuration)
- [API Endpoints](#api-endpoints)
- [Stress Level Recommendations](#stress-level-recommendations)
- [Gamification and Progress Tracking](#gamification-and-progress-tracking)
- [Security Features](#security-features)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [License](#license)

---

## Features

### Three Dashboard System

#### 1. User Dashboard
- User registration with email OTP verification
- **18-question CBT-based stress assessment**
- **ML-powered stress level prediction** (Low / Moderate / High / Severe)
- **24/7 AI Stress Counselor** chatbot with automatic stress detection
- Personalized, categorized recommendations (immediate relief, daily habits, weekly goals, lifestyle changes)
- View test history with trend analysis
- Book appointments with verified doctors
- Upload and manage medical records
- Gamification: badges, streaks, points, and leveling system

#### 2. Doctor Dashboard
- Doctor registration with NMC license validation (format: 2 letters + 6-8 digits, e.g., `MD123456`)
- View scheduled appointments with patient stress data
- Access patient's complete test history
- Approve/reject appointments and add consultation notes
- Track appointment statistics

#### 3. Admin Dashboard
- Comprehensive statistics dashboard with data visualization
- User management (view all users, tests, activity)
- Doctor management (verify licenses, activate/deactivate accounts)
- Appointment oversight
- Stress level distribution charts, user registration trends, and appointment status breakdowns

---

## Architecture Overview

```
+-------------------+          +--------------------+         +------------------+
|                   |   HTTP   |                    |  Query  |                  |
|  React Frontend   +--------->+  FastAPI Backend   +-------->+     MongoDB      |
|  (TypeScript)     |   REST   |  (Python)          |         |   (Database)     |
|                   |<---------+                    |<--------+                  |
+-------------------+          +---------+----------+         +------------------+
                                         |
                              +----------+----------+
                              |                     |
                    +---------v--------+  +---------v--------+
                    |  ML Model        |  |  Groq LLM API    |
                    |  (Random Forest) |  |  (AI Chatbot)    |
                    |  scikit-learn    |  |  llama-3.3-70b   |
                    +------------------+  +------------------+
```

---

## Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| **Python 3.10+** | Core backend language |
| **FastAPI** | Async REST API framework |
| **MongoDB (PyMongo)** | NoSQL document database |
| **scikit-learn** | Machine learning model training and inference |
| **NumPy / Pandas** | Data manipulation and numerical computation |
| **JWT (PyJWT)** | Token-based authentication |
| **bcrypt** | Password hashing |
| **Pydantic** | Request/response data validation |
| **Groq SDK** | LLM-powered AI chatbot |
| **aiosmtplib** | Async email for OTP verification |

### Frontend
| Technology | Purpose |
|---|---|
| **React 18** | UI library |
| **TypeScript** | Type-safe JavaScript |
| **Vite** | Build tool and dev server |
| **Tailwind CSS** | Utility-first CSS framework |
| **Axios** | HTTP client for API calls |
| **React Router** | Client-side routing |
| **Lucide React** | Icon library |

---

## Machine Learning: In-Depth

### What is Machine Learning?

Machine Learning (ML) is a subset of Artificial Intelligence that enables systems to **learn from data** and **improve their performance** without being explicitly programmed for every scenario. Instead of writing rigid rules (e.g., "if score > 60, then high stress"), an ML model discovers patterns and relationships in training data and uses those learned patterns to make predictions on new, unseen data.

The core workflow is:

1. **Data Collection** -- Gather labeled examples (inputs paired with known outcomes).
2. **Feature Engineering** -- Select and transform raw data into meaningful numerical features.
3. **Model Training** -- An algorithm iterates over the training data, adjusting its internal parameters to minimize prediction errors.
4. **Evaluation** -- The trained model is tested on held-out data to measure generalization performance.
5. **Inference** -- The model receives new inputs and outputs predictions in real time.

In this project, the "inputs" are 18 questionnaire responses (each rated 1-5), and the "output" is one of four stress levels.

### Types of Machine Learning

| Type | Description | Example |
|---|---|---|
| **Supervised Learning** | Model learns from labeled data (input-output pairs) | This project: questionnaire responses -> stress level |
| **Unsupervised Learning** | Model finds hidden structure in unlabeled data | Customer segmentation, anomaly detection |
| **Reinforcement Learning** | Agent learns by trial and error, maximizing rewards | Game-playing AI, robotics |

This project uses **supervised classification** -- the model is trained on questionnaire responses (features) paired with known stress levels (labels), and it learns to classify new responses into one of four categories.

### Algorithm Used: Random Forest Classifier

#### What is a Decision Tree?

A **Decision Tree** is the building block of a Random Forest. It works by recursively splitting the data on feature thresholds to create a tree-like structure of decisions:

```
                    [Is Q18 (financial stress) >= 3.5?]
                    /                                  \
                 Yes                                    No
                /                                        \
    [Is Q3 (irritability) >= 3.5?]            [Is Q8 (concentration) >= 2.5?]
    /                         \                /                            \
  Yes                         No             Yes                            No
   |                           |              |                              |
 Severe                      High         Moderate                          Low
```

Each internal node tests a feature, each branch represents a decision, and each leaf node represents a predicted class. The tree learns which features and thresholds best separate the stress levels by measuring **information gain** (reduction in impurity) at each split.

**Limitations of a single tree:**
- Prone to **overfitting** (memorizes training data noise).
- **Unstable** -- small changes in data can produce a completely different tree.
- High **variance** in predictions.

#### What is a Random Forest?

A **Random Forest** solves these problems by combining many decision trees into an **ensemble**. The key ideas are:

1. **Bagging (Bootstrap Aggregating):** Each tree is trained on a random subset of the training data (sampled with replacement). This means each tree sees a slightly different version of the data, reducing variance.

2. **Feature Randomness:** At each split in each tree, only a random subset of features is considered. This decorrelates the trees, so they don't all make the same mistakes.

3. **Majority Voting:** For classification, each tree "votes" for a class. The final prediction is the class with the most votes across all trees.

```
Input (18 questionnaire responses)
         |
   +-----+-----+-----+-----+-- ... --+
   |     |     |     |     |          |
 Tree1 Tree2 Tree3 Tree4 Tree5 ... Tree100
   |     |     |     |     |          |
  High  High   Mod  High  High  ...  High
   |     |     |     |     |          |
   +-----+-----+-----+-----+-- ... --+
         |
   Majority Vote: HIGH (confidence: 85%)
```

#### Why Random Forest for This Project?

| Property | Benefit for Stress Detection |
|---|---|
| **Handles non-linear relationships** | Stress is influenced by complex interactions between multiple factors |
| **Robust to noise** | Individual questionnaire answers may have variance; ensemble averaging smooths this out |
| **Feature importance** | Reveals which questions contribute most to predictions, informing clinical insight |
| **No feature scaling required** | Works directly with the 1-5 Likert scale responses without normalization |
| **Interpretable confidence scores** | `predict_proba()` gives the proportion of trees voting for each class as a confidence measure |
| **Handles class imbalance** | `class_weight="balanced"` adjusts for uneven distribution of stress levels |
| **Low overfitting risk** | The ensemble of 100 trees generalizes well with `max_depth=10` constraint |

#### Hyperparameters Used

```python
RandomForestClassifier(
    n_estimators=100,      # 100 decision trees in the forest
    max_depth=10,          # Each tree can be at most 10 levels deep (prevents overfitting)
    random_state=42,       # Fixed seed for reproducible results
    class_weight="balanced" # Automatically adjusts weights inversely proportional to class frequency
)
```

| Parameter | Value | Explanation |
|---|---|---|
| `n_estimators` | 100 | Number of trees. More trees = better generalization but slower inference. 100 is a good balance. |
| `max_depth` | 10 | Maximum depth per tree. Limits complexity to prevent overfitting on 18 features. |
| `random_state` | 42 | Ensures identical results across training runs for reproducibility. |
| `class_weight` | `"balanced"` | Assigns higher weight to minority classes (e.g., Severe stress has fewer samples) so the model does not bias toward majority classes. |

### How the Stress Prediction Pipeline Works

```
Step 1: User completes 18-question CBT questionnaire
        [q1=3, q2=4, q3=2, q4=5, q5=1, ..., q18=4]
                        |
Step 2: Input validation (18 integers, each 1-5)
                        |
Step 3: Create feature vector as a Pandas DataFrame
        columns: [q1, q2, q3, ..., q18]
                        |
Step 4: model.predict(X) --> stress_level (0, 1, 2, or 3)
        100 trees each vote; majority wins
                        |
Step 5: model.predict_proba(X) --> [0.05, 0.10, 0.72, 0.13]
        Confidence = probability of the predicted class = 0.72 (72%)
                        |
Step 6: Map prediction to label
        0 = Low, 1 = Moderate, 2 = High, 3 = Severe
                        |
Step 7: Generate personalized recommendations
        Based on stress level + individual high-scoring responses
                        |
Step 8: Return (stress_level, stress_label, confidence, recommendations)
```

**Code flow:**
1. User submits responses via `POST /api/user/test/submit`
2. Backend calls `StressPredictor.predict(responses)` in [`predictor.py`](backend/ml_model/predictor.py:43)
3. The model loaded from `stress_model.pkl` runs inference
4. Results are stored in MongoDB and returned to the frontend

### Training Data and Feature Engineering

#### Dataset
- **100,000 samples** from a comprehensive training dataset (`stress_training_dataset_100k.csv`)
- Falls back to 1,000 synthetic samples if the CSV is unavailable
- **Stratified 80/20 train-test split** ensures proportional class representation in both sets

#### Features (18 CBT Questions)
Each feature (`q1` through `q18`) corresponds to a CBT questionnaire question, rated on a 1-5 Likert scale:

| Feature | Category | Question Theme |
|---|---|---|
| q1 - q3 | Emotional State | Anxiety, sadness/depression, irritability/anger |
| q4 - q7 | Physical Symptoms | Physical pain, fatigue, sleep disturbance, elevated heart rate |
| q8 - q11 | Cognitive Patterns | Concentration difficulty, negative thoughts, worry, decision-making |
| q12 - q14 | Behavioral Changes | Appetite changes, social withdrawal, feeling overwhelmed |
| q15 - q18 | Life Stressors | Work-life balance, work/study stress, relationship stress, financial stress |

#### Target Variable
- `stress_level`: 0 (Low), 1 (Moderate), 2 (High), 3 (Severe)

#### Training Process
The model is trained via [`train_model.py`](backend/ml_model/train_model.py:72):

1. Load the CSV dataset (or generate synthetic data as fallback)
2. Split into 80% training / 20% test with stratification
3. Train `RandomForestClassifier` with balanced class weights
4. Evaluate on test set and print classification report
5. Save trained model as `stress_model.pkl` (pickle serialization)
6. Save training metadata to `stress_model_meta.json`

### Model Performance

Trained on the 100K dataset, the model achieves:

```
Accuracy: 89.56%

Classification Report:
              precision    recall  f1-score
Low               ~0.90     ~0.88    ~0.89
Moderate          ~0.87     ~0.92    ~0.89
High              ~0.90     ~0.90    ~0.90
Severe            ~0.93     ~0.85    ~0.89
```

**Key metrics explained:**
- **Precision**: Of all predictions for a class, what proportion was correct? High precision for "Severe" means few false alarms.
- **Recall**: Of all actual instances of a class, what proportion was detected? High recall for "Moderate" means few cases are missed.
- **F1-Score**: Harmonic mean of precision and recall, balancing both concerns.

### Feature Importance Analysis

Random Forest provides a built-in feature importance metric based on how much each feature reduces impurity (Gini index) across all trees. The top contributing questions are:

| Rank | Question | Category | Importance |
|---|---|---|---|
| 1 | Q18 - Financial Stress | Life Stressors | ~8.9% |
| 2 | Q3 - Irritability/Anger | Emotional State | ~8.6% |
| 3 | Q8 - Concentration Difficulties | Cognitive Patterns | ~7.8% |
| 4 | Q2 - Sadness/Depression | Emotional State | ~7.5% |
| 5 | Q13 - Social Withdrawal | Behavioral Changes | ~6.5% |

**Clinical significance:** Financial stress (Q18) and emotional regulation (Q3) are the strongest predictors of overall stress level, aligning with established psychological research on primary stress triggers.

### AI Chatbot: Real-Time Stress Detection

Beyond the questionnaire-based ML model, the application includes a **24/7 AI Stress Counselor** powered by Groq's LLM API (llama-3.3-70b-versatile model):

- Users can chat naturally about their feelings and daily experiences
- The LLM analyzes conversational text and **automatically detects stress indicators**
- Returns a stress level estimate alongside empathetic, actionable counseling responses
- Complements the structured questionnaire with free-form interaction

### Continuous Learning Strategy

The system is designed for ongoing model improvement:

1. **Data Accumulation**: Every user test submission is stored in MongoDB alongside the ML prediction.
2. **Periodic Retraining**: The stored data can be exported and used to retrain the model with real-world responses.
3. **Performance Monitoring**: Training metadata (accuracy, feature importance) is saved in `stress_model_meta.json` for tracking model drift.
4. **Auto-Recovery**: If the model file is missing or corrupted, `StressPredictor` automatically retrains from the dataset on startup.

---

## CBT Questionnaire Design

The questionnaire is grounded in Cognitive Behavioral Therapy principles, organized into five clinical categories:

### Categories and Questions

| # | Category | Question Theme | Clinical Rationale |
|---|---|---|---|
| Q1 | Emotional State | Anxiety levels | Core CBT emotional assessment |
| Q2 | Emotional State | Sadness/depression | Mood indicator linked to chronic stress |
| Q3 | Emotional State | Irritability/anger | Emotional dysregulation marker |
| Q4 | Physical Symptoms | Physical pain/tension | Somatic stress manifestation |
| Q5 | Physical Symptoms | Fatigue/energy | Physical depletion indicator |
| Q6 | Physical Symptoms | Sleep quality | Sleep disruption is both cause and effect of stress |
| Q7 | Physical Symptoms | Elevated heart rate | Physiological arousal response |
| Q8 | Cognitive Patterns | Concentration | Cognitive load and impairment |
| Q9 | Cognitive Patterns | Negative thoughts | Cognitive distortion frequency |
| Q10 | Cognitive Patterns | Excessive worry | Anticipatory anxiety measure |
| Q11 | Cognitive Patterns | Decision-making difficulty | Executive function impact |
| Q12 | Behavioral Changes | Appetite changes | Behavioral stress response |
| Q13 | Behavioral Changes | Social withdrawal | Isolation tendency |
| Q14 | Behavioral Changes | Feeling overwhelmed | Coping capacity assessment |
| Q15 | Life Stressors | Work-life balance | Structural stress source |
| Q16 | Life Stressors | Work/study pressure | Occupational stress |
| Q17 | Life Stressors | Relationship stress | Interpersonal stress source |
| Q18 | Life Stressors | Financial stress | Economic stress (top predictor) |

### Response Scale (1-5 Likert)
| Score | Meaning |
|---|---|
| 1 | Never / Not at all |
| 2 | Rarely / Slightly |
| 3 | Sometimes / Moderately |
| 4 | Often / Very |
| 5 | Always / Extremely |

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- **MongoDB** running on `localhost:27017` (or provide a remote URI)

---

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd AI-STRESS-DETECTOR
```

### 2. Backend Setup

```bash
cd backend

# Create and activate a virtual environment (recommended)
python -m venv myenv
myenv\Scripts\activate       # Windows
# source myenv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Train the ML model (required on first run)
python -m ml_model.train_model

# Start the backend server
python -m app.main
# or
uvicorn app.main:app --reload
```

Backend runs at: **http://localhost:8000**
API docs available at: **http://localhost:8000/docs** (Swagger UI)

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Frontend runs at: **http://localhost:3000** or **http://localhost:5173**

### 4. Quick Launch (Windows)

Use the provided batch scripts:
```bash
start.bat    # Starts both backend and frontend
test.bat     # Runs tests
```

---

## Environment Variables

Create a `backend/.env` file with the following:

```env
# Required
JWT_SECRET_KEY=your_strong_secret_key_here
ADMIN_PASSWORD=your_secure_admin_password_here
MONGODB_URL=mongodb://localhost:27017/aistressdetector

# AI Chatbot
GROQ_API_KEY=your_groq_api_key
GROQ_CHAT_MODEL=llama-3.3-70b-versatile

# Email (OTP Verification)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=your_email@gmail.com

# Optional: SMS Notifications (Fast2SMS)
SMS_PROVIDER=fast2sms
FAST2SMS_API_KEY=your_fast2sms_api_key
FAST2SMS_ENABLE_NON_OTP_SMS=true
FAST2SMS_ROUTE=q
FAST2SMS_OTP_ROUTE=otp
FAST2SMS_NOTIFICATION_ROUTE=q
FAST2SMS_WELCOME_ROUTE=q
FAST2SMS_LANGUAGE=english
FAST2SMS_COUNTRY_CODE=91
FAST2SMS_SENDER_ID=
FAST2SMS_NOTIFICATION_SENDER_ID=
FAST2SMS_NOTIFICATION_ENTITY_ID=

# Optional: Use DLT manual route for welcome/account-verified SMS
FAST2SMS_WELCOME_SENDER_ID=
FAST2SMS_WELCOME_TEMPLATE_ID=
FAST2SMS_WELCOME_ENTITY_ID=
FAST2SMS_WELCOME_MESSAGE=

# Optional: DLT template IDs for non-OTP notifications
FAST2SMS_TEMPLATE_APPOINTMENT_BOOKED_ID=
FAST2SMS_TEMPLATE_APPOINTMENT_APPROVED_ID=
FAST2SMS_TEMPLATE_APPOINTMENT_REJECTED_ID=
FAST2SMS_TEMPLATE_APPOINTMENT_COMPLETED_ID=
FAST2SMS_TEMPLATE_STRESS_RESULT_ID=

# Optional: CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Optional: JWT Expiration
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

---

## Database Configuration

The application connects to MongoDB at the URI specified by `MONGODB_URL` (defaults to `mongodb://localhost:27017/aistressdetector`).

### Collections Created Automatically
| Collection | Purpose |
|---|---|
| `users` | User accounts and profiles |
| `doctors` | Doctor accounts with license data |
| `admins` | Admin accounts |
| `tests` | Stress test results and ML predictions |
| `appointments` | Doctor-patient appointments |
| `medical_records` | Uploaded medical documents |
| `achievements` | Gamification data (badges, points, streaks) |

### Default Admin Account
On first startup, the backend creates an admin user if one does not exist:
- **Email:** `admin@stressanalyzer.com`
- **Password:** Value of `ADMIN_PASSWORD` environment variable

Change this password after first login in any production deployment.

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/user` | Register a new user |
| POST | `/api/auth/register/doctor` | Register a new doctor |
| POST | `/api/auth/login` | Login (all roles) |
| POST | `/api/auth/verify-otp` | Verify email OTP |
| POST | `/api/auth/resend-otp` | Resend verification OTP |

### User
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/user/questionnaire` | Get CBT questions |
| POST | `/api/user/test/submit` | Submit test and get ML prediction |
| GET | `/api/user/test/history/{user_id}` | Get test history |
| GET | `/api/user/test/{test_id}` | Get test details |
| GET | `/api/user/doctors` | Get verified doctors list |
| POST | `/api/user/appointment/book` | Book an appointment |
| GET | `/api/user/appointments/{user_id}` | Get user's appointments |
| POST | `/api/user/chatbot/chat` | Chat with AI counselor |

### Doctor
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/doctor/appointments/{doctor_id}` | Get appointments with patient data |
| GET | `/api/doctor/appointment/{id}/patient-tests` | Get patient's test history |
| PUT | `/api/doctor/appointment/{id}` | Update appointment status |
| GET | `/api/doctor/stats/{doctor_id}` | Get doctor statistics |

### Admin
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/admin/stats` | Get comprehensive statistics |
| GET | `/api/admin/users` | Get all users |
| GET | `/api/admin/doctors` | Get all doctors |
| PUT | `/api/admin/doctor/{id}/verify` | Verify a doctor |
| GET | `/api/admin/appointments` | Get all appointments |
| DELETE | `/api/admin/user/{id}` | Delete a user |
| DELETE | `/api/admin/doctor/{id}` | Delete a doctor |

All protected endpoints require the `Authorization: Bearer <token>` header.

---

## Stress Level Recommendations

The system generates personalized recommendations based on predicted stress level, organized into categories:

### Level 0 -- Low
- Continue current self-care routine
- Maintain healthy habits and preventive practices
- Use preventive stress-management techniques such as meditation

### Level 1 -- Moderate
- Practice daily relaxation techniques (breathing exercises, meditation)
- Aim for 7-8 hours of quality sleep
- Regular physical activity for at least 30 minutes/day
- Talk with friends, family, or a counselor

### Level 2 -- High
- **Professional support recommended**
- Schedule an appointment with a mental health professional
- Practice stress-reduction techniques multiple times per day
- Prioritize and organize tasks to reduce overwhelm
- Limit caffeine and alcohol

### Level 3 -- Severe
- **URGENT: Seek professional help immediately**
- Book a doctor appointment today
- Contact a crisis helpline if in immediate distress (988 Suicide & Crisis Lifeline)
- Inform trusted family members or friends

Additionally, the Enhanced Recommendation Engine provides:
- **Immediate Relief** -- 2-5 minute techniques (4-7-8 breathing, 5-4-3-2-1 grounding)
- **Daily Habits** -- Morning mindfulness, exercise, journaling, sleep routine
- **Weekly Goals** -- Support groups, therapy sessions, nature therapy
- **Lifestyle Changes** -- 12-week exercise programs, nutrition plans, MBSR courses
- **Curated Resources** -- App recommendations (Headspace, Calm, BetterHelp)

---

## Gamification and Progress Tracking

The system includes a gamification layer to encourage consistent engagement with stress-management activities:

### Points System
| Activity | Points |
|---|---|
| Complete a recommendation | 10 |
| Complete daily goal | 25 |
| Maintain streak (per day) | 5 x streak days |
| Rate a recommendation | 2 |
| Meditation (per minute) | 1 |
| Exercise (per minute) | 1 |
| Journal entry | 15 |
| Therapy session | 50 |

### Levels
| Level | Name | Points Required |
|---|---|---|
| 1 | Beginner | 0 |
| 2 | Explorer | 100 |
| 3 | Practitioner | 300 |
| 4 | Dedicated | 600 |
| 5 | Advanced | 1,000 |
| 6 | Expert | 1,500 |
| 7 | Master | 2,500 |
| 8 | Zen Master | 4,000 |

### Badges
- First Step (1 recommendation completed)
- Getting Started (5 recommendations)
- Week Warrior (7-day streak)
- Month Master (30-day streak)
- Stress Crusher (20 recommendations)
- Zen Master (100 minutes meditation)
- Fitness Fan (200 minutes exercise)
- Journal Enthusiast (30 journal entries)
- Therapy Champion (5 therapy sessions)

---

## Security Features

- **JWT-based authentication** with configurable expiration
- **bcrypt password hashing** (with 72-byte truncation per bcrypt spec)
- **Role-based access control (RBAC)** -- user, doctor, admin
- **Protected API routes** with token verification and user existence checks
- **Input validation** via Pydantic models
- **CORS configuration** with configurable allowed origins
- **NMC license validation** for doctor registration
- **Email OTP verification** for new user accounts
- **Environment-based secret management** (no hardcoded credentials)

---

## Deployment

### Backend (Railway / Render / Heroku)
```bash
# Set environment variables on your platform
MONGODB_URL=your_mongodb_atlas_url
JWT_SECRET_KEY=your_strong_secret_key
ADMIN_PASSWORD=your_admin_password
GROQ_API_KEY=your_groq_api_key
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
```

### Frontend (Vercel / Netlify)
```bash
# Set build command and environment variable
VITE_API_URL=your_backend_url
```

---

## Troubleshooting

### MongoDB Connection Issues
```bash
# Check if MongoDB is running
mongosh

# Start MongoDB service
sudo systemctl start mongod      # Linux
brew services start mongodb-community  # macOS
net start MongoDB                 # Windows
```

### Backend Port Already in Use
Change the port in `app/main.py`:
```python
uvicorn.run(app, host="0.0.0.0", port=8001)
```

### Model Not Found
The model auto-retrains on startup if `stress_model.pkl` is missing or corrupted. You can also manually retrain:
```bash
cd backend
python -m ml_model.train_model
```

### Frontend API Connection Issues
Verify that:
1. The backend is running on the expected port (default: 8000)
2. `ALLOWED_ORIGINS` in the backend `.env` includes your frontend URL
3. Check `vite.config.ts` proxy settings if applicable

### Fast2SMS Shows "Sent" But Welcome SMS Is Not Delivered
If you receive OTP SMS but not welcome, appointment, or stress-result SMS:

1. The backend now treats Fast2SMS success as "submitted" to the gateway, not guaranteed handset delivery.
2. OTP SMS and non-OTP notifications can use different routes:
   `FAST2SMS_OTP_ROUTE=otp` is preferred for verification codes.
   `FAST2SMS_NOTIFICATION_ROUTE=q` keeps the old Quick SMS behavior for informational messages.
3. Quick SMS acceptance in the dashboard does not always mean the operator delivered the message.
4. If you do not have DLT set up yet, keep OTP SMS enabled and disable non-OTP SMS:
   `FAST2SMS_ENABLE_NON_OTP_SMS=false`
   This keeps verification codes working while stopping welcome/appointment/stress-result SMS from being submitted as Quick SMS.
5. For reliable non-OTP notifications, use approved DLT templates and configure:
   `FAST2SMS_NOTIFICATION_ROUTE=dlt_manual`
   `FAST2SMS_NOTIFICATION_SENDER_ID=YOUR6CHARHEADER`
   `FAST2SMS_NOTIFICATION_ENTITY_ID=YOUR_ENTITY_ID`
6. Add the DLT template ID for each message type you send:
   `FAST2SMS_WELCOME_ROUTE=dlt_manual`
   `FAST2SMS_WELCOME_TEMPLATE_ID=YOUR_WELCOME_TEMPLATE_ID`
   `FAST2SMS_TEMPLATE_APPOINTMENT_BOOKED_ID=...`
   `FAST2SMS_TEMPLATE_APPOINTMENT_APPROVED_ID=...`
   `FAST2SMS_TEMPLATE_APPOINTMENT_REJECTED_ID=...`
   `FAST2SMS_TEMPLATE_APPOINTMENT_COMPLETED_ID=...`
   `FAST2SMS_TEMPLATE_STRESS_RESULT_ID=...`
7. If you need the welcome SMS text to exactly match a DLT template, set:
   `FAST2SMS_WELCOME_MESSAGE=Exact approved DLT message text`

---

## Project Structure

```
AI-STRESS-DETECTOR/
|-- backend/
|   |-- app/
|   |   |-- main.py                    # FastAPI application entry point
|   |   |-- auth.py                    # JWT authentication and RBAC
|   |   |-- config.py                  # Application settings (Pydantic)
|   |   |-- database.py               # MongoDB connection and initialization
|   |   |-- models.py                  # Pydantic request/response models
|   |   |-- recommendation_engine.py   # Enhanced personalized recommendations
|   |   |-- progress_tracker.py        # Gamification and streak tracking
|   |   |-- email_service.py           # Email sending (OTP, notifications)
|   |   |-- sms_service.py             # SMS notifications (Fast2SMS)
|   |   |-- nmc_verification.py        # Doctor license validation
|   |   |-- otp_utils.py               # OTP generation and verification
|   |   |-- routes/
|   |       |-- auth_routes.py         # Authentication endpoints
|   |       |-- user_routes.py         # User endpoints (tests, appointments)
|   |       |-- doctor_routes.py       # Doctor endpoints
|   |       |-- admin_routes.py        # Admin endpoints
|   |       |-- medical_records_routes.py  # Medical records management
|   |-- ml_model/
|   |   |-- train_model.py            # Model training script
|   |   |-- predictor.py              # StressPredictor class (inference)
|   |   |-- stress_model.pkl          # Trained model (binary)
|   |   |-- stress_model_meta.json    # Training metadata
|   |   |-- stress_training_dataset_100k.csv  # Training dataset
|   |-- requirements.txt              # Python dependencies
|
|-- frontend/
|   |-- src/
|   |   |-- App.tsx                    # Main React component with routing
|   |   |-- main.tsx                   # Application entry point
|   |   |-- index.css                  # Global styles (Tailwind)
|   |   |-- services/
|   |   |   |-- api.ts                 # Axios API client
|   |   |-- components/
|   |   |   |-- EnhancedRecommendations.tsx
|   |   |   |-- ProgressTracker.tsx
|   |   |   |-- AppointmentBooking.tsx
|   |   |   |-- MedicalRecordsManager.tsx
|   |   |   |-- VideoAssessmentModal.tsx
|   |   |-- pages/
|   |       |-- HomePage.tsx
|   |       |-- LoginPage.tsx
|   |       |-- RegisterPage.tsx
|   |       |-- UserDashboard.tsx
|   |       |-- DoctorDashboard.tsx
|   |       |-- AdminDashboard.tsx
|   |       |-- OTPVerificationPage.tsx
|   |       |-- ForgotPasswordPage.tsx
|   |       |-- AccountDetailsPage.tsx
|   |       |-- AppointmentsPage.tsx
|   |-- index.html
|   |-- package.json
|   |-- Postcss.config.js
|
|-- start.bat / start.sh               # Quick-launch scripts
|-- test.bat / test.sh                  # Test runner scripts
|-- README.md
```

---

## License

This project is built for mental health awareness and educational purposes.
