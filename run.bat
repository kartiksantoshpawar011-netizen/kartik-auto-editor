@echo off
REM Kartik Auto Editor - Windows launcher
REM Creates .venv, installs dependencies, and launches the GUI

setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Check if Python 3.11+ is available
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python was not found in PATH.
    echo Please install Python 3.11 or later from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Create virtual environment if it does not exist
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Creating local Python virtual environment...
    echo.
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created.
)

REM Upgrade pip
echo.
echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip
    pause
    exit /b 1
)

REM Install dependencies from requirements.txt
echo Installing dependencies from requirements.txt...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    echo.
    echo Make sure requirements.txt exists and your internet connection is working.
    pause
    exit /b 1
)

echo.
echo Setup complete. Launching Kartik Auto Editor...
echo.

REM Launch the application using pythonw (no console window)
start "" ".venv\Scripts\pythonw.exe" app\main.py

REM If pythonw is not available, fall back to python
if errorlevel 1 (
    ".venv\Scripts\python.exe" app\main.py
)

endlocal
