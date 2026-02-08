# データベース選択ガイド

JRVLTSQLは**SQLite**データベースを使用します。32-bit Python環境での安定動作を重視した設計です。

## 重要なお知らせ

**32-bit Python対応のため、SQLiteのみをサポートしています。**

地方競馬DATA (UmaConn) APIは32-bit COM DLLとして提供されており、32-bit Python環境が必須です。そのため、以下のデータベースは非対応または制限があります：

- **PostgreSQL**: psycopgライブラリが64-bit環境を推奨（JRA-VANのみの場合は利用可能）

## SQLite の特徴

| 項目 | 内容 |
|------|------|
| **用途** | すべての用途（開発・分析・運用） |
| **セットアップ** | 不要（Python標準ライブラリ） |
| **ファイル** | 単一の.dbファイル |
| **同時接続** | 単一プロセス |
| **分析クエリ** | 高速（適切なインデックス設定で） |
| **書き込み** | 高速 |
| **メモリ使用** | 少（軽量） |
| **32-bit対応** | 完全対応 |

## SQLiteの詳細

### 特徴

- **ファイルベース**: 単一の`.db`ファイルで管理
- **セットアップ不要**: Pythonに標準搭載（追加インストール不要）
- **軽量**: メモリ使用量が少なく、高速動作
- **ポータブル**: ファイルをコピーするだけでバックアップ・移行可能
- **32-bit完全対応**: 32-bit Python環境で安定動作
- **大規模データ対応**: 適切なインデックス設定で数十GB以上も処理可能

### 推奨用途

- **すべての用途**: 開発・テスト・本番運用
- JRA-VAN (JV-Link) データ取得
- 地方競馬DATA (UmaConn) データ取得
- データ分析（適切なインデックス設定で高速化）
- 個人利用・共有利用

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
# デフォルトはSQLite
jltsql fetch --from 20240101 --to 20241231 --spec RACE

# 明示的に指定する場合
jltsql fetch --from 20240101 --to 20241231 --spec RACE --db sqlite
```

### パフォーマンス最適化

SQLiteでも以下の設定で高速な分析クエリが可能です：

```sql
-- インデックスの作成
CREATE INDEX idx_nl_ra_year ON NL_RA(Year);
CREATE INDEX idx_nl_se_kakutei ON NL_SE(KakuteiJyuni);
CREATE INDEX idx_nl_se_kisyu ON NL_SE(KisyuCode);

-- プラグマ設定（高速化）
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;  -- 64MBキャッシュ
PRAGMA temp_store = MEMORY;
```

## 分析クエリ例

SQLiteでも高速な分析クエリが可能です：

```sql
-- 年別レース数
SELECT Year, COUNT(*) as race_count
FROM NL_RA
GROUP BY Year
ORDER BY Year;

-- 騎手別勝率（インデックス使用で高速化）
SELECT
    k.KisyuName,
    COUNT(*) as rides,
    SUM(CASE WHEN s.KakuteiJyuni = 1 THEN 1 ELSE 0 END) as wins,
    ROUND(CAST(SUM(CASE WHEN s.KakuteiJyuni = 1 THEN 1 ELSE 0 END) AS REAL) * 100.0 / COUNT(*), 2) as win_rate
FROM NL_SE s
JOIN NL_KS k ON s.KisyuCode = k.KisyuCode
WHERE s.Year = 2024
GROUP BY k.KisyuCode, k.KisyuName
ORDER BY wins DESC
LIMIT 20;

-- 競馬場別レース数
SELECT
    ba.JyoCode,
    ba.JyoName,
    COUNT(*) as race_count
FROM NL_RA ra
JOIN NL_BA ba ON ra.JyoCode = ba.JyoCode
WHERE ra.Year = 2024
GROUP BY ba.JyoCode, ba.JyoName
ORDER BY race_count DESC;
```

## バックアップとリストア

SQLiteはファイルベースなので、バックアップが非常に簡単です：

```bash
# バックアップ（ファイルコピー）
copy data\keiba.db data\keiba_backup_20240101.db

# リストア（ファイル復元）
copy data\keiba_backup_20240101.db data\keiba.db

# 別環境への移行
# keiba.db ファイルをコピーするだけ
```

## NARテーブル（地方競馬）

NAR（地方競馬）データはJRAテーブルと同じスキーマ構造で、テーブル名に `_NAR` サフィックスが付きます。

| JRAテーブル | NARテーブル | 説明 |
|------------|-----------|------|
| NL_RA | NL_RA_NAR | レース詳細 |
| NL_SE | NL_SE_NAR | 馬毎レース情報 |
| NL_HR | NL_HR_NAR | 払戻情報 |
| NL_UM | NL_UM_NAR | 馬マスタ |
| RT_RA | RT_RA_NAR | レース情報（速報） |
| ... | ..._NAR | 全テーブルに対応 |

NARテーブルは `create_all_nar_tables(db)` で一括作成できます：

```python
from src.database.schema_nar import create_all_nar_tables

with db:
    create_all_nar_tables(db)
```

`jltsql create-tables` コマンドでもJRA・NARテーブルが一括作成されます。

## よくある質問

### Q: PostgreSQLは使えますか？

A: 64-bit Python環境が推奨されるため、現在は限定的なサポートです。JRA-VANのみを使用する場合は、64-bit Python + PostgreSQLの組み合わせが可能ですが、地方競馬DATAとの併用はできません。

### Q: SQLiteで大規模データは扱えますか？

A: はい、適切なインデックス設定とプラグマ設定により、数十GB以上のデータも高速に処理できます。JRVLTSQLは最適化されたスキーマとインデックスを自動作成します。
