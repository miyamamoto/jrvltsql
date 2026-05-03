@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title JLTSQL Daily Sync

cd /d "%~dp0"

set "DB_TYPE=postgresql"
set "DAYS_BACK=7"
set "DAYS_FORWARD=3"
set "ENSURE_TABLES=0"

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

if defined PYTHON (
    "%PYTHON%" scripts/quickstart.py --mode update --yes %DB_ARGS% --from-date "%FROM_DATE%" --to-date "%TO_DATE%"
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

if exist "%~dp0venv32\Scripts\python.exe" (
    "%~dp0venv32\Scripts\python.exe" scripts/quickstart.py --mode update --yes %DB_ARGS% --from-date "%FROM_DATE%" --to-date "%TO_DATE%"
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" scripts/quickstart.py --mode update --yes %DB_ARGS% --from-date "%FROM_DATE%" --to-date "%TO_DATE%"
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

py -3.12-32 --version >nul 2>&1
if !errorlevel!==0 (
    py -3.12-32 scripts/quickstart.py --mode update --yes %DB_ARGS% --from-date "%FROM_DATE%" --to-date "%TO_DATE%"
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

py --version >nul 2>&1
if !errorlevel!==0 (
    py scripts/quickstart.py --mode update --yes %DB_ARGS% --from-date "%FROM_DATE%" --to-date "%TO_DATE%"
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

python --version >nul 2>&1
if !errorlevel!==0 (
    python scripts/quickstart.py --mode update --yes %DB_ARGS% --from-date "%FROM_DATE%" --to-date "%TO_DATE%"
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
