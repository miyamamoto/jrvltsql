#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""完全データセットアップスクリプト

指定年以降の全データを一括取得し、リアルタイム監視まで自動セットアップします。

使用例:
    # 2024年以降の全データを取得
    python scripts/setup_full_data.py --from-year 2024

    # 2024年以降 + オッズデータも取得
    python scripts/setup_full_data.py --from-year 2024 --with-odds

    # 2024年以降 + リアルタイム監視も開始
    python scripts/setup_full_data.py --from-year 2024 --start-monitor
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class FullDataSetup:
    """完全データセットアップクラス"""

    def __init__(self, args):
        self.args = args
        self.project_root = Path(__file__).parent.parent
        self.current_year = datetime.now().year
        self.errors = []

    def run(self) -> int:
        """セットアップ実行"""
        print("=" * 70)
        print("JLTSQL 完全データセットアップ")
        print("=" * 70)
        print()
        print(f"取得期間: {self.args.from_year}年 ～ {self.current_year}年")
        print(f"データ仕様: DIFF (マスタ) + RACE (レース)")
        if self.args.with_odds:
            print(f"オッズ: O1, O2, O6")
        if self.args.start_monitor:
            print(f"リアルタイム監視: 有効")
        print()

        # 確認
        if not self.args.yes:
            response = input("続行しますか? [y/N]: ")
            if response.lower() != 'y':
                print("キャンセルしました。")
                return 0

        # Phase 1: 基本セットアップ
        if not self._run_quickstart():
            return 1

        # Phase 2: 年次データ取得
        years = range(self.args.from_year, self.current_year + 1)
        for year in years:
            print()
            print(f"{'=' * 70}")
            print(f"  {year}年データ取得")
            print(f"{'=' * 70}")
            print()

            # DIFF (マスタデータ)
            if not self._load_year_data(year, "DIFF"):
                self.errors.append(f"{year}年 DIFF取得失敗")
                if not self.args.continue_on_error:
                    return 1

            # RACE (レースデータ)
            if not self._load_year_data(year, "RACE"):
                self.errors.append(f"{year}年 RACE取得失敗")
                if not self.args.continue_on_error:
                    return 1

            # オッズデータ (オプション)
            if self.args.with_odds:
                for odds_spec in ["O1", "O2", "O6"]:
                    if not self._load_year_data(year, odds_spec):
                        self.errors.append(f"{year}年 {odds_spec}取得失敗")
                        if not self.args.continue_on_error:
                            return 1

        # Phase 3: リアルタイム監視開始 (オプション)
        if self.args.start_monitor:
            print()
            print(f"{'=' * 70}")
            print(f"  リアルタイム監視開始")
            print(f"{'=' * 70}")
            print()
            self._start_monitor()

        # 完了サマリー
        self._print_summary()
        return 0 if not self.errors else 1

    def _run_quickstart(self) -> bool:
        """基本セットアップ実行"""
        print("Phase 1: 基本セットアップ")
        print("-" * 70)

        try:
            result = subprocess.run(
                [sys.executable, "scripts/quickstart.py"],
                cwd=self.project_root,
                timeout=120,
            )
            return result.returncode == 0
        except Exception as e:
            print(f"✗ セットアップ失敗: {e}")
            self.errors.append(f"基本セットアップ失敗: {e}")
            return False

    def _load_year_data(self, year: int, spec: str) -> bool:
        """年次データ取得"""
        print(f"  取得中: {year}年 {spec}")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/load_year_data.py",
                    "--year", str(year),
                    "--spec", spec,
                    "--db", self.args.db,
                ],
                cwd=self.project_root,
                timeout=1800,  # 30分
            )

            if result.returncode == 0:
                print(f"  ✓ {year}年 {spec} 完了")
                return True
            else:
                print(f"  ✗ {year}年 {spec} 失敗")
                return False

        except subprocess.TimeoutExpired:
            print(f"  ✗ {year}年 {spec} タイムアウト")
            return False
        except Exception as e:
            print(f"  ✗ {year}年 {spec} エラー: {e}")
            return False

    def _start_monitor(self):
        """リアルタイム監視開始"""
        print("リアルタイム監視をバックグラウンドで開始します...")

        try:
            subprocess.Popen(
                [sys.executable, "-m", "src.cli.main", "monitor", "--daemon"],
                cwd=self.project_root,
            )
            print("✓ リアルタイム監視を開始しました")
            print()
            print("停止するには: jltsql stop")
        except Exception as e:
            print(f"✗ 監視開始失敗: {e}")
            self.errors.append(f"監視開始失敗: {e}")

    def _print_summary(self):
        """サマリー出力"""
        print()
        print("=" * 70)
        print("セットアップ完了")
        print("=" * 70)

        if self.errors:
            print()
            print("⚠ エラーが発生しました:")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print()
            print("✓ 全てのデータ取得が完了しました！")

        print()
        print("次のステップ:")
        print("  1. データ確認: jltsql status")
        print("  2. データエクスポート: jltsql export --table NL_RA --output races.csv")
        if not self.args.start_monitor:
            print("  3. リアルタイム監視: jltsql monitor --daemon")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="JLTSQL 完全データセットアップ - 指定年以降の全データを一括取得",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 2024年以降の全データを取得
  python scripts/setup_full_data.py --from-year 2024

  # 2024年以降 + オッズデータも取得
  python scripts/setup_full_data.py --from-year 2024 --with-odds

  # 2024年以降 + リアルタイム監視も開始
  python scripts/setup_full_data.py --from-year 2024 --start-monitor

  # 確認なしで自動実行
  python scripts/setup_full_data.py --from-year 2024 -y

処理内容:
  1. 基本セットアップ (init + create-tables + create-indexes)
  2. 各年のDIFF (マスタデータ) 取得
  3. 各年のRACE (レースデータ) 取得
  4. オプション: 各年のオッズデータ取得
  5. オプション: リアルタイム監視開始

データ仕様:
  DIFF : マスタデータ (競走馬、騎手、調教師など)
  RACE : レースデータ (レース詳細、出走馬、払戻)
  O1   : 単勝・複勝オッズ
  O2   : 馬連オッズ
  O6   : 3連複・3連単オッズ
        """,
    )

    parser.add_argument(
        "--from-year",
        type=int,
        required=True,
        help="データ取得開始年 (例: 2024)",
    )

    parser.add_argument(
        "--db",
        choices=["sqlite", "duckdb"],
        default="duckdb",
        help="データベースタイプ (デフォルト: duckdb)",
    )

    parser.add_argument(
        "--with-odds",
        action="store_true",
        help="オッズデータ (O1, O2, O6) も取得する",
    )

    parser.add_argument(
        "--start-monitor",
        action="store_true",
        help="データ取得後、リアルタイム監視を開始する",
    )

    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="確認なしで実行",
    )

    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="エラーが発生しても続行する",
    )

    args = parser.parse_args()

    # 検証
    current_year = datetime.now().year
    if args.from_year < 1986:
        parser.error("1986年以降の年を指定してください")
    if args.from_year > current_year:
        parser.error(f"{current_year}年以前の年を指定してください")

    # 実行
    setup = FullDataSetup(args)
    sys.exit(setup.run())


if __name__ == "__main__":
    main()
