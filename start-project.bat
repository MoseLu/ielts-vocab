@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

pushd "%ROOT%" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Cannot enter project directory: %ROOT%
  exit /b 1
)

set "FRONTEND_PORT=3002"
set "BACKEND_PORT=5000"
set "LOG_DIR=%ROOT%\logs\runtime"
set "FRONTEND_OUT=%LOG_DIR%\frontend-preview.out.log"
set "FRONTEND_ERR=%LOG_DIR%\frontend-preview.err.log"
set "BACKEND_OUT=%LOG_DIR%\backend.out.log"
set "BACKEND_ERR=%LOG_DIR%\backend.err.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

echo [1/5] Checking running project instances...
call :inspect_port %BACKEND_PORT%
if /I not "%PORT_STATUS%"=="FREE" (
  echo [ERROR] Port %BACKEND_PORT% is already in use.
  echo         Stop the existing backend or any process on this port before starting.
  call :print_process_hint
  goto :fail
)

call :inspect_port %FRONTEND_PORT%
if /I not "%PORT_STATUS%"=="FREE" (
  echo [ERROR] Port %FRONTEND_PORT% is already in use.
  echo         Stop the existing frontend preview or any process on this port before starting.
  call :print_process_hint
  goto :fail
)

echo [2/5] Checking required commands and files...
call :require_command git
if errorlevel 1 goto :fail
call :require_command npm
if errorlevel 1 goto :fail
call :require_command python
if errorlevel 1 goto :fail

if not exist "%ROOT%\package.json" (
  echo [ERROR] package.json was not found in the project root.
  goto :fail
)

if not exist "%ROOT%\backend\app.py" (
  echo [ERROR] backend\app.py was not found.
  goto :fail
)

if not exist "%ROOT%\backend\.env" (
  echo [ERROR] backend\.env was not found.
  echo         Flask configuration is incomplete.
  goto :fail
)

echo [3/5] Ensuring the working tree is up to date...
for /f "delims=" %%I in ('git rev-parse --is-inside-work-tree 2^>nul') do set "IS_GIT_REPO=%%I"
if /I not "%IS_GIT_REPO%"=="true" (
  echo [ERROR] The current directory is not a Git repository.
  goto :fail
)

git update-index -q --refresh >nul 2>&1
for /f "delims=" %%I in ('git status --porcelain --untracked-files=all') do (
  echo [ERROR] The working tree is not clean.
  echo         Commit, stash, or remove local changes before starting.
  goto :fail
)

echo         Fetching latest remote refs...
git fetch --prune origin
if errorlevel 1 (
  echo [ERROR] git fetch origin failed.
  echo         Cannot confirm the latest remote code.
  goto :fail
)

for /f "delims=" %%I in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "CURRENT_BRANCH=%%I"
for /f "delims=" %%I in ('git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2^>nul') do set "UPSTREAM_BRANCH=%%I"
if not defined UPSTREAM_BRANCH (
  echo [ERROR] Branch %CURRENT_BRANCH% has no upstream branch configured.
  goto :fail
)

set "AHEAD=0"
set "BEHIND=0"
for /f "tokens=1,2" %%A in ('git rev-list --left-right --count HEAD...%UPSTREAM_BRANCH%') do (
  set "AHEAD=%%A"
  set "BEHIND=%%B"
)

if not "%BEHIND%"=="0" (
  if "%AHEAD%"=="0" (
    echo         Local branch is behind %UPSTREAM_BRANCH% by %BEHIND% commit(s).
    echo         Attempting fast-forward pull...
    git pull --ff-only
    if errorlevel 1 (
      echo [ERROR] Fast-forward pull failed.
      echo         Sync the branch manually before starting.
      goto :fail
    )
  ) else (
    echo [ERROR] The current branch has diverged from %UPSTREAM_BRANCH%.
    echo         Local ahead: %AHEAD%  Remote ahead: %BEHIND%
    echo         Resolve the divergence manually before starting.
    goto :fail
  )
)

