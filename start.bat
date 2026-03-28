@echo off
REM Windows startup script for AI Stress Analyzer
REM ✅ LOW FIX: Create Windows-compatible scripts (previously Bash-only)

setlocal enabledelayedexpansion

echo.
echo ================================
echo AI Stress Level Analyzer - Start
echo ================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if !errorlevel! neq 0 (
    echo WARNING: Node.js is not installed. Frontend development server will not start.
) else (
    echo ✓ Node.js detected
)

echo.
echo Starting Backend Server...
echo.

REM Navigate to backend directory
cd /d "%~dp0backend"

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

REM Train questionnaire model if it has not been created for this environment yet
if not exist "..\data\runtime_models\stress_model.pkl" (
    echo.
    echo Training ML model (first time only)...
    python -m ml_model.train_model
)

REM Start backend server
echo.
echo ✓ Starting backend server on http://localhost:8000
echo.
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

REM If we get here, backend failed to start
echo.
echo ERROR: Backend server failed to start
echo.
pause
exit /b 1
