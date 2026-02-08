# E2E テスト（実機テスト）

## 概要

このディレクトリには、A6 (Windows) 上で **実際の COM API** を使って実行する End-to-End テストが含まれます。
CI では実行できません。COM API（JV-Link / NV-Link）が必要なため、GUI コンテキストのある Windows 環境で手動実行します。

## 前提条件

| 項目 | 要件 |
|------|------|
| OS | Windows (A6: 192.168.0.250) |
| Python | 32-bit Python 3.12 (`C:\Users\mitsu\AppData\Local\Programs\Python\Python312-32\python.exe`) |
| JV-Link | インストール済み、サービスキー設定済み |
| NV-Link | インストール済み、サービスキー設定済み |
| 実行方法 | **RDP/VNC でログインし、コマンドプロンプトから実行**（SSH不可） |

## テストスクリプト一覧

| スクリプト | 内容 | 所要時間目安 |
|-----------|------|-------------|
| `e2e_jra_smoke.py` | JRA: 1日分データ取得→パース→DB格納→SQLクエリ検証 | 2-5分 |
| `e2e_nar_smoke.py` | NAR: 1日分データ取得→パース→DB格納→SQLクエリ検証 | 2-5分 |
| `e2e_error_recovery.py` | エラーリカバリ（-502等）の動作確認 | 1-3分 |

## 実行手順

### 1. A6 に VNC/RDP で接続

```
VNC: 192.168.0.250:5900 (pass: vnc123)
```

### 2. コマンドプロンプトを開く

```cmd
cd C:\Users\mitsu\work\jrvltsql
```

### 3. JRA スモークテスト実行

```cmd
C:\Users\mitsu\AppData\Local\Programs\Python\Python312-32\python.exe tests\e2e\e2e_jra_smoke.py 2>&1 | tee data\e2e_jra_result.txt
```

### 4. NAR スモークテスト実行

```cmd
C:\Users\mitsu\AppData\Local\Programs\Python\Python312-32\python.exe tests\e2e\e2e_nar_smoke.py 2>&1 | tee data\e2e_nar_result.txt
```

### 5. エラーリカバリテスト実行

```cmd
C:\Users\mitsu\AppData\Local\Programs\Python\Python312-32\python.exe tests\e2e\e2e_error_recovery.py 2>&1 | tee data\e2e_error_result.txt
```

## 結果の確認

各スクリプトは終了時に `PASS` / `FAIL` を表示します。
詳細ログは `data/e2e_*.txt` に出力されます。

## 注意事項

- **SSH からは実行不可**（COM API は GUI コンテキストが必要）
- テスト用DBは `data/e2e_test.db` に作成され、テスト後に自動削除されます
- 既存の `data/keiba.db` には一切影響しません
- `-502` エラー（データ準備中）が出た場合、テストはスキップ扱いになります
