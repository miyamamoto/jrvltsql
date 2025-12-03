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
echo   データベースファイル: data\keiba.db (SQLite)
echo.
echo   データを確認するには:
echo     - DB Browser for SQLite などで直接開く
echo     - Python: sqlite3.connect('data/keiba.db')
echo.
echo   CLIコマンド:
echo     jltsql status   - データベースの状態を確認
echo     jltsql fetch    - 追加データ取得
echo     jltsql --help   - その他のコマンド
echo.
echo   Claude Code / Claude Desktop をお使いの方へ:
echo     MCP Server をインストールすると、AIから直接DBにアクセスできます
echo     https://github.com/miyamamoto/jvlink-mcp-server/releases
echo.
echo   Enterキーを押すと終了します...
set /p dummy=
