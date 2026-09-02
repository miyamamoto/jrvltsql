# CLI リファレンス

現在使うコマンドだけを記載します。正確なオプション一覧は、実行環境で `jltsql --help` または各サブコマンドの `--help` を確認してください。

## 初期化・確認

```bat
jltsql status
jltsql create-tables
jltsql create-indexes
```

## 蓄積データ取得

```bat
jltsql fetch --from 20260101 --to 20260417 --spec RACE --option 1
```

対応済みの `JVOpen` / `JVRTOpen` spec、保存先テーブル、運用コマンドは
[対応データ種別一覧](data_support.md) を参照してください。

主な `option`:

| option | 用途 |
|--------|------|
| 1 | 通常取得（差分） |
| 2 | 今週データ |
| 3 | セットアップ |
| 4 | 分割セットアップ |

`option 4` は長期間をまとめて取得するため、一定件数ごとにコミットします。途中で中断しても、
そこまでに取り込んだぶんは残ります。

実機で範囲形式 `fromtime` を確認済みの `RACE`（option `1` / `3` / `4`）は、
`--from`〜`--to` を暦年で刻んで `JVOpen` を繰り返します。1 回の `JVOpen` に並ぶ
対象ファイル数が `JVRead` 1 回の費用を決めるためで、`--to` はそのまま download 範囲の
終端になります。option `2` は `RACE` でも start-only です。終了時刻を指定できない spec
（`TOKU` / `DIFN` / `HOSN` / `HOYU` / `COMM` など）と、range挙動を実機確認していない
spec（`SLOP` / `WOOD` を含む）も、安全側で start-only `JVOpen` を 1 回だけ使います。
start-onlyの場合の `--to` は取得後の client-side filterです。option `3` / `4` は要求開始日の
直前 `23:59:59`、option `1` / `2` は要求開始日の `00:00:00` を開始cursorに使います。
複数年setupは数時間かかり得るため、配備側では監視可能な有限の
`JVLINK_OPEN_TIMEOUT_SECONDS`（1〜86,400秒、既定120秒）を指定できます。

主な `spec`:

| spec | 用途 |
|------|------|
| RACE | レース・出走馬・結果・確定オッズ（`O1`〜`O6`レコードを含む） |
| DIFN | 差分（旧名 `DIFF` は受け付けません） |
| MING | データマイニング予想 |

`O1`〜`O6` はレコード種別IDで、単独の `JVOpen` specではありません。
確定オッズは `--spec RACE` で取得します。同じoptionで有効な4文字specは
`--spec RACEDIFN` のように連結できます。

## リアルタイム取得

```bat
jltsql realtime start --specs 0B12,0B15,0B30
jltsql realtime specs
```

主な `JVRTOpen` spec:

| spec | 用途 |
|------|------|
| 0B12 | レース情報・払戻 |
| 0B15 | レース情報 |
| 0B30 | 速報オッズ（全賭式、1週間） |
| 0B31 | 速報オッズ（単複枠、1週間） |
| 0B32 | 速報オッズ（馬連、1週間） |
| 0B33 | 速報オッズ（ワイド、1週間） |
| 0B34 | 速報オッズ（馬単、1週間） |
| 0B35 | 速報オッズ（三連複、1週間） |
| 0B36 | 速報オッズ（三連単、1週間） |
| 0B41 | 時系列オッズ（単複枠、1年） |
| 0B42 | 時系列オッズ（馬連、1年） |

## 過去時系列オッズ

公式1年保持の単複枠・馬連時系列オッズは `odds-timeseries` で取得します。

```bat
jltsql realtime odds-timeseries --from 20250425 --to 20260425 --db postgresql
```

- `odds-timeseries` は `0B41/0B42` を取得し、`TS_O1/TS_O2` に保存します。
- `--spec` で片方だけを指定できます。公式長期時系列ではない `0B30`〜`0B36` や
  その他の spec は、この alias では nonzero で拒否します。
- `0B41/0B42` は公式仕様上の保存期間が 1年間です。
- 0B30〜0B36 は速報オッズで、公式仕様上の保存期間は 1週間です。
- コマンドは `NL_RA` に登録済みのレースを対象にし、JVRTOpen に `YYYYMMDDJJRR` 形式のキーを渡します。
- `0B30` は全賭式を返すため、JVRead の各レコード先頭 `O1`〜`O6` を見て `TS_SOKUHO_O1`〜`TS_SOKUHO_O6` へ振り分けます。ただし過去取得は1週間までです。
- 特定時刻を指定して取得することはできません。全時系列を取得し、保存後に `HassoTime` で必要時刻を抽出します。
- ワイド・馬単・三連複・三連単の長期締切前オッズ評価に使う場合は、開催週に `odds-sokuho-timeseries` で継続蓄積してください。

単一 spec を調査する場合だけ `timeseries --spec` を使います。

```bat
jltsql realtime timeseries --spec 0B41,0B42 --from 20250425 --to 20260425 --db-path data/keiba.db
jltsql realtime odds-sokuho-timeseries --from 20260418 --to 20260419 --db postgresql
jltsql realtime odds-sokuho-timeseries --from 20260418 --to 20260419 --db sqlite --db-path data/keiba.db
```

## TS_SOKUHO 主キーの明示移行

