@echo off
:: Move to the directory where this bat file is located
cd /d "%~dp0"

echo [JWFileFilter] 가상 환경(venv)을 활성화하는 중...

:: 가상 환경 활성화 확인 및 실행
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate
    echo [JWFileFilter] 애플리케이션 실행 중...
    python jwfilefiltergui.py
) else (
    echo [오류] venv 폴더 또는 가상 환경 활성화 스크립트가 존재하지 않습니다.
    echo README.md를 참고하여 'python -m venv venv'로 가상 환경을 생성하고
    echo 'pip install -r requirements.txt'로 필요한 패키지를 설치해 주세요.
    pause
)

:: 실행 에러 코드가 있을 경우 창 유지
if %ERRORLEVEL% neq 0 (
    echo.
    echo [오류] 애플리케이션이 에러 코드 %ERRORLEVEL%로 종료되었습니다.
    pause
)
