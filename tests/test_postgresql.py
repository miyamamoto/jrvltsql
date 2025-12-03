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

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


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
        print(f"    pip install pg8000      # 純粋Python (Win32対応)")
        print(f"    pip install psycopg     # 高速 (libpq必要)")
        return False

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
        return False

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
        return False

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
        return False

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
        return False

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
    return True


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
            return False

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
        return True

    except Exception as e:
        print(f"  [ERROR] スキーマ作成テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


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
