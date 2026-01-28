@echo off
REM Quick setup script for GlueUp Circle Bridge UI

echo 🔄 Setting up GlueUp Circle Bridge Web UI...
echo.

REM Check Python version
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3.8 or higher
    echo    Download from: https://www.python.org/downloads/
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Found Python %PYTHON_VERSION%

REM Check if virtual environment exists
if not exist ".venv\" (
    echo 📦 Creating virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ❌ Failed to create virtual environment
        exit /b 1
    )
) else (
    echo ✅ Virtual environment already exists
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install backend dependencies
if exist "requirements.txt" (
    echo 📦 Installing backend dependencies...
    python -m pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
) else (
    echo ⚠️  requirements.txt not found, skipping backend dependencies
)

REM Install UI dependencies
if exist "requirements-ui.txt" (
    echo 📦 Installing UI dependencies...
    pip install --quiet -r requirements-ui.txt
) else (
    echo ⚠️  requirements-ui.txt not found, skipping UI dependencies
)

echo.
echo ✅ Setup complete!
echo.
echo To start the application:
echo.
echo   Quick start:
echo     scripts\start.bat
echo.
echo   Or manually (two terminals):
echo.
echo   Terminal 1 (Backend):
echo     .venv\Scripts\activate.bat
echo     python -m src.web.server
echo.
echo   Terminal 2 (UI):
echo     .venv\Scripts\activate.bat
echo     streamlit run streamlit_app.py
echo.

pause
