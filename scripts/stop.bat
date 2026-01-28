@echo off
REM Stop GlueUp Circle Bridge services

echo 🛑 Stopping GlueUp Circle Bridge services...

REM Kill Flask backend
for /f "tokens=2" %%a in ('tasklist /FI "WINDOWTITLE eq Flask Backend*" /NH 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    echo   ✅ Flask stopped
)

REM Kill Streamlit
for /f "tokens=2" %%a in ('tasklist /FI "WINDOWTITLE eq Streamlit UI*" /NH 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    echo   ✅ Streamlit stopped
)

REM Alternative: kill by process name if window title doesn't work
taskkill /F /IM python.exe /FI "COMMANDLINE eq *src.web.server*" >nul 2>&1
taskkill /F /IM python.exe /FI "COMMANDLINE eq *streamlit*" >nul 2>&1

echo ✅ All services stopped
