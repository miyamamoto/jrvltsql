#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""JLTSQL Quick Start Script

このスクリプトはJLTSQLの初期セットアップを自動化します。

使用例:
    # 基本セットアップのみ (init + create-tables + create-indexes)
    python scripts/quickstart.py

    # サンプルデータ取得も実行
    python scripts/quickstart.py --fetch --from 20240101 --to 20240131 --spec RACE

    # 全自動セットアップ (マスタデータも取得)
    python scripts/quickstart.py --fetch --from 20240101 --to 20240131 --spec DIFF
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class QuickstartRunner:
    """クイックスタート実行クラス"""

    def __init__(self, args):
        self.args = args
        self.project_root = Path(__file__).parent.parent
        self.errors = []
        self.warnings = []

    def run(self) -> int:
        """クイックスタート実行

        Returns:
            終了コード (0: 成功, 1: エラー)
        """
        print("=" * 70)
        print("JLTSQL Quick Start")
        print("=" * 70)
        print()

        # 1. 前提条件チェック
        if not self._check_prerequisites():
            self._print_summary(success=False)
            return 1

        # 2. プロジェクト初期化
        if not self._run_init():
            self._print_summary(success=False)
            return 1

        # 3. テーブル作成
        if not self._run_create_tables():
            self._print_summary(success=False)
            return 1

        # 4. インデックス作成
        if not self._run_create_indexes():
            self._print_summary(success=False)
            return 1

        # 5. データ取得 (オプション)
        if self.args.fetch:
            if not self._run_fetch():
                self._print_summary(success=False)
                return 1

        # 6. ステータス確認
        self._run_status()

        # 完了
        self._print_summary(success=True)
        return 0

    def _check_prerequisites(self) -> bool:
        """前提条件チェック

        Returns:
            True: 全チェックOK, False: エラーあり
        """
        print("Step 1/6: 前提条件チェック")
        print("-" * 70)

        has_error = False

        # Python バージョンチェック
        python_version = sys.version_info
        if python_version >= (3, 10):
            print(f"✓ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        else:
            print(f"✗ Python {python_version.major}.{python_version.minor}.{python_version.micro} (3.10以上が必要)")
            self.errors.append("Python 3.10以上が必要です")
            has_error = True

        # OS チェック (Windows)
        if sys.platform == "win32":
            print("✓ Windows OS")
        else:
            print(f"✗ {sys.platform} (JV-LinkはWindows専用)")
            self.errors.append("WindowsOSが必要です")
            has_error = True

        # JV-Link チェック (win32comが利用可能か)
        try:
            import win32com.client
            win32com.client.Dispatch("JVDTLab.JVLink")
            print("✓ JV-Link COM API")
        except Exception as e:
            print(f"✗ JV-Link COM API ({e})")
            self.warnings.append("JV-Linkがインストールされていません（データ取得時に必要）")

        # config.yaml チェック
        config_path = self.project_root / "config" / "config.yaml"
        if config_path.exists():
            print(f"✓ 設定ファイル: {config_path}")
        else:
            print(f"⚠ 設定ファイル未作成: {config_path}")
            self.warnings.append("config/config.yamlを作成してください（jltsql initで自動作成）")

        print()
        return not has_error

    def _run_init(self) -> bool:
        """プロジェクト初期化実行

        Returns:
            True: 成功, False: 失敗
        """
        print("Step 2/6: プロジェクト初期化")
        print("-" * 70)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "src.cli.main", "init"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print("✓ プロジェクト初期化完了")
                print()
                return True
            else:
                print(f"✗ 初期化失敗: {result.stderr}")
                self.errors.append(f"初期化失敗: {result.stderr}")
                print()
                return False

        except Exception as e:
            print(f"✗ 初期化エラー: {e}")
            self.errors.append(f"初期化エラー: {e}")
            print()
            return False

    def _run_create_tables(self) -> bool:
        """テーブル作成実行

        Returns:
            True: 成功, False: 失敗
        """
        print("Step 3/6: データベーステーブル作成 (57テーブル)")
        print("-" * 70)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "src.cli.main", "create-tables"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                print("✓ テーブル作成完了 (NL_*: 38, RT_*: 19)")
                print()
                return True
            else:
                print(f"✗ テーブル作成失敗: {result.stderr}")
                self.errors.append(f"テーブル作成失敗: {result.stderr}")
                print()
                return False

        except Exception as e:
            print(f"✗ テーブル作成エラー: {e}")
            self.errors.append(f"テーブル作成エラー: {e}")
            print()
            return False

    def _run_create_indexes(self) -> bool:
        """インデックス作成実行

        Returns:
            True: 成功, False: 失敗
        """
        print("Step 4/6: データベースインデックス作成 (120+インデックス)")
        print("-" * 70)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "src.cli.main", "create-indexes"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                print("✓ インデックス作成完了")
                print()
                return True
            else:
                print(f"✗ インデックス作成失敗: {result.stderr}")
                self.errors.append(f"インデックス作成失敗: {result.stderr}")
                print()
                return False

        except Exception as e:
            print(f"✗ インデックス作成エラー: {e}")
            self.errors.append(f"インデックス作成エラー: {e}")
            print()
            return False

    def _run_fetch(self) -> bool:
        """データ取得実行

        Returns:
            True: 成功, False: 失敗
        """
        print(f"Step 5/6: データ取得 ({self.args.spec}: {self.args.from_date} ~ {self.args.to_date})")
        print("-" * 70)

        try:
            cmd = [
                sys.executable,
                "-m",
                "src.cli.main",
                "fetch",
                "--from",
                self.args.from_date,
                "--to",
                self.args.to_date,
                "--spec",
                self.args.spec,
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=False,  # リアルタイム出力
                text=True,
                timeout=600,  # 10分
            )

            if result.returncode == 0:
                print("✓ データ取得完了")
                print()
                return True
            else:
                print("✗ データ取得失敗")
                self.errors.append("データ取得失敗")
                print()
                return False

        except subprocess.TimeoutExpired:
            print("✗ データ取得タイムアウト (10分)")
            self.errors.append("データ取得タイムアウト")
            print()
            return False
        except Exception as e:
            print(f"✗ データ取得エラー: {e}")
            self.errors.append(f"データ取得エラー: {e}")
            print()
            return False

    def _run_status(self) -> bool:
        """ステータス確認実行

        Returns:
            True: 成功, False: 失敗
        """
        step = "6/6" if self.args.fetch else "5/6"
        print(f"Step {step}: ステータス確認")
        print("-" * 70)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "src.cli.main", "status"],
                cwd=self.project_root,
                capture_output=False,
                text=True,
                timeout=30,
            )

            print()
            return result.returncode == 0

        except Exception as e:
            print(f"⚠ ステータス確認エラー: {e}")
            print()
            return False

    def _print_summary(self, success: bool):
        """サマリー出力

        Args:
            success: 成功フラグ
        """
        print("=" * 70)
        if success:
            print("✓ クイックスタート完了!")
        else:
            print("✗ クイックスタート失敗")
        print("=" * 70)

        if self.warnings:
            print()
            print("⚠ 警告:")
            for warning in self.warnings:
                print(f"  - {warning}")

        if self.errors:
            print()
            print("✗ エラー:")
            for error in self.errors:
                print(f"  - {error}")

        print()
        if success:
            print("次のステップ:")
            if not self.args.fetch:
                print("  1. データ取得: jltsql fetch --from YYYYMMDD --to YYYYMMDD --spec RACE")
                print("  2. リアルタイム監視: jltsql monitor --daemon")
            else:
                print("  1. データ確認: jltsql export --table NL_RA --output races.csv")
                print("  2. リアルタイム監視: jltsql monitor --daemon")
            print()
            print("詳細: jltsql --help")
        else:
            print("問題を解決後、再度実行してください。")
        print()


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="JLTSQL Quick Start - 初期セットアップ自動化スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本セットアップ (init + create-tables + create-indexes)
  python scripts/quickstart.py

  # サンプルデータ取得も実行 (2024年1月のレースデータ)
  python scripts/quickstart.py --fetch --from 20240101 --to 20240131 --spec RACE

  # マスタデータも取得
  python scripts/quickstart.py --fetch --from 20240101 --to 20240131 --spec DIFF

