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
echo Specs:      0B41,0B42 ^(official 1-year O1/O2 time-series^)
echo Database:   PostgreSQL ^(config/config.yaml^)
echo.

if not exist "config\config.yaml" (
    echo [ERROR] config\config.yaml not found.
    echo Run quickstart.bat or copy config\config.yaml.example first.
    exit /b 1
)

REM JLTSQL is an explicit operator override for a separately validated SDK
REM environment. This script deliberately does not discover jltsql from PATH.
if defined PYTHON (
    if not exist "%PYTHON%" (
        echo [ERROR] PYTHON must be a full path to python.exe.
        exit /b 1
    )
    "%PYTHON%" -c "import sys; raise SystemExit(sys.version_info < (3, 12))" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] PYTHON must point to Python 3.12 or later.
        exit /b 1
    )
    set "JLTSQL="!PYTHON!" -m src.cli.main"
)
if not defined JLTSQL if defined VIRTUAL_ENV (
    if not exist "%VIRTUAL_ENV%\Scripts\python.exe" (
        echo [ERROR] VIRTUAL_ENV must point to Python 3.12 or later.
        exit /b 1
    )
    "%VIRTUAL_ENV%\Scripts\python.exe" -c "import struct,sys; raise SystemExit(sys.version_info < (3, 12) or struct.calcsize('P') != 4)" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] VIRTUAL_ENV must point to 32-bit Python 3.12 or later.
        exit /b 1
    )
    set "JLTSQL="!VIRTUAL_ENV!\Scripts\python.exe" -m src.cli.main"
)
if not defined JLTSQL if exist "venv32\Scripts\python.exe" (
    "venv32\Scripts\python.exe" -c "import struct,sys; raise SystemExit(sys.version_info < (3, 12) or struct.calcsize('P') != 4)" >nul 2>&1
    if !errorlevel!==0 set "JLTSQL=venv32\Scripts\python.exe -m src.cli.main"
)
if not defined JLTSQL if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import struct,sys; raise SystemExit(sys.version_info < (3, 12) or struct.calcsize('P') != 4)" >nul 2>&1
    if !errorlevel!==0 set "JLTSQL=.venv\Scripts\python.exe -m src.cli.main"
)
if not defined JLTSQL (
    py -3.12-32 --version >nul 2>&1
    if !errorlevel!==0 set "JLTSQL=py -3.12-32 -m src.cli.main"
)
if not defined JLTSQL (
    echo [ERROR] 32-bit Python was not found. For a separately validated SDK,
    echo         set JLTSQL to a fully quoted executable command explicitly.
    exit /b 1
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
