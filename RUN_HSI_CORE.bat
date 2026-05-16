@echo off
REM HSI-Core One-Click Launcher for Windows
REM Double-click this file to start the system

setlocal enabledelayedexpansion

cls

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║                                                           ║
echo ║   HSI-Core: Hyperspectral Imaging System v3.0             ║
echo ║                                                           ║
echo ║              Starting up...                              ║
echo ║                                                           ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo [OK] Python found

REM Create virtual environment if needed
if not exist "venv" (
    echo.
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo Installing dependencies (this may take 1-2 minutes^)...
pip install --quiet --upgrade pip

echo   Installing fastapi...
pip install --quiet fastapi
echo   Installing uvicorn...
pip install --quiet uvicorn[standard]
echo   Installing numpy...
pip install --quiet numpy
echo   Installing opencv-python...
pip install --quiet opencv-python
echo   Installing PyQt5...
pip install --quiet PyQt5
echo   Installing matplotlib...
pip install --quiet matplotlib
echo   Installing pydantic...
pip install --quiet pydantic
echo   Installing tifffile...
pip install --quiet tifffile
echo   Installing scipy...
pip install --quiet scipy
echo   Installing scikit-learn...
pip install --quiet scikit-learn

echo [OK] Dependencies installed

REM Create directories
if not exist "datasets" mkdir datasets
if not exist "scan_images" mkdir scan_images

echo.
echo ═════════════════════════════════════════════════════════════
echo SYSTEM READY
echo ═════════════════════════════════════════════════════════════
echo.

REM Show menu
echo Choose interface:
echo.
echo   1) Web Dashboard (Recommended^)
echo   2) Desktop GUI (PyQt5^)
echo   3) Exit
echo.

set /p choice="Enter choice (1-3^): "

if "%choice%"=="1" (
    cls
    echo.
    echo Starting Web Server...
    echo.
    echo Open browser to: http://localhost:8000
    echo Press Ctrl+C to stop
    echo.
    python server_enhanced.py
) else if "%choice%"=="2" (
    cls
    echo.
    echo Starting Desktop GUI...
    echo.
    python gui_main.py
) else if "%choice%"=="3" (
    echo Exiting...
    exit /b 0
) else (
    echo Invalid choice
    pause
    exit /b 1
)

pause
