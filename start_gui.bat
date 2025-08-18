@echo off
echo Starting VTuber GUI Application...
echo.

REM Change to the directory containing this script
cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Start the GUI using the Python script
python start_gui.py

echo.
echo Press any key to exit...
pause > nul