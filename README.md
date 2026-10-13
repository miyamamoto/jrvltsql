# JRVLTSQL

JRVLTSQL は、JRA-VAN DataLab の中央競馬（JRA）データを JV-Link で取得し、
SQLite または PostgreSQL に保存するツールです。コマンド名は `jltsql` です。
地方競馬（NAR）は対象外です。

公開ドキュメント: https://miyamamoto.github.io/jrvltsql/

## 何を保存できるか

JV-Link（JRA-VAN が配布する Windows 用のデータ取得部品）には 2 種類の取得口があります。

| 種類 | JV-Link の関数 | 主な内容 | 保存先の例 |
| --- | --- | --- | --- |
| 蓄積系 | `JVOpen` | 出馬表、成績、払戻、確定オッズ、マスタ（馬・騎手など）、血統、調教 | `NL_RA`, `NL_SE`, `NL_HR`, `NL_O1`〜`NL_O6`, `NL_UM` |
| 速報系 | `JVRTOpen` | 当日の速報（馬体重・開催情報・結果など）、締切前のオッズ | `RT_*`, `TS_O1`, `TS_O2`, `TS_SOKUHO_O1`〜`TS_SOKUHO_O6` |

オッズは 3 種類あり、意味が違います。

| データ | 保存先 | 内容 | JRA-VAN 側の保持期間 |
| --- | --- | --- | --- |
| 確定オッズ | `NL_O1`〜`NL_O6` | レース後の確定値。投資判断の時点のオッズではありません。 | — |
| 公式時系列オッズ（`0B41` / `0B42`） | `TS_O1`, `TS_O2` | 単勝・複勝・枠連と馬連だけ | 約 1 年 |
| 速報オッズ（`0B30`〜`0B36`） | `TS_SOKUHO_O1`〜`TS_SOKUHO_O6` | 全賭式 | 約 1 週間 |

データ種別ごとの対応表は [対応データ種別一覧](docs/data_support.md)、
レコードごとの主キーや移行手順は [レコード別の公式契約と移行手順](docs/record_contracts.md) にあります。

## 前提

| 項目 | 要件 |
| --- | --- |
| 契約 | JRA-VAN DataLab の利用契約とサービスキー |
| JV-Link | インストール・利用規約への同意・サービスキー登録は人が行います。このリポジトリは代行しません。 |
| OS | Windows 10 / 11、または x86_64 の Linux + Docker（Wine で JV-Link を動かす） |
| Python | 3.12 以上。Windows の batch は 32-bit の Python 3.12 以上を要求します。 |
| PostgreSQL | PostgreSQL に保存する場合だけ |

- リリースで検証しているのは 32-bit の JV-Link です。64-bit の実行経路は未検証です。
- ARM（Apple Silicon など）では動きません。JV-Link が 32-bit x86 のためです。
  詳しくは [Wine/Docker](docs/wine_docker.md)。
- JV-Link が未登録なら、取得は理由を出して止まります。

## インストール

運用環境では、正式リリースの tag を固定してインストールします。
現在の安定版は `v2.3.2` です。

```powershell
git clone --branch v2.3.2 --depth 1 https://github.com/miyamamoto/jrvltsql.git
cd jrvltsql
git rev-parse HEAD
pip install .
```

採用したら、次の 2 つを運用記録に残してください。

- `git rev-parse HEAD` が出した full SHA（40 桁のコミット ID）
- 使った配布物（artifact）の SHA-256

