@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ============================================================
echo   JRVLTSQL Quickstart - JRA Data Fetcher
echo ============================================================
echo.

cd /d "%~dp0.."

REM Try 64-bit Python first, fall back to 32-bit
set PYTHON=python
where python >nul 2>&1
if errorlevel 1 (
    set PYTHON=C:\Users\mitsu\AppData\Local\Programs\Python\Python313\python.exe
)

%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and try again.
    pause
    exit /b 1
)

echo [1/4] Environment check...
%PYTHON% --version
echo.

echo [2/4] Select option:
echo   1. Fetch this week's data   (option=2: 今週データ)
echo   2. Fetch differential data  (option=1: 差分データ)
echo   3. Full setup fetch         (option=4: 分割セットアップ)
echo.
set /p OPT="Select [1-3] (default=1): "
if "%OPT%"=="2" set OPTION=1
if "%OPT%"=="3" set OPTION=4
if not defined OPTION set OPTION=2

echo.
echo [3/4] Fetching JRA data (option=%OPTION%)...
%PYTHON% scripts\quickstart.py --option %OPTION%
if errorlevel 1 (
    echo.
    echo [ERROR] Quickstart failed. Check output above.
    pause
    exit /b 1
)

echo.
echo [4/4] Verifying database...
%PYTHON% scripts\raceday_verify.py --phase pre

echo.
echo ============================================================
echo   Complete! Database is ready.
echo   Run 'python -m src.cli.main status' to check status.
echo ============================================================
pause
