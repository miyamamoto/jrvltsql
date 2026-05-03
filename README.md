# JRVLTSQL

JRA-VAN DataLab データを SQLite/PostgreSQL に取り込む Windows 専用パイプライン。

JRA（中央競馬）専用です。

ドキュメント: https://miyamamoto.github.io/jrvltsql/

---

## まず何をすればよいか

| 目的 | まず実行 | 到達点 |
|------|----------|--------|
| SQLite で試す | `quickstart.bat` | JRA の主要データがローカル DB に入ります。 |
| SQLite に公式時系列オッズも入れる | `quickstart.bat` で時系列オッズ取得を選択、または `quickstart.bat --yes --include-timeseries` | SQLite の `TS_O1` / `TS_O2` に公式1年保持の単複枠・馬連時系列オッズが入ります。 |
| PostgreSQL 運用を始める | `quickstart_postgres_timeseries.bat 20250426 20260412` | `RACE` 系データと公式 `TS_O1` / `TS_O2` が入り、日次同期タスク登録まで進めます。 |
| 公式時系列オッズだけ足す | `fetch_timeseries_postgres.bat 20250426 20260412` | 既存 PostgreSQL に `TS_O1` / `TS_O2` だけ追加します。 |
| 三連複・三連単の締切前オッズを残す | `jltsql realtime odds-sokuho-timeseries --from 20260418 --to 20260419 --db postgresql` | 開催週の全賭式オッズが `TS_O1`〜`TS_O6` に入ります。 |
| 日次同期を自動化する | `quickstart.bat` / `quickstart_postgres_timeseries.bat` の最後で登録、または `install_tasks.ps1` | `daily_sync.bat` が Windows タスクとして登録されます。SQLite / PostgreSQL のどちらにも対応します。 |

`daily_sync.bat` は通常データ更新用です。`--db sqlite` / `--db postgresql`
の両方に対応します。公式時系列オッズや全賭式速報オッズを継続蓄積したい場合は、
上のオッズ取得コマンドを別途実行してください。

## どこまで対応しているか

| データ | 対応 | 保存先 | 注意 |
|--------|------|--------|------|
| JRA の出馬表・成績・払戻 | 対応済み | `NL_RA`, `NL_SE`, `NL_HR` など | `quickstart.bat` / `quickstart_postgres_timeseries.bat` で取得します。 |
| 確定オッズ 全賭式 | 対応済み | `NL_O1`〜`NL_O6` | レース後の確定オッズです。投資判断時点のオッズではありません。 |
| 単複枠・馬連の公式時系列オッズ | 対応済み | `TS_O1`, `TS_O2` | `0B41` / `0B42`。JRA-VAN 側の保持は約1年です。 |
| ワイド・馬単・三連複・三連単の締切前オッズ | 開催週の蓄積で対応 | `TS_O3`〜`TS_O6` | `0B30` または `0B33`〜`0B36`。SQLite / PostgreSQL どちらにも保存できます。JRA-VAN 側の保持は約1週間です。 |
| NAR / 地方競馬 | 非対応 | - | このリポジトリは JRA 専用です。 |

---

## 必要要件

| 項目 | 要件 |
|------|------|
| OS | Windows 10 / 11 |
| Python | **3.12 (32-bit)** — JV-Link COM DLL が 32-bit のため必須 |
| JRA-VAN | DataLab 会員登録 + サービスキー |

> **なぜ 32-bit Python?**  
> JV-Link (`JVDTLab.JVLink`) は 32-bit COM DLL として提供されています。64-bit + DllSurrogate は
> セットアップモード (option=3/4) でハング等の不安定な動作が確認されているため、32-bit Python を推奨します。

---

## クイックスタート詳細

一般利用（SQLite 既定）:

```bat
quickstart.bat
```

`quickstart.bat` をダブルクリック（または CMD から実行）するだけで以下を自動処理します：

1. Python (32-bit) の検出
2. S3 キャッシュの事前ダウンロード（オプション）
3. データ取得モードの選択（今週 / 差分 / フルセットアップ）
4. JRA-VAN からのデータ取得・DB 格納
5. S3 キャッシュのアップロード（オプション）
6. DB 検証 (`raceday_verify --phase pre`)
7. SQLite 日次同期タスク登録の実行確認（オプション）

