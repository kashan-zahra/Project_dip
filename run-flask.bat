@echo off
rem Image Lab - Python / Flask version (double-click to start, close the window to stop)
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo First run setup.bat to create the venv.
    pause
    exit /b 1
)
start "" http://127.0.0.1:5000
cd python-flask
"..\venv\Scripts\python.exe" app.py
pause
