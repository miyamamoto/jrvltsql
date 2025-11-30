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
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Windows cp932対策: stdoutをUTF-8に再設定
if sys.platform == "win32" and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ログ設定: コンソールにはERROR以上のみ表示、それ以外はファイルに出力
from src.utils.logger import setup_logging
setup_logging(level="DEBUG", console_level="ERROR", log_to_file=True, log_to_console=True)

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
    mode_table.add_row(
        "4", "更新",
        "標準と同じ [cyan](差分のみ)[/cyan]",
        "前回更新以降"
    )

    console.print(mode_table)
    console.print()

    choice = Prompt.ask(
        "選択",
        choices=["1", "2", "3", "4"],
        default="1"
    )

    today = datetime.now()
    settings['from_date'] = "19860101"  # 常に全期間
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
    else:  # choice == "4"
        settings['mode'] = 'update'
        settings['mode_name'] = '更新'

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
    settings['enable_background'] = Confirm.ask("バックグラウンド更新を開始しますか？", default=False)
    console.print()

    # 確認
    console.print(Panel("[bold]設定確認[/bold]", border_style="blue"))

    confirm_table = Table(show_header=False, box=None, padding=(0, 1))
    confirm_table.add_column("Key", style="dim")
    confirm_table.add_column("Value", style="white")

    confirm_table.add_row("モード", settings['mode_name'])
    confirm_table.add_row("速報系", "[green]取得[/green]" if settings.get('include_realtime') else "[dim]なし[/dim]")
    confirm_table.add_row("定期更新", "[green]開始[/green]" if settings.get('enable_background') else "[dim]なし[/dim]")

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

    # セットアップモード
    print("1. セットアップモードを選択してください:")
    print()
    print("   No  モード  対象データ                          期間")
    print("   ──────────────────────────────────────────────────────────")
    print("   1)  簡易    RACE,DIFF (レース結果・馬情報)       全期間(1986年〜)")
    print("   2)  標準    簡易+BLOD,YSCH,TOKU,SNAP等           全期間(1986年〜)")
    print("   3)  フル    標準+O1〜O6 (確定オッズ)             全期間(1986年〜)")
    print("   4)  更新    標準と同じ (差分のみ)                前回更新以降")
    print()

    choice = input("選択 [1]: ").strip() or "1"

    today = datetime.now()
    settings['from_date'] = "19860101"  # 常に全期間
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
    else:  # choice == "4"
        settings['mode'] = 'update'
        settings['mode_name'] = '更新'

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
    print("   [y/N]: ", end="")
    bg_choice = input().strip().lower()
    settings['enable_background'] = bg_choice in ('y', 'yes')
    print()

    # 確認
    print("-" * 60)
    print("設定確認:")
    print(f"  モード: {settings['mode_name']}")
    print(f"  速報系: {'取得' if settings.get('include_realtime') else 'なし'}")
    print(f"  定期更新: {'開始' if settings.get('enable_background') else 'なし'}")
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
    # (スペック名, 説明, オプション) - オプション: 1=セットアップ, 2=通常

    # 簡易モード: レース結果と馬情報のみ
    SIMPLE_SPECS = [
        ("RACE", "レース情報", 1),      # RA, SE, HR, WF, JG
        ("DIFF", "マスタ情報", 1),      # UM, KS, CH, BR, BN, HN, SK, RC, HC
    ]

    # 標準モード: 簡易 + 付加情報
    STANDARD_SPECS = [
        ("RACE", "レース情報", 1),
        ("DIFF", "マスタ情報", 1),
        ("BLOD", "血統情報", 1),
        ("YSCH", "開催スケジュール", 1),
        ("TOKU", "特別登録馬", 1),
        ("SNAP", "出馬表", 1),
        ("SLOP", "坂路調教", 1),
        ("HOYU", "馬名の意味由来", 1),
        ("HOSE", "市場取引価格", 1),
    ]

    # フルモード: 標準 + オッズ
    FULL_SPECS = [
        ("RACE", "レース情報", 1),
        ("DIFF", "マスタ情報", 1),
        ("BLOD", "血統情報", 1),
        ("YSCH", "開催スケジュール", 1),
        ("TOKU", "特別登録馬", 1),
        ("SNAP", "出馬表", 1),
        ("SLOP", "坂路調教", 1),
        ("HOYU", "馬名の意味由来", 1),
        ("HOSE", "市場取引価格", 1),
        ("O1", "単勝・複勝・枠連オッズ", 1),
        ("O2", "馬連オッズ", 1),
        ("O3", "ワイドオッズ", 1),
        ("O4", "馬単オッズ", 1),
        ("O5", "3連複オッズ", 1),
        ("O6", "3連単オッズ", 1),
    ]

    # 今週データモード: option=2で直近のレースデータのみ取得（高速）
    UPDATE_SPECS = [
        ("RACE", "レース情報", 2),
        ("DIFF", "マスタ情報", 2),
        ("BLOD", "血統情報", 2),
        ("YSCH", "開催スケジュール", 2),
        ("TOKU", "特別登録馬", 2),
        ("SNAP", "出馬表", 2),
        ("SLOP", "坂路調教", 2),
        ("HOYU", "馬名の意味由来", 2),
        ("HOSE", "市場取引価格", 2),
    ]

    # 速報系データスペック（JVRTOpen使用、過去約1週間分取得可能）
    # 注意: 速報系は蓄積系と異なるAPI (JVRTOpen) を使用
    REALTIME_SPECS = [
        ("0B11", "レース詳細（速報）"),
        ("0B12", "馬毎レース情報（速報）"),
        ("0B15", "払戻情報（速報）"),
        ("0B20", "競走馬マスタ（速報）"),
        ("0B30", "騎手マスタ（速報）"),
        ("0B31", "オッズ情報"),
        ("0B32", "オッズ（時系列）"),
        ("0B33", "馬体重"),
        ("0B34", "騎手変更・取消"),
        ("0B35", "天候馬場状態"),
        ("0B36", "コース変更"),
    ]

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
            return self.SIMPLE_SPECS.copy()
        elif mode == 'standard':
            return self.STANDARD_SPECS.copy()
        elif mode == 'update':
            return self.UPDATE_SPECS.copy()
        else:  # full
            return self.FULL_SPECS.copy()

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

    # === 速報系データ取得 ===

    def _run_fetch_realtime_rich(self) -> bool:
        """速報系データ取得（Rich UI）"""
        specs = self.REALTIME_SPECS
        total_specs = len(specs)

        console.print()
        console.print(Panel(
            f"[bold]速報系データ取得[/bold] ({total_specs}スペック)\n"
            "[dim]過去約1週間分のデータを取得します[/dim]",
            border_style="yellow",
        ))

        for idx, (spec, description) in enumerate(specs, 1):
            console.print(f"\n  [cyan]({idx}/{total_specs})[/cyan] [bold]{spec}[/bold]: {description}")

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

        return (self.stats['specs_success'] + self.stats['specs_nodata']) > 0

    def _run_fetch_realtime_simple(self) -> bool:
        """速報系データ取得（シンプル版）"""
        specs = self.REALTIME_SPECS
        total = len(specs)

        print(f"  速報系データ取得 ({total}スペック)")
        print("  過去約1週間分のデータを取得します")
        print()

        for idx, (spec, desc) in enumerate(specs, 1):
            print(f"  [{idx}/{total}] {spec}: {desc}...", end=" ", flush=True)

            status, _ = self._fetch_single_realtime_spec(spec)

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

            time.sleep(0.3)

        print(f"\n  取得成功: {self.stats['specs_success']}, データなし: {self.stats['specs_nodata']}, 契約外: {self.stats['specs_skipped']}, エラー: {self.stats['specs_failed']}")
        return (self.stats['specs_success'] + self.stats['specs_nodata']) > 0

    def _fetch_single_realtime_spec(self, spec: str) -> tuple:
        """単一の速報系スペックを取得

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
            db_path = self.project_root / "data" / "keiba.db"
            db = SQLiteDatabase({"path": str(db_path)})

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
        """単一データスペック取得（スピナー付きリアルタイム進捗表示）

        Returns:
            tuple: (status, details)
                status: "success", "nodata", "skipped", "failed"
                details: dict with progress info
        """
        import re
        from rich.live import Live
        from rich.text import Text

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

        # 時間計測用
        phase_start_time = [time.time()]  # リストにしてクロージャで更新可能に

        # 処理状態
        current_phase = "初期化"
        current_table = None
        tables_processed = []
        frame_idx = [0]  # リストにしてクロージャで更新可能に

        def get_spinner():
            """スピナー文字を取得（呼び出すたびにアニメーション）"""
            frame = self.SPINNER_FRAMES[frame_idx[0] % len(self.SPINNER_FRAMES)]
            frame_idx[0] += 1
            return frame

        def make_status_display():
            """現在の処理状態を表示用テキストで返す"""
            spinner = get_spinner()

            if current_phase == "初期化":
                return Text.assemble(
                    ("    ", ""),
                    (spinner, "cyan"),
                    (" 初期化中...", "dim")
                )

            elif current_phase == "ダウンロード":
                return Text.assemble(
                    ("    ", ""),
                    (spinner, "cyan"),
                    (f" ダウンロード中... ", "dim"),
                    (f"({details['download_count']}ファイル)", "dim cyan")
                )

            elif current_phase == "読み込み":
                if details['records_fetched'] > 0:
                    # レコード処理中の進捗を表示
                    # ファイル進捗と残り時間を計算
                    files_done = details['files_processed']
                    files_total = details['total_files']

                    progress_text = ""
                    eta_text = ""

                    if files_total > 0 and files_done > 0:
                        pct = (files_done / files_total) * 100
                        progress_text = f" ({files_done}/{files_total}ファイル {pct:.0f}%)"

                        # 残り時間を計算
                        elapsed = time.time() - phase_start_time[0]
                        if files_done > 0:
                            time_per_file = elapsed / files_done
                            remaining_files = files_total - files_done
                            eta_seconds = time_per_file * remaining_files
                            if eta_seconds > 60:
                                eta_text = f" 残り約{int(eta_seconds // 60)}分{int(eta_seconds % 60)}秒"
                            else:
                                eta_text = f" 残り約{int(eta_seconds)}秒"

                    return Text.assemble(
                        ("    ", ""),
                        (spinner, "cyan"),
                        (f" レコード処理中: ", "dim"),
                        (f"{details['records_fetched']:,}件", "cyan"),
                        (f" ({details['speed']}件/秒)", "dim") if details['speed'] else ("", ""),
                        (progress_text, "dim"),
                        (eta_text, "yellow") if eta_text else ("", "")
                    )
                else:
                    return Text.assemble(
                        ("    ", ""),
                        (spinner, "cyan"),
                        (f" ファイル読み取り中: ", "dim"),
                        (f"{details['read_count']:,}ファイル", "dim cyan")
                    )

            elif current_phase == "保存":
                if details['records_saved'] > 0:
                    return Text.assemble(
                        ("    ", ""),
                        (spinner, "cyan"),
                        (f" {current_table} 保存中: ", "dim"),
                        (f"{details['records_saved']:,}件", "cyan")
                    )
                else:
                    return Text.assemble(
                        ("    ", ""),
                        (spinner, "cyan"),
                        (f" {current_table} 保存中...", "dim")
                    )

            elif current_phase == "完了":
                return Text.assemble(("    ", ""), ("✓ 処理完了", "green"))

            else:
                return Text.assemble(
                    ("    ", ""),
                    (spinner, "cyan"),
                    (f" {current_phase}...", "dim")
                )

        try:
            cmd = [
                sys.executable, "-u", "-m", "src.cli.main", "fetch",
                "--from", self.settings['from_date'],
                "--to", self.settings['to_date'],
                "--spec", spec,
                "--option", str(option),
            ]

            # 環境変数でPythonのバッファリングを無効化
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

            # Popenでリアルタイム出力を取得
            # stderrもstdoutにマージして全てのメッセージをキャプチャ
            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=env,
            )

            output_lines = []
            error_lines = []  # エラーっぽい行を保存

            # Live表示でスピナーを回しながら進捗を表示
            with Live(make_status_display(), console=console, refresh_per_second=10, transient=True) as live:
                for line in process.stdout:
                    output_lines.append(line)

                    # エラー関連のキーワードを含む行を保存
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in ['error', 'exception', 'failed', 'エラー', 'traceback']):
                        error_lines.append(line.strip())

                    # ダウンロード数を抽出
                    if 'download_count=' in line or 'download_count:' in line:
                        match = re.search(r'download_count[=:]\s*(\d+)', line)
                        if match:
                            count = int(match.group(1))
                            if count > 0 and details['download_count'] == 0:
                                details['download_count'] = count
                                current_phase = "ダウンロード"

                    # 読み取り件数を抽出
                    if 'read_count=' in line or 'read_count:' in line:
                        match = re.search(r'read_count[=:]\s*(\d+)', line)
                        if match:
                            count = int(match.group(1))
                            if count > 0:
                                details['read_count'] = count
                                details['total_files'] = count  # read_countはファイル数
                                if current_phase != "読み込み":
                                    current_phase = "読み込み"
                                    phase_start_time[0] = time.time()  # 読み込みフェーズ開始時刻を記録

                    # ダウンロード完了
                    if 'Download completed' in line:
                        if current_phase != "読み込み":
                            current_phase = "読み込み"
                            phase_start_time[0] = time.time()  # 読み込みフェーズ開始時刻を記録

                    # レコード処理中の進捗を抽出（Processing records records_fetched=xxx）
                    if 'records_fetched=' in line:
                        match = re.search(r'records_fetched[=:]\s*(\d+)', line)
                        if match:
                            details['records_fetched'] = int(match.group(1))
                        speed_match = re.search(r'speed[=:]\s*(\d+)', line)
                        if speed_match:
                            details['speed'] = speed_match.group(1)
                        # ファイル進捗を抽出
                        files_done_match = re.search(r'files_processed[=:]\s*(\d+)', line)
                        if files_done_match:
                            details['files_processed'] = int(files_done_match.group(1))
                        files_total_match = re.search(r'total_files[=:]\s*(\d+)', line)
                        if files_total_match:
                            details['total_files'] = int(files_total_match.group(1))

                    # バッチ保存を検出
                    if 'Batch inserted' in line and 'table=' in line:
                        current_phase = "保存"
                        table_match = re.search(r'table[=:]\s*(NL_[A-Z0-9]+|RT_[A-Z0-9]+)', line)
                        if table_match:
                            current_table = table_match.group(1)
                            if current_table not in tables_processed:
                                tables_processed.append(current_table)

                        records_match = re.search(r'records[=:]\s*(\d+)', line)
                        if records_match:
                            details['records_saved'] += int(records_match.group(1))

                    # パース済みレコード数を抽出
                    if 'records_parsed=' in line or 'records_parsed:' in line:
                        match = re.search(r'records_parsed[=:]\s*(\d+)', line)
                        if match:
                            details['records_parsed'] = int(match.group(1))

                    # 毎行で表示を更新（スピナーを回す）
                    live.update(make_status_display())

            # プロセス終了を待つ
            process.wait(timeout=600)
            returncode = process.returncode
            output = ''.join(output_lines)

            # 処理したテーブル一覧を表示
            if tables_processed:
                tables_str = ", ".join(tables_processed)
                console.print(f"    [dim]処理テーブル: {tables_str}[/dim]")

            # 出力から状態を判定
            if returncode == 0:
                if "No data available" in output or "read_count=0" in output or "read_count: 0" in output:
                    return ("nodata", details)
                return ("success", details)
            else:
                # データなし判定（正常）
                if "No data" in output or "read_count=0" in output or "read_count: 0" in output:
                    return ("nodata", details)

                # エラー分析（error_linesも渡す）
                error_type, error_message = self._analyze_error(output, returncode, error_lines)
                details['error_type'] = error_type
                details['error_message'] = error_message

                # 契約外は警告として処理
                if error_type == 'contract':
                    self.warnings.append(f"{spec}: {error_message}")
                    return ("skipped", details)

                # その他のエラー
                self.errors.append({
                    'spec': spec,
                    'type': error_type,
                    'message': error_message,
                })
                return ("failed", details)

        except subprocess.TimeoutExpired:
            error_msg = "処理がタイムアウトしました（10分以上経過）"
            details['error_type'] = 'timeout'
            details['error_message'] = error_msg
            self.errors.append({
                'spec': spec,
                'type': 'timeout',
                'message': error_msg,
            })
            if process:
                process.kill()
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

    args = parser.parse_args()

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

        settings['from_date'] = "19860101"  # 常に全期間
        settings['to_date'] = today.strftime("%Y%m%d")

        # モード設定（デフォルトは簡易）
        mode = args.mode or 'simple'
        settings['mode'] = mode
        mode_names = {'simple': '簡易', 'standard': '標準', 'full': 'フル', 'update': '更新'}
        settings['mode_name'] = mode_names[mode]

        # 速報系データ取得オプション
        settings['include_realtime'] = args.include_realtime

        # バックグラウンド更新
        settings['enable_background'] = args.background

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
