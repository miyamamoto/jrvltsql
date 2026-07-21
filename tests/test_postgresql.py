#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PostgreSQL接続テストスクリプト

ローカルのPostgreSQLに接続してテーブル作成・データ挿入をテストします。

使用方法:
    python tests/test_postgresql.py

環境変数:
    PGHOST: ホスト名 (デフォルト: localhost)
    PGPORT: ポート番号 (デフォルト: 5432)
    PGDATABASE: データベース名 (デフォルト: keiba_test)
    PGUSER: ユーザー名 (デフォルト: postgres)
    PGPASSWORD: パスワード (デフォルト: postgres)
"""

import os
import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_normalize_blank_numeric_insert_values():
    """PostgreSQL inserts convert blank numeric JV-Data fields to NULL."""
    from src.database.postgresql_handler import PostgreSQLDatabase

    data = PostgreSQLDatabase._normalize_insert_data(
        "TS_O1",
        {
            "RecordSpec": "O1",
            "Year": "2026",
            "TanVote": "",
            "FukuVote": "123",
            "JyoCD": "",
        },
    )

    assert data["TanVote"] is None
    assert data["FukuVote"] == 123
    assert data["JyoCD"] == ""

    odds_data = PostgreSQLDatabase._normalize_insert_data(
        "TS_O2",
        {"Odds": "******", "Ninki": "***", "Vote": "100"},
    )
    assert odds_data["Odds"] is None
    assert odds_data["Ninki"] is None
    assert odds_data["Vote"] == 100


def test_dedupe_rows_by_primary_key_keeps_last_row():
    """PostgreSQL multi-row upsert must not contain duplicate conflict keys."""
    from src.database.postgresql_handler import PostgreSQLDatabase

    rows = [
        {"Year": 2026, "MonthDay": 426, "JyoCD": "03", "RaceNum": 1, "Kumi": "01-02", "HassoTime": "1000", "Odds": 10.0},
        {"Year": 2026, "MonthDay": 426, "JyoCD": "03", "RaceNum": 1, "Kumi": "01-02", "HassoTime": "1000", "Odds": 10.5},
        {"Year": 2026, "MonthDay": 426, "JyoCD": "03", "RaceNum": 1, "Kumi": "01-03", "HassoTime": "1000", "Odds": 20.0},
    ]

    deduped = PostgreSQLDatabase._dedupe_rows_by_primary_key(
        rows,
        ["year", "monthday", "jyocd", "racenum", "kumi", "hassotime"],
    )

    assert len(deduped) == 2
    assert deduped[0]["Kumi"] == "01-02"
    assert deduped[0]["Odds"] == 10.5
    assert deduped[1]["Kumi"] == "01-03"


def test_pg8000_explicit_batch_transaction(monkeypatch):
    """The native fallback must not autocommit each batch row."""
    from unittest.mock import MagicMock, call

    import src.database.postgresql_handler as postgresql_handler

    database = postgresql_handler.PostgreSQLDatabase({})
    database._connection = MagicMock()
    monkeypatch.setattr(postgresql_handler, "DRIVER", "pg8000")

    database.begin_transaction()
    database.begin_transaction()
    database.commit()
    database.commit()

    assert database._connection.run.call_args_list == [call("BEGIN"), call("COMMIT")]


def test_pg8000_caller_managed_transaction_can_roll_back(monkeypatch):
    """auto_commit=False callers retain one explicit transaction."""
    from unittest.mock import MagicMock, call

    import src.database.postgresql_handler as postgresql_handler

    database = postgresql_handler.PostgreSQLDatabase({})
    database._connection = MagicMock()
    monkeypatch.setattr(postgresql_handler, "DRIVER", "pg8000")

    database.begin_transaction()
    database.begin_transaction()
    database.rollback()
    database.rollback()

    assert database._connection.run.call_args_list == [call("BEGIN"), call("ROLLBACK")]


def test_pg8000_statement_failure_does_not_end_caller_transaction(monkeypatch):
    """A row failure must leave the batch transaction for the caller to roll back."""
    from unittest.mock import MagicMock, call

    import src.database.postgresql_handler as postgresql_handler
    from src.database.base import DatabaseError

    database = postgresql_handler.PostgreSQLDatabase({})
    database._connection = MagicMock()
    database._connection.run.side_effect = [[], RuntimeError("constraint failure"), []]
    monkeypatch.setattr(postgresql_handler, "DRIVER", "pg8000")

    database.begin_transaction()
    with pytest.raises(DatabaseError, match="constraint failure"):
        database.execute("BAD")

    assert database._transaction_active
    database.rollback()
    assert database._connection.run.call_args_list == [
        call("BEGIN"),
        call("BAD"),
        call("ROLLBACK"),
    ]


def test_pg8000_execute_converts_realtime_delete_placeholders(monkeypatch):
    """RealtimeUpdater's SQLite-style DELETE executes through pg8000."""
    from unittest.mock import MagicMock, call

    import src.database.postgresql_handler as postgresql_handler

    database = postgresql_handler.PostgreSQLDatabase({})
    database._connection = MagicMock()
    monkeypatch.setattr(postgresql_handler, "DRIVER", "pg8000")

    database.execute(
        "DELETE FROM RT_RA WHERE Year = ? AND MonthDay = ?",
        (2026, "0715"),
    )

    assert database._connection.run.call_args_list == [
        call(
            "DELETE FROM RT_RA WHERE Year = :param1 AND MonthDay = :param2",
            param1=2026,
            param2="0715",
        )
    ]


