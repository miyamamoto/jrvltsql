#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PostgreSQL接続テストスクリプト

ローカルのPostgreSQLに接続してテーブル作成・データ挿入をテストします。

使用方法:
    JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 pytest tests/test_postgresql.py

環境変数（scripts/setup_pg_test_db.py と同一契約。POSTGRES_* が PG* より優先）:
    POSTGRES_HOST / PGHOST: ホスト名 (デフォルト: localhost)
    POSTGRES_PORT / PGPORT: ポート番号 (デフォルト: 5432)
    POSTGRES_DB / PGDATABASE: データベース名 (デフォルト: jltsql_test)
    POSTGRES_USER / PGUSER: ユーザー名 (デフォルト: jltsql)
    POSTGRES_PASSWORD / PGPASSWORD: パスワード (デフォルト: 空)
"""

import os
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

RUN_POSTGRESQL_INTEGRATION = (
    os.environ.get("JLTSQL_RUN_POSTGRESQL_INTEGRATION") == "1"
)
postgresql_integration = pytest.mark.skipif(
    not RUN_POSTGRESQL_INTEGRATION,
    reason="set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run live PostgreSQL tests",
)

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.setup_pg_test_db import postgresql_test_config, setup_test_database  # noqa: E402

LIVE_POSTGRESQL_ENV = (
    "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
    "PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD",
)
_DEFAULT_LIVE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "jltsql_test",
    "user": "jltsql",
    "password": "",
    "connect_timeout": 5,
}


@pytest.mark.parametrize(
    ("environ", "expected"),
    [
        ({}, _DEFAULT_LIVE_CONFIG),
        (
            {"PGHOST": "pg.internal", "PGPORT": "6543", "PGDATABASE": "legacy db",
             "PGUSER": "legacy", "PGPASSWORD": "legacy-value"},
            {**_DEFAULT_LIVE_CONFIG, "host": "pg.internal", "port": 6543,
             "database": "legacy db", "user": "legacy", "password": "legacy-value"},
        ),
        (
            {"PGDATABASE": "legacy db", "POSTGRES_DB": "primary_db", "POSTGRES_USER": "primary"},
            {**_DEFAULT_LIVE_CONFIG, "database": "primary_db", "user": "primary"},
        ),
    ],
    ids=["defaults", "pg-variables", "postgres-variables-win"],
)
def test_live_postgresql_config_contract_is_shared(monkeypatch, environ, expected):
    """Every live PostgreSQL entry point resolves one env/default contract."""
    from tests import test_e2e_comprehensive, test_metadata_application

    for name in LIVE_POSTGRESQL_ENV:
        monkeypatch.delenv(name, raising=False)
    for name, value in environ.items():
        monkeypatch.setenv(name, value)

    assert postgresql_test_config() == expected
    assert test_e2e_comprehensive.postgresql_test_config is postgresql_test_config
    assert test_metadata_application.postgresql_test_config is postgresql_test_config


def test_setup_pg_test_db_uses_shared_contract_connect_timeout_and_quoted_identifier(
    monkeypatch, capsys
):
    """The bootstrap script uses psycopg3 connect_timeout and a quoted CREATE DATABASE."""
    import psycopg

    executed = []
    connect_kwargs = {}

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, statement, params=None):
            executed.append((statement, params))

        def fetchone(self):
            return None

    class _Connection:
        def cursor(self):
            return _Cursor()

        def close(self):
            pass

    def _connect(**kwargs):
        connect_kwargs.update(kwargs)
        return _Connection()

    for name in LIVE_POSTGRESQL_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("POSTGRES_DB", 'weird"db')
    monkeypatch.setenv("POSTGRES_PASSWORD", "password-value")
    monkeypatch.setattr(psycopg, "connect", _connect)

    assert setup_test_database() is True
    assert connect_kwargs["dbname"] == "postgres"
    assert connect_kwargs["password"] == "password-value"
    assert connect_kwargs["connect_timeout"] == 5
    assert "timeout" not in connect_kwargs
    assert connect_kwargs["user"] == "jltsql"
    create_statement = executed[-1][0]
    assert isinstance(create_statement, psycopg.sql.Composed)
    assert create_statement.as_string(None) == 'CREATE DATABASE "weird""db"'
    assert "password-value" not in capsys.readouterr().out


@pytest.mark.parametrize("table_name", ["NL_RA", "NL_O1"])
def test_normalize_row_matches_per_column_type_lookup(table_name):
    """行ごとに 1 回引いた列型が、列ごとに引いた場合と同じ結果を出すこと。"""
    from src.database.postgresql_handler import PostgreSQLDatabase
    from src.database.schema_types import get_column_type, get_table_column_types

    row = {
        column: ["", "  ", "***", "0103*****", "42", "12.5", None][index % 7]
        for index, column in enumerate(get_table_column_types(table_name))
    }
    assert PostgreSQLDatabase._normalize_insert_data(table_name, row) == {
        column: PostgreSQLDatabase._normalize_insert_value(
            get_column_type(table_name, column), value
        )
        for column, value in row.items()
    }


def test_normalize_row_leaves_an_unknown_table_untouched():
    from src.database.postgresql_handler import PostgreSQLDatabase

    row = {"Whatever": "  ", "Another": "42"}
    assert PostgreSQLDatabase._normalize_insert_data("NO_SUCH_TABLE", row) == row


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


def test_insert_many_binds_one_row_template_through_executemany(monkeypatch):
    """One batch must parse one statement, not one per chunk of rows.

    psycopg refuses to cache a query longer than 4096 bytes or carrying more
    than 50 parameters, so the old multi-row ``VALUES (...), (...)`` statement
    re-parsed the whole SQL string on every chunk (keibaai_cloud#280).
    A single-row template stays inside both limits and is parsed once.
    """
    from unittest.mock import MagicMock

    import src.database.postgresql_handler as postgresql_handler

    monkeypatch.setattr(postgresql_handler, "DRIVER", "psycopg")
    monkeypatch.setattr(
        postgresql_handler.PostgreSQLDatabase,
        "_get_primary_key_columns",
        lambda self, table_name: ["year", "kumi"],
    )

    database = postgresql_handler.PostgreSQLDatabase({})
    database._connection = MagicMock()
    cursor = MagicMock()
    # rowcount must not leak into the return value; see the return assertion below.
    cursor.rowcount = 999
    database._cursor = cursor

    rows = [
        {"Year": 2026, "Kumi": "01-02", "Odds": 10.0},
        # Expanded records are ragged: this row binds the column union too.
        {"Year": 2026, "Kumi": "01-03", "Ninki": 2},
        # Same conflict key as the first row.
        {"Year": 2026, "Kumi": "01-02", "Odds": 10.5},
    ]

    inserted = database.insert_many("test_batch_upsert", rows, use_replace=True)

    cursor.execute.assert_not_called()
    # One placeholder group for the whole batch, not one per row.
    assert cursor.executemany.call_args.args[0] == (
        "INSERT INTO test_batch_upsert (year, kumi, odds, ninki) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT (year, kumi) "
        "DO UPDATE SET odds = EXCLUDED.odds, ninki = EXCLUDED.ninki"
    )
    # _dedupe_rows_by_primary_key still collapses the in-batch duplicate.
    assert list(cursor.executemany.call_args.args[1]) == [
        (2026, "01-02", 10.5, None),
        (2026, "01-03", None, 2),
    ]
    # len(data_list), not cursor.rowcount: callers bind this value.
    assert inserted == 2


def test_insert_many_keeps_pg8000_on_bounded_multi_row_statements(monkeypatch):
    """The pg8000 fallback must not turn one batch into one network call per row."""

    from unittest.mock import MagicMock

    import src.database.postgresql_handler as postgresql_handler

    monkeypatch.setattr(postgresql_handler, "DRIVER", "pg8000")
    monkeypatch.setattr(
        postgresql_handler.PostgreSQLDatabase,
        "_get_primary_key_columns",
        lambda self, table_name: ["year", "kumi"],
    )

    database = postgresql_handler.PostgreSQLDatabase({})
    database._connection = MagicMock()
    database._connection.row_count = 100
    rows = [{"Year": 2026, "Kumi": f"{index:05d}", "Odds": index / 10} for index in range(100)]

    assert database.insert_many("test_batch_upsert", rows, use_replace=True) == 100

    assert database._connection.run.call_count == 1
    sql = database._connection.run.call_args.args[0]
    params = database._connection.run.call_args.kwargs
    assert sql.count("VALUES") == 1
    assert sql.count("(:param") == 100
    assert "ON CONFLICT (year, kumi) DO UPDATE SET odds = EXCLUDED.odds" in sql
    assert list(params.values())[:6] == [2026, "00000", 0.0, 2026, "00001", 0.1]
    assert list(params.values())[-3:] == [2026, "00099", 9.9]


def test_insert_many_pg8000_rolls_back_all_chunks_on_late_failure(monkeypatch):
    """A split pg8000 batch owns one transaction and cannot partially persist."""

    from unittest.mock import MagicMock

    import src.database.postgresql_handler as postgresql_handler
    from src.database.base import DatabaseError

    monkeypatch.setattr(postgresql_handler, "DRIVER", "pg8000")
    monkeypatch.setattr(postgresql_handler, "PG8000_MAX_INSERT_PARAMETERS", 6)
    monkeypatch.setattr(
        postgresql_handler.PostgreSQLDatabase,
        "_get_primary_key_columns",
        lambda self, table_name: ["year", "kumi"],
    )

    database = postgresql_handler.PostgreSQLDatabase({})
    database._connection = MagicMock()
    database._connection.row_count = 3
    insert_calls = 0

    def run(sql, **params):
        nonlocal insert_calls
        if sql.startswith("INSERT"):
            insert_calls += 1
            if insert_calls == 2:
                raise RuntimeError("late constraint failure")

    database._connection.run.side_effect = run
    rows = [{"Year": 2026, "Kumi": str(index)} for index in range(4)]

    with pytest.raises(DatabaseError, match="late constraint failure"):
        database.insert_many("test_batch_upsert", rows, use_replace=True)

    commands = [call.args[0] for call in database._connection.run.call_args_list]
    assert commands[0] == "BEGIN"
    assert sum(command.startswith("INSERT") for command in commands) == 2
    assert commands[-1] == "ROLLBACK"
    assert "COMMIT" not in commands


def test_pg8000_explicit_batch_transaction(monkeypatch):
    """The native fallback must not autocommit each batch row."""
    from unittest.mock import MagicMock, call

    import src.database.postgresql_handler as postgresql_handler

    database = postgresql_handler.PostgreSQLDatabase({})
    database._connection = MagicMock()
    monkeypatch.setattr(postgresql_handler, "DRIVER", "pg8000")

    database.begin_transaction()
    assert database.has_pending_transaction() is True
    database.begin_transaction()
    database.commit()
    assert database.has_pending_transaction() is False
    database.commit()

    assert database._connection.run.call_args_list == [call("BEGIN"), call("COMMIT")]


def test_psycopg_pending_transaction_inspection_is_fail_closed(monkeypatch):
    """Implicit psycopg state is observable and inspection errors propagate."""
    from unittest.mock import MagicMock

    import src.database.postgresql_handler as postgresql_handler
    from src.database.base import DatabaseError

    database = postgresql_handler.PostgreSQLDatabase({})
    database._connection = MagicMock()
    monkeypatch.setattr(postgresql_handler, "DRIVER", "psycopg")

    database._connection.info.transaction_status = (
        postgresql_handler.psycopg.pq.TransactionStatus.IDLE
    )
    assert database.has_pending_transaction() is False
    database._connection.info.transaction_status = (
        postgresql_handler.psycopg.pq.TransactionStatus.INTRANS
    )
    assert database.has_pending_transaction() is True

    class BrokenInfo:
        @property
        def transaction_status(self):
            raise RuntimeError("status unavailable")

    database._connection.info = BrokenInfo()
    with pytest.raises(DatabaseError, match="Failed to inspect PostgreSQL"):
        database.has_pending_transaction()


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
   - POSTGRES_HOST / PGHOST=localhost
   - POSTGRES_PORT / PGPORT=5432
   - POSTGRES_DB / PGDATABASE=jltsql_test
   - POSTGRES_USER / PGUSER=jltsql
   - POSTGRES_PASSWORD / PGPASSWORD=(空)

   テスト用データベースを作成:
   > psql -U postgres
   postgres=# CREATE DATABASE jltsql_test;
   postgres=# \\q

4. psqlへのパス:

   PostgreSQLのbinディレクトリをPATHに追加:
   - 通常: C:\\Program Files\\PostgreSQL\\16\\bin
   - 環境変数 PATH に追加

================================================================================
""")


