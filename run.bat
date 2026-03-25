@echo off
REM Vehicle Test Analysis - Windows Startup Script

setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run install.bat first.
    exit /b 1
)

set COMMAND=%1

if "%COMMAND%"=="" goto help
if "%COMMAND%"=="gui" goto gui
if "%COMMAND%"=="cli" goto cli
if "%COMMAND%"=="test" goto test
if "%COMMAND%"=="install" goto install
if "%COMMAND%"=="clean" goto clean

:help
echo.
echo Vehicle Test Analysis
echo.
echo Usage: run.bat [command]
echo.
echo Commands:
echo   gui      Start GUI
echo   cli      Start CLI
echo   test     Run tests
echo   install  Install dependencies
echo   clean    Clean cache files
echo.
exit /b 0

:gui
echo Starting GUI...
venv\Scripts\python.exe -m src.main --gui
exit /b %ERRORLEVEL%

:cli
echo Starting CLI...
venv\Scripts\python.exe -m src.main
exit /b %ERRORLEVEL%

:test
echo Running tests...
venv\Scripts\python.exe -m pytest tests/ -v --cov=src --cov-report=term-missing
exit /b %ERRORLEVEL%

:install
echo Installing dependencies...
venv\Scripts\pip.exe install -r requirements.txt
venv\Scripts\pip.exe install -e .
echo Done.
exit /b 0

:clean
echo Cleaning cache files...
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
if exist ".coverage" del /q ".coverage"
if exist "htmlcov" rd /s /q "htmlcov"
if exist ".pytest_cache" rd /s /q ".pytest_cache"
echo Done.
exit /b 0

endlocal
