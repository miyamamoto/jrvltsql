#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""JLTSQL Quick Start Script - Claude Code風のモダンなUI

このスクリプトはJLTSQLの完全自動セットアップを実行します：
1. プロジェクト初期化
2. テーブル・インデックス作成
3. すべてのデータ取得（蓄積系データ）
4. リアルタイム監視の開始
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.text import Text
    from rich.live import Live
    from rich.layout import Layout
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from src.utils.lock_manager import ProcessLock, ProcessLockError


console = Console() if RICH_AVAILABLE else None


class QuickstartRunner:
    """完全自動セットアップ実行クラス（Claude Code風UI）"""

    # すべてのデータスペック（優先順位順）
    DATA_SPECS = [
        ("DIFN", "マスタ情報", 1),
        ("BLDN", "血統情報", 1),
        ("RACE", "レース情報", 1),
        ("YSCH", "開催スケジュール", 1),
        ("TOKU", "特別登録", 1),
        ("JGDW", "重賞情報", 1),
        ("HOSN", "市場取引", 2),
        ("COMM", "各種解説", 2),
        ("SNPN", "速報情報", 2),
        ("0B11", "データマイニング", 2),
        ("0B20", "成績", 2),
        ("0B31", "払戻", 2),
        ("0B41", "繁殖牝馬", 1),
    ]

    # オッズデータスペック
    ODDS_SPECS = [
        ("SLOP", "単勝・複勝オッズ", 2),
        ("HOYU", "馬連・ワイドオッズ", 2),
        ("O4", "枠連オッズ", 2),
        ("O5", "馬単オッズ", 2),
        ("O6", "3連複・3連単オッズ", 2),
        ("WOOD", "調教データ", 2),
        ("MING", "当日発表", 2),
    ]

    def __init__(self, args):
        self.args = args
        self.project_root = Path(__file__).parent.parent
        self.errors = []
        self.warnings = []
        self.stats = {
            'specs_success': 0,
            'specs_failed': 0,
            'specs_skipped': 0,
            'total_records': 0,
        }

    def run(self) -> int:
        """完全自動セットアップ実行"""
        if RICH_AVAILABLE:
            return self._run_rich()
        else:
            return self._run_simple()

    def _run_rich(self) -> int:
        """Rich UIで実行"""
        console.clear()

        # ヘッダー
        header = Text()
        header.append("╭─", style="blue")
        header.append(" JLTSQL ", style="bold white")
        header.append("─╮", style="blue")
        console.print()
        console.print(Panel(
            "[bold]JRA-VAN DataLab → SQLite[/bold]\n"
            "[dim]競馬データベース自動セットアップ[/dim]",
            title="[bold blue]JLTSQL[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        ))
        console.print()

        # セットアップ内容
        steps_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        steps_table.add_column("Step", style="cyan", width=4)
        steps_table.add_column("Description")

        steps = [
            ("1.", "プロジェクト初期化"),
            ("2.", "テーブル作成 (57テーブル)"),
            ("3.", "インデックス作成 (61個)"),
            ("4.", "データ取得 (全20スペック)"),
        ]
        if not self.args.no_monitor:
            steps.append(("5.", "リアルタイム監視開始"))

        for num, desc in steps:
            steps_table.add_row(num, desc)

        console.print(steps_table)
        console.print()

        # 設定情報
        info_table = Table(show_header=False, box=None, padding=(0, 1))
        info_table.add_column("Key", style="dim")
        info_table.add_column("Value", style="white")

        if self.args._years_used:
            info_table.add_row("期間", f"過去{self.args.years}年間")
        info_table.add_row("開始", self.args.from_date)
        info_table.add_row("終了", self.args.to_date)
        if self.args.no_odds:
            info_table.add_row("オッズ", "[yellow]除外[/yellow]")

        console.print(Panel(info_table, title="[dim]設定[/dim]", border_style="dim"))
        console.print()

        # 確認
        if not self._confirm_rich():
            console.print("[yellow]キャンセルしました[/yellow]")
            return 0

        console.print()

        # 実行
        with Progress(
            SpinnerColumn(),
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
        if not self._run_fetch_all_rich():
            self._print_summary_rich(success=False)
            return 1

        # 6. リアルタイム監視
        if not self.args.no_monitor:
            console.print()
            with console.status("[cyan]リアルタイム監視を開始中...", spinner="dots"):
                if not self._run_monitor():
                    self.warnings.append("リアルタイム監視の起動に失敗")

        # 完了
        self._print_summary_rich(success=True)
        return 0

    def _confirm_rich(self) -> bool:
        """Rich UIで確認"""
        if self.args.yes:
            return True
        try:
            return Confirm.ask("[bold]セットアップを開始しますか？[/bold]", default=True)
        except (KeyboardInterrupt, EOFError):
            return False

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
            checks.append(("JV-Link", "インストール済み", True))
        except Exception:
            checks.append(("JV-Link", "未インストール", False))
            has_error = True

        # 結果表示
        for name, value, ok in checks:
            status = "[green]✓[/green]" if ok else "[red]✗[/red]"
            console.print(f"  {status} {name}: {value}")

        return not has_error

    def _run_fetch_all_rich(self) -> bool:
        """データ取得（Rich UI）"""
        specs_to_fetch = self.DATA_SPECS.copy()
        if not self.args.no_odds:
            specs_to_fetch.extend(self.ODDS_SPECS)

        total_specs = len(specs_to_fetch)

        console.print()
        console.print(Panel(
            f"[bold]データ取得[/bold] ({total_specs}スペック)",
            border_style="blue",
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:

            main_task = progress.add_task(
                f"[cyan]データ取得中...",
                total=total_specs
            )

            for idx, (spec, description, option) in enumerate(specs_to_fetch, 1):
                progress.update(
                    main_task,
                    description=f"[cyan]{spec}: {description}"
                )

                success = self._fetch_single_spec(spec, option)

                if success:
                    self.stats['specs_success'] += 1
                else:
                    self.stats['specs_failed'] += 1

                progress.update(main_task, advance=1)
                time.sleep(0.5)  # API負荷軽減

        return self.stats['specs_success'] > 0

    def _print_summary_rich(self, success: bool):
        """サマリー出力（Rich版）"""
        console.print()

        if success:
            console.print(Panel(
                "[bold green]セットアップ完了！[/bold green]",
                border_style="green",
            ))

            # 統計
            if self.stats['specs_success'] > 0:
                stats_table = Table(show_header=False, box=None)
                stats_table.add_column("", style="dim")
                stats_table.add_column("")
                stats_table.add_row("成功", f"[green]{self.stats['specs_success']}[/green]")
                stats_table.add_row("失敗", f"[red]{self.stats['specs_failed']}[/red]")
                console.print(stats_table)

            # 次のステップ
            console.print()
            console.print("[dim]次のステップ:[/dim]")
            console.print("  [cyan]jltsql status[/cyan]    - ステータス確認")
            console.print("  [cyan]jltsql export[/cyan]    - データエクスポート")
            if not self.args.no_monitor:
                console.print("  [cyan]jltsql monitor --stop[/cyan] - 監視停止")
        else:
            console.print(Panel(
                "[bold red]セットアップ失敗[/bold red]",
                border_style="red",
            ))

            if self.errors:
                console.print()
                console.print("[red]エラー:[/red]")
                for error in self.errors[:5]:  # 最初の5件のみ
                    safe_error = str(error)[:80]
                    console.print(f"  [dim]•[/dim] {safe_error}")

        console.print()

    # === シンプル版（richなしの場合）===

    def _run_simple(self) -> int:
        """シンプルなテキストUIで実行（richなしの場合）"""
        print("=" * 60)
        print("JLTSQL セットアップ")
        print("=" * 60)
        print()
        print(f"期間: {self.args.from_date} ～ {self.args.to_date}")
        print()

        if not self._confirm_simple():
            print("キャンセルしました。")
            return 0

        # 1. 前提条件
        print("\n[1/5] 前提条件チェック...")
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

        # 6. 監視
        if not self.args.no_monitor:
            print("\nリアルタイム監視を開始中...")
            self._run_monitor()

        print("\n" + "=" * 60)
        print("セットアップ完了！")
        print("=" * 60)
        return 0

    def _confirm_simple(self) -> bool:
        """シンプルな確認"""
        if self.args.yes:
            return True
        try:
            response = input("実行しますか？ [Y/n]: ").strip().lower()
            return response in ('', 'y', 'yes')
        except (KeyboardInterrupt, EOFError):
            return False

    def _check_prerequisites_simple(self) -> bool:
        """前提条件チェック（シンプル版）"""
        has_error = False

        # Python
        v = sys.version_info
        if v >= (3, 10):
            print(f"  [OK] Python {v.major}.{v.minor}")
        else:
            print(f"  [NG] Python {v.major}.{v.minor} (3.10以上が必要)")
            has_error = True

        # OS
        if sys.platform == "win32":
            print("  [OK] Windows")
        else:
            print(f"  [NG] {sys.platform} (Windowsが必要)")
            has_error = True

        # JV-Link
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
        specs = self.DATA_SPECS.copy()
        if not self.args.no_odds:
            specs.extend(self.ODDS_SPECS)

        total = len(specs)
        for idx, (spec, desc, option) in enumerate(specs, 1):
            print(f"  [{idx}/{total}] {spec}: {desc}...", end=" ", flush=True)

            if self._fetch_single_spec(spec, option):
                self.stats['specs_success'] += 1
                print("OK")
            else:
                self.stats['specs_failed'] += 1
                print("SKIP")

            time.sleep(0.5)

        print(f"\n  完了: {self.stats['specs_success']}/{total}")
        return self.stats['specs_success'] > 0

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

    def _fetch_single_spec(self, spec: str, option: int) -> bool:
        """単一データスペック取得"""
        try:
            cmd = [
                sys.executable, "-m", "src.cli.main", "fetch",
                "--from", self.args.from_date,
                "--to", self.args.to_date,
                "--spec", spec,
                "--option", str(option),
            ]
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=600,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            self.errors.append(f"{spec}: タイムアウト")
            return False
        except Exception as e:
            self.errors.append(f"{spec}: {str(e)[:100]}")
            return False

    def _run_monitor(self) -> bool:
        """リアルタイム監視開始"""
        try:
            cmd = [sys.executable, "-m", "src.cli.main", "monitor", "--daemon"]
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

    parser.add_argument("--years", type=int, default=10, help="過去N年間 (デフォルト: 10)")
    parser.add_argument("--from", dest="from_date", default=None, help="開始日 (YYYYMMDD)")
    parser.add_argument("--to", dest="to_date", default=None, help="終了日 (YYYYMMDD)")
    parser.add_argument("--no-odds", action="store_true", help="オッズ除外")
    parser.add_argument("--no-monitor", action="store_true", help="監視なし")
    parser.add_argument("-y", "--yes", action="store_true", help="確認スキップ")

    args = parser.parse_args()

    # 期間計算
    today = datetime.now()
    args._years_used = (args.from_date is None)

    if args.from_date is None:
        args.from_date = (today - timedelta(days=365 * args.years)).strftime("%Y%m%d")
    if args.to_date is None:
        args.to_date = today.strftime("%Y%m%d")

    # 日付検証
    try:
        datetime.strptime(args.from_date, "%Y%m%d")
        datetime.strptime(args.to_date, "%Y%m%d")
    except ValueError:
        parser.error("日付は YYYYMMDD 形式で指定してください")

    # 実行
    try:
        with ProcessLock("quickstart"):
            runner = QuickstartRunner(args)
            sys.exit(runner.run())
    except ProcessLockError as e:
        if RICH_AVAILABLE:
            console.print(f"[red]エラー: {e}[/red]")
        else:
            print(f"エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
