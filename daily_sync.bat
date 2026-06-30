@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title JLTSQL Daily Sync

cd /d "%~dp0"

set "DB_TYPE=postgresql"
set "DAYS_BACK=7"
set "DAYS_FORWARD=3"
set "ENSURE_TABLES=1"
set "INCLUDE_TIMESERIES=1"
set "INCLUDE_REALTIME=1"

:parse_args
if "%~1"=="" goto :parsed
if /I "%~1"=="--db" (
    set "DB_TYPE=%~2"
    shift
    shift
    goto :parse_args
)
if /I "%~1"=="--days-back" (
    set "DAYS_BACK=%~2"
    shift
    shift
    goto :parse_args
)
if /I "%~1"=="--days-forward" (
    set "DAYS_FORWARD=%~2"
    shift
    shift
    goto :parse_args
)
if /I "%~1"=="--ensure-tables" (
    set "ENSURE_TABLES=1"
    shift
    goto :parse_args
)
if /I "%~1"=="--no-ensure-tables" (
    set "ENSURE_TABLES=0"
    shift
    goto :parse_args
)
if /I "%~1"=="--no-timeseries" (
    set "INCLUDE_TIMESERIES=0"
    shift
    goto :parse_args
)
if /I "%~1"=="--no-realtime" (
    set "INCLUDE_REALTIME=0"
    shift
    goto :parse_args
)
echo [WARN] Unknown argument ignored: %~1
shift
goto :parse_args

:parsed
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).AddDays(-%DAYS_BACK%).ToString('yyyyMMdd')"') do set "FROM_DATE=%%i"
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).AddDays(%DAYS_FORWARD%).ToString('yyyyMMdd')"') do set "TO_DATE=%%i"

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

echo ============================================================
echo   JLTSQL Daily Sync
echo ============================================================
echo Date range: %FROM_DATE% - %TO_DATE%
echo DB type:    %DB_TYPE%
echo.

if /I "%DB_TYPE%"=="postgresql" (
    if "%POSTGRES_PASSWORD%"=="" (
        echo [ERROR] POSTGRES_PASSWORD is required for PostgreSQL sync.
        exit /b 1
    )
    set "DB_ARGS=--db-type postgresql --pg-host %POSTGRES_HOST% --pg-port %POSTGRES_PORT% --pg-database %POSTGRES_DATABASE% --pg-user %POSTGRES_USER% --pg-password %POSTGRES_PASSWORD%"
) else (
    set "DB_ARGS=--db-type sqlite"
)

set "EXTRA_ARGS="
if "%INCLUDE_TIMESERIES%"=="1" set "EXTRA_ARGS=!EXTRA_ARGS! --include-timeseries --timeseries-from-date %FROM_DATE% --timeseries-to-date %TO_DATE%"
if "%INCLUDE_REALTIME%"=="1" set "EXTRA_ARGS=!EXTRA_ARGS! --include-realtime"

set "SYNC_SCRIPT=scripts/quickstart.py"
set "SYNC_ARGS=--mode update --yes %DB_ARGS% --from-date %FROM_DATE% --to-date %TO_DATE% !EXTRA_ARGS!"
if "%INCLUDE_TIMESERIES%"=="0" if "%INCLUDE_REALTIME%"=="0" (
    rem Task Scheduler production path: avoid quickstart's rich progress UI and
    rem use the non-interactive daily updater. 0B12/0B15 are speed-report
    rem specs (JVRTOpen, idempotent INSERT OR REPLACE into RT_* tables).
    if not defined JRA_DAILY_UPDATE_SPECS set "JRA_DAILY_UPDATE_SPECS=RACE,DIFN,SLOP,WOOD,0B12,0B15"
    set "SYNC_SCRIPT=scripts/daily_update.py"
    set "SYNC_ARGS=--days-back %DAYS_BACK% --days-forward %DAYS_FORWARD% --db %DB_TYPE% --specs !JRA_DAILY_UPDATE_SPECS! --force-incremental --ignore-jvopen-error-codes -303"
    if "%ENSURE_TABLES%"=="0" set "SYNC_ARGS=!SYNC_ARGS! --no-ensure-tables"
)

if defined PYTHON (
    "%PYTHON%" %SYNC_SCRIPT% !SYNC_ARGS!
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

if exist "%~dp0venv32\Scripts\python.exe" (
    "%~dp0venv32\Scripts\python.exe" %SYNC_SCRIPT% !SYNC_ARGS!
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" %SYNC_SCRIPT% !SYNC_ARGS!
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

py -3.12-32 --version >nul 2>&1
if !errorlevel!==0 (
    py -3.12-32 %SYNC_SCRIPT% !SYNC_ARGS!
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

py --version >nul 2>&1
if !errorlevel!==0 (
    py %SYNC_SCRIPT% !SYNC_ARGS!
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

python --version >nul 2>&1
if !errorlevel!==0 (
    python %SYNC_SCRIPT% !SYNC_ARGS!
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

echo [ERROR] Python not found.
exit /b 1

:check_result
if not "%SCRIPT_EXIT_CODE%"=="0" (
    echo [ERROR] Daily sync failed. Exit code: %SCRIPT_EXIT_CODE%
    exit /b %SCRIPT_EXIT_CODE%
)

echo [OK] Daily sync completed.
exit /b 0
