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

主な `spec`:

| spec | 用途 |
|------|------|
| RACE | レース・出走馬・結果 |
| DIFF / DIFN | 差分 |
| O1-O6 | 確定オッズ |
| MING | データマイニング予想 |

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
- `0B41/0B42` は公式仕様上の保存期間が 1年間です。
- 0B30〜0B36 は速報オッズで、公式仕様上の保存期間は 1週間です。
- コマンドは `NL_RA` に登録済みのレースを対象にし、JVRTOpen に `YYYYMMDDJJRR` 形式のキーを渡します。
- `0B30` は全賭式を返すため、JVRead の各レコード先頭 `O1`〜`O6` を見て `TS_O1`〜`TS_O6` へ振り分けます。ただし過去取得は1週間までです。
- 特定時刻を指定して取得することはできません。全時系列を取得し、保存後に `HassoTime` で必要時刻を抽出します。
- ワイド・馬単・三連複・三連単の長期締切前オッズ評価に使う場合は、開催週に `odds-sokuho-timeseries` で継続蓄積してください。

単一 spec を調査する場合だけ `timeseries --spec` を使います。

```bat
jltsql realtime timeseries --spec 0B41,0B42 --from 20250425 --to 20260425 --db-path data/keiba.db
jltsql realtime odds-sokuho-timeseries --from 20260418 --to 20260419 --db postgresql
```

## PostgreSQL 時系列オッズ quickstart

PostgreSQL に RACE と公式1年保持の TS_O1/TS_O2 を投入します。

```bat
quickstart_postgres_timeseries.bat 20250426 20260412
```

`quickstart.bat` からも通常セットアップ完了後にこの処理を続けて実行できます。
`quickstart_postgres_timeseries.bat` の最後では、`daily_sync.bat` を
 Windows タスクスケジューラに登録するか確認します。

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
