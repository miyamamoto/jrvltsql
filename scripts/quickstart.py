#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""JLTSQL Quick Start Script - Claude Code風のモダンなUI

このスクリプトはJLTSQLの完全自動セットアップを実行します：
1. プロジェクト初期化
2. テーブル・インデックス作成
3. すべてのデータ取得（蓄積系データ）
4. リアルタイム監視の開始（オプション）
"""

import argparse
import io
import json
import os
import subprocess
import sys
import time
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Set COM threading model to Apartment Threaded (STA)
# This MUST be set before any other COM/win32com imports or usage
# Required for 64-bit Python to communicate with 32-bit UmaConn (ActiveX/GUI)
try:
    sys.coinit_flags = 2
except AttributeError:
    # sys module might not be fully initialized yet in some environments
    pass

# Windows cp932対策: stdoutをUTF-8に再設定
if sys.platform == "win32" and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ログ設定: 自動設定を無効化（進捗表示を邪魔しないため）
# 環境変数でモジュールインポート時の自動ログ設定をスキップ
os.environ['JLTSQL_SKIP_AUTO_LOGGING'] = '1'
from src.utils.logger import setup_logging, get_logger
# 初期設定: ログファイル出力は無効（main()で引数に基づいて再設定）
setup_logging(level="DEBUG", console_level="CRITICAL", log_to_file=False, log_to_console=False)
logger = get_logger(__name__)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.table import Table
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from src.utils.lock_manager import ProcessLock, ProcessLockError


# Windows cp932対策: stdoutをUTF-8に設定した上でConsoleを作成
if RICH_AVAILABLE:
    console = Console(file=sys.stdout, force_terminal=True, legacy_windows=False)
else:
    console = None


def interactive_setup() -> dict:
    """対話形式で設定を収集"""
    if RICH_AVAILABLE:
        return _interactive_setup_rich()
    else:
        return _interactive_setup_simple()


# セットアップ履歴ファイルのパス
SETUP_HISTORY_FILE = project_root / "data" / "setup_history.json"


def _load_setup_history() -> Optional[dict]:
    """前回のセットアップ履歴を読み込む

    Returns:
        前回のセットアップ情報、なければNone
    """
    if not SETUP_HISTORY_FILE.exists():
        return None

    try:
        with open(SETUP_HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _save_setup_history(settings: dict, specs: list):
    """セットアップ履歴を保存する

    Args:
        settings: セットアップ設定
        specs: 取得したデータ種別リスト [(spec, desc, option), ...]
    """
    history = {
        'timestamp': datetime.now().isoformat(),
        'mode': settings.get('mode'),
        'mode_name': settings.get('mode_name'),
        'from_date': settings.get('from_date'),
        'to_date': settings.get('to_date'),
        'specs': [spec for spec, _, _ in specs],
        'include_realtime': settings.get('include_realtime', False),
        # データベース設定
        'db_type': settings.get('db_type', 'sqlite'),
        'db_path': settings.get('db_path', 'data/keiba.db'),
    }

    # PostgreSQL設定（パスワード以外を保存）
    if settings.get('db_type') == 'postgresql':
        history['pg_host'] = settings.get('pg_host', 'localhost')
        history['pg_port'] = settings.get('pg_port', 5432)
        history['pg_database'] = settings.get('pg_database', 'keiba')
        history['pg_user'] = settings.get('pg_user', 'postgres')
        # パスワードは保存しない（セキュリティ上の理由）
        # 次回実行時はPGPASSWORD環境変数または再入力が必要

    # data ディレクトリがなければ作成
    SETUP_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(SETUP_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except IOError:
        pass  # 保存失敗しても継続


# === バックグラウンド更新管理 ===

def _check_background_updater_running() -> tuple[bool, Optional[int]]:
    """バックグラウンド更新プロセスが起動中かどうか確認

    Returns:
        (is_running, pid): 起動中かどうかとPID
    """
    lock_file = project_root / ".locks" / "background_updater.lock"
    if not lock_file.exists():
        return (False, None)

    try:
        with open(lock_file, 'r') as f:
            pid = int(f.read().strip())

        # プロセスが実際に動いているか確認
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True, timeout=5
            )
            if str(pid) in result.stdout:
                return (True, pid)
        else:
            try:
                os.kill(pid, 0)
                return (True, pid)
            except OSError:
                pass

        # プロセスが動いていなければロックファイルを削除
        lock_file.unlink(missing_ok=True)
        return (False, None)

    except (ValueError, IOError, subprocess.TimeoutExpired):
        return (False, None)


def _stop_background_updater(pid: int) -> bool:
    """バックグラウンド更新プロセスを停止

    Args:
        pid: 停止するプロセスのPID

    Returns:
        停止に成功したかどうか
    """
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True, timeout=10
            )
        else:
            os.kill(pid, 15)  # SIGTERM

        # 停止を待機
        time.sleep(2)

        # ロックファイルを削除
        lock_file = project_root / ".locks" / "background_updater.lock"
        if lock_file.exists():
            lock_file.unlink()

        return True
    except Exception:
        return False


def _get_startup_folder() -> Optional[Path]:
    """Windowsスタートアップフォルダのパスを取得

    Returns:
        スタートアップフォルダのパス（Windows以外はNone）
    """
    if sys.platform != "win32":
        return None

    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        )
        try:
            startup_path, _ = winreg.QueryValueEx(key, "Startup")
            return Path(startup_path)
        finally:
            winreg.CloseKey(key)
    except Exception:
        # フォールバック: 標準的なパス
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return None


def _get_startup_batch_path() -> Optional[Path]:
    """スタートアップに配置するバッチファイルのパスを取得"""
    startup_folder = _get_startup_folder()
    if startup_folder:
        return startup_folder / "jltsql_background_updater.bat"
    return None


def _is_auto_start_enabled() -> bool:
    """自動起動が設定されているか確認"""
    batch_path = _get_startup_batch_path()
    return batch_path is not None and batch_path.exists()


def _enable_auto_start() -> bool:
    """Windows起動時の自動起動を有効化

    Returns:
        設定に成功したかどうか
    """
    batch_path = _get_startup_batch_path()
    if batch_path is None:
        return False

    try:
        # バッチファイルの内容を作成
        python_exe = sys.executable
        script_path = project_root / "scripts" / "background_updater.py"

        batch_content = f'''@echo off
REM JLTSQL バックグラウンド更新サービス自動起動
REM このファイルはJLTSQLセットアップにより作成されました

cd /d "{project_root}"
start "" /MIN "{python_exe}" "{script_path}"
'''
        batch_path.write_text(batch_content, encoding='cp932')
        return True

    except Exception:
        return False


def _disable_auto_start() -> bool:
    """Windows起動時の自動起動を無効化

    Returns:
        設定に成功したかどうか
    """
    batch_path = _get_startup_batch_path()
    if batch_path is None:
        return False

    try:
        if batch_path.exists():
            batch_path.unlink()
        return True
    except Exception:
        return False


def _check_jvlink_service_key() -> tuple[bool, str]:
    """JV-Linkのサービスキー設定状況を実際にAPIで確認

    Returns:
        (is_valid, message): サービスキーが有効かどうかとメッセージ
    """
    import struct
    is_64bit = struct.calcsize("P") * 8 == 64
    
    try:
        import win32com.client
        jvlink = win32com.client.Dispatch("JVDTLab.JVLink")

        # JVInitで認証チェック（sidは任意の文字列）
        result = jvlink.JVInit("JLTSQL")

        if result == 0:
            return True, "JV-Link認証OK"
        elif result == -100:
            return False, "サービスキー未設定"
        elif result == -101:
            return False, "サービスキーが無効"
        elif result == -102:
            return False, "サービスキーの有効期限切れ"
        elif result == -103:
            return False, "サービス利用不可"
        else:
            return False, f"JV-Link初期化エラー (code: {result})"
    except Exception as e:
        error_msg = str(e).lower()
        # 64-bit Python + 32-bit DLL の問題を検出
        if is_64bit and ("class not registered" in error_msg or 
                         "クラスが登録されていません" in error_msg or
                         "-2147221164" in error_msg):
            return False, (
                "JV-Link検出不可 (64-bit Python使用中)\n"
                "    → JV-Linkは32-bit DLLのため、32-bit Pythonが必要です\n"
                "    → py -3.12-32 でインストール: python.org から Windows installer (32-bit) をダウンロード"
            )
        elif "no module named 'win32com'" in error_msg:
            return False, "pywin32未インストール: pip install pywin32"
        else:
            return False, f"JV-Link未インストールまたはアクセス不可: {e}"


def _check_nvlink_service_key() -> tuple[bool, str]:
    """NV-Link（UmaConn）のサービスキー設定状況を実際にAPIで確認
    
    Note:
        64-bit Python環境でのCOM初期化(STAモード)を確実に有効にするため、
        現在のプロセスではなく、独立したサブプロセスでチェックを行います。
        これにより、他ライブラリによるCOM干渉を防ぎます。

    Returns:
        (is_valid, message): サービスキーが有効かどうかとメッセージ
    """
    import subprocess
    import sys
    
    # 独立したプロセスで実行する検証コード
    check_code = """
import sys
try:
    sys.coinit_flags = 2  # STA mode
except Exception:
    pass
import win32com.client
import pythoncom

try:
    pythoncom.CoInitialize()
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
    result = nvlink.NVInit("JLTSQL_CHECK")
    print(f"RESULT:{result}")
except Exception as e:
    print(f"ERROR:{e}")
"""
    
    try:
        # サブプロセスで実行
        proc = subprocess.run(
            [sys.executable, "-c", check_code],
            capture_output=True,
            text=True,
            encoding='utf-8', # Force UTF-8 for communication
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        
        output = proc.stdout.strip()
        
        # 結果の解析
        if "RESULT:0" in output:
             return True, "NV-Link（UmaConn）認証OK"
        elif "RESULT:" in output:
            try:
                # RESULT:-100 などを抽出
                result_code = int(output.split("RESULT:")[1].strip())
                if result_code == -100:
                    return False, "サービスキー未設定"
                elif result_code == -101:
                    return False, "サービスキーが無効"
                elif result_code == -102:
                    return False, "サービスキーの有効期限切れ"
                elif result_code == -103:
                    return False, "サービス利用不可"
                else:
                    return False, f"NV-Link初期化エラー (code: {result_code})"
            except Exception:
                return False, f"予期しないレスポンス: {output}"
        else:
            # エラーメッセージが含まれている場合
            if "ERROR:" in output:
                error_msg = output.split("ERROR:")[1].strip()
                return False, f"NV-Linkエラー: {error_msg}"
            return False, f"NV-Link検証プロセスが失敗しました: {proc.stderr}"

    except Exception as e:
        return False, f"NV-Link検証実行エラー: {e}"


def _check_nar_initial_setup() -> tuple[bool, str]:
    """NV-Linkの初回セットアップが完了しているか確認

    NVOpen後にNVStatusを確認し、-203エラーが出ないかチェックします。
    -203エラーは初回セットアップが完了していないことを示します。

    Returns:
        (is_setup_complete, message): セットアップ完了かどうかとメッセージ
    """
    import subprocess
    import sys

    check_code = """
import sys
import time
try:
    sys.coinit_flags = 2  # STA mode
except Exception:
    pass
import win32com.client
import pythoncom

try:
    pythoncom.CoInitialize()
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")

    # Initialize
    init_result = nvlink.NVInit("JLTSQL_SETUP_CHECK")
    if init_result != 0:
        print(f"INIT_ERROR:{init_result}")
        sys.exit(0)

    # Try NVOpen with option=1 (normal mode)
    result = nvlink.NVOpen("RACE", "20241201000000", 1)
    read_count = nvlink.m_ReadCount
    download_count = nvlink.m_DownloadCount

    # Check status if download is pending
    if download_count > 0:
        time.sleep(0.5)
        status = nvlink.NVStatus()
        if status == -203:
            print("SETUP_NEEDED:-203")
        else:
            print(f"STATUS:{status}")
    elif read_count > 0:
        # Try to read a record
        ret_code = nvlink.NVGets()
        filename = nvlink.m_FileName
        if ret_code == -203:
            print("SETUP_NEEDED:-203")
        elif ret_code > 0 or ret_code == 0:
            print("SETUP_COMPLETE")
        elif ret_code == -1:
            # File switch - check again
            ret_code = nvlink.NVGets()
            if ret_code == -203:
                print("SETUP_NEEDED:-203")
            else:
                print("SETUP_COMPLETE")
        else:
            print(f"READ_ERROR:{ret_code}")
    else:
        # No data but that's OK - setup is complete
        print("SETUP_COMPLETE:nodata")

    nvlink.NVClose()

except Exception as e:
    print(f"ERROR:{e}")
"""

    try:
        proc = subprocess.run(
            [sys.executable, "-c", check_code],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        output = proc.stdout.strip()

        if "SETUP_COMPLETE" in output:
            return True, "初回セットアップ完了"
        elif "SETUP_NEEDED" in output:
            return False, "初回セットアップが必要です"
        elif "INIT_ERROR" in output:
            return False, "NV-Link初期化エラー"
        elif "READ_ERROR" in output:
            error_code = output.split(":")[1] if ":" in output else "不明"
            return False, f"データ読み込みエラー (code: {error_code})"
        elif "ERROR:" in output:
            error_msg = output.split("ERROR:")[1].strip()
            return False, f"エラー: {error_msg}"
        else:
            return False, f"不明なレスポンス: {output}"

    except subprocess.TimeoutExpired:
        return False, "タイムアウト"
    except Exception as e:
        return False, f"チェックエラー: {e}"


def _run_nar_initial_setup(console=None, show_progress: bool = True) -> tuple[bool, str]:
    """NV-Linkの初回セットアップダイアログを開く

    NVSetUIPropertiesを呼び出してサービスキー設定ダイアログを開きます。

    Note:
        UmaConn/NV-Linkの初回データダウンロードは、公式アプリケーションを
        通じて手動で完了する必要があります。NV-Link APIだけでは初回セット
        アップを完了できないため、以下の手順が必要です：
        1. NVSetUIPropertiesでサービスキーを設定
        2. 地方競馬DATAセットアップツールで「セットアップ」を実行

    Args:
        console: Rich console for output (optional)
        show_progress: Whether to show progress updates

    Returns:
        (success, message): セットアップ成功かどうかとメッセージ
    """
    import subprocess
    import sys

    # Open NVSetUIProperties dialog for service key configuration
    setup_code = """
import sys
try:
    sys.coinit_flags = 2  # STA mode for UI
except Exception:
    pass
import win32com.client
import pythoncom

try:
    pythoncom.CoInitialize()
    nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")

    # Open UI Properties dialog
    result = nvlink.NVSetUIProperties()

    if result == 0:
        print("DIALOG_CLOSED")
    else:
        print(f"DIALOG_ERROR:{result}")

except Exception as e:
    print(f"ERROR:{e}")
