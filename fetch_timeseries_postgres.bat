@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

cd /d "%~dp0"

set "FROM_DATE=%~1"
set "TO_DATE=%~2"

if "%FROM_DATE%"=="" (
    for /f %%i in ('powershell -NoProfile -Command "(Get-Date).AddDays(-365).ToString('yyyyMMdd')"') do set "FROM_DATE=%%i"
)
if "%TO_DATE%"=="" (
    for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd')"') do set "TO_DATE=%%i"
)

echo ============================================================
echo   JRA-VAN Time-Series Odds - PostgreSQL
echo ============================================================
echo.
echo Date range: %FROM_DATE% - %TO_DATE%
echo Specs:      0B30 ^(returns O1-O6 snapshots^)
echo Database:   PostgreSQL ^(config/config.yaml^)
echo.

if not exist "config\config.yaml" (
    echo [ERROR] config\config.yaml not found.
    echo Run quickstart.bat or copy config\config.yaml.example first.
    exit /b 1
)

where jltsql >nul 2>&1
if %errorlevel% equ 0 (
    set "JLTSQL=jltsql"
) else if exist ".venv\Scripts\jltsql.exe" (
    set "JLTSQL=.venv\Scripts\jltsql.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "JLTSQL=.venv\Scripts\python.exe -m src.cli.main"
) else (
    set "JLTSQL=python -m src.cli.main"
)

echo Command: %JLTSQL% realtime odds-timeseries --from %FROM_DATE% --to %TO_DATE% --db postgresql
echo.

%JLTSQL% realtime odds-timeseries --from %FROM_DATE% --to %TO_DATE% --db postgresql
set "SCRIPT_EXIT_CODE=%errorlevel%"

echo.
if not "%SCRIPT_EXIT_CODE%"=="0" (
    echo [ERROR] Time-series odds fetch failed. Exit code: %SCRIPT_EXIT_CODE%
    exit /b %SCRIPT_EXIT_CODE%
)

echo [OK] Time-series odds fetch completed.
exit /b 0
