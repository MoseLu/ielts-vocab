@echo off
cd /d %~dp0

:: IELTS Vocabulary Project - Project Manager
:: Starts backend (Python/Flask) and frontend (Vite) together
:: Managed by NSSM

set BACKEND_DIR=%~dp0backend
set LOG_DIR=D:\logs
set PYTHON_EXE=D:\Program Files\Python\python.exe

:: Start backend in background
echo [%date% %time%] Starting backend... >> %LOG_DIR%\ielts-vocab.log
start /B "" "%PYTHON_EXE%" -u "%BACKEND_DIR%\app.py" >> %LOG_DIR%\ielts-vocab-backend.log 2>&1

:: Wait for backend to be ready
echo [%date% %time%] Waiting for backend... >> %LOG_DIR%\ielts-vocab.log
timeout /t 3 /nobreak > nul

:: Start frontend
echo [%date% %time%] Starting frontend... >> %LOG_DIR%\ielts-vocab.log
start /B "" cmd /c "cd /d %~dp0 && pnpm run preview"

:: Keep script running to maintain NSSM service
echo [%date% %time%] All services started >> %LOG_DIR%\ielts-vocab.log
pause
