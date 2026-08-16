@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ============================================================
echo   JRVLTSQL Quickstart - JRA Data Fetcher
echo ============================================================
echo.

cd /d "%~dp0.."

REM Automatic discovery keeps the release-validated 32-bit path first.
set "PYTHON_CMD="
if defined PYTHON (
    if not exist "%PYTHON%" (
        echo [ERROR] PYTHON must be a full path to python.exe.
        exit /b 1
    )
    "%PYTHON%" -c "import sys; raise SystemExit(sys.version_info ^< (3, 12))" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] PYTHON must point to Python 3.12 or later.
        exit /b 1
    )
    set "PYTHON_CMD="!PYTHON!""
)
if not defined PYTHON_CMD if defined VIRTUAL_ENV if exist "%VIRTUAL_ENV%\Scripts\python.exe" set "PYTHON_CMD="!VIRTUAL_ENV!\Scripts\python.exe""
if not defined PYTHON_CMD if exist "%~dp0..\venv32\Scripts\python.exe" set "PYTHON_CMD="%~dp0..\venv32\Scripts\python.exe""
if not defined PYTHON_CMD if exist "%~dp0..\.venv\Scripts\python.exe" set "PYTHON_CMD="%~dp0..\.venv\Scripts\python.exe""
if not defined PYTHON_CMD (
    py -3.12-32 --version >nul 2>&1
    if !errorlevel!==0 set "PYTHON_CMD=py -3.12-32"
)
if not defined PYTHON_CMD (
    py -3.12 --version >nul 2>&1
    if !errorlevel!==0 set "PYTHON_CMD=py -3.12"
)
if not defined PYTHON_CMD (
    py -3 --version >nul 2>&1
    if !errorlevel!==0 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    python --version >nul 2>&1
    if !errorlevel!==0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo [ERROR] Python not found. Install Python 3.12+ and try again.
    pause
    exit /b 1
)

echo [1/5] Environment check...
%PYTHON_CMD% --version
echo.

REM ============================================================
REM Step 2: S3 cache pre-download (speeds up setup if cache exists)
REM ============================================================
echo [2/5] Cache check...
if exist "config\s3_credentials.enc" (
    echo   S3 credentials found: config\s3_credentials.enc
    echo   Downloading cache from S3 before fetch saves time by reusing cached records.
    echo.
    set /p DOWNLOAD_S3="  Download cache from S3 now? [Y/n]: "
    if /i not "!DOWNLOAD_S3!"=="n" (
        echo   Syncing cache from S3 (S3 -> local)...
        %PYTHON_CMD% -m src.cli.main cache sync --download
        if errorlevel 1 (
            echo   [WARN] S3 download failed or skipped. Continuing with JV-Link fetch.
        )
    )
) else (
    echo   No S3 credentials configured (optional).
    echo   To enable S3 cache sync, run: jltsql cache s3-setup
)
echo.

REM ============================================================
REM Step 3: Select fetch mode
REM ============================================================
echo [3/5] Select fetch mode:
echo   1. This week's data   (今週データ:    fast, recent races only)
echo   2. Differential data  (差分データ:    recent changes since last fetch)
echo   3. Full setup         (フルセットアップ: all historical data - slow)
echo.
set /p OPT="Select [1-3] (default=1): "
if "%OPT%"=="2" (
    set MODE=simple
    set MODE_LABEL=差分データ
) else if "%OPT%"=="3" (
    set MODE=full
    set MODE_LABEL=フルセットアップ
) else (
    set MODE=update
    set MODE_LABEL=今週データ
)

echo.
echo [4/5] Fetching JRA data (mode=%MODE_LABEL%)...
%PYTHON_CMD% scripts\quickstart.py --mode %MODE% --yes
if errorlevel 1 (
    echo.
    echo [ERROR] Fetch failed. Check output above.
    pause
    exit /b 1
)

REM ============================================================
REM Step 4b: Show cache info
REM ============================================================
echo.
echo   Local cache status:
%PYTHON_CMD% -m src.cli.main cache info
echo.

REM ============================================================
REM Step 4c: S3 cache upload after fetch
REM ============================================================
if exist "config\s3_credentials.enc" (
    set /p UPLOAD_S3="  Upload updated cache to S3? [Y/n]: "
    if /i not "!UPLOAD_S3!"=="n" (
        echo   Uploading cache to S3 (local -> S3)...
        %PYTHON_CMD% -m src.cli.main cache sync --upload
        if errorlevel 1 (
            echo   [WARN] S3 upload failed. Cache remains local.
        )
    )
)

REM ============================================================
REM Step 5: Verify database
REM ============================================================
echo.
echo [5/5] Verifying database...
%PYTHON_CMD% scripts\raceday_verify.py --phase pre

echo.
echo ============================================================
echo   Complete! Database is ready.
echo.
echo   Useful commands:
echo     jltsql status               -- check DB status
echo     jltsql cache info           -- show cache statistics
echo     jltsql cache sync           -- sync cache with S3
echo     jltsql realtime start ...   -- start realtime monitoring
echo ============================================================
pause
