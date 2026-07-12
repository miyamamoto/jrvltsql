# Crawler Audit #1: MING (データマイニング予想) が収集されず DM/脚質が全滅

## 症状（KPS 側の特徴量監査で判明）

KPS 特徴量監査（LOOP10 / LOOP12）で、以下が本番で恒久的に死んでいた:

- **`kyakusitukubun`（今回レース脚質判定）** … raw PostgreSQL `nl_se` で
  **236,791 行中、有効コード('1'〜'4')が 0 行**。値はほぼ全て `@`(0x40) と
  少数の散在 ASCII。NAR `nl_se_nar` も **367,115 行中 0 行**。
- **`dm_*`（マイニング予測タイム/順位）** … KPS `dm_features.py` が参照する
  `nl_dm` は raw PG に **存在するが 0 行**、`nl_dm_nar` は不在。

## 根本原因

SE レコード（`src/parser/se_parser.py`）のフィールド 65〜70 は**マイニング
（DM）ブロック**である:

| # | フィールド | 位置 |
|---|---|---|
| 65 | DMKubun | 445 |
| 66 | DMTime（予想走破タイム） | 446 |
| 67 | DMGosaP | 451 |
| 68 | DMGosaM | 455 |
| 69 | DMJyuni（予想順位） | 459 |
| 70 | **KyakusituKubun（今回レース脚質判定）** | 461 |

これらは JRA-VAN の **MING（データマイニング予想）データスペック**が供給する。
別レコード種別 `DM` → `NL_DM` テーブルも同じ MING 由来。

しかし日次収集スペック（`scripts/daily_update.py` の `UPDATE_SPECS` /
`daily_sync.bat` の `JRA_DAILY_UPDATE_SPECS`）は
**`TOKU,RACE,DIFN,TCVN,RCVN,SLOP,WOOD,0B12,0B15`** のみで **`MING` を含まない**。
そのため:

- `NL_DM` が空 → KPS `dm_*` が生成不可（LOOP12 の 4 列欠落の真因）。
- SE の DM/脚質ブロックが埋まらず、`kyakusitukubun` が無効値のまま
  （LOOP10 の全 NULL の真因）。

実データ検証で SE の他フィールド（`kakuteijyuni`、コーナー通過順位
`jyuni1c..4c`、`ninki`、`honsyokin`）は**正しくパースされている**ため、
パーサのオフセットずれではなく**スペック未収集**が原因と確定。

## 修正（本 PR）

- `UPDATE_SPECS` に `("MING", 1)` を追加（`daily_sync.bat` の既定にも `MING`）。
  `DM`→`NL_DM` の parser/importer/schema は既に実装済み（`importer.py`
  `_table_map["DM"]="NL_DM"`, `schema.py` `NL_DM`）なので、収集さえ行えば
  `NL_DM` が埋まる。
- 未購読時は既存の graceful skip（`not subscribed, skipping spec`）で無害。
- 回帰テスト `test_daily_update_includes_mining_spec` を追加。

## 重要な限界（運用判断が必要）

- MING は**レース当日発表**の商品であり、**過去分の一括 backfill は原則不可**。
  したがって `dm_*` と正しい `kyakusitukubun` は**前向きにのみ**蓄積される。
  過去データ（モデル学習期間）は復元できない。
- ⇒ 学習用の脚質は **LOOP10 のコーナー通過順位フォールバックが正しい恒久解**。
  本 PR は将来データの MING/DM 供給を回復するもので、LOOP10 を置き換えない。
- 実際の収集開始には (a) JRA-VAN のマイニング商品の購読確認、(b) ライブ
  コレクタ（Wine/JV-Link）の再実行が必要。これらは運用操作でありユーザー承認が要る。

## 未対応の関連クローラー所見（次ループ以降）

- **WE レコード（0B14 馬場状態）未取得**（LOOP7）: `nl_we`/`rt_we` 0 行 →
  `babajotai_code_*` が定数。日次スペックに WE 相当が無い件を別途監査。
- **NAR 側**（`jrvltsql-nar`）の脚質/マイニング欠落は UmaConn の提供有無を含め別途。
