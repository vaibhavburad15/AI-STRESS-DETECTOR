"""
Application entry point.
"""

import os
import logging
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables before importing modules that read them at import time.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.database import init_admin, close_mongo_connection
from app.routes import auth_routes, user_routes, doctor_routes, admin_routes

logger = logging.getLogger(__name__)

# Try to import medical records routes
MEDICAL_RECORDS_ENABLED = False
try:
    from app.routes import medical_records_routes
    if hasattr(medical_records_routes, "router"):
        MEDICAL_RECORDS_ENABLED = True
except (ImportError, AttributeError) as e:
    logger.warning("Medical records routes disabled: %s", e)


def _get_allowed_origins() -> list[str]:
    origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
    valid_origins: list[str] = []

    for origin in origins_raw.split(","):
        candidate = origin.strip().rstrip("/")
        if not candidate:
            continue

        parsed = urlparse(candidate)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            valid_origins.append(candidate)
        else:
            logger.warning("Ignoring invalid CORS origin: %s", candidate)

    if not valid_origins:
        valid_origins = ["http://localhost:3000"]

    return valid_origins

# Initialize FastAPI app
app = FastAPI(
    title="AI Stress Level Analyzer API",
    description="CBT-based stress detection system with ML and Medical Records Management",
    version="1.1.0"
)

# CORS configuration
# ✅ FIX: Add env variable for frontend URL, restrict CORS in production
allowed_origins = _get_allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Specify actual frontend URL(s)
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
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
    # ✅ CRITICAL FIX: Don't print hardcoded admin credentials
    # Admin password should be set via environment variable or secure admin creation flow
    
    # Create uploads directory if it doesn't exist (NEW)
    upload_dir = Path("uploads/medical_records")
    upload_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Upload directory ready: {upload_dir}")

@app.on_event("shutdown")
async def shutdown_event():
    """Close resources on shutdown."""
    close_mongo_connection()

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
    """Health check endpoint - verifies database connectivity"""
    # ✅ FIX: Actually check database health, not just return "healthy"
    try:
        from app.database import client
        if client is not None:
            client.admin.command('ping')
            db_status = "connected"
        else:
            db_status = "unavailable"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "medical_records": MEDICAL_RECORDS_ENABLED
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