@postgresql_integration
def test_connection():
    """PostgreSQL接続テスト"""
    print("=" * 60)
    print("PostgreSQL接続テスト")
    print("=" * 60)

    # 設定を取得
    config = postgresql_test_config()

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
        pytest.fail(f"PostgreSQL integration was requested but no driver is available: {e}")

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
        raise

    # バージョン確認
    print(f"\nPostgreSQLバージョン...")
    try:
        result = db.fetch_one("SELECT version()")
        assert result
        # pg8000はリストを返す、psycopgはdictを返す
        if isinstance(result, (list, tuple)):
            version = result[0]
        else:
            version = result.get("version", result)
        assert version
        print(f"  {version}")
    except Exception as e:
        print(f"  [ERROR] バージョン取得失敗: {e}")
        raise

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
        raise

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
        raise

    # データ読み取りテスト
    print(f"\nデータ読み取りテスト...")
    try:
        # 単一行取得
        row = db.fetch_one("SELECT * FROM test_jltsql WHERE name = ?", ("test1",))
        print(f"  単一行: {row}")

        # 全行取得
        rows = db.fetch_all("SELECT name, value FROM test_jltsql ORDER BY value")
        assert len(rows) == 4
        print(f"  全行数: {len(rows)}")
        for r in rows:
            print(f"    {r}")

    except Exception as e:
        print(f"  [ERROR] データ読み取り失敗: {e}")
        db.disconnect()
        raise

    # クリーンアップ
    print(f"\nクリーンアップ...")
    try:
        db.execute("DROP TABLE test_jltsql")
        print(f"  [OK] テストテーブル削除完了")
    except Exception as e:
        print(f"  [WARNING] クリーンアップ失敗: {e}")
        raise

    # 切断
    db.disconnect()
    print(f"  [OK] 切断完了")

    print(f"\n" + "=" * 60)
    print("PostgreSQL接続テスト: 全て成功")
    print("=" * 60)


