@echo off
SETLOCAL EnableDelayedExpansion
TITLE Nana AI 2.0 - Production Launcher

cd /d "%~dp0"

:: Ensure logs directory exists
if not exist "backend\logs" mkdir "backend\logs"

:: Check for quiet/background flag
set "QUIET_MODE=0"
if "%1"=="--background" set "QUIET_MODE=1"

if "%QUIET_MODE%"=="0" (
    echo ========================================
    echo   Starting Nana AI Production 2.0
    echo ========================================
    echo.
)

:: Startup Backend (FastAPI + Uvicorn)
:: Using a loop to ensure it restarts if it crashes
echo [+] Launching Backend (FastAPI) [Auto-Restart Enabled]...
if "%QUIET_MODE%"=="1" (
    :: In quiet mode, we start the python process directly in background
    start "" /B "backend\.venv\Scripts\python.exe" -m uvicorn nana_backend_v2:socket_app --app-dir backend --host 0.0.0.0 --port 3001 --workers 1
) else (
    start "Nana Backend" cmd /k "cd backend && :loop && .venv\Scripts\python.exe -m uvicorn nana_backend_v2:socket_app --host 0.0.0.0 --port 3001 --workers 1 && echo Backend crashed! Restarting in 5s... && timeout 5 && goto loop"
)

:: Startup Frontend (Vite)
echo [+] Launching Frontend (Vite)...
cd frontend
if "%QUIET_MODE%"=="1" (
    start "" /B cmd /c "npm run dev"
) else (
    echo [INFO] Opening interface at http://localhost:5173
    timeout /t 3 /nobreak >nul
    start "" "http://localhost:5173"
    call npm run dev
)
cd ..

if "%QUIET_MODE%"=="1" (
    echo [OK] Nana AI is running in the background.
)
