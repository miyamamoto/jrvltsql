# パーサーAPI

JV-Dataのレコードをパースするための38種類のパーサーについて説明します。

## ParserFactory

パーサーの取得にはファクトリーパターンを使用します。

```python
from src.parser.factory import get_parser_factory

factory = get_parser_factory()  # シングルトン

# レコードタイプを指定してパーサー取得
parser = factory.get_parser("RA")

# 生データをパース
parsed = parser.parse(raw_bytes)

# 自動検出パース（先頭2バイトでタイプ判定）
parsed = factory.parse(raw_bytes)

# サポートされるタイプ一覧
types = factory.supported_types()  # ['RA', 'SE', 'HR', ...]
```

## レコードタイプ

### 蓄積系データ (38種類)

| タイプ | パーサー | 説明 |
|--------|---------|------|
| RA | RAParser | レース詳細 |
| SE | SEParser | 馬毎レース情報 |
| HR | HRParser | 払戻情報 |
| H1 | H1Parser | 払戻詳細 |
| H6 | H6Parser | 三連単払戻 |
| O1 | O1Parser | 単勝・複勝オッズ |
| O2 | O2Parser | 馬連オッズ |
| O3 | O3Parser | ワイドオッズ |
| O4 | O4Parser | 馬単オッズ |
| O5 | O5Parser | 三連複オッズ |
| O6 | O6Parser | 三連単オッズ |
| UM | UMParser | 馬マスタ |
| KS | KSParser | 騎手マスタ |
| CH | CHParser | 調教師マスタ |
| BN | BNParser | 馬主マスタ |
| BR | BRParser | 生産者マスタ |
| BT | BTParser | 血統マスタ |
| HN | HNParser | 繁殖馬マスタ |
| SK | SKParser | 産駒マスタ |
| RC | RCParser | レコード情報 |
| HC | HCParser | 調教師成績 |
| HY | HYParser | 馬名履歴 |
| YS | YSParser | 開催スケジュール |
| JG | JGParser | 出走取消 |
| JC | JCParser | 騎手変更 |
| TC | TCParser | 発走時刻変更 |
| CC | CCParser | コース変更 |
| WE | WEParser | 天候馬場 |
| WH | WHParser | 馬体重 |
| WF | WFParser | WIN5 |
| WC | WCParser | 調教 |
| TK | TKParser | 登録馬 |
| TM | TMParser | タイムマスタ |
| DM | DMParser | データマイニング |
| CS | CSParser | コースマスタ |
| CK | CKParser | 競走馬情報 |
| AV | AVParser | 市場取引 |
| HS | HSParser | 馬主履歴 |

## BaseParser

すべてのパーサーの基底クラスです。

### フィールド定義

```python
from dataclasses import dataclass

@dataclass
class FieldDef:
    name: str      # フィールド名
    pos: int       # 開始位置（バイト）
    size: int      # サイズ（バイト）
    type: str      # 型（ASCII, NUMERIC, SJIS等）
    default: Any   # デフォルト値
```

### パーサーの構造

```python
class RAParser(BaseParser):
    record_type = "RA"

    def _define_fields(self) -> List[FieldDef]:
        return [
            FieldDef("RecordSpec", 0, 2, "ASCII"),
            FieldDef("DataKubun", 2, 1, "ASCII"),
            FieldDef("Year", 3, 4, "NUMERIC"),
            FieldDef("MonthDay", 7, 4, "NUMERIC"),
            # ...
        ]
```

### メソッド

#### parse(record: bytes) -> dict

生バイトデータをパースして辞書を返します。

```python
parser = factory.get_parser("RA")
data = parser.parse(raw_bytes)
print(data["Year"])      # 2024
print(data["RaceNum"])   # 11
```

#### get_field_names() -> List[str]

フィールド名のリストを返します。

```python
fields = parser.get_field_names()
# ['RecordSpec', 'DataKubun', 'Year', 'MonthDay', ...]
```

#### get_field_def(field_name) -> FieldDef

指定フィールドの定義を返します。

```python
field = parser.get_field_def("Year")
print(field.pos)   # 3
print(field.size)  # 4
print(field.type)  # NUMERIC
```

## 型変換

### フィールドタイプ

| タイプ | 説明 | 変換結果 |
|--------|------|---------|
| ASCII | ASCII文字列 | str |
| NUMERIC | 数値文字列 | int |
| SJIS | Shift-JIS文字列 | str |

### 特殊な変換

#### オッズ値

JV-Dataのオッズは10倍値で格納されています：

```python
# 元データ: "0035" -> 3.5倍
odds = int(raw_odds) / 10  # 自動変換される
```

#### タイム値

タイムは0.1秒単位：

```python
# 元データ: "01234" -> 123.4秒
time = int(raw_time) / 10
```

## カスタムパーサー

新しいレコードタイプに対応する場合：

```python
from src.parser.base import BaseParser, FieldDef

class CustomParser(BaseParser):
    record_type = "XX"

    def _define_fields(self):
        return [
            FieldDef("RecordSpec", 0, 2, "ASCII"),
            FieldDef("CustomField", 2, 10, "SJIS"),
            # ...
        ]

# ファクトリーに登録
factory.register_parser("XX", CustomParser)
```

## 使用例

### 基本的なパース

```python
from src.parser.factory import get_parser_factory

factory = get_parser_factory()

# RAレコードをパース
with open("data.jvd", "rb") as f:
    raw = f.read(factory.get_parser("RA").RECORD_LENGTH)
    data = factory.parse(raw)
    print(f"レース: {data['Hondai']}")
    print(f"距離: {data['Kyori']}m")
```

### フェッチャーとの連携

```python
from src.fetcher.historical import HistoricalFetcher

fetcher = HistoricalFetcher(sid="JLTSQL")

# fetchはパース済みデータを返す
for record in fetcher.fetch("RACE", "20240101", "20241231"):
    print(record["Year"], record["RaceNum"])
```

### バッチ処理

```python
from src.importer.batch import BatchProcessor

processor = BatchProcessor(database=db, sid="JLTSQL")

# 内部でパーサーを使用
stats = processor.process_date_range(
    data_spec="RACE",
    from_date="20240101",
    to_date="20241231"
)
```

## エンコーディング

JV-DataはShift-JISエンコーディングを使用しています。パーサーは自動的に変換を行いますが、特殊文字や外字の処理には注意が必要です。

```python
# 内部では以下のような処理
try:
    text = raw_bytes.decode('shift_jis')
except UnicodeDecodeError:
    text = raw_bytes.decode('cp932', errors='replace')
```

詳細なパーサー仕様は各パーサーのソースコードを参照してください。
