# 取得サマリ JSON（daily_update）

`scripts/daily_update.py --summary-json PATH` は、dataspec ごとに「JV-Link に何を送り、何が
返ったか」を JSON で書き出します。下流（collector / scheduler）が機械的に読むための契約です。

0 件の日次同期が成功と見分けられなかった（JVOpen `-1` と `read_count == 0` を「データなし」
として exit 0 にし、戻り値もどこにも残さなかった）ことへの対処です。JVOpen `-1` は
「該当データ無し」のほかに「最新バージョンが公開され、ユーザーが最新バージョンの
ダウンロードを選択した」場合にも返ります（JV-Link インターフェース仕様書 4.9.0.1 p.54）。
そのため `-1` はサーバーが空であることの証明にはならず、このサマリは値を記録するだけで
解釈はしません。

## CLI

| オプション | 意味 |
| --- | --- |
| `--summary-json PATH` | サマリを `PATH` に書く。一時ファイルから `os.replace` で置き換えるので、読み手が途中の状態を見ることはない。すべての終了経路（argparse を含む引数エラー、config / DB 接続の失敗、例外、中断）で書く。書けなかったときは stderr に出し、ほかの例外が起きていなければその `OSError` で終わる |
| `--require-records SPEC[,SPEC]` | 列挙した spec が何も返さなければ exit 3。JVOpen spec は `read_count`（JVOpen が返した対象ファイル数、p.19）が 0 のとき、`0Bxx` spec は読んだレコードが 0 件のとき。skip / error になった spec も満たさない扱い。`--specs` で選んでいない spec を書くと exit 2 |
| `--log-file PATH` | 構造化ログの出力先（相対パスは cwd 基準）。省略時は config の `logging.file.path`、それも無ければ `logs/jltsql.log`。config 由来・既定の相対パスはプロジェクトルート基準（スケジューラの cwd には依存しない） |

どれも省略すると従来どおり動きます（0 件でも exit 0。stdout の
`[daily-sync] SPEC fetched=.. parsed=.. imported=.. failed=..` 行も同じ形のまま）。
変わるのは、構造化ログがファイルに出ることです。spec が何も返さなかったときはログに
WARNING（`daily_update spec returned no data`）を残します。TOKU や非開催日の `0Bxx` は正当に
空になるので stdout / stderr には出さず、「空なら失敗」は `--require-records` で指定します。
ログの出力先に書けないときは stderr に `[daily-sync] WARNING file logging disabled: ..` を出し、
同期は続けます。

### exit code

| code | 意味 |
| --- | --- |
| 0 | 正常終了（`--require-records` が無ければ 0 件でも 0） |
| 1 | 例外（JVOpen エラー、`-2`、取込拒否など）。従来どおり traceback を出す（Ctrl-C は 130） |
| 2 | 引数エラー（argparse が拒否した引数、未知の spec、`--specs` に無い `--require-records` spec）。`--summary-json` には `outcome: "usage_error"` で書く。argparse が拒否した場合は `from_date` / `to_date` が null。`--help` は何も書かない |
| 3 | `--require-records` の spec が何も返さなかった。ほかの spec は最後まで同期し、commit 済み |

## 文書

```json
{
  "schema_version": 1,
  "generator": "jltsql scripts/daily_update.py",
  "jltsql_version": "2.1.2",
  "started_at": "2026-10-11T08:05:00+09:00",
  "finished_at": "2026-10-11T08:05:07+09:00",
  "from_date": "20261010",
  "to_date": "20261011",
  "required_specs": ["RACE"],
  "outcome": "required_records_missing",
  "exit_code": 3,
  "error": null,
  "requirement_failures": [
    {"dataspec": "RACE", "status": "no_data", "read_count": 0}
  ],
  "specs": [
    {
      "kind": "jvopen",
      "dataspec": "RACE",
      "option": 1,
      "from_date": "20261010",
      "to_date": "20261011",
      "status": "no_data",
      "jvopen_code": -1,
      "fromtimes": ["20261010000000-20261011235959"],
      "read_count": 0,
      "download_count": 0,
      "lastfiletimestamp": null,
      "records_read": 0,
      "records_parsed": 0,
      "records_imported": 0,
      "records_failed": 0,
      "records_out_of_range": 0,
      "elapsed_seconds": 4.812,
      "error": null,
      "opens": [
        {
          "fromtime": "20261010000000-20261011235959",
          "jvopen_code": -1,
          "read_count": 0,
          "download_count": 0,
          "lastfiletimestamp": "",
          "recovery": false
        }
      ]
    }
  ]
}
```

### トップレベル

