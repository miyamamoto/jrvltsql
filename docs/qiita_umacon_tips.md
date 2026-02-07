# UmaConn（地方競馬DATA）をPythonで使う際の注意点まとめ

## はじめに

地方競馬DATAの **UmaConn（NV-Link API）** を Python から使用する際に遭遇した問題と解決策をまとめます。JV-Link（JRA）の経験があっても、UmaConn 特有の挙動でハマることがあるので参考になれば幸いです。

## 環境

- Windows 11
- Python 3.12 (32-bit) / Python 3.13 (64-bit)
- UmaConn（NV-Link）
- pywin32

## 注意点1: 正しい ProgID を使う

### 問題

COM オブジェクトの生成に失敗する。

```python
# これは失敗する
nv = win32com.client.Dispatch("NVDTLab.NVLink")
# エラー: クラス文字列が無効です (-2147221005)
```

### 解決策

NV-Link の正しい ProgID は `NVDTLabLib.NVLink` です。

```python
# 正しい書き方
nv = win32com.client.Dispatch("NVDTLabLib.NVLink")
```

| API | ProgID |
|-----|--------|
| JV-Link (JRA) | `JVDTLab.JVLink` |
| NV-Link (NAR) | `NVDTLabLib.NVLink` |

## 注意点2: COM メモリリークへの対処

### 問題

長時間の連続データ取得で COM オブジェクトのメモリが枯渇し、`NVRead` が `-1`（ダウンロード中）を返し続ける。

```python
# 数日分のデータを連続取得
for date in date_range:
    result = nv.NVOpen("RACE", date, 1, 0, 0)
    while True:
        rc, buff, size, fname = nv.NVRead("", 110000, "")
        if rc == 0:
            break
        elif rc == -1:
            time.sleep(0.1)  # 永遠にここから抜けない...
```

### 原因

COM オブジェクトを長時間使い続けると、内部的なリソースリークが発生する可能性があります。特に数日分のデータを一度に取得しようとすると発生しやすいです。

### 解決策: サブプロセスで日単位に分割

各日のデータ取得を別プロセスで実行し、プロセス終了時に COM リソースを完全に解放します。

```python
import subprocess
import sys
from datetime import datetime, timedelta

def fetch_single_day(target_date: str) -> list:
    """サブプロセスで1日分のデータを取得"""
    script = f'''
import win32com.client
import json

nv = win32com.client.Dispatch("NVDTLabLib.NVLink")
nv.NVInit("UNKNOWN")

result = nv.NVOpen("RACE", "{target_date}000000", 1, 0, 0)
records = []

if result[0] in (-1, -301):
    import time
    # ダウンロード完了待機
    for _ in range(300):
        status = nv.NVStatus()
        if status == 0:
            break
        time.sleep(0.2)

# データ読み取り
for _ in range(10000):
    rc, buff, size, fname = nv.NVRead("", 110000, "")
    if rc > 0:
        records.append({{"file": fname, "size": rc}})
    elif rc == 0:
        break
    elif rc == -1:
        time.sleep(0.1)
    else:
        break

nv.NVClose()
print(json.dumps({{"count": len(records)}}))
'''

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode == 0:
        import json
        return json.loads(result.stdout)
    return {"count": 0, "error": result.stderr}


# 使用例: 過去7日分を取得
today = datetime.now()
for i in range(7):
    date = (today - timedelta(days=i)).strftime("%Y%m%d")
    result = fetch_single_day(date)
    print(f"{date}: {result['count']} records")
```

## 注意点3: NVStatus の解釈

### NVStatus の戻り値

| 値 | 意味 |
|---|------|
| 0 | ダウンロード完了（または不要） |
| 1〜100 | ダウンロード進捗（%） |
| -1 | ダウンロード中（進捗不明） |
| -2 | ダウンロードエラー |
| -203 | Not Opened（NVOpenが呼ばれていない） |
| -502 | サーバーエラー |

### よくある勘違い

`NVStatus() == 0` は「完了」だけでなく「ダウンロード不要」の場合も含みます。`NVOpen` の戻り値で `download_count` を確認してください。

```python
rc, read_count, download_count, last_ts = nv.NVOpen("RACE", fromtime, 1, 0, 0)

if download_count == 0:
    print("新規データなし、即座に読み取り可能")
else:
    print(f"{download_count}件のダウンロードが必要")
    # NVStatus でダウンロード完了を待機
```

## 注意点4: 64bit Python での使用

### 問題

64bit Python から COM 接続すると `REGDB_E_CLASSNOTREG` エラーが発生する。

### 解決策

DLL Surrogate レジストリ設定が必要です。詳細は別記事を参照してください。

👉 [64bit Pythonから32bit COM DLL（JV-Link/UmaConn）を使う方法](./qiita_64bit_python_com.md)

### NV-Link 特有の追加作業

NV-Link は `RunAs` レジストリ値が設定されており、DLL Surrogate と競合します。この値の削除が必要です。

```reg
[HKEY_CLASSES_ROOT\AppID\{F726BBA6-5784-4529-8C67-26E152D49D73}]
"RunAs"=-
```

## 注意点5: データファイル名の形式

### JV-Link との違い

NV-Link のファイル名形式は JV-Link と異なります。

```
# JV-Link (JRA)
RACERA2024120108010512.jvd

# NV-Link (NAR)
20241201_1_RACE.dat
```

ファイル名からレース情報を抽出する場合は、形式の違いに注意してください。

## 注意点6: レコード仕様の違い

### フィールド定義

NAR（地方競馬）のレコード仕様は JRA とは異なります。同じフィールド名でも長さや位置が違うことがあります。

公式のレコード仕様書を確認してください：
- [地方競馬DATA レコードレイアウト](https://www.keiba-data.net/)

## サンプルスクリプト

本記事で紹介したコードを含む完全なサンプルスクリプトは Gist で公開しています：

- [check_dll_surrogate.py](https://gist.github.com/miyamamoto/d71445a0e992d7e34372fb5cf10c42fe) - DLL Surrogate 設定確認・修正
- [remove_dll_surrogate.py](https://gist.github.com/miyamamoto/2ce62fdcb64567901ef7ef3b000be039) - DLL Surrogate 設定削除
- [nvlink_subprocess_fetch.py](https://gist.github.com/miyamamoto/cbe26d18173fce119a3f6ef56e31d9d5) - サブプロセス方式でのデータ取得

## まとめ

| 注意点 | 対策 |
|-------|------|
| ProgID が違う | `NVDTLabLib.NVLink` を使う |
| メモリリーク | サブプロセスで日単位に分割 |
| NVStatus の解釈 | download_count も確認 |
| 64bit Python | DLL Surrogate + RunAs削除 |

UmaConn は JV-Link と似ていますが、細かい違いがあります。本記事が同じ問題でハマっている方の参考になれば幸いです。
