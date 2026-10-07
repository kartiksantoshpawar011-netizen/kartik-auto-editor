@echo off
REM Kartik Auto Editor - Windows Launcher
REM This script sets up the Python environment and launches the GUI application.
REM User should only need to double-click this file.

setlocal enabledelayedexpansion

REM Get the directory where this script is located
cd /d "%~dp0"

echo.
echo ============================================================
echo  Kartik Auto Editor v1.0.0
echo ============================================================
echo.

REM Check if Python is installed and accessible
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python 3.11+ is not installed or not in PATH.
    echo.
    echo How to fix:
    echo   1. Download Python 3.11+ from https://www.python.org/downloads/
    echo   2. During installation, CHECK "Add Python to PATH"
    echo   3. After installation, close this window and run run.bat again
    echo.
    pause
    exit /b 1
)

REM Display Python version
echo [OK] Python found:
python --version
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment (.venv)...
    echo.
    
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create virtual environment.
        echo.
        echo Possible reasons:
        echo   - Not enough disk space
        echo   - Permission denied (try running as Administrator)
        echo   - Python installation is corrupted
        echo.
        echo Try this:
        echo   1. Delete the .venv folder if it exists
        echo   2. Right-click run.bat and select "Run as Administrator"
        echo   3. Try again
        echo.
        pause
        exit /b 1
    )
    
    echo [OK] Virtual environment created
    echo.
)

REM Upgrade pip
echo [INFO] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo [WARNING] pip upgrade had issues (continuing anyway)
)
echo.

REM Install dependencies from requirements.txt
echo [INFO] Installing dependencies from requirements.txt...
echo.
echo This may take a few minutes on first run...
echo.

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies.
    echo.
    echo Possible reasons:
    echo   - Internet connection is not working
    echo   - requirements.txt is missing or corrupted
    echo   - pip cache is corrupted
    echo.
    echo Try this:
    echo   1. Check your internet connection
    echo   2. Delete the .venv folder
    echo   3. Run run.bat again
    echo.
    echo If problems persist, try in Command Prompt:
    echo   ".venv\Scripts\python.exe" -m pip install --upgrade pip
    echo   ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] All dependencies installed successfully
echo.

REM Verify that required modules are installed
echo [INFO] Verifying installation...
".venv\Scripts\python.exe" -c "import PySide6; import faster_whisper; import imageio_ffmpeg; print('[OK] All required modules are available')" 2>nul
if errorlevel 1 (
    echo [ERROR] Missing required modules after installation.
    echo.
    echo Try this:
    echo   1. Delete the .venv folder
    echo   2. Run run.bat again
    echo   3. If problem persists, check your internet connection
    echo.
    pause
    exit /b 1
)
echo.

REM Create necessary directories
if not exist "models" mkdir models
if not exist "exports" mkdir exports
if not exist "work" mkdir work

echo [INFO] Directories ready:
echo   - models/ (for Whisper models)
echo   - exports/ (for final videos)
echo   - work/ (for temporary files)
echo.

REM Launch the application
echo [INFO] Launching Kartik Auto Editor GUI...
echo.

REM Try to launch with pythonw (no console window)
REM If that fails, fall back to python (with console window for debugging)
start "" ".venv\Scripts\pythonw.exe" "app\main.py" 2>nul
if errorlevel 1 (
    REM pythonw failed, try python instead
    ".venv\Scripts\python.exe" "app\main.py"
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to launch the application.
        echo.
        echo Try running in Command Prompt to see the error:
        echo   cd /d "%cd%"
        echo   ".venv\Scripts\python.exe" "app\main.py"
        echo.
        pause
        exit /b 1
    )
) else (
    REM Application launched successfully
    echo [OK] GUI launched. If you don't see a window, it may be loading.
    echo     Please wait a moment for the interface to appear.
    echo.
    echo Note: This window will close automatically.
)

endlocal
exit /b 0
