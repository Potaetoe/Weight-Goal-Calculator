@echo off
rem Double-click launcher for the Weight Goal Calculator.
rem No build step and no dependencies - it just runs the Python app.
rem Requires Python 3.8+ with tkinter (see README.dev.md).
rem
rem Runs from the repo root rather than from this folder, because the app
rem imports core.calc_core and needs the root on sys.path.

cd /d "%~dp0..\.."

where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw -m apps.desktop.weight_calculator
    goto :eof
)

where python >nul 2>&1
if %errorlevel%==0 (
    python -m apps.desktop.weight_calculator
    goto :eof
)

echo.
echo Python was not found on your PATH.
echo Install Python 3.8 or newer from https://www.python.org/downloads/
echo and be sure to check "Add Python to PATH" during setup.
echo.
pause
