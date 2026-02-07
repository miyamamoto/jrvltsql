@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title JLTSQL Setup (Debug)

REM Move to batch file directory
cd /d "%~dp0"

echo ============================================================
echo   JLTSQL Quickstart - Debug Mode
echo ============================================================
echo.
echo Arguments: %*
echo.

REM ============================================================
REM   Python Detection (32-bit preferred for UmaConn/NAR)
REM ============================================================

REM First try: explicit PYTHON environment variable
if defined PYTHON (
    echo Using PYTHON environment variable: %PYTHON%
    "%PYTHON%" scripts/quickstart.py %*
    goto :end
)

REM Second try: py launcher with 32-bit Python 3.12
py -3.12-32 --version >nul 2>&1
if %errorlevel%==0 (
    echo Using: Python 3.12 (32-bit)
    py -3.12-32 scripts/quickstart.py %*
    goto :end
)

REM Third try: py launcher with any 32-bit Python
py -32 --version >nul 2>&1
if %errorlevel%==0 (
    echo Using: Python (32-bit)
    py -32 scripts/quickstart.py %*
    goto :end
)

REM Fourth try: py launcher (any version)
py --version >nul 2>&1
if %errorlevel%==0 (
    echo Using: Python (py launcher)
    echo [WARNING] 64-bit Python may not support NAR/UmaConn
    py scripts/quickstart.py %*
    goto :end
)

REM Fifth try: python in PATH
python --version >nul 2>&1
if %errorlevel%==0 (
    echo Using: Python (PATH)
    echo [WARNING] 64-bit Python may not support NAR/UmaConn
    python scripts/quickstart.py %*
    goto :end
)

REM No Python found
echo ERROR: Python not found
echo Please install Python 3.12 (32-bit) for full NAR/UmaConn support
echo Download: https://www.python.org/downloads/
pause
exit /b 1

:end
echo.
echo ============================================================
echo   Exit code: %errorlevel%
echo ============================================================
echo.
echo   If an error occurred, check the traceback above.
echo.
pause
