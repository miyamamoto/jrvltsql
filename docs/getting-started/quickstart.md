# クイックスタート

## 初回セットアップ: `quickstart.bat`

最も簡単な方法は、`quickstart.bat` をダブルクリックするか、コマンドラインから実行することです。

```bat
quickstart.bat
```

内部では `scripts/quickstart.py` を呼び出します。  
Windows 実機で `quickstart.bat --mode update --yes --no-odds` が動作し、実際にレースデータ取得が進むことを確認しています。

`quickstart.bat` は次の順で Python を探します。

1. `venv32\Scripts\python.exe`
2. `.venv\Scripts\python.exe`
3. `PYTHON`
4. `py`
5. `python`

### セットアップの流れ

1. 設定ファイル確認
2. JV-Link 接続チェック
3. テーブル作成と初期化
4. 初回データ取得
5. 完了後の状態確認

## 日次同期: `daily_sync.bat`

日次運用では `daily_sync.bat` を使います。

```bat
daily_sync.bat
```

これは `scripts/daily_update.py` を呼び出し、直近 7 日分の差分を取り込みます。  
現在の対象 spec は `TOKU`, `RACE`, `TCVN`, `RCVN` です。

Windows 実機での確認では、

- `TOKU` の取得が完了
- 続いて `RACE` の取り込みが進行
- `NL_JG`, `NL_H1` などへの insert が実際に発生

を確認しています。

## Scheduled Task の登録

```powershell
powershell -ExecutionPolicy Bypass -File .\install_tasks.ps1 -Force
```

これで `JRVLTSQL_DailySync` を毎日 `06:30` に登録または更新します。

## コマンドラインでの手動セットアップ

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

JV-Link では `option=4` でセットアップ、`option=1` で差分取得を行います。  
現在の batch 実装では、長い setup 範囲を年単位に分割して処理するため、巨大レンジでも以前より安全に流せます。

```bash
# レースデータ取得（2024年）
jltsql fetch --from 20240101 --to 20241231 --spec RACE

# マスターデータ取得
jltsql fetch --from 20240101 --to 20241231 --spec DIFF
```

## `quickstart.py` オプション

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
