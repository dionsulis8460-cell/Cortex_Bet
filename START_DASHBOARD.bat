@echo off
TITLE Cortex Bet  - Dashboard Launcher
COLOR 0B

echo ====================================================
echo      CORTEX BET - INITIALIZING...
echo ====================================================

:: Path configuration
set PROJECT_ROOT=c:\Users\Valmont\Desktop\Cortex_Bet
set VENV_ACTIVATE=%PROJECT_ROOT%\.venv\Scripts\activate.bat

echo [1/2] Starting System (Backend) in new window...
start cmd /k "cd /d %PROJECT_ROOT% && call %VENV_ACTIVATE% && echo Starting System... && python start_system.py"

echo [2/2] Starting Dashboard (Frontend)...
cd /d %PROJECT_ROOT%\web_app
npm run dev

pause
