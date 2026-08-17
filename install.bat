@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title JLTSQL Installer

echo.
echo   ============================================
echo     JLTSQL Installer
echo     JRA-VAN DataLab -^> SQL
echo   ============================================
echo.

set "INSTALL_DIR=%USERPROFILE%\jrvltsql"
set "REPO_URL=https://github.com/miyamamoto/jrvltsql.git"
set "VENV_DIR=%INSTALL_DIR%\.venv"
set "PYTHON_CMD="
set "PYTHON_BITS="
set "VENV_BITS="

REM === Step 1: Find Python 3.12+ ===
echo   Step 1/7: Checking Python 3.12 or later...

if defined PYTHON (
    if not exist "%PYTHON%" (
        echo   [NG] PYTHON must be a full path to python.exe.
        exit /b 1
    )
    "%PYTHON%" -c "import sys; raise SystemExit(sys.version_info < (3, 12))" >nul 2>&1
    if !errorlevel! neq 0 (
        echo   [NG] PYTHON must point to Python 3.12 or later.
        exit /b 1
    )
    set "PYTHON_CMD="!PYTHON!""
    goto :found_python
)

REM Keep the release-validated 32-bit JV-Link path as the automatic default.
REM A caller may opt into another matching interpreter through PYTHON.
py -3.12-32 --version >nul 2>&1
if !errorlevel!==0 (
    set "PYTHON_CMD=py -3.12-32"
    goto :found_python
)

echo   [NG] Python 3.12 or later not found.
echo.
echo   Install 32-bit Python, or set PYTHON to a full path only for explicit SDK validation:
echo     Download: https://www.python.org/downloads/
echo     Check 'Add Python to PATH'
echo.
pause
exit /b 1

:found_python
set "BITS_FILE=%TEMP%\jltsql_python_bits_!RANDOM!_!RANDOM!.txt"
%PYTHON_CMD% -c "import struct; print(struct.calcsize('P') * 8)" > "!BITS_FILE!" 2>nul
if !errorlevel! neq 0 (
    if exist "!BITS_FILE!" del /q "!BITS_FILE!"
    echo   [NG] Failed to inspect selected Python architecture.
    exit /b 1
)
set /p PYTHON_BITS=<"!BITS_FILE!"
del /q "!BITS_FILE!"
if not "!PYTHON_BITS!"=="32" if not "!PYTHON_BITS!"=="64" (
    echo   [NG] Selected Python returned an invalid architecture.
    exit /b 1
)
echo   [OK] Found: %PYTHON_CMD% ^(!PYTHON_BITS!-bit^)
if "!PYTHON_BITS!"=="64" echo   [!!] 64-bit execution is not release-validated; use only for explicit SDK validation.

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
echo   Step 4/7: Creating virtual environment...

if exist "%INSTALL_DIR%\.venv\Scripts\python.exe" (
    set "VENV_DIR=%INSTALL_DIR%\.venv"
) else if exist "%INSTALL_DIR%\venv32\Scripts\python.exe" (
    REM Preserve upgrades from releases that created venv32.
    set "VENV_DIR=%INSTALL_DIR%\venv32"
)

if exist "%VENV_DIR%\Scripts\python.exe" (
    "%VENV_DIR%\Scripts\python.exe" -c "import sys; raise SystemExit(sys.version_info < (3, 12))" >nul 2>&1
    if !errorlevel!==0 (
        "%VENV_DIR%\Scripts\python.exe" -c "import struct; raise SystemExit(struct.calcsize('P') * 8 != int('!PYTHON_BITS!'))" >nul 2>&1
        if !errorlevel!==0 set "VENV_BITS=!PYTHON_BITS!"
        if "!VENV_BITS!"=="!PYTHON_BITS!" (
            echo   [OK] Compatible virtual environment exists
            goto :venv_ready
        )
        echo   [!!] Existing virtual environment bitness does not match selected Python; recreating...
    ) else (
        echo   [!!] Existing venv uses unsupported Python; recreating...
    )
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
    echo   [!!] Review %INSTALL_DIR%\config\config.yaml for database settings
    echo   [!!] Register JV-Link in the JRA-VAN DataLab application
) else (
    echo   [!!] config.yaml.example not found; restore the checkout and re-run this installer
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
echo     3. Run: cd /d "%INSTALL_DIR%"
echo        jltsql --config "config\config.yaml" fetch --from 20240101 --to 20241231 --spec RACE
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