データ仕様 (--spec):
  RACE : レース詳細データ
  DIFF : マスタ差分データ (競走馬、騎手、調教師など)
  YSCH : スケジュールデータ
  O1   : 単勝・複勝オッズ
  O2   : 馬連オッズ
  O3   : ワイドオッズ
  O4   : 枠連オッズ
  O5   : 馬単オッズ
  O6   : 3連複・3連単オッズ
        """,
    )

    parser.add_argument(
        "--fetch",
        action="store_true",
        help="データ取得も実行する",
    )

    parser.add_argument(
        "--from",
        dest="from_date",
        metavar="YYYYMMDD",
        help="データ取得開始日 (例: 20240101)",
    )

    parser.add_argument(
        "--to",
        dest="to_date",
        metavar="YYYYMMDD",
        help="データ取得終了日 (例: 20240131)",
    )

    parser.add_argument(
        "--spec",
        default="RACE",
        choices=["RACE", "DIFF", "YSCH", "O1", "O2", "O3", "O4", "O5", "O6"],
        help="データ仕様 (デフォルト: RACE)",
    )

    args = parser.parse_args()

    # データ取得オプションの検証
    if args.fetch:
        if not args.from_date or not args.to_date:
            parser.error("--fetch を指定する場合、--from と --to が必要です")

        # 日付形式チェック
        try:
            datetime.strptime(args.from_date, "%Y%m%d")
            datetime.strptime(args.to_date, "%Y%m%d")
        except ValueError:
            parser.error("日付は YYYYMMDD 形式で指定してください (例: 20240101)")

    # クイックスタート実行
    runner = QuickstartRunner(args)
    sys.exit(runner.run())


if __name__ == "__main__":
    main()