@postgresql_integration
def test_schema_creation():
    """スキーマ作成テスト (NL_RAテーブル)"""
    print("\n" + "=" * 60)
    print("スキーマ作成テスト (NL_RAテーブル)")
    print("=" * 60)

    config = postgresql_test_config()

    try:
        from src.database.postgresql_handler import PostgreSQLDatabase
        from src.database.schema import SCHEMAS

        db = PostgreSQLDatabase(config)
        db.connect()

        # NL_RAスキーマを取得してPostgreSQL用に変換
        sqlite_schema = SCHEMAS.get("NL_RA", "")
        if not sqlite_schema:
            pytest.fail("NL_RA schema is missing")

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
        raise


@postgresql_integration
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
    config = postgresql_test_config()

    from src.database.postgresql_handler import PostgreSQLDatabase
    from src.database.migration import (
        _get_existing_columns,
        _get_existing_primary_key_columns,
    )

    db = PostgreSQLDatabase(config)
    db.connect()

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


@contextmanager
def _live_batch_table(table):
    """Yield a connected handler owning one throwaway upsert table."""
    from src.database.postgresql_handler import PostgreSQLDatabase

    db = PostgreSQLDatabase(postgresql_test_config())
    db.connect()
    try:
        db.execute(f"DROP TABLE IF EXISTS {table}")
        db.execute(
            f"""
            CREATE TABLE {table} (
                year INTEGER NOT NULL,
                kumi TEXT NOT NULL,
                ninki INTEGER NOT NULL,
                PRIMARY KEY (year, kumi)
            )
            """
        )
        db.commit()
        yield db
    finally:
        db.rollback()
        db.execute(f"DROP TABLE IF EXISTS {table}")
        db.commit()
        db.disconnect()


