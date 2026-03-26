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

REM Check if Playwright is installed
if not exist "node_modules\.bin\playwright.cmd" (
    echo Installing Playwright...
    call npx playwright install chromium
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
call npx playwright test
goto end

:run_specific
echo.
set /p testfile="Enter test file name (e.g., auth.spec.ts): "
echo Running %testfile%...
call npx playwright test %testfile%
goto end

:run_headed
echo.
echo Running tests in headed mode...
call npx playwright test --headed
goto end

:run_ui
echo.
echo Running tests with UI...
call npx playwright test --ui
goto end

:run_debug
echo.
echo Running tests in debug mode...
call npx playwright test --debug
goto end

:view_report
echo.
echo Opening test report...
call npx playwright show-report
goto end

:install_playwright
echo.
echo Installing Playwright browsers...
call npx playwright install --with-deps chromium
echo.
echo Installation complete!
goto end

:end
echo.
echo Done!
pause
