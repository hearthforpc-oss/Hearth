@echo off
echo Starting HearthSync...

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b
)

:: Run the app
python "%~dp0hearth_sync.pyw"
pause
