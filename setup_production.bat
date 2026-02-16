@echo off
SETLOCAL EnableDelayedExpansion
TITLE Nana AI 2.0 - Production Setup

:: Ensure we are in the correct directory
cd /d "%~dp0"

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] ERROR: Please run this script as ADMINISTRATOR.
    echo Right-click -> Run as Administrator
    pause
    exit /b
)

echo ========================================
echo   Nana AI 2.0: Production Setup
echo ========================================
echo.

set "TASK_NAME=NanaAI_Production"
set "SCRIPT_DIR=%~dp0"
set "LAUNCHER=%SCRIPT_DIR%start_nana_v2.bat"
set "PS_HELPER=%SCRIPT_DIR%run_hidden_v2.ps1"

:: 1. Create PS Helper
echo [1/4] Creating hidden launch helper...
(
echo $scriptPath = Join-Path $PSScriptRoot "start_nana_v2.bat"
echo $arguments = "--background"
echo Start-Process -FilePath "cmd.exe" -ArgumentList "/c \`"$scriptPath\`" $arguments" -WindowStyle Hidden
) > "!PS_HELPER!"
echo [OK] Helper created.

:: 2. Configure Firewall
echo [2/4] Configuring Windows Firewall...
netsh advfirewall firewall delete rule name="Nana AI - Backend" >nul 2>&1
netsh advfirewall firewall delete rule name="Nana AI - Frontend" >nul 2>&1
netsh advfirewall firewall add rule name="Nana AI - Backend" dir=in action=allow protocol=TCP localport=3001 profile=any description="Nana AI production backend" >nul
netsh advfirewall firewall add rule name="Nana AI - Frontend" dir=in action=allow protocol=TCP localport=5173 profile=any description="Nana AI production frontend" >nul
echo [OK] Ports 3001 and 5173 are open.

:: 3. Create Task Scheduler Entry
echo [3/4] Registering Windows Task Scheduler entry...
:: Delete existing if any
schtasks /delete /tn "!TASK_NAME!" /f >nul 2>&1

:: Create new task: Run at logon of any user, highest privileges
schtasks /create /tn "!TASK_NAME!" /tr "powershell.exe -ExecutionPolicy Bypass -File \"!PS_HELPER!\"" /sc onlogon /rl highest /f

if !errorLevel! equ 0 (
    echo [OK] Task Registered: Nana will start automatically at login.
) else (
    echo [ERROR] Failed to register task.
)

:: 4. Cleanup old Startup Shortcut
echo [4/4] Cleaning up legacy startup shortcuts...
set "OLD_SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Nana_AI_Assistant.lnk"
if exist "!OLD_SHORTCUT!" (
    del "!OLD_SHORTCUT!"
    echo [OK] Legacy shortcut removed.
) else (
    echo [SKIP] No legacy shortcut found.
)

echo.
echo ========================================
echo   Production Setup Complete!
echo ========================================
echo.
echo Nana AI 2.0 is now configured for high-stability background operation.
echo It will start automatically next time you log in.
echo.
echo You can start it manually now by running: start_nana_v2.bat
echo.
pause
