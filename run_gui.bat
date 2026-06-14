@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Photo Organizer GUI Launcher
echo ========================================
echo.

cd /d "%~dp0"

if not exist "photo_organizer" (
    echo [ERROR] photo_organizer folder not found.
    pause
    exit /b 1
)

cd photo_organizer

if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
    echo [INFO] venv created.
) else (
    echo [INFO] Using existing venv.
)

echo [INFO] Activating venv...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate venv.
    pause
    exit /b 1
)

echo [INFO] Installing requirements...
if exist "..\requirements.txt" (
    pip install -r ..\requirements.txt --quiet
) else (
    echo [WARN] requirements.txt not found.
)

echo [INFO] Starting GUI...
echo.
python -m gui.main_gui

deactivate

echo.
echo [INFO] GUI closed.
pause
endlocal
