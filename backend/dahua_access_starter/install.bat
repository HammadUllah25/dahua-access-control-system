@echo off
setlocal
cd /d "%~dp0"

set "PROJECT_PYTHON=%~dp0.venv\Scripts\python.exe"
set "SDK_WHEEL=%~dp0vendor\NetSDK-2.0.0.1-py3-none-win_amd64.whl"

if not exist "%PROJECT_PYTHON%" (
    echo Creating project-local Python environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Could not create .venv. Check that 64-bit Python is installed and on PATH.
        pause
        exit /b 1
    )
)

if not exist "%SDK_WHEEL%" (
    echo ERROR: Bundled Dahua SDK wheel was not found:
    echo %SDK_WHEEL%
    pause
    exit /b 1
)

"%PROJECT_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :failed

"%PROJECT_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

"%PROJECT_PYTHON%" -m pip install "%SDK_WHEEL%"
if errorlevel 1 goto :failed

"%PROJECT_PYTHON%" tools\verify_setup.py
if errorlevel 1 goto :failed

echo.
echo Setup completed. Start the API with run.bat.
echo.
pause
exit /b 0

:failed
echo.
echo SETUP FAILED. Read the error above, correct it, and run install.bat again.
echo.
pause
exit /b 1
