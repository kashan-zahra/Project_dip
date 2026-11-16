@echo off
rem ============================================================
rem  Image Lab (Python / Flask) - one-time setup
rem  Creates the virtual environment in this folder (.\venv)
rem  and installs everything from requirements.txt.
rem ============================================================
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    echo The venv already exists. Updating the packages...
    goto install
)

set "PY="
rem (quotes kept inside PY because the path has a space)
if exist "E:\program files\python\python.exe" set PY="E:\program files\python\python.exe"
if not defined PY (
    where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo Python was not found. Install it from https://www.python.org and run this again.
    pause
    exit /b 1
)

echo Creating the virtual environment with %PY% ...
%PY% -m venv venv
if errorlevel 1 (
    echo Could not create the venv.
    pause
    exit /b 1
)

:install
echo Installing packages (first time: a few minutes)...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Something went wrong while installing. Check your internet connection and run this again.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Done! Start the app with run.bat, or in VS Code open
echo  app.py and press the Run button.
echo ============================================================
pause
