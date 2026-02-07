#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NV-Link（UmaConn）サブプロセス方式データ取得スクリプト

COM メモリリークを回避するため、日単位でサブプロセスを起動して
データを取得します。

使用方法:
    python nvlink_subprocess_fetch.py              # 過去7日分を取得
    python nvlink_subprocess_fetch.py --days 30    # 過去30日分を取得
    python nvlink_subprocess_fetch.py --date 20241201  # 特定日のみ取得

必要条件:
    - pywin32 がインストールされていること
    - UmaConn（地方競馬DATA）がセットアップ済みであること
    - 初回セットアップはGUIで完了させておくこと

Author: @your_username
License: MIT
"""

import subprocess
import shlex
import re
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any


# サブプロセスで実行するスクリプトテンプレート
FETCH_SCRIPT_TEMPLATE = '''
import win32com.client
import json
import time
import sys

def fetch_data(target_date: str, data_type: str = "RACE") -> dict:
    """指定日のデータを取得"""
    result = {
        "date": target_date,
        "type": data_type,
        "records": [],
        "error": None,
        "download_status": None
    }

    try:
        nv = win32com.client.Dispatch("NVDTLabLib.NVLink")
        rc = nv.NVInit("UNKNOWN")

        if rc != 0:
            result["error"] = f"NVInit failed: {{rc}}"
            return result

        # データを開く（option=1: 通常モード）
        fromtime = f"{{target_date}}000000"
        open_result = nv.NVOpen(data_type, fromtime, 1, 0, 0)

        if isinstance(open_result, tuple):
            open_rc, read_count, download_count, last_ts = open_result
        else:
            open_rc = open_result
            read_count = download_count = 0
            last_ts = ""

        result["open_rc"] = open_rc
        result["read_count"] = read_count
        result["download_count"] = download_count

        # ダウンロードが必要な場合は待機
        if open_rc in (-1, -301) and download_count > 0:
            max_wait = 120  # 最大120秒待機
            start_time = time.time()

            while time.time() - start_time < max_wait:
                status = nv.NVStatus()
                result["download_status"] = status

                if status == 0:
                    # ダウンロード完了
                    break
                elif status > 0:
                    # 進捗表示（1-100%）
                    pass
                elif status < 0 and status != -1:
                    # エラー
                    result["error"] = f"NVStatus error: {{status}}"
                    break

                time.sleep(0.3)

        # データ読み取り
        max_reads = 10000
        for i in range(max_reads):
            nv_result = nv.NVRead("", 110000, "")

            if isinstance(nv_result, tuple):
                read_rc = nv_result[0]
                buff = nv_result[1] if len(nv_result) > 1 else ""
                size = nv_result[2] if len(nv_result) > 2 else 0
                fname = nv_result[3] if len(nv_result) > 3 else ""
            else:
                read_rc = nv_result
                buff = fname = ""
                size = 0

            if read_rc > 0:
                # データ取得成功
                result["records"].append({
                    "file": fname,
                    "size": read_rc,
                    "spec": buff[:2] if buff else ""
                })
            elif read_rc == 0:
                # 全データ読み取り完了
                break
            elif read_rc == -1:
                # ダウンロード中、少し待機
                time.sleep(0.1)
            else:
                # エラー
                if not result["error"]:
                    result["error"] = f"NVRead error: {{read_rc}}"
                break

        nv.NVClose()

    except Exception as e:
        result["error"] = str(e)

    return result

if __name__ == "__main__":
    result = fetch_data("{target_date}", "{data_type}")
    print(json.dumps(result, ensure_ascii=False))
'''


def fetch_single_day(
    target_date: str,
    data_type: str = "RACE",
    timeout: int = 180
) -> Dict[str, Any]:
    """サブプロセスで1日分のデータを取得

    Args:
        target_date: 対象日 (YYYYMMDD形式)
        data_type: データ種別 (RACE, DIFF等)
        timeout: タイムアウト秒数

    Returns:
        取得結果の辞書
    """
    # Validate inputs to prevent code injection via .format()
        for param_name, param_value in [("target_date", target_date), ("data_type", data_type)]:
            if not re.match(r'^[a-zA-Z0-9_-]+$', str(param_value)):
                raise ValueError(f"Invalid {param_name}: {param_value}")
        script = FETCH_SCRIPT_TEMPLATE.format(
        target_date=target_date,
        data_type=data_type
    )

    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8"
        )

        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        else:
            return {
                "date": target_date,
                "type": data_type,
                "records": [],
                "error": result.stderr or "Unknown error"
            }

    except subprocess.TimeoutExpired:
        return {
            "date": target_date,
            "type": data_type,
            "records": [],
            "error": f"Timeout after {timeout} seconds"
        }
    except json.JSONDecodeError as e:
        return {
            "date": target_date,
            "type": data_type,
            "records": [],
            "error": f"JSON decode error: {e}"
        }
    except Exception as e:
        return {
            "date": target_date,
            "type": data_type,
            "records": [],
            "error": str(e)
        }


def fetch_date_range(
    start_date: datetime,
    end_date: datetime,
    data_type: str = "RACE",
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """日付範囲のデータを取得

    Args:
        start_date: 開始日
        end_date: 終了日
        data_type: データ種別
        verbose: 進捗表示

    Returns:
        各日の取得結果リスト
    """
    results = []
    current = start_date

    while current <= end_date:
        date_str = current.strftime("%Y%m%d")

        if verbose:
            print(f"Fetching {date_str}...", end=" ", flush=True)

        result = fetch_single_day(date_str, data_type)
        results.append(result)

        if verbose:
            record_count = len(result.get("records", []))
            if result.get("error"):
                print(f"ERROR: {result['error']}")
            else:
                print(f"{record_count} records")

        current += timedelta(days=1)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="NV-Link（UmaConn）サブプロセス方式データ取得"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="取得する過去日数（デフォルト: 7）"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="特定日を取得（YYYYMMDD形式）"
    )
    parser.add_argument(
        "--type",
        type=str,
        default="RACE",
        help="データ種別（デフォルト: RACE）"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="進捗表示を抑制"
    )
    args = parser.parse_args()

    if args.date:
        # 特定日のみ取得
        print(f"Fetching {args.date}...")
        result = fetch_single_day(args.date, args.type)

        if result.get("error"):
            print(f"ERROR: {result['error']}")
            return 1

        print(f"Records: {len(result['records'])}")
        for rec in result["records"][:5]:
            print(f"  - {rec['file']} ({rec['size']} bytes)")
        if len(result["records"]) > 5:
            print(f"  ... and {len(result['records']) - 5} more")

    else:
        # 日付範囲を取得
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days - 1)

        print(f"Fetching {args.days} days of data...")
        print(f"Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print()

        results = fetch_date_range(
            start_date,
            end_date,
            args.type,
            verbose=not args.quiet
        )

        # サマリー
        print()
        print("=" * 50)
        total_records = sum(len(r.get("records", [])) for r in results)
        error_count = sum(1 for r in results if r.get("error"))
        print(f"Total: {total_records} records from {len(results)} days")
        if error_count:
            print(f"Errors: {error_count} days")

    return 0


if __name__ == "__main__":
    sys.exit(main())
