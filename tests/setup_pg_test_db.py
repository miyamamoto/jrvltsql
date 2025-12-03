#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PostgreSQLテスト用データベースをセットアップするスクリプト"""

import os
import sys

def setup_test_database():
    """テスト用データベースを作成"""

    host = os.environ.get("PGHOST", "localhost")
    port = int(os.environ.get("PGPORT", 5432))
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD", "postgres")
    test_db = os.environ.get("PGDATABASE", "keiba_test")

    print(f"PostgreSQL テスト用データベースのセットアップ")
    print(f"  Host: {host}:{port}")
    print(f"  User: {user}")
    print(f"  Target DB: {test_db}")

    try:
        import pg8000.native
        print(f"\n  [INFO] pg8000ドライバーを使用")
    except ImportError:
        print(f"\n  [ERROR] pg8000がインストールされていません")
        print(f"  pip install pg8000")
        return False

    # まずpostgresデータベースに接続
    print(f"\npostgresデータベースに接続中...")
    try:
        conn = pg8000.native.Connection(
            user=user,
            password=password,
            host=host,
            port=port,
            database="postgres",  # デフォルトDBに接続
            timeout=10,
        )
        print(f"  [OK] 接続成功")
    except Exception as e:
        print(f"  [ERROR] 接続失敗: {e}")
        print(f"\n  PostgreSQLのパスワードを確認してください:")
        print(f"    PGPASSWORD環境変数を設定")
        print(f"    または pg_hba.conf で trust 認証を設定")
        return False

    # テスト用データベースが存在するか確認
    print(f"\n'{test_db}'データベースの存在確認...")
    try:
        rows = conn.run("SELECT datname FROM pg_database WHERE datname = :db", db=test_db)
        if rows:
            print(f"  [INFO] データベースは既に存在します")
        else:
            # データベースを作成
            print(f"  データベースを作成中...")
            conn.run(f"CREATE DATABASE {test_db}")
            print(f"  [OK] データベース '{test_db}' を作成しました")
    except Exception as e:
        print(f"  [ERROR] データベース作成失敗: {e}")
        conn.close()
        return False

    conn.close()
    print(f"\n[OK] セットアップ完了")
    return True


if __name__ == "__main__":
    success = setup_test_database()
    sys.exit(0 if success else 1)
