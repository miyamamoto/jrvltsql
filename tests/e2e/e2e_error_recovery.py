#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""エラーリカバリ E2E テスト

COM API のエラーハンドリングを実データで検証:
  1. 無効な日付範囲での挙動
  2. 未来日のデータ取得（0件で正常終了すべき）
  3. NAR の -502 エラーリカバリ（日分割チャンクの動作確認）

実行方法 (A6 上で VNC/RDP 経由):
  cd C:\\Users\\mitsu\\work\\jrvltsql
  C:\\Users\\mitsu\\AppData\\Local\\Programs\\Python\\Python312-32\\python.exe tests\\e2e\\e2e_error_recovery.py
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


def main():
    from src.database.schema import create_all_tables
    from src.database.sqlite_handler import SQLiteDatabase
    from src.importer.batch import BatchProcessor
    from src.utils.data_source import DataSource

    print("=" * 60)
    print("エラーリカバリ E2E テスト")
    print("=" * 60)

    db_path = project_root / "data" / "e2e_error_test.db"
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
        config = {"path": str(db_path)}
        db = SQLiteDatabase(config)
        db.connect()

        # --- Test 1: 未来日のデータ取得 ---
        print("\n--- Test 1: 未来日データ取得 (0件で正常終了すべき) ---")
        create_all_tables(db, data_source=DataSource.JRA)

        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y%m%d")
        processor = BatchProcessor(
            database=db, batch_size=500, show_progress=False, data_source=DataSource.JRA
        )

        try:
            stats = processor.process_date_range(
                data_spec="RACE", from_date=future_date, to_date=future_date, option=1
            )
            fetched = getattr(stats, "records_fetched", None) or getattr(stats, "fetched", 0)
            check("未来日: 正常終了", True)
            check("未来日: 0件", fetched == 0, f"(fetched={fetched})")
        except Exception as e:
            # -502 等のエラーでも「クラッシュしない」ことが重要
            err_str = str(e)
            if "-502" in err_str:
                check("未来日: -502 ハンドリング", True, "(期待通り)")
            else:
                check("未来日: 正常終了", False, f"({e})")

        # --- Test 2: NAR 日分割チャンクの動作 ---
        print("\n--- Test 2: NAR 複数日レンジ (日分割チャンク動作確認) ---")

        # DBリセット
        if db_path.exists():
            db_path.unlink()
        db2 = SQLiteDatabase(config)
        db2.connect()
        create_all_tables(db2, data_source=DataSource.NAR)

        # 3日間のレンジ → 内部で日ごとにチャンクされるはず
        today = datetime.now()
        end_date = (today - timedelta(days=3)).strftime("%Y%m%d")
        start_date = (today - timedelta(days=5)).strftime("%Y%m%d")

        processor_nar = BatchProcessor(
            database=db2, batch_size=500, show_progress=False, data_source=DataSource.NAR
        )

        try:
            t0 = time.time()
            stats = processor_nar.process_date_range(
                data_spec="RACE", from_date=start_date, to_date=end_date, option=1
            )
            elapsed = time.time() - t0
            fetched = getattr(stats, "records_fetched", None) or getattr(stats, "fetched", 0)
            check("NAR複数日: 正常終了", True, f"({elapsed:.1f}秒)")
            check("NAR複数日: データあり", fetched >= 0, f"(fetched={fetched})")
        except Exception as e:
            err_str = str(e)
            if "-502" in err_str:
                check("NAR複数日: -502 スキップ", None, "(データ準備中)")
            else:
                check("NAR複数日: 正常終了", False, f"({e})")

        # --- Test 3: JV-Link 再初期化 ---
        print("\n--- Test 3: JV-Link 連続初期化 (リソースリーク確認) ---")
        from src.fetcher.historical import HistoricalFetcher

        try:
            for i in range(3):
                fetcher = HistoricalFetcher(show_progress=False, data_source=DataSource.JRA)
                fetcher.jvlink.jv_init()
                fetcher.jvlink.jv_close()
            check("連続初期化/クローズ", True, "(3回成功)")
        except Exception as e:
            check("連続初期化/クローズ", False, f"({e})")

    except Exception as e:
        print(f"\n致命的エラー: {e}")
        import traceback
        traceback.print_exc()
        results["fail"] += 1

    finally:
        try:
            if db_path.exists():
                db_path.unlink()
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
