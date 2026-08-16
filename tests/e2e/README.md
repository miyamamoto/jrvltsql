# E2E テスト（実機テスト）

## 概要

このディレクトリには、Windows 実機上で **実際の COM API** を使って実行する End-to-End テストが含まれます。
CI では実行できません。COM API（JV-Link）が必要なため、GUI コンテキストのある Windows 環境で手動実行します。

## 前提条件

| 項目 | 要件 |
|------|------|
| OS | Windows 10 / 11 |
| Python | 32-bit Python 3.12 以上（リリース検証済み経路） |
| JV-Link | 32-bit 版をインストール済み、サービスキー設定済み |
| 実行方法 | **RDP/VNC でログインし、コマンドプロンプトから実行**（SSH不可） |

## テストスクリプト一覧

| スクリプト | 内容 | 所要時間目安 |
|-----------|------|-------------|
| `e2e_jra_smoke.py` | JRA: 1日分データ取得→パース→DB格納→SQLクエリ検証 | 2-5分 |
| `e2e_error_recovery.py` | エラーリカバリ（-502等）の動作確認 | 1-3分 |
| `e2e_edge_cases.py` | 異常レース検証（中止、取消、除外、少頭数、震災期間等） | 1分 |

## 実行手順

### 1. Windows 実機へ GUI セッションで接続

### 2. コマンドプロンプトを開く

```cmd
cd <jrvltsql checkout>
```

### 3. JRA スモークテスト実行

```cmd
py -3.12-32 tests\e2e\e2e_jra_smoke.py 2>&1 | tee data\e2e_jra_result.txt
```

公式SDK 5.0.0にはx64版もありますが、jrvltsqlの64-bit実行経路は未検証です。
x64をリリース対応済みとするには、別途実SDKでこのE2Eを完走する必要があります。

### 4. エラーリカバリテスト実行

```cmd
py -3.12-32 tests\e2e\e2e_error_recovery.py 2>&1 | tee data\e2e_error_result.txt
```

### 5. 異常レース・エッジケース検証（既存DB使用）

```cmd
py -3.12-32 tests\e2e\e2e_edge_cases.py 2>&1 | tee data\e2e_edge_result.txt
```

> **注意:** このテストは既存の `data/keiba.db` を **読み取り専用** で使用します。COM API は不要なので SSH からも実行可能です。

## 結果の確認

各スクリプトは終了時に `PASS` / `FAIL` を表示します。
詳細ログは `data/e2e_*.txt` に出力されます。

## 注意事項

- **SSH からは実行不可**（COM API は GUI コンテキストが必要）
- テスト用DBは `data/e2e_test.db` に作成され、テスト後に自動削除されます
- 既存の `data/keiba.db` には一切影響しません
- `-502` エラー（データ準備中）が出た場合、テストはスキップ扱いになります
