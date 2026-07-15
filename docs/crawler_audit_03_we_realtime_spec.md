# クローラ監査 #03: WE（天候馬場状態）速報レコードの未収集とスペック定義の不整合

## 概要

生 PostgreSQL の `nl_we`（0行）/ `rt_we`（0行）が空で、WE レコード
（天候馬場状態）が一度も取り込まれていない。調査の結果、複数の欠陥が
重なっていた。

## 権威ある仕様（JV-Data 4.9.0.1「データ種別一覧」）

JVRTOpen の速報系データ種別ID（正）:

| dataspec | 名称 | レコード |
|----------|------|----------|
| 0B11 | 速報馬体重 | WH |
| 0B12 | 速報レース情報(成績確定後) | RA, SE |
| 0B13 | 速報タイム型データマイニング予想 | DM |
| **0B14** | **速報開催情報(一括)** | **WE（天候馬場状態）** |
| 0B15 | 速報レース情報(出走馬名表～) | RA |
| **0B16** | **速報開催情報(指定)** | **WE（天候馬場状態）** |
| 0B17 | 速報対戦型データマイニング予想 | TM |
| 0B51 | 速報重勝式(WIN5) | WF |

→ WE を供給し `RT_WE` を埋めるのは **0B14 / 0B16 のみ**。ただし 0B14 は
`YYYYMMDD` による一括取得、0B16 は `JVWatchEvent()` のイベントメソッドが返す
リクエストパラメータによる指定取得であり、同じ日付ループでは扱えない。

## 欠陥

1. **`scripts/quickstart.py` の `SPEED_REPORT_SPECS` のラベルが仕様と食い違って
   いた**（本番の既定収集経路）。`0B11` を「開催情報(WE)」と誤記（実際は馬体重
   WH）、`0B14` を「出走取消・除外(AV)」と誤記（実際は WE）、`0B15` を「払戻(HR)」、
   `0B51` を「コース情報(CC)」と誤記。
   dataspec コード自体は fetch に使われるためラベル誤りは直接の収集欠落では
   ないが、誤ラベルは本監査でも混乱を招いた。

2. **`scripts/daily_update.py` の `UPDATE_SPECS` に日付指定用 0B14 が無かった**。
   `daily_sync.bat` の非対話パス（`--no-timeseries --no-realtime` 指定時）で
   使われる。

3. **速報系の投入失敗が成功として集計されていた**（`daily_update.py`）。
   `RealtimeUpdater.process_record()` は失敗時も `{"success": False}` という
   truthy な dict を返すため、`if result:` 判定では PK 不備・insert 失敗も
   `records_imported` に数えられ、`RT_WE` 収集が全滅しても `failed=0` になり得た。

## 本番の実行経路（重要）

`install_tasks.ps1` は `--no-timeseries`/`--no-realtime` を渡さず、
`daily_sync.bat` の既定は `INCLUDE_TIMESERIES=1` / `INCLUDE_REALTIME=1`。
したがって**既定のスケジュールタスクは `quickstart.py`（realtime 経路）を実行**
する（`daily_update.py` は両フラグ 0 の時のみ）。よって本番の WE 収集には
`quickstart.py` の修正が必須で、`daily_update.py` 側は補助経路として合わせて修正。

## 修正

- `scripts/quickstart.py`: `SPEED_REPORT_SPECS` を仕様準拠のラベルへ訂正し、
  日付指定ループには一括取得の `0B14` のみを設定。
- `scripts/daily_update.py`: `UPDATE_SPECS` に `0B14` を追加。投入失敗を
  `success` フラグで正しく `records_failed` に集計するよう修正。
- `daily_sync.bat`: `JRA_DAILY_UPDATE_SPECS` に日付指定用 `0B14` を追加。
- 0B14 は差分ではなく一括スナップショットのため、取得成功後に同一日付の
  `RT_WE` / `RT_AV` / `RT_JC` / `RT_TC` / `RT_CC` を同一トランザクション内で
  削除してから再投入する。後続応答から消えた変更情報を残さない。
- `tests/test_daily_update.py`: 0B14 の収集・選択テスト、および失敗集計の
  回帰テストを追加。

## 影響と限界

- 過去分の学習用馬場状態は RA レコード（field50 芝馬場 / field51 ダート馬場,
  crawler 監査 #02 / PR #131）が供給するため、**ヒストリカル学習は #02 で復旧済み**。
  本件は主にライブの発走前天候・馬場（`RT_WE`）に関わる。
- `0B14`/`0B16` はレース当日発表のため**過去分 backfill は不可**（前向き蓄積）。
- 一日一回のタスクでは開催中に変化する天候・馬場を完全には追随できない
  （厳密なライブ発走前馬場には開催中の定期実行 / realtime monitor への
  0B14 の定期取得と、別経路での JVWatchEvent/0B16 組込みが必要）。本 PR は
  日付指定の 0B14 と集計の正当化に留め、
  実収集開始は JV-Link ライブコレクタの realtime 実行（運用承認）が前提。

## 残課題
- KPS 側で `RT_WE`（発走前馬場）をライブ推論特徴量へ接続（別リポジトリ）。
- 開催中の定期 realtime 実行（運用）の設計。
- NAR（`jrvltsql-nar`）の同等スペック監査。
