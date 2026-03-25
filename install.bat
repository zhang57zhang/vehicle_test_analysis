@echo off
REM Vehicle Test Analysis - Install Script

setlocal
cd /d "%~dp0"

echo.
echo ========================================
echo Vehicle Test Analysis - Installer
echo ========================================
echo.

echo [1/4] Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    echo Download: https://www.python.org/downloads/
    exit /b 1
)
python --version

echo.
echo [2/4] Creating virtual environment...
if exist "venv" (
    echo Virtual environment already exists, skipping
) else (
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment
        exit /b 1
    )
    echo Virtual environment created
)

echo.
echo [3/4] Installing dependencies...
venv\Scripts\pip.exe install --upgrade pip
venv\Scripts\pip.exe install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install dependencies
    exit /b 1
)

echo.
echo [4/4] Installing project...
venv\Scripts\pip.exe install -e .

echo.
echo ========================================
echo Installation complete!
echo ========================================
echo.
echo Usage:
echo   run.bat gui    Start GUI
echo   run.bat test   Run tests
echo   run.bat help   Show all commands
echo.

endlocal
