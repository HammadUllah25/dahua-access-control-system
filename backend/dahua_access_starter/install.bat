@echo off
setlocal
cd /d "%~dp0"

if not exist .venv (
    py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo If the Dahua wheel is not installed in this environment, install it now:
echo   pip install "C:\path\to\NetSDK-2.0.0.1-py3-none-win_amd64.whl"
echo.
echo Then run run.bat
pause
