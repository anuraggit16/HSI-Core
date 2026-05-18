@echo off
setlocal EnableExtensions

title HSI-Core Instrument OS
cd /d "%~dp0"

set "APP_URL=http://127.0.0.1:8000"
set "PYTHON_EXE=venv\Scripts\python.exe"

cls
echo.
echo ============================================================
echo  HSI-Core Instrument OS
echo ============================================================
echo.

if "%~1"=="--check" (
    echo Launcher check OK
    exit /b 0
)

if not exist "%PYTHON_EXE%" (
    echo [SETUP] Creating local Python environment...
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo [ERROR] Python environment could not be created.
        echo Install Python, then run this file again.
        pause
        exit /b 1
    )
)

"%PYTHON_EXE%" -c "import fastapi, uvicorn, cv2, numpy, tifffile, pydantic" >nul 2>nul
if errorlevel 1 (
    echo [SETUP] Installing required packages. First run may take a few minutes...
    "%PYTHON_EXE%" -m pip install --upgrade pip
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Required packages could not be installed.
        pause
        exit /b 1
    )
)

if not exist "scan_images" mkdir scan_images
if not exist "datasets" mkdir datasets

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing '%APP_URL%/api/status' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
if not errorlevel 1 (
    echo [OK] HSI-Core is already running.
    echo Opening dashboard: %APP_URL%
    if not "%HSI_NO_BROWSER%"=="1" start "" "%APP_URL%"
    exit /b 0
)

echo [START] Starting backend and opening dashboard...
echo.
echo Dashboard: %APP_URL%
echo Stop: close this window or press Ctrl+C
echo.

if not "%HSI_NO_BROWSER%"=="1" start "" "%APP_URL%"
"%PYTHON_EXE%" -m uvicorn server_enhanced:app --host 127.0.0.1 --port 8000

echo.
echo HSI-Core stopped.
pause
