# データベースハンドラAPI仕様書

JRVLTSQLプロジェクトのデータベースハンドラAPIリファレンス

## 目次

1. [概要](#概要)
2. [BaseDatabase 抽象クラス](#basedatabase-抽象クラス)
3. [データベース実装](#データベース実装)
4. [スキーマ概要](#スキーマ概要)
5. [エラーハンドリング](#エラーハンドリング)

---

## 概要

JRVLTSQLは、JV-Data（JRA-VAN競馬データ）をSQLite、DuckDB、PostgreSQLに格納・管理するためのデータベースハンドラを提供します。

### サポートデータベース

- **SQLite**: 軽量、ファイルベース、組み込みデータベース
- **DuckDB**: 分析処理に特化したOLAPデータベース
- **PostgreSQL**: 本格的なリレーショナルデータベース（将来対応予定）

### 主な機能

- 統一されたデータベースAPI（BaseDatabase抽象クラス）
- UPSERT機能による重複データの自動更新
- データベース固有の最適化
- トランザクション管理
- コンテキストマネージャー対応

---

## BaseDatabase 抽象クラス

### クラス定義

```python
from src.database.base import BaseDatabase, DatabaseError

class BaseDatabase(ABC):
    """すべてのデータベース実装の基底クラス"""
```

### 初期化

```python
def __init__(self, config: Dict[str, Any])
```

**パラメータ:**
- `config` (Dict[str, Any]): データベース設定辞書

**例:**
```python
# SQLiteの場合
config = {
    "path": "./data/keiba.db",
    "timeout": 30.0,
    "check_same_thread": False
}
db = SQLiteDatabase(config)

# DuckDBの場合
config = {
    "path": "./data/keiba.duckdb",
    "read_only": False,
    "memory_limit": "2GB",
    "threads": 4
}
db = DuckDBDatabase(config)
```

---

### 接続管理

#### connect()

データベースへの接続を確立します。

```python
def connect(self) -> None
```

**例外:**
- `DatabaseError`: 接続に失敗した場合

**例:**
```python
db = SQLiteDatabase(config)
db.connect()
```

#### disconnect()

データベース接続を切断します。

```python
def disconnect(self) -> None
```

**例:**
```python
db.disconnect()
```

#### is_connected()

接続状態を確認します。

```python
def is_connected(self) -> bool
```

**戻り値:**
- `bool`: 接続中の場合True

**例:**
```python
if db.is_connected():
    print("データベースに接続中")
```

---

### SQL実行

#### execute()

SQL文を実行します。

```python
def execute(self, sql: str, parameters: Optional[tuple] = None) -> int
```

**パラメータ:**
- `sql` (str): 実行するSQL文
- `parameters` (Optional[tuple]): パラメータ化クエリの値

**戻り値:**
- `int`: 影響を受けた行数

**例外:**
- `DatabaseError`: 実行に失敗した場合

**例:**
```python
# テーブル作成
db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")

# パラメータ化クエリ
db.execute("INSERT INTO test (id, name) VALUES (?, ?)", (1, "テスト"))

# 更新
rows_affected = db.execute("UPDATE test SET name = ? WHERE id = ?", ("更新", 1))
print(f"{rows_affected}行を更新しました")
```

#### executemany()

複数のパラメータセットでSQL文を実行します。

```python
def executemany(self, sql: str, parameters_list: List[tuple]) -> int
```

**パラメータ:**
- `sql` (str): 実行するSQL文
- `parameters_list` (List[tuple]): パラメータのリスト

**戻り値:**
- `int`: 影響を受けた行数

**例外:**
- `DatabaseError`: 実行に失敗した場合

**例:**
```python
data = [
    (1, "馬A"),
    (2, "馬B"),
    (3, "馬C")
]
db.executemany("INSERT INTO horses (id, name) VALUES (?, ?)", data)
```

---

### データ取得

#### fetch_one()

1行のみ取得します。

```python
def fetch_one(self, sql: str, parameters: Optional[tuple] = None) -> Optional[Dict[str, Any]]
```

**パラメータ:**
- `sql` (str): 実行するクエリ
- `parameters` (Optional[tuple]): パラメータ化クエリの値

**戻り値:**
- `Optional[Dict[str, Any]]`: カラム名をキーとする辞書、または None

**例外:**
- `DatabaseError`: クエリに失敗した場合

**例:**
```python
# 馬情報を取得
row = db.fetch_one("SELECT * FROM NL_UM WHERE KettoNum = ?", ("2020105123",))
if row:
    print(f"馬名: {row['Bamei']}")
    print(f"性別: {row['SexCD']}")
```

#### fetch_all()

すべての行を取得します。

```python
def fetch_all(self, sql: str, parameters: Optional[tuple] = None) -> List[Dict[str, Any]]
```

**パラメータ:**
- `sql` (str): 実行するクエリ
- `parameters` (Optional[tuple]): パラメータ化クエリの値

**戻り値:**
- `List[Dict[str, Any]]`: 辞書のリスト

**例外:**
- `DatabaseError`: クエリに失敗した場合

**例:**
```python
# 2024年の全レース結果を取得
races = db.fetch_all("SELECT * FROM NL_RA WHERE Year = ?", (2024,))
for race in races:
    print(f"レース: {race['Hondai']} ({race['MonthDay']})")
```

---

### データ挿入（UPSERT機能）

#### insert()

1行のデータを挿入します。デフォルトでUPSERT動作（重複時は更新）を行います。

```python
def insert(self, table_name: str, data: Dict[str, Any], use_replace: bool = True) -> int
```

**パラメータ:**
- `table_name` (str): テーブル名
- `data` (Dict[str, Any]): カラム名と値の辞書
- `use_replace` (bool): True の場合 UPSERT を実行（デフォルト: True）

**戻り値:**
- `int`: 挿入された行数（成功時は1）

**例外:**
- `DatabaseError`: 挿入に失敗した場合

**UPSERT動作:**
- プライマリキーが存在する場合、既存レコードを更新
- プライマリキーが存在しない場合、新規レコードを挿入
- 同じインポートを複数回実行しても安全

**例:**
```python
# 馬情報を挿入（または更新）
horse_data = {
    "KettoNum": "2020105123",
    "Bamei": "サンプル馬",
    "SexCD": "1",
    "BirthDate": "20200415"
}
db.insert("NL_UM", horse_data)

# UPSERTを使用せず、エラーを発生させる場合
db.insert("NL_UM", horse_data, use_replace=False)  # 重複時はエラー
```

#### insert_many()

複数行のデータを一括挿入します。UPSERT機能付き。

```python
def insert_many(self, table_name: str, data_list: List[Dict[str, Any]], use_replace: bool = True) -> int
```

**パラメータ:**
- `table_name` (str): テーブル名
- `data_list` (List[Dict[str, Any]]): データの辞書のリスト
- `use_replace` (bool): True の場合 UPSERT を実行（デフォルト: True）

**戻り値:**
- `int`: 挿入/更新された行数

**例外:**
- `DatabaseError`: 挿入に失敗した場合

**例:**
```python
# 複数のレース結果を一括挿入
race_results = [
    {
        "Year": 2024,
        "MonthDay": "0525",
        "JyoCD": "05",
        "Kaiji": 3,
        "Nichiji": 5,
        "RaceNum": 11,
        "Umaban": 1,
        "KakuteiJyuni": 1
    },
    {
        "Year": 2024,
        "MonthDay": "0525",
        "JyoCD": "05",
        "Kaiji": 3,
        "Nichiji": 5,
        "RaceNum": 11,
        "Umaban": 2,
        "KakuteiJyuni": 2
    }
]
rows = db.insert_many("NL_SE", race_results)
print(f"{rows}行を挿入しました")
```

---

### テーブル管理

#### create_table()

テーブルを作成します。

```python
def create_table(self, table_name: str, schema: str) -> None
```

**パラメータ:**
- `table_name` (str): テーブル名
- `schema` (str): CREATE TABLE SQL文

**例外:**
- `DatabaseError`: テーブル作成に失敗した場合

**例:**
```python
schema = """
CREATE TABLE IF NOT EXISTS test_table (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    value REAL
)
"""
db.create_table("test_table", schema)
```

#### table_exists()

テーブルの存在を確認します。

```python
def table_exists(self, table_name: str) -> bool
```

**パラメータ:**
- `table_name` (str): テーブル名

**戻り値:**
- `bool`: テーブルが存在する場合True

**例:**
```python
if db.table_exists("NL_RA"):
    print("レーステーブルが存在します")
else:
    print("テーブルを作成する必要があります")
```

#### get_table_info()

テーブルのスキーマ情報を取得します。

```python
def get_table_info(self, table_name: str) -> List[Dict[str, Any]]
```

**パラメータ:**
- `table_name` (str): テーブル名

**戻り値:**
- `List[Dict[str, Any]]`: カラム情報の辞書のリスト

**例外:**
- `DatabaseError`: クエリに失敗した場合

**例:**
```python
columns = db.get_table_info("NL_UM")
for col in columns:
    print(f"カラム: {col['name']}, 型: {col['type']}")
```

---

### トランザクション管理

#### commit()

現在のトランザクションをコミットします。

```python
def commit(self) -> None
```

**例外:**
- `DatabaseError`: コミットに失敗した場合

**例:**
```python
try:
    db.execute("INSERT INTO test VALUES (1, 'data')")
    db.execute("INSERT INTO test VALUES (2, 'data')")
    db.commit()
    print("トランザクションをコミットしました")
except DatabaseError as e:
    db.rollback()
    print(f"エラー: {e}")
```

#### rollback()

現在のトランザクションをロールバックします。

```python
def rollback(self) -> None
```

**例外:**
- `DatabaseError`: ロールバックに失敗した場合

**例:**
```python
try:
    db.execute("INSERT INTO test VALUES (1, 'data')")
    # エラーが発生
    raise Exception("テストエラー")
except Exception as e:
    db.rollback()
    print("トランザクションをロールバックしました")
```

---

### コンテキストマネージャー

BaseDatabase はコンテキストマネージャーとして使用できます。

```python
def __enter__(self) -> 'BaseDatabase'
def __exit__(self, exc_type, exc_val, exc_tb) -> None
```

**動作:**
- `__enter__`: データベースに接続
- `__exit__`:
  - 例外が発生した場合: ロールバック
  - 正常終了した場合: コミット
  - いずれの場合も切断

**例:**
```python
# 自動的に接続、コミット/ロールバック、切断を管理
with SQLiteDatabase(config) as db:
    db.insert("NL_UM", horse_data)
    # 正常終了時は自動コミット
    # エラー時は自動ロールバック
# 自動的に切断される
```

---

### メンテナンス操作

#### vacuum()

データベースを最適化し、領域を回収します（SQLite/DuckDB）。

```python
def vacuum(self) -> None
```

**例外:**
- `DatabaseError`: 最適化に失敗した場合

**例:**
```python
# SQLite: 削除されたデータの領域を回収
db.vacuum()

# DuckDB: WALをディスクにフラッシュ
db.vacuum()  # 内部的にCHECKPOINTを実行
```

#### analyze()

データベース統計を更新します（DuckDB）。

```python
def analyze(self) -> None
```

**例外:**
- `DatabaseError`: 統計更新に失敗した場合

**例:**
```python
# クエリプランナーの最適化のため統計を更新
db.analyze()
```

---

## データベース実装

### SQLiteDatabase

ファイルベースの軽量データベース。

#### 設定項目

```python
config = {
    "path": "./data/keiba.db",        # データベースファイルパス
    "timeout": 30.0,                  # 接続タイムアウト（秒）
    "check_same_thread": False        # スレッド間共有の許可
}
```

#### 特徴

**UPSERT構文:**
```sql
INSERT OR REPLACE INTO table_name (columns...) VALUES (values...)
```

**識別子のクォート:**
- バッククォート（`）を使用
```python
def _quote_identifier(self, identifier: str) -> str:
    return f"`{identifier}`"
```

**パフォーマンス最適化:**
```python
PRAGMA journal_mode = WAL        # Write-Ahead Logging
PRAGMA synchronous = NORMAL      # 同期モードを緩和
PRAGMA cache_size = -64000       # 64MBキャッシュ
PRAGMA temp_store = MEMORY       # 一時テーブルをメモリに
PRAGMA foreign_keys = ON         # 外部キー制約を有効化
```

**例:**
```python
from src.database.sqlite_handler import SQLiteDatabase

config = {"path": "./data/keiba.db"}
db = SQLiteDatabase(config)

with db:
    # データ挿入（UPSERT）
    db.insert("NL_UM", {
        "KettoNum": "2020105123",
        "Bamei": "サンプル馬"
    })

    # クエリ実行
    horses = db.fetch_all("SELECT * FROM NL_UM WHERE BirthDate > ?", ("20200101",))
```

---

### DuckDBDatabase

分析処理に特化したOLAPデータベース。

#### 設定項目

```python
config = {
    "path": "./data/keiba.duckdb",   # データベースファイルパス
    "read_only": False,              # 読み取り専用モード
    "memory_limit": "2GB",           # メモリ制限
    "threads": 4                     # 使用スレッド数
}
```

#### 特徴

**UPSERT構文:**
```sql
INSERT INTO table_name (columns...)
VALUES (values...)
ON CONFLICT (primary_key_columns) DO UPDATE SET
    column1 = EXCLUDED.column1,
    column2 = EXCLUDED.column2
```

**識別子のクォート:**
- ダブルクォート（"）を使用（SQL標準）
```python
def _quote_identifier(self, identifier: str) -> str:
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'
```

**パフォーマンス最適化:**
```python
SET preserve_insertion_order = false  # 挿入順序の保持を無効化
```

**プライマリキーの自動検出:**
- `ON CONFLICT` 句で使用するため、テーブルのプライマリキーを自動検出
- プライマリキーがない場合は通常のINSERTにフォールバック

**例:**
```python
from src.database.duckdb_handler import DuckDBDatabase

config = {
    "path": "./data/keiba.duckdb",
    "memory_limit": "4GB",
    "threads": 8
}
db = DuckDBDatabase(config)

with db:
    # 複数レコードを一括挿入（UPSERT）
    race_data = [
        {"Year": 2024, "MonthDay": "0525", "JyoCD": "05", ...},
        {"Year": 2024, "MonthDay": "0526", "JyoCD": "06", ...},
    ]
    db.insert_many("NL_RA", race_data)

    # 分析クエリ（DuckDBの強み）
    stats = db.fetch_all("""
        SELECT
            Year,
            COUNT(*) as race_count,
            AVG(SyussoTosu) as avg_horses
        FROM NL_RA
        WHERE Year >= 2020
        GROUP BY Year
        ORDER BY Year
    """)
```

---

### PostgreSQLDatabase

（将来実装予定）

本格的なリレーショナルデータベース。

#### 予定される特徴

**UPSERT構文:**
```sql
INSERT INTO table_name (columns...)
VALUES (values...)
ON CONFLICT (primary_key_columns) DO UPDATE SET
    column1 = EXCLUDED.column1,
    column2 = EXCLUDED.column2
```

**識別子のクォート:**
- ダブルクォート（"）を使用

---

## データベース固有の動作比較

| 機能 | SQLite | DuckDB | PostgreSQL |
|------|--------|--------|------------|
| UPSERT構文 | `INSERT OR REPLACE` | `ON CONFLICT DO UPDATE` | `ON CONFLICT DO UPDATE` |
| 識別子クォート | バッククォート ` | ダブルクォート " | ダブルクォート " |
| プライマリキー自動検出 | 不要 | 必要 | 必要 |
| VACUUM | 領域回収 | CHECKPOINT | 領域回収 |
| ANALYZE | 未対応 | 統計更新 | 統計更新 |
| 並列処理 | 制限あり | 最適化済み | 最適化済み |

---

## スキーマ概要

JRVLTSQLは58のテーブルを定義しています。すべてのテーブルにプライマリキー制約が設定されています。

### テーブルのカテゴリ

#### 1. NL_ テーブル（蓄積データ）

確定後のデータを格納。JVOpen APIで取得。

**レース関連:**
- `NL_RA`: レース詳細（Race）
- `NL_SE`: 成績（SEiseki）
- `NL_RC`: レコード情報（ReCord）
- `NL_TK`: 登録馬（TouKoku）
- `NL_YS`: 開催スケジュール（Yotei Schedule）

**マスタ:**
- `NL_UM`: 馬マスタ（UMa）
- `NL_SK`: 馬生産（Seisan Keito）
- `NL_KS`: 騎手マスタ（KiSyu）
- `NL_CH`: 調教師マスタ（CHokyosi）
- `NL_BN`: 馬主マスタ（BaNusi）
- `NL_BR`: 生産者マスタ（BRreeder）
- `NL_BT`: 繁殖系統（BreediTng）
- `NL_HN`: 繁殖馬（HaNsyoku）
- `NL_CS`: コース（CourSe）

**オッズ:**
- `NL_O1` ~ `NL_O6`: 各種オッズ（単勝、複勝、枠連、馬連、ワイド、馬単、三連複、三連単）

**払戻:**
- `NL_H1`: 払戻情報（Haraimodosi）
- `NL_H6`: 三連単払戻
- `NL_HR`: 払戻返還情報

**その他:**
- `NL_CK`: 競走馬累積情報（Keisoba Keiseki）
- `NL_HC`: 調教師累積情報
- `NL_TM`: タイム指数（TiMe index）
- `NL_WF`: Win5（Wide Fukurenpuku）
- `NL_CC`: コース変更（Course Change）
- `NL_JC`: 騎手変更（Jockey Change）
- `NL_TC`: 時刻変更（Time Change）
- `NL_JG`: 場外発売情報
- `NL_WE`: 天候馬場状態（WEather）
- `NL_WH`: 天候馬場状態変更履歴
- `NL_DM`: データマイニング
- `NL_AV`: セリ市場情報（Auction Value）
- `NL_HS`: 繁殖馬セリ市場
- `NL_WC`: 調教情報（Workout Course）
- `NL_HY`: 馬名（Horse Yomi）

#### 2. RT_ テーブル（速報データ）

レース前・レース中の速報データ。JVRTOpen APIで取得。

- `RT_RA`, `RT_SE`, `RT_O1` ~ `RT_O6`, `RT_H1`, `RT_H6`, `RT_HR`, など
- NL_と同じ構造だが、リアルタイムデータ用

#### 3. TS_ テーブル（時系列データ）

オッズの時系列変化を記録。

- `TS_O1` ~ `TS_O6`: 各種オッズの時系列データ
- プライマリキーに `HassoTime`（発走時刻）を含む

### プライマリキーの規則

**レース単位のテーブル:**
```sql
PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)
```

**馬単位のテーブル（成績など）:**
```sql
PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban)
```

**オッズテーブル:**
```sql
-- 単勝・複勝（馬番単位）
PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban)

-- 馬連・ワイドなど（組み合わせ単位）
PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Kumi)
```

**時系列オッズテーブル:**
```sql
PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban, HassoTime)
```

**マスタテーブル:**
```sql
-- 馬マスタ
PRIMARY KEY (KettoNum)

-- 騎手マスタ
PRIMARY KEY (KisyuCode)

-- 調教師マスタ
PRIMARY KEY (ChokyosiCode)
```

### データ型の最適化

```sql
-- 整数型: 年、回次、日次、レース番号、馬番、距離、月日
Year INTEGER
MonthDay INTEGER
Kaiji INTEGER
Nichiji INTEGER
RaceNum INTEGER
Umaban INTEGER
Kyori INTEGER

-- 実数型: オッズ、タイム、ハロンタイム、賞金
Odds REAL
Time REAL
Haron3F REAL
Honsyokin REAL

-- テキスト型: コード（固定長）、日付（YYYYMMDD）、名前
JyoCD TEXT          -- 競馬場コード
KettoNum TEXT       -- 血統登録番号
Bamei TEXT          -- 馬名
```

---

## エラーハンドリング

### DatabaseError 例外

すべてのデータベース操作エラーは `DatabaseError` 例外として発生します。

```python
from src.database.base import DatabaseError
```

### 例外の種類

**接続エラー:**
```python
try:
    db.connect()
except DatabaseError as e:
    print(f"接続エラー: {e}")
```

**SQL実行エラー:**
```python
try:
    db.execute("INVALID SQL")
except DatabaseError as e:
    print(f"SQL実行エラー: {e}")
    # 自動的にロールバックされる
```

**データ挿入エラー:**
```python
try:
    db.insert("NL_UM", {})  # 空データ
except DatabaseError as e:
    print(f"挿入エラー: {e}")
```

### エラーハンドリングのベストプラクティス

#### 1. コンテキストマネージャーの使用

```python
try:
    with SQLiteDatabase(config) as db:
        db.insert("NL_UM", horse_data)
        db.insert("NL_SE", race_data)
        # 正常終了時は自動コミット
        # エラー時は自動ロールバック
except DatabaseError as e:
    print(f"データベースエラー: {e}")
    # 必要に応じてリトライやログ記録
```

#### 2. 明示的なトランザクション管理

```python
db = SQLiteDatabase(config)
db.connect()

try:
    # 複数の操作を1トランザクションで
    for data in large_dataset:
        db.insert("NL_SE", data)

    db.commit()
    print("すべてのデータを挿入しました")

except DatabaseError as e:
    db.rollback()
    print(f"エラーが発生、ロールバックしました: {e}")

finally:
    db.disconnect()
```

#### 3. バッチ処理でのエラーハンドリング

```python
def safe_batch_insert(db, table_name, data_list, batch_size=1000):
    """バッチ単位で安全にデータを挿入"""
    total = len(data_list)
    inserted = 0

    for i in range(0, total, batch_size):
        batch = data_list[i:i + batch_size]

        try:
            count = db.insert_many(table_name, batch)
            inserted += count
            db.commit()
            print(f"進捗: {inserted}/{total}")

        except DatabaseError as e:
            db.rollback()
            print(f"バッチ {i}-{i+batch_size} でエラー: {e}")

            # 1件ずつリトライ
            for data in batch:
                try:
                    db.insert(table_name, data)
                    db.commit()
                    inserted += 1
                except DatabaseError as e2:
                    print(f"スキップ: {e2}")

    return inserted
```

---

## 使用例

### 基本的な使用パターン

```python
from src.database.sqlite_handler import SQLiteDatabase
from src.database.schema import SchemaManager

# 1. データベース初期化
config = {"path": "./data/keiba.db"}
db = SQLiteDatabase(config)

with db:
    # 2. テーブル作成
    schema_mgr = SchemaManager(db)
    schema_mgr.create_all_tables()

    # 3. データ挿入
    horse_data = {
        "KettoNum": "2020105123",
        "Bamei": "サンプル馬",
        "SexCD": "1",
        "BirthDate": "20200415"
    }
    db.insert("NL_UM", horse_data)

    # 4. データ取得
    horses = db.fetch_all(
        "SELECT * FROM NL_UM WHERE BirthDate >= ?",
        ("20200101",)
    )

    for horse in horses:
        print(f"{horse['Bamei']} ({horse['KettoNum']})")
```

### 分析処理（DuckDB）

```python
from src.database.duckdb_handler import DuckDBDatabase

config = {
    "path": "./data/keiba.duckdb",
    "memory_limit": "4GB",
    "threads": 8
}

with DuckDBDatabase(config) as db:
    # 集計クエリ
    stats = db.fetch_all("""
        SELECT
            r.Year,
            r.JyoCD,
            COUNT(*) as race_count,
            AVG(r.SyussoTosu) as avg_horses,
            AVG(s.Time) as avg_time
        FROM NL_RA r
        LEFT JOIN NL_SE s ON
            r.Year = s.Year AND
            r.MonthDay = s.MonthDay AND
            r.JyoCD = s.JyoCD AND
            r.Kaiji = s.Kaiji AND
            r.Nichiji = s.Nichiji AND
            r.RaceNum = s.RaceNum AND
            s.KakuteiJyuni = 1
        WHERE r.Year >= 2020
        GROUP BY r.Year, r.JyoCD
        ORDER BY r.Year, r.JyoCD
    """)

    for row in stats:
        print(f"{row['Year']} - 場所{row['JyoCD']}: "
              f"{row['race_count']}レース, "
              f"平均{row['avg_horses']:.1f}頭")
```

### 大量データのインポート

```python
from src.database.sqlite_handler import SQLiteDatabase

config = {"path": "./data/keiba.db"}
db = SQLiteDatabase(config)
db.connect()

try:
    # 大量データを準備
    race_results = []
    for i in range(10000):
        race_results.append({
            "Year": 2024,
            "MonthDay": "0525",
            "JyoCD": "05",
            "Kaiji": 3,
            "Nichiji": 5,
            "RaceNum": i % 12 + 1,
            "Umaban": i % 18 + 1,
            "KakuteiJyuni": i % 18 + 1
        })

    # バッチサイズを指定して一括挿入
    batch_size = 1000
    for i in range(0, len(race_results), batch_size):
        batch = race_results[i:i + batch_size]
        db.insert_many("NL_SE", batch)
        db.commit()
        print(f"進捗: {min(i + batch_size, len(race_results))}/{len(race_results)}")

    print("インポート完了")

except DatabaseError as e:
    print(f"エラー: {e}")
    db.rollback()

finally:
    db.disconnect()
```

---

## まとめ

JRVLTSQLのデータベースハンドラAPIは以下の特徴を持ちます:

1. **統一されたインターフェース**: BaseDatabase抽象クラスによる一貫したAPI
2. **UPSERT機能**: 重複データの自動更新で安全な再インポート
3. **データベース固有の最適化**: 各DBの特性を活かした実装
4. **エラーハンドリング**: DatabaseError例外による統一的なエラー処理
5. **トランザクション管理**: コンテキストマネージャーによる安全な処理
6. **高速なバッチ処理**: executemany()による効率的なデータ挿入

このAPIを使用することで、JV-Dataを効率的にデータベースに格納し、分析することができます。
