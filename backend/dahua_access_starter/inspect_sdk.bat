@echo off
setlocal
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python tools\inspect_sdk.py > sdk_inspection.txt 2>&1
echo SDK inspection saved to sdk_inspection.txt
pause
