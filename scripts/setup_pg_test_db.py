#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PostgreSQLテスト用データベースをセットアップするスクリプト

live PostgreSQL テスト（``JLTSQL_RUN_POSTGRESQL_INTEGRATION=1``）と同じ
接続契約を使う。``POSTGRES_*`` が優先、次に ``PG*``、最後に既定値。
"""

import os
import sys

DEFAULT_LIVE_DATABASE = "jltsql_test"
DEFAULT_LIVE_USER = "jltsql"
LIVE_CONNECT_TIMEOUT_SECONDS = 5


def _env(primary: str, fallback: str, default: str) -> str:
    return os.environ.get(primary) or os.environ.get(fallback) or default


def postgresql_test_config() -> dict:
    """Return the single live-PostgreSQL connection contract shared by tests."""
    return {
        "host": _env("POSTGRES_HOST", "PGHOST", "localhost"),
        "port": int(_env("POSTGRES_PORT", "PGPORT", "5432")),
        "database": _env("POSTGRES_DB", "PGDATABASE", DEFAULT_LIVE_DATABASE),
        "user": _env("POSTGRES_USER", "PGUSER", DEFAULT_LIVE_USER),
        "password": os.environ.get("POSTGRES_PASSWORD") or os.environ.get("PGPASSWORD", ""),
        "connect_timeout": LIVE_CONNECT_TIMEOUT_SECONDS,
    }


def setup_test_database():
    """テスト用データベースを作成"""

    config = postgresql_test_config()
    test_db = config["database"]

    print("PostgreSQL テスト用データベースのセットアップ")
    print(f"  Host: {config['host']}:{config['port']}")
    print(f"  User: {config['user']}")
    print(f"  Target DB: {test_db}")

    try:
        import psycopg
        from psycopg import sql
        print("\n  [INFO] psycopgドライバーを使用")
    except ImportError:
        print("\n  [ERROR] psycopgがインストールされていません")
        print('  pip install "psycopg[binary]"')
        return False

    # まずpostgresデータベースに接続
    print("\npostgresデータベースに接続中...")
    try:
        conn = psycopg.connect(
            user=config["user"],
            password=config["password"],
            host=config["host"],
            port=config["port"],
            dbname="postgres",  # デフォルトDBに接続
            autocommit=True,
            connect_timeout=config["connect_timeout"],
        )
        print("  [OK] 接続成功")
    except Exception as e:
        print(f"  [ERROR] 接続失敗: {e}")
        print("\n  PostgreSQLのパスワードを確認してください:")
        print("    POSTGRES_PASSWORD または PGPASSWORD 環境変数を設定")
        print("    または pg_hba.conf で trust 認証を設定")
        return False

    # テスト用データベースが存在するか確認
    print(f"\n'{test_db}'データベースの存在確認...")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT datname FROM pg_database WHERE datname = %s", (test_db,))
            if cur.fetchone():
                print("  [INFO] データベースは既に存在します")
            else:
                # データベースを作成
                print("  データベースを作成中...")
                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_db))
                )
                print(f"  [OK] データベース '{test_db}' を作成しました")
    except Exception as e:
        print(f"  [ERROR] データベース作成失敗: {e}")
        conn.close()
        return False

    conn.close()
    print("\n[OK] セットアップ完了")
    return True


if __name__ == "__main__":
    success = setup_test_database()
    sys.exit(0 if success else 1)