旧版で作成した `TS_SOKUHO_O1`〜`TS_SOKUHO_O6` の主キー末尾に
`CollectedAt` が残っている場合、通常の起動・テーブル準備・時系列オッズ書き込みは
自動移行せず停止します。PostgreSQL のエラーには対象テーブルと、最初に実行する
読み取り専用 dry run の exact command が表示されます。この command に `--apply` は
含まれず、データを変更しません。SQLite のエラーは in-place 移行コマンドを案内せず、
backup と現行 schema での table 再構築を指示します。

既定は読み取り専用の dry run です。全テーブルを検査する場合:

```bat
jltsql db migrate-sokuho-capture-identity --db postgresql
```

対象を限定するには `--table` を繰り返します。dry run は各テーブルについて、現在の
主キー、総行数、発表単位の distinct group 数、削除予定行数、保持行の
`CollectedAt` を最古の非 NULL 値へ書き換える group 数を表示します。読み取り専用
transaction を使い、`ACCESS EXCLUSIVE` lock は取得しません。

```bat
jltsql db migrate-sokuho-capture-identity --db postgresql --table TS_SOKUHO_O1 --table TS_SOKUHO_O2
```

対象が PostgreSQL の search path 外にある場合は schema を明示します。エラーに
表示される exact dry-run command にも `--schema` が含まれます。

```bat
jltsql db migrate-sokuho-capture-identity --db postgresql --schema archive --table TS_SOKUHO_O2
```

内容を確認し、すべての collector / writer を停止してから、同じ command に
`--apply` を明示します。データを変更するのは `--apply` を付けた実行だけです。

```bat
jltsql db migrate-sokuho-capture-identity --db postgresql --schema archive --table TS_SOKUHO_O2 --apply
```

apply は指定した legacy table を1 transaction で処理し、grouping snapshot より前に
`ACCESS EXCLUSIVE` lock を取得します。同じ発表の行は、最新 poll の列値と最古の
非 NULL `CollectedAt` を持つ1行へ統合します。時刻検証、保持行数検証、DDL の
いずれかが失敗すると全テーブルを rollback し、nonzero で終了します。

SQLite に同じコマンドを実行しても database connection を開かず、in-place 移行は
行わず nonzero で拒否します。
SQLite は先に database をバックアップし、現行 schema で対象 table を再構築して
ください。公式1年時系列の `TS_O1` / `TS_O2` はこの移行の対象外です。

当日ライブ収集で全レースを再取得しない場合は、`odds-timeseries` にレースレコードの
発走時刻ウィンドウを明示します。次の例は、現在時刻（JST）から30分以内に発走し、
発走後2分を超えていないレースだけを対象にします。

```bat
jltsql realtime odds-timeseries --spec 0B41 --from 20260901 --to 20260901 --db postgresql --post-time-within-minutes 30 --post-time-not-past-minutes 2
```

両オプションの既定値は無効です。どちらかを指定した場合、`NL_RA` / `RT_RA` の
日付だけで有効な bound の完全な範囲外と確定できるキーを先に除外し、残る候補の
`HassoTime`（レースの発走時刻）を使います。候補で発走時刻が欠損、strict な4桁
`HHMM` として解釈不能、または同じ取得キー内で不一致の場合は、該当キーを表示して
JV-Link を開く前に停止します。日付で除外済みのキーの発走時刻は解釈しません。
表示する `considered` / `candidates` / `kept` / `future` / `past` / `date_excluded` は
それぞれ全キー、発走時刻を評価した候補、保持数、理由別除外数、日付だけで除外した
数です。
これは取得後のオッズ行にある `HassoTime`（発表時刻）とは別の値です。
ウィンドウ指定時に `--from` / `--to` を省略した場合の既定日付も JST で決めます。

## 範囲指定つき時系列オッズ quickstart

SQLite / PostgreSQL に、指定範囲の通常データと公式1年保持の TS_O1/TS_O2 を投入します。

```bat
quickstart_timeseries.bat --db postgresql --from 20250426 --to 20260412
quickstart_timeseries.bat --db sqlite --from 20250426 --to 20260412
```

範囲指定つき時系列 quickstart は SQLite / PostgreSQL とも `quickstart_timeseries.bat` を使います。
`quickstart_timeseries.bat` の最後では、`daily_sync.bat` を
Windows タスクスケジューラに登録するか確認します。

SQLite に公式時系列オッズを保存する場合は、通常 quickstart に
対話形式で時系列オッズ取得を選ぶか、非対話では `--yes --include-timeseries`
を付けます。CLI で直接取得する場合は `--db sqlite` を指定します。

```bat
quickstart.bat --yes --include-timeseries
jltsql realtime odds-timeseries --from 20250426 --to 20260412 --db sqlite --db-path data/keiba.db
```

既に RACE / NL_RA がある場合は、時系列オッズだけ追加します。

```bat
fetch_timeseries_postgres.bat 20250426 20260412
```

## キャッシュ

```bat
jltsql cache info
jltsql cache sync --download
jltsql cache sync --upload
```

## レースデー検証

```bat
python scripts/raceday_verify.py --phase pre
python scripts/raceday_verify.py --phase rt-check
python scripts/raceday_verify.py --phase post
python scripts/raceday_verify.py --phase final
python scripts/raceday_verify.py --phase auto
```
