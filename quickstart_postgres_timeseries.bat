@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title JLTSQL PostgreSQL Time-Series Quickstart

cd /d "%~dp0"

set "FROM_DATE=%~1"
set "TO_DATE=%~2"

if "%FROM_DATE%"=="" (
    for /f %%i in ('powershell -NoProfile -Command "(Get-Date).AddDays(-365).ToString('yyyyMMdd')"') do set "FROM_DATE=%%i"
)
if "%TO_DATE%"=="" (
    for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd')"') do set "TO_DATE=%%i"
)

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
    echo [ERROR] POSTGRES_PASSWORD is required.
    echo Set it before running this batch.
    exit /b 1
)

echo ============================================================
echo   JLTSQL PostgreSQL Time-Series Quickstart
echo ============================================================
echo.
echo PostgreSQL: %POSTGRES_USER%@%POSTGRES_HOST%:%POSTGRES_PORT%/%POSTGRES_DATABASE%
echo Date range: %FROM_DATE% - %TO_DATE%
echo Includes:   RACE data + official TS_O1/TS_O2 time-series odds
echo.

set "SCRIPT_EXIT_CODE=0"

if defined PYTHON (
    echo Using PYTHON environment variable: %PYTHON%
    "%PYTHON%" scripts/quickstart.py --mode update --yes --db-type postgresql --pg-host "%POSTGRES_HOST%" --pg-port "%POSTGRES_PORT%" --pg-database "%POSTGRES_DATABASE%" --pg-user "%POSTGRES_USER%" --pg-password "%POSTGRES_PASSWORD%" --from-date "%FROM_DATE%" --to-date "%TO_DATE%" --include-timeseries --timeseries-from-date "%FROM_DATE%" --timeseries-to-date "%TO_DATE%"
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

py -3.12-32 --version >nul 2>&1
if !errorlevel!==0 (
    echo Using: Python 3.12 ^(32-bit^)
    py -3.12-32 scripts/quickstart.py --mode update --yes --db-type postgresql --pg-host "%POSTGRES_HOST%" --pg-port "%POSTGRES_PORT%" --pg-database "%POSTGRES_DATABASE%" --pg-user "%POSTGRES_USER%" --pg-password "%POSTGRES_PASSWORD%" --from-date "%FROM_DATE%" --to-date "%TO_DATE%" --include-timeseries --timeseries-from-date "%FROM_DATE%" --timeseries-to-date "%TO_DATE%"
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

py -32 --version >nul 2>&1
if !errorlevel!==0 (
    echo Using: Python ^(32-bit^)
    py -32 scripts/quickstart.py --mode update --yes --db-type postgresql --pg-host "%POSTGRES_HOST%" --pg-port "%POSTGRES_PORT%" --pg-database "%POSTGRES_DATABASE%" --pg-user "%POSTGRES_USER%" --pg-password "%POSTGRES_PASSWORD%" --from-date "%FROM_DATE%" --to-date "%TO_DATE%" --include-timeseries --timeseries-from-date "%FROM_DATE%" --timeseries-to-date "%TO_DATE%"
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

python --version >nul 2>&1
if !errorlevel!==0 (
    echo Using: Python ^(PATH^)
    echo [WARNING] 64-bit Python may not support JV-Link COM API
    python scripts/quickstart.py --mode update --yes --db-type postgresql --pg-host "%POSTGRES_HOST%" --pg-port "%POSTGRES_PORT%" --pg-database "%POSTGRES_DATABASE%" --pg-user "%POSTGRES_USER%" --pg-password "%POSTGRES_PASSWORD%" --from-date "%FROM_DATE%" --to-date "%TO_DATE%" --include-timeseries --timeseries-from-date "%FROM_DATE%" --timeseries-to-date "%TO_DATE%"
    set "SCRIPT_EXIT_CODE=!errorlevel!"
    goto :check_result
)

echo ERROR: Python not found
echo Please install Python 3.12 (32-bit) for JV-Link COM API support.
exit /b 1

:check_result
echo.
if not "%SCRIPT_EXIT_CODE%"=="0" (
    echo [ERROR] PostgreSQL time-series quickstart failed. Exit code: %SCRIPT_EXIT_CODE%
    exit /b %SCRIPT_EXIT_CODE%
)

echo [OK] PostgreSQL time-series quickstart completed.
exit /b 0
