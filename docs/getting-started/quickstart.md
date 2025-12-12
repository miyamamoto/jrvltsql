# クイックスタート

## 対話形式セットアップ

最も簡単な方法は、quickstartスクリプトを使用することです：

```bash
python scripts/quickstart.py
```

または、`quickstart.bat`をダブルクリックしてください。

### セットアップの流れ

1. **データベース選択**: SQLite / DuckDB / PostgreSQL
2. **データ範囲指定**: 過去何年分のデータを取得するか
3. **データ種別選択**: 取得するデータの種類
4. **確認と実行**: 設定を確認してインポート開始

## コマンドラインでのセットアップ

### 1. 初期化

```bash
jltsql init
```

これにより以下が作成されます：
- `config/config.yaml` - 設定ファイル
- `data/` - データベースファイル格納ディレクトリ
- `logs/` - ログファイル格納ディレクトリ

### 2. テーブル作成

```bash
jltsql create-tables
```

64テーブルすべてが作成されます。

### 3. データ取得

```bash
# レースデータ取得（2024年）
jltsql fetch --from 20240101 --to 20241231 --spec RACE

# マスターデータ取得
jltsql fetch --from 20240101 --to 20241231 --spec DIFF
```

## quickstartオプション

```bash
# 過去5年分のデータを取得
python scripts/quickstart.py --years 5

# オッズデータを除外
python scripts/quickstart.py --no-odds

# 確認プロンプトをスキップ
python scripts/quickstart.py -y

# DuckDBを使用
python scripts/quickstart.py --db duckdb
```

## データ取得後の確認

```bash
# ステータス確認
jltsql status

# テーブル一覧と件数
sqlite3 data/keiba.db "SELECT name, (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=m.name) FROM sqlite_master m WHERE type='table';"
```

## 次のステップ

- [設定](configuration.md) - 詳細な設定方法
- [CLIリファレンス](../user-guide/cli.md) - すべてのコマンド
- [データインポート](../user-guide/data-import.md) - データ取得の詳細
