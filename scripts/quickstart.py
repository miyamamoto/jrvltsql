#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""JLTSQL Quick Start Script - 完全自動セットアップ

このスクリプトはJLTSQLの完全自動セットアップを実行します：
1. プロジェクト初期化
2. テーブル・インデックス作成
3. すべてのデータ取得（蓄積系データ）
4. リアルタイム監視の開始

使用例:
    # デフォルト: 直近1ヶ月のデータ + リアルタイム監視
    python scripts/quickstart.py

    # データ期間を指定
    python scripts/quickstart.py --from 20240101 --to 20241231

    # リアルタイム監視なし（データ取得のみ）
    python scripts/quickstart.py --no-monitor

    # オッズデータを除外
    python scripts/quickstart.py --no-odds
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

from src.utils.lock_manager import ProcessLock, ProcessLockError


class QuickstartRunner:
    """完全自動セットアップ実行クラス"""

    # すべてのデータスペック（優先順位順）
    DATA_SPECS = [
        ("DIFN", "マスタ情報（新）", 1),      # 競走馬、騎手、調教師マスタ
        ("BLDN", "血統情報（新）", 1),        # 血統、繁殖馬
        ("RACE", "レース情報", 1),           # レース詳細、出馬表、払戻
        ("YSCH", "開催スケジュール", 1),      # 開催スケジュール
        ("TOKU", "特別登録", 1),             # 特別登録馬
        ("JGDW", "重賞情報", 1),             # 重賞グレード情報
        ("HOSN", "市場取引（新）", 2),        # 市場取引価格
        ("COMM", "各種解説", 2),             # コメント
        ("SNPN", "速報情報（新）", 2),        # 速報情報
        ("0B11", "データマイニング", 2),      # データマイニング予想
        ("0B20", "成績", 2),                 # 成績データ
        ("0B31", "払戻", 2),                 # 異常配当情報
        ("0B41", "繁殖牝馬", 1),             # 繁殖牝馬情報
    ]

    # オッズデータスペック（全6種類）
    ODDS_SPECS = [
        ("SLOP", "単勝・複勝オッズ", 2),
        ("HOYU", "馬連・ワイドオッズ", 2),
        ("O4", "枠連オッズ", 2),
        ("O5", "馬単オッズ", 2),
        ("O6", "3連複・3連単オッズ", 2),
        ("WOOD", "ウッドチップ調教", 2),
        ("MING", "レース当日発表", 2),
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
        print("=" * 80)
        print("JLTSQL 完全自動セットアップ")
        print("=" * 80)
        print()
        print("このスクリプトは以下を実行します:")
        print("  1. プロジェクト初期化")
        print("  2. データベーステーブル作成（57テーブル: NL_38 + RT_19）")
        print("  3. インデックス作成（61インデックス）")
        print("  4. 全データ取得（蓄積系データ → NL_テーブル）")
        if not self.args.no_monitor:
            print("  5. リアルタイム監視開始（速報データ → RT_テーブル）")
        print()

        # 期間表示（--fromが手動指定されていない場合のみ「過去X年間」を表示）
        if self.args._years_used:
            print(f"データ期間: 過去{self.args.years}年間 ({self.args.from_date} ～ {self.args.to_date})")
        else:
            print(f"データ期間: {self.args.from_date} ～ {self.args.to_date}")

        if self.args.no_odds:
            print("オッズデータ: 除外")
        print()

        if not self._confirm():
            print("キャンセルしました。")
            return 0

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

        # 5. 全データ取得
        if not self._run_fetch_all():
            self._print_summary(success=False)
            return 1

        # 6. リアルタイム監視開始
        if not self.args.no_monitor:
            if not self._run_monitor():
                self.warnings.append("リアルタイム監視の起動に失敗しました")

        # 7. ステータス確認
        self._run_status()

        # 完了
        self._print_summary(success=True)
        return 0

    def _confirm(self) -> bool:
        """実行確認"""
        if self.args.yes:
            return True

        try:
            response = input("実行しますか？ [Y/n]: ").strip().lower()
            return response in ('', 'y', 'yes')
        except (KeyboardInterrupt, EOFError):
            print()
            return False

    def _check_prerequisites(self) -> bool:
        """前提条件チェック"""
        print("[1/7] 前提条件チェック")
        print("-" * 80)

        has_error = False

        # Python バージョンチェック
        python_version = sys.version_info
        if python_version >= (3, 10):
            print(f"  [OK] Python {python_version.major}.{python_version.minor}")
        else:
            print(f"  [NG] Python {python_version.major}.{python_version.minor} (3.10以上が必要)")
            self.errors.append("Python 3.10以上が必要です")
            has_error = True

        # OS チェック
        if sys.platform == "win32":
            print("  [OK] Windows OS")
        else:
            print(f"  [NG] {sys.platform} (JV-LinkはWindows専用)")
            self.errors.append("WindowsOSが必要です")
            has_error = True

        # JV-Link チェック
        try:
            import win32com.client
            win32com.client.Dispatch("JVDTLab.JVLink")
            print("  [OK] JV-Link COM API")
        except Exception as e:
            print(f"  [NG] JV-Link COM API")
            self.errors.append(f"JV-Linkがインストールされていません: {e}")
            has_error = True

        # config.yaml チェック
        config_path = self.project_root / "config" / "config.yaml"
        if config_path.exists():
            print(f"  [OK] 設定ファイル")
        else:
            print(f"  [!!] 設定ファイル未作成（自動作成します）")

        print()
        return not has_error

    def _run_init(self) -> bool:
        """プロジェクト初期化"""
        print("[2/7] プロジェクト初期化")
        print("-" * 80)

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

            if result.returncode == 0:
                print("  [OK] 初期化完了")
                print()
                return True
            else:
                print(f"  [NG] 初期化失敗")
                self.errors.append(f"初期化失敗: {result.stderr}")
                print()
                return False

        except Exception as e:
            print(f"  [NG] 初期化エラー: {e}")
            self.errors.append(f"初期化エラー: {e}")
            print()
            return False

    def _run_create_tables(self) -> bool:
        """テーブル作成"""
        print("[3/7] データベーステーブル作成（57テーブル: NL_38 + RT_19）")
        print("-" * 80)

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

            if result.returncode == 0:
                print("  [OK] テーブル作成完了")
                print()
                return True
            else:
                print(f"  [NG] テーブル作成失敗")
                self.errors.append(f"テーブル作成失敗: {result.stderr}")
                print()
                return False

        except Exception as e:
            print(f"  [NG] テーブル作成エラー: {e}")
            self.errors.append(f"テーブル作成エラー: {e}")
            print()
            return False

    def _run_create_indexes(self) -> bool:
        """インデックス作成"""
        print("[4/7] データベースインデックス作成（61インデックス）")
        print("-" * 80)

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

            if result.returncode == 0:
                print("  [OK] インデックス作成完了")
                print()
                return True
            else:
                print(f"  [NG] インデックス作成失敗")
                self.errors.append(f"インデックス作成失敗: {result.stderr}")
                print()
                return False

        except Exception as e:
            print(f"  [NG] インデックス作成エラー: {e}")
            self.errors.append(f"インデックス作成エラー: {e}")
            print()
            return False

    def _run_fetch_all(self) -> bool:
        """全データ取得"""
        print("[5/7] 全データ取得")
        print("-" * 80)
        print()

        # データスペックリストを作成
        specs_to_fetch = self.DATA_SPECS.copy()
        if not self.args.no_odds:
            specs_to_fetch.extend(self.ODDS_SPECS)

        total_specs = len(specs_to_fetch)

        for idx, (spec, description, option) in enumerate(specs_to_fetch, 1):
            print(f"  [{idx}/{total_specs}] {spec}: {description}")
            print(f"      期間: {self.args.from_date} ～ {self.args.to_date}")

            success = self._fetch_single_spec(spec, option)

            if success:
                self.stats['specs_success'] += 1
                print(f"      [OK] 完了")
            else:
                self.stats['specs_failed'] += 1
                print(f"      [!!] スキップ（データなしまたはエラー）")

            print()
            time.sleep(1)  # API負荷軽減

        print()
        print(f"  データ取得完了: {self.stats['specs_success']}/{total_specs} 成功")
        print()
        return self.stats['specs_success'] > 0

    def _fetch_single_spec(self, spec: str, option: int) -> bool:
        """単一データスペック取得"""
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
                spec,
                "--option",
                str(option),
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Unicode decoding errors を無視
                timeout=600,  # 10分
            )

            # エラー詳細をログ
            if result.returncode != 0:
                if result.stderr:
                    # デバッグ用にエラーを記録（本番では表示しない）
                    self.errors.append(f"{spec}: {result.stderr[:200]}")

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            self.errors.append(f"{spec}: タイムアウト")
            return False
        except Exception as e:
            self.errors.append(f"{spec}: {str(e)[:200]}")
            return False

    def _run_monitor(self) -> bool:
        """リアルタイム監視開始"""
        print("[6/7] リアルタイム監視開始")
        print("-" * 80)

        try:
            # バックグラウンドで監視開始
            cmd = [
                sys.executable,
                "-m",
                "src.cli.main",
                "monitor",
                "--daemon",
            ]

            result = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            time.sleep(2)  # 起動待ち

            if result.poll() is None:
                print("  [OK] リアルタイム監視を開始しました")
                print()
                return True
            else:
                print("  [!!] リアルタイム監視の起動に失敗しました")
                print()
                return False

        except Exception as e:
            print(f"  [!!] リアルタイム監視エラー: {e}")
            print()
            return False

    def _run_status(self) -> bool:
        """ステータス確認"""
        step = "7/7"
        print(f"[{step}] ステータス確認")
        print("-" * 80)
        print()

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
            print(f"  [!!] ステータス確認エラー: {e}")
            print()
            return False

    def _print_summary(self, success: bool):
        """サマリー出力"""
        print("=" * 80)
        if success:
            print("[OK] セットアップ完了！")
        else:
            print("[NG] セットアップ失敗")
        print("=" * 80)
        print()

        # 統計情報
        if self.stats['specs_success'] > 0:
            print("[STAT] データ取得統計:")
            print(f"  成功: {self.stats['specs_success']}")
            print(f"  失敗: {self.stats['specs_failed']}")
            print()

        # 警告
        if self.warnings:
            print("[!!] 警告:")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()

        # エラー
        if self.errors:
            print("[NG] エラー:")
            for error in self.errors:
                # Unicode文字をASCII安全に変換
                safe_error = str(error).encode('ascii', 'replace').decode('ascii')
                print(f"  - {safe_error}")
            print()

        # 次のステップ
        if success:
            print("[NEXT] 次のステップ:")
            print("  1. データ確認: jltsql export --table NL_RA --output races.csv")
            if not self.args.no_monitor:
                print("  2. 監視状況確認: jltsql status")
                print("  3. 監視停止: jltsql monitor --stop")
            print()
            print("詳細: jltsql --help")
        else:
            print("問題を解決後、再度実行してください。")
        print()


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="JLTSQL 完全自動セットアップ - すべてのデータ取得 + リアルタイム監視",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # デフォルト: 直近10年間のデータ + リアルタイム監視
  python scripts/quickstart.py

  # 過去5年間のデータを取得
  python scripts/quickstart.py --years 5

  # 過去20年間のデータを取得
  python scripts/quickstart.py --years 20

  # データ期間を直接指定
  python scripts/quickstart.py --from 20240101 --to 20241231

  # リアルタイム監視なし
  python scripts/quickstart.py --no-monitor

  # オッズデータを除外
  python scripts/quickstart.py --no-odds

  # 確認なしで実行
  python scripts/quickstart.py --yes

