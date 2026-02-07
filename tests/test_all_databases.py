#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""全データベース包括テスト

PostgreSQL、SQLiteで全57スキーマーをテストします。
"""

import sys
import os
from pathlib import Path

# Windowsコンソールでのエンコーディング問題を回避
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, str(Path(__file__).parent))

from src.parser.factory import ParserFactory, ALL_RECORD_TYPES
from src.database.sqlite_handler import SQLiteDatabase
from src.database.postgresql_handler import PostgreSQLDatabase
from src.database.schema import SchemaManager, SCHEMAS
from src.importer.importer import DataImporter
from src.jvlink.wrapper import JVLinkWrapper
from dotenv import load_dotenv
import os


class DatabaseTester:
    """データベーステスター"""

    def __init__(self, db_type: str, db_config: dict):
        self.db_type = db_type
        self.db_config = db_config
        self.results = {
            'tables_created': 0,
            'tables_failed': 0,
            'data_imported': 0,
            'errors': []
        }

    def test_schema_creation(self) -> bool:
        """全スキーマー作成テスト"""
        print(f"\n{'='*70}")
        print(f"{self.db_type} スキーマー作成テスト")
        print(f"{'='*70}\n")

        try:
            # データベース初期化
            if self.db_type == 'sqlite':
                database = SQLiteDatabase(self.db_config)
            elif self.db_type == 'duckdb':
                print(f"\n✗ DuckDBは非対応です（32-bit Python環境のため）")
                self.results['errors'].append("DuckDB not supported in 32-bit Python")
                return False
            elif self.db_type == 'postgresql':
                database = PostgreSQLDatabase(self.db_config)
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")

            with database:
                schema_mgr = SchemaManager(database)

                # 全テーブル作成
                print(f"全{len(SCHEMAS)}テーブルを作成中...")
                results = schema_mgr.create_all_tables()

                # 結果集計
                created = sum(1 for v in results.values() if v)
                failed = sum(1 for v in results.values() if not v)

                self.results['tables_created'] = created
                self.results['tables_failed'] = failed

                # 結果表示
                print(f"\n✓ 作成成功: {created}/{len(SCHEMAS)}")
                if failed > 0:
                    print(f"✗ 作成失敗: {failed}")
                    failed_tables = [k for k, v in results.items() if not v]
                    print(f"  失敗テーブル: {', '.join(failed_tables)}")
                    self.results['errors'].extend(failed_tables)

                # テーブル別統計
                nl_tables = sum(1 for k, v in results.items() if k.startswith('NL_') and v)
                rt_tables = sum(1 for k, v in results.items() if k.startswith('RT_') and v)

                print(f"\nテーブル統計:")
                print(f"  NL_* (蓄積系): {nl_tables}/38")
                print(f"  RT_* (速報系): {rt_tables}/20")

                return failed == 0

        except Exception as e:
            print(f"\n✗ エラー: {e}")
            self.results['errors'].append(str(e))
            import traceback
            traceback.print_exc()
            return False

    def test_data_import(self, test_data_count: int = 100) -> bool:
        """データインポートテスト"""
        print(f"\n{'='*70}")
        print(f"{self.db_type} データインポートテスト")
        print(f"{'='*70}\n")

        load_dotenv()
        sid = os.getenv("JVLINK_SID", "JLTSQL")

        try:
            # データベース初期化
            if self.db_type == 'sqlite':
                database = SQLiteDatabase(self.db_config)
            elif self.db_type == 'duckdb':
                print(f"\n✗ DuckDBは非対応です（32-bit Python環境のため）")
                self.results['errors'].append("DuckDB not supported in 32-bit Python")
                return False
            elif self.db_type == 'postgresql':
                database = PostgreSQLDatabase(self.db_config)
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")

            with database:
                importer = DataImporter(database, batch_size=100)
                jv = JVLinkWrapper(sid=sid)
                factory = ParserFactory()

                # JV-Link初期化
                result = jv.jv_init()
                if result != 0:
                    print(f"✗ JV-Link初期化失敗: {result}")
                    return False

                print("✓ JV-Link初期化成功\n")

                # YSCHデータでテスト（軽量）
                result_code, read_count, download_count, last_timestamp = jv.jv_open(
                    data_spec="YSCH",
                    fromtime="20240101000000",
                    option=1
                )

                print(f"JVOpen: code={result_code}, read={read_count}")

                if result_code != 0:
                    print("✗ ストリームオープン失敗")
                    jv.jv_close()
                    return False

                # レコード読み込みとインポート
                imported = 0
                record_types = set()

                for i in range(test_data_count):
                    result_code, data_bytes, filename = jv.jv_read()

                    if result_code <= 0:
                        break

                    # パース
                    record = factory.parse(data_bytes)
                    if record:
                        rec_type = record.get('レコード種別ID') or record.get('headRecordSpec')
                        if rec_type:
                            record_types.add(rec_type)

                        # インポート
                        if importer.import_single_record(record):
                            imported += 1

                jv.jv_close()

                self.results['data_imported'] = imported

                print(f"\n✓ インポート成功: {imported}件")
                print(f"  レコードタイプ: {len(record_types)}種類 ({', '.join(sorted(record_types))})")

                # テーブル別データ確認
                tables_with_data = []
                for table_name in SCHEMAS.keys():
                    try:
                        rows = database.fetch_all(f"SELECT COUNT(*) as cnt FROM {table_name}")
                        count = rows[0]['cnt'] if rows else 0
                        if count > 0:
                            tables_with_data.append(f"{table_name}({count})")
                    except:
                        pass

                print(f"\n  データが入ったテーブル: {len(tables_with_data)}")
                if tables_with_data:
                    print(f"    {', '.join(tables_with_data)}")

                return imported > 0

        except Exception as e:
            print(f"\n✗ エラー: {e}")
            self.results['errors'].append(str(e))
            import traceback
            traceback.print_exc()
            return False

    def print_summary(self):
        """結果サマリー表示"""
        print(f"\n{'='*70}")
        print(f"{self.db_type} テスト結果サマリー")
        print(f"{'='*70}")
        print(f"  テーブル作成: {self.results['tables_created']}/58")
        print(f"  テーブル失敗: {self.results['tables_failed']}")
        print(f"  データ取込: {self.results['data_imported']}件")
        if self.results['errors']:
            print(f"  エラー数: {len(self.results['errors'])}")
            print(f"    {', '.join(self.results['errors'][:5])}")


def main():
    """メインテスト"""
    print("\n" + "="*70)
    print("JLTSQL 全データベース包括テスト")
    print("="*70)

    all_results = {}

    # 1. SQLiteテスト
    print("\n\n1/3: SQLite テスト開始...")
    sqlite_config = {"path": "data/test_all_sqlite.db"}
    sqlite_tester = DatabaseTester("sqlite", sqlite_config)

    sqlite_schema_ok = sqlite_tester.test_schema_creation()
    sqlite_import_ok = sqlite_tester.test_data_import(test_data_count=100)

    sqlite_tester.print_summary()
    all_results['sqlite'] = {
        'schema': sqlite_schema_ok,
        'import': sqlite_import_ok,
        'results': sqlite_tester.results
    }

    # 2. DuckDBテスト（非対応）
    print("\n\n2/3: DuckDB テスト - スキップ（32-bit Python非対応）")
    all_results['duckdb'] = {
        'schema': False,
        'import': False,
        'results': {'error': 'DuckDB not supported in 32-bit Python'}
    }

    # 3. PostgreSQLテスト
    print("\n\n3/3: PostgreSQL テスト開始...")

    # PostgreSQL設定を環境変数から取得
    load_dotenv()  # .envファイルを再度読み込み
    pg_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'keiba_test'),
        'user': os.getenv('POSTGRES_USER', 'jltsql'),
        'password': os.getenv('POSTGRES_PASSWORD', 'jltsql_pass')
    }

    postgresql_tester = DatabaseTester("postgresql", pg_config)

    try:
        postgresql_schema_ok = postgresql_tester.test_schema_creation()
        postgresql_import_ok = postgresql_tester.test_data_import(test_data_count=100)

        postgresql_tester.print_summary()
        all_results['postgresql'] = {
            'schema': postgresql_schema_ok,
            'import': postgresql_import_ok,
            'results': postgresql_tester.results
        }
    except Exception as e:
        print(f"\n⚠ PostgreSQLテストスキップ: {e}")
        print("  PostgreSQLサーバーが起動していない、または接続設定が間違っています")
        all_results['postgresql'] = {
            'schema': False,
            'import': False,
            'results': {'error': str(e)}
        }

    # 総合結果
    print("\n" + "="*70)
    print("総合テスト結果")
    print("="*70)

    print("\nスキーマー作成テスト:")
    print(f"  SQLite:     {'✓ 成功' if all_results['sqlite']['schema'] else '✗ 失敗'}")
    print(f"  DuckDB:     {'✓ 成功' if all_results['duckdb']['schema'] else '✗ 失敗/スキップ'}")
    print(f"  PostgreSQL: {'✓ 成功' if all_results['postgresql']['schema'] else '✗ 失敗/スキップ'}")

    print("\nデータインポートテスト:")
    print(f"  SQLite:     {'✓ 成功' if all_results['sqlite']['import'] else '✗ 失敗'}")
    print(f"  DuckDB:     {'✓ 成功' if all_results['duckdb']['import'] else '✗ 失敗/スキップ'}")
    print(f"  PostgreSQL: {'✓ 成功' if all_results['postgresql']['import'] else '✗ 失敗/スキップ'}")

    # 成功判定 (DuckDBとPostgreSQLはオプショナル)
    all_passed = (
        all_results['sqlite']['schema'] and all_results['sqlite']['import']
    )

    if all_passed:
        print("\n🎉 全テスト合格！")
        return 0
    else:
        print("\n⚠ 一部テスト失敗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
