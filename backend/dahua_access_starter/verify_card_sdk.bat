@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run install.bat first to create the project-local .venv.
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" tools\verify_card_sdk.py
if errorlevel 1 pause
endlocal