"""

    if console:
        console.print()
        console.print("    [yellow]サービスキー設定ダイアログを開いています...[/yellow]")
        console.print()
        console.print("    [bold]手順:[/bold]")
        console.print("    1. ダイアログでサービスキーを入力/確認")
        console.print("    2. 「OK」をクリックしてダイアログを閉じる")
        console.print()

    try:
        proc = subprocess.run(
            [sys.executable, "-c", setup_code],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=300,  # 5 minutes for dialog interaction
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        output = proc.stdout.strip()

        if "DIALOG_CLOSED" in output:
            if console:
                console.print()
                console.print("    [yellow]⚠ 重要: 初回データダウンロードについて[/yellow]")
                console.print()
                console.print("    UmaConnの初回セットアップを完了するには、")
                console.print("    [bold]地方競馬DATAセットアップツール[/bold]を実行してください:")
                console.print()
                console.print("    スタートメニュー → 地方競馬DATA → セットアップ")
                console.print("    または: C:\\UmaConn\\chiho.k-ba\\data\\UmaConn設定.exe")
                console.print()
            return True, "サービスキー設定完了（初回データダウンロードは手動で実行してください）"
        elif "DIALOG_ERROR" in output:
            error_code = output.split(":")[1] if ":" in output else "不明"
            return False, f"ダイアログエラー (code: {error_code})"
        elif "ERROR:" in output:
            error_msg = output.split("ERROR:")[1].strip()
            return False, f"エラー: {error_msg}"
        else:
            return False, f"不明なレスポンス: {output}"

    except subprocess.TimeoutExpired:
        return False, "タイムアウト（5分）"
    except Exception as e:
        return False, f"セットアップ実行エラー: {e}"



def _check_service_key_detailed(data_source: str = "jra") -> dict:
    """データソースに応じたサービスキー確認（詳細版）

    Args:
        data_source: "jra", "nar", または "all"

    Returns:
        dict with:
            - all_valid: bool - すべて有効か
            - jra_valid: bool - JRAが有効か（all/jraの場合）
            - nar_valid: bool - NARが有効か（all/narの場合）
            - jra_msg: str - JRAのメッセージ
            - nar_msg: str - NARのメッセージ
            - available_sources: list - 利用可能なソース ['jra', 'nar']
    """
    result = {
        'all_valid': False,
        'jra_valid': False,
        'nar_valid': False,
        'jra_msg': '',
        'nar_msg': '',
        'available_sources': []
    }

    if data_source == "nar":
        nar_valid, nar_msg = _check_nvlink_service_key()
        result['nar_valid'] = nar_valid
        result['nar_msg'] = nar_msg
        result['all_valid'] = nar_valid
        if nar_valid:
            result['available_sources'] = ['nar']
    elif data_source == "all":
        jra_valid, jra_msg = _check_jvlink_service_key()
        nar_valid, nar_msg = _check_nvlink_service_key()
        result['jra_valid'] = jra_valid
        result['nar_valid'] = nar_valid
        result['jra_msg'] = jra_msg
        result['nar_msg'] = nar_msg
        result['all_valid'] = jra_valid and nar_valid
        if jra_valid:
            result['available_sources'].append('jra')
        if nar_valid:
            result['available_sources'].append('nar')
    else:  # jra
        jra_valid, jra_msg = _check_jvlink_service_key()
        result['jra_valid'] = jra_valid
        result['jra_msg'] = jra_msg
        result['all_valid'] = jra_valid
        if jra_valid:
            result['available_sources'] = ['jra']

    return result


def _check_service_key(data_source: str = "jra") -> tuple[bool, str]:
    """データソースに応じたサービスキー確認

    Args:
        data_source: "jra", "nar", または "all"

    Returns:
        (is_valid, message): サービスキーが有効かどうかとメッセージ
    """
    if data_source == "nar":
        return _check_nvlink_service_key()
    elif data_source == "all":
        # 両方チェック
        jra_valid, jra_msg = _check_jvlink_service_key()
        nar_valid, nar_msg = _check_nvlink_service_key()
        if jra_valid and nar_valid:
            return True, f"JRA: {jra_msg}, NAR: {nar_msg}"
        elif not jra_valid:
            return False, f"JRA: {jra_msg}"
        else:
            return False, f"NAR: {nar_msg}"
    else:
        return _check_jvlink_service_key()


# マスコット - シンプルな絵文字ベース
HORSE_EMOJI = "🐴"
HORSE_EMOJI_HAPPY = "🐴✨"
HORSE_EMOJI_SAD = "🐴💦"
HORSE_EMOJI_WORK = "🐴💨"


def _get_version() -> str:
    """Gitタグからバージョンを取得"""
    import subprocess
    try:
        # git describe でタグからバージョン取得
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "dev"


def _print_header_rich():
    """ヘッダー表示（馬絵文字付き）"""
    version = _get_version()
    console.print()
    console.print(Panel(
        f"[bold]{HORSE_EMOJI} JLTSQL[/bold] [dim]{version}[/dim]\n"
        "[white]JRA-VAN DataLab → SQLite / PostgreSQL[/white]\n"
        "[dim]競馬データベース自動セットアップ[/dim]",
        border_style="blue",
        padding=(1, 2),
    ))
    console.print()


def _check_postgresql_database(host: str, port: int, database: str, user: str, password: str):
    """PostgreSQLデータベースの存在確認と作成

    Args:
        host: ホスト名
        port: ポート番号
        database: データベース名
        user: ユーザー名
        password: パスワード

    Returns:
        (ステータス, メッセージ)
        ステータス: "exists" (既存), "created" (新規作成), "error" (エラー)
    """
    try:
        # PostgreSQLドライバのインポート
        try:
            import pg8000.native
            driver = "pg8000"
        except ImportError:
            try:
                import psycopg
                driver = "psycopg"
            except ImportError:
                return "error", "PostgreSQLドライバがインストールされていません。\npip install pg8000 または pip install psycopg を実行してください。"

        # まずpostgresデータベースに接続してターゲットDBの存在確認
        if driver == "pg8000":
            conn = pg8000.native.Connection(
                host=host,
                port=port,
                database="postgres",  # デフォルトDBに接続
                user=user,
                password=password,
                timeout=10
            )
            # データベースの存在確認
            rows = conn.run("SELECT datname FROM pg_database WHERE datname = :db", db=database)
            db_exists = len(rows) > 0

            if not db_exists:
                # データベースを作成
                conn.run(f'CREATE DATABASE "{database}"')
                conn.close()
                return "created", f"データベース '{database}' を作成しました"
            else:
                conn.close()
                return "exists", f"データベース '{database}' は既に存在します"

        else:  # psycopg
            import psycopg
            conn = psycopg.connect(
                host=host,
                port=port,
                dbname="postgres",
                user=user,
                password=password,
                connect_timeout=10,
                autocommit=True
            )
            cur = conn.cursor()
            cur.execute("SELECT datname FROM pg_database WHERE datname = %s", (database,))
            db_exists = cur.fetchone() is not None

            if not db_exists:
                cur.execute(f'CREATE DATABASE "{database}"')
                conn.close()
                return "created", f"データベース '{database}' を作成しました"
            else:
                conn.close()
                return "exists", f"データベース '{database}' は既に存在します"

    except Exception as e:
        return "error", str(e)


def _drop_postgresql_database(host: str, port: int, database: str, user: str, password: str):
    """PostgreSQLデータベースを削除して再作成

    Args:
        host: ホスト名
        port: ポート番号
        database: データベース名
        user: ユーザー名
        password: パスワード

    Returns:
        (成功/失敗, メッセージ)
    """
    try:
        try:
            import pg8000.native
            driver = "pg8000"
        except ImportError:
            import psycopg
            driver = "psycopg"

        if driver == "pg8000":
            conn = pg8000.native.Connection(
                host=host,
                port=port,
                database="postgres",
                user=user,
                password=password,
                timeout=10
            )
            # 既存の接続を強制切断
            conn.run(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = :db AND pid <> pg_backend_pid()
            """, db=database)
            # データベースを削除
            conn.run(f'DROP DATABASE IF EXISTS "{database}"')
            # データベースを再作成
            conn.run(f'CREATE DATABASE "{database}"')
            conn.close()
        else:  # psycopg
            import psycopg
            conn = psycopg.connect(
                host=host,
                port=port,
                dbname="postgres",
                user=user,
                password=password,
                connect_timeout=10,
                autocommit=True
            )
            cur = conn.cursor()
            # 既存の接続を強制切断
            cur.execute("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid()
            """, (database,))
            # データベースを削除して再作成
            cur.execute(f'DROP DATABASE IF EXISTS "{database}"')
            cur.execute(f'CREATE DATABASE "{database}"')
            conn.close()

        return True, f"データベース '{database}' を再作成しました"

    except Exception as e:
        return False, str(e)


def _test_postgresql_connection(host: str, port: int, database: str, user: str, password: str):
    """PostgreSQL接続をテスト

    Args:
        host: ホスト名
        port: ポート番号
        database: データベース名
        user: ユーザー名
        password: パスワード

    Returns:
        (成功/失敗, メッセージ)
    """
    try:
        # PostgreSQLドライバのインポート
        try:
            import pg8000.native
            driver = "pg8000"
        except ImportError:
            try:
                import psycopg
                driver = "psycopg"
            except ImportError:
                return False, "PostgreSQLドライバがインストールされていません。\npip install pg8000 または pip install psycopg を実行してください。"

        # 接続テスト
        if driver == "pg8000":
            conn = pg8000.native.Connection(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                timeout=10
            )
            conn.close()
        else:  # psycopg
            import psycopg
            conn = psycopg.connect(
                host=host,
                port=port,
                dbname=database,
                user=user,
                password=password,
                connect_timeout=10
            )
            conn.close()

        return True, f"接続成功: {user}@{host}:{port}/{database}"

    except Exception as e:
        error_msg = str(e)
        return False, f"接続失敗: {error_msg}"


def _interactive_setup_rich() -> dict:
    """Rich UIで対話形式設定"""
    console.clear()
    _print_header_rich()

    settings = {}

    # データソース選択
    console.print("[bold]0. データソース選択[/bold]")
    console.print()

    source_table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    source_table.add_column("No", style="cyan", width=3, justify="center")
    source_table.add_column("データソース", width=12)
    source_table.add_column("説明", width=50)

    source_table.add_row(
        "1", "中央競馬",
        "[dim](デフォルト)[/dim] JRA-VAN DataLab (JV-Link)"
    )
    source_table.add_row(
        "2", "地方競馬",
        "地方競馬DATA (UmaConn/NV-Link)"
    )
    source_table.add_row(
        "3", "両方",
        "中央競馬と地方競馬の両方を同時に取得"
    )

    console.print(source_table)
    console.print()

    source_choice = Prompt.ask(
        "選択",
        choices=["1", "2", "3"],
        default="1"
    )

    if source_choice == "1":
        settings['data_source'] = 'jra'
        console.print("[dim]中央競馬（JRA）を使用します[/dim]")
    elif source_choice == "2":
        settings['data_source'] = 'nar'
        console.print("[dim]地方競馬（NAR）を使用します[/dim]")
    else:
        settings['data_source'] = 'all'
        console.print("[dim]中央競馬（JRA）と地方競馬（NAR）の両方を使用します[/dim]")

    console.print()

    # データベース選択
    console.print("[bold]1. データベース選択[/bold]")
    console.print()

    db_table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    db_table.add_column("No", style="cyan", width=3, justify="center")
    db_table.add_column("データベース", width=12)
    db_table.add_column("説明", width=50)

    db_table.add_row(
        "1", "SQLite",
        "[dim](デフォルト)[/dim] ファイルベースのデータベース、設定不要"
    )
    db_table.add_row(
        "2", "PostgreSQL",
        "高性能データベース、サーバー設定が必要"
    )

    console.print(db_table)
    console.print()

    db_choice = Prompt.ask(
        "選択",
        choices=["1", "2"],
        default="1"
    )

    if db_choice == "1":
        # SQLite
        settings['db_type'] = 'sqlite'
        settings['db_path'] = 'data/keiba.db'
        console.print("[dim]SQLiteを使用します (data/keiba.db)[/dim]")
    elif db_choice == "2":
        # PostgreSQL
        settings['db_type'] = 'postgresql'
        console.print()
        console.print("[cyan]PostgreSQL接続設定[/cyan]")
        console.print()

        # 接続設定の入力
        while True:
            pg_host = Prompt.ask("ホスト", default="localhost")
            pg_port = IntPrompt.ask("ポート", default=5432)
            pg_database = Prompt.ask("データベース名", default="keiba")
            pg_user = Prompt.ask("ユーザー名", default="postgres")

            # パスワード入力（マスク表示、デフォルトpostgres）
            from rich.prompt import Prompt as RichPrompt
            pg_password = RichPrompt.ask("パスワード", default="postgres", password=True)

            console.print()
            console.print("[cyan]データベース確認中...[/cyan]")

            # データベースの存在確認と作成
            status, message = _check_postgresql_database(
                pg_host, pg_port, pg_database, pg_user, pg_password
            )

            if status == "created":
                # 新規作成成功
                console.print(f"[green]✓[/green] {message}")
                settings['pg_host'] = pg_host
                settings['pg_port'] = pg_port
                settings['pg_database'] = pg_database
                settings['pg_user'] = pg_user
                settings['pg_password'] = pg_password
                break

            elif status == "exists":
                # 既存DBがある場合は選択肢を表示
                console.print(f"[yellow]![/yellow] {message}")
                console.print()
                console.print("  [cyan]1)[/cyan] 既存データを保持して更新（追加インポート）")
                console.print("  [cyan]2)[/cyan] データベースを再作成（全データ削除）")
                console.print("  [cyan]3)[/cyan] 別のデータベース名を指定")
                console.print()

                db_choice = Prompt.ask(
                    "選択",
                    choices=["1", "2", "3"],
                    default="1"
                )
                console.print()

                if db_choice == "1":
                    # 既存DBをそのまま使用
                    console.print("[dim]既存データベースを使用します[/dim]")
                    settings['pg_host'] = pg_host
                    settings['pg_port'] = pg_port
                    settings['pg_database'] = pg_database
                    settings['pg_user'] = pg_user
                    settings['pg_password'] = pg_password
                    break
                elif db_choice == "2":
                    # DROP & CREATE
                    console.print("[cyan]データベースを再作成中...[/cyan]")
                    success, drop_msg = _drop_postgresql_database(
                        pg_host, pg_port, pg_database, pg_user, pg_password
                    )
                    if success:
                        console.print(f"[green]✓[/green] {drop_msg}")
                        settings['pg_host'] = pg_host
                        settings['pg_port'] = pg_port
                        settings['pg_database'] = pg_database
                        settings['pg_user'] = pg_user
                        settings['pg_password'] = pg_password
                        break
                    else:
                        console.print(f"[red]✗[/red] 再作成失敗: {drop_msg}")
                        # ループ継続して再入力
                elif db_choice == "3":
                    # 別のDB名を指定（ループ継続）
                    continue

            else:  # status == "error"
                console.print(f"[red]✗[/red] {message}")
                console.print()
                console.print(Panel(
                    "[bold]PostgreSQLのインストール・設定方法[/bold]\n\n"
                    "[cyan]1. PostgreSQLのインストール:[/cyan]\n"
                    "   https://www.postgresql.org/download/\n\n"
                    "[cyan]2. サービスの起動確認:[/cyan]\n"
                    "   services.msc → postgresql-x64-XX を開始\n\n"
                    "[cyan]3. Pythonドライバのインストール:[/cyan]\n"
                    "   pip install pg8000",
                    border_style="yellow",
                ))
                console.print()

                console.print("  [cyan]1)[/cyan] 再試行")
                console.print("  [cyan]2)[/cyan] SQLiteに切り替え")
                console.print()

                retry_choice = Prompt.ask(
                    "選択",
                    choices=["1", "2"],
                    default="1"
                )
                console.print()

                if retry_choice == "2":
                    console.print("[dim]SQLiteに切り替えます (data/keiba.db)[/dim]")
                    settings['db_type'] = 'sqlite'
                    settings['db_path'] = 'data/keiba.db'
                    break
                # retry_choice == "1" の場合はループ継続

    console.print()

    # サービスキーの確認（データソースに応じてJV-Link/NV-Linkをチェック）
    data_source = settings.get('data_source', 'jra')
    if data_source == 'nar':
        console.print("[bold]2. NV-Link（UmaConn）サービスキー確認[/bold]")
    elif data_source == 'all':
        console.print("[bold]2. JV-Link & NV-Link サービスキー確認[/bold]")
    else:
        console.print("[bold]2. JV-Link サービスキー確認[/bold]")
    console.print()

    # 詳細チェックを実行
    check_result = _check_service_key_detailed(data_source)

    if data_source == 'all':
        # 両方選択時は部分成功を許可
        if check_result['jra_valid']:
            console.print(f"  [green]OK[/green] JRA: {check_result['jra_msg']}")
        else:
            console.print(f"  [red]NG[/red] JRA: {check_result['jra_msg']}")

        if check_result['nar_valid']:
            console.print(f"  [green]OK[/green] NAR: {check_result['nar_msg']}")
            # NAR初回セットアップ確認
            console.print("      初回セットアップ確認中...")
            nar_setup_complete, nar_setup_msg = _check_nar_initial_setup()
            if nar_setup_complete:
                console.print(f"      [green]OK[/green] {nar_setup_msg}")
            else:
                console.print(f"      [yellow]⚠️[/yellow] {nar_setup_msg}")
                console.print()
                console.print("[bold]地方競馬DATAの初回セットアップが必要です。[/bold]")
                console.print()
                console.print("初回セットアップでは、地方競馬DATAサーバーから")
                console.print("基本データをダウンロードします（数分〜数十分かかります）。")
                console.print()

                if Confirm.ask("初回セットアップを実行しますか？", default=True):
                    console.print("[dim]初回セットアップを実行中...[/dim]")
                    setup_success, setup_msg = _run_nar_initial_setup(console)
                    console.print()

                    if setup_success:
                        console.print(f"      [green]OK[/green] {setup_msg}")
                    else:
                        # NARが使えない場合はavailable_sourcesから除外
                        console.print(f"      [red]NG[/red] {setup_msg}")
                        console.print("[yellow]NARの初回セットアップが失敗したため、NARは利用できません。[/yellow]")
                        if 'nar' in check_result['available_sources']:
                            check_result['available_sources'].remove('nar')
                        check_result['nar_valid'] = False
                else:
                    # NARセットアップをスキップした場合はavailable_sourcesから除外
                    console.print("[yellow]NARの初回セットアップをスキップしました。[/yellow]")
                    if 'nar' in check_result['available_sources']:
                        check_result['available_sources'].remove('nar')
                    check_result['nar_valid'] = False
        else:
            console.print(f"  [red]NG[/red] NAR: {check_result['nar_msg']}")

        console.print()

        # 少なくとも1つ利用可能ならば続行を提案
        if check_result['available_sources']:
            if not check_result['all_valid']:
                # 部分成功の場合
                available_names = []
                if 'jra' in check_result['available_sources']:
                    available_names.append('中央競馬（JRA）')
                if 'nar' in check_result['available_sources']:
                    available_names.append('地方競馬（NAR）')

                console.print(f"[yellow]⚠️  {' と '.join(available_names)} のみ利用可能です[/yellow]")
                console.print()

                if Confirm.ask("利用可能なソースのみで続行しますか？", default=True):
                    # 利用可能なソースのみに変更
                    if len(check_result['available_sources']) == 1:
                        settings['data_source'] = check_result['available_sources'][0]
                        source_name = '中央競馬（JRA）' if settings['data_source'] == 'jra' else '地方競馬（NAR）'
                        console.print(f"[dim]{source_name} のみで続行します[/dim]")
                    # 両方利用可能な場合はそのまま（このケースは発生しないはずだがフォールバック）
                else:
                    console.print("[red]セットアップを中止します。[/red]")
                    sys.exit(1)
        else:
            # 両方とも利用不可
            console.print("[yellow]JRA-VAN DataLab と UmaConn のサービスキーを設定してください[/yellow]")
            console.print("[dim]JRA: https://jra-van.jp/dlb/[/dim]")
            console.print("[dim]NAR: https://www.umaconn.com/[/dim]")
            console.print()
            console.print("[red]セットアップを中止します。[/red]")
            sys.exit(1)
    else:
        # jra または nar の単独選択時
        if check_result['all_valid']:
            message = check_result['jra_msg'] if data_source == 'jra' else check_result['nar_msg']
            console.print(f"  [green]OK[/green] {message}")

            # NARの場合は初回セットアップも確認
            if data_source == 'nar':
                console.print()
                console.print("[bold]  初回セットアップ確認中...[/bold]")
                setup_complete, setup_msg = _check_nar_initial_setup()

                if setup_complete:
                    console.print(f"  [green]OK[/green] {setup_msg}")
                else:
                    console.print(f"  [yellow]⚠️[/yellow] {setup_msg}")
                    console.print()
                    console.print("[bold]地方競馬DATAの初回セットアップが必要です。[/bold]")
                    console.print()
                    console.print("初回セットアップでは、地方競馬DATAサーバーから")
                    console.print("基本データをダウンロードします（数分〜数十分かかります）。")
                    console.print()

                    if Confirm.ask("初回セットアップを実行しますか？", default=True):
                        console.print("[dim]初回セットアップを実行中...[/dim]")
                        setup_success, setup_result_msg = _run_nar_initial_setup(console)
                        console.print()

                        if setup_success:
                            console.print(f"  [green]OK[/green] {setup_result_msg}")
                        else:
                            console.print(f"  [red]NG[/red] {setup_result_msg}")
                            console.print()
                            console.print("[red]初回セットアップが失敗しました。[/red]")
                            console.print("再度 quickstart を実行してください。")
                            sys.exit(1)
                    else:
                        console.print()
                        console.print("[red]セットアップを中止します。[/red]")
                        console.print("後で quickstart を再実行するか、jltsql setup-nar を実行してください。")
                        sys.exit(1)

            console.print()
        else:
            message = check_result['jra_msg'] if data_source == 'jra' else check_result['nar_msg']
            console.print(f"  [red]NG[/red] {message}")
            console.print()
            if data_source == 'nar':
                console.print("[yellow]UmaConn（地方競馬DATA）ソフトウェアでサービスキーを設定してください[/yellow]")
                console.print("[dim]https://www.umaconn.com/[/dim]")
            else:
                console.print("[yellow]JRA-VAN DataLabソフトウェアでサービスキーを設定してください[/yellow]")
                console.print("[dim]https://jra-van.jp/dlb/[/dim]")
            console.print()
            console.print("[red]セットアップを中止します。[/red]")
            sys.exit(1)

    # 前回セットアップ履歴を確認
    last_setup = _load_setup_history()

    # セットアップモードの選択
    console.print("[bold]3. セットアップモード[/bold]")
    console.print()

    mode_table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    mode_table.add_column("No", style="cyan", width=3, justify="center")
    mode_table.add_column("モード", width=6)
    mode_table.add_column("対象データ", width=50)

    mode_table.add_row(
        "1", "簡易",
        "RACE, DIFF\n[dim](レース結果・確定オッズ・馬情報)[/dim]"
    )
    mode_table.add_row(
        "2", "標準",
        "簡易 + BLOD,YSCH,TOKU,SLOP,HOYU,HOSE等\n[dim](血統・調教・スケジュール等)[/dim]"
    )
    mode_table.add_row(
        "3", "フル",
        "標準 + MING,WOOD,COMM\n[dim](マイニング・調教詳細・解説)[/dim]"
    )

    # 更新モードは前回セットアップがある場合のみ表示
    if last_setup:
        last_date = datetime.fromisoformat(last_setup['timestamp'])
        last_date_str = last_date.strftime("%Y-%m-%d %H:%M")
        mode_table.add_row(
            "4", "更新",
            f"前回と同じ ({last_setup.get('mode_name', '?')}) [dim]差分のみ {last_date_str}〜[/dim]"
        )
        choices = ["1", "2", "3", "4"]
    else:
        choices = ["1", "2", "3"]

    console.print(mode_table)
    console.print()

    choice = Prompt.ask(
        "選択",
        choices=choices,
        default="1"
    )

    today = datetime.now()
    settings['to_date'] = today.strftime("%Y%m%d")

    if choice == "1":
        settings['mode'] = 'simple'
        settings['mode_name'] = '簡易'
    elif choice == "2":
        settings['mode'] = 'standard'
        settings['mode_name'] = '標準'
    elif choice == "3":
        settings['mode'] = 'full'
        settings['mode_name'] = 'フル'

    # 更新モード以外は期間選択
    if choice in ["1", "2", "3"]:
        console.print()
        console.print("[bold cyan]取得期間を選択してください[/bold cyan]")
        console.print()

        # モードに応じた所要時間の見積もり（簡易=1.0, 標準=1.5, フル=2.5倍）
        time_multiplier = {"1": 1.0, "2": 1.5, "3": 2.5}[choice]

        def format_time(base_minutes: float) -> str:
            """所要時間を見積もってフォーマット"""
            minutes = base_minutes * time_multiplier
            if minutes < 60:
                return f"[green]約{int(minutes)}分[/green]"
            elif minutes < 300:
                hours = minutes / 60
                return f"[yellow]約{hours:.0f}〜{hours*1.5:.0f}時間[/yellow]"
            else:
                hours = minutes / 60
                return f"[bold red]約{hours:.0f}時間以上[/bold red]"

        period_table = Table(show_header=True, header_style="bold", box=None)
        period_table.add_column("No", width=4)
        period_table.add_column("期間", width=14)
        period_table.add_column("説明", width=20)
        period_table.add_column("所要時間(税込)", width=20)

        # セットアップモード(option=4)では調教データ等が全期間分返されるため
        # 短期間でも相当な時間がかかる
        period_table.add_row("1", "直近1週間", "[dim]デバッグ・テスト用[/dim]", format_time(30))
        period_table.add_row("2", "直近1ヶ月", "[dim]短期テスト用[/dim]", format_time(60))
        period_table.add_row("3", "直近1年", "[dim]実用的な範囲[/dim]", format_time(180))
        period_table.add_row("4", "直近5年", "[dim]中長期分析用[/dim]", format_time(480))
        period_table.add_row("5", "全期間", "[dim]1986年〜[/dim]", format_time(960))
        period_table.add_row("6", "カスタム", "[dim]日付を指定[/dim]", "[dim]期間による[/dim]")

        console.print(period_table)
        console.print()

        period_choice = Prompt.ask(
            "選択",
            choices=["1", "2", "3", "4", "5", "6"],
            default="3"
        )

        if period_choice == "1":
            settings['from_date'] = (today - timedelta(days=7)).strftime("%Y%m%d")
        elif period_choice == "2":
            settings['from_date'] = (today - timedelta(days=30)).strftime("%Y%m%d")
        elif period_choice == "3":
            settings['from_date'] = (today - timedelta(days=365)).strftime("%Y%m%d")
        elif period_choice == "4":
            settings['from_date'] = (today - timedelta(days=365*5)).strftime("%Y%m%d")
        elif period_choice == "5":
            settings['from_date'] = "19860101"
        else:
            # カスタム日付入力
            console.print()
            console.print("[bold cyan]開始日を入力してください[/bold cyan]")
            console.print("[dim]形式: YYYY-MM-DD または YYYYMMDD (例: 2020-01-01)[/dim]")
            console.print()

            while True:
                from_input = Prompt.ask("開始日", default="2020-01-01")
                # ハイフンを除去
                from_date_str = from_input.replace("-", "").replace("/", "")
                try:
                    # 日付として有効か確認
                    from_date = datetime.strptime(from_date_str, "%Y%m%d")
                    if from_date < datetime(1986, 1, 1):
                        console.print("[yellow]1986年より前のデータはありません。1986-01-01に設定します。[/yellow]")
                        from_date_str = "19860101"
                    elif from_date > today:
                        console.print("[red]未来の日付は指定できません。[/red]")
                        continue
                    settings['from_date'] = from_date_str

                    # 所要時間を計算して表示
                    # セットアップモードでは調教データ等が全期間分取得されるため基準時間を増加
                    days_diff = (today - datetime.strptime(from_date_str, "%Y%m%d")).days
                    estimated_minutes = (days_diff / 365) * 180 * time_multiplier  # 1年あたり180分
                    # 最低30分（調教データ等の固定オーバーヘッド）
                    estimated_minutes = max(estimated_minutes, 30 * time_multiplier)
                    if estimated_minutes < 60:
                        time_str = f"約{int(estimated_minutes)}分"
                    else:
                        time_str = f"約{estimated_minutes/60:.0f}〜{estimated_minutes/60*1.5:.0f}時間"
                    console.print(f"[cyan]推定所要時間: {time_str}[/cyan]")
                    break
                except ValueError:
                    console.print("[red]無効な日付形式です。YYYY-MM-DD形式で入力してください。[/red]")

    if choice == "4":  # 更新モード
        settings['mode'] = 'update'
        settings['mode_name'] = '更新'
        # 前回のセットアップ情報を引き継ぐ
        settings['last_setup'] = last_setup
        # 前回の取得日から開始
        last_date = datetime.fromisoformat(last_setup['timestamp'])
        settings['from_date'] = last_date.strftime("%Y%m%d")
        # 前回のデータ種別を引き継ぐ
        settings['update_specs'] = last_setup.get('specs', [])

        # 前回のDB設定を引き継ぐ
        settings['db_type'] = last_setup.get('db_type', 'sqlite')
        settings['db_path'] = last_setup.get('db_path', 'data/keiba.db')
        if settings['db_type'] == 'postgresql':
            settings['pg_host'] = last_setup.get('pg_host', 'localhost')
            settings['pg_port'] = last_setup.get('pg_port', 5432)
            settings['pg_database'] = last_setup.get('pg_database', 'keiba')
            settings['pg_user'] = last_setup.get('pg_user', 'postgres')
            # パスワードは環境変数から取得、なければ入力を求める
            settings['pg_password'] = os.environ.get('PGPASSWORD', '')
            if not settings['pg_password']:
                console.print()
                console.print("[yellow]PostgreSQLパスワードが必要です[/yellow]")
                settings['pg_password'] = Prompt.ask("パスワード", password=True)

        # 更新範囲を表示
        console.print()
        console.print(Panel("[bold]更新情報[/bold]", border_style="yellow"))

        update_info = Table(show_header=False, box=None, padding=(0, 1))
        update_info.add_column("Key", style="dim")
        update_info.add_column("Value", style="white")

        update_info.add_row("前回モード", last_setup.get('mode_name', '不明'))
        update_info.add_row("前回取得日時", last_date.strftime("%Y-%m-%d %H:%M"))
        update_info.add_row("更新範囲", f"{settings['from_date']} 〜 {settings['to_date']}")
        specs_str = ", ".join(last_setup.get('specs', []))
        update_info.add_row("対象データ", specs_str if len(specs_str) <= 40 else specs_str[:37] + "...")
        # DB情報を表示
        if settings['db_type'] == 'postgresql':
            db_info = f"PostgreSQL ({settings['pg_user']}@{settings['pg_host']}:{settings['pg_port']}/{settings['pg_database']})"
        else:
            db_info = f"SQLite ({settings['db_path']})"
        update_info.add_row("データベース", db_info)

        console.print(update_info)

    console.print()

    # 時系列オッズ取得オプション
    console.print("[bold]3. 時系列オッズ（オッズ変動履歴）[/bold]")
    console.print()

    data_source = settings.get('data_source', 'jra')
    if data_source == 'nar':
        table_name = "NL_RA_NAR"
        source_name = "地方競馬（NAR）"
    else:
        table_name = "NL_RA"
        source_name = "中央競馬（JRA）"

    console.print(Panel(
        "[bold]時系列オッズ（オッズ変動履歴）について[/bold]\n\n"
        "発売開始から締切までのオッズ推移を記録するデータです。\n"
        "例: 発売開始時10倍 → 締切時3倍 のような変化を追跡できます。\n\n"
        "[cyan]取得条件:[/cyan]\n"
        f"  - データソース: {source_name}\n"
        "  - 公式サポート期間: 過去1年間\n"
        "  - TS_O1〜O6テーブルに保存\n\n"
        "[yellow]注: 1年以上前のデータも保存されている場合がありますが、\n"
        "公式サポート外のため取得できない可能性があります。[/yellow]\n\n"
        f"[dim]時系列オッズ取得には回次・日次情報（{table_name}）が必要です。\n"
        f"{table_name}が不足している場合は、必要な期間のRACEデータを自動取得します。[/dim]",
        border_style="blue",
    ))
    console.print()
    settings['include_timeseries'] = Confirm.ask("時系列オッズを取得しますか？", default=False)
    if settings['include_timeseries']:
        # 期間選択
        console.print()
        console.print("[cyan]取得期間を選択してください:[/cyan]")

        ts_period_table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
        ts_period_table.add_column("No", style="cyan", width=3, justify="center")
        ts_period_table.add_column("期間", width=15)
        ts_period_table.add_column("説明", width=40)

        ts_period_table.add_row("1", "過去1ヶ月", "[dim]直近のオッズ変動のみ[/dim]")
        ts_period_table.add_row("2", "過去3ヶ月", "[green]短期分析向け（推奨）[/green]")
        ts_period_table.add_row("3", "過去6ヶ月", "[dim]中期分析向け[/dim]")
        ts_period_table.add_row("4", "過去12ヶ月", "[dim]1年分（公式サポート期間）[/dim]")
        ts_period_table.add_row("5", "カスタム", "[yellow]任意の期間を指定（公式サポート外の可能性あり）[/yellow]")

        console.print(ts_period_table)
        console.print()

        ts_choice = Prompt.ask("期間を選択", choices=["1", "2", "3", "4", "5"], default="2")

        if ts_choice == "5":
            # カスタム期間入力
            today = datetime.now()

            console.print()
            console.print("[yellow]カスタム期間を指定します[/yellow]")
            console.print("[dim]注: 1年以上前のデータは公式サポート外です。取得できない場合があります。[/dim]")
            console.print()

            while True:
                ts_from_input = Prompt.ask("開始日 (YYYY-MM-DD)", default=(today - timedelta(days=90)).strftime("%Y-%m-%d"))
                ts_from_str = ts_from_input.replace("-", "").replace("/", "")
                try:
                    ts_from_date = datetime.strptime(ts_from_str, "%Y%m%d")
                    if ts_from_date > today:
                        console.print("[red]未来の日付は指定できません。[/red]")
                        continue
                    settings['timeseries_from_date'] = ts_from_str
                    break
                except ValueError:
                    console.print("[red]無効な日付形式です。YYYY-MM-DD形式で入力してください。[/red]")

            while True:
                ts_to_input = Prompt.ask("終了日 (YYYY-MM-DD)", default=today.strftime("%Y-%m-%d"))
                ts_to_str = ts_to_input.replace("-", "").replace("/", "")
                try:
                    ts_to_date = datetime.strptime(ts_to_str, "%Y%m%d")
                    if ts_to_date > today:
                        console.print("[yellow]終了日を今日に設定します。[/yellow]")
                        ts_to_str = today.strftime("%Y%m%d")
                    if ts_to_date < ts_from_date:
                        console.print("[red]終了日は開始日より後にしてください。[/red]")
                        continue
                    settings['timeseries_to_date'] = ts_to_str
                    break
                except ValueError:
                    console.print("[red]無効な日付形式です。YYYY-MM-DD形式で入力してください。[/red]")

            # カスタム期間の場合はmonthsを0に設定（日付を直接使用）
            settings['timeseries_months'] = 0
            settings['timeseries_custom'] = True
            console.print(f"[dim]取得期間: {settings['timeseries_from_date'][:4]}/{settings['timeseries_from_date'][4:6]}/{settings['timeseries_from_date'][6:]} 〜 {settings['timeseries_to_date'][:4]}/{settings['timeseries_to_date'][4:6]}/{settings['timeseries_to_date'][6:]}[/dim]")
        else:
            ts_months_map = {"1": 1, "2": 3, "3": 6, "4": 12}
            settings['timeseries_months'] = ts_months_map[ts_choice]
            settings['timeseries_custom'] = False

            months = settings['timeseries_months']
            if months == 1:
                console.print(f"[dim]取得期間: 過去1ヶ月[/dim]")
            else:
                console.print(f"[dim]取得期間: 過去{months}ヶ月[/dim]")
    else:
        settings['timeseries_months'] = 0
        settings['timeseries_custom'] = False

    console.print()

    # 速報系データの取得
    console.print("[bold]4. 当日レース情報の取得[/bold]")
    console.print("[dim]レース当日に更新される情報を取得します。[/dim]")
    console.print("[dim]含まれる情報: 馬体重、出走取消、騎手変更、天候・馬場状態など[/dim]")
    console.print()
    settings['include_realtime'] = Confirm.ask("当日レース情報を取得しますか？", default=False)
    console.print()

    # バックグラウンド更新
    console.print("[bold]5. 自動更新サービス[/bold]")
    console.print("[dim]データを自動で最新に保つバックグラウンドサービスです。[/dim]")
    console.print("[dim]起動しておくと、新しいレース情報やオッズが自動的にDBに追加されます。[/dim]")
    console.print()

    # 既存のバックグラウンドプロセスをチェック
    is_running, running_pid = _check_background_updater_running()
    auto_start_enabled = _is_auto_start_enabled()

    if is_running:
        console.print(f"[yellow]注意: バックグラウンド更新が既に起動中です (PID: {running_pid})[/yellow]")
        console.print()
        console.print("  [cyan]1)[/cyan] そのまま継続（新しく起動しない）")
        console.print("  [cyan]2)[/cyan] 停止して新しく起動する")
        console.print("  [cyan]3)[/cyan] 停止のみ（起動しない）")
        console.print()

        bg_choice = Prompt.ask(
            "選択",
            choices=["1", "2", "3"],
            default="1"
        )

        if bg_choice == "1":
            settings['enable_background'] = False
            settings['keep_existing_background'] = True
            console.print("[dim]既存のプロセスを継続します[/dim]")
        elif bg_choice == "2":
            console.print("[cyan]既存のプロセスを停止中...[/cyan]")
            if _stop_background_updater(running_pid):
                console.print("[green]停止しました[/green]")
                settings['enable_background'] = True
            else:
                console.print("[red]停止に失敗しました。手動で停止してください。[/red]")
                settings['enable_background'] = False
        else:  # "3"
            console.print("[cyan]既存のプロセスを停止中...[/cyan]")
            if _stop_background_updater(running_pid):
                console.print("[green]停止しました[/green]")
            settings['enable_background'] = False
    else:
        settings['enable_background'] = Confirm.ask("バックグラウンド更新を開始しますか？", default=False)

    console.print()

    # 自動起動設定（バックグラウンドが有効または継続の場合のみ）
    if settings.get('enable_background') or settings.get('keep_existing_background'):
        console.print("[bold]6. Windows起動時の自動起動[/bold]")
        if auto_start_enabled:
            console.print("[dim]現在: [green]有効[/green] (Windowsスタートアップに登録済み)[/dim]")
        else:
            console.print("[dim]現在: [yellow]無効[/yellow][/dim]")
        console.print()

        if auto_start_enabled:
            if not Confirm.ask("自動起動を維持しますか？", default=True):
                if _disable_auto_start():
                    console.print("[dim]自動起動を無効化しました[/dim]")
                    settings['auto_start'] = False
                else:
                    console.print("[red]自動起動の無効化に失敗しました[/red]")
                    settings['auto_start'] = True
            else:
                settings['auto_start'] = True
        else:
            if Confirm.ask("Windows起動時に自動でバックグラウンド更新を開始しますか？", default=False):
                if _enable_auto_start():
                    console.print("[green]自動起動を設定しました[/green]")
                    settings['auto_start'] = True
                else:
                    console.print("[red]自動起動の設定に失敗しました[/red]")
                    settings['auto_start'] = False
            else:
                settings['auto_start'] = False

        console.print()
    elif not settings.get('enable_background') and auto_start_enabled:
        # バックグラウンドを無効にしたが、自動起動が設定されている場合
        console.print("[yellow]注意: 自動起動が設定されていますが、バックグラウンド更新は開始しません[/yellow]")
        if Confirm.ask("自動起動を無効化しますか？", default=True):
            if _disable_auto_start():
                console.print("[dim]自動起動を無効化しました[/dim]")
            else:
                console.print("[red]自動起動の無効化に失敗しました[/red]")
        console.print()

    # 確認
    console.print(Panel("[bold]設定確認[/bold]", border_style="blue"))

    confirm_table = Table(show_header=False, box=None, padding=(0, 1))
    confirm_table.add_column("Key", style="dim")
    confirm_table.add_column("Value", style="white")

    # データソース情報
    data_source = settings.get('data_source', 'jra')
    if data_source == 'nar':
        source_info = "[cyan]地方競馬（NAR/UmaConn）[/cyan]"
    else:
        source_info = "中央競馬（JRA）"
    confirm_table.add_row("データソース", source_info)

    # データベース情報
    if settings.get('db_type') == 'postgresql':
        db_info = f"PostgreSQL ({settings['pg_user']}@{settings['pg_host']}:{settings['pg_port']}/{settings['pg_database']})"
    else:
        db_info = f"SQLite ({settings.get('db_path', 'data/keiba.db')})"
    confirm_table.add_row("データベース", db_info)

    confirm_table.add_row("取得モード", settings['mode_name'])
    confirm_table.add_row("オッズ変動履歴", "[dim]自動更新で蓄積[/dim]")
    confirm_table.add_row("当日レース情報", "[green]取得する[/green]" if settings.get('include_realtime') else "[dim]取得しない[/dim]")
    if settings.get('keep_existing_background'):
        confirm_table.add_row("自動更新", "[cyan]起動中（継続）[/cyan]")
    else:
        confirm_table.add_row("自動更新", "[green]起動する[/green]" if settings.get('enable_background') else "[dim]起動しない[/dim]")
    if settings.get('auto_start'):
        confirm_table.add_row("PC起動時に自動起動", "[green]有効[/green]")

    console.print(confirm_table)
    console.print()

    if not Confirm.ask("[bold]この設定でセットアップを開始しますか？[/bold]", default=True):
        console.print("[yellow]キャンセルしました[/yellow]")
        sys.exit(0)

    # data_sourceはステップ0で設定済み
    return settings


def _interactive_setup_simple() -> dict:
    """シンプルな対話形式設定"""
    print("=" * 60)
    print("JLTSQL セットアップ")
    print("=" * 60)
    print()

    settings = {}

    # データソース選択
    print("0. データソース選択")
    print()
    print("   1) 中央競馬 (デフォルト) - JRA-VAN DataLab (JV-Link)")
    print("   2) 地方競馬 - 地方競馬DATA (UmaConn/NV-Link)")
    print("   3) 両方 - 中央競馬と地方競馬の両方を同時に取得")
    print()

    source_choice = input("選択 [1]: ").strip() or "1"

    if source_choice == "2":
        settings['data_source'] = 'nar'
        print("地方競馬（NAR）を使用します")
    elif source_choice == "3":
        settings['data_source'] = 'all'
        print("中央競馬（JRA）と地方競馬（NAR）の両方を使用します")
    else:
        settings['data_source'] = 'jra'
        print("中央競馬（JRA）を使用します")
    print()

    # データベース選択
    print("1. データベース選択")
    print()
    print("   1) SQLite (デフォルト) - ファイルベースのデータベース、設定不要")
    print("   2) PostgreSQL - 高性能データベース、サーバー設定が必要")
    print()

    db_choice = input("選択 [1]: ").strip() or "1"

    if db_choice == "2":
        # PostgreSQL
        settings['db_type'] = 'postgresql'
        print()
        print("PostgreSQL接続設定:")
        print()

        while True:
            pg_host = input("ホスト [localhost]: ").strip() or "localhost"
            pg_port = input("ポート [5432]: ").strip() or "5432"
            pg_port = int(pg_port)
            pg_database = input("データベース名 [keiba]: ").strip() or "keiba"
            pg_user = input("ユーザー名 [postgres]: ").strip() or "postgres"

            import getpass
            pg_password = getpass.getpass("パスワード [postgres]: ") or "postgres"

            print()
            print("データベース確認中...")

            # データベースの存在確認と作成
            status, message = _check_postgresql_database(
                pg_host, pg_port, pg_database, pg_user, pg_password
            )

            if status == "created":
                # 新規作成成功
                print(f"[OK] {message}")
                settings['pg_host'] = pg_host
                settings['pg_port'] = pg_port
                settings['pg_database'] = pg_database
                settings['pg_user'] = pg_user
                settings['pg_password'] = pg_password
                break

            elif status == "exists":
                # 既存DBがある場合は選択肢を表示
                print(f"[!] {message}")
                print()
                print("  1) 既存データを保持して更新（追加インポート）")
                print("  2) データベースを再作成（全データ削除）")
                print("  3) 別のデータベース名を指定")
                print()
                db_action = input("選択 [1]: ").strip() or "1"

                if db_action == "1":
                    # 既存DBをそのまま使用
                    print("既存データベースを使用します")
                    settings['pg_host'] = pg_host
                    settings['pg_port'] = pg_port
                    settings['pg_database'] = pg_database
                    settings['pg_user'] = pg_user
                    settings['pg_password'] = pg_password
                    break
                elif db_action == "2":
                    # DROP & CREATE
                    print("データベースを再作成中...")
                    success, drop_msg = _drop_postgresql_database(
                        pg_host, pg_port, pg_database, pg_user, pg_password
                    )
                    if success:
                        print(f"[OK] {drop_msg}")
                        settings['pg_host'] = pg_host
                        settings['pg_port'] = pg_port
                        settings['pg_database'] = pg_database
                        settings['pg_user'] = pg_user
                        settings['pg_password'] = pg_password
                        break
                    else:
                        print(f"[NG] 再作成失敗: {drop_msg}")
                        # ループ継続して再入力
                elif db_action == "3":
                    # 別のDB名を指定（ループ継続）
                    continue

            else:  # status == "error"
                print(f"[NG] {message}")
                print()
                print("PostgreSQLのインストール・設定方法:")
                print("  1. https://www.postgresql.org/download/")
                print("  2. サービス起動: services.msc -> postgresql-x64-XX")
                print("  3. Pythonドライバ: pip install pg8000")
                print()
                retry = input("再試行しますか？ (y/n) [y]: ").strip().lower() or "y"
                if retry != "y":
                    print("SQLiteに切り替えます")
                    settings['db_type'] = 'sqlite'
                    settings['db_path'] = 'data/keiba.db'
                    break
    else:
        # SQLite (デフォルト)
        settings['db_type'] = 'sqlite'
        settings['db_path'] = 'data/keiba.db'
        print("SQLiteを使用します (data/keiba.db)")

    print()

    # サービスキーの確認（データソースに応じてJV-Link/NV-Linkをチェック）
    data_source = settings.get('data_source', 'jra')
    if data_source == 'nar':
        print("2. NV-Link（UmaConn）サービスキー確認")
    elif data_source == 'all':
        print("2. JV-Link & NV-Link サービスキー確認")
    else:
        print("2. JV-Link サービスキー確認")
    print()

    # 詳細チェックを実行
    check_result = _check_service_key_detailed(data_source)

    if data_source == 'all':
        # 両方選択時は部分成功を許可
        if check_result['jra_valid']:
            print(f"  [OK] JRA: {check_result['jra_msg']}")
        else:
            print(f"  [NG] JRA: {check_result['jra_msg']}")

        if check_result['nar_valid']:
            print(f"  [OK] NAR: {check_result['nar_msg']}")
        else:
            print(f"  [NG] NAR: {check_result['nar_msg']}")

        print()

        # 少なくとも1つ利用可能ならば続行を提案
        if check_result['available_sources']:
            if not check_result['all_valid']:
                # 部分成功の場合
                available_names = []
                if 'jra' in check_result['available_sources']:
                    available_names.append('中央競馬（JRA）')
                if 'nar' in check_result['available_sources']:
                    available_names.append('地方競馬（NAR）')

                print(f"⚠️  {' と '.join(available_names)} のみ利用可能です")
                print()

                response = input("利用可能なソースのみで続行しますか？ (y/n) [y]: ").strip().lower() or "y"
                if response == "y":
                    # 利用可能なソースのみに変更
                    if len(check_result['available_sources']) == 1:
                        settings['data_source'] = check_result['available_sources'][0]
                        source_name = '中央競馬（JRA）' if settings['data_source'] == 'jra' else '地方競馬（NAR）'
                        print(f"{source_name} のみで続行します")
                    # 両方利用可能な場合はそのまま（このケースは発生しないはずだがフォールバック）
                else:
                    print("[NG] セットアップを中止します。")
                    sys.exit(1)
        else:
            # 両方とも利用不可
            print("  JRA-VAN DataLab と UmaConn のサービスキーを設定してください")
            print("  JRA: https://jra-van.jp/dlb/")
            print("  NAR: https://www.umaconn.com/")
            print()
            print("[NG] セットアップを中止します。")
            sys.exit(1)
    else:
        # jra または nar の単独選択時
        if check_result['all_valid']:
            message = check_result['jra_msg'] if data_source == 'jra' else check_result['nar_msg']
            print(f"  [OK] {message}")
        else:
            message = check_result['jra_msg'] if data_source == 'jra' else check_result['nar_msg']
            print(f"  [NG] {message}")
            print()
            if data_source == 'nar':
                print("  UmaConn（地方競馬DATA）ソフトウェアでサービスキーを設定してください")
                print("  https://www.umaconn.com/")
            else:
                print("  JRA-VAN DataLabソフトウェアでサービスキーを設定してください")
                print("  https://jra-van.jp/dlb/")
            print()
            print("[NG] セットアップを中止します。")
            sys.exit(1)

    print()

    # 前回セットアップ履歴を確認
    last_setup = _load_setup_history()

    # セットアップモード
    print("3. セットアップモードを選択してください:")
    print()
    print("   No  モード  対象データ                                期間")
    print("   ──────────────────────────────────────────────────────────────")
    print("   1)  簡易    RACE,DIFF (レース結果・確定オッズ・馬情報)")
    print("   2)  標準    簡易+BLOD,YSCH,TOKU,SLOP等 (血統・調教等)")
    print("   3)  フル    標準+MING,WOOD,COMM (マイニング・解説等)")
    if last_setup:
        last_date = datetime.fromisoformat(last_setup['timestamp'])
        print(f"   4)  更新    前回({last_setup.get('mode_name', '?')})と同じ          前回({last_date.strftime('%Y-%m-%d')})以降")
    print()

    valid_choices = ["1", "2", "3"]
    if last_setup:
        valid_choices.append("4")

    choice = input("選択 [1]: ").strip() or "1"
    if choice not in valid_choices:
        choice = "1"

    today = datetime.now()
    settings['to_date'] = today.strftime("%Y%m%d")

    if choice == "1":
        settings['mode'] = 'simple'
        settings['mode_name'] = '簡易'
    elif choice == "2":
        settings['mode'] = 'standard'
        settings['mode_name'] = '標準'
    elif choice == "3":
        settings['mode'] = 'full'
        settings['mode_name'] = 'フル'

    # 更新モード以外は期間選択
    if choice in ["1", "2", "3"]:
        # モードに応じた所要時間の見積もり
        time_mult = {"1": 1.0, "2": 1.5, "3": 2.5}[choice]

        def fmt_time(base_min):
            m = base_min * time_mult
            if m < 60:
                return f"約{int(m)}分"
            else:
                return f"約{m/60:.0f}〜{m/60*1.5:.0f}時間"

        print()
        print("取得期間を選択してください:")
        print("※セットアップモードでは調教データ等が全期間分取得されます")
        print()
        print(f"   1)  直近1週間   デバッグ用 ({fmt_time(30)})")
        print(f"   2)  直近1ヶ月   短期テスト ({fmt_time(60)})")
        print(f"   3)  直近1年     実用的 ({fmt_time(180)})")
        print(f"   4)  直近5年     中長期分析 ({fmt_time(480)})")
        print(f"   5)  全期間      1986年〜 ({fmt_time(960)})")
        print(f"   6)  カスタム    日付を指定")
        print()

        period_choice = input("選択 [3]: ").strip() or "3"
        if period_choice not in ["1", "2", "3", "4", "5", "6"]:
            period_choice = "3"

        if period_choice == "1":
            settings['from_date'] = (today - timedelta(days=7)).strftime("%Y%m%d")
        elif period_choice == "2":
            settings['from_date'] = (today - timedelta(days=30)).strftime("%Y%m%d")
        elif period_choice == "3":
            settings['from_date'] = (today - timedelta(days=365)).strftime("%Y%m%d")
        elif period_choice == "4":
            settings['from_date'] = (today - timedelta(days=365*5)).strftime("%Y%m%d")
        elif period_choice == "5":
            settings['from_date'] = "19860101"
        else:
            # カスタム日付入力
            print()
            print("開始日を入力してください")
            print("形式: YYYY-MM-DD または YYYYMMDD (例: 2020-01-01)")
            print()

            while True:
                from_input = input("開始日 [2020-01-01]: ").strip() or "2020-01-01"
                # ハイフンを除去
                from_date_str = from_input.replace("-", "").replace("/", "")
                try:
                    # 日付として有効か確認
                    from_date = datetime.strptime(from_date_str, "%Y%m%d")
                    if from_date < datetime(1986, 1, 1):
                        print("1986年より前のデータはありません。1986-01-01に設定します。")
                        from_date_str = "19860101"
                    elif from_date > today:
                        print("未来の日付は指定できません。")
                        continue
                    settings['from_date'] = from_date_str

                    # 所要時間を計算して表示
                    # セットアップモードでは調教データ等が全期間分取得されるため基準時間を増加
                    days_diff = (today - datetime.strptime(from_date_str, "%Y%m%d")).days
                    estimated_minutes = (days_diff / 365) * 180 * time_mult  # 1年あたり180分
                    # 最低30分（調教データ等の固定オーバーヘッド）
                    estimated_minutes = max(estimated_minutes, 30 * time_mult)
                    if estimated_minutes < 60:
                        time_str = f"約{int(estimated_minutes)}分"
                    else:
                        time_str = f"約{estimated_minutes/60:.0f}〜{estimated_minutes/60*1.5:.0f}時間"
                    print(f"推定所要時間: {time_str}")
                    break
                except ValueError:
                    print("無効な日付形式です。YYYY-MM-DD形式で入力してください。")

    if choice == "4":  # 更新モード
        settings['mode'] = 'update'
        settings['mode_name'] = '更新'
        settings['last_setup'] = last_setup
        last_date = datetime.fromisoformat(last_setup['timestamp'])
        settings['from_date'] = last_date.strftime("%Y%m%d")
        settings['update_specs'] = last_setup.get('specs', [])

        # 前回のDB設定を引き継ぐ
        settings['db_type'] = last_setup.get('db_type', 'sqlite')
        settings['db_path'] = last_setup.get('db_path', 'data/keiba.db')
        if settings['db_type'] == 'postgresql':
            settings['pg_host'] = last_setup.get('pg_host', 'localhost')
            settings['pg_port'] = last_setup.get('pg_port', 5432)
            settings['pg_database'] = last_setup.get('pg_database', 'keiba')
            settings['pg_user'] = last_setup.get('pg_user', 'postgres')
            # パスワードは環境変数から取得、なければ入力を求める
            settings['pg_password'] = os.environ.get('PGPASSWORD', '')
            if not settings['pg_password']:
                import getpass
                print()
                print("[PostgreSQLパスワードが必要です]")
                settings['pg_password'] = getpass.getpass("パスワード: ")

        # 更新範囲を表示
        print()
        print("  --- 更新情報 ---")
        print(f"  前回モード:   {last_setup.get('mode_name', '不明')}")
        print(f"  前回取得日時: {last_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"  更新範囲:     {settings['from_date']} 〜 {settings['to_date']}")
        specs_str = ", ".join(last_setup.get('specs', []))
        print(f"  対象データ:   {specs_str[:50]}{'...' if len(specs_str) > 50 else ''}")
        # DB情報を表示
        if settings['db_type'] == 'postgresql':
            db_info = f"PostgreSQL ({settings['pg_user']}@{settings['pg_host']}:{settings['pg_port']}/{settings['pg_database']})"
        else:
            db_info = f"SQLite ({settings['db_path']})"
        print(f"  データベース: {db_info}")

    print()

    # 時系列オッズ取得オプション
    print("3. 時系列オッズ（オッズ変動履歴）")
    print()

    data_source = settings.get('data_source', 'jra')
    if data_source == 'nar':
        table_name = "NL_RA_NAR"
        source_name = "地方競馬（NAR）"
    else:
        table_name = "NL_RA"
        source_name = "中央競馬（JRA）"

    print("   ┌────────────────────────────────────────────────────────┐")
    print("   │ 時系列オッズ（オッズ変動履歴）について                 │")
    print("   │                                                        │")
    print("   │ 発売開始から締切までのオッズ推移を記録するデータです。 │")
    print("   │ 例: 発売開始時10倍 → 締切時3倍 のような変化を追跡     │")
    print("   │                                                        │")
    print("   │ 取得条件:                                              │")
    print(f"   │   - データソース: {source_name:<33}│")
    print("   │   - 公式サポート期間: 過去1年間                        │")
    print("   │   - TS_O1〜O6テーブルに保存                            │")
    print(f"   │   - {table_name}不足時は自動でRACEデータを取得{' ' * (22 - len(table_name))}│")
    print("   │                                                        │")
    print("   │ 注: 1年以上前のデータも保存されている場合がありますが、│")
    print("   │     公式サポート外のため取得できない可能性があります。 │")
    print("   └────────────────────────────────────────────────────────┘")
    print()
    print("時系列オッズを取得しますか？ [y/N]: ", end="")
    timeseries_choice = input().strip().lower()
    settings['include_timeseries'] = timeseries_choice in ('y', 'yes')
    if settings['include_timeseries']:
        # 期間選択
        print()
        print("   取得期間を選択してください:")
        print("   1) 過去1ヶ月  - 直近のオッズ変動のみ")
        print("   2) 過去3ヶ月  - 短期分析向け（推奨）")
        print("   3) 過去6ヶ月  - 中期分析向け")
        print("   4) 過去12ヶ月 - 1年分（公式サポート期間）")
        print("   5) カスタム   - 任意の期間を指定（公式サポート外の可能性あり）")
        print()
        print("   期間を選択 [1-5] (デフォルト: 2): ", end="")
        ts_period_input = input().strip()

        if ts_period_input == "5":
            # カスタム期間入力
            today = datetime.now()

            print()
            print("   カスタム期間を指定します")
            print("   注: 1年以上前のデータは公式サポート外です。取得できない場合があります。")
            print()

            while True:
                default_from = (today - timedelta(days=90)).strftime("%Y-%m-%d")
                print(f"   開始日 (YYYY-MM-DD) [{default_from}]: ", end="")
                ts_from_input = input().strip()
                if not ts_from_input:
                    ts_from_input = default_from
                ts_from_str = ts_from_input.replace("-", "").replace("/", "")
                try:
                    ts_from_date = datetime.strptime(ts_from_str, "%Y%m%d")
                    if ts_from_date > today:
                        print("   [エラー] 未来の日付は指定できません。")
                        continue
                    settings['timeseries_from_date'] = ts_from_str
                    break
                except ValueError:
                    print("   [エラー] 無効な日付形式です。YYYY-MM-DD形式で入力してください。")

            while True:
                default_to = today.strftime("%Y-%m-%d")
                print(f"   終了日 (YYYY-MM-DD) [{default_to}]: ", end="")
                ts_to_input = input().strip()
                if not ts_to_input:
                    ts_to_input = default_to
                ts_to_str = ts_to_input.replace("-", "").replace("/", "")
                try:
                    ts_to_date = datetime.strptime(ts_to_str, "%Y%m%d")
                    if ts_to_date > today:
                        print("   [注意] 終了日を今日に設定します。")
                        ts_to_str = today.strftime("%Y%m%d")
                    if ts_to_date < ts_from_date:
                        print("   [エラー] 終了日は開始日より後にしてください。")
                        continue
                    settings['timeseries_to_date'] = ts_to_str
                    break
                except ValueError:
                    print("   [エラー] 無効な日付形式です。YYYY-MM-DD形式で入力してください。")

            settings['timeseries_months'] = 0
            settings['timeseries_custom'] = True
            print(f"   -> 取得期間: {settings['timeseries_from_date'][:4]}/{settings['timeseries_from_date'][4:6]}/{settings['timeseries_from_date'][6:]} 〜 {settings['timeseries_to_date'][:4]}/{settings['timeseries_to_date'][4:6]}/{settings['timeseries_to_date'][6:]}")
        elif ts_period_input in ('1', '2', '3', '4'):
            ts_months_map = {"1": 1, "2": 3, "3": 6, "4": 12}
            settings['timeseries_months'] = ts_months_map[ts_period_input]
            settings['timeseries_custom'] = False

            months = settings['timeseries_months']
            if months == 1:
                print(f"   -> 過去1ヶ月の時系列オッズを取得します")
            else:
                print(f"   -> 過去{months}ヶ月の時系列オッズを取得します")
        else:
            # デフォルト: 3ヶ月
            settings['timeseries_months'] = 3
            settings['timeseries_custom'] = False
            print(f"   -> 過去3ヶ月の時系列オッズを取得します")
    else:
        settings['timeseries_months'] = 0
        settings['timeseries_custom'] = False

    print()

    # 速報系データ
    print("4. 当日レース情報を取得しますか？")
    print("   レース当日に更新される情報（馬体重、出走取消、騎手変更など）")
    print("   [y/N]: ", end="")
    realtime_choice = input().strip().lower()
    settings['include_realtime'] = realtime_choice in ('y', 'yes')
    print()

    # バックグラウンド更新
    print("5. 自動更新サービスを起動しますか？")
    print("   データを自動で最新に保つバックグラウンドサービスです。")
    print("   起動しておくと、新しいレース情報やオッズが自動的にDBに追加されます。")
    print()

    # 既存のバックグラウンドプロセスをチェック
    is_running, running_pid = _check_background_updater_running()
    auto_start_enabled = _is_auto_start_enabled()

    if is_running:
        print(f"   [注意] バックグラウンド更新が既に起動中です (PID: {running_pid})")
        print()
        print("   1) そのまま継続（新しく起動しない）")
        print("   2) 停止して新しく起動する")
        print("   3) 停止のみ（起動しない）")
        print()
        bg_choice = input("   選択 [1]: ").strip() or "1"

        if bg_choice == "1":
            settings['enable_background'] = False
            settings['keep_existing_background'] = True
            print("   既存のプロセスを継続します")
        elif bg_choice == "2":
            print("   既存のプロセスを停止中...")
            if _stop_background_updater(running_pid):
                print("   停止しました")
                settings['enable_background'] = True
            else:
                print("   [NG] 停止に失敗しました。手動で停止してください。")
                settings['enable_background'] = False
        else:  # "3"
            print("   既存のプロセスを停止中...")
            if _stop_background_updater(running_pid):
                print("   停止しました")
            settings['enable_background'] = False
    else:
        print("   [y/N]: ", end="")
        bg_input = input().strip().lower()
        settings['enable_background'] = bg_input in ('y', 'yes')

    print()

    # 自動起動設定（バックグラウンドが有効または継続の場合のみ）
    if settings.get('enable_background') or settings.get('keep_existing_background'):
        print("6. Windows起動時の自動起動")
        if auto_start_enabled:
            print("   現在: 有効 (Windowsスタートアップに登録済み)")
            print("   自動起動を維持しますか？ [Y/n]: ", end="")
            keep_auto = input().strip().lower()
            if keep_auto in ('n', 'no'):
                if _disable_auto_start():
                    print("   自動起動を無効化しました")
                    settings['auto_start'] = False
                else:
                    print("   [NG] 自動起動の無効化に失敗しました")
                    settings['auto_start'] = True
            else:
                settings['auto_start'] = True
        else:
            print("   現在: 無効")
            print("   Windows起動時に自動でバックグラウンド更新を開始しますか？ [y/N]: ", end="")
            enable_auto = input().strip().lower()
            if enable_auto in ('y', 'yes'):
                if _enable_auto_start():
                    print("   自動起動を設定しました")
                    settings['auto_start'] = True
                else:
                    print("   [NG] 自動起動の設定に失敗しました")
                    settings['auto_start'] = False
            else:
                settings['auto_start'] = False
        print()
    elif not settings.get('enable_background') and auto_start_enabled:
        # バックグラウンドを無効にしたが、自動起動が設定されている場合
        print("   [注意] 自動起動が設定されていますが、バックグラウンド更新は開始しません")
        print("   自動起動を無効化しますか？ [Y/n]: ", end="")
        disable_auto = input().strip().lower()
        if disable_auto not in ('n', 'no'):
            if _disable_auto_start():
                print("   自動起動を無効化しました")
        print()

    # 確認
    print("-" * 60)
    print("設定確認:")
    # データベース情報
    if settings.get('db_type') == 'postgresql':
        db_info = f"PostgreSQL ({settings['pg_user']}@{settings['pg_host']}:{settings['pg_port']}/{settings['pg_database']})"
    else:
        db_info = f"SQLite ({settings.get('db_path', 'data/keiba.db')})"
    print(f"  データベース:     {db_info}")
    print(f"  取得モード:       {settings['mode_name']}")
    print(f"  オッズ変動履歴:   自動更新で蓄積")
    print(f"  当日レース情報:   {'取得する' if settings.get('include_realtime') else '取得しない'}")
    if settings.get('keep_existing_background'):
        print("  自動更新:         起動中（継続）")
    else:
        print(f"  自動更新:         {'起動する' if settings.get('enable_background') else '起動しない'}")
    if settings.get('auto_start'):
        print("  PC起動時に自動起動: 有効")
    print("-" * 60)
    print()

    confirm = input("この設定でセットアップを開始しますか？ [Y/n]: ").strip().lower()
    if confirm in ('n', 'no'):
        print("キャンセルしました")
        sys.exit(0)

    # data_sourceはステップ0で設定済み
    return settings


class QuickstartRunner:
    """完全自動セットアップ実行クラス（Claude Code風UI）"""

    # モード別データスペック定義
    # (スペック名, 説明, オプション)
    # オプション: 1=通常データ（差分）, 2=今週データ, 3=セットアップ（ダイアログ）, 4=分割セットアップ

    # 簡易モード: レース情報とマスタ情報のみ (option=1)
    # RACE: RA, SE, HR, H1, H6, O1-O6, WF, JG
    # DIFN: UM, KS, CH, BR, BN, RC + 地方・海外レース(RA, SE)
    SIMPLE_SPECS = [
        ("RACE", "レース情報", 1),
        ("DIFN", "蓄積系ソフト用蓄積情報", 1),
    ]

    # 標準モード: 簡易 + 付加情報 (option=1)
    STANDARD_SPECS = [
        ("TOKU", "特別登録馬", 1),
        ("RACE", "レース情報", 1),
        ("DIFN", "蓄積系ソフト用蓄積情報", 1),
        ("BLDN", "蓄積系ソフト用血統情報", 1),
        ("MING", "蓄積系ソフト用マイニング情報", 1),
        ("SLOP", "坂路調教情報", 1),
        ("WOOD", "ウッドチップ調教", 1),
        ("YSCH", "開催スケジュール", 1),
        ("HOSN", "競走馬市場取引価格情報", 1),
        ("HOYU", "馬名の意味由来情報", 1),
        ("COMM", "各種解説情報", 1),
    ]

    # フルモード: 標準 + オッズ (option=1)
    # 注意: オッズ(O1-O6)はRACEデータ種別に含まれる（レコード種別として）
    # RACE dataspecを指定すると RA,SE,HR,H1,H6,O1,O2,O3,O4,O5,O6,WF,JG が取得される
    FULL_SPECS = [
        ("TOKU", "特別登録馬", 1),
        ("RACE", "レース情報", 1),  # オッズ(O1-O6)もRACEに含まれる
        ("DIFN", "蓄積系ソフト用蓄積情報", 1),
        ("BLDN", "蓄積系ソフト用血統情報", 1),
        ("MING", "蓄積系ソフト用マイニング情報", 1),
        ("SLOP", "坂路調教情報", 1),
        ("WOOD", "ウッドチップ調教", 1),
        ("YSCH", "開催スケジュール", 1),
        ("HOSN", "競走馬市場取引価格情報", 1),
        ("HOYU", "馬名の意味由来情報", 1),
        ("COMM", "各種解説情報", 1),
    ]

    # 今週データモード: option=2で直近のレースデータのみ取得（高速）
    # 注意: option=2 は TOKU, RACE, TCVN, RCVN のみ対応
    UPDATE_SPECS = [
        ("TOKU", "特別登録馬", 2),
        ("RACE", "レース情報", 2),
        ("TCVN", "調教師変更情報", 2),
        ("RCVN", "騎手変更情報", 2),
    ]

    # JVRTOpenデータスペック（速報系・時系列）
    # 注意: JVRTOpenは蓄積系(JVOpen)とは異なるAPI

    # 速報系データ (0B1x, 0B4x, 0B5x) - レース確定情報・変更情報
    # 表5.1-1 JVRTOpen対応: 0B11, 0B12, 0B13, 0B14, 0B15, 0B17, 0B41, 0B42, 0B51
    SPEED_REPORT_SPECS = [
        ("0B11", "開催情報"),              # WE
        ("0B12", "レース情報"),            # RA, SE
        ("0B13", "データマイニング予想"),   # DM
        ("0B14", "出走取消・競走除外"),     # AV
        ("0B15", "払戻情報"),              # HR
        ("0B17", "対戦型データマイニング予想"),  # TM
        ("0B41", "騎手変更情報"),          # RC
        ("0B42", "調教師変更情報"),        # TC
        ("0B51", "コース情報"),            # CC
    ]

    # 時系列データ (0B2x-0B3x) - 継続更新オッズ・票数
    # 表5.1-1 JVRTOpen対応: 0B20, 0B31, 0B32, 0B33, 0B34, 0B35, 0B36
    TIME_SERIES_SPECS = [
        ("0B20", "票数情報"),              # H1, H6
        ("0B31", "複勝・枠連オッズ"),       # O1, O2
        ("0B32", "馬連オッズ"),            # O3
        ("0B33", "ワイドオッズ"),          # O4
        ("0B34", "馬単オッズ"),            # O5
        ("0B35", "3連複オッズ"),           # O6
        ("0B36", "3連単オッズ"),           # O6
    ]

    # 全リアルタイムスペック（後方互換性のため残す）
    REALTIME_SPECS = SPEED_REPORT_SPECS + TIME_SERIES_SPECS

    def __init__(self, settings: dict):
        self.settings = settings
        self.project_root = Path(__file__).parent.parent
        self.errors = []
        self.warnings = []
        self.stats = {
            'specs_success': 0,
            'specs_nodata': 0,      # データなし（正常）
            'specs_skipped': 0,     # 契約外などでスキップ
            'specs_failed': 0,      # 実際のエラー
        }
        # データベースパス設定
        db_path_setting = settings.get('db_path')
        if db_path_setting:
            self.db_path = Path(db_path_setting)
            if not self.db_path.is_absolute():
                self.db_path = self.project_root / self.db_path
        else:
            self.db_path = self.project_root / "data" / "keiba.db"

    def _create_database(self):
        """設定に基づいてデータベースハンドラを作成

        Returns:
            BaseDatabase: SQLiteDatabase または PostgreSQLDatabaseのインスタンス
        """
        from src.database.sqlite_handler import SQLiteDatabase
        from src.database.postgresql_handler import PostgreSQLDatabase
        from src.database.base import DatabaseError

        db_type = self.settings.get('db_type', 'sqlite')

        if db_type == 'postgresql':
            # PostgreSQL設定
            db_config = {
                'host': self.settings.get('pg_host', 'localhost'),
                'port': self.settings.get('pg_port', 5432),
                'database': self.settings.get('pg_database', 'keiba'),
                'user': self.settings.get('pg_user', 'postgres'),
                'password': self.settings.get('pg_password', ''),
            }
            try:
                return PostgreSQLDatabase(db_config)
            except Exception as e:
                raise DatabaseError(f"PostgreSQL接続に失敗しました: {e}")
        else:
            # SQLite設定（デフォルト）
            db_config = {"path": str(self.db_path)}
            return SQLiteDatabase(db_config)

    def run(self) -> int:
        """完全自動セットアップ実行"""
        if RICH_AVAILABLE:
            return self._run_rich()
        else:
            return self._run_simple()

    def _run_rich(self) -> int:
        """Rich UIで実行"""
        console.print()

        # 実行
        with Progress(
            SpinnerColumn(finished_text="[green]OK[/green]"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:

            # 1. 前提条件チェック
            task = progress.add_task("[cyan]前提条件チェック...", total=1)
            if not self._check_prerequisites_rich():
                progress.update(task, completed=1)
                self._print_summary_rich(success=False)
                return 1
            progress.update(task, completed=1)

            # 2. プロジェクト初期化
            task = progress.add_task("[cyan]初期化中...", total=1)
            if not self._run_init():
                progress.update(task, completed=1)
                self._print_summary_rich(success=False)
                return 1
            progress.update(task, completed=1)

            # 3. テーブル作成
            task = progress.add_task("[cyan]テーブル作成中...", total=1)
            if not self._run_create_tables():
                progress.update(task, completed=1)
                self._print_summary_rich(success=False)
                return 1
            progress.update(task, completed=1)

            # 4. インデックス作成
            task = progress.add_task("[cyan]インデックス作成中...", total=1)
            if not self._run_create_indexes():
                progress.update(task, completed=1)
                self._print_summary_rich(success=False)
                return 1
            progress.update(task, completed=1)

        # 5. データ取得（別のProgressで表示）
        # 蓄積系データ取得
        if not self._run_fetch_all_rich():
            self._print_summary_rich(success=False)
            return 1

        # 時系列オッズ取得（オプション）
        if self._should_fetch_timeseries():
            if not self._run_fetch_timeseries_rich():
                self.warnings.append("時系列オッズの取得に失敗（一部またはすべて）")

        # 速報系データ取得（オプション）
        if self._should_fetch_realtime():
            if not self._run_fetch_realtime_rich():
                self._print_summary_rich(success=False)
                return 1

        # 6. バックグラウンド更新
        if self.settings.get('enable_background', False):
            console.print()
            with console.status("[cyan]バックグラウンド更新を開始中...", spinner="dots"):
                if not self._run_background_updater():
                    self.warnings.append("バックグラウンド更新の起動に失敗")

        # 7. セットアップ履歴を保存
        specs = self._get_specs_for_mode()
        _save_setup_history(self.settings, specs)

        # 完了
        self._print_summary_rich(success=True)
        return 0

    def _check_prerequisites_rich(self) -> bool:
        """前提条件チェック（Rich版）"""
        has_error = False
        checks = []

        # Python バージョン
        python_version = sys.version_info
        if python_version >= (3, 10):
            checks.append(("Python", f"{python_version.major}.{python_version.minor}", True))
        else:
            checks.append(("Python", f"{python_version.major}.{python_version.minor} (要3.10+)", False))
            has_error = True

        # OS
        if sys.platform == "win32":
            checks.append(("OS", "Windows", True))
        else:
            checks.append(("OS", f"{sys.platform} (要Windows)", False))
            has_error = True

        # JV-Link
        try:
            import win32com.client
            win32com.client.Dispatch("JVDTLab.JVLink")
            checks.append(("JV-Link", "OK", True))
        except Exception:
            checks.append(("JV-Link", "未インストール", False))
            has_error = True

        # 結果表示
        for name, value, ok in checks:
            status = "[green]OK[/green]" if ok else "[red]NG[/red]"
            console.print(f"  [{status}] {name}: {value}")

        return not has_error

    def _get_specs_for_mode(self) -> list:
        """モードに応じたスペックリストを取得（蓄積系のみ）"""
        mode = self.settings.get('mode', 'simple')
        if mode == 'simple':
            specs = self.SIMPLE_SPECS.copy()
        elif mode == 'standard':
            specs = self.STANDARD_SPECS.copy()
        elif mode == 'update':
            # 更新モード: UPDATE_SPECSを使用（option=2で今週データのみ）
            specs = self.UPDATE_SPECS.copy()
        else:  # full
            specs = self.FULL_SPECS.copy()

        # --no-odds: オッズ系スペック(O1-O6)を除外
        if self.settings.get('no_odds'):
            specs = [(s, d, o) for s, d, o in specs if not s.startswith('O')]

        return specs

    def _should_fetch_realtime(self) -> bool:
        """速報系データを取得するかどうか"""
        return self.settings.get('include_realtime', False)

    def _should_fetch_timeseries(self) -> bool:
        """時系列オッズを取得するかどうか"""
        return self.settings.get('include_timeseries', False)

    def _get_races_from_db(self, from_date: str, to_date: str) -> list:
        """データベースから開催レース情報を取得（Kaiji/Nichiji含む）

        Args:
            from_date: 開始日 (YYYYMMDD)
            to_date: 終了日 (YYYYMMDD)

        Returns:
            [(date, jyo_code, kaiji, nichiji, race_num), ...] のリスト
            時系列オッズ用の16桁キー生成に必要な情報を含む
        """
        races = []
        try:
            db = self._create_database()

            # データソースに応じてテーブルを選択
            data_source_str = self.settings.get('data_source', 'jra')
            if data_source_str == 'nar':
                table_name = 'nl_ra_nar'
                table_name_upper = 'NL_RA_NAR'
            else:
                table_name = 'nl_ra'
                table_name_upper = 'NL_RA'

            with db:
                # NL_RA/NL_RA_NARテーブルから開催情報を取得（Kaiji/Nichiji含む）
                # Year + MonthDay で日付を構成
                # PostgreSQLでは printf の代わりに lpad を使用
                # pg8000では :name 形式のプレースホルダーを使用
                if db.get_db_type() == 'postgresql':
                    query = f"""
                        SELECT DISTINCT
                            year || lpad(monthday::text, 4, '0') as race_date,
                            jyocd,
                            kaiji,
                            nichiji,
                            racenum
                        FROM {table_name}
                        WHERE (year || lpad(monthday::text, 4, '0')) >= :from_date
                          AND (year || lpad(monthday::text, 4, '0')) <= :to_date
                        ORDER BY race_date, jyocd, racenum
                    """
                else:
                    query = f"""
                        SELECT DISTINCT
                            Year || printf('%04d', CAST(MonthDay AS INTEGER)) as race_date,
                            JyoCD,
                            Kaiji,
                            Nichiji,
                            RaceNum
                        FROM {table_name_upper}
                        WHERE (Year || printf('%04d', CAST(MonthDay AS INTEGER))) >= ?
                          AND (Year || printf('%04d', CAST(MonthDay AS INTEGER))) <= ?
                        ORDER BY race_date, JyoCD, RaceNum
                    """
                # PostgreSQLでは辞書形式、SQLiteではタプル形式でパラメータを渡す
                if db.get_db_type() == 'postgresql':
                    results = db.fetch_all(query, {'from_date': from_date, 'to_date': to_date})
                else:
                    results = db.fetch_all(query, (from_date, to_date))
                # fetch_all returns a list of dictionaries with lowercase keys for PostgreSQL
                # For consistency, we convert dict rows to tuple rows
                if db.get_db_type() == 'postgresql':
                    races = [
                        (
                            row.get('race_date'),
                            row.get('jyocd'),
                            int(row.get('kaiji')) if row.get('kaiji') else 1,
                            int(row.get('nichiji')) if row.get('nichiji') else 1,
                            int(row.get('racenum'))
                        )
                        for row in results
                    ]
                else:
                    # SQLite: keys are case-sensitive as defined in query
                    races = [
                        (
                            row.get('race_date'),
                            row.get('JyoCD'),
                            int(row.get('Kaiji')) if row.get('Kaiji') else 1,
                            int(row.get('Nichiji')) if row.get('Nichiji') else 1,
                            int(row.get('RaceNum'))
                        )
                        for row in results
                    ]
        except Exception as e:
            pass  # 開催情報取得エラーは無視（NL_RAにデータがない場合など）
        return races

    def _run_fetch_timeseries_rich(self) -> bool:
        """時系列オッズ取得（Rich UI）

        時系列オッズをTS_O1-O6テーブルに保存。
        NL_RA/NL_RA_NARから実際の開催情報を取得して、開催があるレースのみを対象に取得。
        蓄積系データ取得（_run_fetch_all_rich）と同じUIデザイン（JVLinkProgressDisplay）を使用。

        Note: JRA（中央競馬）とNAR（地方競馬）の両方に対応。
        """
        from datetime import datetime, timedelta
        from src.utils.progress import JVLinkProgressDisplay

        today = datetime.now()

        # カスタム日付設定か月数設定かを判定
        if self.settings.get('timeseries_custom', False):
            # カスタム期間が設定されている場合
            from_date = self.settings.get('timeseries_from_date')
            to_date = self.settings.get('timeseries_to_date')
            period_text = f"{from_date[:4]}/{from_date[4:6]}/{from_date[6:]} 〜 {to_date[:4]}/{to_date[4:6]}/{to_date[6:]}"
        else:
            # 月数で期間を計算（デフォルト3ヶ月に変更）
            months = self.settings.get('timeseries_months', 3)
            start_date = today - timedelta(days=months * 30)  # 概算
            from_date = start_date.strftime("%Y%m%d")
            to_date = today.strftime("%Y%m%d")

            # 期間の表示用テキスト
            if months == 1:
                period_text = "過去1ヶ月"
            elif months == 12:
                period_text = "過去1年間"
            else:
                period_text = f"過去{months}ヶ月"

        # 時系列オッズスペック（0B30-0B36）
        timeseries_specs = [
            ("0B30", "単勝オッズ"),
            ("0B31", "複勝・枠連オッズ"),
            ("0B32", "馬連オッズ"),
            ("0B33", "ワイドオッズ"),
            ("0B34", "馬単オッズ"),
            ("0B35", "3連複オッズ"),
            ("0B36", "3連単オッズ"),
        ]

        # NL_RAから実際の開催レースを取得（Kaiji/Nichiji含む）
        races = self._get_races_from_db(from_date, to_date)

        if not races:
            # NL_RAにデータがない場合は、自動的にRACEデータを取得
            console.print()
            console.print(Panel(
                "[bold cyan]NL_RAデータの自動取得[/bold cyan]\n\n"
                f"時系列オッズ取得に必要な開催情報（NL_RA）が不足しています。\n"
                f"期間 {from_date[:4]}/{from_date[4:6]}/{from_date[6:]} 〜 {to_date[:4]}/{to_date[4:6]}/{to_date[6:]} の\n"
                "RACEデータを自動的に取得します。\n\n"
                "[dim]これは時系列オッズ取得のために回次・日次情報を取得するために必要です。[/dim]",
                border_style="cyan",
            ))

            # 一時的に設定を保存して、RACE取得用の設定に変更
            original_from_date = self.settings.get('from_date')
            original_to_date = self.settings.get('to_date')
            self.settings['from_date'] = from_date
            self.settings['to_date'] = to_date

            try:
                # RACEデータを取得（NL_RAが含まれる）
                console.print("\n[bold]RACEデータ取得中...[/bold]")
                status, details = self._fetch_single_spec_with_progress("RACE", 4)

                if status == "success":
                    console.print(f"[green]✓ RACEデータ取得完了: {details.get('records_saved', 0):,}件[/green]")
                elif status == "nodata":
                    console.print("[yellow]⚠ 該当期間にRACEデータがありませんでした[/yellow]")
                else:
                    console.print(f"[red]✗ RACEデータ取得失敗: {details.get('error_message', '不明なエラー')}[/red]")

            finally:
                # 設定を元に戻す
                if original_from_date is not None:
                    self.settings['from_date'] = original_from_date
                if original_to_date is not None:
                    self.settings['to_date'] = original_to_date

            # NL_RAから再度レースを取得
            races = self._get_races_from_db(from_date, to_date)

            if not races:
                # それでもデータがない場合はスキップ
                console.print()
                console.print(Panel(
                    "[bold yellow]注意[/bold yellow]\n"
                    "RACEデータを取得しましたが、NL_RAに開催情報が見つかりませんでした。\n"
                    "[dim]該当期間にレースがない可能性があります。時系列オッズ取得をスキップします。[/dim]",
                    border_style="yellow",
                ))
                return True  # 警告のみで続行

        total_specs = len(timeseries_specs)
        total_races = len(races)
        # 全体の総アイテム数（スペック × レース数）
        total_items = total_specs * total_races

        console.print()
        console.print(Panel(
            f"[bold]時系列オッズ取得[/bold] ({total_specs}スペック × {total_races}レース)\n"
            f"[dim]期間: {from_date} 〜 {to_date}（{period_text}）[/dim]",
            border_style="yellow",
        ))

        try:
            from src.fetcher.realtime import RealtimeFetcher
            from src.realtime.updater import RealtimeUpdater
            from src.jvlink.constants import JYO_CODES, generate_time_series_full_key
            from src.nvlink.constants import NAR_JYO_CODES, generate_nar_time_series_full_key
            from src.utils.data_source import DataSource

            # データソースを取得
            data_source_str = self.settings.get('data_source', 'jra')
            if data_source_str == 'nar':
                data_source = DataSource.NAR
                jyo_codes = NAR_JYO_CODES
                generate_key = generate_nar_time_series_full_key
            else:
                data_source = DataSource.JRA
                jyo_codes = JYO_CODES
                generate_key = generate_time_series_full_key

            db = self._create_database()

            total_records = 0
            success_count = 0
            nodata_count = 0
            skipped_count = 0
            failed_count = 0
            global_processed = 0  # 全体の処理済みアイテム数
            cumulative_records = 0  # 累計レコード数（リアルタイム表示用）

            with db:
                fetcher = RealtimeFetcher(sid="JLTSQL", data_source=data_source)
                updater = RealtimeUpdater(db)

                # JVLinkProgressDisplayを使用してリッチな進捗表示
                progress = JVLinkProgressDisplay()

                with progress:
                    # ダウンロード進捗タスク
                    download_task = progress.add_download_task(
                        "時系列オッズ取得",
                        total=total_items,
                    )
                    # メイン処理タスク
                    main_task = progress.add_task(
                        "レコード処理",
                        total=total_items,
                    )

                    start_time = time.time()

                    # 各スペックを順番に処理
                    for spec_idx, (spec, desc) in enumerate(timeseries_specs, 1):
                        spec_records = 0
                        status = "success"
                        error_msg = ""

                        try:
                            # 開催レースごとに取得
                            for race_idx, race_info in enumerate(races, 1):
                                race_date, jyo_code, kaiji, nichiji, race_num = race_info
                                global_processed += 1

                                # 進捗表示を更新
                                track_name = jyo_codes.get(jyo_code, jyo_code)
                                progress.update_download(
                                    download_task,
                                    completed=global_processed,
                                    status=f"{spec} {track_name}{race_num}R",
                                )
                                progress.update(
                                    main_task,
                                    completed=global_processed,
                                    status=f"({global_processed}/{total_items})",
                                )

                                try:
                                    # 16桁フルキーを生成して取得
                                    full_key = generate_key(
                                        race_date, jyo_code, kaiji, nichiji, race_num
                                    )
                                    for record in fetcher.fetch(
                                        data_spec=spec,
                                        key=full_key,
                                        continuous=False,
                                    ):
                                        raw_buff = record.get("_raw", "")
                                        if raw_buff:
                                            updater.process_record(raw_buff, timeseries=True)
                                            spec_records += 1
                                            cumulative_records += 1

                                    # 統計を更新（リアルタイム）
                                    elapsed = time.time() - start_time
                                    speed = cumulative_records / elapsed if elapsed > 0 else 0
                                    progress.update_stats(
                                        fetched=cumulative_records,
                                        parsed=cumulative_records,
                                        skipped=skipped_count,
                                        failed=failed_count,
                                        speed=speed,
                                    )

                                except Exception as e:
                                    error_str = str(e)
                                    if '-111' in error_str or '-114' in error_str:
                                        # 契約外はスキップ
                                        status = "skipped"
                                        error_msg = "契約外"
                                        break
                                    # -1はデータなし（正常）
                                    elif '-1' not in error_str:
                                        # その他のエラーを記録
                                        status = "failed"
                                        error_msg = error_str[:80] if len(error_str) > 80 else error_str
                                        break

                        except Exception as e:
                            error_str = str(e)
                            if '-111' in error_str or '-114' in error_str or '契約' in error_str:
                                status = "skipped"
                                error_msg = "データ提供サービス契約外"
                            else:
                                status = "failed"
                                error_msg = error_str[:80]

                        # スペックごとの結果を集計
                        if status == "success":
                            if spec_records > 0:
                                success_count += 1
                            else:
                                nodata_count += 1
                            total_records += spec_records
                        elif status == "skipped":
                            skipped_count += 1
                            self.warnings.append(f"時系列{spec}: {error_msg}")
                            # 契約外の場合、残りのレースをスキップ
                            global_processed = spec_idx * total_races
                        else:
                            failed_count += 1

                        # スペック処理後の統計更新（スキップ/失敗時に表示を更新）
                        elapsed = time.time() - start_time
                        speed = cumulative_records / elapsed if elapsed > 0 else 0
                        progress.update_stats(
                            fetched=cumulative_records,
                            parsed=cumulative_records,
                            skipped=skipped_count,
                            failed=failed_count,
                            speed=speed,
                        )

                    # 最終の進捗更新
                    elapsed = time.time() - start_time
                    speed = cumulative_records / elapsed if elapsed > 0 else 0
                    progress.update_download(download_task, completed=total_items, status="完了")
                    progress.update(main_task, completed=total_items, status="完了")
                    progress.update_stats(
                        fetched=cumulative_records,
                        parsed=cumulative_records,
                        skipped=skipped_count,
                        failed=failed_count,
                        speed=speed,
                    )

            # 完了メッセージ
            elapsed = time.time() - start_time
            console.print(f"    [green]✓[/green] 完了: [bold]{cumulative_records:,}件[/bold]保存 [dim]({elapsed:.1f}秒)[/dim]")

            # 統計をself.statsに追加
            self.stats['timeseries_success'] = success_count
            self.stats['timeseries_nodata'] = nodata_count
            self.stats['timeseries_skipped'] = skipped_count
            self.stats['timeseries_failed'] = failed_count
            self.stats['timeseries_records'] = cumulative_records

            return (success_count + nodata_count) > 0

        except Exception as e:
            console.print(f"\n    [red]✗[/red] 初期化エラー")
            console.print(f"      [red]原因:[/red] {e}")
            self.errors.append(f"時系列オッズ取得エラー: {e}")
            return False

    def _run_fetch_all_rich(self) -> bool:
        """データ取得（Rich UI）- チェックボックス形式の進捗表示"""
        specs_to_fetch = self._get_specs_for_mode()

        historical_specs = len(specs_to_fetch)
        # 時系列オッズを含む場合は+7（0B30-0B36の7スペック）
        timeseries_specs = 7 if self._should_fetch_timeseries() else 0
        total_specs = historical_specs + timeseries_specs

        console.print()
        console.print(Panel(
            f"[bold]データ取得[/bold] ({historical_specs}スペック" +
            (f" + 時系列{timeseries_specs}スペック" if timeseries_specs > 0 else "") + ")",
            border_style="blue",
        ))
        console.print()

        # スペック一覧を□付きで表示（2列表示）
        spec_status = {}  # spec -> status
        for spec, description, option in specs_to_fetch:
            spec_status[spec] = "pending"

        # 最初にすべてのスペックを□で表示
        self._print_spec_list(specs_to_fetch, spec_status)

        # 各スペックを処理して結果を表示
        results = []
        for idx, (spec, description, option) in enumerate(specs_to_fetch, 1):
            start_time = time.time()
            status, details = self._fetch_single_spec_with_progress(spec, option)
            elapsed = time.time() - start_time

            if status == "success":
                self.stats['specs_success'] += 1
                saved = details.get('records_saved', 0)
                spec_status[spec] = "success"
                if saved > 0:
                    results.append(f"  [green]✓[/green] {spec}: {saved:,}件 ({elapsed:.1f}秒)")
                else:
                    results.append(f"  [green]✓[/green] {spec}: 完了 ({elapsed:.1f}秒)")
            elif status == "nodata":
                self.stats['specs_nodata'] += 1
                spec_status[spec] = "nodata"
                results.append(f"  [dim]-[/dim] {spec}: サーバーにデータなし")
            elif status == "skipped":
                self.stats['specs_skipped'] += 1
                spec_status[spec] = "skipped"
                results.append(f"  [yellow]⚠[/yellow] {spec}: 契約外")
            else:
                self.stats['specs_failed'] += 1
                spec_status[spec] = "failed"
                results.append(f"  [red]✗[/red] {spec}: エラー")
                if details.get('error_message'):
                    error_type = details.get('error_type', 'unknown')
                    error_label = self._get_error_label(error_type)
                    results.append(f"      [red]原因:[/red] [{error_label}] {details['error_message']}")

        # 更新されたチェックボックス一覧を表示
        console.print()
        self._print_spec_list(specs_to_fetch, spec_status)

        # 結果詳細を表示
        console.print()
        console.print("[dim]取得結果:[/dim]")
        for result in results:
            console.print(result)

        # 成功またはデータなしがあれば成功とみなす
        return (self.stats['specs_success'] + self.stats['specs_nodata']) > 0

    def _print_spec_list(self, specs: list, status_map: dict):
        """スペック一覧をチェックボックス形式で2列表示"""
        # ステータスに応じた記号
        def get_checkbox(status):
            if status == "success":
                return "[green]☑[/green]"
            elif status == "nodata":
                return "[dim]☐[/dim]"
            elif status == "skipped":
                return "[yellow]☐[/yellow]"
            elif status == "failed":
                return "[red]☒[/red]"
            else:  # pending
                return "[dim]□[/dim]"

        # 2列で表示
        items = [(spec, desc) for spec, desc, _ in specs]
        mid = (len(items) + 1) // 2

        for i in range(mid):
            left_spec, left_desc = items[i]
            left_check = get_checkbox(status_map.get(left_spec, "pending"))
            left_str = f"  {left_check} {left_spec:6} {left_desc[:12]:<12}"

            if i + mid < len(items):
                right_spec, right_desc = items[i + mid]
                right_check = get_checkbox(status_map.get(right_spec, "pending"))
                right_str = f"  {right_check} {right_spec:6} {right_desc[:12]:<12}"
            else:
                right_str = ""

            console.print(f"{left_str}{right_str}")

    def _print_summary_rich(self, success: bool):
        """サマリー出力（Rich版）"""
        console.print()

        if success:
            console.print(Panel(
                f"[bold green]{HORSE_EMOJI_HAPPY} セットアップ完了！[/bold green]\n"
                "[dim]お疲れ様でした[/dim]",
                border_style="green",
            ))

            # 統計
            stats_table = Table(show_header=False, box=None)
            stats_table.add_column("", style="dim")
            stats_table.add_column("")
            if self.stats['specs_success'] > 0:
                stats_table.add_row("取得成功", f"[green]{self.stats['specs_success']}[/green]")
            if self.stats['specs_nodata'] > 0:
                stats_table.add_row("データなし", f"[dim]{self.stats['specs_nodata']}[/dim]")
            if self.stats['specs_skipped'] > 0:
                stats_table.add_row("契約外", f"[yellow]{self.stats['specs_skipped']}[/yellow]")
            if self.stats['specs_failed'] > 0:
                stats_table.add_row("エラー", f"[red]{self.stats['specs_failed']}[/red]")
            console.print(stats_table)

            # 警告表示
            if self.warnings:
                console.print()
                console.print("[yellow]警告:[/yellow]")
                for warning in self.warnings[:5]:
                    console.print(f"  [dim]-[/dim] {warning}")

            # 次のステップ
            console.print()
            console.print("[dim]次のステップ:[/dim]")
            console.print("  [cyan]jltsql status[/cyan]    - ステータス確認")
            console.print("  [cyan]jltsql fetch[/cyan]     - 追加データ取得")
            if not self.settings.get('no_monitor', True):
                console.print("  [cyan]jltsql monitor --stop[/cyan] - 監視停止")

            # MCP Server案内（SQLite利用時のみ）
            db_type = self.settings.get('db_type', 'sqlite')
            if db_type == 'sqlite':
                console.print()
                console.print("[dim]Claude Code / Claude Desktop をお使いの方へ:[/dim]")
                console.print("  MCP Server をインストールすると、AIから直接DBにアクセスできます")
                mcp_url = "https://github.com/miyamamoto/jvlink-mcp-server"
                console.print(f"  [link={mcp_url}]{mcp_url}[/link]")
                # サイトを開くか確認（-yオプションでない場合のみ）
                if not self.settings.get('auto_yes', False):
                    console.print()
                    if Confirm.ask("  [cyan]サイトを開きますか？[/cyan]", default=False):
                        webbrowser.open(mcp_url)
                        console.print("  [green]ブラウザでサイトを開きました[/green]")
        else:
            console.print(Panel(
                f"[bold red]{HORSE_EMOJI_SAD} セットアップ失敗[/bold red]\n"
                "[dim]エラーを確認してください[/dim]",
                border_style="red",
            ))

            if self.errors:
                console.print()
                console.print("[red]エラー:[/red]")
                for error in self.errors[:5]:
                    if isinstance(error, dict):
                        spec = error.get('spec', 'unknown')
                        msg = error.get('message', 'unknown error')
                        console.print(f"  [dim]•[/dim] [bold]{spec}[/bold]: {msg}")
                    else:
                        # 古い形式のエラー（互換性のため）
                        safe_error = str(error)[:80]
                        console.print(f"  [dim]•[/dim] {safe_error}")

        console.print()

    # === シンプル版（richなしの場合）===

    def _run_simple(self) -> int:
        """シンプルなテキストUIで実行"""
        print()

        # 1. 前提条件
        print("[1/5] 前提条件チェック...")
        if not self._check_prerequisites_simple():
            return 1

        # 2. 初期化
        print("\n[2/5] 初期化中...")
        if not self._run_init():
            return 1
        print("  OK")

        # 3. テーブル作成
        print("\n[3/5] テーブル作成中...")
        if not self._run_create_tables():
            return 1
        print("  OK")

        # 4. インデックス作成
        print("\n[4/5] インデックス作成中...")
        if not self._run_create_indexes():
            return 1
        print("  OK")

        # 5. データ取得
        print("\n[5/5] データ取得中...")
        if not self._run_fetch_all_simple():
            return 1

        # 速報系データ取得（オプション）
        if self._should_fetch_realtime():
            print("\n[追加] 速報系データ取得中...")
            if not self._run_fetch_realtime_simple():
                return 1

        # 6. バックグラウンド更新
        if self.settings.get('enable_background', False):
            print("\nバックグラウンド更新を開始中...")
            self._run_background_updater()

        # 7. セットアップ履歴を保存
        specs = self._get_specs_for_mode()
        _save_setup_history(self.settings, specs)

        print("\n" + "=" * 60)
        print("セットアップ完了！")
        print("=" * 60)
        return 0

    def _check_prerequisites_simple(self) -> bool:
        """前提条件チェック（シンプル版）"""
        has_error = False

        v = sys.version_info
        if v >= (3, 10):
            print(f"  [OK] Python {v.major}.{v.minor}")
        else:
            print(f"  [NG] Python {v.major}.{v.minor} (3.10以上が必要)")
            has_error = True

        if sys.platform == "win32":
            print("  [OK] Windows")
        else:
            print(f"  [NG] {sys.platform} (Windowsが必要)")
            has_error = True

        try:
            import win32com.client
            win32com.client.Dispatch("JVDTLab.JVLink")
            print("  [OK] JV-Link")
        except Exception:
            print("  [NG] JV-Link (未インストール)")
            has_error = True

        return not has_error

    def _run_fetch_all_simple(self) -> bool:
        """データ取得（シンプル版）"""
        specs = self._get_specs_for_mode()

        total = len(specs)
        for idx, (spec, desc, option) in enumerate(specs, 1):
            print(f"  [{idx}/{total}] {spec}: {desc}...", end=" ", flush=True)

            status = self._fetch_single_spec(spec, option)

            if status == "success":
                self.stats['specs_success'] += 1
                print("OK")
            elif status == "nodata":
                self.stats['specs_nodata'] += 1
                print(f"(サーバーにデータなし)")
            elif status == "skipped":
                self.stats['specs_skipped'] += 1
                print("(契約外)")
            else:
                self.stats['specs_failed'] += 1
                print("NG")

            time.sleep(0.5)

        print(f"\n  取得成功: {self.stats['specs_success']}, データなし: {self.stats['specs_nodata']}, 契約外: {self.stats['specs_skipped']}, エラー: {self.stats['specs_failed']}")
        return (self.stats['specs_success'] + self.stats['specs_nodata']) > 0

    # === リアルタイムデータ取得（JVRTOpen）===

    def _run_fetch_realtime_rich(self) -> bool:
        """リアルタイムデータ取得（Rich UI）- 速報系 + 時系列"""
        speed_specs = self.SPEED_REPORT_SPECS
        time_specs = self.TIME_SERIES_SPECS
        total_specs = len(speed_specs) + len(time_specs)

        console.print()
        console.print(Panel(
            f"[bold]リアルタイムデータ取得[/bold] ({total_specs}スペック)\n"
            f"[dim]速報系: {len(speed_specs)}件 / 時系列: {len(time_specs)}件[/dim]\n"
            "[dim]過去約1週間分のデータを取得します[/dim]",
            border_style="yellow",
        ))

        # 速報系データ
        console.print("\n[bold cyan]【速報系データ】[/bold cyan]")
        for idx, (spec, description) in enumerate(speed_specs, 1):
            self._fetch_and_display_realtime(idx, len(speed_specs), spec, description)

        # 時系列データ
        console.print("\n[bold cyan]【時系列データ】[/bold cyan]")
        for idx, (spec, description) in enumerate(time_specs, 1):
            self._fetch_and_display_realtime(idx, len(time_specs), spec, description)

        return (self.stats['specs_success'] + self.stats['specs_nodata']) > 0

    def _fetch_and_display_realtime(self, idx: int, total: int, spec: str, description: str):
        """リアルタイムデータの取得と表示"""
        console.print(f"\n  [cyan]({idx}/{total})[/cyan] [bold]{spec}[/bold]: {description}")

        start_time = time.time()
        status, details = self._fetch_single_realtime_spec(spec)
        elapsed = time.time() - start_time

        if status == "success":
            self.stats['specs_success'] += 1
            saved = details.get('records_saved', 0)
            if saved > 0:
                console.print(f"    [green]OK[/green] 完了: [bold]{saved:,}件[/bold]保存 [dim]({elapsed:.1f}秒)[/dim]")
            else:
                console.print(f"    [green]OK[/green] 完了 [dim]({elapsed:.1f}秒)[/dim]")
        elif status == "nodata":
            self.stats['specs_nodata'] += 1
            console.print(f"    [dim]- {spec}: サーバーにデータなし[/dim] [dim]({elapsed:.1f}秒)[/dim]")
        elif status == "skipped":
            self.stats['specs_skipped'] += 1
            console.print(f"    [yellow]![/yellow] 契約外 [dim]({elapsed:.1f}秒)[/dim]")
        else:
            self.stats['specs_failed'] += 1
            console.print(f"    [red]X[/red] エラー [dim]({elapsed:.1f}秒)[/dim]")
            if details.get('error_message'):
                console.print(f"      [red]原因:[/red] {details['error_message']}")

    def _run_fetch_realtime_simple(self) -> bool:
        """リアルタイムデータ取得（シンプル版）- 速報系 + 時系列"""
        speed_specs = self.SPEED_REPORT_SPECS
        time_specs = self.TIME_SERIES_SPECS
        total = len(speed_specs) + len(time_specs)

        print(f"  リアルタイムデータ取得 ({total}スペック)")
        print(f"  速報系: {len(speed_specs)}件 / 時系列: {len(time_specs)}件")
        print("  過去約1週間分のデータを取得します")
        print()

        # 速報系データ
        print("  【速報系データ】")
        for idx, (spec, desc) in enumerate(speed_specs, 1):
            print(f"  [{idx}/{len(speed_specs)}] {spec}: {desc}...", end=" ", flush=True)
            status, _ = self._fetch_single_realtime_spec(spec)
            self._print_realtime_status(status, spec)
            time.sleep(0.3)

        # 時系列データ
        print("\n  【時系列データ】")
        for idx, (spec, desc) in enumerate(time_specs, 1):
            print(f"  [{idx}/{len(time_specs)}] {spec}: {desc}...", end=" ", flush=True)
            status, _ = self._fetch_single_realtime_spec(spec)
            self._print_realtime_status(status, spec)
            time.sleep(0.3)

        print(f"\n  取得成功: {self.stats['specs_success']}, データなし: {self.stats['specs_nodata']}, 契約外: {self.stats['specs_skipped']}, エラー: {self.stats['specs_failed']}")
        return (self.stats['specs_success'] + self.stats['specs_nodata']) > 0

    def _print_realtime_status(self, status: str, spec: str):
        """リアルタイム取得ステータスを表示"""
        if status == "success":
            self.stats['specs_success'] += 1
            print("OK")
        elif status == "nodata":
            self.stats['specs_nodata'] += 1
            print(f"(サーバーにデータなし)")
        elif status == "skipped":
            self.stats['specs_skipped'] += 1
            print("(契約外)")
        else:
            self.stats['specs_failed'] += 1
            print("NG")

    def _get_recent_race_dates(self, days: int = 7) -> list:
        """過去N日間の開催日（土日）を取得

        Args:
            days: 遡る日数（デフォルト: 7日間）

        Returns:
            list: YYYYMMDD形式の日付リスト（新しい順）
        """
        from datetime import datetime, timedelta

        race_dates = []
        now = datetime.now()

        for i in range(days):
            date = now - timedelta(days=i)
            # 競馬開催日は土曜(5)と日曜(6)
            if date.weekday() in (5, 6):
                race_dates.append(date.strftime("%Y%m%d"))

        return race_dates

    def _get_race_keys_for_date(self, date_str: str) -> list:
        """指定日の全レースキー（YYYYMMDDJJRR形式）を生成

        時系列データ（0B20, 0B31-0B36）用。
        各競馬場（中央10場）の全レース（1-12R）のkeyを生成。

        Args:
            date_str: YYYYMMDD形式の日付

        Returns:
            list: YYYYMMDDJJRR形式のキーリスト
        """
        # 競馬場コード: 01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京,
        #             06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉
        jyo_codes = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]
        race_nums = [f"{i:02d}" for i in range(1, 13)]  # 01-12

        keys = []
        for jyo in jyo_codes:
            for race in race_nums:
                keys.append(f"{date_str}{jyo}{race}")

        return keys

    def _fetch_single_realtime_spec(self, spec: str) -> tuple:
        """単一のリアルタイムスペックを取得（速報系/時系列共通）

        JVRTOpenにはkeyパラメータが必要。
        - 速報系(0B1x): YYYYMMDD形式（日付単位）
        - 時系列(0B2x-0B3x): YYYYMMDDJJRR形式（レース単位）
        過去1週間の開催日（土日）を対象にデータを取得する。

        Returns:
            tuple: (status, details)
                status: "success", "nodata", "skipped", "failed"
                details: dict with info
        """
        details = {
            'records_saved': 0,
            'error_message': None,
        }

        # 時系列データかどうか判定（0B20, 0B30-0B36）
        is_time_series = spec.startswith("0B2") or spec.startswith("0B3")

        try:
            from src.fetcher.realtime import RealtimeFetcher
            from src.importer.importer import DataImporter
            from src.utils.data_source import DataSource

            # データソースを取得
            data_source_str = self.settings.get('data_source', 'jra')
            if data_source_str == 'nar':
                data_source = DataSource.NAR
            else:
                data_source = DataSource.JRA

            # データベース接続
            db = self._create_database()

            # 過去1週間の開催日を取得
            race_dates = self._get_recent_race_dates(days=7)

            if not race_dates:
                return ("nodata", details)

            total_records = 0

            with db:
                fetcher = RealtimeFetcher(sid="JLTSQL", data_source=data_source)
                importer = DataImporter(db, batch_size=1000)

                for date_str in race_dates:
                    # 時系列データはレース単位のキーが必要
                    if is_time_series:
                        keys = self._get_race_keys_for_date(date_str)
                    else:
                        keys = [date_str]  # 速報系は日付単位

                    for key in keys:
                        records = []
                        try:
                            for record in fetcher.fetch(data_spec=spec, key=key, continuous=False):
                                records.append(record)
                        except Exception as e:
                            error_str = str(e)
                            # 契約外チェック
                            if '-111' in error_str or '-114' in error_str or '契約' in error_str:
                                return ("skipped", details)
                            # データなし (-1) は次のキーへ
                            if '-1' in error_str or 'no data' in error_str.lower():
                                continue
                            raise

                        if records:
                            # インポート
                            import_stats = importer.import_records(iter(records), auto_commit=True)
                            total_records += import_stats.get('records_imported', len(records))

                details['records_saved'] = total_records

                if total_records > 0:
                    return ("success", details)
                else:
                    return ("nodata", details)

        except Exception as e:
            error_str = str(e)
            # エラー種別判定
            # -111, -114, -115: 契約外データ種別
            if '-111' in error_str or '-114' in error_str or '-115' in error_str or '契約' in error_str:
                return ("skipped", details)
            if '-100' in error_str or 'サービスキー' in error_str:
                details['error_message'] = 'サービスキーが未設定です'
            elif 'JVRTOpen' in error_str:
                details['error_message'] = f'JVRTOpen エラー: {error_str}'
            else:
                details['error_message'] = str(e)[:100]
            return ("failed", details)

    # === 共通処理 ===

    def _run_init(self) -> bool:
        """プロジェクト初期化"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "src.cli.main", "init"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
            )
            if result.returncode != 0:
                self.errors.append(f"初期化失敗: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            self.errors.append(f"初期化エラー: {e}")
            return False

    def _run_create_tables(self) -> bool:
        """テーブル作成"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "src.cli.main", "create-tables"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60,
            )
            if result.returncode != 0:
                self.errors.append(f"テーブル作成失敗: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            self.errors.append(f"テーブル作成エラー: {e}")
            return False

    def _run_create_indexes(self) -> bool:
        """インデックス作成"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "src.cli.main", "create-indexes"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120,
            )
            if result.returncode != 0:
                self.errors.append(f"インデックス作成失敗: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            self.errors.append(f"インデックス作成エラー: {e}")
            return False

    # スピナーフレーム
    SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    # エラータイプの日本語ラベル
    ERROR_TYPE_LABELS = {
        'auth': 'JV-Link認証エラー',
        'connection': '接続エラー',
        'contract': '契約外',
        'timeout': 'タイムアウト',
        'parse': 'データ解析エラー',
        'db': 'データベースエラー',
        'permission': 'アクセス権限エラー',
        'disk': 'ディスク容量エラー',
        'exception': '予期しないエラー',
        'unknown': 'エラー',
    }

    def _get_error_label(self, error_type: str) -> str:
        """エラータイプのラベルを取得"""
        return self.ERROR_TYPE_LABELS.get(error_type, 'エラー')

    def _analyze_error(self, output: str, returncode: int, error_lines: list = None) -> tuple:
        """エラー出力を分析して具体的なエラータイプとメッセージを返す

        Args:
            output: 全出力テキスト
            returncode: プロセス終了コード
            error_lines: エラー関連の行のリスト（オプション）

        Returns:
            tuple: (error_type, error_message)
        """
        output_lower = output.lower()

        # エラー行が提供されている場合、それも検索対象に含める
        combined_errors = output
        if error_lines:
            combined_errors = '\n'.join(error_lines) + '\n' + output
            output_lower = combined_errors.lower()

        # JV-Link接続エラー
        if 'jvinit' in output_lower or 'jvlink' in output_lower:
            if '-100' in output or 'サービスキー未設定' in output:
                return ('auth', 'サービスキーが未設定です')
            elif '-101' in output or 'サービスキーが無効' in output:
                return ('auth', 'サービスキーが無効です')
            elif '-102' in output or '有効期限切れ' in output:
                return ('auth', 'サービスキーの有効期限が切れています')
            elif '-103' in output or 'サービス利用不可' in output:
                return ('auth', 'サービスが利用できません')
            else:
                return ('connection', 'JV-Link接続エラー - JRA-VAN DataLabソフトウェアを確認してください')

        # 契約外エラー
        if '-111' in output or '契約' in output or 'contract' in output_lower:
            return ('contract', 'データ提供サービス契約外です')

        # タイムアウトエラー
        if 'timeout' in output_lower or 'timed out' in output_lower:
            return ('timeout', 'データ取得がタイムアウトしました')

        # ネットワークエラー
        if 'connection' in output_lower and ('refused' in output_lower or 'failed' in output_lower):
            return ('connection', 'ネットワーク接続エラー - インターネット接続を確認してください')

        # パースエラー
        if 'parse' in output_lower or 'invalid data' in output_lower or 'decode' in output_lower:
            return ('parse', 'データ解析エラー - データ形式が不正です')

        # データベースエラー
        if 'database' in output_lower or 'sqlite' in output_lower:
            if 'lock' in output_lower:
                return ('db', 'データベースがロックされています - 他のプロセスが実行中の可能性があります')
            else:
                return ('db', 'データベースエラー')

        # ファイルシステムエラー
        if 'permission' in output_lower or 'access denied' in output_lower:
            return ('permission', 'ファイルアクセス権限エラー')

        if 'no space' in output_lower or 'disk full' in output_lower:
            return ('disk', 'ディスク容量不足')

        # 不明なエラー - エラー行があればそれを優先、なければ最後の数行を抽出
        if error_lines:
            # エラー行から最も有用な情報を抽出
            relevant_errors = []
            for line in error_lines[-5:]:  # 最後の5行まで
                # 一般的なログプレフィックスを除去
                cleaned = line
                for prefix in ['ERROR:', 'Error:', 'Exception:', 'エラー:']:
                    if prefix in cleaned:
                        cleaned = cleaned.split(prefix, 1)[1].strip()
                if cleaned and len(cleaned) > 10:  # 意味のある長さのメッセージ
                    relevant_errors.append(cleaned)

            if relevant_errors:
                error_snippet = ' | '.join(relevant_errors)[:200]
                return ('unknown', error_snippet)

        # エラー行がない場合、出力の最後の数行を抽出
        lines = output.strip().split('\n')
        last_lines = [line.strip() for line in lines[-3:] if line.strip() and not line.startswith('---')]
        if last_lines:
            error_snippet = ' | '.join(last_lines)[:200]
            return ('unknown', error_snippet)

        return ('unknown', f'終了コード {returncode}')

    def _fetch_single_spec_with_progress(self, spec: str, option: int) -> tuple:
        """単一データスペック取得（直接API呼び出し + JVLinkProgressDisplay）

        BatchProcessorを直接呼び出すことで、JVLinkProgressDisplayの
        リッチな進捗表示がそのまま動作します。

        Returns:
            tuple: (status, details)
                status: "success", "nodata", "skipped", "failed"
                details: dict with progress info
        """
        from src.database.schema import create_all_tables
        from src.importer.batch import BatchProcessor
        from src.jvlink.wrapper import JVLinkError
        from src.nvlink.wrapper import NVLinkError
        from src.fetcher.base import FetcherError

        details = {
            'download_count': 0,
            'read_count': 0,
            'records_parsed': 0,
            'records_saved': 0,
            'records_fetched': 0,
            'speed': '',
            'files_processed': 0,
            'total_files': 0,
            'error_type': None,
            'error_message': None,
        }

        # 日付範囲の検証
        from_date = self.settings['from_date']
        to_date = self.settings['to_date']
        if from_date > to_date:
            details['error_type'] = 'invalid_date_range'
            details['error_message'] = f'無効な日付範囲: from_date ({from_date}) > to_date ({to_date})'
            logger.error(details['error_message'])
            return ("failed", details)

        # option=2は特定のデータスペックのみ対応
        OPTION_2_SUPPORTED_SPECS = {"TOKU", "RACE", "TCVN", "RCVN"}
        if option == 2 and spec not in OPTION_2_SUPPORTED_SPECS:
            details['error_type'] = 'invalid_option'
            details['error_message'] = f'option=2 (今週データ) は {spec} に対応していません'
            logger.warning(details['error_message'])
            return ("skipped", details)

        # option=3/4（セットアップモード）は一部のスペックのみ対応
        # RACE, DIFF, BLOD等の主要スペックはoption=2対応
        # COMM, PARA等の補助スペックはoption=1のみ対応
        OPTION_4_SUPPORTED_SPECS = {
            "RACE", "DIFF", "BLOD", "SNAP", "SLOP", "WOOD",
            "YSCH", "HOSE", "HOYU", "CHOK", "KISI", "BRDR",
            "TOKU", "MING", "O1", "O2", "O3", "O4", "O5", "O6",
        }

        # option=1（差分データ）はJV-Link側の「最終取得時刻」以降のデータのみ返す
        # 初回セットアップや全データ取得にはoption=2（セットアップモード）を使用
        # ただし、option=2非対応スペックはoption=1のまま維持
        data_source_str = self.settings.get('data_source', 'jra')

        # NAR (NV-Link) では option 1 が正常動作しない（NVStatusが-203を返す既知の問題）
        # 原因: NVDTLabのセットアップ不完全、またはキャッシュの問題
        # 対策: NAR では常に option 2 を使用することで回避
        # 参考: docs/reference/error-codes.md#nvlink--203-エラー-地方競馬data
        if data_source_str == 'nar':
            if option == 1 or option == 2:
                option = 2  # NAR: ローカルデータのみ取得（option=2はファイルエラーになるため）
        elif option == 1 and spec in OPTION_4_SUPPORTED_SPECS:
            option = 4  # JRA: 分割セットアップモード（全データ取得）
        # option=2非対応スペックはoption=1で実行（差分データ）

        try:
            # 設定読み込み
            from src.utils.config import load_config
            config = load_config(str(self.project_root / "config" / "config.yaml"))

            # データベース接続
            database = self._create_database()

            with database:
                # テーブル作成（必要に応じて）
                data_source_str = self.settings.get('data_source', 'jra')
                try:
                    if data_source_str == 'nar':
                        # NAR用テーブルを作成
                        from src.database.schema_nar import get_nar_schemas
                        nar_schemas = get_nar_schemas()
                        for table_name, schema_sql in nar_schemas.items():
                            try:
                                database.execute(schema_sql)
                            except Exception:
                                pass  # Table might already exist
                    elif data_source_str == 'all':
                        # 両方のテーブルを作成
                        create_all_tables(database)  # JRA tables
                        from src.database.schema_nar import get_nar_schemas
                        nar_schemas = get_nar_schemas()
                        for table_name, schema_sql in nar_schemas.items():
                            try:
                                database.execute(schema_sql)
                            except Exception:
                                pass  # Table might already exist
                    else:
                        create_all_tables(database)
                except Exception:
                    pass  # 既存テーブルがあってもOK

                # DataSource enumに変換
                from src.utils.data_source import DataSource

                if data_source_str == 'all':
                    # 両方のソースからデータ取得（独立して処理、一方が失敗しても他方は続行）
                    jra_result = {}
                    nar_result = {}
                    jra_error = None
                    nar_error = None

                    # JRAデータ取得（エラーがあっても続行）
                    try:
                        jra_processor = BatchProcessor(
                            database=database,
                            sid=config.get("jvlink.sid", "JLTSQL"),
                            batch_size=1000,
                            service_key=config.get("jvlink.service_key"),
                            show_progress=True,
                            data_source=DataSource.JRA,
                        )
                        jra_result = jra_processor.process_date_range(
                            data_spec=spec,
                            from_date=self.settings['from_date'],
                            to_date=self.settings['to_date'],
                            option=option,
                        )
                    except Exception as e:
                        jra_error = str(e)
                        logger.warning(f"JRAデータ取得でエラーが発生しましたが、NARデータ取得を続行します: {jra_error}")

                    # NARデータ取得（JRAの成否に関わらず実行）
                    try:
                        nar_processor = BatchProcessor(
                            database=database,
                            sid=config.get("jvlink.sid", "JLTSQL"),
                            batch_size=1000,
                            service_key=config.get("jvlink.service_key"),
                            initialization_key=config.get("nvlink.initialization_key", "UNKNOWN"),
                            show_progress=True,
                            data_source=DataSource.NAR,
                        )
                        nar_result = nar_processor.process_date_range(
                            data_spec=spec,
                            from_date=self.settings['from_date'],
                            to_date=self.settings['to_date'],
                            option=option,
                        )
                    except Exception as e:
                        nar_error = str(e)
                        logger.warning(f"NARデータ取得でエラーが発生しました: {nar_error}")

                    # 結果を統合（両方失敗した場合のみエラー）
                    if jra_error and nar_error:
                        # 両方失敗 - エラーを報告
                        raise FetcherError(f"JRAとNAR両方のデータ取得に失敗しました。JRA: {jra_error[:50]}, NAR: {nar_error[:50]}")
                    elif jra_error:
                        # JRAのみ失敗 - 警告を追加してNARのみ使用
                        self.warnings.append(f"{spec}(JRA): データ取得失敗 - {jra_error[:50]}")
                        result = nar_result
                    elif nar_error:
                        # NARのみ失敗 - 警告を追加してJRAのみ使用
                        self.warnings.append(f"{spec}(NAR): データ取得失敗 - {nar_error[:50]}")
                        result = jra_result
                    else:
                        # 両方成功 - 結果を統合
                        result = {
                            'records_fetched': jra_result.get('records_fetched', 0) + nar_result.get('records_fetched', 0),
                            'records_parsed': jra_result.get('records_parsed', 0) + nar_result.get('records_parsed', 0),
                            'records_imported': jra_result.get('records_imported', 0) + nar_result.get('records_imported', 0),
                        }
                else:
                    data_source = DataSource.NAR if data_source_str == 'nar' else DataSource.JRA

                    # BatchProcessorを直接呼び出し（show_progress=Trueでリッチ進捗表示）
                    processor = BatchProcessor(
                        database=database,
                        sid=config.get("jvlink.sid", "JLTSQL"),
                        batch_size=1000,
                        service_key=config.get("jvlink.service_key"),
                        initialization_key=config.get("nvlink.initialization_key", "UNKNOWN") if data_source == DataSource.NAR else None,
                        show_progress=True,  # JVLinkProgressDisplayを有効化
                        data_source=data_source,
                    )

                    # データ取得実行
                    result = processor.process_date_range(
                        data_spec=spec,
                        from_date=self.settings['from_date'],
                        to_date=self.settings['to_date'],
                        option=option,
                    )

                # 結果をdetailsに反映
                details['records_fetched'] = result.get('records_fetched', 0)
                details['records_parsed'] = result.get('records_parsed', 0)
                details['records_saved'] = result.get('records_imported', 0)

                # 成功判定
                if result.get('records_fetched', 0) == 0:
                    return ("nodata", details)

                return ("success", details)

        except JVLinkError as e:
            error_code = getattr(e, 'error_code', None)
            error_str = str(e)

            # エラーコード別の判定
            if error_code == -111 or '契約' in error_str:
                details['error_type'] = 'contract'
                # オッズ系(O1-O6)は別契約が必要な場合がある
                if spec.startswith('O'):
                    details['error_message'] = 'オッズデータは別途契約が必要です'
                else:
                    details['error_message'] = 'データ提供サービス契約外です'
                self.warnings.append(f"{spec}: {details['error_message']}")
                return ("skipped", details)
            elif error_code in (-100, -101, -102, -103):
                details['error_type'] = 'auth'
                details['error_message'] = f'JV-Link認証エラー: {error_str}'
            elif error_code == -2:
                # No data available
                return ("nodata", details)
            else:
                details['error_type'] = 'connection'
                details['error_message'] = f'JV-Linkエラー: {error_str}'

            self.errors.append({
                'spec': spec,
                'type': details['error_type'],
                'message': details['error_message'],
            })
            return ("failed", details)

        except NVLinkError as e:
            error_code = getattr(e, 'error_code', None)
            error_str = str(e)

            # NV-Link (NAR) 固有のエラー処理
            if error_code == -111 or error_code == -114 or '契約' in error_str:
                details['error_type'] = 'contract'
                details['error_message'] = '地方競馬DATAの契約対象外です'
                self.warnings.append(f"{spec}: {details['error_message']}")
                return ("skipped", details)
            elif error_code in (-100, -101, -102, -103):
                details['error_type'] = 'auth'
                details['error_message'] = f'NV-Link認証エラー: NVDTLab設定ツールでサービスキーを確認してください'
            elif error_code == -2:
                return ("nodata", details)
            else:
                details['error_type'] = 'nvlink'
                details['error_message'] = f'NV-Linkエラー: {error_str}'

            self.errors.append({
                'spec': spec,
                'type': details['error_type'],
                'message': details['error_message'],
            })
            return ("failed", details)

        except FetcherError as e:
            error_str = str(e)

            # FetcherError の内容からエラー種別を判定
            if '-203' in error_str or 'キャッシュ' in error_str:
                details['error_type'] = 'cache'
                details['error_message'] = 'NV-Linkキャッシュエラー: NVDTLab設定ツールでキャッシュをクリアしてください'
            elif '-3' in error_str or 'ファイル' in error_str:
                details['error_type'] = 'file'
                details['error_message'] = 'データファイルが見つかりません: NVDTLab設定ツールでデータを再取得してください'
            elif '契約' in error_str:
                details['error_type'] = 'contract'
                details['error_message'] = 'データ提供サービス契約外です'
                self.warnings.append(f"{spec}: {details['error_message']}")
                return ("skipped", details)
            else:
                details['error_type'] = 'fetch'
                details['error_message'] = f'データ取得エラー: {error_str[:100]}'

            self.errors.append({
                'spec': spec,
                'type': details['error_type'],
                'message': details['error_message'],
            })
            return ("failed", details)

        except Exception as e:
            error_msg = f"予期しないエラー: {str(e)[:100]}"
            details['error_type'] = 'exception'
            details['error_message'] = error_msg
            self.errors.append({
                'spec': spec,
                'type': 'exception',
                'message': error_msg,
            })
            return ("failed", details)

    def _make_progress_bar(self, progress: float, width: int = 15) -> str:
        """シンプルな進捗バーを生成"""
        filled = int(width * progress / 100)
        empty = width - filled
        bar = "█" * filled + "░" * empty
        return f"[cyan]{bar}[/cyan]"

    def _fetch_single_spec(self, spec: str, option: int) -> str:
        """単一データスペック取得（シンプル版）

        Returns:
            "success": データ取得成功
            "nodata": データなし（正常）
            "skipped": 契約外などでスキップ
            "failed": エラー
        """
        status, _ = self._fetch_single_spec_with_progress(spec, option)
        return status

    def _run_background_updater(self) -> bool:
        """バックグラウンド更新サービスを開始"""
        try:
            # background_updater.pyをバックグラウンドで起動
            script_path = self.project_root / "scripts" / "background_updater.py"
            cmd = [sys.executable, str(script_path)]

            # Windowsでは新しいコンソールウィンドウで起動
            if sys.platform == "win32":
                result = subprocess.Popen(
                    cmd,
                    cwd=self.project_root,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                result = subprocess.Popen(
                    cmd,
                    cwd=self.project_root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            time.sleep(2)
            return result.poll() is None
        except Exception:
            return False


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="JLTSQL セットアップ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--mode", choices=["simple", "standard", "full", "update"], default=None,
                        help="セットアップモード: simple(簡易), standard(標準), full(フル), update(更新)")
    parser.add_argument("--include-timeseries", action="store_true",
                        help="時系列オッズを取得（オッズ推移→TS_O1-O6テーブル）")
    parser.add_argument("--timeseries-months", type=int, default=12,
                        help="時系列オッズの取得期間（月数、デフォルト: 12）。12以上は非推奨")
    parser.add_argument("--include-realtime", action="store_true",
                        help="速報系データも取得（過去約1週間分）")
    parser.add_argument("--background", action="store_true",
                        help="バックグラウンド更新を開始（蓄積系定期更新 + 速報系監視）")
    parser.add_argument("-y", "--yes", action="store_true", help="確認スキップ（非対話モード）")
    parser.add_argument("-i", "--interactive", action="store_true", help="対話モード（デフォルト）")
    parser.add_argument("--db-path", type=str, default=None,
                        help="データベースファイルパス（デフォルト: data/keiba.db）")
    parser.add_argument("--db-type", type=str, choices=["sqlite", "postgresql"], default="sqlite",
                        help="データベースタイプ (sqlite, postgresql、デフォルト: sqlite)")
    parser.add_argument("--pg-host", type=str, default="localhost",
                        help="PostgreSQLホスト（デフォルト: localhost）")
    parser.add_argument("--pg-port", type=int, default=5432,
                        help="PostgreSQLポート（デフォルト: 5432）")
    parser.add_argument("--pg-database", type=str, default="keiba",
                        help="PostgreSQLデータベース名（デフォルト: keiba、自動作成）")
    parser.add_argument("--pg-user", type=str, default="postgres",
                        help="PostgreSQLユーザー名（デフォルト: postgres）")
    parser.add_argument("--pg-password", type=str, default=None,
                        help="PostgreSQLパスワード（デフォルト: PGPASSWORD環境変数またはプロンプト）")
    parser.add_argument("--from-date", type=str, default=None,
                        help="取得開始日 (YYYYMMDD形式、デフォルト: 19860101)")
    parser.add_argument("--to-date", type=str, default=None,
                        help="取得終了日 (YYYYMMDD形式、デフォルト: 今日)")
    parser.add_argument("--years", type=int, default=None,
                        help="取得期間（年数）。指定すると--from-dateは無視される")
    parser.add_argument("--no-odds", action="store_true",
                        help="オッズデータ(O1-O6)を除外")
    parser.add_argument("--no-monitor", action="store_true",
                        help="バックグラウンド監視を無効化")
    parser.add_argument("--log-file", type=str, default=None,
                        help="ログファイルパス（指定するとログ出力有効。デフォルト: 無効）")
    parser.add_argument("--source", type=str, choices=["jra", "nar", "all"], default="jra",
                        help="データソース: jra(中央競馬), nar(地方競馬), all(両方)。デフォルト: jra")

    args = parser.parse_args()

    # ログ設定: --log-file指定時のみファイルに出力
    if args.log_file:
        setup_logging(
            level="DEBUG",
            console_level="CRITICAL",
            log_to_file=True,
            log_to_console=False,
            log_file=args.log_file
        )

    # 対話モードかどうかを判定
    # コマンドライン引数が指定されていなければ対話モード
    use_interactive = args.interactive or (
        args.mode is None and
        not args.yes
    )

    if use_interactive:
        # 対話形式で設定を収集
        settings = interactive_setup()
    else:
        # コマンドライン引数から設定を構築
        settings = {}
        today = datetime.now()

        # 日付設定
        if args.years:
            # --years指定時: 過去N年分
            from_date = (today - timedelta(days=365 * args.years)).strftime("%Y%m%d")
            settings['from_date'] = from_date
        elif args.from_date:
            settings['from_date'] = args.from_date
        else:
            settings['from_date'] = "19860101"  # デフォルト: 全期間

        settings['to_date'] = args.to_date if args.to_date else today.strftime("%Y%m%d")

        # モード設定（デフォルトは簡易）
        mode = args.mode or 'simple'
        settings['mode'] = mode
        mode_names = {'simple': '簡易', 'standard': '標準', 'full': 'フル', 'update': '更新'}
        settings['mode_name'] = mode_names[mode]

        # 時系列オッズ取得オプション
        settings['include_timeseries'] = args.include_timeseries
        settings['timeseries_months'] = args.timeseries_months

        # 速報系データ取得オプション
        settings['include_realtime'] = args.include_realtime

        # バックグラウンド更新
        settings['enable_background'] = args.background and not args.no_monitor

        # データベース設定
        settings['db_path'] = args.db_path
        settings['db_type'] = args.db_type

        # PostgreSQL設定
        if args.db_type == 'postgresql':
            settings['pg_host'] = args.pg_host
            settings['pg_port'] = args.pg_port
            settings['pg_database'] = args.pg_database
            settings['pg_user'] = args.pg_user

            # パスワードは引数 > 環境変数 > デフォルト(postgres)の優先順位
            if args.pg_password:
                settings['pg_password'] = args.pg_password
            elif 'PGPASSWORD' in os.environ:
                settings['pg_password'] = os.environ['PGPASSWORD']
            else:
                # デフォルトパスワード
                settings['pg_password'] = 'postgres'

            # CLIモードでもデータベース自動作成
            print(f"PostgreSQLデータベース '{args.pg_database}' を確認中...")
            status, message = _check_postgresql_database(
                args.pg_host, args.pg_port, args.pg_database,
                args.pg_user, settings['pg_password']
            )
            if status == "created":
                print(f"[OK] {message}")
            elif status == "exists":
                print(f"[INFO] {message} - 既存データを使用します")
            else:  # error
                print(f"[ERROR] {message}")
                sys.exit(1)

        # オッズ除外
        settings['no_odds'] = args.no_odds

        # データソース（JRA/NAR）
        settings['data_source'] = args.source

        # 非対話モードではサービスキーを自動チェック
        is_valid, message = _check_service_key(args.source)
        if not is_valid:
            if args.source == "all":
                source_name = "中央競馬（JRA）& 地方競馬（NAR/UmaConn）"
            elif args.source == "nar":
                source_name = "地方競馬（NAR/UmaConn）"
            else:
                source_name = "中央競馬（JRA）"
            print(f"[NG] {source_name}サービス認証エラー: {message}")
            if args.source == "jra":
                print("JRA-VAN DataLabソフトウェアでサービスキーを設定してください")
            elif args.source == "all":
                print("JRA-VAN DataLab と UmaConn のサービスキーを設定してください")
            else:
                print("UmaConnソフトウェアでサービスキーを設定してください")
            sys.exit(1)

    # 実行
    try:
        with ProcessLock("quickstart"):
            runner = QuickstartRunner(settings)
            sys.exit(runner.run())
    except ProcessLockError as e:
        if RICH_AVAILABLE:
            console.print(f"[red]エラー: {e}[/red]")
        else:
            print(f"エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
