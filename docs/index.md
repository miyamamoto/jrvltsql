# JRVLTSQL ドキュメント

JRVLTSQL は、JRA-VAN DataLab の JRA データを SQLite または PostgreSQL に保存する
Windows 向けツールです。NAR / 地方競馬は対象外です。

初めて使う場合は、まず [はじめに](getting_started.md) を読んでください。

## 最初に見る順序

1. [はじめに](getting_started.md): 目的別の実行順序
2. [時系列オッズ](timeseries_odds.md): 公式時系列と開催週速報オッズの違い
3. [PostgreSQL](postgresql.md): PostgreSQL 運用と日次同期
4. [対応データ種別一覧](data_support.md): JVOpen / JVRTOpen spec と保存先
5. [CLI](CLI.md): `jltsql` の主要コマンド
6. [スクリプト一覧](scripts.md): batch / PowerShell の役割
7. [アーキテクチャ](architecture.md): 実装構成

## まず使うコマンド

| 目的 | コマンド |
| --- | --- |
| SQLite でまず作る | `quickstart.bat` |
| SQLite に公式時系列オッズも入れる | `quickstart_timeseries.bat --db sqlite --from <FROM> --to <TO>` |
| PostgreSQL で始める | `quickstart_timeseries.bat --db postgresql --from <FROM> --to <TO>` |
| 既存 PostgreSQL に公式時系列だけ足す | `fetch_timeseries_postgres.bat <FROM> <TO>` |
| 開催週の全賭式速報オッズを蓄積する | `jltsql realtime odds-sokuho-timeseries --from <FROM> --to <TO> --db postgresql` |
| DB 状態を確認する | `jltsql status` |
| 日次同期を手動実行する | `daily_sync.bat --db sqlite` / `daily_sync.bat --db postgresql` |

## 重要な区別

| データ | 保存先 | 注意 |
| --- | --- | --- |
| 通常データ | `NL_*` | 出馬表、成績、払戻、確定オッズなどです。 |
| 確定オッズ | `NL_O1`〜`NL_O6` | レース後の確定オッズです。投資判断時点のオッズではありません。 |
| 公式時系列オッズ | `TS_O1`, `TS_O2` | 単複枠・馬連のみ。JRA-VAN 側の保持は約1年です。 |
| 開催週の速報オッズ | `TS_O1`〜`TS_O6` | 全賭式対応。ただし JRA-VAN 側の保持は約1週間です。 |
| 日次同期 | `daily_sync.bat` | 通常データだけを更新します。時系列オッズは取得しません。 |
