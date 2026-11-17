@echo off
rem DIP Lab Basics (double-click to start, close the window to stop)
cd /d "%~dp0"
set "PY=venv\Scripts\python.exe"
rem no venv here yet? use the one from the full version if it exists
if not exist "%PY%" if exist "..\python-flask\venv\Scripts\python.exe" set "PY=..\python-flask\venv\Scripts\python.exe"
if not exist "%PY%" (
    echo First run setup.bat to create the venv.
    pause
    exit /b 1
)
start "" http://127.0.0.1:5000
"%PY%" app.py
pause
