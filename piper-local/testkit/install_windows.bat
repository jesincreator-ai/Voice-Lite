@echo off
setlocal
cd /d "%~dp0"
py -3.11 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo.
echo Installed. Run: .venv\Scripts\python test_ta_si.py --language ta --mode standard
pause
exit /b 0
:fail
echo Installation failed. Install Python 3.11 64-bit and retry.
pause
exit /b 1
