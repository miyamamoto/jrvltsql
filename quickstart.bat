@echo off
chcp 65001 >nul 2>&1
title JLTSQL Setup

REM Python 32bit版を探す
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3-32 scripts/quickstart.py %*
) else (
    python scripts/quickstart.py %*
)

pause
