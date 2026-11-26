@echo off
setlocal
cd /d "%~dp0"
echo BILLI Tamil + Sinhala Piper repair
if not exist .venv\Scripts\python.exe py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements_fix.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe generate_local_tamil_sinhala.py --language all --mode all
if errorlevel 1 goto failed
echo.
echo DONE. Generated clips are in build\voice_clips. Play WAVs on PC and verify pronunciation before SD copy.
pause
exit /b 0
:failed
echo.
echo ERROR. Check network, Python 3.11 install and pip output above.
pause
exit /b 1
