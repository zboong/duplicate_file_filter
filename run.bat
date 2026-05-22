@echo off
:: Move to the directory where this bat file is located
cd /d "%~dp0"

echo [JWFileFilter] Checking virtual environment...

if not exist venv\Scripts\python.exe goto ERROR_NO_VENV

echo [JWFileFilter] Running application...
venv\Scripts\python.exe jwfilefiltergui.py
if %ERRORLEVEL% neq 0 goto ERROR_RUN
goto END

:ERROR_NO_VENV
echo [ERROR] Virtual environment (venv) not found.
echo Please create it first by running:
echo   python -m venv venv
echo   venv\Scripts\pip install -r requirements.txt
echo.
pause
goto END

:ERROR_RUN
echo.
echo [ERROR] Application exited with error code %ERRORLEVEL%.
pause
goto END

:END
