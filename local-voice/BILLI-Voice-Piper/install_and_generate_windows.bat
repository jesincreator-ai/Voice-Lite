@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher 'py' is missing. Install Python 3.11 x64 first.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv
  if errorlevel 1 goto :fail
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail
python -m host.generate_voice_clips --languages all --modes all
if errorlevel 1 goto :fail
echo.
echo Generated clips under build\voice_clips. Copy en, ta and si to /billi_voice/ on the SD card.
pause
exit /b 0
:fail
echo.
echo Setup or generation failed. Read the error above and docs\PC_SETUP.md.
pause
exit /b 1