def _rows_of(db, table):
    return [
        (row["kumi"], row["ninki"])
        for row in db.fetch_all(f"SELECT kumi, ninki FROM {table} ORDER BY kumi")
    ]


@postgresql_integration
def test_insert_many_upsert_round_trip_against_live_postgresql():
    """``ON CONFLICT DO UPDATE`` semantics survive the executemany rewrite.

    keibaai_cloud#280 replaced the multi-row ``VALUES`` statement with a
    single-row template driven by ``executemany``. Last row wins inside a
    batch, a re-run updates instead of duplicating, and the return value
    counts the deduped rows.
    """
    table = "test_insert_many_upsert"
    with _live_batch_table(table) as db:
        first_batch = [
            {"Year": 2026, "Kumi": "01-02", "Ninki": 1},
            {"Year": 2026, "Kumi": "01-03", "Ninki": 2},
            # Same conflict key as the first row: the last one wins.
            {"Year": 2026, "Kumi": "01-02", "Ninki": 3},
        ]
        assert db.insert_many(table, first_batch, use_replace=True) == 2
        db.commit()
        assert _rows_of(db, table) == [("01-02", 3), ("01-03", 2)]

        # Re-inserting the same conflict keys updates in place.
        second_batch = [
            {"Year": 2026, "Kumi": "01-02", "Ninki": 4},
            {"Year": 2026, "Kumi": "01-04", "Ninki": 5},
        ]
        assert db.insert_many(table, second_batch, use_replace=True) == 2
        db.commit()
        assert _rows_of(db, table) == [("01-02", 4), ("01-03", 2), ("01-04", 5)]


