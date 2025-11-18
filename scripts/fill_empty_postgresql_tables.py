#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PostgreSQL本番データベースの空テーブルを埋める

残り44個の空テーブルに対して、適切なデータスペックでデータを取得・格納
"""
import sys
import time
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.postgresql_handler import PostgreSQLDatabase
from src.fetcher.historical import HistoricalFetcher
from src.importer.importer import DataImporter
from src.parser.factory import ParserFactory
import structlog

logger = structlog.get_logger()

class EmptyTableFiller:
    """空テーブルを埋めるためのクラス"""

    def __init__(self):
        self.db_config = {
            "host": "localhost",
            "port": 5432,
            "database": "keiba",
            "user": "postgres",
            "password": "postgres",
        }
        self.service_key = "5UJC-VRFM-448X-F3V4-4"

    def get_empty_tables(self, db):
        """空テーブルのリストを取得"""
        result = db.fetch_all("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            AND (table_name LIKE 'nl_%' OR table_name LIKE 'rt_%')
            ORDER BY table_name
        """)

        empty_tables = []
        for row in result:
            table_name = row[0]
            count_result = db.fetch_one(f"SELECT COUNT(*) FROM {table_name}")
            if count_result and count_result[0] == 0:
                empty_tables.append(table_name.upper())

        return empty_tables

    def fetch_and_import(self, db, data_spec, from_date, option, max_records=10000):
        """データスペックからデータ取得してインポート

        Args:
            db: Database handler
            data_spec: データスペック (e.g., "DIFN", "RACE")
            from_date: 開始日 (YYYYMMDD 8桁形式)
            option: JVOpenオプション (0=通常, 1=セットアップ, 2=更新)
            max_records: 最大レコード数
        """
        print(f"\n[{data_spec}] {from_date} から取得 (option={option})...")

        try:
            fetcher = HistoricalFetcher(
                sid=f"FILL_{data_spec}",
                service_key=self.service_key,
                show_progress=False
            )

            # データ取得
            records = []
            for record in fetcher.fetch(
                data_spec=data_spec,
                from_date=from_date,
                to_date=None,
                option=option
            ):
                records.append(record)
                if len(records) >= max_records:
                    print(f"  ! 最大レコード数 ({max_records}) に達しました")
                    break

            if not records:
                stats = fetcher.get_statistics()
                print(f"  - データなし (エラーコード: {stats.get('last_error_code', 'N/A')})")
                return {}

            # インポート
            importer = DataImporter(db, batch_size=1000)
            import_stats = importer.import_records(records, auto_commit=True)

            print(f"  OK {import_stats['records_imported']:,} レコード挿入")
            print(f"     失敗: {import_stats['records_failed']:,}")

            # テーブル別統計
            table_stats = {}
            for table_name, count in import_stats.get('tables', {}).items():
                if count > 0:
                    table_stats[table_name] = count
                    print(f"     {table_name}: {count:,} レコード")

            return table_stats

        except Exception as e:
            print(f"  NG エラー: {e}")
            return {}

    def fill_tables(self):
        """空テーブルを埋める"""
        print("=" * 80)
        print("PostgreSQL 空テーブル埋めプロセス")
        print("=" * 80)

        db = PostgreSQLDatabase(self.db_config)
        db.connect()

        # 現在の空テーブルを確認
        print("\n[1/4] 空テーブル確認中...")
        empty_tables = self.get_empty_tables(db)
        print(f"  空テーブル数: {len(empty_tables)}")
        print(f"  リスト: {', '.join(empty_tables[:20])}")
        if len(empty_tables) > 20:
            print(f"         ... 他 {len(empty_tables) - 20} テーブル")

        # データスペック別に取得
        # 蓄積系データ (option=1)
        # - DIFN: マスタデータ (新)  → UM, CH, KS, BN, BR等
        # - BLDN: 血統情報 (新)     → HN, SK等
        # - YSCH: 開催スケジュール   → YS
        # - TOKU: 特別登録          → TK
        #
        # 速報系データ (option=2)
        # - SNAP: 速報レース詳細    → 変更系 (CC, JC, TC, WE, WH)
        # - HOSN: 市場取引 (新)     → AV
        # - COMM: 各種解説
        # - MING: レース当日発表

        print("\n[2/4] 蓄積系データ取得 (option=1)...")

        all_table_stats = defaultdict(int)

        # DIFNデータスペック
        stats = self.fetch_and_import(db, "DIFN", "20230101", option=1, max_records=15000)
        for table, count in stats.items():
            all_table_stats[table] += count

        # BLDNデータスペック
        stats = self.fetch_and_import(db, "BLDN", "20230101", option=1, max_records=15000)
        for table, count in stats.items():
            all_table_stats[table] += count

        # YSCHデータスペック
        stats = self.fetch_and_import(db, "YSCH", "20241001", option=1, max_records=5000)
        for table, count in stats.items():
            all_table_stats[table] += count

        # TOKUデータスペック
        stats = self.fetch_and_import(db, "TOKU", "20241001", option=1, max_records=5000)
        for table, count in stats.items():
            all_table_stats[table] += count

        print("\n[3/4] 速報系データ取得 (option=2)...")

        # SNAPデータスペック (直近1週間の速報)
        stats = self.fetch_and_import(db, "SNAP", "20241110", option=2, max_records=10000)
        for table, count in stats.items():
            all_table_stats[table] += count

        # HOSNデータスペック
        stats = self.fetch_and_import(db, "HOSN", "20230101", option=2, max_records=5000)
        for table, count in stats.items():
            all_table_stats[table] += count

        # MINGデータスペック
        stats = self.fetch_and_import(db, "MING", "20241110", option=2, max_records=5000)
        for table, count in stats.items():
            all_table_stats[table] += count

        print("\n[4/4] 最終統計確認...")

        # 最終結果
        result = db.fetch_all("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            AND (table_name LIKE 'nl_%' OR table_name LIKE 'rt_%')
            ORDER BY table_name
        """)

        filled_tables = []
        still_empty = []
        total_records = 0

        for row in result:
            table_name = row[0]
            count_result = db.fetch_one(f"SELECT COUNT(*) FROM {table_name}")
            count = count_result[0] if count_result else 0
            total_records += count

            if table_name.upper() in empty_tables and count > 0:
                filled_tables.append(f"{table_name.upper()}({count:,})")
            elif count == 0:
                still_empty.append(table_name.upper())

        print("\n" + "=" * 80)
        print("実行結果")
        print("=" * 80)

        print(f"\n今回埋まったテーブル ({len(filled_tables)}個):")
        if filled_tables:
            for i in range(0, len(filled_tables), 5):
                print("  " + ", ".join(filled_tables[i:i+5]))
        else:
            print("  (なし)")

        print(f"\nまだ空のテーブル ({len(still_empty)}個):")
        if still_empty:
            for i in range(0, len(still_empty), 5):
                print("  " + ", ".join(still_empty[i:i+5]))
        else:
            print("  (なし)")

        print(f"\n総レコード数: {total_records:,}")
        print(f"データを持つテーブル: {57 - len(still_empty)}/57")

        print("\n今回追加されたレコード数:")
        for table, count in sorted(all_table_stats.items()):
            print(f"  {table}: {count:,}")

        db.disconnect()

        print("\n" + "=" * 80)
        print("完了")
        print("=" * 80)

def main():
    filler = EmptyTableFiller()
    filler.fill_tables()

if __name__ == "__main__":
    main()
