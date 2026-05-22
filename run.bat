@echo off
:: Move to the directory where this bat file is located
cd /d "%~dp0"

echo [JWFileFilter] 가상 환경(venv)의 Python을 확인하고 실행합니다...

:: 가상 환경의 python.exe 존재 확인 및 실행
if exist "venv\Scripts\python.exe" (
    echo [JWFileFilter] 애플리케이션 실행 중...
    "venv\Scripts\python.exe" jwfilefiltergui.py
) else (
    echo [오류] venv 가상 환경이 설정되지 않았거나 venv\Scripts\python.exe를 찾을 수 없습니다.
    echo README.md를 참고하여 'python -m venv venv'로 가상 환경을 생성하고
    echo 'venv\Scripts\pip install -r requirements.txt'로 패키지를 설치해 주세요.
    pause
)

:: 실행 에러 코드가 있을 경우 창 유지
if %ERRORLEVEL% neq 0 (
    echo.
    echo [오류] 애플리케이션이 에러 코드 %ERRORLEVEL%로 종료되었습니다.
    pause
)
