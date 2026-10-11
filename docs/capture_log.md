# 速報の取得ログ（0B11 / 0B14）

`scripts/daily_update.py` は 2.3.0 から、速報馬体重 `0B11` と速報開催情報(一括)
`0B14` を取得するたびに、JVRTOpen 1 回ごとの記録と JVRead が返したレコードを
**追記型**の 2 表に残します。

| 表 | 1 行の単位 | 主キー |
| --- | --- | --- |
| `RT_CAPTURE_FETCH` | JVRTOpen 1 回（dataspec × 要求キー） | `FetchId` |
| `RT_CAPTURE_RECORD` | JVRead が返したバッファ 1 つ | `FetchId`, `Seq` |

## なぜ別の表か

`RT_WH` / `RT_WE` / `RT_AV` / `RT_JC` / `RT_TC` / `RT_CC` は**現在状態**です。

- `0B14` は開催日単位の完全な snapshot で、取り消された変更は以後の応答から
  消えます。JV-Data 仕様書 4.9.0.1「データ提供タイミング・提供単位」※1 は
  「取得する度に前回取得の情報を破棄し、データ取得時点で含まれている情報のみを
  利用」するよう求めているので、jltsql は取得ごとに当該日の 5 表を置き換えます
  （[0B14 の日単位 snapshot 置換と 0B16](record_contracts.md#0b14-snapshot-0b16)）。
  この置換は 2.3.0 でも変えていません。
- `0B11` は発走約 1 時間前から「馬体重が発表される毎にレコード追加・更新」されます。
  2.3.0 から `RT_WH` は発表時刻 `HappyoTime` を主キーに含み、発表ごとに行が残ります
  （[WH](record_contracts.md#wh)）。

どちらの表にも「jltsql がいつその値を受け取ったか」は残りません。発走前のある時刻に
何が分かっていたか（取消された騎手変更や、後から訂正された馬体重を含む）を後から
再現するには、受け取った時刻つきの記録が要ります。それがこの 2 表です。jltsql は
この 2 表に INSERT しかしません（置換・削除しない）。

## `RT_CAPTURE_FETCH`

| 列 | 型 | 意味 |
| --- | --- | --- |
| `FetchId` | TEXT | この取得の ID（UUID4 の 32 桁 hex）。`--summary-json` の `specs[].opens[].fetch_id` と同じ値 |
| `DataSpec` | TEXT | `0B11` / `0B14` |
| `RequestKey` | TEXT | JVRTOpen に渡したキー（`YYYYMMDD`、開催日単位） |
| `Status` | TEXT | `complete`（JVRTOpen `0` で JVRead が `0` まで読めた）/ `no_data`（JVRTOpen `-1`） |
| `JVRTOpenCode` | INTEGER | JVRTOpen の戻り値（JV-Link IF 4.9.0.1 p.22, p.54） |
| `RecordCount` | INTEGER | この取得で JVRead が返したバッファ数（＝`RT_CAPTURE_RECORD` の行数） |
| `RequestedAt` | TEXT | JVRTOpen を呼ぶ直前の時刻 |
| `OpenedAt` | TEXT | JVRTOpen が戻った時刻（IF p.23: データの受信を完了した時点で戻る） |
| `CompletedAt` | TEXT | JVRead が `0`（全レコード読込終了）を返した後の時刻。`no_data` では `OpenedAt` の直後。commit より前の時刻で、行が DB で見えるようになるのは spec の commit 後 |
| `Producer` | TEXT | 書いたプログラム（例 `jltsql scripts/daily_update.py`） |
| `JltsqlVersion` | TEXT | jltsql の version |

## `RT_CAPTURE_RECORD`

| 列 | 型 | 意味 |
| --- | --- | --- |
| `FetchId` | TEXT | `RT_CAPTURE_FETCH.FetchId` |
| `Seq` | INTEGER | その取得の中での 1 始まりの通し番号（JVRead の順） |
| `CollectedAt` | TEXT | JVRead がこのバッファを返した時刻 |
| `DataSpec` / `RequestKey` | TEXT | `RT_CAPTURE_FETCH` と同じ |
| `RecordSpec` / `DataKubun` / `MakeDate` | TEXT | レコード先頭 11 バイト（全形式共通のヘッダ） |
| `Year` / `MonthDay` / `JyoCD` / `Kaiji` / `Nichiji` / `RaceNum` / `HappyoTime` / `HenkoID` / `Umaban` | TEXT | 生バイトの公式位置からそのまま切り出したキー項目（下表）。その形式に無い項目は NULL |
| `RawEncoding` | TEXT | `cp932`（通常）。CP932 として読めないバイト列、CP932 で読めても同じバイト列に戻らないもの（NEC/IBM 拡張の重複コード。例 `0x8790` と `0x81E0` はどちらも「≒」、`0xFBFC` と `0xEEE0` はどちらも「髙」）、NUL（`0x00`、PostgreSQL の TEXT に入らない）を含むものは `hex` |
| `RawRecord` | TEXT | 受け取ったレコード全体（末尾 CR/LF を含む）。`RawEncoding` で元のバイト列に戻る |
| `RawSha256` | TEXT | 元のバイト列の SHA-256 |
| `RowsJson` | TEXT | jltsql のパーサ出力（WH は馬ごとの行の配列、ほかは 1 要素）。`_` で始まる内部キーを除く。パースできなければ NULL。**RT_* に書いた行そのものではない**（型変換・正規化の前の値で、パーサによって文字列と数値が混ざる）。正本は `RawRecord` |

キー項目の位置（JV-Data 仕様書 4.9.0.1 フォーマット 101〜106、1 始まり）:

| 種別 | 開催年〜日次 | レース番号 | 発表月日時分 | その他 |
| --- | --- | --- | --- | --- |
| `WH` 馬体重 | 12–25 | 26–27 | 28–35 | 18 頭分を持つので `Umaban` は NULL |
| `WE` 天候馬場状態 | 12–25 | なし | 26–33 | `HenkoID` 34 |
| `AV` 出走取消・競走除外 | 12–25 | 26–27 | 28–35 | `Umaban` 36–37 |
| `JC` 騎手変更 | 12–25 | 26–27 | 28–35 | `Umaban` 36–37 |
| `TC` 発走時刻変更 | 12–25 | 26–27 | 28–35 | |
| `CC` コース変更 | 12–25 | 26–27 | 28–35 | |

時刻はすべて UTC の ISO 8601 で、常に同じ形（マイクロ秒 6 桁、`+00:00`。例
`2026-10-11T00:41:07.123456+00:00`）です。この形に限り文字列の大小比較が時刻の前後と
一致します。ほかの形の時刻と比べるときは、PostgreSQL なら `::timestamptz` にしてください。

## 書き込みの規則

- 対象は `0B11` と `0B14` だけ（`src/realtime/capture_log.py` の
  `CAPTURE_LOG_SPECS`）。ほかの速報 spec と蓄積系は記録しません。
- 書くのは `scripts/daily_update.py`（と、それを使う runtime）の速報取得経路と、
  単発取得 `jltsql realtime fetch` です（`Producer` で区別できる）。
  `jltsql realtime start`（`RealtimeMonitor`）は 2.3.0 では書きません。
- RT_* への取込と**同じ transaction** で書きます。spec が失敗して rollback
  された（JVRead エラー、取込拒否など）ときは、その spec の取得ログも残りません。
  残った `RT_CAPTURE_FETCH` 行は、その取得が最後まで読めて commit されたことを示します。
- レコードの中身が原因で取得ログの行が作れないことはありません（読めないバイト列は
  hex、パースできなければ `RowsJson` が NULL）。壊れたバッファ 1 件が取得ログのせいで
  spec 全体を rollback させることはありません（取込側が拒否すれば従来どおり spec は失敗）。
  DB のエラー（容量不足など）は spec の失敗になります。
- JVRTOpen `-1`（該当データ無し）も `Status = no_data`、`RecordCount = 0` の行を
  残します。`-1` は「最新バージョンのダウンロードを選んだ」場合にも返る（IF p.54）
  ので、サーバーが空だった証明ではありません。
- JVRTOpen が `-1` 未満を返した・例外になった取得は、spec ごと失敗するので記録しません
  （`--summary-json` の `opens[]` には `fetch_id: null` で残ります）。
- 同じキーを何度取得しても、そのたびに新しい `FetchId` で追記します。

## 読み方

### 0B14: 時刻 T に分かっていた開催変更

`0B14` の 1 回の取得は、その日の完全な snapshot です。時刻 T の状態は
「`CompletedAt <= T` で最後に完了した取得のレコード全部」です。

```sql
WITH last_fetch AS (
  SELECT FetchId
  FROM RT_CAPTURE_FETCH
  WHERE DataSpec = '0B14' AND RequestKey = '20261011'
    AND Status IN ('complete', 'no_data') AND CompletedAt <= :t
  ORDER BY CompletedAt DESC
  LIMIT 1
)
SELECT r.*
FROM RT_CAPTURE_RECORD r JOIN last_fetch f ON r.FetchId = f.FetchId
ORDER BY r.Seq;
```

- 選んだ取得が `no_data` なら、その時点でサーバーから何も得られていない
  （空の snapshot として扱うか、1 つ前の `complete` を使うかは読み手が決める）。
  なお RT_* の現在状態は `-1` では置き換えないので、直前の `complete` の内容が残る。
- `complete` かつ `RecordCount = 0` は「その時点で開催変更が 0 件」という snapshot です。
- 取得の間隔より細かい時刻は分かりません。T の直前の取得が古ければ、その分だけ
  古い状態です。

### 0B11: 時刻 T に分かっていた馬体重

`0B11` は発表ごとの追加なので、`CollectedAt <= T` で受け取った WH レコードのうち、
レースごとに `HappyoTime` が最大のものが T 時点の最新発表です。

```sql
SELECT *
FROM (
  SELECT r.*, ROW_NUMBER() OVER (
    PARTITION BY Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum
    ORDER BY HappyoTime DESC, CollectedAt DESC, FetchId DESC, Seq DESC
  ) AS rn
  FROM RT_CAPTURE_RECORD r
  WHERE DataSpec = '0B11' AND RecordSpec = 'WH' AND CollectedAt <= :t
) latest
WHERE rn = 1;
```

馬ごとの値は `RowsJson`、または `RawRecord` を jltsql の `WHParser` で再パースして
得ます。

## 保持と容量

jltsql は取得ログを削除しません。daily_update を 5 分ごとに回すと、0B11 は
「その日の発表済み全レース分」を毎回返す（開催日単位の提供）ので、行数は
取得回数 × その時点の発表レース数で増えます。保持期間と削除は利用側で決めてください。

## migration

- この 2 表は 2.3.0 の `create_all_tables`（daily_update の既定 `--ensure-tables` を
  含む）が `CREATE TABLE IF NOT EXISTS` で作ります（追加のみ）。`--no-ensure-tables` で
  運用している環境は、事前に `jltsql create-tables` などで作ってください。
- **既存の `RT_WH` の主キー変更（`HappyoTime` を追加）は自動では行いません。**
  オペレーターの手順（[WH](record_contracts.md#wh)、2.3.0 の `RELEASE_NOTES.md`）です。
  未移行のあいだは起動もほかの spec も動き、`0B11` の取得と RT_WH への書き込みだけが
  JVRTOpen の前に停止します（fail closed）。
