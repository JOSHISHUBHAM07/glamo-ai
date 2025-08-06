@echo off
TITLE 🚀 AI PHOTO - FastAPI Server
echo ============================================
echo    🚀 Starting AI PHOTO FastAPI Application
echo ============================================

:: Step 1 - Check Python installation
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Python is not installed or not in PATH.
    pause
    exit /b
)

:: Step 2 - Check if virtual environment exists
IF NOT EXIST "venv" (
    echo 📦 Creating Python virtual environment...
    python -m venv venv
)

:: Step 3 - Activate virtual environment
call venv\Scripts\activate

:: Step 4 - Upgrade pip
echo ⏳ Upgrading pip...
python -m pip install --upgrade pip

:: Step 5 - Install dependencies
IF EXIST "requirements.txt" (
    echo 📥 Installing dependencies from requirements.txt...
    pip install -r requirements.txt
) ELSE (
    echo ⚠️ requirements.txt not found. Skipping dependency installation.
)

:: Step 6 - Start FastAPI server
echo ✅ Launching FastAPI server on http://127.0.0.1:8000
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

:: Keep the terminal open
pause
