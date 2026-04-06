@echo off
REM E2E Test Runner for IELTS Vocabulary App

echo ========================================
echo IELTS Vocabulary E2E Test Runner
echo ========================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Node.js is not installed
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check if pnpm is installed
where pnpm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: pnpm is not installed
    echo Please install pnpm or enable Corepack first
    pause
    exit /b 1
)

REM Check if Playwright is installed
if not exist "node_modules\.bin\playwright.cmd" (
    echo Installing frontend dependencies...
    call pnpm install
    if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
)

if not exist "node_modules\.bin\playwright.cmd" (
    echo Error: Playwright CLI is still unavailable after pnpm install
    pause
    exit /b 1
)

echo Ensuring Playwright browser is installed...
call pnpm exec playwright install chromium
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
)

echo.
echo Choose an option:
echo 1. Run all E2E tests
echo 2. Run specific test file
echo 3. Run tests in headed mode (show browser)
echo 4. Run tests with UI
echo 5. Run tests in debug mode
echo 6. View test report
echo 7. Install Playwright browsers
echo 8. Exit
echo.

set /p choice="Enter your choice (1-8): "

if "%choice%"=="1" goto run_all
if "%choice%"=="2" goto run_specific
if "%choice%"=="3" goto run_headed
if "%choice%"=="4" goto run_ui
if "%choice%"=="5" goto run_debug
if "%choice%"=="6" goto view_report
if "%choice%"=="7" goto install_playwright
if "%choice%"=="8" goto end

echo Invalid choice
pause
goto end

:run_all
echo.
echo Running all E2E tests...
call pnpm exec playwright test
goto end

:run_specific
echo.
set /p testfile="Enter test file name (e.g., auth.spec.ts): "
echo Running %testfile%...
call pnpm exec playwright test %testfile%
goto end

:run_headed
echo.
echo Running tests in headed mode...
call pnpm exec playwright test --headed
goto end

:run_ui
echo.
echo Running tests with UI...
call pnpm exec playwright test --ui
goto end

:run_debug
echo.
echo Running tests in debug mode...
call pnpm exec playwright test --debug
goto end

:view_report
echo.
echo Opening test report...
call pnpm exec playwright show-report
goto end

:install_playwright
echo.
echo Installing Playwright browsers...
call pnpm exec playwright install --with-deps chromium
echo.
echo Installation complete!
goto end

:end
echo.
echo Done!
pause
