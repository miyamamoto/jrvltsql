# クイックスタート

## quickstartスクリプトで簡単セットアップ

最も簡単な方法は、`quickstart.bat`をダブルクリックするか、コマンドラインから実行することです：

```bash
# batファイル（32-bit Pythonを自動検出）
quickstart.bat

# または直接実行
python scripts/quickstart.py
```

`quickstart.bat`はPython 3.12 (32-bit) を優先的に検出します（`py -3.12-32` → `py -32` → `py` → `python`の順）。

### セットアップの流れ

1. **データソース選択**: JRA（中央）/ NAR（地方）/ ALL（両方）
2. **データベース選択**: SQLite（デフォルト）/ PostgreSQL
3. **サービスキー確認**: JV-Link / NV-Link の接続チェック
4. **セットアップモード選択**: 簡易 / 標準 / フル
5. **データ範囲指定**: 過去何年分のデータを取得するか
6. **オプション設定**: 時系列オッズ、当日レース情報、自動更新サービス
7. **確認と実行**: 設定を確認してインポート開始

### データソースモード

| モード | 説明 | 必要なサービス |
|--------|------|---------------|
| **JRA** | 中央競馬データのみ取得 | JV-Link (JRA-VAN DataLab) |
| **NAR** | 地方競馬データのみ取得 | NV-Link (地方競馬DATA) |
| **ALL** | 中央・地方の両方を取得 | JV-Link + NV-Link |

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

### 3. データ取得

JV-Link / NV-Linkでは`option=4`でセットアップ（全データ取得）、`option=1`で差分取得を行います。11ヶ月以上前のデータはquickstartが自動的に`option=4`を選択します。

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
```

## データ取得後の確認

```bash
# ステータス確認
jltsql status

# SQLiteでテーブル一覧と件数を確認
sqlite3 data/keiba.db "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
```

## 次のステップ

- [設定](configuration.md) - 詳細な設定方法
- [CLIリファレンス](../user-guide/cli.md) - すべてのコマンド
- [データインポート](../user-guide/data-import.md) - データ取得の詳細
