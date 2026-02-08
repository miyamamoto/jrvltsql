# 設定ガイド

## 設定ファイル

設定はYAML形式で管理されます：

```
config/config.yaml
```

### 基本構造

```yaml
# JV-Link (中央競馬) 設定
jvlink:
  service_key: "${JVLINK_SERVICE_KEY}"  # サービスキー（環境変数推奨）

# NV-Link (地方競馬DATA) 設定
nvlink:
  service_key: "${NVLINK_SERVICE_KEY}"  # サービスキー（環境変数推奨）
  initialization_key: "UNKNOWN"         # 必ず "UNKNOWN" を設定（変更すると-301エラー）

# データベース設定
database:
  type: sqlite                          # sqlite または postgresql

databases:
  sqlite:
    enabled: true
    path: "./data/keiba.db"

  postgresql:
    enabled: false
    host: "${POSTGRES_HOST:localhost}"
    port: 5432
    database: "keiba"
    user: "${POSTGRES_USER}"
    password: "${POSTGRES_PASSWORD}"

logging:
  level: INFO
  file:
    enabled: true
    path: "./logs/jltsql.log"
```

## 環境変数

機密情報は環境変数で管理することを推奨します。

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `JVLINK_SERVICE_KEY` | JRA-VANサービスキー | JRA利用時 |
| `NVLINK_SERVICE_KEY` | 地方競馬DATAサービスキー | NAR利用時 |
| `POSTGRES_HOST` | PostgreSQLホスト | PostgreSQL使用時 |
| `POSTGRES_USER` | PostgreSQLユーザー | PostgreSQL使用時 |
| `POSTGRES_PASSWORD` | PostgreSQLパスワード | PostgreSQL使用時 |

### 環境変数の設定

=== "Windows (PowerShell)"

    ```powershell
    # 一時的
    $env:JVLINK_SERVICE_KEY = "YOUR_KEY"
    $env:NVLINK_SERVICE_KEY = "YOUR_KEY"

    # 永続的
    [System.Environment]::SetEnvironmentVariable("JVLINK_SERVICE_KEY", "YOUR_KEY", "User")
    [System.Environment]::SetEnvironmentVariable("NVLINK_SERVICE_KEY", "YOUR_KEY", "User")
    ```

=== "Windows (コマンドプロンプト)"

    ```cmd
    set JVLINK_SERVICE_KEY=YOUR_KEY
    setx JVLINK_SERVICE_KEY "YOUR_KEY"
    set NVLINK_SERVICE_KEY=YOUR_KEY
    setx NVLINK_SERVICE_KEY "YOUR_KEY"
    ```

## JV-Link 設定

```yaml
jvlink:
  service_key: "${JVLINK_SERVICE_KEY}"
```

JRA-VAN DataLabのサービスキーを設定します。JV-Link COM APIを通じて中央競馬データを取得します。

## NV-Link 設定

```yaml
nvlink:
  service_key: "${NVLINK_SERVICE_KEY}"
  initialization_key: "UNKNOWN"
```

- **service_key**: 地方競馬DATAのサービスキー
- **initialization_key**: NVInit で使用するソフトウェアID。**必ず `"UNKNOWN"` を設定してください**。他の値を設定すると -301 認証エラーが発生します
- **ProgID**: `NVDTLabLib.NVLink`（コード内で自動使用。フォールバックとして `NVDTLab.NVLink` も試行）

## データベース設定

### SQLite（デフォルト）

```yaml
database:
  type: sqlite

databases:
  sqlite:
    enabled: true
    path: "./data/keiba.db"
    pragma:
      journal_mode: "WAL"
      synchronous: "NORMAL"
      cache_size: -64000    # 64MB
      temp_store: "MEMORY"
```

追加インストール不要。Python標準の`sqlite3`モジュールを使用します。

### PostgreSQL

```yaml
database:
  type: postgresql

databases:
  postgresql:
    enabled: true
    host: localhost
    port: 5432
    database: keiba
    user: postgres
    password: "${POSTGRES_PASSWORD}"
    pool_size: 5
    max_overflow: 10
```

マルチユーザー環境やサーバーデプロイ向けです。

## データ取得設定

```yaml
data_fetch:
  initial:
    enabled: true
    date_from: "2020-01-01"
    date_to: "2024-12-31"
    data_specs:
      - "RACE"    # レースデータ (RA, SE, HR)
      - "DIFF"    # マスターデータ (UM, KS, CH, BR, BN)
      - "YSCH"    # スケジュール
      - "O1"      # 単勝・複勝・枠連オッズ
      - "O2"      # 馬連オッズ
      - "O3"      # ワイドオッズ
      - "O4"      # 馬単オッズ
      - "O5"      # 三連複オッズ
      - "O6"      # 三連単オッズ

  realtime:
    enabled: true
    interval_seconds: 60
```

## パフォーマンス設定

```yaml
performance:
  batch_size: 1000            # バッチサイズ
  commit_interval: 10000      # コミット間隔
  max_workers: 4              # ワーカー数
  memory_limit_mb: 500        # メモリ制限(MB)
```

!!! tip "推奨設定"
    - **初回インポート**: `batch_size: 5000`, `commit_interval: 10000`
    - **差分更新**: `batch_size: 1000`, `commit_interval: 1000`
    - **メモリ制限がある場合**: `batch_size: 500`

## ログ設定

```yaml
logging:
  level: INFO
  file:
    enabled: true
    path: "./logs/jltsql.log"
    max_size_mb: 100
    backup_count: 5
  console:
    enabled: true
    colored: true
```

## 詳細設定

完全な設定オプションについては、[config/config.yaml](https://github.com/miyamamoto/jrvltsql/blob/master/config/config.yaml)を参照してください。
