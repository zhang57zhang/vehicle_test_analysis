@echo off
REM Vehicle Test Analysis - One-Click Stop Script
REM This script stops all running application processes

setlocal
cd /d "%~dp0"

echo ========================================
echo Vehicle Test Analysis - Stopping...
echo ========================================
echo.

REM Kill python processes running the application
echo [INFO] Stopping application processes...

REM Method 1: Kill by window title (if started with pythonw)
tasklist /FI "WINDOWTITLE eq Vehicle Test Analysis*" 2>nul | find /I "pythonw.exe" >nul
if %ERRORLEVEL% equ 0 (
    taskkill /F /FI "WINDOWTITLE eq Vehicle Test Analysis*" >nul 2>&1
    echo [OK] Stopped GUI window
)

REM Method 2: Kill python processes running src.main
wmic process where "CommandLine like '%%src.main%%'" get ProcessId 2>nul | findstr /r "[0-9]" >nul
if %ERRORLEVEL% equ 0 (
    for /f "skip=1" %%i in ('wmic process where "CommandLine like '%%src.main%%'" get ProcessId 2^>nul') do (
        taskkill /F /PID %%i >nul 2>&1
    )
    echo [OK] Stopped main process
)

REM Method 3: Kill any pythonw processes in this directory
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq pythonw.exe" /FO LIST ^| findstr "PID:"') do (
    taskkill /F /PID %%i >nul 2>&1
)
echo [OK] Cleanup complete

echo.
echo ========================================
echo Application stopped.
echo ========================================
echo.

endlocal