if not "%AHEAD%"=="0" if "%BEHIND%"=="0" (
  echo [INFO] Local branch is ahead of %UPSTREAM_BRANCH% by %AHEAD% commit(s).
  echo        Startup will use the current local HEAD.
)

echo [4/5] Building frontend preview assets...
call npm run build
if errorlevel 1 (
  echo [ERROR] Frontend build failed.
  echo         No services were started.
  goto :fail
)

echo.>> "%BACKEND_OUT%"
echo ===== [%date% %time%] backend start =====>> "%BACKEND_OUT%"
echo.>> "%BACKEND_ERR%"
echo ===== [%date% %time%] backend start =====>> "%BACKEND_ERR%"
echo.>> "%FRONTEND_OUT%"
echo ===== [%date% %time%] frontend preview start =====>> "%FRONTEND_OUT%"
echo.>> "%FRONTEND_ERR%"
echo ===== [%date% %time%] frontend preview start =====>> "%FRONTEND_ERR%"

echo [5/5] Starting Flask backend and frontend preview...
start "IELTS Flask Backend" cmd /c "cd /d ""%ROOT%\backend"" && python -u app.py 1>>""%BACKEND_OUT%"" 2>>""%BACKEND_ERR%"""
call :wait_for_port %BACKEND_PORT% 30
if errorlevel 1 (
  echo [ERROR] Flask backend did not start listening on port %BACKEND_PORT% within 30 seconds.
  echo         Check the log: %BACKEND_ERR%
  goto :fail
)

start "IELTS Frontend Preview" cmd /c "cd /d ""%ROOT%"" && npm run preview -- --host 0.0.0.0 --port %FRONTEND_PORT% 1>>""%FRONTEND_OUT%"" 2>>""%FRONTEND_ERR%"""
call :wait_for_port %FRONTEND_PORT% 30
if errorlevel 1 (
  echo [ERROR] Frontend preview did not start listening on port %FRONTEND_PORT% within 30 seconds.
  echo         Check the log: %FRONTEND_ERR%
  goto :fail
)

echo [DONE] Project started successfully.
echo        Frontend preview: http://127.0.0.1:%FRONTEND_PORT%
echo        Flask backend:    http://127.0.0.1:%BACKEND_PORT%
echo        Logs directory:   %LOG_DIR%
goto :success

:require_command
where %~1 >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Required command not found: %~1
  exit /b 1
)
exit /b 0

:inspect_port
set "PORT_STATUS=FREE"
set "PORT_PID="
set "PORT_PROCESS="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$port = %~1; " ^
  "$conn = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1; " ^
  "if (-not $conn) { 'STATE=FREE'; exit 0 } " ^
  "$owningPid = $conn.OwningProcess; " ^
  "$name = ''; try { $name = (Get-Process -Id $owningPid -ErrorAction Stop).ProcessName } catch {} " ^
  "'STATE=OCCUPIED'; " ^
  "'PID=' + $owningPid; " ^
  "'PROC=' + $name"`) do (
  for /f "tokens=1,* delims==" %%A in ("%%I") do (
    if /I "%%A"=="STATE" set "PORT_STATUS=%%B"
    if /I "%%A"=="PID" set "PORT_PID=%%B"
    if /I "%%A"=="PROC" set "PORT_PROCESS=%%B"
  )
)
exit /b 0

:print_process_hint
if defined PORT_PID echo         PID=%PORT_PID%
if defined PORT_PROCESS echo         Process=%PORT_PROCESS%
exit /b 0

:wait_for_port
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$deadline = (Get-Date).AddSeconds(%~2); " ^
  "while ((Get-Date) -lt $deadline) { " ^
  "  if (Get-NetTCPConnection -State Listen -LocalPort %~1 -ErrorAction SilentlyContinue | Select-Object -First 1) { exit 0 } " ^
  "  Start-Sleep -Milliseconds 500 " ^
  "} " ^
  "exit 1"
exit /b %ERRORLEVEL%

:fail
popd >nul
exit /b 1

:success
popd >nul
exit /b 0
