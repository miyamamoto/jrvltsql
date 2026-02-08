@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title JLTSQL Installer

echo.
echo   ============================================
echo     JLTSQL Installer
echo     JRA-VAN DataLab / UmaConn -^> SQL
echo   ============================================
echo.

set "INSTALL_DIR=%USERPROFILE%\jrvltsql"
set "REPO_URL=https://github.com/miyamamoto/jrvltsql.git"
set "VENV_DIR=%INSTALL_DIR%\venv32"
set "PYTHON32="
set "PYTHON_CMD="

REM === Step 1: Find 32-bit Python 3.12 ===
echo   Step 1/7: Checking 32-bit Python 3.12...

REM Try py launcher
py -3.12-32 --version >nul 2>&1
if !errorlevel!==0 (
    for /f "tokens=*" %%v in ('py -3.12-32 --version 2^>^&1') do set "PYVER=%%v"
    echo   [OK] Found: !PYVER! ^(py launcher^)
    set "PYTHON_CMD=py -3.12-32"
    goto :found_python
)

REM Try common paths
for %%p in (
    "%LOCALAPPDATA%\Programs\Python\Python312-32\python.exe"
    "C:\Python312-32\python.exe"
    "C:\Python312\python.exe"
) do (
    if exist %%p (
        for /f %%a in ('%%p -c "import struct; print(struct.calcsize('P') * 8)" 2^>nul') do (
            if "%%a"=="32" (
                for /f "tokens=*" %%v in ('%%p --version 2^>^&1') do set "PYVER=%%v"
                echo   [OK] Found: !PYVER! at %%p
                set "PYTHON_CMD=%%p"
                goto :found_python
            )
        )
    )
)

echo   [NG] 32-bit Python 3.12 not found.
echo.
echo   Please install Python 3.12 ^(32-bit^):
echo     Download: https://www.python.org/downloads/
echo     Choose 'Windows installer ^(32-bit^)'
echo     Check 'Add Python to PATH'
echo.
pause
exit /b 1

:found_python

REM === Step 2: Check Git ===
echo.
echo   Step 2/7: Checking Git...

git --version >nul 2>&1
if !errorlevel! neq 0 (
    echo   [NG] Git not found.
    echo   Install from: https://git-scm.com/download/win
    echo   Or: winget install Git.Git
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('git --version 2^>^&1') do echo   [OK] Found: %%v

REM === Step 3: Clone or update repository ===
echo.
echo   Step 3/7: Setting up repository...

if exist "%INSTALL_DIR%\.git" (
    echo   [OK] Repository exists at %INSTALL_DIR%
    pushd "%INSTALL_DIR%"
    git pull --ff-only origin master >nul 2>&1
    if !errorlevel!==0 (
        echo   [OK] Updated to latest version
    ) else (
        echo   [!!] Could not update ^(local changes?^)
    )
    popd
) else (
    echo   Cloning to %INSTALL_DIR%...
    git clone %REPO_URL% "%INSTALL_DIR%" >nul 2>&1
    if !errorlevel! neq 0 (
        echo   [NG] Failed to clone repository
        pause
        exit /b 1
    )
    echo   [OK] Cloned to %INSTALL_DIR%
)

REM === Step 4: Create virtual environment ===
echo.
echo   Step 4/7: Creating virtual environment ^(32-bit^)...

if exist "%VENV_DIR%\Scripts\python.exe" (
    for /f %%a in ('"%VENV_DIR%\Scripts\python.exe" -c "import struct; print(struct.calcsize('P') * 8)" 2^>nul') do (
        if "%%a"=="32" (
            echo   [OK] Virtual environment exists ^(32-bit verified^)
            goto :venv_ready
        )
    )
    echo   [!!] Existing venv is not 32-bit, recreating...
    rmdir /s /q "%VENV_DIR%"
)

%PYTHON_CMD% -m venv "%VENV_DIR%"
if !errorlevel! neq 0 (
    echo   [NG] Failed to create virtual environment
    pause
    exit /b 1
)
echo   [OK] Virtual environment created

:venv_ready

REM === Step 5: Install dependencies ===
echo.
echo   Step 5/7: Installing dependencies...

"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1

pushd "%INSTALL_DIR%"
"%VENV_DIR%\Scripts\pip.exe" install -e . >nul 2>&1
if !errorlevel! neq 0 (
    echo   [NG] Failed to install dependencies
    popd
    pause
    exit /b 1
)
echo   [OK] Dependencies installed
popd

REM === Step 6: Setup config ===
echo.
echo   Step 6/7: Setting up configuration...

if not exist "%INSTALL_DIR%\config" mkdir "%INSTALL_DIR%\config"
if not exist "%INSTALL_DIR%\data" mkdir "%INSTALL_DIR%\data"
if not exist "%INSTALL_DIR%\logs" mkdir "%INSTALL_DIR%\logs"

if exist "%INSTALL_DIR%\config\config.yaml" (
    echo   [OK] config.yaml already exists
) else if exist "%INSTALL_DIR%\config\config.yaml.example" (
    copy "%INSTALL_DIR%\config\config.yaml.example" "%INSTALL_DIR%\config\config.yaml" >nul
    echo   [OK] Created config.yaml from template
    echo   [!!] Edit %INSTALL_DIR%\config\config.yaml to set your service keys
) else (
    echo   [!!] config.yaml.example not found, run 'jltsql init' later
)

REM === Step 7: Add to PATH ===
echo.
echo   Step 7/7: Setting up PATH...

set "SCRIPTS_DIR=%VENV_DIR%\Scripts"

REM Check if already in PATH
echo %PATH% | findstr /i /c:"%SCRIPTS_DIR%" >nul 2>&1
if !errorlevel!==0 (
    echo   [OK] PATH already configured
) else (
    REM Add to user PATH via PowerShell (most reliable method)
    powershell -NoProfile -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';%SCRIPTS_DIR%;%INSTALL_DIR%', 'User')" >nul 2>&1
    if !errorlevel!==0 (
        echo   [OK] Added to PATH
        echo   [!!] Restart your terminal for PATH changes to take effect
    ) else (
        echo   [!!] Could not update PATH automatically
        echo   Add manually: %SCRIPTS_DIR%
    )
)

REM === Complete ===
echo.
echo   ============================================
echo     Installation Complete!
echo   ============================================
echo.
echo   Install directory: %INSTALL_DIR%
echo.
echo   Next steps:
echo     1. Restart your terminal
echo     2. Edit config: %INSTALL_DIR%\config\config.yaml
echo     3. Run: jltsql init
echo     4. Run: jltsql fetch --from 20240101 --to 20241231 --spec RACE
echo.
echo   Quick start ^(interactive^):
echo     cd %INSTALL_DIR% ^&^& quickstart.bat
echo.
echo   Commands:
echo     jltsql version     Show version info
echo     jltsql update      Update to latest version
echo     jltsql --help      Show all commands
echo.
pause
endlocal
exit /b 0
