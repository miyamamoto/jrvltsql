# データベース選択ガイド

JRVLTSQLは3種類のデータベースに対応しています。用途に応じて最適なものを選択してください。

## 比較表

| 特徴 | SQLite | DuckDB | PostgreSQL |
|------|--------|--------|------------|
| **用途** | 開発・軽量運用 | 分析・OLAP | 本番運用 |
| **セットアップ** | 不要 | 不要 | サーバー必要 |
| **ファイル** | 単一ファイル | 単一ファイル | サーバー管理 |
| **同時接続** | 単一 | 単一 | 複数 |
| **分析クエリ** | 普通 | 高速 | 普通 |
| **書き込み** | 高速 | 普通 | 高速 |
| **メモリ使用** | 少 | 中〜多 | 設定次第 |

## SQLite

### 特徴

- **ファイルベース**: 単一の`.db`ファイルで管理
- **セットアップ不要**: Pythonに標準搭載
- **軽量**: 小〜中規模データに最適
- **ポータブル**: ファイルをコピーするだけでバックアップ

### 推奨用途

- 開発・テスト環境
- 個人利用
- 小規模データ（〜数GB）
- バックアップが容易

### 設定例

```yaml
database:
  type: sqlite

databases:
  sqlite:
    path: "data/keiba.db"
    timeout: 30.0
```

### 使用方法

```bash
jltsql fetch --from 20240101 --to 20241231 --spec RACE --db sqlite
```

## DuckDB

### 特徴

- **列指向ストレージ**: 分析クエリに最適化
- **並列処理**: マルチスレッド対応
- **メモリ効率**: 大規模データでも高速
- **SQLite互換**: 移行が容易

### 推奨用途

- データ分析
- 集計・統計処理
- 大規模データ（数十GB以上）
- Jupyter Notebook連携

### 設定例

```yaml
database:
  type: duckdb

databases:
  duckdb:
    path: "data/keiba.duckdb"
    memory_limit: "4GB"
    threads: 8
```

### 使用方法

```bash
jltsql fetch --from 20240101 --to 20241231 --spec RACE --db duckdb
```

### 分析クエリ例

```sql
-- 年別レース数（DuckDBで高速）
SELECT Year, COUNT(*) as race_count
FROM NL_RA
GROUP BY Year
ORDER BY Year;

-- 騎手別勝率
SELECT
    k.KisyuName,
    COUNT(*) as rides,
    SUM(CASE WHEN s.KakuteiJyuni = 1 THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(CASE WHEN s.KakuteiJyuni = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate
FROM NL_SE s
JOIN NL_KS k ON s.KisyuCode = k.KisyuCode
WHERE s.Year = 2024
GROUP BY k.KisyuCode, k.KisyuName
ORDER BY wins DESC
LIMIT 20;
```

## PostgreSQL

### 特徴

- **マルチユーザー**: 複数同時接続対応
- **高信頼性**: ACID完全準拠
- **豊富な機能**: 全文検索、JSON対応
- **スケーラブル**: 大規模運用に対応

### 推奨用途

- 本番環境
- Webアプリケーション連携
- 複数ユーザーでの共有
- 高可用性が必要な場合

### 設定例

```yaml
database:
  type: postgresql

databases:
  postgresql:
    host: localhost
    port: 5432
    database: keiba
    user: postgres
    password: "${POSTGRES_PASSWORD}"
```

### セットアップ

```bash
# PostgreSQLのインストール（Windows）
# https://www.postgresql.org/download/windows/

# データベース作成
createdb keiba

# テーブル作成
jltsql create-tables --db postgresql
```

## 選択のポイント

### 個人利用・開発

→ **SQLite**を推奨

- セットアップ不要
- ファイル管理が簡単
- 十分な性能

### データ分析メイン

→ **DuckDB**を推奨

- 集計クエリが高速
- Pandas/Jupyter連携
- メモリ内処理

### 本番運用・共有

→ **PostgreSQL**を推奨

- 複数接続対応
- 高信頼性
- バックアップ・レプリケーション

## データベース間の移行

SQLite → DuckDB/PostgreSQLへの移行は、エクスポート/インポートで行えます：

```bash
# SQLiteからエクスポート
jltsql export --table NL_RA --output races.parquet --format parquet --db sqlite

# DuckDBにインポート（DuckDB CLIで）
duckdb data/keiba.duckdb "CREATE TABLE NL_RA AS SELECT * FROM 'races.parquet'"
```
