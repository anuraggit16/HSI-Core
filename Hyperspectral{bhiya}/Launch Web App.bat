@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set "ROOT=%cd%"
set "PY=%ROOT%\.venv\Scripts\python.exe"
set "APP=%ROOT%\src\hyperspectral_viz\app.py"

if not exist "%PY%" (
  echo.
  echo  First-time setup: creating .venv ...
  where py >nul 2>&1
  if !errorlevel! equ 0 (
    py -3 -m venv ".venv"
  ) else (
    python -m venv ".venv"
  )
  if not exist "%PY%" (
    echo.
    echo  Could not create a venv. Install Python 3.10+ from https://www.python.org/downloads/
    echo  and ensure "python" or "py" is available in a new Command Prompt.
    echo.
    pause
    exit /b 1
  )
)

"%PY%" -m pip install -q --upgrade pip >nul 2>&1
"%PY%" -m pip install -q -e "%ROOT%"
if errorlevel 1 (
  echo.
  echo  pip install failed. Check your network connection and try again.
  echo.
  pause
  exit /b 1
)

echo.
echo  Starting local web app...
echo  If the browser does not open, go to: http://localhost:8501
echo  Close this window to stop the server.
echo.

"%PY%" -m streamlit run "%APP%" --server.address localhost --server.port 8501

echo.
pause
