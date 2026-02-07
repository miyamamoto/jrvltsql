# 設定ガイド (Configuration Guide)

JLTSQL の設定方法と環境変数について説明します。

## 目次

1. [設定概要](#設定概要)
2. [環境変数](#環境変数)
3. [データベース設定](#データベース設定)
4. [パフォーマンス設定](#パフォーマンス設定)
5. [ログ設定](#ログ設定)
6. [設定例](#設定例)

---

## 設定概要

### 設定ファイルの場所

JLTSQL の設定は YAML 形式で管理されます。

```
config/config.yaml
```

初回セットアップ時には、サンプル設定ファイルをコピーして編集してください：

```bash
cp config/config.yaml.example config/config.yaml
```

### YAML 構造

設定ファイルは以下のセクションで構成されています：

- **jvlink**: JRA-VAN JV-Link の接続設定
- **database**: デフォルトのデータベースタイプ
- **databases**: 各データベースの詳細設定（SQLite, PostgreSQL）
- **data_fetch**: データ取得設定（初期取得・リアルタイム取得）
- **performance**: パフォーマンスチューニング設定
- **logging**: ログ出力設定
- **monitoring**: 監視・ヘルスチェック設定
- **advanced**: 高度な設定（リトライ、タイムアウト、エンコーディング）

### 環境変数の展開

設定ファイル内で `${VAR_NAME}` または `${VAR_NAME:デフォルト値}` の形式で環境変数を参照できます。

```yaml
service_key: "${JVLINK_SERVICE_KEY}"
host: "${POSTGRES_HOST:localhost}"
```

この機能により、機密情報（サービスキー、パスワード）を設定ファイルに直接記述せず、環境変数で管理できます。

---

## 環境変数

### 環境変数一覧

| 変数名 | 説明 | 必須 | デフォルト値 |
|--------|------|------|-------------|
| `JVLINK_SERVICE_KEY` | JRA-VAN サービスキー | 必須 | - |
| `POSTGRES_HOST` | PostgreSQL ホスト名 | PostgreSQL 使用時 | localhost |
| `POSTGRES_USER` | PostgreSQL ユーザー名 | PostgreSQL 使用時 | - |
| `POSTGRES_PASSWORD` | PostgreSQL パスワード | PostgreSQL 使用時 | - |
| `POSTGRES_DB` | PostgreSQL データベース名 | PostgreSQL 使用時 | keiba |
| `POSTGRES_PORT` | PostgreSQL ポート番号 | PostgreSQL 使用時 | 5432 |

### 環境変数の設定方法

#### Windows (PowerShell)

```powershell
# 一時的な設定（現在のセッションのみ）
$env:JVLINK_SERVICE_KEY = "YOUR_SERVICE_KEY_HERE"
$env:POSTGRES_PASSWORD = "your_password"

# 永続的な設定（ユーザー環境変数）
[System.Environment]::SetEnvironmentVariable("JVLINK_SERVICE_KEY", "YOUR_SERVICE_KEY_HERE", "User")
```

#### Windows (コマンドプロンプト)

```cmd
rem 一時的な設定
set JVLINK_SERVICE_KEY=YOUR_SERVICE_KEY_HERE
set POSTGRES_PASSWORD=your_password

rem 永続的な設定
setx JVLINK_SERVICE_KEY "YOUR_SERVICE_KEY_HERE"
```

#### Linux/macOS

```bash
# 一時的な設定（現在のセッションのみ）
export JVLINK_SERVICE_KEY="YOUR_SERVICE_KEY_HERE"
export POSTGRES_PASSWORD="your_password"

# 永続的な設定（~/.bashrc または ~/.zshrc に追記）
echo 'export JVLINK_SERVICE_KEY="YOUR_SERVICE_KEY_HERE"' >> ~/.bashrc
source ~/.bashrc
```

#### .env ファイルの使用

プロジェクトルートに `.env` ファイルを作成して環境変数を管理することも可能です：

```bash
# .env
JVLINK_SERVICE_KEY=YOUR_SERVICE_KEY_HERE
POSTGRES_HOST=localhost
POSTGRES_USER=keiba_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=keiba
POSTGRES_PORT=5432
```

**注意**: `.env` ファイルには機密情報が含まれるため、Git にコミットしないでください（`.gitignore` に追加）。

---

## データベース設定

### データベースタイプの選択

`database.type` でデフォルトのデータベースを指定します：

```yaml
database:
  type: "sqlite"  # sqlite, postgresql のいずれか
```

### SQLite 設定（シングルユーザー推奨）

SQLite はセットアップが簡単で、小～中規模のデータに適しています。

```yaml
databases:
  sqlite:
    enabled: true
    path: "./data/keiba.db"
    pragma:
      journal_mode: "WAL"      # Write-Ahead Logging（並行読み取り性能向上）
      synchronous: "NORMAL"     # 安全性と性能のバランス
      cache_size: -64000        # キャッシュサイズ（負の値は KB 単位、この例は 64MB）
      temp_store: "MEMORY"      # 一時データをメモリに保存
```

#### PRAGMA オプション

- **journal_mode**: ジャーナルモード
  - `DELETE`: デフォルト（トランザクション後にジャーナル削除）
  - `WAL`: Write-Ahead Logging（推奨、並行読み取り可能）
  - `TRUNCATE`, `PERSIST`, `MEMORY`, `OFF`

- **synchronous**: 同期モード
  - `FULL`: 最も安全だが低速
  - `NORMAL`: 推奨（ほとんどの場合で安全）
  - `OFF`: 最も高速だがクラッシュ時にデータ損失リスク

- **cache_size**: ページキャッシュサイズ
  - 正の値: ページ数
  - 負の値: キロバイト単位（例: -64000 = 64MB）

- **temp_store**: 一時データの保存場所
  - `MEMORY`: メモリに保存（高速）
  - `FILE`: ディスクに保存（メモリ節約）

### PostgreSQL 設定（マルチユーザー・サーバー環境推奨）

複数ユーザーでの同時アクセスや大規模データに適しています。

```yaml
databases:
  postgresql:
    enabled: true
    host: "${POSTGRES_HOST:localhost}"
    port: 5432
    database: "keiba"
    user: "${POSTGRES_USER}"
    password: "${POSTGRES_PASSWORD}"
    pool_size: 5              # コネクションプールサイズ
    max_overflow: 10          # プールを超えた場合の最大接続数
```

#### パラメータ説明

- **host**: PostgreSQL サーバーのホスト名または IP アドレス
- **port**: ポート番号（デフォルト: 5432）
- **database**: データベース名
- **user**: 接続ユーザー名
- **password**: パスワード
- **pool_size**: 通常時の接続プールサイズ（推奨: 5～10）
- **max_overflow**: プール不足時に追加で作成できる接続数（推奨: pool_size の 2 倍程度）

#### PostgreSQL の事前準備

データベースとユーザーを作成しておく必要があります：

```sql
-- データベース作成
CREATE DATABASE keiba ENCODING 'UTF8';

-- ユーザー作成と権限付与
CREATE USER keiba_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE keiba TO keiba_user;
```

---

## データ取得設定

### 初期一括取得設定

過去データの一括取得設定です。

```yaml
data_fetch:
  initial:
    enabled: true
    date_from: "2020-01-01"
    date_to: "2024-12-31"
    data_specs:
      - "RACE"      # レースデータ（RA, SE, HR）
      - "DIFF"      # マスターデータ（UM, KS, CH, BR, BN）
      - "YSCH"      # 開催スケジュール
      - "O1"        # 単勝・複勝・枠連オッズ
      - "O2"        # 馬連オッズ
      - "O3"        # ワイドオッズ
      - "O4"        # 馬単オッズ
      - "O5"        # 三連複オッズ
      - "O6"        # 三連単オッズ
```

#### データ種別コード（data_specs）

- **RACE**: レース情報（RA: レース詳細、SE: 馬情報、HR: 払戻金）
- **DIFF**: マスターデータ（UM: 馬マスター、KS: 騎手、CH: 調教師、BR: 繁殖馬、BN: 生産者）
- **YSCH**: 開催スケジュール
- **O1～O6**: オッズ情報（各種賭式）

### リアルタイム取得設定

レース当日のリアルタイムデータ更新設定です。

```yaml
data_fetch:
  realtime:
    enabled: true
    interval_seconds: 60      # 更新間隔（秒）
    data_specs:
      - "0B12"      # レース結果
      - "0B15"      # 馬体重
      - "0B20"      # オッズ更新
      - "0B31"      # 払戻金
```

---

## パフォーマンス設定

データ取得・処理のパフォーマンスを調整できます。

```yaml
performance:
  batch_size: 1000            # バッチ挿入サイズ
  commit_interval: 10000      # コミット間隔（レコード数）
  max_workers: 4              # 並列処理ワーカー数
  prefetch_size: 100          # プリフェッチバッファサイズ
  memory_limit_mb: 500        # バッファリングメモリ上限（MB）
```

### パラメータ調整ガイド

| パラメータ | 推奨値 | 説明 |
|-----------|--------|------|
| `batch_size` | 500～2000 | 大きいほど高速だが、メモリ使用量増加 |
| `commit_interval` | 5000～20000 | トランザクションのコミット頻度（大きいほど高速） |
| `max_workers` | 2～8 | CPU コア数に応じて調整（通常は 4 で十分） |
| `prefetch_size` | 50～200 | データ取得の先読みバッファ |
| `memory_limit_mb` | 256～1024 | メモリ制約がある場合は小さく設定 |

**パフォーマンス向上のヒント**:
- SSD を使用している場合は `batch_size` と `commit_interval` を大きくすると効果的
- メモリに余裕がある場合は `memory_limit_mb` を 1GB 以上に設定
- CPU コアが 8 個以上ある場合は `max_workers` を 6～8 に増やすと高速化

---

## ログ設定

ログ出力のレベルと出力先を設定します。

```yaml
logging:
  level: "INFO"               # ログレベル
  file:
    enabled: true
    path: "./logs/jltsql.log"
    max_size_mb: 100          # ローテーションサイズ
    backup_count: 5           # バックアップ世代数
    rotation: "size"          # size または time
  console:
    enabled: true
    colored: true             # カラー出力（対応端末のみ）
  format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
```

### ログレベル

| レベル | 説明 | 用途 |
|--------|------|------|
| `DEBUG` | 詳細なデバッグ情報 | 開発・トラブルシューティング |
| `INFO` | 一般的な情報メッセージ | 通常運用（推奨） |
| `WARNING` | 警告メッセージ | 重要な運用情報のみ |
| `ERROR` | エラーメッセージ | エラーのみ記録 |
| `CRITICAL` | 致命的なエラー | 最小限のログ |

### ローテーション設定

- **rotation: "size"**: ファイルサイズでローテーション
  - `max_size_mb` に達したら新ファイル作成
  - `backup_count` 世代分を保持

- **rotation: "time"**: 時間ベースでローテーション
  - 日次、週次などでローテーション（実装による）

---

## 監視・高度な設定

### 監視設定

```yaml
monitoring:
  metrics_enabled: false      # メトリクス収集（将来の機能）
  health_check_port: 8080     # ヘルスチェック用ポート
```

### リトライ設定

ネットワークエラーやデータベース接続エラー時の再試行設定です。

```yaml
advanced:
  retry:
    max_attempts: 3           # 最大試行回数
    backoff_factor: 2         # 待機時間の倍率（指数バックオフ）
    max_wait_seconds: 60      # 最大待機時間
```

指数バックオフの動作例（backoff_factor: 2）:
- 1 回目: 即座にリトライ
- 2 回目: 2 秒待機
- 3 回目: 4 秒待機
- 4 回目: 8 秒待機

### タイムアウト設定

各種操作のタイムアウト時間（秒）です。

```yaml
advanced:
  timeout:
    jvlink_connect: 30        # JV-Link 接続タイムアウト
    jvlink_read: 10           # JV-Link データ読み取りタイムアウト
    db_connect: 10            # データベース接続タイムアウト
    db_query: 300             # データベースクエリタイムアウト
```

### エンコーディング設定

```yaml
advanced:
  encoding:
    jvdata: "cp932"           # JV-Data のエンコーディング（固定）
    database: "utf-8"         # データベースのエンコーディング
```

**注意**: `jvdata` は JRA-VAN データ仕様に基づき `cp932`（Shift-JIS）固定です。変更しないでください。

---

## 設定例

### 例 1: 最小構成（SQLite、ローカル開発）

シンプルで手軽なセットアップ。個人利用や開発環境に最適です。

```yaml
# config/config.yaml
jvlink:
  service_key: "${JVLINK_SERVICE_KEY}"

database:
  type: "sqlite"

databases:
  sqlite:
    enabled: true
    path: "./data/keiba.db"
    pragma:
      journal_mode: "WAL"
      synchronous: "NORMAL"

data_fetch:
  initial:
    enabled: true
    date_from: "2023-01-01"
    date_to: "2024-12-31"
    data_specs:
      - "RACE"
      - "DIFF"

  realtime:
    enabled: false

performance:
  batch_size: 1000
  max_workers: 2

logging:
  level: "INFO"
  file:
    enabled: true
    path: "./logs/jltsql.log"
  console:
    enabled: true
```

環境変数設定（PowerShell）:

```powershell
$env:JVLINK_SERVICE_KEY = "YOUR_SERVICE_KEY_HERE"
```

---

### 例 2: PostgreSQL（本番環境・マルチユーザー）

複数ユーザーでの同時アクセスやサーバー環境に適しています。

```yaml
# config/config.yaml
jvlink:
  service_key: "${JVLINK_SERVICE_KEY}"

database:
  type: "postgresql"

databases:
  postgresql:
    enabled: true
    host: "${POSTGRES_HOST:localhost}"
    port: 5432
    database: "keiba"
    user: "${POSTGRES_USER}"
    password: "${POSTGRES_PASSWORD}"
    pool_size: 10             # 同時接続ユーザー数に応じて調整
    max_overflow: 20

data_fetch:
  initial:
    enabled: true
    date_from: "2020-01-01"
    date_to: "2024-12-31"
    data_specs:
      - "RACE"
      - "DIFF"
      - "YSCH"
      - "O1"
      - "O2"
      - "O3"
      - "O4"
      - "O5"
      - "O6"

  realtime:
    enabled: true
    interval_seconds: 30      # 本番環境では短めに設定
    data_specs:
      - "0B12"
      - "0B15"
      - "0B20"
      - "0B31"

performance:
  batch_size: 1500
  commit_interval: 15000
  max_workers: 8
  prefetch_size: 150
  memory_limit_mb: 1024

logging:
  level: "INFO"
  file:
    enabled: true
    path: "/var/log/jltsql/jltsql.log"
    max_size_mb: 100
    backup_count: 10
    rotation: "size"
  console:
    enabled: true
    colored: false            # サーバー環境ではカラー無効

monitoring:
  metrics_enabled: true
  health_check_port: 8080

advanced:
  retry:
    max_attempts: 5           # 本番環境では多めに設定
    backoff_factor: 2
    max_wait_seconds: 120
  timeout:
    jvlink_connect: 60
    jvlink_read: 30
    db_connect: 15
    db_query: 600
```

環境変数設定（Linux サーバー、/etc/environment または systemd の EnvironmentFile）:

```bash
JVLINK_SERVICE_KEY=YOUR_SERVICE_KEY_HERE
POSTGRES_HOST=db.example.com
POSTGRES_USER=keiba_app
POSTGRES_PASSWORD=secure_password_here
```

PostgreSQL データベース準備:

```sql
CREATE DATABASE keiba ENCODING 'UTF8' LC_COLLATE 'ja_JP.UTF-8' LC_CTYPE 'ja_JP.UTF-8';
CREATE USER keiba_app WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE keiba TO keiba_app;

-- 接続後、スキーマ権限も付与
\c keiba
GRANT ALL PRIVILEGES ON SCHEMA public TO keiba_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO keiba_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO keiba_app;
```

---

## トラブルシューティング

### 設定ファイルが読み込めない

**エラー**: `Configuration file not found: config/config.yaml`

**解決方法**:
```bash
# サンプル設定をコピー
cp config/config.yaml.example config/config.yaml
```

### 環境変数が展開されない

**エラー**: `Invalid JV-Link service key` または空の値

**解決方法**:
1. 環境変数が正しく設定されているか確認
   ```powershell
   # Windows PowerShell
   echo $env:JVLINK_SERVICE_KEY
   ```
   ```bash
   # Linux/macOS
   echo $JVLINK_SERVICE_KEY
   ```

2. 環境変数を設定し直す
   ```powershell
   $env:JVLINK_SERVICE_KEY = "YOUR_SERVICE_KEY_HERE"
   ```

3. アプリケーションを再起動

### データベース接続エラー

**PostgreSQL の場合**:
```
FATAL: database "keiba" does not exist
```

**解決方法**: データベースを作成してください
```sql
CREATE DATABASE keiba ENCODING 'UTF8';
```

**SQLite の場合**:
```
unable to open database file
```

**解決方法**: data ディレクトリを作成してください
```bash
mkdir data
```

### パフォーマンスが遅い

**確認項目**:
1. `batch_size` を大きくする（1000 → 2000）
2. `commit_interval` を大きくする（10000 → 20000）
3. SQLite の場合は `journal_mode: "WAL"` を使用
4. `max_workers` を CPU コア数に合わせて調整
5. SSD を使用しているか確認

---

## 参考資料

- [JRA-VAN データラボ](https://jra-van.jp/dlb/)
- [SQLite PRAGMA 文](https://www.sqlite.org/pragma.html)
- [PostgreSQL 公式ドキュメント](https://www.postgresql.org/docs/)

---

## サポート

問題が解決しない場合は、以下の情報を含めて Issue を作成してください：

1. 使用している OS とバージョン
2. Python のバージョン
3. `config/config.yaml` の内容（パスワードは削除）
4. エラーメッセージ全文
5. `logs/jltsql.log` の該当部分

---

最終更新: 2024-12-06
