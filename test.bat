@echo off
REM Windows test script for AI Stress Analyzer
REM ✅ LOW FIX: Create Windows-compatible test scripts

setlocal enabledelayedexpansion

echo.
echo ================================
echo AI Stress Level Analyzer - Tests
echo ================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

cd /d "%~dp0backend"

REM Activate virtual environment
if exist "venv\" (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found
    echo Please run start.bat first
    exit /b 1
)

echo Running backend tests...
echo.

REM Run pytest if available
python -m pytest -v

if !errorlevel! neq 0 (
    echo.
    echo Tests completed with errors
    exit /b 1
)

echo.
echo ✓ All tests passed!
echo.
