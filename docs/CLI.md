# CLI Reference

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

主な `option`:

| option | 用途 |
|--------|------|
| 1 | 通常取得 |
| 2 | セットアップ簡易 |
| 3 | セットアップ標準 |
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
| 0B30 | 単勝時系列オッズ |
| 0B31 | 複勝・枠連時系列オッズ |
| 0B32 | 馬連時系列オッズ |
| 0B33 | ワイド時系列オッズ |
| 0B34 | 馬単時系列オッズ |
| 0B35 | 三連複時系列オッズ |
| 0B36 | 三連単時系列オッズ |

## 過去時系列オッズ

KPS 向けには `odds-timeseries` を使います。

```bat
jltsql realtime odds-timeseries --from 20250425 --to 20260425 --db postgresql
```

- JRA-VAN 公式提供範囲は過去1年分です。
- コマンドは `NL_RA` に登録済みのレースを対象にし、JVRTOpen に `YYYYMMDDJJRR` 形式のキーを渡します。
- 保存先は `TS_O1` から `TS_O6` です。
- KPS の締切オッズ予測では `odds-timeseries` を使い、0B30 から O1〜O6 スナップショットを一括取得します。

単一 spec を調査する場合だけ `timeseries --spec` を使います。

```bat
jltsql realtime timeseries --spec 0B30 --from 20250425 --to 20260425 --db-path data/keiba.db
```

## KPS quickstart

PostgreSQL に RACE と TS_O1〜TS_O6 を投入します。

```bat
quickstart_kps_postgres.bat 20250426 20260412
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
