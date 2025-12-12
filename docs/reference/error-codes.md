# エラーコード

JRVLTSQLで発生するエラーとその対処法について説明します。

## JV-Linkエラーコード

### 接続・オープン関連

| コード | 説明 | 対処法 |
|--------|------|--------|
| 0 | 成功 | - |
| -1 | データなし | 指定した期間にデータがありません |
| -100 | サービスキー未設定 | DataLabでサービスキーを設定 |
| -101 | サービスキー無効 | サービスキーを確認 |
| -102 | サービスキー期限切れ | 会員契約を更新 |
| -111 | 未契約データ | 該当データの契約が必要 |
| -201 | JV-Link初期化失敗 | DataLabを再インストール |
| -202 | JV-Link接続失敗 | PCを再起動 |
| -203 | サーバー接続失敗 | ネットワークを確認 |

### 読み取り関連

| コード | 説明 | 対処法 |
|--------|------|--------|
| -1 | ストリーム終了 | 正常終了 |
| -2 | 読み取りエラー | 再試行 |
| -3 | ファイルなし | 指定ファイルが存在しない |
| -302 | ダウンロード待機中 | しばらく待って再試行 |
| -303 | ダウンロード中 | ダウンロード完了まで待機 |
| -402 | ファイル読み取りエラー | ファイルを確認 |
| -403 | 内部エラー | DataLabを再起動 |

## データベースエラー

### SQLite

| エラー | 説明 | 対処法 |
|--------|------|--------|
| `database is locked` | 他のプロセスがロック中 | 他のプロセスを終了 |
| `disk I/O error` | ディスクエラー | ディスク空き容量を確認 |
| `no such table` | テーブルなし | `jltsql create-tables`を実行 |
| `UNIQUE constraint failed` | 重複キー | 通常はINSERT OR REPLACEで解決 |

### DuckDB

| エラー | 説明 | 対処法 |
|--------|------|--------|
| `Out of Memory` | メモリ不足 | `memory_limit`を調整 |
| `Connection refused` | 接続拒否 | ファイルのロックを確認 |
| `IO Error` | I/Oエラー | ディスクを確認 |

### PostgreSQL

| エラー | 説明 | 対処法 |
|--------|------|--------|
| `connection refused` | 接続拒否 | PostgreSQLサーバーを確認 |
| `authentication failed` | 認証失敗 | ユーザー名/パスワードを確認 |
| `database does not exist` | DBなし | `createdb`でDB作成 |
| `permission denied` | 権限なし | 権限を確認 |

## アプリケーションエラー

### 設定関連

| エラー | 説明 | 対処法 |
|--------|------|--------|
| `ConfigError: File not found` | 設定ファイルなし | `jltsql init`を実行 |
| `ConfigError: Invalid YAML` | YAML構文エラー | YAMLを修正 |
| `ConfigError: Missing required` | 必須項目なし | 設定を追加 |

### インポート関連

| エラー | 説明 | 対処法 |
|--------|------|--------|
| `ImportError: No parser` | パーサーなし | レコードタイプを確認 |
| `ImportError: Type conversion` | 型変換エラー | データを確認 |
| `ImportError: Batch failed` | バッチ失敗 | ログを確認 |

## トラブルシューティング

### JV-Link接続できない

```
JVLinkError: Failed to initialize JV-Link
```

**対処法**:
1. JRA-VAN DataLabがインストールされているか確認
2. DataLabソフトウェアを一度起動
3. PCを再起動

### サービスキーエラー

```
JVLinkError: Service key not set (-100)
```

**対処法**:
1. DataLabソフトウェアを起動
2. メニューから「設定」→「サービスキー設定」
3. 有効なサービスキーを入力

### データベースロック

```
DatabaseError: database is locked
```

**対処法**:
1. 他のプロセスを終了
2. `.db-wal`ファイルを確認
3. タイムアウトを延長

```yaml
databases:
  sqlite:
    timeout: 60.0  # 30秒から延長
```

### メモリ不足

```
MemoryError: Unable to allocate
```

**対処法**:
1. バッチサイズを小さくする

```bash
jltsql fetch --batch-size 200
```

2. DuckDBのメモリ制限

```yaml
databases:
  duckdb:
    memory_limit: "1GB"
```

### ネットワークエラー

```
JVLinkError: Server connection failed (-203)
```

**対処法**:
1. インターネット接続を確認
2. ファイアウォール設定を確認
3. しばらく待って再試行

## ログの確認

詳細なエラー情報はログファイルで確認できます：

```bash
# 最新のログを表示
tail -f logs/jltsql.log

# エラーのみ抽出
grep ERROR logs/jltsql.log
```

DEBUGログを有効にする：

```bash
jltsql fetch --from 20240101 --to 20241231 --spec RACE -v
```