取得されるデータ:
  - マスタデータ（競走馬、騎手、調教師、血統等）
  - レース情報（レース詳細、出馬表、払戻）
  - スケジュール、特別登録
  - オッズデータ（--no-oddsで除外可能）
  - リアルタイム監視（--no-monitorで除外可能）
        """,
    )

    parser.add_argument(
        "--years",
        type=int,
        default=10,
        metavar="N",
        help="過去N年間のデータを取得（デフォルト: 10年）",
    )

    parser.add_argument(
        "--from",
        dest="from_date",
        default=None,
        metavar="YYYYMMDD",
        help="データ取得開始日（--years より優先）",
    )

    parser.add_argument(
        "--to",
        dest="to_date",
        default=None,
        metavar="YYYYMMDD",
        help="データ取得終了日（デフォルト: 今日）",
    )

    parser.add_argument(
        "--no-odds",
        action="store_true",
        help="オッズデータを除外",
    )

    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="リアルタイム監視を開始しない",
    )

    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="確認なしで実行",
    )

    args = parser.parse_args()

    # デフォルト期間を計算
    today = datetime.now()

    # --fromが手動指定されたかを記録
    args._years_used = (args.from_date is None)

    # --from が指定されていない場合、--years から計算
    if args.from_date is None:
        args.from_date = (today - timedelta(days=365 * args.years)).strftime("%Y%m%d")

    # --to が指定されていない場合、今日
    if args.to_date is None:
        args.to_date = today.strftime("%Y%m%d")

    # 日付形式チェック
    try:
        datetime.strptime(args.from_date, "%Y%m%d")
        datetime.strptime(args.to_date, "%Y%m%d")
    except ValueError:
        parser.error("日付は YYYYMMDD 形式で指定してください (例: 20240101)")

    # セットアップ実行（プロセスロック付き）
    try:
        with ProcessLock("quickstart"):
            runner = QuickstartRunner(args)
            sys.exit(runner.run())
    except ProcessLockError as e:
        print()
        print("[NG] " + str(e))
        print()
        print("他のquickstartプロセスが実行中です。")
        print("完了まで待つか、手動でロックファイルを削除してください。")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
