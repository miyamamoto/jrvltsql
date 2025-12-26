# NV-Link（地方競馬データ）のCOMメモリ制限を克服する - Pythonでの実装パターン

## はじめに

地方競馬のデータを取得するためのNV-Link（UmaConn）APIは、JRA（中央競馬）のJV-Linkと同様のCOM APIを提供しています。しかし、実際に大量のデータを取得しようとすると、**COMメモリ制限**という厄介な問題に直面します。

本記事では、この問題の原因と解決策を紹介します。

## 環境

- Windows 10/11
- Python 3.12 (32-bit) ※COM APIは32-bit DLLのため必須
- pywin32
- UmaConn（地方競馬データサービス）

## 問題：COMメモリ制限

### 症状

NV-Linkで数千レコードを連続して読み取ると、突然以下のようなエラーが発生します：

```
pywintypes.com_error: (-2147418113, 'Catastrophic failure', None, None)
# または
E_UNEXPECTED (-2147418113)
```

### 原因

COMオブジェクトは内部でメモリを蓄積し、約**1,000〜2,500レコード**を処理すると限界に達します。これはNV-Link固有の問題ではなく、COMの仕様によるものです。

## 解決策：サブプロセス方式

Pythonでは、プログラム全体を再起動する代わりに、**サブプロセス**を使って各日のデータを独立したプロセスで取得します。

### アーキテクチャ

```
メインプロセス
    ├── 12/19のデータ取得 (subprocess) → 終了してメモリ解放
    ├── 12/20のデータ取得 (subprocess) → 終了してメモリ解放
    ├── 12/21のデータ取得 (subprocess) → 終了してメモリ解放
    └── ...
```

### 実装のポイント

1. **1日分ずつサブプロセスで処理** - COMメモリが限界に達する前にプロセス終了
2. **skipFilesパターン** - 取得済みファイルをスキップしてリトライ
3. **十分な待機時間** - レート制限(-421)対策
4. **read_countによる完了判定** - 全データ取得済みを検出

## サンプルコード