def test_pg8000_primary_key_lookup_failure_aborts_caller_transaction(monkeypatch):
    """Metadata failures must propagate without inserting outside the transaction."""
    from unittest.mock import MagicMock, call

    import src.database.postgresql_handler as postgresql_handler
    from src.database.base import DatabaseError

    database = postgresql_handler.PostgreSQLDatabase({})
    database._connection = MagicMock()
    database._connection.run.side_effect = [
        [],
        RuntimeError("metadata statement failed"),
        [],
    ]
    monkeypatch.setattr(postgresql_handler, "DRIVER", "pg8000")

    database.begin_transaction()
    with pytest.raises(DatabaseError, match="metadata statement failed"):
        database.insert("RT_RA", {"Year": 2026})

    assert database._transaction_active
    database.rollback()
    assert database._connection.run.call_args_list == [
        call("BEGIN"),
        call(
            """
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = to_regclass(:param1)
                AND i.indisprimary
                ORDER BY array_position(i.indkey, a.attnum)
            """,
            param1="rt_ra",
        ),
        call("ROLLBACK"),
    ]


def test_psycopg_primary_key_lookup_failure_aborts_caller_transaction(monkeypatch):
    """The psycopg path must preserve transaction ownership on metadata failure."""
    from unittest.mock import MagicMock

    import src.database.postgresql_handler as postgresql_handler
    from src.database.base import DatabaseError

    database = postgresql_handler.PostgreSQLDatabase({})
    database._connection = MagicMock()
    database._cursor = MagicMock()
    database._cursor.execute.side_effect = RuntimeError("metadata statement failed")
    monkeypatch.setattr(postgresql_handler, "DRIVER", "psycopg")

    database.begin_transaction()
    with pytest.raises(DatabaseError, match="metadata statement failed"):
        database.insert("RT_RA", {"Year": 2026})

    assert database._transaction_active
    database.rollback()
    assert database._cursor.execute.call_count == 1
    database._connection.rollback.assert_called_once_with()
    database._connection.commit.assert_not_called()


def print_installation_guide():
    """PostgreSQLのインストールガイドを表示"""
    print("""
================================================================================
PostgreSQL接続エラー
================================================================================

PostgreSQLに接続できませんでした。以下を確認してください:

1. PostgreSQLがインストールされていない場合:

   Windows インストール方法:
   -------------------------
   a) 公式インストーラー (推奨):
      https://www.postgresql.org/download/windows/
      - 「Download the installer」をクリック
      - インストーラーを実行 (例: postgresql-16.x-windows-x64.exe)
      - インストール先: C:\\Program Files\\PostgreSQL\\16
      - パスワードを設定 (覚えておくこと)
      - ポート: 5432 (デフォルト)
      - Stack Builder: スキップ可能

   b) Chocolatey:
      choco install postgresql

   c) Scoop:
      scoop install postgresql

2. PostgreSQLがインストール済みの場合:

   サービスが起動しているか確認:
   - Win+R → services.msc → 「postgresql-x64-16」を探す
   - 「開始」をクリック

   または PowerShell (管理者):
   > net start postgresql-x64-16

3. 接続設定:

   環境変数で設定するか、デフォルト値を使用:
   - PGHOST=localhost
   - PGPORT=5432
   - PGDATABASE=keiba_test
   - PGUSER=postgres
   - PGPASSWORD=postgres

   テスト用データベースを作成:
   > psql -U postgres
   postgres=# CREATE DATABASE keiba_test;
   postgres=# \\q

4. psqlへのパス:

   PostgreSQLのbinディレクトリをPATHに追加:
   - 通常: C:\\Program Files\\PostgreSQL\\16\\bin
   - 環境変数 PATH に追加

================================================================================
""")