[GitHub Release](https://github.com/miyamamoto/jrvltsql/releases/tag/v2.3.2) には
wheel（`jltsql-2.3.2-py3-none-any.whl`）と sdist（`jltsql-2.3.2.tar.gz`）があります。
wheel に入るのは `jltsql` コマンド（`src/`）だけです。`quickstart.bat` などの batch や
`scripts/daily_update.py` を使う場合は、上の手順で tag を clone してください。

次の 2 つは常に `master` の最新へ更新するので、運用環境では使いません。

- `install.ps1`（one-command installer。既存の checkout も `master` へ更新します）
- `jltsql update`

採用とロールバックの規則は [リリース運用方針](docs/release_policy.md) にあります。

## アップグレード

既存の DB を 2.3.2 で使う前に、DB を作った版に応じて移行が要ります。
移行は自動では行いません。どの手順も、先に書き込み中の collector をすべて止め、
バックアップを取ってから行います。

| DB を作った版 | 2.3.2 の前に必要なこと |
| --- | --- |
| 2.3.1 | DB の移行はなし（終了コードが変わる。下の注意を参照） |
| 2.3.0 | `TS_SOKUHO_O*` の主キーに `CollectedAt` を戻す拡幅。行は消えません。 |
| 2.2.0 | 上の行に加えて、`RT_WH` の主キーに `HappyoTime` を足す移行 |
| 2.0.0〜2.1.2 | 上の 2 つに加えて、`NL_HR` / `RT_HR` の予備 flag 3 列の型変更（INTEGER → TEXT） |
| 1.x、2.0.0 の pre-release | DB の作り直しと再取込（v2 は schema の境界） |

手順はそれぞれ [RELEASE_NOTES.md](RELEASE_NOTES.md) の次の節にあります。

| 移行 | 節 | 移行しないとどうなるか |
| --- | --- | --- |
| `TS_SOKUHO_O*` の拡幅 | [Upgrade to 2.3.1 (TS_SOKUHO)](RELEASE_NOTES.md#upgrade-to-231-ts_sokuho) | 起動と書き込みが止まる |
| `RT_WH` の主キー | [Upgrade from 2.2.0](RELEASE_NOTES.md#upgrade-from-220-operator-migration-for-rt_wh) | `0B11`（速報馬体重）の取得と `RT_WH` への書き込みだけが止まる |
| HR flag 3 列の型 | [Upgrade from 2.1.2](RELEASE_NOTES.md#upgrade-from-212-migration-required) | HR の取込が拒否される |
| 1.x からの作り直し | [Required database migration](RELEASE_NOTES.md#required-database-migration) | — |

注意:

- `TS_SOKUHO_O*` の拡幅は、PostgreSQL では `jltsql db migrate-sokuho-capture-identity` で行います。
  既定は報告だけ（dry run）で、`--apply` を付けたときだけ変更します。
  SQLite では使えません。バックアップを取って表を作り直します。
- 1.x で作った `TS_SOKUHO_O*` は、すでに 2.3.1 以降と同じ主キーです。
  2.0〜2.3.0 の `migrate-sokuho-capture-identity --apply` を当ててはいけません（行が消えます）。
- `RT_WH` の移行後は、同じ馬に発表ごとの行ができます。`RT_WH` を読む側の変更も要ります。
- 2.3.2 では、時系列オッズのコマンド（`realtime timeseries` / `odds-timeseries` /
  `odds-sokuho-timeseries`）が、一部のレースで取得に失敗したとき exit 4 で終わります
  （2.3.1 までは exit 0）。呼び出す側が exit 0 以外を失敗として扱うなら、その動きも変わります。
  たとえば日付を区切って順に取得する呼び出し側が、exit 0 以外でその区切りを失敗にして止まる場合は、
  失敗した日付を取り直す手順を用意してください。

## 使い方

### Windows: まず SQLite で動かす

```bat
quickstart.bat
```

出馬表・成績・払戻・確定オッズなどが `data\keiba.db` に入ります。
最後に、日次同期を Windows タスクスケジューラへ登録するか聞かれます。

### 目的別のコマンド

| 目的 | コマンド |
| --- | --- |
| 範囲を指定して、通常データと公式時系列オッズを入れる | `quickstart_timeseries.bat --db sqlite --from 20250426 --to 20260412`（PostgreSQL は `--db postgresql`） |
| 日次同期を手動で回す | `daily_sync.bat --db sqlite --days-back 7 --days-forward 3` |
| 日次同期を Windows タスクに登録する | `powershell -NoProfile -ExecutionPolicy Bypass -File install_tasks.ps1 -DbType sqlite -Time 06:30` |
| 蓄積系を spec を指定して取る | `jltsql fetch --from 20240101 --to 20241231 --spec RACE` |
| 開催週の速報オッズ（全賭式）を取る | `jltsql realtime odds-sokuho-timeseries --from 20260418 --to 20260419 --db postgresql` |
| 当日の速報を 1 回だけ取る | `jltsql realtime fetch --specs 0B11,0B14 --date 20261011 --summary-json rt.json` |

- `daily_sync.bat` の既定の保存先は PostgreSQL です。通常データに加えて、
  公式時系列オッズと開催週の速報も取ります。通常データだけなら `--no-timeseries --no-realtime` を付けます。
- `quickstart_timeseries.bat` で `--from` / `--to` を省くと、今日から過去 365 日が対象です。
- batch の一覧は [スクリプト一覧](docs/scripts.md)、判断の流れは [はじめに](docs/getting_started.md) にあります。

### `jltsql` コマンド

`jltsql init` が、今いるディレクトリに `config/config.yaml`、`data/`、`logs/` を作ります。
ほかのサブコマンドはこの設定ファイルを読みます（`--help` も同じ）。
別の場所の設定は `jltsql -c <path>` で指定します。

```bash
jltsql init
jltsql status
jltsql fetch --from 20260101 --to 20260417 --spec RACE
jltsql --help
```

すべてのオプションは [CLI](docs/CLI.md) にあります。

### PostgreSQL に保存する

設定ファイルの `databases.postgresql` は環境変数 `POSTGRES_HOST` / `POSTGRES_USER` /
`POSTGRES_PASSWORD` を読みます。batch（`daily_sync.bat` など）は、さらに
`POSTGRES_PORT` / `POSTGRES_DATABASE` も読みます。

```bat
set POSTGRES_HOST=127.0.0.1
set POSTGRES_PORT=5432
set POSTGRES_DATABASE=keiba_dev
set POSTGRES_USER=ingestion_writer
set POSTGRES_PASSWORD=<password>
quickstart_timeseries.bat --db postgresql --from 20250426 --to 20260412
```

詳しくは [PostgreSQL](docs/postgresql.md)。

### Linux（Docker + Wine）

イメージには Wine、32-bit の bridge、ブラウザから操作する画面（noVNC）が入っています。

```bash
docker compose up -d jltsql
```

1. ブラウザで `http://localhost:6080/vnc.html` を開きます（`127.0.0.1` にだけ公開しています。
   別のホストからは `ssh -L 6080:localhost:6080` で転送します）。
2. その画面で JV-Link をインストールし、規約に同意し、サービスキーを入力します。
   手順は [JV-Link 手動登録](docs/jvlink_manual_registration.md) にあります。
3. 登録後は Windows と同じコマンドを使います。

```bash
docker compose exec jltsql jltsql init
docker compose exec jltsql jltsql fetch --spec RACE --from 20260101 --to 20260417
```

取得中に JV-Link が確認ダイアログを出すと、人が答えるまで取得は進みません。
無人で流すときだけ `JVLINK_AUTO_CLOSE_DIALOGS=1` を明示すると、既知のダイアログを
Escape で拒否します（承諾はしません）。応答待ちの上限は `JVLINK_OPEN_TIMEOUT_SECONDS`
（1〜86400 秒）で変えられます。詳しくは [Wine/Docker](docs/wine_docker.md)。

## 終了コードと失敗の扱い

| コマンド | 終了コード |
| --- | --- |
| `scripts/daily_update.py` | 0 正常、1 エラー、2 引数の誤り、3 `--require-records` の spec が何も返さなかった |
| `jltsql realtime fetch` | `daily_update.py` と同じ |
| `jltsql fetch` | 0 正常、1 エラー、2 必須オプションの欠落などの引数の誤り。途中の spec が失敗したら、残りの spec は実行しません。 |
| `jltsql realtime timeseries` / `odds-timeseries` / `odds-sokuho-timeseries` | 0 正常、1 エラー、2 引数の誤り、4 一部のレースで取得（JVRTOpen）に失敗した（2.3.2 以降） |

- 0 件でも、`--require-records` を付けなければ exit 0 です。「空なら失敗」にしたい spec を
  `--require-records` に書きます。
- JVOpen の戻り値 `-1` は「該当データ無し」以外の意味も持つので、空であることの証明にはしません。
- `--summary-json PATH` を付けると、spec ごとの戻り値と件数を JSON に書きます（失敗時も書きます）。
  形式は [取得サマリ JSON](docs/fetch_summary.md)。
- 時系列オッズのコマンドは、取得に失敗したレースがあっても全 spec を取り終え、取れた分を保存してから
  exit 4 で終わります。失敗の数は出力の `Failed keys:` 行に spec ごとに `0B42=184` の形で出ます
  （失敗がなければ `0`）。その日付を取り直してください。
- データが無いレース（中止など）は失敗に数えません。
- 2.3.1 までは、取得に失敗したレースがあっても exit 0 でした。

## 開発・テスト

```bash
pip install -e ".[dev,postgres]"
pytest tests --ignore=tests/integration --ignore=tests/e2e -m "not slow" -q
```

- テストに JV-Link は要りません。Docker イメージには実行時の依存しか入っていないので、
  テストはリポジトリ側で実行します。
- PostgreSQL を使うテストは `JLTSQL_RUN_POSTGRESQL_INTEGRATION=1` を付けたときだけ走ります。
- 構成は [アーキテクチャ](docs/architecture.md)、変更履歴は [CHANGELOG.md](CHANGELOG.md) と
  [RELEASE_NOTES.md](RELEASE_NOTES.md) にあります。

## ライセンスと利用規約

- このリポジトリのコードは Apache License 2.0 です（[LICENSE](LICENSE)）。
- JV-Link と、取得したデータの扱いは、JRA-VAN DataLab の利用規約に従ってください。
