@echo off
cd /d %~dp0

:: IELTS Vocabulary Project Launcher
:: Manages backend (Python) and frontend (Vite) as a single NSSM service

set LOG_DIR=D:\logs
set BACKEND_LOG=%LOG_DIR%\ielts-vocab-backend.log
set FRONTEND_LOG=%LOG_DIR%\ielts-vocab-frontend.log
set PROJECT_LOG=%LOG_DIR%\ielts-vocab.log

echo [%date% %time%] === IELTS Vocabulary Starting === > %PROJECT_LOG%

:: Kill any existing processes on our ports first
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    echo [%date% %time%] Killing backend PID %%a >> %PROJECT_LOG%
    taskkill /F /PID %%a >> %PROJECT_LOG% 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3002 " ^| findstr "LISTENING"') do (
    echo [%date% %time%] Killing frontend PID %%a >> %PROJECT_LOG%
    taskkill /F /PID %%a >> %PROJECT_LOG% 2>&1
)

timeout /t 2 /nobreak > nul

:: Start backend
echo [%date% %time%] Starting backend... >> %PROJECT_LOG%
start /B "" cmd /c "cd /d F:\enterprise-workspace\projects\ielts-vocab\backend && D:\Program Files\Python\python.exe -u app.py" >> "%BACKEND_LOG%" 2>&1

:: Wait for backend to start
timeout /t 4 /nobreak > nul

:: Start frontend using node.exe directly (avoids pnpm.ps1 issues)
echo [%date% %time%] Starting frontend via node... >> %PROJECT_LOG%
start "ieltsfe" cmd /c "cd /d F:\enterprise-workspace\projects\ielts-vocab && node node_modules\vite\bin\vite.js --port 3002 --host 0.0.0.0" >> "%FRONTEND_LOG%" 2>&1

echo [%date% %time%] All services started >> %PROJECT_LOG%

:: Monitor loop - just keep running and restart if ports go down
:monitor
timeout /t 20 /nobreak > nul

:: Simple check - if port not listening, restart that service
netstat -ano | findstr ":5000 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo [%date% %time%] Backend down, restarting... >> %PROJECT_LOG%
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
    start /B "" cmd /c "cd /d F:\enterprise-workspace\projects\ielts-vocab\backend && D:\Program Files\Python\python.exe -u app.py" >> "%BACKEND_LOG%" 2>&1
)

netstat -ano | findstr ":3002 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo [%date% %time%] Frontend down, restarting... >> %PROJECT_LOG%
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3002 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
    start "ieltsfe" cmd /c "cd /d F:\enterprise-workspace\projects\ielts-vocab && node node_modules\vite\bin\vite.js --port 3002 --host 0.0.0.0" >> "%FRONTEND_LOG%" 2>&1
)

goto monitor
