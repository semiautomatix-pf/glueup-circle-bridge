@echo off
REM Start both backend and frontend for GlueUp Circle Bridge

echo 🚀 Starting GlueUp Circle Bridge...

REM Check if virtual environment exists
if not exist ".venv\" (
    echo ❌ Virtual environment not found. Run setup-ui.bat first
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Load .env file
if exist .env (
    for /f "usebackq tokens=*" %%a in (".env") do (
        set "%%a"
    )
)

set SERVER_PORT=%SERVER_PORT%
if "%SERVER_PORT%"=="" set SERVER_PORT=8080

echo 🔧 Starting Flask backend on port %SERVER_PORT%...
start "Flask Backend" cmd /k "python -m src.web.server"

REM Wait for backend to be ready
echo ⏳ Waiting for backend to be ready...
timeout /t 3 /nobreak >nul

echo 🌐 Starting Streamlit UI...
start "Streamlit UI" cmd /k "streamlit run streamlit_app.py"

echo.
echo 📊 Services started in separate windows
echo   - Flask backend: http://localhost:%SERVER_PORT%
echo   - Streamlit UI: http://localhost:8501
echo.
echo Close the terminal windows to stop services
echo Or run scripts\stop.bat
