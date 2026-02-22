"""
FIXED main.py file
Location: backend/app/main.py
Action: REPLACE your existing backend/app/main.py with this entire file
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth_routes, user_routes, doctor_routes, admin_routes
from app.database import init_admin
import os
from pathlib import Path

# Try to import medical records routes
MEDICAL_RECORDS_ENABLED = False
try:
    from app.routes import medical_records_routes
    MEDICAL_RECORDS_ENABLED = True
except ImportError as e:
    print(f"⚠️ Medical records routes not found - feature disabled: {e}")

# Initialize FastAPI app
app = FastAPI(
    title="AI Stress Level Analyzer API",
    description="CBT-based stress detection system with ML and Medical Records Management",
    version="1.1.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(doctor_routes.router)
app.include_router(admin_routes.router)

# Include medical records router if available (NEW)
if MEDICAL_RECORDS_ENABLED:
    app.include_router(medical_records_routes.router)  # type: ignore
    print("✅ Medical Records routes enabled")

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_admin()
    print("🚀 Server started successfully!")
    print("📊 Admin credentials: username='admin', password='admin123'")
    
    # Create uploads directory if it doesn't exist (NEW)
    upload_dir = Path("uploads/medical_records")
    upload_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Upload directory ready: {upload_dir}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to AI Stress Level Analyzer API",
        "version": "1.1.0",
        "docs": "/docs",
        "status": "operational",
        "features": {
            "stress_testing": True,
            "appointments": True,
            "medical_records": MEDICAL_RECORDS_ENABLED
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "medical_records": MEDICAL_RECORDS_ENABLED
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)