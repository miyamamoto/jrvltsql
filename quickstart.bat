@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title JLTSQL Setup

REM batファイルのあるディレクトリに移動
cd /d "%~dp0"

REM Python 32bit版を探す
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3-32 scripts/quickstart.py %*
) else (
    python scripts/quickstart.py %*
)

echo.
echo ============================================================
echo   セットアップ完了
echo ============================================================
echo.
echo   よく使うコマンド:
echo     jltsql status     - データベースの状態を確認
echo     jltsql fetch      - データ取得
echo     jltsql export     - データをCSV/JSONにエクスポート
echo.
echo   詳細は jltsql --help を参照してください
echo.
echo   Enterキーを押すと終了します...
set /p dummy=
