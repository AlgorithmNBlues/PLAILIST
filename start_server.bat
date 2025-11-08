@echo off
echo Starting Flask server...
echo.
cd /d "%~dp0"
call ub_hacking\Scripts\activate.bat
echo Virtual environment activated
echo.
python backend\app.py
pause
