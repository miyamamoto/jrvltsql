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
echo   CLI commands:
echo     jltsql status   - Check database status
echo     jltsql fetch    - Fetch additional data
echo     fetch_timeseries_postgres.bat       - Fill TS_O1/TS_O2 historical odds
echo     quickstart_postgres_timeseries.bat  - PostgreSQL setup + TS odds
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
