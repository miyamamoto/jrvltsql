# スキーマ定義

JRVLTSQLのデータベーススキーマ（64テーブル）について説明します。

## テーブル分類

### NL_テーブル（蓄積系）: 38テーブル

レース終了後に確定するデータを格納します。

### RT_テーブル（速報系）: 20テーブル

レース当日のリアルタイムデータを格納します。

### TS_テーブル（時系列）: 6テーブル

オッズの時間推移を記録します。

## 主要テーブル

### レース情報

| テーブル | 説明 | PRIMARY KEY |
|---------|------|-------------|
| NL_RA | レース詳細 | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum |
| NL_SE | 馬毎レース情報 | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban |
| NL_HR | 払戻情報 | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum |
| NL_H1 | 払戻詳細 | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum |
| NL_H6 | 三連単払戻 | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, SanrentanKumi |

### オッズ情報

| テーブル | 説明 | 式別 |
|---------|------|------|
| NL_O1 | 単勝・複勝・枠連 | 単勝、複勝、枠連 |
| NL_O2 | 馬連 | 馬連 |
| NL_O3 | ワイド | ワイド |
| NL_O4 | 馬単 | 馬単 |
| NL_O5 | 三連複 | 三連複 |
| NL_O6 | 三連単 | 三連単 |

### マスターデータ

| テーブル | 説明 | PRIMARY KEY |
|---------|------|-------------|
| NL_UM | 馬マスタ | KettoNum |
| NL_KS | 騎手マスタ | KisyuCode |
| NL_CH | 調教師マスタ | ChokyosiCode |
| NL_BN | 馬主マスタ | BanusiCode |
| NL_BR | 生産者マスタ | BreederCode |
| NL_BT | 血統マスタ | HansyokuNum |
| NL_HN | 繁殖馬マスタ | HansyokuNum |

## データ型

JRVLTSQLは適切な型に最適化しています：

| 型 | 用途 | 例 |
|----|------|---|
| INTEGER | 年、月日、レース番号、馬番 | Year, MonthDay, RaceNum, Umaban |
| REAL | オッズ、タイム、体重 | TanOdds, Time, BaTaijyu |
| TEXT | コード、名前、日付文字列 | JyoCD, Bamei, MakeDate |
| BIGINT | 賞金、票数 | Honsyokin, TanVote |

## 主要カラム

### レース識別キー（6項目）

ほとんどのテーブルで共通のキー構成：

| カラム | 説明 | 例 |
|--------|------|---|
| Year | 開催年 | 2024 |
| MonthDay | 月日（MMDD形式） | 601 (6月1日) |
| JyoCD | 競馬場コード | 05 (東京) |
| Kaiji | 回次 | 3 (第3回) |
| Nichiji | 日次 | 8 (8日目) |
| RaceNum | レース番号 | 11 |

### 競馬場コード (JyoCD)

| コード | 競馬場 |
|--------|--------|
| 01 | 札幌 |
| 02 | 函館 |
| 03 | 福島 |
| 04 | 新潟 |
| 05 | 東京 |
| 06 | 中山 |
| 07 | 中京 |
| 08 | 京都 |
| 09 | 阪神 |
| 10 | 小倉 |

### 馬識別キー

| カラム | 説明 | 例 |
|--------|------|---|
| KettoNum | 血統登録番号（10桁） | 2019104567 |

### 人物識別キー

| カラム | 説明 |
|--------|------|
| KisyuCode | 騎手コード |
| ChokyosiCode | 調教師コード |
| BanusiCode | 馬主コード |
| BreederCode | 生産者コード |

## NL_RAテーブル（レース詳細）

```sql
CREATE TABLE NL_RA (
    RecordSpec TEXT,
    DataKubun TEXT,
    MakeDate TEXT,
    Year INTEGER,
    MonthDay INTEGER,
    JyoCD TEXT,
    Kaiji INTEGER,
    Nichiji INTEGER,
    RaceNum INTEGER,
    YoubiCD TEXT,          -- 曜日コード
    Hondai TEXT,           -- レース名
    GradeCD TEXT,          -- グレード (A=G1, B=G2, C=G3...)
    Kyori INTEGER,         -- 距離
    TrackCD TEXT,          -- コース (01=芝, 02=ダート...)
    HassoTime TEXT,        -- 発走時刻
    TenkoCD TEXT,          -- 天候
    SibaBabaCD TEXT,       -- 芝馬場状態
    DirtBabaCD TEXT,       -- ダート馬場状態
    -- ... 他多数
    PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)
);
```

## NL_SEテーブル（馬毎レース情報）

```sql
CREATE TABLE NL_SE (
    -- 識別キー
    Year INTEGER,
    MonthDay INTEGER,
    JyoCD TEXT,
    Kaiji INTEGER,
    Nichiji INTEGER,
    RaceNum INTEGER,
    Umaban INTEGER,        -- 馬番

    -- 馬情報
    KettoNum TEXT,         -- 血統登録番号
    Bamei TEXT,            -- 馬名
    SexCD TEXT,            -- 性別
    Barei INTEGER,         -- 馬齢

    -- 騎手・調教師
    KisyuCode TEXT,
    ChokyosiCode TEXT,

    -- 結果
    KakuteiJyuni INTEGER,  -- 確定着順
    Time REAL,             -- タイム
    Odds REAL,             -- 単勝オッズ
    Ninki INTEGER,         -- 人気

    PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban)
);
```

## NL_UMテーブル（馬マスタ）

```sql
CREATE TABLE NL_UM (
    KettoNum TEXT,         -- 血統登録番号
    Bamei TEXT,            -- 馬名
    BameiKana TEXT,        -- 馬名カナ
    BirthDate TEXT,        -- 生年月日
    SexCD TEXT,            -- 性別
    KeiroCD TEXT,          -- 毛色

    -- 血統（父、母、祖父母等）
    Ketto3InfoHansyokuNum1 TEXT,  -- 父
    Ketto3InfoBamei1 TEXT,
    Ketto3InfoHansyokuNum2 TEXT,  -- 母
    Ketto3InfoBamei2 TEXT,
    -- ...

    -- 関係者
    ChokyosiCode TEXT,     -- 調教師
    BanusiCode TEXT,       -- 馬主
    BreederCode TEXT,      -- 生産者

    PRIMARY KEY (KettoNum)
);
```

## 時系列テーブル（TS_O*）

HassoTimeをキーに含めて、複数時点のオッズを記録：

```sql
CREATE TABLE TS_O1 (
    Year INTEGER,
    MonthDay INTEGER,
    JyoCD TEXT,
    Kaiji INTEGER,
    Nichiji INTEGER,
    RaceNum INTEGER,
    HassoTime TEXT,        -- 時刻（キーに含む）
    Umaban INTEGER,
    TanOdds REAL,
    TanNinki INTEGER,
    PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban, HassoTime)
);
```

## スキーマ操作API

### テーブル作成

```python
from src.database.schema import create_all_tables, SCHEMAS

# 全テーブル作成
create_all_tables(db)

# 個別テーブル作成
db.execute(SCHEMAS["NL_RA"])
```

### SchemaManager

```python
from src.database.schema import SchemaManager

manager = SchemaManager(db)

# テーブル一覧
tables = manager.get_table_names()

# 存在確認
if manager.table_exists("NL_RA"):
    print("存在")

# 欠落テーブル確認
missing = manager.get_missing_tables()
```

詳細なスキーマ情報は[API.md](https://github.com/miyamamoto/jrvltsql/blob/master/docs/API.md)を参照してください。
