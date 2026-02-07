# アーキテクチャ

JRVLTSQLのシステムアーキテクチャについて説明します。

## 全体構成

```
┌─────────────────────────────────────────────────────────┐
│                      CLI Layer                          │
│  (click-based commands: fetch, realtime, export, etc.) │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   Service Layer                         │
│  (BatchProcessor, RealtimeMonitor, DataImporter)       │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   Fetcher Layer                         │
│  (HistoricalFetcher, RealtimeFetcher)                  │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   JV-Link Layer                         │
│  (JVLinkWrapper - COM API Interface)                   │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   Parser Layer                          │
│  (38 Parsers via ParserFactory)                        │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                  Database Layer                         │
│  (SQLite, PostgreSQL handlers)                         │
└─────────────────────────────────────────────────────────┘
```

## モジュール構成

```
src/
├── cli/                 # CLIコマンド
│   └── main.py         # click-based CLI
├── database/           # データベース層
│   ├── base.py         # BaseDatabase抽象クラス
│   ├── sqlite_handler.py
│   ├── postgresql_handler.py
│   ├── schema.py       # 64テーブル定義
│   ├── schema_metadata.py  # メタデータ
│   └── index_manager.py
├── fetcher/            # データ取得層
│   ├── historical.py   # 蓄積データ取得
│   └── realtime.py     # リアルタイムデータ取得
├── importer/           # インポート層
│   ├── importer.py     # DataImporter
│   └── batch.py        # BatchProcessor
├── jvlink/             # JV-Link連携層
│   ├── wrapper.py      # COM APIラッパー
│   └── constants.py    # 定数定義
├── parser/             # パーサー層
│   ├── base.py         # BaseParser
│   ├── factory.py      # ParserFactory
│   └── *_parser.py     # 38種のパーサー
├── services/           # サービス層
│   └── realtime_monitor.py
└── utils/              # ユーティリティ
    ├── config.py       # 設定管理
    ├── logger.py       # ログ設定
    └── lock_manager.py # プロセスロック
```

## データフロー

### 蓄積データ取得

```
1. CLI: jltsql fetch --spec RACE
   │
2. BatchProcessor.process_date_range()
   │
3. HistoricalFetcher.fetch()
   │  - JVLinkWrapper.jv_open()
   │  - JVLinkWrapper.jv_read() (loop)
   │  - ParserFactory.parse()
   │
4. DataImporter.import_records()
   │  - _convert_record() (型変換)
   │  - database.insert_many() (バッチ挿入)
   │
5. Database (SQLite/PostgreSQL)
```

### リアルタイムデータ取得

```
1. CLI: jltsql realtime start
   │
2. RealtimeMonitor.start()
   │  - スレッド起動
   │
3. RealtimeFetcher.fetch_stream() (継続)
   │  - JVLinkWrapper.jv_rt_open()
   │  - JVLinkWrapper.jv_read()
   │  - ParserFactory.parse()
   │
4. DataImporter (RT_テーブルに格納)
```

## 主要クラス

### JVLinkWrapper

JRA-VAN JV-Link COM APIのPythonラッパー。

```python
class JVLinkWrapper:
    def jv_init() -> int
    def jv_open(data_spec, fromtime, option) -> tuple
    def jv_read() -> tuple
    def jv_close() -> int
    def jv_rt_open(data_spec, key) -> int
```

### ParserFactory

38種のパーサーを管理するファクトリー。

```python
class ParserFactory:
    def get_parser(record_type: str) -> BaseParser
    def parse(raw_bytes: bytes) -> dict
    def supported_types() -> List[str]
```

### BaseDatabase

データベースハンドラーの抽象基底クラス。

```python
class BaseDatabase(ABC):
    @abstractmethod
    def connect()
    def disconnect()
    def execute(sql, params)
    def fetch_all(sql, params)
    def insert(table, data)
    def insert_many(table, data_list)
```

### DataImporter

パース済みデータをデータベースにインポート。

```python
class DataImporter:
    def import_records(records_iter) -> dict
    def _convert_record(record, table_name) -> dict
```

## 設計原則

### 1. 抽象化

データベース層は抽象クラスで統一され、SQLite/PostgreSQLを同じインターフェースで扱えます。

### 2. ファクトリーパターン

パーサーはファクトリーで管理され、レコードタイプに応じた適切なパーサーを自動選択します。

### 3. イテレーターパターン

データ取得はイテレーターで実装され、大量データもメモリ効率よく処理できます。

### 4. コンテキストマネージャー

データベース接続は`with`文で自動管理され、リソースリークを防止します。

### 5. UPSERT

INSERT OR REPLACEにより、再実行時も重複を気にせず安全にインポートできます。

## エラー処理

### 例外階層

```
DatabaseError (基底例外)
├── ConnectionError
├── QueryError
└── TransactionError

JVLinkError (JV-Link関連)
├── OpenError
├── ReadError
└── ServiceKeyError
```

### リトライ機構

`tenacity`ライブラリによる自動リトライ：

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def fetch_with_retry():
    ...
```

## パフォーマンス最適化

### バッチ処理

- デフォルトバッチサイズ: 1000レコード
- コミット間隔: 5000レコード

### SQLite最適化

- WALモード
- 64MBキャッシュ
- メモリ内一時テーブル

## 拡張ポイント

### 新規データベース対応

1. `BaseDatabase`を継承
2. 必須メソッドを実装
3. `database/__init__.py`に登録

### 新規パーサー対応

1. `BaseParser`を継承
2. `_define_fields()`を実装
3. `ParserFactory`に登録

詳細な設計ドキュメントは[ARCHITECTURE_DESIGN.md](https://github.com/miyamamoto/jrvltsql/blob/master/docs/ARCHITECTURE_DESIGN.md)を参照してください。
