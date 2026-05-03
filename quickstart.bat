@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title JLTSQL Quickstart

REM Move to batch file directory
cd /d "%~dp0"

echo ============================================================
echo   JLTSQL Quickstart
echo ============================================================
echo.

REM Store exit code for later
set SCRIPT_EXIT_CODE=0
set SKIP_SCHEDULER_FOR_YES=0

if not "%~1"=="" (
    for %%A in (%*) do (
        if /I "%%~A"=="--yes" set "SKIP_SCHEDULER_FOR_YES=1"
        if /I "%%~A"=="-y" set "SKIP_SCHEDULER_FOR_YES=1"
    )
)

REM Prefer repo-local interpreters first so Windows collectors can run
REM without relying on global PATH state.
if exist "%~dp0venv32\Scripts\python.exe" (
    set "PYTHON=%~dp0venv32\Scripts\python.exe"
    goto :run
)

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON=%~dp0.venv\Scripts\python.exe"
    goto :run
)

REM First try: explicit PYTHON environment variable
if defined PYTHON (
    goto :run
)

REM Prefer regular py launcher; JLTSQL now supports bridge-based JRA access
REM and no longer requires a global 32-bit Python install.
py --version >nul 2>&1
if !errorlevel!==0 (
    set "PYTHON=py"
    goto :run
)

REM Fallback: python in PATH
python --version >nul 2>&1
if !errorlevel!==0 (
    set "PYTHON=python"
    goto :run
)

REM No Python found
echo ERROR: Python not found
echo Please install Python 3.10+ or create venv32/.venv in this repository.
echo Download: https://www.python.org/downloads/
pause
exit /b 1

:run
echo Using Python: %PYTHON%
"%PYTHON%" scripts/quickstart.py %*
set SCRIPT_EXIT_CODE=!errorlevel!
goto :check_result

:check_result
echo.
if !SCRIPT_EXIT_CODE! neq 0 (
    echo ============================================================
    echo   Setup Failed (Exit Code: !SCRIPT_EXIT_CODE!)
    echo ============================================================
    echo.
    echo   Please check the error messages above.
    echo   Common issues:
    echo     - Missing config/config.yaml
    echo     - Invalid service key
    echo     - No data available for the specified date range
    echo.
    echo   Press Enter to close...
    set /p dummy=
    endlocal & exit /b 1
)

echo ============================================================
echo   Setup Complete
echo ============================================================
echo.
echo   Database file: data\keiba.db (SQLite)
echo.
echo   To view data:
echo     - Use DB Browser for SQLite
echo     - Python: sqlite3.connect('data/keiba.db')
echo.
call :prompt_sqlite_daily_sync
if !errorlevel! neq 0 (
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    echo.
    echo ============================================================
    echo   Daily Sync Task Registration Failed
    echo ============================================================
    echo.
    echo   Exit Code: !SCRIPT_EXIT_CODE!
    echo.
    echo   Press Enter to close...
    set /p dummy=
    endlocal & exit /b !SCRIPT_EXIT_CODE!
)

echo.
echo   CLI commands:
echo     jltsql status   - Check database status
echo     jltsql fetch    - Fetch additional data
echo     quickstart.bat --yes --include-timeseries - Fill SQLite TS_O1/TS_O2 odds
echo     quickstart_postgres_timeseries.bat  - PostgreSQL setup + TS_O1/TS_O2
echo     jltsql --help   - Other commands
echo.
echo   For Claude Code / Claude Desktop users:
echo     Install MCP Server to access DB directly from AI
echo     https://github.com/miyamamoto/jvlink-mcp-server
echo.
echo   Press Enter to close...
set /p dummy=
endlocal
exit /b 0

:prompt_sqlite_daily_sync
if /I "!JLTSQL_SKIP_SCHEDULER_PROMPT!"=="1" exit /b 0
if "!SKIP_SCHEDULER_FOR_YES!"=="1" exit /b 0

if not exist "%~dp0install_tasks.ps1" (
    echo [INFO] install_tasks.ps1 not found. Daily sync task registration skipped.
    exit /b 0
)

echo.
echo ============================================================
echo   Optional SQLite Daily Sync Task Registration
echo ============================================================
echo.
echo   This registers daily_sync.bat as a Windows scheduled task.
echo   Database: SQLite ^(data\keiba.db^)
echo   Default task: JRVLTSQL_DailySync, daily at 06:30.
echo.
set /p REGISTER_TASK="  Register or update the scheduled task now? [y/N]: "
if /I not "!REGISTER_TASK!"=="y" (
    echo [INFO] Scheduled task registration skipped.
    exit /b 0
)

set "TASK_TIME=06:30"
set /p TASK_TIME_INPUT="  Daily run time HH:mm [06:30]: "
if not "!TASK_TIME_INPUT!"=="" set "TASK_TIME=!TASK_TIME_INPUT!"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_tasks.ps1" -Time "!TASK_TIME!" -DbType sqlite
set "TASK_EXIT_CODE=!errorlevel!"
if not "!TASK_EXIT_CODE!"=="0" (
    echo [ERROR] Scheduled task registration failed. Exit code: !TASK_EXIT_CODE!
    exit /b !TASK_EXIT_CODE!
)

echo [OK] Scheduled task registration completed.
exit /b 0
