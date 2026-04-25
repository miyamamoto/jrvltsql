# JRVLTSQL

JRA-VAN DataLab データを SQLite/PostgreSQL に取り込む Windows 専用パイプライン。

JRA（中央競馬）専用です。

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

## クイックスタート

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

KPS 運用（PostgreSQL + 時系列オッズ）:

```bat
quickstart_kps_postgres.bat 20250426 20260412
```

`quickstart_kps_postgres.bat` は、KPS が必要とする `RACE` データと `TS_O1〜TS_O6` 時系列オッズを PostgreSQL に投入します。

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
jltsql realtime start --specs 0B12,0B15,0B30,0B31,0B32,0B33,0B34,0B35,0B36
jltsql realtime odds-timeseries --from 20250426 --to 20260412 --db postgresql
jltsql cache info                      # キャッシュ統計
jltsql cache sync --download           # S3 → ローカル同期
jltsql cache sync --upload             # ローカル → S3 同期
```

### KPS向け: PostgreSQL投入

KPS の締切オッズ予測では `TS_O1〜TS_O6` を PostgreSQL に入れてから DuckDB へ取り込みます。初回または期間を指定してまとめて投入する場合:

```bat
quickstart_kps_postgres.bat 20250426 20260412
```

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

`odds-timeseries` は `0B30〜0B36` を一括取得し、`TS_O1〜TS_O6` に保存します。従来の `realtime timeseries --spec ...` も残していますが、KPS では `odds-timeseries` を使います。

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
| [docs/index.md](docs/index.md) | 最小ドキュメント |
| [docs/CLI.md](docs/CLI.md) | CLI 最小リファレンス |
| [CHANGELOG.md](CHANGELOG.md) | 変更履歴 |

---

## ライセンス

[LICENSE](LICENSE) を参照してください。
