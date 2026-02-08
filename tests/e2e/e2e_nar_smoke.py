#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""NAR (地方競馬) E2E スモークテスト

実際の NV-Link COM API を使って以下のフローを一気通貫テスト:
  1. NV-Link 接続・初期化
  2. 直近の開催日1日分のデータ取得
  3. パース → SQLite DB 格納
  4. SQL クエリで件数・値の妥当性検証

実行方法 (A6 上で VNC/RDP 経由):
  cd C:\\Users\\mitsu\\work\\jrvltsql
  C:\\Users\\mitsu\\AppData\\Local\\Programs\\Python\\Python312-32\\python.exe tests\\e2e\\e2e_nar_smoke.py
"""

import io
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "buffer"):
            setattr(sys, stream_name, io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"))

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    sys.coinit_flags = 2
except AttributeError:
    pass

os.environ["JLTSQL_SKIP_AUTO_LOGGING"] = "1"


def find_recent_weekday(days_back_start=2, days_back_end=10):
    """地方競馬は平日開催が多いので、直近の平日を探す"""
    today = datetime.now()
    for i in range(days_back_start, days_back_end):
        d = today - timedelta(days=i)
        if d.weekday() < 5:  # 月-金
            return d.strftime("%Y%m%d")
    return (today - timedelta(days=3)).strftime("%Y%m%d")


def main():
    from src.database.schema import create_all_tables
    from src.database.sqlite_handler import SQLiteDatabase
    from src.importer.batch import BatchProcessor
    from src.utils.data_source import DataSource

    print("=" * 60)
    print("NAR E2E スモークテスト")
    print("=" * 60)

    target_date = find_recent_weekday()
    print(f"\n対象日: {target_date}")

    db_path = project_root / "data" / "e2e_nar_test.db"
    if db_path.exists():
        db_path.unlink()

    results = {"pass": 0, "fail": 0, "skip": 0}

    def check(name, condition, detail=""):
        if condition is None:
            results["skip"] += 1
            print(f"  SKIP: {name} {detail}")
        elif condition:
            results["pass"] += 1
            print(f"  PASS: {name} {detail}")
        else:
            results["fail"] += 1
            print(f"  FAIL: {name} {detail}")

    try:
        # --- Step 1: DB作成 ---
        print("\n--- Step 1: DB・テーブル作成 ---")
        config = {"path": str(db_path)}
        db = SQLiteDatabase(config)
        db.connect()
        create_all_tables(db, data_source=DataSource.NAR)
        check("テーブル作成", True)

        # --- Step 2: データ取得→格納 ---
        print(f"\n--- Step 2: NAR データ取得・格納 ({target_date}) ---")
        processor = BatchProcessor(
            database=db,
            batch_size=500,
            show_progress=False,
            data_source=DataSource.NAR,
        )

        t0 = time.time()
        try:
            stats = processor.process_date_range(
                data_spec="RACE",
                from_date=target_date,
                to_date=target_date,
                option=1,
            )
            elapsed = time.time() - t0
            print(f"  取得完了: {elapsed:.1f}秒")

            fetched = getattr(stats, "records_fetched", None) or getattr(stats, "fetched", 0)
            imported = getattr(stats, "records_imported", None) or getattr(stats, "imported", 0)
            failed = getattr(stats, "records_failed", None) or getattr(stats, "failed", 0)
            print(f"  fetched={fetched}, imported={imported}, failed={failed}")

            check("データ取得", fetched > 0, f"({fetched} records)")
            check("データ格納", imported > 0, f"({imported} records)")
            check("エラー件数", failed == 0, f"({failed} errors)")

        except Exception as e:
            elapsed = time.time() - t0
            err_str = str(e)
            if "-502" in err_str or "502" in err_str:
                check("データ取得", None, "(-502: データ準備中のためスキップ)")
            else:
                check("データ取得", False, f"({e})")
                raise

        # --- Step 3: SQLクエリ検証 ---
        print("\n--- Step 3: SQLクエリ検証 ---")
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        # NAR テーブル一覧を取得
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f"  作成されたテーブル数: {len(tables)}")

        # NN_ プレフィックスのテーブルがあるか確認
        nar_tables = [t for t in tables if t.startswith("NN_")]
        if nar_tables:
            prefix = "NN_"
        else:
            # NL_ プレフィックスの可能性もある（スキーマ設計次第）
            nar_tables = [t for t in tables if t.startswith("NL_")]
            prefix = "NL_"

        check("NARテーブル存在", len(nar_tables) > 0, f"({len(nar_tables)} tables, prefix={prefix})")

        # レーステーブルを探す
        race_table = f"{prefix}RA" if f"{prefix}RA" in nar_tables else None
        if race_table:
            cur.execute(f"SELECT COUNT(*) FROM {race_table}")
            ra_count = cur.fetchone()[0]
            check(f"{race_table} レコード数", ra_count > 0, f"({ra_count} races)")
        else:
            check("レーステーブル", None, "(テーブルが見つからない)")

        # 出走馬テーブル
        entry_table = f"{prefix}SE" if f"{prefix}SE" in nar_tables else None
        if entry_table:
            cur.execute(f"SELECT COUNT(*) FROM {entry_table}")
            se_count = cur.fetchone()[0]
            check(f"{entry_table} レコード数", se_count > 0, f"({se_count} entries)")

        conn.close()

    except Exception as e:
        print(f"\n致命的エラー: {e}")
        import traceback
        traceback.print_exc()
        results["fail"] += 1

    finally:
        try:
            if db_path.exists():
                db_path.unlink()
                print(f"\nテストDB削除: {db_path}")
        except Exception:
            pass

    print("\n" + "=" * 60)
    total = results["pass"] + results["fail"] + results["skip"]
    print(f"結果: {results['pass']} PASS / {results['fail']} FAIL / {results['skip']} SKIP (計 {total})")
    if results["fail"] == 0:
        print("✓ PASS")
    else:
        print("✗ FAIL")
    print("=" * 60)

    return 0 if results["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