対話形式では、公式1年保持の時系列オッズを取得するか確認されます。
非対話で SQLite に `TS_O1/TS_O2` を入れる場合は以下です。

```bat
quickstart.bat --yes --include-timeseries
```

PostgreSQL + 時系列オッズ:

```bat
quickstart_postgres_timeseries.bat 20250426 20260412
```

`quickstart_postgres_timeseries.bat` は、`RACE` データと公式1年保持の
`TS_O1/TS_O2` 時系列オッズを PostgreSQL に投入します。完了時に
Windows タスクスケジューラへ `daily_sync.bat` を登録するか確認します。
タスクから PostgreSQL に接続する場合は、現在の `POSTGRES_*` 接続情報を
Windows ユーザー環境変数へ保存するかも確認されます。

---

## インストール

```powershell
# PowerShell（ワンライナー）
irm https://raw.githubusercontent.com/miyamamoto/jrvltsql/master/install.ps1 | iex
```

または手動：

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
jltsql realtime start --specs 0B12,0B15,0B30
jltsql realtime odds-timeseries --from 20250426 --to 20260412 --db postgresql
jltsql cache info                      # キャッシュ統計
jltsql cache sync --download           # S3 → ローカル同期
jltsql cache sync --upload             # ローカル → S3 同期
```

### PostgreSQL投入

公式1年保持の `TS_O1/TS_O2` を PostgreSQL にまとめて投入する場合:

```bat
quickstart_postgres_timeseries.bat 20250426 20260412
```

`quickstart.bat` から PostgreSQL 専用セットアップは呼びません。SQLite と
PostgreSQL の導線を分けるため、PostgreSQL 運用を始める場合は
`quickstart_postgres_timeseries.bat` を直接実行してください。

既に `NL_RA` が入っていて時系列オッズだけを追加する場合:

```bat
fetch_timeseries_postgres.bat 20250426 20260412
```

日付を省略した場合は今日から過去365日分を取得します。

```bat
fetch_timeseries_postgres.bat
```

直接 CLI を使う場合:

```bat
jltsql realtime odds-timeseries --from <FROM> --to <TO> --db postgresql
```

SQLite に保存する場合:

```bat
jltsql realtime odds-timeseries --from <FROM> --to <TO> --db sqlite --db-path data/keiba.db
```

`odds-timeseries` は `0B41/0B42` で公式1年保持の単複枠・馬連時系列を取得し、`TS_O1/TS_O2` に保存します。`0B30` の全賭式速報オッズは1週間保持なので、開催週に蓄積する場合だけ `realtime odds-sokuho-timeseries` を使います。

### Windows タスク登録

`daily_sync.bat` は SQLite / PostgreSQL の両方に対応しています。
`quickstart.bat` の最後では SQLite 用、`quickstart_postgres_timeseries.bat`
の最後では PostgreSQL 用として Windows タスクスケジューラに登録するか確認されます。
手動で登録する場合は以下を実行します。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File install_tasks.ps1 -DbType sqlite -Time 06:30
powershell -NoProfile -ExecutionPolicy Bypass -File install_tasks.ps1 -DbType postgresql -Time 06:30
```

`POSTGRES_PASSWORD` などを現在の CMD セッションだけで設定している場合、
タスク実行時には見えません。登録時の確認で `POSTGRES_*` を Windows
ユーザー環境変数へ保存するか、あらかじめ永続的な環境変数として設定してください。

### fetch オプション

| option | 内容 |
|--------|------|
| 1 | 通常取得（差分） |
| 2 | 今週データ |
| 3 | セットアップ |
| 4 | 分割セットアップ |

---

## ドキュメント

- [アーキテクチャ](docs/architecture.md)
- [CLI](docs/CLI.md)
- [対応データ種別一覧](docs/data_support.md)
- [PostgreSQL](docs/postgresql.md)
- [時系列オッズ](docs/timeseries_odds.md)
- [スクリプト一覧](docs/scripts.md)

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
| [docs/index.md](docs/index.md) | 最小ドキュメント |
| [docs/CLI.md](docs/CLI.md) | CLI 最小リファレンス |
| [CHANGELOG.md](CHANGELOG.md) | 変更履歴 |

---

## ライセンス

[LICENSE](LICENSE) を参照してください。
