@echo off
setlocal
cd /d "%~dp0"
if exist "..\venv\Scripts\python.exe" (
  ..\venv\Scripts\python.exe tools\verify_card_sdk.py
) else (
  python tools\verify_card_sdk.py
)
if errorlevel 1 pause
endlocal
