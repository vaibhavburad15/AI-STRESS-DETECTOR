# AI Stress Level Analyzer 🧠

A comprehensive full-stack web application for **AI-powered stress detection** using **Cognitive Behavioral Therapy (CBT) principles** and **Machine Learning**.

## 🌟 Features

### Three Dashboard System

#### 1. 👤 User Dashboard
- User registration and login
- **18-question CBT-based stress assessment**
- **ML-powered stress level prediction** (Low/Moderate/High/Severe)
- Personalized recommendations based on stress level
- View test history with trend analysis
- Book appointments with verified doctors
- View appointment status

#### 2. 👨‍⚕️ Doctor Dashboard
- Doctor registration with license validation
- License number format: **2 letters + 6-8 digits** (e.g., MD123456)
- View scheduled appointments
- Access patient's complete test history
- View patient's stress levels for each appointment
- Approve/reject appointments
- Add consultation notes
- Track appointment statistics

#### 3. 👨‍💼 Admin Dashboard
- Comprehensive statistics dashboard
- User management (view all users, tests, activity)
- Doctor management (verify licenses, activate/deactivate)
- Appointment oversight
- Data visualization:
  - Stress level distribution charts
  - User registration trends
  - Appointment status breakdown
- Delete users/doctors if needed

## 🛠️ Tech Stack

### Backend
- **Python 3.10+** with FastAPI
- **MongoDB** for database
- **JWT** authentication with bcrypt password hashing
- **scikit-learn** for ML model (Random Forest Classifier)
- **Pydantic** for data validation

### Frontend
- **React 18** with TypeScript
- **Vite** for fast development
- **Tailwind CSS** for styling
- **Axios** for API calls
- **React Router** for navigation
- **Recharts** for data visualization

### Machine Learning
- **Random Forest Classifier** (95% accuracy)
- **18 CBT-based features** from questionnaire
- **4 stress levels**: Low (0), Moderate (1), High (2), Severe (3)
- Confidence scoring for predictions
- Model persistence with pickle

## 📋 Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm/yarn
- **MongoDB** running on `localhost:27017`

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd stress-analyzer
```

### 2. Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Train the ML model (required first time)
python -m ml_model.train_model

# Start the backend server
python -m app.main
# or
uvicorn app.main:app --reload
```

Backend will run on: **http://localhost:8000**

### 2.1 Optional SMS Notifications (Fast2SMS)

To enable OTP and appointment updates via Fast2SMS, add these values in `backend/.env`:

```env
SMS_PROVIDER=fast2sms
FAST2SMS_API_KEY=your_fast2sms_api_key
FAST2SMS_ROUTE=q
FAST2SMS_LANGUAGE=english
FAST2SMS_COUNTRY_CODE=91
```

If these values are not set, SMS sending stays disabled and core app flows still work.

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run on: **http://localhost:3000**

## 🗄️ Database Configuration

The application connects to MongoDB at:
```
mongodb://localhost:27017/ai%20stress%20detector
```

### Collections Created Automatically:
- `users` - User accounts
- `doctors` - Doctor accounts
- `tests` - Stress test results
- `appointments` - Doctor appointments
- `admin` - Admin accounts

### Default Admin Credentials:
```
Username: admin
Password: admin123
```

⚠️ **Change this in production!**

## 📊 ML Model Details

### Training Data
- **1000 synthetic samples** generated with realistic patterns
- **18 features** corresponding to CBT questionnaire
- **Stratified train-test split** (80/20)

### Model Performance
```
Accuracy: 95.00%

Classification Report:
              precision    recall  f1-score
Low               0.98      0.92      0.95
Moderate          0.92      0.99      0.95
High              0.94      0.96      0.95
Severe            1.00      0.88      0.94
```

### Most Important Questions (Feature Importance):
1. Question 18: Financial stress (8.9%)
2. Question 3: Irritability/anger (8.6%)
3. Question 8: Concentration difficulties (7.8%)
4. Question 2: Sadness/depression (7.5%)
5. Question 13: Social withdrawal (6.5%)

## 🔐 API Endpoints

### Authentication
- `POST /api/auth/register/user` - Register user
- `POST /api/auth/register/doctor` - Register doctor
- `POST /api/auth/login` - Login (all roles)