| キー | 型 | 意味 |
| --- | --- | --- |
| `schema_version` | int | 現在 1。キーを足すだけの変更では上げない。意味や型を変えるときに上げる |
| `outcome` | `"ok"` / `"usage_error"` / `"required_records_missing"` / `"error"` | `exit_code` 0 / 2 / 3 / 1（中断なら 130）に対応 |
| `exit_code` | int | プロセスの exit code と同じ値 |
| `error` | string / null | 例外の型と文言（500 文字まで） |
| `required_specs` | string[] | 正規化（大文字）済みの `--require-records` |
| `requirement_failures` | object[] | 満たさなかった spec ごとに `dataspec` / `status` / `read_count`。実行されなかった spec は `status: "not_run"` |
| `specs` | object[] | 実行した順。例外で止まったときは失敗した spec までを含む |

### `specs[]`

| キー | 型 | 意味 |
| --- | --- | --- |
| `kind` | `"jvopen"` / `"jvrtopen"` | 蓄積系（JVOpen）か速報系（`0Bxx`、JVRTOpen） |
| `option` | int / null | 実際に送った JVOpen option（`--force-incremental` と DIFN の setup fallback を適用後）。jvrtopen は null |
| `status` | `"ok"` / `"no_data"` / `"skipped"` / `"error"` | 下表 |
| `jvopen_code` | int / null | 代表の戻り値。最初のエラーコード → 1 つでも 0 なら 0 → すべて -1 なら -1 → open していなければ null。skipped ではスキップの原因になったコード。jvrtopen でも JVRTOpen の戻り値をこのキーに入れる（コード表は p.54 で共通） |
| `fromtimes` | string[] | JVOpen に実際に渡した fromtime。RACE は暦年で刻むので複数になり得る |
| `read_count` / `download_count` | int / null | JVOpen が返した値の合計（p.19）。値を返した open が 1 つも無い（最初の open が例外、JVOpen 前に失敗、jvrtopen）なら null。途中の chunk で失敗したときは、それまでに返った分の合計 |
| `lastfiletimestamp` | string / null | JVOpen が返した中で最も新しい値（p.19）。空文字は null |
| `records_read` | int | JVRead が返したレコード数 |
| `records_parsed` | int | パースして取込に渡したレコード数（`to_date` で落としたぶんを除く） |
| `records_imported` | int / null | DB に書いた行数。error / skipped では null（＝不明）。option 1/2 と 0Bxx は spec 単位でロールバックされるが、option 4（DIFN の setup fallback）は完了した chunk ごとに commit するので、失敗前の chunk の行は DB に残っている |
| `records_failed` | int | パーサ・取込が拒否した件数 |
| `records_out_of_range` | int | パース後、client 側の `to_date` filter で落とした件数 |
| `elapsed_seconds` | number | この spec の所要時間 |
| `error` | string / null | status が error のときの例外 |
| `opens` | object[] | JVOpen 1 回ごとの `fromtime` / `jvopen_code` / `read_count` / `download_count` / `lastfiletimestamp`。jvrtopen は日付キーごとの `key` / `jvrtopen_code`。JVOpen の各要素には `recovery`（bool）があり、JVRead `-402`（p.56）からの自己修復で同じ条件のまま開き直した open は `true`。`recovery: true` の要素は `jvopen_code` / `fromtimes` / `read_count` / `download_count` / `lastfiletimestamp` の集計に入れない |

| status | 条件 |
| --- | --- |
| `ok` | jvopen は `read_count > 0`、jvrtopen は `records_read > 0` |
| `no_data` | 例外なく終わったが上の条件を満たさない（JVOpen `-1`、または `0` かつ対象 0 ファイル） |
| `skipped` | `--ignore-jvopen-error-codes` か、スクリプトが未購読として扱うコード（`SUBSCRIPTION_ERROR_CODES` = `-111` / `-114` / `-115`）で spec を飛ばした。仕様書 p.54 ではこの 3 つはパラメータ不正（dataspec / key / option）であり、購読状態を表すコードではない点に注意 |
| `error` | 例外。プロセスは exit 1 |

JVOpen の `-2`（セットアップダイアログでキャンセル、p.54）は「データなし」ではないので
`error` になります。

### 注意

- `--require-records` が見るのは JVOpen の `read_count`（対象ファイル数）です。ファイルは
  あったが中身がすべて `to_date` より後で落とされた場合（`records_out_of_range` に数える）は
  満たした扱いになります。
- 例外や `--require-records` の失敗時に出す ERROR ログは、console 設定（ERROR 以上）により stdout にも出ます。
  成功時の stdout は変わりません。
- NL キャッシュに完全に当たったときは JVOpen を呼ばないので `opens` は空で `no_data` に
  なります。daily_update はキャッシュを使わないので現状は起きません。