### メインスクリプト（親プロセス）

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NV-Link サブプロセス方式データ取得
COMメモリ制限対策として、1日分ずつ別プロセスで取得
"""

import subprocess
import sys
import json
import time
from datetime import datetime, timedelta

# 32-bit Python のパス（COM APIは32-bit必須）
PYTHON_32BIT = r"C:\path\to\python312-32\python.exe"
MAX_RETRIES = 35

# 子プロセス用スクリプト（文字列として埋め込み）
CHILD_SCRIPT = r'''
import sys
import json
sys.path.insert(0, r'C:\path\to\your\project')

from your_nvlink_wrapper import NVLinkWrapper
import time

RECOVERABLE_ERRORS = (-203, -402, -403, -502, -503)

def fetch_day(fromtime, skip_files=None):
    """1日分のデータを取得（skipFilesでスキップ）"""
    if skip_files is None:
        skip_files = set()
    else:
        skip_files = set(skip_files)

    result = {
        "records": 0,
        "complete": False,
        "error": None,
        "fetched_files": [],
        "read_count": 0,
        "download_count": 0
    }

    try:
        wrapper = NVLinkWrapper()
        wrapper.nv_init()

        rc, read_count, download_count, last_ts = wrapper.nv_open("RACE", fromtime, 1)
        result["read_count"] = read_count
        result["download_count"] = download_count

        if rc < 0 and rc != -1:
            result["error"] = f"NVOpen: {rc}"
            return result

        if read_count == 0 and download_count == 0:
            result["complete"] = True
            return result

        # ダウンロード待機（80msポーリング）
        if download_count > 0:
            start = time.time()
            last_progress = 0
            stay_start = time.time()

            while time.time() - start < 180:
                status = wrapper.nv_status()
                if status > 0:
                    if status != last_progress:
                        last_progress = status
                        stay_start = time.time()
                elif status == 0:
                    break
                elif status < 0:
                    result["error"] = f"Download: {status}"
                    wrapper.nv_close()
                    return result

                # 60秒間進捗がなければタイムアウト
                if last_progress > 0 and time.time() - stay_start > 60:
                    result["error"] = "Download stalled"
                    wrapper.nv_close()
                    return result

                time.sleep(0.08)

        # データ読み取り（skipFilesでスキップ）
        records = 0
        fetched_files = []

        for _ in range(100000):
            try:
                ret_code, data, fname = wrapper.nv_read()
            except Exception as e:
                # COMエラー発生 - 取得済み情報を返す
                result["error"] = f"COM at {records}"
                result["records"] = records
                result["fetched_files"] = fetched_files
                wrapper.nv_close()
                return result

            if ret_code > 0:
                # スキップ対象ファイルはスキップ
                if fname and fname in skip_files:
                    continue
                records += 1
                if fname:
                    fetched_files.append(fname)

            elif ret_code == 0:
                # 全データ読み取り完了
                result["complete"] = True
                break

            elif ret_code == -1:
                # ファイル切り替え
                continue

            elif ret_code in RECOVERABLE_ERRORS:
                # 回復可能エラー: FileDelete + 継続
                if fname:
                    try:
                        wrapper.nv_file_delete(fname)
                    except:
                        pass
                continue

            else:
                result["error"] = f"Fatal: {ret_code}"
                break

        wrapper.nv_close()
        result["records"] = records
        result["fetched_files"] = fetched_files

    except Exception as e:
        result["error"] = str(e)[:100]

    return result

if __name__ == "__main__":
    fromtime = sys.argv[1]
    skip_files = json.loads(sys.argv[2]) if len(sys.argv) > 2 else []
    result = fetch_day(fromtime, skip_files)
    print("RESULT_JSON:" + json.dumps(result))
'''


def run_subprocess_fetch(fromtime: str, skip_files: list = None) -> dict:
    """子プロセスで1日分のデータを取得"""
    if skip_files is None:
        skip_files = []

    try:
        proc = subprocess.run(
            [PYTHON_32BIT, "-c", CHILD_SCRIPT, fromtime, json.dumps(skip_files)],
            capture_output=True,
            text=True,
            timeout=300
        )

        for line in proc.stdout.split('\n'):
            if line.startswith('RESULT_JSON:'):
                return json.loads(line[12:])

        return {"records": 0, "complete": False, "error": f"No JSON: {proc.stdout[-100:]}"}

    except subprocess.TimeoutExpired:
        return {"records": 0, "complete": False, "error": "Timeout"}
    except Exception as e:
        return {"records": 0, "complete": False, "error": str(e)}


def fetch_day_with_retry(target_date: datetime, max_retries: int = MAX_RETRIES) -> tuple:
    """リトライ付きで1日分のデータを完全取得"""
    fromtime = target_date.strftime("%Y%m%d000000")
    date_label = target_date.strftime("%m/%d")

    total_records = 0
    all_files = set()  # 取得済みファイル（スキップ用）
    retries = 0
    consecutive_no_progress = 0
    last_total = 0

    while retries < max_retries:
        # 取得済みファイルをスキップ
        result = run_subprocess_fetch(fromtime, list(all_files))

        records = result.get("records", 0)
        complete = result.get("complete", False)
        error = result.get("error")
        fetched_files = result.get("fetched_files", [])

        # 新しく取得したファイルを記録
        total_records += records
        all_files.update(fetched_files)

        if complete:
            print(f"[{date_label}] {total_records}レコード OK")
            return total_records, True, retries

        if error:
            retries += 1

            # 進捗チェック
            if total_records == last_total:
                consecutive_no_progress += 1
            else:
                consecutive_no_progress = 0
                last_total = total_records

            # 完了判定: read_count <= 取得済みファイル数 なら全データ取得済み
            read_count = result.get("read_count", 0)
            if read_count > 0 and len(all_files) >= read_count:
                print(f"[{date_label}] {total_records}レコード OK (全データ取得済み)")
                return total_records, True, retries

            # エラー種別に応じた待機時間
            if "-421" in str(error):
                # レート制限: 30秒待機
                print(f"[{date_label}] レート制限、30秒待機...")
                time.sleep(30)
            elif "-413" in str(error):
                # サーバーエラー: 20秒待機
                print(f"[{date_label}] サーバーエラー、20秒待機...")
                time.sleep(20)
            elif "COM" in str(error):
                # COMエラー: 5-10秒待機
                wait_time = 10 if consecutive_no_progress >= 3 else 5
                print(f"[{date_label}] {total_records}レコード取得中...")
                time.sleep(wait_time)
            else:
                print(f"[{date_label}] エラー: {error[:40]}...")
                time.sleep(10)
            continue

        if records == 0 and not complete:
            retries += 1
            time.sleep(5)
            continue

    print(f"[{date_label}] {total_records}レコード (リトライ上限)")
    return total_records, False, retries


def main():
    """過去7日間のデータを取得"""
    print("=" * 60)
    print("NV-Link サブプロセス方式データ取得")
    print("=" * 60)

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    total_records = 0
    complete_days = 0

    for i, days_ago in enumerate(range(7, 0, -1)):
        target_date = today - timedelta(days=days_ago)
        records, complete, retries = fetch_day_with_retry(target_date)
        total_records += records

        if complete:
            complete_days += 1

        # 日付間の待機（レート制限対策）
        if i < 6:
            print(f"    次の日まで10秒待機...")
            time.sleep(10)

    print()
    print("=" * 60)
    print(f"結果: {total_records}レコード")
    print(f"  完了: {complete_days}日 / 7日")
    print("=" * 60)

    return complete_days == 7


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

### NVLinkWrapper クラス（参考実装）

```python
import win32com.client

class NVLinkWrapper:
    """NV-Link COM APIのラッパー"""

    def __init__(self):
        self._nv = None

    def nv_init(self, sid: str = "UNKNOWN") -> int:
        """初期化"""
        self._nv = win32com.client.Dispatch("NVDTLabLib.NVLink")
        return self._nv.NVInit(sid)

    def nv_open(self, dataspec: str, fromtime: str, option: int) -> tuple:
        """データオープン"""
        result = self._nv.NVOpen(dataspec, fromtime, option, 0, 0)
        if isinstance(result, tuple):
            return result[0], result[1], result[2], result[3]
        return result, 0, 0, ""

    def nv_status(self) -> int:
        """ダウンロード状況取得"""
        return self._nv.NVStatus()

    def nv_read(self) -> tuple:
        """データ読み取り"""
        result = self._nv.NVRead("", 110000, "")
        if isinstance(result, tuple):
            ret_code = result[0]
            data = result[1] if len(result) > 1 else b""
            fname = result[3] if len(result) > 3 else ""

            # 文字列の場合はバイト列に変換
            if isinstance(data, str):
                data = data.encode('cp932', errors='replace')

            return ret_code, data, fname
        return result, b"", ""

    def nv_close(self):
        """クローズ"""
        if self._nv:
            self._nv.NVClose()

    def nv_file_delete(self, filename: str) -> int:
        """ファイル削除（エラー回復用）"""
        return self._nv.NVFiledelete(filename)

    def reinitialize_com(self):
        """COM再初期化"""
        if self._nv:
            try:
                self._nv.NVClose()
            except:
                pass
        self._nv = None
```

## エラーコード一覧

| コード | 意味 | 対処法 |
|--------|------|--------|
| -1 | ファイル切り替え | 継続 |
| -203 | ファイル読み取りエラー | FileDelete + 継続 |
| -402 | ダウンロードエラー | FileDelete + 継続 |
| -403 | ダウンロードエラー | FileDelete + 継続 |
| -413 | サーバーエラー | 20秒待機 + リトライ |
| -421 | レート制限 | 30秒待機 + リトライ |
| -502 | サーバーエラー | FileDelete + 継続 |
| -503 | サーバーエラー | FileDelete + 継続 |

## 実行結果

```
============================================================
NV-Link サブプロセス方式データ取得
============================================================

[12/19] 2530レコード OK (リトライ14回)
    次の日まで10秒待機...
[12/20] 2155レコード OK (リトライ12回)
    次の日まで10秒待機...
[12/21] 3698レコード OK (全データ取得済み)
    次の日まで10秒待機...
[12/22] 3156レコード OK (全データ取得済み)
    次の日まで10秒待機...
[12/23] 1500レコード OK (リトライ1回)
    次の日まで10秒待機...
[12/24] 2467レコード OK
    次の日まで10秒待機...
[12/25] 1328レコード OK

============================================================
結果: 16834レコード
  完了: 7日 / 7日
============================================================
```

## まとめ

NV-LinkのCOMメモリ制限は、以下の方法で克服できます：

1. **サブプロセス方式**: 1日分ずつ別プロセスで処理し、メモリを完全解放
2. **skipFilesパターン**: 取得済みファイルをスキップしてリトライ
3. **適切な待機時間**: レート制限対策として十分な待機時間を設定
4. **read_count完了判定**: 全データ取得済みを正確に検出

この方法により、地方競馬の大量データを安定して取得できるようになりました。

## 参考

- [UmaConn](https://chiho.k-ba.com/) - 地方競馬データサービス

## タグ

`Python` `競馬` `COM` `地方競馬` `NVLink` `UmaConn`
