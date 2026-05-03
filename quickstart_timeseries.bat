@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title JLTSQL Time-Series Quickstart

cd /d "%~dp0"

set "DB_TYPE=sqlite"
set "FROM_DATE="
set "TO_DATE="

:parse_args
if "%~1"=="" goto :parsed
if /I "%~1"=="--db" (
    set "DB_TYPE=%~2"
    shift
    shift
    goto :parse_args
)
if /I "%~1"=="--from" (
    set "FROM_DATE=%~2"
    shift
    shift
    goto :parse_args
)
if /I "%~1"=="--from-date" (
    set "FROM_DATE=%~2"
    shift
    shift
    goto :parse_args
)
if /I "%~1"=="--to" (
    set "TO_DATE=%~2"
    shift
    shift
    goto :parse_args
)
if /I "%~1"=="--to-date" (
    set "TO_DATE=%~2"
    shift
    shift
    goto :parse_args
)

REM Positional compatibility: quickstart_timeseries.bat 20250426 20260412
if "%FROM_DATE%"=="" (
    set "FROM_DATE=%~1"
    shift
    goto :parse_args
)
if "%TO_DATE%"=="" (
    set "TO_DATE=%~1"
    shift
    goto :parse_args
)

echo [WARN] Unknown argument ignored: %~1
shift
goto :parse_args

:parsed
if /I not "%DB_TYPE%"=="sqlite" if /I not "%DB_TYPE%"=="postgresql" (
    echo [ERROR] --db must be sqlite or postgresql.
    exit /b 1
)

if "%FROM_DATE%"=="" (
    for /f %%i in ('powershell -NoProfile -Command "(Get-Date).AddDays(-365).ToString('yyyyMMdd')"') do set "FROM_DATE=%%i"
)
if "%TO_DATE%"=="" (
    for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd')"') do set "TO_DATE=%%i"
)

if /I "%DB_TYPE%"=="postgresql" (
    if "%POSTGRES_HOST%"=="" set "POSTGRES_HOST=127.0.0.1"
    if "%POSTGRES_PORT%"=="" set "POSTGRES_PORT=5432"
    if "%POSTGRES_DATABASE%"=="" (
        if "%POSTGRES_DB%"=="" (
            set "POSTGRES_DATABASE=keiba_dev"
        ) else (
            set "POSTGRES_DATABASE=%POSTGRES_DB%"
        )
    )
    if "%POSTGRES_USER%"=="" set "POSTGRES_USER=ingestion_writer"
    if "%POSTGRES_PASSWORD%"=="" (
        echo [ERROR] POSTGRES_PASSWORD is required for PostgreSQL.
        echo Set it before running this batch.
        exit /b 1
    )
)

echo ============================================================
echo   JLTSQL Time-Series Quickstart
echo ============================================================
echo.
echo DB type:            %DB_TYPE%
if /I "%DB_TYPE%"=="postgresql" echo PostgreSQL:         %POSTGRES_USER%@%POSTGRES_HOST%:%POSTGRES_PORT%/%POSTGRES_DATABASE%
echo Normal data range:  %FROM_DATE% - %TO_DATE%
echo Time-series range:  %FROM_DATE% - %TO_DATE%
echo Includes:           normal data + official TS_O1/TS_O2 odds
echo.

set "PYTHON_CMD="
if defined PYTHON set "PYTHON_CMD=%PYTHON%"
if not defined PYTHON_CMD if exist "%~dp0venv32\Scripts\python.exe" set "PYTHON_CMD="%~dp0venv32\Scripts\python.exe""
if not defined PYTHON_CMD if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON_CMD="%~dp0.venv\Scripts\python.exe""
if not defined PYTHON_CMD (
    py -3.12-32 --version >nul 2>&1
    if !errorlevel!==0 set "PYTHON_CMD=py -3.12-32"
)
if not defined PYTHON_CMD (
    py -32 --version >nul 2>&1
    if !errorlevel!==0 set "PYTHON_CMD=py -32"
)
if not defined PYTHON_CMD (
    py --version >nul 2>&1
    if !errorlevel!==0 set "PYTHON_CMD=py"
)
if not defined PYTHON_CMD (
    python --version >nul 2>&1
    if !errorlevel!==0 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    echo [ERROR] Python not found.
    echo Please install Python 3.10+ or create venv32/.venv in this repository.
    exit /b 1
)

echo Using Python: %PYTHON_CMD%
echo.

if /I "%DB_TYPE%"=="postgresql" (
    %PYTHON_CMD% scripts/quickstart.py --mode update --yes --db-type postgresql --pg-host "%POSTGRES_HOST%" --pg-port "%POSTGRES_PORT%" --pg-database "%POSTGRES_DATABASE%" --pg-user "%POSTGRES_USER%" --pg-password "%POSTGRES_PASSWORD%" --from-date "%FROM_DATE%" --to-date "%TO_DATE%" --include-timeseries --timeseries-from-date "%FROM_DATE%" --timeseries-to-date "%TO_DATE%"
) else (
    %PYTHON_CMD% scripts/quickstart.py --mode update --yes --db-type sqlite --from-date "%FROM_DATE%" --to-date "%TO_DATE%" --include-timeseries --timeseries-from-date "%FROM_DATE%" --timeseries-to-date "%TO_DATE%"
)
set "SCRIPT_EXIT_CODE=%errorlevel%"

echo.
if not "%SCRIPT_EXIT_CODE%"=="0" (
    echo [ERROR] Time-series quickstart failed. Exit code: %SCRIPT_EXIT_CODE%
    exit /b %SCRIPT_EXIT_CODE%
)

echo [OK] Time-series quickstart completed.
call :prompt_scheduler
if !errorlevel! neq 0 exit /b !errorlevel!
exit /b 0

:prompt_scheduler
if /I "!JLTSQL_SKIP_SCHEDULER_PROMPT!"=="1" exit /b 0

if not exist "%~dp0install_tasks.ps1" (
    echo [INFO] install_tasks.ps1 not found. Daily sync task registration skipped.
    exit /b 0
)

echo.
echo ============================================================
echo   Optional Windows Task Scheduler Registration
echo ============================================================
echo.
echo   This registers daily_sync.bat as a Windows scheduled task.
echo   Database: %DB_TYPE%
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

set "PERSIST_ENV_ARG="
if /I "%DB_TYPE%"=="postgresql" (
    echo.
    echo   PostgreSQL scheduled tasks need persistent POSTGRES_* environment variables.
    echo   Saving them stores the current connection values in your Windows user environment.
    echo.
    set /p SAVE_PG_ENV="  Save current POSTGRES_* values for the scheduled task? [y/N]: "
    if /I "!SAVE_PG_ENV!"=="y" set "PERSIST_ENV_ARG=-PersistPostgresEnvironment"
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_tasks.ps1" -Time "!TASK_TIME!" -DbType "%DB_TYPE%" !PERSIST_ENV_ARG!
set "TASK_EXIT_CODE=!errorlevel!"
if not "!TASK_EXIT_CODE!"=="0" (
    echo [ERROR] Scheduled task registration failed. Exit code: !TASK_EXIT_CODE!
    exit /b !TASK_EXIT_CODE!
)

echo [OK] Scheduled task registration completed.
exit /b 0
