@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
python -m unittest discover -s tests -v
if errorlevel 1 exit /b 1
python -m compileall -q host esp32 training tests
if errorlevel 1 exit /b 1
echo All host tests passed.
