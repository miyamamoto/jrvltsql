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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

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
from src.utils.logger import setup_logging
# 初期設定: ログファイル出力は無効（main()で引数に基づいて再設定）
setup_logging(level="DEBUG", console_level="CRITICAL", log_to_file=False, log_to_console=False)

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
    }

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
        lock_file.unlink()
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
        startup_path, _ = winreg.QueryValueEx(key, "Startup")
        winreg.CloseKey(key)
        return Path(startup_path)
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
        batch_path.write_text(batch_content, encoding='shift_jis')
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
        return False, f"JV-Link未インストール: {e}"


def _interactive_setup_rich() -> dict:
    """Rich UIで対話形式設定"""
    console.clear()
    console.print()
    console.print(Panel(
        "[bold]JRA-VAN DataLab -> SQLite[/bold]\n"
        "[dim]競馬データベース自動セットアップ[/dim]",
        title="[bold blue]JLTSQL[/bold blue]",
        border_style="blue",
        padding=(1, 2),
    ))
    console.print()

    settings = {}

    # サービスキーの確認（JV-Link APIで実際にチェック）
    console.print("[bold]0. JV-Link サービスキー確認[/bold]")
    console.print()

    is_valid, message = _check_jvlink_service_key()

    if is_valid:
        console.print(f"  [green]OK[/green] {message}")
        console.print()
    else:
        console.print(f"  [red]NG[/red] {message}")
        console.print()
        console.print("[yellow]JRA-VAN DataLabソフトウェアでサービスキーを設定してください[/yellow]")
        console.print("[dim]https://jra-van.jp/dlb/[/dim]")
        console.print()
        console.print("[red]セットアップを中止します。[/red]")
        sys.exit(1)

    # 前回セットアップ履歴を確認
    last_setup = _load_setup_history()

    # セットアップモードの選択
    console.print("[bold]1. セットアップモード[/bold]")
    console.print()

    mode_table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    mode_table.add_column("No", style="cyan", width=3, justify="center")
    mode_table.add_column("モード", width=6)
    mode_table.add_column("対象データ", width=35)
    mode_table.add_column("期間", width=18)

    mode_table.add_row(
        "1", "簡易",
        "RACE, DIFF\n[dim](レース結果・馬情報)[/dim]",
        "全期間\n[dim](1986年〜)[/dim]"
    )
    mode_table.add_row(
        "2", "標準",
        "簡易 + BLOD,YSCH,TOKU,SNAP,SLOP,HOYU,HOSE\n[dim](血統・調教・スケジュール等)[/dim]",
        "全期間\n[dim](1986年〜)[/dim]"
    )
    mode_table.add_row(
        "3", "フル",
        "標準 + O1〜O6\n[dim](確定オッズ)[/dim]",
        "全期間\n[dim](1986年〜)[/dim]"
    )

    # 更新モードは前回セットアップがある場合のみ表示
    if last_setup:
        last_date = datetime.fromisoformat(last_setup['timestamp'])
        last_date_str = last_date.strftime("%Y-%m-%d %H:%M")
        mode_table.add_row(
            "4", "更新",
            f"前回と同じ ({last_setup.get('mode_name', '?')})\n[dim](差分データのみ)[/dim]",
            f"前回以降\n[dim]({last_date_str}〜)[/dim]"
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
        settings['from_date'] = "19860101"
    elif choice == "2":
        settings['mode'] = 'standard'
        settings['mode_name'] = '標準'
        settings['from_date'] = "19860101"
    elif choice == "3":
        settings['mode'] = 'full'
        settings['mode_name'] = 'フル'
        settings['from_date'] = "19860101"
    else:  # choice == "4" (更新モード)
        settings['mode'] = 'update'
        settings['mode_name'] = '更新'
        # 前回のセットアップ情報を引き継ぐ
        settings['last_setup'] = last_setup
        # 前回の取得日から開始
        last_date = datetime.fromisoformat(last_setup['timestamp'])
        settings['from_date'] = last_date.strftime("%Y%m%d")
        # 前回のデータ種別を引き継ぐ
        settings['update_specs'] = last_setup.get('specs', [])

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

        console.print(update_info)

    console.print()

    # 速報系データの取得
    console.print("[bold]2. 速報系データ[/bold]")
    console.print("[dim]過去約1週間分のリアルタイムデータ（オッズ変動・馬体重等）[/dim]")
    console.print()
    settings['include_realtime'] = Confirm.ask("速報系データも取得しますか？", default=False)
    console.print()

    # バックグラウンド更新
    console.print("[bold]3. バックグラウンド更新[/bold]")
    console.print("[dim]蓄積系データの定期更新（30分毎）と速報系データの監視[/dim]")
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
        console.print("[bold]4. Windows起動時の自動起動[/bold]")
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

    confirm_table.add_row("モード", settings['mode_name'])
    confirm_table.add_row("速報系", "[green]取得[/green]" if settings.get('include_realtime') else "[dim]なし[/dim]")
    if settings.get('keep_existing_background'):
        confirm_table.add_row("定期更新", "[cyan]継続（既存プロセス）[/cyan]")
    else:
        confirm_table.add_row("定期更新", "[green]開始[/green]" if settings.get('enable_background') else "[dim]なし[/dim]")
    if settings.get('auto_start'):
        confirm_table.add_row("自動起動", "[green]有効[/green]")

    console.print(confirm_table)
    console.print()

    if not Confirm.ask("[bold]この設定でセットアップを開始しますか？[/bold]", default=True):
        console.print("[yellow]キャンセルしました[/yellow]")
        sys.exit(0)

    return settings


def _interactive_setup_simple() -> dict:
    """シンプルな対話形式設定"""
    print("=" * 60)
    print("JLTSQL セットアップ")
    print("=" * 60)
    print()

    settings = {}

    # サービスキーの確認（JV-Link APIで実際にチェック）
    print("0. JV-Link サービスキー確認")
    print()

    is_valid, message = _check_jvlink_service_key()

    if is_valid:
        print(f"  [OK] {message}")
    else:
        print(f"  [NG] {message}")
        print()
        print("  JRA-VAN DataLabソフトウェアでサービスキーを設定してください")
        print("  https://jra-van.jp/dlb/")
        print()
        print("[NG] セットアップを中止します。")
        sys.exit(1)

    print()

    # 前回セットアップ履歴を確認
    last_setup = _load_setup_history()

    # セットアップモード
    print("1. セットアップモードを選択してください:")
    print()
    print("   No  モード  対象データ                          期間")
    print("   ──────────────────────────────────────────────────────────")
    print("   1)  簡易    RACE,DIFF (レース結果・馬情報)       全期間(1986年〜)")
    print("   2)  標準    簡易+BLOD,YSCH,TOKU,SNAP等           全期間(1986年〜)")
    print("   3)  フル    標準+O1〜O6 (確定オッズ)             全期間(1986年〜)")
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
        settings['from_date'] = "19860101"
    elif choice == "2":
        settings['mode'] = 'standard'
        settings['mode_name'] = '標準'
        settings['from_date'] = "19860101"
    elif choice == "3":
        settings['mode'] = 'full'
        settings['mode_name'] = 'フル'
        settings['from_date'] = "19860101"
    else:  # choice == "4" (更新モード)
        settings['mode'] = 'update'
        settings['mode_name'] = '更新'
        settings['last_setup'] = last_setup
        last_date = datetime.fromisoformat(last_setup['timestamp'])
        settings['from_date'] = last_date.strftime("%Y%m%d")
        settings['update_specs'] = last_setup.get('specs', [])

        # 更新範囲を表示
        print()
        print("  --- 更新情報 ---")
        print(f"  前回モード:   {last_setup.get('mode_name', '不明')}")
        print(f"  前回取得日時: {last_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"  更新範囲:     {settings['from_date']} 〜 {settings['to_date']}")
        specs_str = ", ".join(last_setup.get('specs', []))
        print(f"  対象データ:   {specs_str[:50]}{'...' if len(specs_str) > 50 else ''}")

    print()

    # 速報系データ
    print("2. 速報系データも取得しますか？")
    print("   (過去約1週間分のオッズ変動・馬体重等)")
    print("   [y/N]: ", end="")
    realtime_choice = input().strip().lower()
    settings['include_realtime'] = realtime_choice in ('y', 'yes')
    print()

    # バックグラウンド更新
    print("3. バックグラウンド更新を開始しますか？")
    print("   (蓄積系データの定期更新 + 速報系データの監視)")
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
        print("4. Windows起動時の自動起動")
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
    print(f"  モード: {settings['mode_name']}")
    print(f"  速報系: {'取得' if settings.get('include_realtime') else 'なし'}")
    if settings.get('keep_existing_background'):
        print("  定期更新: 継続（既存プロセス）")
    else:
        print(f"  定期更新: {'開始' if settings.get('enable_background') else 'なし'}")
    if settings.get('auto_start'):
        print("  自動起動: 有効")
    print("-" * 60)
    print()

    confirm = input("この設定でセットアップを開始しますか？ [Y/n]: ").strip().lower()
    if confirm in ('n', 'no'):
        print("キャンセルしました")
        sys.exit(0)

    return settings


class QuickstartRunner:
    """完全自動セットアップ実行クラス（Claude Code風UI）"""

    # モード別データスペック定義
    # (スペック名, 説明, オプション)
    # オプション: 1=通常データ（差分）, 2=今週データ, 3=セットアップ（ダイアログ）, 4=分割セットアップ

    # 簡易モード: レース結果と馬情報のみ
    SIMPLE_SPECS = [
        ("RACE", "レース情報", 1),      # RA, SE, HR, WF, JG
        ("DIFF", "マスタ情報", 1),      # UM, KS, CH, BR, BN, HN, SK, RC, HC
    ]

    # 標準モード: 簡易 + 付加情報 (option=1)
    STANDARD_SPECS = [
        ("TOKU", "特別登録馬", 1),
        ("RACE", "レース情報", 1),
        ("DIFF", "マスタ情報", 1),
        ("BLOD", "血統情報", 1),
        ("MING", "データマイニング予想", 1),
        ("SLOP", "坂路調教", 1),
        ("WOOD", "ウッドチップ調教", 1),
        ("YSCH", "開催スケジュール", 1),
        ("HOSE", "市場取引価格", 1),
        ("HOYU", "馬名の意味由来", 1),
        ("COMM", "コメント情報", 1),
    ]

    # フルモード: 標準 + オッズ (option=1)
    FULL_SPECS = [
        ("TOKU", "特別登録馬", 1),
        ("RACE", "レース情報", 1),
        ("DIFF", "マスタ情報", 1),
        ("BLOD", "血統情報", 1),
        ("MING", "データマイニング予想", 1),
        ("SLOP", "坂路調教", 1),
        ("WOOD", "ウッドチップ調教", 1),
        ("YSCH", "開催スケジュール", 1),
        ("HOSE", "市場取引価格", 1),
        ("HOYU", "馬名の意味由来", 1),
        ("COMM", "コメント情報", 1),
        ("O1", "単勝・複勝・枠連オッズ", 1),
        ("O2", "馬連オッズ", 1),
        ("O3", "ワイドオッズ", 1),
        ("O4", "馬単オッズ", 1),
        ("O5", "3連複オッズ", 1),
        ("O6", "3連単オッズ", 1),
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

    # 速報系データ (0B1x, 0B4x) - レース確定情報・変更情報
    SPEED_REPORT_SPECS = [
        ("0B11", "開催情報"),              # WE
        ("0B12", "レース情報"),            # RA, SE
        ("0B13", "データマイニング予想"),   # DM
        ("0B14", "出走取消・競走除外"),     # AV
        ("0B15", "払戻情報"),              # HR
        ("0B16", "馬体重"),                # WH
        ("0B17", "対戦型データマイニング予想"),  # TM
        ("0B41", "騎手変更情報"),          # RC
        ("0B42", "調教師変更情報"),        # TC
    ]

    # 時系列データ (0B2x-0B3x) - 継続更新オッズ・票数
    TIME_SERIES_SPECS = [
        ("0B20", "票数情報"),              # H1, H6
        ("0B30", "単勝オッズ"),            # O1
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

    def _run_fetch_all_rich(self) -> bool:
        """データ取得（Rich UI）- リアルタイム進捗表示"""
        specs_to_fetch = self._get_specs_for_mode()

        total_specs = len(specs_to_fetch)

        console.print()
        console.print(Panel(
            f"[bold]データ取得[/bold] ({total_specs}スペック)",
            border_style="blue",
        ))

        # 各スペックを順番に処理（リアルタイム進捗表示）
        for idx, (spec, description, option) in enumerate(specs_to_fetch, 1):
            # ヘッダー表示
            console.print(f"\n  [cyan]({idx}/{total_specs})[/cyan] [bold]{spec}[/bold]: {description}")

            start_time = time.time()
            status, details = self._fetch_single_spec_with_progress(spec, option)
            elapsed = time.time() - start_time

            if status == "success":
                self.stats['specs_success'] += 1
                saved = details.get('records_saved', 0)
                if saved > 0:
                    console.print(f"    [green]✓[/green] 完了: [bold]{saved:,}件[/bold]保存 [dim]({elapsed:.1f}秒)[/dim]")
                else:
                    console.print(f"    [green]✓[/green] 完了 [dim]({elapsed:.1f}秒)[/dim]")
            elif status == "nodata":
                self.stats['specs_nodata'] += 1
                console.print(f"    [dim]- データなし[/dim] [dim]({elapsed:.1f}秒)[/dim]")
            elif status == "skipped":
                self.stats['specs_skipped'] += 1
                console.print(f"    [yellow]⚠[/yellow] 契約外 [dim]({elapsed:.1f}秒)[/dim]")
            else:
                self.stats['specs_failed'] += 1
                console.print(f"    [red]✗[/red] エラー [dim]({elapsed:.1f}秒)[/dim]")
                # エラー詳細を表示
                if details.get('error_message'):
                    error_type = details.get('error_type', 'unknown')
                    error_label = self._get_error_label(error_type)
                    console.print(f"      [red]原因:[/red] [{error_label}] {details['error_message']}")

        # 成功またはデータなしがあれば成功とみなす
        return (self.stats['specs_success'] + self.stats['specs_nodata']) > 0

    def _print_summary_rich(self, success: bool):
        """サマリー出力（Rich版）"""
        console.print()

        if success:
            console.print(Panel(
                "[bold green]セットアップ完了！[/bold green]",
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
            console.print("  [cyan]jltsql export[/cyan]    - データエクスポート")
            if not self.settings.get('no_monitor', True):
                console.print("  [cyan]jltsql monitor --stop[/cyan] - 監視停止")
        else:
            console.print(Panel(
                "[bold red]セットアップ失敗[/bold red]",
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
                print("(データなし)")
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
            console.print(f"    [dim]- データなし[/dim] [dim]({elapsed:.1f}秒)[/dim]")
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
            self._print_realtime_status(status)
            time.sleep(0.3)

        # 時系列データ
        print("\n  【時系列データ】")
        for idx, (spec, desc) in enumerate(time_specs, 1):
            print(f"  [{idx}/{len(time_specs)}] {spec}: {desc}...", end=" ", flush=True)
            status, _ = self._fetch_single_realtime_spec(spec)
            self._print_realtime_status(status)
            time.sleep(0.3)

        print(f"\n  取得成功: {self.stats['specs_success']}, データなし: {self.stats['specs_nodata']}, 契約外: {self.stats['specs_skipped']}, エラー: {self.stats['specs_failed']}")
        return (self.stats['specs_success'] + self.stats['specs_nodata']) > 0

    def _print_realtime_status(self, status: str):
        """リアルタイム取得ステータスを表示"""
        if status == "success":
            self.stats['specs_success'] += 1
            print("OK")
        elif status == "nodata":
            self.stats['specs_nodata'] += 1
            print("(データなし)")
        elif status == "skipped":
            self.stats['specs_skipped'] += 1
            print("(契約外)")
        else:
            self.stats['specs_failed'] += 1
            print("NG")

    def _fetch_single_realtime_spec(self, spec: str) -> tuple:
        """単一のリアルタイムスペックを取得（速報系/時系列共通）

        Returns:
            tuple: (status, details)
                status: "success", "nodata", "skipped", "failed"
                details: dict with info
        """
        details = {
            'records_saved': 0,
            'error_message': None,
        }

        try:
            from src.fetcher.realtime import RealtimeFetcher
            from src.database.sqlite_handler import SQLiteDatabase
            from src.importer.importer import DataImporter

            # データベース接続
            db = SQLiteDatabase({"path": str(self.db_path)})

            with db:
                fetcher = RealtimeFetcher(sid="JLTSQL")
                importer = DataImporter(db, batch_size=1000)

                records = []
                try:
                    for record in fetcher.fetch(data_spec=spec, continuous=False):
                        records.append(record)
                except Exception as e:
                    error_str = str(e)
                    # 契約外チェック
                    if '-111' in error_str or '契約' in error_str:
                        return ("skipped", details)
                    # データなしチェック
                    if 'no data' in error_str.lower() or 'no more data' in error_str.lower():
                        return ("nodata", details)
                    raise

                if not records:
                    return ("nodata", details)

                # インポート
                import_stats = importer.import_records(iter(records), auto_commit=True)
                details['records_saved'] = import_stats.get('records_imported', len(records))

                return ("success", details)

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
        from src.database.sqlite_handler import SQLiteDatabase
        from src.database.schema import create_all_tables
        from src.importer.batch import BatchProcessor
        from src.jvlink.wrapper import JVLinkError

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

        try:
            # 設定読み込み
            from src.utils.config import load_config
            config = load_config(str(self.project_root / "config" / "config.yaml"))

            # データベース接続（コマンドライン引数で上書き可能）
            db_config = {"path": str(self.db_path)}

            database = SQLiteDatabase(db_config)

            with database:
                # テーブル作成（必要に応じて）
                try:
                    create_all_tables(database)
                except Exception:
                    pass  # 既存テーブルがあってもOK

                # BatchProcessorを直接呼び出し（show_progress=Trueでリッチ進捗表示）
                processor = BatchProcessor(
                    database=database,
                    sid=config.get("jvlink.sid", "JLTSQL"),
                    batch_size=1000,
                    service_key=config.get("jvlink.service_key"),
                    show_progress=True,  # JVLinkProgressDisplayを有効化
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
    parser.add_argument("--include-realtime", action="store_true",
                        help="速報系データも取得（過去約1週間分）")
    parser.add_argument("--background", action="store_true",
                        help="バックグラウンド更新を開始（蓄積系定期更新 + 速報系監視）")
    parser.add_argument("-y", "--yes", action="store_true", help="確認スキップ（非対話モード）")
    parser.add_argument("-i", "--interactive", action="store_true", help="対話モード（デフォルト）")
    parser.add_argument("--db-path", type=str, default=None,
                        help="データベースファイルパス（デフォルト: data/keiba.db）")
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

        # 速報系データ取得オプション
        settings['include_realtime'] = args.include_realtime

        # バックグラウンド更新
        settings['enable_background'] = args.background and not args.no_monitor

        # データベースパス
        settings['db_path'] = args.db_path

        # オッズ除外
        settings['no_odds'] = args.no_odds

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
