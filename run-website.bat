@echo off
rem Image Lab - website version, served locally (double-click to start, close the window to stop)
cd /d "%~dp0web"
set "PY=..\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
start "" http://localhost:8000
"%PY%" -m http.server 8000
pause
