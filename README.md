# JRVLTSQL

JRA-VAN DataLab データを SQLite / PostgreSQL に取り込む Windows 向けツールです。  
JRA（中央競馬）専用です。

## 必要要件

| 項目 | 要件 |
|------|------|
| OS | Windows 10 / 11 |
| Python | 3.10 以上 |
| JRA-VAN | DataLab 会員登録 + サービスキー |

`quickstart.bat` と `daily_sync.bat` は、次の順で Python を探します。

1. `venv32\\Scripts\\python.exe`
2. `.venv\\Scripts\\python.exe`
3. `PYTHON` 環境変数
4. `py`
5. `python`

JV-Link は Windows 上でのみ動作します。既存の 32-bit Python 環境がある場合はそのまま使えますが、現在のバッチ起動導線は repo 内仮想環境を優先します。

## Windows での使い方

### 初回セットアップ

```bat
quickstart.bat
```

`quickstart.bat` は対話型セットアップです。Windows 実機で起動確認済みで、`scripts/quickstart.py` を呼び出して:

1. Python を検出
2. 設定と接続を確認
3. テーブルを初期化
4. 初回データ取得を開始

を行います。

### 日次同期

```bat
daily_sync.bat
```

`daily_sync.bat` は非対話の日次差分取得用です。`scripts/daily_update.py` を呼び出し、直近 7 日の `TOKU / RACE / TCVN / RCVN` を順に同期します。  
Windows 実機では `TOKU` 取得と `RACE` 取り込みが進み、実際に PostgreSQL への insert が発生することを確認しています。

### Scheduled Task 登録

```powershell
powershell -ExecutionPolicy Bypass -File .\install_tasks.ps1 -Force
```

これで `JRVLTSQL_DailySync` を毎日 `06:30` に登録または更新します。

## インストール

```bat
git clone https://github.com/miyamamoto/jrvltsql.git
cd jrvltsql
pip install -e .
```

---

## 主な CLI コマンド

```bat
jltsql status                          # DB 状態確認
jltsql create-tables                   # テーブル作成
jltsql create-indexes                  # インデックス作成
jltsql fetch --from 20260101 --to 20260417 --spec RACE --option 1
jltsql realtime start --specs 0B12,0B15,0B30,0B31,0B32,0B33,0B34,0B35,0B36
jltsql cache info                      # キャッシュ統計
jltsql cache sync --download           # S3 → ローカル同期
jltsql cache sync --upload             # ローカル → S3 同期
```

### fetch オプション

| option | 内容 |
|--------|------|
| 1 | 通常取得（差分） |
| 2 | セットアップ（簡易） |
| 3 | セットアップ（標準） |
| 4 | 分割セットアップ（全履歴、1954〜現在） |

---

## レースデー監視

### tmux セッション起動

```bash
# WSL または Git Bash から
bash scripts/raceday_tmux.sh           # 起動 + アタッチ
bash scripts/raceday_tmux.sh --detach  # バックグラウンド起動
bash scripts/raceday_tmux.sh --from 12:00  # 午後から開始
```

tmux セッション `jrvltsql-raceday` を 3 ウィンドウで起動します：

| ウィンドウ | 内容 |
|-----------|------|
| `[0] monitor` | `jltsql realtime start` — RT_ ライブストリーム |
| `[1] scheduler` | `raceday_scheduler.py` — レースごとの自動検証（12R + 事後） |
| `[2] status` | `jltsql status` + `cache info` (watch) |

### Claude Code /loop で自動修正

Claude Code 内で以下を実行すると、検証レポートを読んで問題があれば自動でコードを修正・PR を作成します：

```
/loop 35m
Run python scripts/raceday_verify.py --phase auto, read the JSON report in
data/raceday_report_*.json, and if there are issues: diagnose the root cause,
fix the code, create a branch and PR with gh pr create. Report what you found.
```

### 検証フェーズ

```bat
python scripts/raceday_verify.py --phase pre        # 開催前 (〜10:05)
python scripts/raceday_verify.py --phase rt-check   # レース中 RT_ 確認
python scripts/raceday_verify.py --phase nl-mid     # 後半 NL_+RT_ 確認
python scripts/raceday_verify.py --phase post       # 最終レース後
python scripts/raceday_verify.py --phase final      # 払戻確定後
python scripts/raceday_verify.py --phase quickstart # smoke test
python scripts/raceday_verify.py --phase auto       # 時刻から自動判定
```

---

## キャッシュ

取得したレコードをバイナリ形式でローカルキャッシュします。  
2 回目以降の取得は JV-Link を経由せずキャッシュから読み込むため高速です。

```
data/cache/nl/{SPEC}/{YYYYMMDD}.bin   # NL_ 蓄積系
data/cache/rt/{SPEC}/{YYYYMMDD}.bin   # RT_ リアルタイム系
```

S3 バックアップ設定：

```bat
jltsql cache s3-setup    # S3 認証情報の設定
jltsql cache sync        # 双方向同期
```

---

## ディレクトリ構成

```
jrvltsql/
├── src/
│   ├── cli/main.py          # CLI エントリポイント (jltsql コマンド)
│   ├── fetcher/             # JV-Link データ取得
│   ├── importer/            # DB インポート
│   ├── parser/              # JV-Link レコードパーサー (38種)
│   ├── realtime/            # リアルタイム監視
│   ├── cache/               # バイナリキャッシュ管理
│   └── database/            # SQLite / PostgreSQL ハンドラ
├── scripts/
│   ├── quickstart.py        # 対話型セットアップウィザード
│   ├── raceday_verify.py    # 競馬開催日検証スクリプト
│   ├── raceday_scheduler.py # レース時刻連動スケジューラ
│   └── raceday_tmux.sh      # tmux レースデーセッション
├── tests/                   # pytest (1,178 テスト)
├── quickstart.bat           # Windows ワンクリック起動
└── config/config.yaml       # 設定ファイル
```

---

## テスト

```bat
pytest tests/ -q --ignore=tests/integration/ --ignore=tests/e2e/
```

---

## ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [docs/getting-started/installation.md](docs/getting-started/installation.md) | Windows インストール |
| [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md) | 初回セットアップと日次同期 |
| [docs/getting-started/configuration.md](docs/getting-started/configuration.md) | 設定ファイル |
| [docs/CLI.md](docs/CLI.md) | CLI コマンドリファレンス |
| [CHANGELOG.md](CHANGELOG.md) | 変更履歴 |

---

## ライセンス

[LICENSE](LICENSE) を参照してください。
