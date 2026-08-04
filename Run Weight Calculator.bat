@echo off
rem Double-click launcher for the Weight Goal Calculator.
rem No build step and no dependencies - it just runs the Python script
rem sitting next to it. Requires Python 3.8+ with tkinter (see README).

cd /d "%~dp0"

where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw "weight_calculator.py"
    goto :eof
)

where python >nul 2>&1
if %errorlevel%==0 (
    python "weight_calculator.py"
    goto :eof
)

echo.
echo Python was not found on your PATH.
echo Install Python 3.8 or newer from https://www.python.org/downloads/
echo and be sure to check "Add Python to PATH" during setup.
echo.
pause