def test_connection():
    """PostgreSQL接続テスト"""
    print("=" * 60)
    print("PostgreSQL接続テスト")
    print("=" * 60)

    # 設定を取得
    config = {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": int(os.environ.get("PGPORT", 5432)),
        "database": os.environ.get("PGDATABASE", "keiba_test"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", "postgres"),
        "connect_timeout": 5,
    }

    print(f"\n接続設定:")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  Database: {config['database']}")
    print(f"  User: {config['user']}")
    print(f"  Password: {'*' * len(config['password'])}")

    # ドライバーの確認
    print(f"\nドライバーの確認...")
    try:
        from src.database.postgresql_handler import DRIVER
        print(f"  使用ドライバー: {DRIVER}")
    except ImportError as e:
        print(f"  [ERROR] ドライバーがインストールされていません: {e}")
        print(f"\n  インストール方法:")
        print('    pip install "psycopg[binary]"')
        pytest.skip("PostgreSQL driver not available")

    # 接続テスト
    print(f"\n接続テスト...")
    try:
        from src.database.postgresql_handler import PostgreSQLDatabase

        db = PostgreSQLDatabase(config)
        db.connect()
        print(f"  [OK] 接続成功")

    except Exception as e:
        print(f"  [ERROR] 接続失敗: {e}")
        print_installation_guide()
        pytest.skip("PostgreSQL driver not available")

    # バージョン確認
    print(f"\nPostgreSQLバージョン...")
    try:
        result = db.fetch_one("SELECT version()")
        if result:
            # pg8000はリストを返す、psycopgはdictを返す
            if isinstance(result, (list, tuple)):
                version = result[0]
            else:
                version = result.get("version", result)
            print(f"  {version}")
    except Exception as e:
        print(f"  [ERROR] バージョン取得失敗: {e}")

    # テーブル作成テスト
    print(f"\nテーブル作成テスト...")
    try:
        # テストテーブルを作成
        db.execute("DROP TABLE IF EXISTS test_jltsql")
        db.execute("""
            CREATE TABLE test_jltsql (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print(f"  [OK] テーブル 'test_jltsql' を作成")

    except Exception as e:
        print(f"  [ERROR] テーブル作成失敗: {e}")
        db.disconnect()
        pytest.skip("PostgreSQL driver not available")

    # データ挿入テスト
    print(f"\nデータ挿入テスト...")
    try:
        # 単一行挿入
        db.execute(
            "INSERT INTO test_jltsql (name, value) VALUES (?, ?)",
            ("test1", 100)
        )
        print(f"  [OK] 単一行挿入成功")

        # 複数行挿入
        db.executemany(
            "INSERT INTO test_jltsql (name, value) VALUES (?, ?)",
            [("test2", 200), ("test3", 300), ("test4", 400)]
        )
        print(f"  [OK] 複数行挿入成功 (3行)")

    except Exception as e:
        print(f"  [ERROR] データ挿入失敗: {e}")
        db.disconnect()
        pytest.skip("PostgreSQL driver not available")

    # データ読み取りテスト
    print(f"\nデータ読み取りテスト...")
    try:
        # 単一行取得
        row = db.fetch_one("SELECT * FROM test_jltsql WHERE name = ?", ("test1",))
        print(f"  単一行: {row}")

        # 全行取得
        rows = db.fetch_all("SELECT name, value FROM test_jltsql ORDER BY value")
        print(f"  全行数: {len(rows)}")
        for r in rows:
            print(f"    {r}")

    except Exception as e:
        print(f"  [ERROR] データ読み取り失敗: {e}")
        db.disconnect()
        pytest.skip("PostgreSQL driver not available")

    # クリーンアップ
    print(f"\nクリーンアップ...")
    try:
        db.execute("DROP TABLE test_jltsql")
        print(f"  [OK] テストテーブル削除完了")
    except Exception as e:
        print(f"  [WARNING] クリーンアップ失敗: {e}")

    # 切断
    db.disconnect()
    print(f"  [OK] 切断完了")

    print(f"\n" + "=" * 60)
    print("PostgreSQL接続テスト: 全て成功")
    print("=" * 60)


def test_schema_creation():
    """スキーマ作成テスト (NL_RAテーブル)"""
    print("\n" + "=" * 60)
    print("スキーマ作成テスト (NL_RAテーブル)")
    print("=" * 60)

    config = {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": int(os.environ.get("PGPORT", 5432)),
        "database": os.environ.get("PGDATABASE", "keiba_test"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", "postgres"),
        "connect_timeout": 5,
    }

    try:
        from src.database.postgresql_handler import PostgreSQLDatabase
        from src.database.schema import SCHEMAS

        db = PostgreSQLDatabase(config)
        db.connect()

        # NL_RAスキーマを取得してPostgreSQL用に変換
        sqlite_schema = SCHEMAS.get("NL_RA", "")
        if not sqlite_schema:
            print("  [ERROR] NL_RAスキーマが見つかりません")
            pytest.skip("PostgreSQL driver not available")

        # SQLiteスキーマをPostgreSQL用に変換
        pg_schema = sqlite_schema
        # INTEGER → INTEGER (そのまま)
        # TEXT → TEXT (そのまま)
        # PRIMARY KEY → PostgreSQLでも同じ

        print(f"\nNL_RAテーブル作成中...")
        db.execute("DROP TABLE IF EXISTS nl_ra")
        db.execute(pg_schema)
        print(f"  [OK] NL_RAテーブル作成成功")

        # テーブル情報取得
        columns = db.get_table_columns("nl_ra")
        print(f"\nカラム情報 (最初の10件):")
        for col in columns[:10]:
            print(f"  {col}")
        print(f"  ... 計 {len(columns)} カラム")

        # クリーンアップ
        db.execute("DROP TABLE nl_ra")
        db.disconnect()

        print(f"\n[OK] スキーマ作成テスト成功")

    except Exception as e:
        print(f"  [ERROR] スキーマ作成テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        pytest.skip("PostgreSQL driver not available")


def test_table_exists_and_column_lookups_respect_search_path():
    """search_path が非 public スキーマを指す環境で、table_exists() /
    migration.py の既存カラム・主キー取得が正しいテーブルを解決すること。

    PR #143 が修正した2つの不具合の回帰テスト:
    1. table_exists() が pg_tables をスキーマ非限定で参照し、search_path に
       無いスキーマの同名テーブルにも True を返していた（migration.py 側の
       to_regclass() ベースの解決と食い違う）。
    2. 複数スキーマに同名テーブルがある場合、current_schema() だけでは
       search_path の優先順位どおりに一意特定できなかった。
    """
    config = {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": int(os.environ.get("PGPORT", 5432)),
        "database": os.environ.get("PGDATABASE", "keiba_test"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", "postgres"),
        "connect_timeout": 5,
    }

    try:
        from src.database.postgresql_handler import PostgreSQLDatabase
        from src.database.migration import (
            _get_existing_columns,
            _get_existing_primary_key_columns,
        )

        db = PostgreSQLDatabase(config)
        db.connect()
    except Exception:
        pytest.skip("PostgreSQL driver not available")

    schema_a = "jltsql_test_search_path_a"
    schema_b = "jltsql_test_search_path_b"
    probe_table = "jltsql_search_path_probe"

    try:
        db.execute(f"DROP SCHEMA IF EXISTS {schema_a} CASCADE")
        db.execute(f"DROP SCHEMA IF EXISTS {schema_b} CASCADE")
        db.execute(f"CREATE SCHEMA {schema_a}")
        db.execute(f"CREATE SCHEMA {schema_b}")
        # 同名テーブルを両スキーマに作成し、カラム構成をあえて変える。
        db.execute(f"CREATE TABLE {schema_a}.{probe_table} (col_a INTEGER PRIMARY KEY)")
        db.execute(f"CREATE TABLE {schema_b}.{probe_table} (col_b TEXT PRIMARY KEY)")
        db.commit()

        # search_path が schema_a を指す場合、schema_a 側のテーブルが解決される。
        db.execute(f"SET search_path TO {schema_a}, public")
        assert db.table_exists(probe_table) is True
        assert _get_existing_columns(db, probe_table) == {"col_a"}
        assert _get_existing_primary_key_columns(db, probe_table) == ["col_a"]

        # search_path を schema_b へ切り替えると、同じ呼び出しが schema_b 側へ
        # 追従する（current_schema() 決め打ちでは一意特定できなかった問題）。
        db.execute(f"SET search_path TO {schema_b}, public")
        assert db.table_exists(probe_table) is True
        assert _get_existing_columns(db, probe_table) == {"col_b"}
        assert _get_existing_primary_key_columns(db, probe_table) == ["col_b"]

        # schema_b のテーブルを削除すると、schema_a にだけ同名テーブルが残る。
        # search_path は schema_b のままなので、table_exists() は
        # False を返さねばならない（旧実装は pg_tables をスキーマ非限定で見て
        # True を返し、直後の to_regclass() ベースの解決と食い違っていた）。
        db.execute(f"DROP TABLE {schema_b}.{probe_table}")
        db.commit()
        assert db.table_exists(probe_table) is False
        assert _get_existing_columns(db, probe_table) == set()
        assert _get_existing_primary_key_columns(db, probe_table) == []
    finally:
        db.execute(f"DROP SCHEMA IF EXISTS {schema_a} CASCADE")
        db.execute(f"DROP SCHEMA IF EXISTS {schema_b} CASCADE")
        db.execute("SET search_path TO public")
        db.commit()
        db.disconnect()


if __name__ == "__main__":
    success = True

    # 基本接続テスト
    if not test_connection():
        success = False
    else:
        # スキーマ作成テスト
        if not test_schema_creation():
            success = False

    sys.exit(0 if success else 1)
