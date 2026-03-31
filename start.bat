@echo off
REM Vehicle Test Analysis - One-Click Start Script
REM This script starts the GUI application

setlocal
cd /d "%~dp0"

echo ========================================
echo Vehicle Test Analysis - Starting...
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run install.bat first to set up the environment.
    echo.
    pause
    exit /b 1
)

REM Check if database exists, create if not
if not exist "database\vehicle_test.db" (
    echo [INFO] Initializing database...
    if not exist "database" mkdir database
    venv\Scripts\python.exe -c "from src.database.models import init_database; init_database('sqlite:///database/vehicle_test.db')"
)

echo [INFO] Starting GUI application...
echo [INFO] Default login: admin / admin123
echo.
echo Close this window to stop the application.
echo ========================================
echo.

REM Start the GUI with skip-login option for development
REM Remove --skip-login to enable login screen
venv\Scripts\pythonw.exe -m src.main --gui --skip-login

endlocal