@postgresql_integration
def test_insert_many_rejects_whole_batch_containing_an_invalid_row():
    """A bad row anywhere in the batch fails the batch, leaving nothing behind.

    ``executemany`` runs one statement per row over a psycopg pipeline, so the
    error surfaces from a different call site than the old single multi-row
    statement did. What callers rely on must not change: ``DatabaseError``
    reaches them, no row of the failed batch is persisted, and the connection
    is still usable afterwards.
    """
    from src.database.base import DatabaseError

    table = "test_insert_many_invalid_row"
    with _live_batch_table(table) as db:
        db.execute(f"INSERT INTO {table} (year, kumi, ninki) VALUES (2026, '00-00', 9)")
        db.commit()

        poisoned_batch = [
            {"Year": 2026, "Kumi": "01-02", "Ninki": 1},
            # NOT NULL violation in the middle of the batch.
            {"Year": 2026, "Kumi": "01-03", "Ninki": None},
            {"Year": 2026, "Kumi": "01-04", "Ninki": 2},
        ]
        with pytest.raises(DatabaseError):
            db.insert_many(table, poisoned_batch, use_replace=True)

        # The rollback scope is the batch: the row before the bad one is gone
        # too, while work committed before the batch survives.
        assert _rows_of(db, table) == [("00-00", 9)]

        # The handler rolled the failed transaction back: the session is clean.
        assert db.insert_many(table, [{"Year": 2026, "Kumi": "02-01", "Ninki": 7}]) == 1
        db.commit()
        assert _rows_of(db, table) == [("00-00", 9), ("02-01", 7)]