### User
- `GET /api/user/questionnaire` - Get CBT questions
- `POST /api/user/test/submit` - Submit test, get ML prediction
- `GET /api/user/test/history/{user_id}` - Get test history
- `GET /api/user/test/{test_id}` - Get test details
- `GET /api/user/doctors` - Get verified doctors
- `POST /api/user/appointment/book` - Book appointment
- `GET /api/user/appointments/{user_id}` - Get appointments

### Doctor
- `GET /api/doctor/appointments/{doctor_id}` - Get appointments with patient data
- `GET /api/doctor/appointment/{appointment_id}/patient-tests` - Get patient tests
- `PUT /api/doctor/appointment/{appointment_id}` - Update appointment status
- `GET /api/doctor/stats/{doctor_id}` - Get doctor statistics

### Admin
- `GET /api/admin/stats` - Get comprehensive statistics
- `GET /api/admin/users` - Get all users
- `GET /api/admin/doctors` - Get all doctors
- `PUT /api/admin/doctor/{doctor_id}/verify` - Verify doctor
- `GET /api/admin/appointments` - Get all appointments
- `DELETE /api/admin/user/{user_id}` - Delete user
- `DELETE /api/admin/doctor/{doctor_id}` - Delete doctor

## 🧪 CBT Questionnaire (18 Questions)

### Categories:
1. **Emotional State** (Q1-Q3): Anxiety, sadness, irritability
2. **Physical Symptoms** (Q4-Q7): Pain, fatigue, sleep, heart rate
3. **Cognitive Patterns** (Q8-Q11): Concentration, negative thoughts, worry, decision-making
4. **Behavioral Changes** (Q12-Q14): Appetite, social withdrawal, overwhelm
5. **Life Stressors** (Q15-Q18): Work-life balance, work stress, relationship stress, financial stress

### Response Scale (1-5):
- **1**: Never/Not at all
- **2**: Rarely/Slightly
- **3**: Sometimes/Moderately
- **4**: Often/Very
- **5**: Always/Extremely

## 🔄 Continuous Learning

The ML model is designed for continuous improvement:
- All user test submissions are stored in MongoDB
- Implement periodic retraining with accumulated data
- Monitor model performance metrics
- Update recommendations based on user feedback

## 🚀 Deployment

### Backend (Railway/Render/Heroku)
```bash
# Set environment variables
MONGODB_URL=your_mongodb_atlas_url
SECRET_KEY=your_strong_secret_key
```

### Frontend (Vercel/Netlify)
```bash
# Set environment variable
VITE_API_URL=your_backend_url
```

## 🤝 Testing

### Sample Test Credentials

**User:**
- Register a new user account
- Take the stress test
- Book appointments

**Doctor:**
- Name: Dr. John Smith
- Email: doctor@example.com
- Password: doctor123
- License: MD123456
- Specialization: Clinical Psychology

**Admin:**
- Username: admin
- Password: admin123

## 📊 Stress Level Recommendations

### Low (0)
- Continue current self-care practices
- Maintain healthy habits
- Preventive stress management

### Moderate (1)
- Daily relaxation techniques
- 7-8 hours sleep
- Regular exercise (30 min/day)
- Talk to friends/counselor

### High (2)
- Professional support recommended
- Multiple daily stress-reduction sessions
- Prioritize tasks
- Limit caffeine/alcohol
- Contact support network

### Severe (3)
- **URGENT**: Seek professional help immediately
- Book doctor appointment today
- Contact crisis helpline if needed
- Consider psychiatrist consultation
- Inform trusted family/friends

## 🐛 Troubleshooting

### MongoDB Connection Issues
```bash
# Check if MongoDB is running
mongosh

# Or start MongoDB service
sudo systemctl start mongod  # Linux
brew services start mongodb-community  # Mac
```

### Backend Port Already in Use
```bash
# Change port in app/main.py
uvicorn.run(app, host="0.0.0.0", port=8001)
```

### Frontend API Connection Issues
```bash
# Check vite.config.ts proxy settings
# Ensure backend is running on port 8000
```

## 📚 Documentation

- **API Documentation**: Visit `http://localhost:8000/docs` after starting backend
- **Interactive API Testing**: Use FastAPI's built-in Swagger UI

## 🔒 Security Features

- ✅ **JWT-based authentication**
- ✅ **bcrypt password hashing**
- ✅ **Role-based access control** (RBAC)
- ✅ **Protected API routes**
- ✅ **Input validation** with Pydantic
- ✅ **CORS configuration**
- ✅ **License validation**




**Built with ❤️ for mental health awareness**

