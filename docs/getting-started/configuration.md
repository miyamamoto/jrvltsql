# 設定ガイド

## 設定ファイル

設定はYAML形式で管理されます：

```
config/config.yaml
```

### 基本構造

```yaml
jvlink:
  sid: "JLTSQL"                    # セッションID
  service_key: "${JVLINK_SERVICE_KEY}"  # サービスキー（環境変数推奨）

database:
  type: sqlite                     # デフォルトDB (sqlite/postgresql)

databases:
  sqlite:
    path: "data/keiba.db"
    timeout: 30.0

  postgresql:
    host: "${POSTGRES_HOST:localhost}"
    port: 5432
    database: "keiba"
    user: "${POSTGRES_USER}"
    password: "${POSTGRES_PASSWORD}"

logging:
  level: INFO                      # DEBUG/INFO/WARNING/ERROR
  file: "logs/jltsql.log"
```

## 環境変数

機密情報は環境変数で管理することを推奨します。

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `JVLINK_SERVICE_KEY` | JRA-VANサービスキー | 必須 |
| `POSTGRES_HOST` | PostgreSQLホスト | PostgreSQL使用時 |
| `POSTGRES_USER` | PostgreSQLユーザー | PostgreSQL使用時 |
| `POSTGRES_PASSWORD` | PostgreSQLパスワード | PostgreSQL使用時 |

### 環境変数の設定

=== "Windows (PowerShell)"

    ```powershell
    # 一時的
    $env:JVLINK_SERVICE_KEY = "YOUR_KEY"

    # 永続的
    [System.Environment]::SetEnvironmentVariable("JVLINK_SERVICE_KEY", "YOUR_KEY", "User")
    ```

=== "Windows (コマンドプロンプト)"

    ```cmd
    set JVLINK_SERVICE_KEY=YOUR_KEY
    setx JVLINK_SERVICE_KEY "YOUR_KEY"
    ```

## データベース設定

### SQLite

```yaml
databases:
  sqlite:
    path: "data/keiba.db"
    timeout: 30.0
    check_same_thread: false
```

**自動最適化設定**:
- `PRAGMA journal_mode = WAL`
- `PRAGMA synchronous = NORMAL`
- `PRAGMA cache_size = -64000` (64MB)

### PostgreSQL

```yaml
databases:
  postgresql:
    host: localhost
    port: 5432
    database: keiba
    user: postgres
    password: "${POSTGRES_PASSWORD}"
    timeout: 30
```

## パフォーマンス設定

```yaml
performance:
  batch_size: 1000          # バッチサイズ
  commit_interval: 5000     # コミット間隔
  workers: 4                # ワーカー数
  memory_limit: "1GB"       # メモリ制限
```

!!! tip "推奨設定"
    - **初回インポート**: `batch_size: 5000`, `commit_interval: 10000`
    - **差分更新**: `batch_size: 1000`, `commit_interval: 1000`
    - **メモリ制限がある場合**: `batch_size: 500`

## ログ設定

```yaml
logging:
  level: INFO               # ログレベル
  file: "logs/jltsql.log"   # ログファイル
  console: true             # コンソール出力
  file_rotation:
    max_bytes: 104857600    # 100MB
    backup_count: 5
```

## 詳細設定

完全な設定オプションについては、[CONFIGURATION.md](https://github.com/miyamamoto/jrvltsql/blob/master/docs/CONFIGURATION.md)を参照してください。
