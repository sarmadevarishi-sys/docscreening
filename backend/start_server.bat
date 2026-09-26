@echo off
echo ============================================================
echo   SatyaKavach AI Backend Server
echo ============================================================
echo.
echo Checking if port 8000 is already in use...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 "') do (
    echo Found existing process on port 8000, stopping it...
    taskkill /F /PID %%a >nul 2>&1
)

:: Reload PATH so FFmpeg installed by winget is visible
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set USERPATH=%%b
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set SYSPATH=%%b
set PATH=%SYSPATH%;%USERPATH%

echo.
echo Starting FastAPI server on http://localhost:8000
echo Pre-cached AI models: YOLO + EasyOCR + SFace Face Verifier
echo (All models run 100% offline from local weights)
echo.
echo Keep this window open while using the website.
echo Close this window to stop the server.
echo.
cd /d "%~dp0"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
