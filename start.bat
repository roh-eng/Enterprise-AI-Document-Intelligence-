@echo off
title AI Document Intelligence - Launcher
cd /d "%~dp0"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

if not exist "%VENV_PY%" goto :noenv

echo ============================================================
echo   AI Document Intelligence Platform - starting...
echo ============================================================
echo.
echo [1/2] Backend  -^> http://localhost:8000/docs
start "AIDoc Backend" /D "%~dp0backend" cmd /k ""%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo       waiting ~8s for the backend to initialise...
timeout /t 8 /nobreak >nul

echo [2/2] Frontend -^> http://localhost:8501
start "AIDoc Frontend" /D "%~dp0." cmd /k ""%VENV_PY%" -m streamlit run frontend/app.py"

echo.
echo Both services launched in separate windows.
echo   Backend : http://localhost:8000/docs
echo   Frontend: http://localhost:8501
echo.
echo Close those two windows to stop the servers.
echo.
pause
exit /b 0

:noenv
echo [ERROR] Virtual environment not found at:
echo     %VENV_PY%
echo.
echo Create it first, from this folder:
echo     python -m venv .venv
echo     .venv\Scripts\python -m pip install -r requirements.txt
echo.
pause
exit /b 1
