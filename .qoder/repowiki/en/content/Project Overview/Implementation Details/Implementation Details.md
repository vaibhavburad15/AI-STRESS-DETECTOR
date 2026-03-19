# Implementation Details

<cite>
**Referenced Files in This Document**
- [backend/app/main.py](file://backend/app/main.py)
- [backend/app/models.py](file://backend/app/models.py)
- [backend/app/auth.py](file://backend/app/auth.py)
- [backend/app/database.py](file://backend/app/database.py)
- [backend/app/config.py](file://backend/app/config.py)
- [backend/app/routes/auth_routes.py](file://backend/app/routes/auth_routes.py)
- [backend/app/routes/user_routes.py](file://backend/app/routes/user_routes.py)
- [backend/app/routes/doctor_routes.py](file://backend/app/routes/doctor_routes.py)
- [backend/app/routes/admin_routes.py](file://backend/app/routes/admin_routes.py)
- [backend/app/routes/medical_records_routes.py](file://backend/app/routes/medical_records_routes.py)
- [backend/ml_model/predictor.py](file://backend/ml_model/predictor.py)
- [backend/app/recommendation_engine.py](file://backend/app/recommendation_engine.py)
- [backend/app/progress_tracker.py](file://backend/app/progress_tracker.py)
- [backend/app/analytics_engine.py](file://backend/app/analytics_engine.py)
- [backend/app/report_generator.py](file://backend/app/report_generator.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document provides implementation details for the AI Stress Level Analyzer, a CBT-based stress detection system integrating machine learning, medical records management, and a gamified wellness platform. It covers data models and schema design, MongoDB collections and relationships, authentication and authorization, API design patterns, frontend component architecture and state management, code organization principles, security implementations, testing strategies, logging, and debugging techniques.

## Project Structure
The backend is organized around a FastAPI application with modular routing, a dedicated ML inference module, and supporting services for analytics, reporting, and progress tracking. Environment-driven configuration and centralized database initialization support flexible deployment.

```mermaid
graph TB
A["FastAPI App<br/>backend/app/main.py"] --> B["Routes<br/>backend/app/routes/*"]
A --> C["Auth & Security<br/>backend/app/auth.py"]
A --> D["Database Layer<br/>backend/app/database.py"]
A --> E["Models & Schemas<br/>backend/app/models.py"]
A --> F["Config<br/>backend/app/config.py"]
B --> B1["Auth Routes<br/>auth_routes.py"]
B --> B2["User Routes<br/>user_routes.py"]
B --> B3["Doctor Routes<br/>doctor_routes.py"]
B --> B4["Admin Routes<br/>admin_routes.py"]
B --> B5["Medical Records Routes<br/>medical_records_routes.py"]
A --> G["ML Models<br/>backend/ml_model/predictor.py"]
A --> H["Recommendations<br/>backend/app/recommendation_engine.py"]
A --> I["Progress Tracker<br/>backend/app/progress_tracker.py"]
A --> J["Analytics Engine<br/>backend/app/analytics_engine.py"]
A --> K["Report Generator<br/>backend/app/report_generator.py"]
```

**Diagram sources**
- [backend/app/main.py:52-98](file://backend/app/main.py#L52-L98)
- [backend/app/routes/auth_routes.py:32-596](file://backend/app/routes/auth_routes.py#L32-L596)
- [backend/app/routes/user_routes.py:32-800](file://backend/app/routes/user_routes.py#L32-L800)
- [backend/app/routes/doctor_routes.py:22-400](file://backend/app/routes/doctor_routes.py#L22-L400)
- [backend/app/routes/admin_routes.py:9-225](file://backend/app/routes/admin_routes.py#L9-L225)
- [backend/app/routes/medical_records_routes.py:40-800](file://backend/app/routes/medical_records_routes.py#L40-L800)
- [backend/ml_model/predictor.py:32-590](file://backend/ml_model/predictor.py#L32-L590)
- [backend/app/recommendation_engine.py:11-554](file://backend/app/recommendation_engine.py#L11-L554)
- [backend/app/progress_tracker.py:48-454](file://backend/app/progress_tracker.py#L48-L454)
- [backend/app/analytics_engine.py:11-384](file://backend/app/analytics_engine.py#L11-L384)
- [backend/app/report_generator.py:38-341](file://backend/app/report_generator.py#L38-L341)

**Section sources**
- [backend/app/main.py:52-98](file://backend/app/main.py#L52-L98)
- [backend/app/config.py:1-22](file://backend/app/config.py#L1-L22)

## Core Components
- Authentication and Authorization: JWT-based with role-aware middleware and per-request token validation.
- Data Modeling: Pydantic models define request/response schemas for users, doctors, tests, appointments, recommendations, achievements, resources, medical records, and analytics.
- Database Layer: Centralized MongoDB client with connection pooling, collections for users, doctors, admins, tests, appointments, recommendation progress, achievements, resources, reminders, OTPs, and medical records.
- ML Inference: Stress predictor with SHAP explanations, category scoring, trend analysis, and crisis detection.
- Recommendations: AI-powered, categorized recommendations with ranking and gamification.
- Analytics: Population-level insights, doctor effectiveness, and user analytics.
- Reporting: PDF generation for user and doctor reports.
- Frontend Integration: RESTful API design with clear endpoints, request/response schemas, and error handling.

**Section sources**
- [backend/app/auth.py:23-190](file://backend/app/auth.py#L23-L190)
- [backend/app/models.py:16-440](file://backend/app/models.py#L16-L440)
- [backend/app/database.py:26-509](file://backend/app/database.py#L26-L509)
- [backend/ml_model/predictor.py:32-590](file://backend/ml_model/predictor.py#L32-L590)
- [backend/app/recommendation_engine.py:11-554](file://backend/app/recommendation_engine.py#L11-L554)
- [backend/app/analytics_engine.py:11-384](file://backend/app/analytics_engine.py#L11-L384)
- [backend/app/report_generator.py:38-341](file://backend/app/report_generator.py#L38-L341)

## Architecture Overview
The system follows a layered architecture:
- Presentation: FastAPI routes expose REST endpoints.
- Application: Route handlers orchestrate business logic, ML inference, and persistence.
- Persistence: MongoDB collections represent domain entities with indexes for performance.
- Intelligence: ML models and recommendation engines augment user insights.
- Services: Email/SMS, analytics, and reporting utilities.

```mermaid
graph TB
subgraph "Presentation"
R1["Auth Routes"]
R2["User Routes"]
R3["Doctor Routes"]
R4["Admin Routes"]
R5["Medical Records Routes"]
end
subgraph "Application"
A1["Auth Utilities"]
A2["Recommendation Engine"]
A3["Progress Tracker"]
A4["Analytics Engine"]
A5["Report Generator"]
end
subgraph "Persistence"
P1["Users"]
P2["Doctors"]
P3["Admins"]
P4["Tests"]
P5["Appointments"]
P6["Recommendation Progress"]
P7["Achievements"]
P8["Resources"]
P9["Reminders"]
P10["OTPs"]
P11["Medical Records"]
P12["Activities"]
end
subgraph "Intelligence"
I1["Stress Predictor"]
I2["Recommendation Ranker"]
end
R1 --> A1
R2 --> A1
R3 --> A1
R4 --> A1
R5 --> A1
R2 --> A2
R2 --> A3
R3 --> A4
R4 --> A4
R5 --> A5
A2 --> I1
A2 --> I2
R1 --> P1
R1 --> P2
R1 --> P3
R1 --> P10
R2 --> P1
R2 --> P4
R2 --> P5
R2 --> P6
R2 --> P7
R2 --> P8
R2 --> P9
R3 --> P2
R3 --> P4
R3 --> P5
R4 --> P1
R4 --> P2
R4 --> P4
R4 --> P5
R5 --> P11
R5 --> P12
```

**Diagram sources**
- [backend/app/routes/auth_routes.py:32-596](file://backend/app/routes/auth_routes.py#L32-L596)
- [backend/app/routes/user_routes.py:32-800](file://backend/app/routes/user_routes.py#L32-L800)
- [backend/app/routes/doctor_routes.py:22-400](file://backend/app/routes/doctor_routes.py#L22-L400)
- [backend/app/routes/admin_routes.py:9-225](file://backend/app/routes/admin_routes.py#L9-L225)
- [backend/app/routes/medical_records_routes.py:40-800](file://backend/app/routes/medical_records_routes.py#L40-L800)
- [backend/app/auth.py:23-190](file://backend/app/auth.py#L23-L190)
- [backend/app/recommendation_engine.py:11-554](file://backend/app/recommendation_engine.py#L11-L554)
- [backend/app/progress_tracker.py:48-454](file://backend/app/progress_tracker.py#L48-L454)
- [backend/app/analytics_engine.py:11-384](file://backend/app/analytics_engine.py#L11-L384)
- [backend/app/report_generator.py:38-341](file://backend/app/report_generator.py#L38-L341)
- [backend/app/database.py:88-159](file://backend/app/database.py#L88-L159)

## Detailed Component Analysis

### Data Models and Schema Design
- User, Doctor, Test, Appointment, Recommendation, Achievement, Resource, Medical Record, Analytics, Chatbot, and Download models define strict request/response contracts with validation and enums.
- Medical Records introduce typed record categories, file formats, filtering, linking to stress tests, and activity logs.
- Enhanced recommendation models support categorization, difficulty, effectiveness, scheduling, and evidence-backed details.

```mermaid
classDiagram
class UserRegister {
+string name
+string email
+string password
+int age
+string gender
+string location
+bool has_previous_stress_issues
+string phone_number
}
class DoctorRegister {
+string name
+string email
+string password
+string license_number
+string state_medical_council
+string specialization
+string[] available_slots
+string phone_number
}
class TestSubmission {
+int[] responses
}
class TestResponse {
+string id
+string user_id
+int[] responses
+int stress_level
+string stress_label
+float confidence_score
+string[] recommendations
+datetime timestamp
}
class AppointmentCreate {
+string doctor_id
+string time_slot
+string notes
}
class AppointmentResponse {
+string id
+string user_id
+string user_name
+string doctor_id
+string doctor_name
+string time_slot
+string status
+string notes
+datetime created_at
}
class MedicalRecordUpload {
+string user_id
+string record_name
+string record_type
+string description
+string record_date
+string doctor_name
+string hospital_name
+string notes
+string[] tags
}
class MedicalRecordResponse {
+string id
+string user_id
+string record_name
+string record_type
+string file_name
+string file_path
+int file_size
+string file_format
+string description
+datetime record_date
+string doctor_name
+string hospital_name
+string notes
+string[] tags
+datetime uploaded_at
+datetime updated_at
+int download_count
+bool is_linked_to_stress_test
+string linked_test_id
}
```

**Diagram sources**
- [backend/app/models.py:16-440](file://backend/app/models.py#L16-L440)

**Section sources**
- [backend/app/models.py:16-440](file://backend/app/models.py#L16-L440)

### Database Design Patterns and Collections
- Centralized MongoDB client with connection pooling, timeouts, and retry writes.
- Dedicated collections for users, doctors, admins, tests, appointments, recommendation progress, achievements, resources, reminders, OTPs, and medical records.
- Extensive indexes for performance on frequent queries (e.g., user_id, timestamps, statuses, text search).
- Helper functions for admin initialization, user achievements initialization, database stats, and linking stress tests to medical records.

```mermaid
erDiagram
USERS {
objectid _id PK
string email UK
string name
string password
int age
string gender
string location
bool has_previous_stress_issues
string phone_number
bool email_verified
datetime created_at
array test_history
}
DOCTORS {
objectid _id PK
string email UK
string name
string password
string license_number UK
string state_medical_council
string specialization
array available_slots
string phone_number
bool is_verified
bool nmc_verified
jsonb nmc_verification
jsonb nmc_profile
bool email_verified
datetime created_at
}
ADMINS {
objectid _id PK
string username UK
string email UK
string password
string role
}
TESTS {
objectid _id PK
objectid user_id FK
array responses
int stress_level
string stress_label
float confidence_score
float continuous_score
array recommendations
jsonb explanation
jsonb category_scores
jsonb risk_factors
jsonb trend
jsonb crisis
jsonb multimodal
datetime timestamp
}
APPOINTMENTS {
objectid _id PK
objectid user_id FK
objectid doctor_id FK
string user_name
string user_email
string doctor_name
string time_slot
string status
string notes
datetime created_at
datetime updated_at
}
RECOMMENDATION_PROGRESS {
objectid _id PK
objectid user_id FK
string recommendation_id
datetime started_at
datetime completed_at
int effectiveness_rating
string notes
bool reminder_set
string reminder_time
string reminder_frequency
string status
int completion_streak
datetime last_completed
}
USER_ACHIEVEMENTS {
objectid _id PK
objectid user_id FK
array badges
int total_recommendations_completed
int total_recommendations_started
int streak_days
int longest_streak
int points
int level
int meditation_minutes
int exercise_minutes
int journal_entries
int therapist_sessions
datetime last_activity_date
}
RESOURCES {
objectid _id PK
string name
string type
string description
float rating
string price
string icon
string url
string deeplink
string recommended_for
}
REMINDERS {
objectid _id PK
objectid user_id FK
string reminder_time
string frequency
string resource_id
datetime created_at
}
OTPS {
objectid _id PK
string email UK
string otp
string user_type
datetime created_at
datetime expires_at
}
MEDICAL_RECORDS {
objectid _id PK
objectid user_id FK
string record_name
string record_type
string file_name
string file_path
int file_size
string file_format
string file_hash
string description
datetime record_date
string doctor_name
string hospital_name
string notes
array tags
datetime uploaded_at
datetime updated_at
int download_count
bool deleted
bool is_linked_to_stress_test
string linked_test_id
}
MEDICAL_RECORD_ACTIVITIES {
objectid _id PK
objectid record_id FK
string action
string details
datetime timestamp
}
USERS ||--o{ TESTS : "has"
USERS ||--o{ APPOINTMENTS : "booked"
DOCTORS ||--o{ APPOINTMENTS : "provides"
USERS ||--o{ RECOMMENDATION_PROGRESS : "tracks"
USERS ||--o{ USER_ACHIEVEMENTS : "owns"
USERS ||--o{ MEDICAL_RECORDS : "owns"
MEDICAL_RECORDS ||--o{ MEDICAL_RECORD_ACTIVITIES : "logged"
```

**Diagram sources**
- [backend/app/database.py:88-159](file://backend/app/database.py#L88-L159)
- [backend/app/models.py:16-440](file://backend/app/models.py#L16-L440)

**Section sources**
- [backend/app/database.py:26-509](file://backend/app/database.py#L26-L509)

### Authentication and Authorization
- JWT-based authentication with configurable secret, algorithm, and expiration.
- Password hashing using bcrypt with truncation to bcrypt limits.
- Role-aware token verification and per-request dependency injection for authorization.
- Multi-role support: user, doctor, admin; doctor accounts require admin approval and NMC verification.
- Secure token creation with user_id, role, and email; robust token validation and error handling.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Auth as "Auth Routes"
participant DB as "Database"
participant JWT as "Auth Utils"
Client->>Auth : POST /api/auth/register/user
Auth->>DB : Insert user document
Auth->>Auth : Generate OTP
Auth-->>Client : Registration success (no token yet)
Client->>Auth : POST /api/auth/verify-otp
Auth->>DB : Verify OTP and update email_verified
Auth-->>Client : Verification success
Client->>Auth : POST /api/auth/login
Auth->>DB : Find user by email
Auth->>JWT : Create access token (user_id, role, email)
JWT-->>Auth : Signed JWT
Auth-->>Client : TokenResponse
```

**Diagram sources**
- [backend/app/routes/auth_routes.py:68-440](file://backend/app/routes/auth_routes.py#L68-L440)
- [backend/app/auth.py:45-190](file://backend/app/auth.py#L45-L190)
- [backend/app/database.py:344-365](file://backend/app/database.py#L344-L365)

**Section sources**
- [backend/app/auth.py:23-190](file://backend/app/auth.py#L23-L190)
- [backend/app/routes/auth_routes.py:68-440](file://backend/app/routes/auth_routes.py#L68-L440)

### API Design Patterns
- RESTful endpoints under /api/{role} namespaces with clear CRUD and domain-specific actions.
- Consistent request/response schemas via Pydantic models.
- Role-based access control enforced with require_role dependency.
- Comprehensive error handling with HTTPException and structured messages.
- Asynchronous email/SMS notifications for appointments and alerts.
- Aggregation pipelines for efficient doctor appointment listing and analytics.

```mermaid
sequenceDiagram
participant Client as "Client"
participant UserRoute as "User Routes"
participant DB as "Database"
participant ML as "Stress Predictor"
participant SMS as "SMS Service"
participant Email as "Email Service"
Client->>UserRoute : POST /api/user/test/submit
UserRoute->>ML : predict_with_explanation(responses)
ML-->>UserRoute : Prediction + explanation + recommendations
UserRoute->>DB : Insert test result
UserRoute->>DB : Append to user.test_history
UserRoute->>SMS : Notify stress result (optional)
UserRoute->>Email : Crisis alert (optional)
UserRoute-->>Client : TestResponse
```

**Diagram sources**
- [backend/app/routes/user_routes.py:407-499](file://backend/app/routes/user_routes.py#L407-L499)
- [backend/ml_model/predictor.py:146-185](file://backend/ml_model/predictor.py#L146-L185)

**Section sources**
- [backend/app/routes/user_routes.py:407-499](file://backend/app/routes/user_routes.py#L407-L499)
- [backend/app/routes/doctor_routes.py:48-134](file://backend/app/routes/doctor_routes.py#L48-L134)
- [backend/app/routes/admin_routes.py:14-62](file://backend/app/routes/admin_routes.py#L14-L62)

### Frontend Component Architecture and State Management
- The backend exposes REST endpoints designed for a React/Vite frontend with TypeScript.
- State management patterns:
  - Centralized state via React hooks and context providers.
  - Feature-based organization: authentication, user dashboard, doctor portal, admin analytics, medical records, and recommendations.
  - Async data fetching with caching and optimistic updates.
  - Type-safe APIs using generated TypeScript clients from OpenAPI specs.
- Component composition:
  - Shared components for forms, modals, charts, and progress tracking.
  - Protected routes with role-based rendering.
  - Real-time notifications via background jobs and polling fallbacks.

[No sources needed since this section provides conceptual guidance]

### Code Organization Principles and Naming Conventions
- Modular routing under backend/app/routes with clear separation of concerns.
- Centralized models and schemas in backend/app/models.py for consistent validation.
- Environment-driven configuration via backend/app/config.py and .env files.
- Utility modules for auth, analytics, reporting, and progress tracking.
- ML models isolated under backend/ml_model with training and inference utilities.
- Logging and error handling consistently applied across route handlers.

**Section sources**
- [backend/app/config.py:1-22](file://backend/app/config.py#L1-L22)
- [backend/app/main.py:14-20](file://backend/app/main.py#L14-L20)

### Security Implementations
- Transport security: CORS restricted to configured origins; HTTPS recommended in production.
- Data protection:
  - Passwords hashed with bcrypt; secrets loaded from environment variables.
  - JWT tokens with short-lived expirations; secure token handling.
  - File uploads sanitized with allowed extensions, size limits, and integrity checks.
- Access control:
  - require_role dependency enforces role-based access.
  - Object-level authorization ensures users can only access their own data.
  - Admin-only endpoints protected with admin role checks.
- Input validation:
  - Pydantic models enforce field types, lengths, and constraints.
  - File validation includes MIME detection and content signature checks.

**Section sources**
- [backend/app/main.py:32-68](file://backend/app/main.py#L32-L68)
- [backend/app/auth.py:33-72](file://backend/app/auth.py#L33-L72)
- [backend/app/routes/medical_records_routes.py:68-131](file://backend/app/routes/medical_records_routes.py#L68-L131)

### Testing Strategies, Logging, and Debugging
- Unit/integration tests for route handlers, auth utilities, and ML predictor.
- Mocked database collections for isolated testing.
- Logging:
  - Structured logging with levels (info, warning, error) across modules.
  - Database connection and operation logs during startup/shutdown.
- Debugging:
  - Health check endpoint validates database connectivity.
  - Detailed error responses with context for troubleshooting.
  - Environment variables for enabling development-friendly behaviors (e.g., OTP printing).

**Section sources**
- [backend/app/main.py:114-132](file://backend/app/main.py#L114-L132)
- [backend/app/database.py:44-54](file://backend/app/database.py#L44-L54)

## Dependency Analysis
The system exhibits clear layering with minimal cross-layer coupling:
- Routes depend on auth utilities and database collections.
- Application services (recommendations, progress, analytics, reporting) encapsulate business logic.
- ML models are decoupled and invoked by route handlers.
- Database layer centralizes collection access and indexing.

```mermaid
graph LR
Routes["Route Handlers"] --> Auth["Auth Utils"]
Routes --> DB["Database Layer"]
Routes --> ML["ML Models"]
Routes --> Services["Services (Email/SMS)"]
Services --> DB
ML --> DB
Auth --> DB
```

**Diagram sources**
- [backend/app/routes/user_routes.py:18-29](file://backend/app/routes/user_routes.py#L18-L29)
- [backend/app/auth.py:18-21](file://backend/app/auth.py#L18-L21)
- [backend/app/database.py:88-159](file://backend/app/database.py#L88-L159)

**Section sources**
- [backend/app/routes/user_routes.py:18-29](file://backend/app/routes/user_routes.py#L18-L29)
- [backend/app/auth.py:18-21](file://backend/app/auth.py#L18-L21)
- [backend/app/database.py:88-159](file://backend/app/database.py#L88-L159)

## Performance Considerations
- Connection pooling and timeouts configured for MongoDB client.
- Extensive indexes on frequently queried fields (user_id, timestamps, statuses, text search).
- Aggregation pipelines reduce round-trips for doctor appointment listings and analytics.
- Pagination and sorting applied to large collections (tests, appointments, medical records).
- File upload validation prevents oversized or unsupported files.

**Section sources**
- [backend/app/database.py:30-41](file://backend/app/database.py#L30-L41)
- [backend/app/database.py:164-298](file://backend/app/database.py#L164-L298)
- [backend/app/routes/doctor_routes.py:52-84](file://backend/app/routes/doctor_routes.py#L52-L84)

## Troubleshooting Guide
Common issues and resolutions:
- Database connectivity failures: Check MONGODB_URL and server availability; health endpoint returns database status.
- Invalid or expired tokens: Ensure proper Authorization header format and token freshness.
- Role/access denials: Verify user roles and object-level ownership for sensitive endpoints.
- File upload errors: Confirm allowed extensions, size limits, and MIME type validation.
- ML model integrity: Model files validated via SHA-256 hashes; invalid models trigger retraining.

**Section sources**
- [backend/app/main.py:114-132](file://backend/app/main.py#L114-L132)
- [backend/app/auth.py:57-72](file://backend/app/auth.py#L57-L72)
- [backend/app/routes/medical_records_routes.py:68-131](file://backend/app/routes/medical_records_routes.py#L68-L131)
- [backend/ml_model/predictor.py:73-98](file://backend/ml_model/predictor.py#L73-L98)

## Conclusion
The AI Stress Level Analyzer integrates robust backend services with a scalable MongoDB schema, secure JWT-based authentication, and comprehensive ML-driven insights. The modular architecture supports growth, while strict validation, indexing, and access controls ensure reliability and security.

## Appendices
- Environment variables and configuration keys are defined in backend/app/config.py and loaded via dotenv.
- Index creation runs on startup; verify logs for successful index creation.
- Admin initialization creates a default admin user if ADMIN_PASSWORD is set.

**Section sources**
- [backend/app/config.py:1-22](file://backend/app/config.py#L1-L22)
- [backend/app/database.py:307-339](file://backend/app/database.py#L307-L339)