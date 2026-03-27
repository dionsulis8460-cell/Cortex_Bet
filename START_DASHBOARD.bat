@echo off
TITLE Cortex Bet  - Dashboard Launcher
COLOR 0B

echo ====================================================
echo      CORTEX BET - INITIALIZING...
echo ====================================================

:: Path configuration based on current script location
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR:~0,-1%
set PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
	echo [ERROR] Python virtual environment not found at:
	echo         %PYTHON_EXE%
	pause
	exit /b 1
)

echo [1/1] Starting unified local stack...
cd /d %PROJECT_ROOT%
"%PYTHON_EXE%" start_system.py

pause
