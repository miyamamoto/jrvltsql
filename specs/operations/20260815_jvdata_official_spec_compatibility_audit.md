# JV-Data / JV-Link 公式仕様・新旧互換性監査

## 結論

対象 `master` は、まだ公式仕様準拠としてリリースできる状態ではない。判定は
**RED / DO NOT RELEASE** とする。blockerを解消する個別PRは、その変更範囲の
exact-SHA testとreviewがgreenなら順次mergeしてよい。

2023年8月8日の仕様変更に対して「旧 dataspec を拒否し、N 付き dataspec で
全件再セットアップする」という方針は、JRA-VAN スタッフの推奨と整合する。
しかし、その入口検査は連結 dataspec を防げず、変更対象7レコードの現行形式も
安全に処理できていない。加えて、変更時期とは独立した次の重大な矛盾がある。

- 9レコードの公開長または終端位置が公式現行長より短く、多くは公式配列の1件目
  だけを保存して途中に偽のレコード区切りを置いている。

したがって、今回の監査報告そのものは保存してよいが、下記 blocker を直して
実 Windows/JV-Link を含む最終検証を終えるまで、製品全体の「仕様準拠」または
release判定には使えない。

## 対象と証跡

- Repository: `miyamamoto/jrvltsql`
- Branch: `codex/jvdata-official-spec-audit-20260815`
- 監査対象 full SHA:
  `d6f8f70e4976e053f636dc1d136a3214fa6996ad`
- 監査開始時の `origin/master`: 同じ SHA
- SDK 本体の公式最新版: 4.9.0.2（2024-08-07）
- JV-Data / JV-Link 公式文書: 4.9.0.1（2024-08-07）
- 直前比較対象 JV-Data: 4.8.0.2
- product source、schema、test fixture は変更していない。

取得した公式資料の SHA-256 は次の通り。

| 資料 | SHA-256 |
|---|---|
| `JV-Data4901.xlsx` | `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234` |
| `JV-Data4901.pdf` | `b6c21aae4ccbba6a71c5e8065609c4fbb1ccee826c16e7d99ca6ecf7a4101522` |
| `JV-Link4901.pdf` | `dfd1c425a62304bb464f15c25106e030ffccbf99c7c777972d6bb6b6d27ef1d7` |
| `JV-Data4802.xlsx` | `6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7` |

主な一次資料:

- SDK 配布ページ: <https://jra-van.jp/dlb/sdv/sdk.html>
- JV-Data 4.9.0.1: <https://jra-van.jp/dlb/sdv/sdk/JV-Data4901.pdf>
- JV-Link 4.9.0.1: <https://jra-van.jp/dlb/sdv/sdk/JV-Link4901.pdf>
- 2023年仕様変更予告: <https://jra-van.jp/dlb/sdv/ml/20230315a.html>
- 2023年8月8日リリース: <https://jra-van.jp/dlb/sdv/ml/20230808a.html>

## 公式文書の扱い

公式資料内にも矛盾があるため、単一表の機械転記だけでは判定していない。

- JV-Data Excel の option 1 は `COMM` と `MING` を含み、変更履歴にも追加が
  明記されている。一方、JV-Link PDF の option 1 表からは両者が欠けている。
  本監査ではデータ仕様書の一覧と変更履歴を優先し、コードの `COMM` / `MING`
  option 1 対応を正しいと判定した。
- 公式開発者コミュニティで JRA-VAN スタッフは、暗黙の仕様変更ではなく文書の
  記載漏れだったこと、TCVN/RCVN を setup に載せた履歴は誤記だったことを認めて
  いる: <https://developer.jra-van.jp/t/topic/457>。
- よって、文書間で食い違う箇所は「コードが誤り」と即断せず、変更履歴、データ
  種別一覧、スタッフ回答、実行可能な境界テストの順で照合した。

## Blocker / high findings

### B-01 解消済み: native COM transport contract

監査開始時の `JVOpen` / `JVGets` 呼出しは公式シグネチャと不一致だったが、PR #163
（`2dad8a5`）で6引数 `JVOpen`、3引数 `JVGets`、`-2` / `-3`、`JVStatus`、
decode failure、close obligationを修正した。PR #165（`fc5d4fb`）ではheadless runtime
起動と既知dialogの安全な拒否を追加し、exact staged sourceで
`JVInit=0 -> JVOpen=0/readcount=30/downloadcount=29 -> JVStatus=29 ->
JVRead=80 bytes -> JVClose=0` を実測した。transport blocker自体は解消済みである。
ただし、この古いSHAのsmokeを最終release candidateの証跡には流用しない。ユーザー指定の
release gateとして、最終マージ済みfull SHAでfresh data acquisitionを再実行する。

### B-02 解消済み: `BaseParser` のbyte-first field extraction

公式の開始位置と長さはバイト単位である。監査開始時はレコード全体をUnicodeへdecodeして
からbyte offsetを文字位置として使っていたが、PR #166（`56acaaf`）で各fieldをraw bytes
から先にsliceし、その後CP932 decodeする実装へ変更した。ASCII正常系と全角`日本`の後続
fieldを対にしたred-first test、全parser focused suite、full suiteで固定されている。
これによりCK/BT/JCの全角文字より後ろの現行offsetは正しく読める。各parser固有の
length/delimiter gateや旧physical layout拒否は別の互換性課題として残る。

### B-03 解消済み: `WH` 速報馬体重の全展開

公式 `WH` は847バイトで、レース番号、発表時刻、18頭分の
`馬番 + 馬名 + 馬体重 + 増減符号 + 増減差`（45バイト×18）を持つ。
監査開始時の40バイト実装は誤りだったが、PR #167
（`d0b4ad3`）で修正済みである。現行 `WHParser` は847バイトとCRLFを厳密検査し、
18枠をbyte-firstで読み、値のある馬を1頭1行へ展開する。`NL_WH` と `RT_WH` も
race identityと`Umaban`を複合主キーに持ち、馬名、馬体重、増減符号、増減差を
保存する。0B11の置換・取消経路、native/standard import、schema migrationは
`tests/test_wh_official_contract.py`で固定されており、`WE`とは別契約になっている。

### B-04 現行38種のうち複数が公式配列を途中で切る

明らかに短い公開契約は、WH、SK、RA、BN、BR、CH、DM、TMの修正後、次の4種である。

```text
KS 772/4173   RC 241/501
TK 727/21657  YS 146/382
```

左が実装上の公開長または終端、右が公式現行長。KS の成績配列、
TK の300頭配列、RC の3頭分記録、YS の3競走案内などを
1件または一部だけ取り、公式レコード内部に `RecordDelimiter` を置くものがある。
これは「不要列を捨てる」だけではなく、繰返し要素のデータ損失と key collision を
固定する schema になっている。

RAはこのイテレーションで4.8.0.2、4.9.0.1、SDK 5.0.0に共通する1272バイトへ統一した。
賞金4配列、25ラップ、4コーナー、更新区分を全展開し、CRLFを厳密検証して、native/standard schemaと
両importerのround-tripを固定した。旧856バイトfixtureは公式rawとは扱わず、位置互換な
先頭713バイトだけをcurrent shapeへ合成するrepository regressionに限定した。

BNは4.8.0.2、4.9.0.1、SDK 5.0.0に共通する477バイトへ統一した。本年・累計の
60バイト成績blockを各9項目へ全展開し、CRLFとrecord typeを厳密検査して、
native/standard schemaと両importerのround-tripを固定した。2003年以前の公式413バイトと
旧repository由来387バイトは現行setupへ混在させず拒否する。既存のkeyless `BANUSI` は
安全に主キーを追加できないため、行を保持したままfail closedで再構築を要求する。既存の
`NL_BN` は主キーを保持したadditive migrationが可能だが、新しい18成績列は既存行では
NULLになる。option 1の差分更新だけでは変更のない馬主を補完できないため、移行後は現行
`DIFN` のoption 3/4 setupから全件を再取込する。

BRは現行DIFN/4.9.0.1/SDK 5.0.0の545バイトへ統一した。本年・累計の60バイト
成績blockを各9項目へ全展開し、record type、strict CP932、CRLFを厳密検査する。
旧DIFF/4.8.0.2の537バイトと旧repository由来455バイトは拒否する。標準名mappingは
schemaと一致する`SEISAN`をcanonicalとし、`BREEDER`はread-side aliasに限定した。
native/standard schemaは8バイト`BreederCode`主キーと27 business fieldで一致し、
既存native DBも移行後に現行DIFN option 3/4 setupから全件再取込する。

CHは4.8.0.2、4.9.0.1、SDK 5.0.0に共通する3862バイトへ統一した。
最近重賞3件（163バイト×3）と、本年・前年・累計の成績3件
（1052バイト×3、各173値）を全展開し、長さ/type/strict CP932/CRLFを厳密検査する。
保存は公式互換DBの構造に合わせ、native/standardともheader 1行と成績3行へ正規化した。
headerは`ChokyosiCode`、成績は`(ChokyosiCode, Num)`を主キーとし、1物理レコードを
両テーブルへ原子的に書く。旧592バイトfixtureは先頭590バイトだけを位置互換の
repository regressionとして合成し、provider rawとは扱わない。既存native `NL_CH`の
旧inline成績列はadditive migrationで保持するが、新しいheader/成績表を埋めるには
現行setupから全件再取込が必要である。

### B-05 2023年変更対象7種は新旧両対応ではない

4.8.0.2 から 4.9.0.1 への物理長変化は次の7種だけである。

| ID | 旧長 | 現行長 | 現行実装 | 旧実装 | 判定 |
|---|---:|---:|---|---|---|
| UM | 1577 | 1609 | 現行位置・厳密長/CRLF | 拒否 | 現行のみ可 |
| BR | 537 | 545 | 現行全位置・厳密長/CRLF | 拒否 | 現行のみ可 |
| HN | 245 | 251 | 現行全位置・厳密長/CRLF | 拒否 | 現行のみ可 |
| SK | 178 | 208 | 現行全位置・血統14件・厳密長/CRLF | 拒否 | 現行のみ可 |
| CK | 6864 | 6870 | 現行offset、byte-first | version dispatchなし | 現行可、旧拒否未達 |
| HS | 196 | 200 | 現行10byte番号に対応 | version dispatchなし | 現行のみ可 |
| BT | 6887 | 6889 | 現行offset、byte-first | version dispatchなし | 現行可、旧拒否未達 |

「長い方を受け入れる」「警告後も読む」は version 対応ではない。幅が2バイト増えると
後続キー・名前・区切りがすべてずれるため、layout を識別して別 offset を使うか、旧物理
record を確実に拒否しなければならない。

HN の修正は、旧パーサーで保存済みの行を自動変換しない。`NL_HN` は主キーを含む値が
すでに誤っている可能性があるため、現行 `DIFN` / `BLDN` の原本から全件再取込する。
旧 `HANSYOKU` 標準名テーブルは `HansyokuNum` と主キーを欠くため、安全な additive
migration はできない。インポータはこの形を fail closed で拒否するので、テーブルを
退避・再作成して同じ現行原本から再取込する。

## 2023年8月8日境界の正しい読み方

公式スタッフ回答から、次の3経路を区別する必要がある。

| 取得経路 | dataspec | 対象時点 | 返る物理構造 |
|---|---|---|---|
| 旧通常更新 | `DIFF/BLOD/SNAP/HOSE/TCOV/RCOV` | 2023-08-07まで | 旧幅 |
| 新通常更新 | `DIFN/BLDN/SNPN/HOSN/TCVN/RCVN` | 2023-08-08以後 | 拡張幅 |
| 新 setup | N付き | 過去分を含むsetup | 過去も拡張幅へ変換 |

スタッフは旧新を同じ store に混ぜず、新 dataspec で再 setup するよう案内している:

- 新 setup と旧データの扱い: <https://developer.jra-van.jp/t/topic/215>
- 旧通常更新と新通常更新の境界: <https://developer.jra-van.jp/t/topic/221>
- 2026年の公式再案内（8月8日以後は DIFN）:
  <https://developer.jra-van.jp/t/topic/898>

したがって、jrvltsql が新世代だけを採用する方針は妥当であり、必ずしも一つの
process で旧新両方を parse する必要はない。ただしその場合でも、旧 byte が COM、cache、
保存済み raw fixture のどの入口からも入らないことと、現行7種が正しく parse できることが
必要である。現在はどちらも満たさない。

### 連結 dataspec による旧形式ガード回避

公式 `JVOpen` は4文字固定 ID を連結して指定できる。コードの
`is_retired_data_spec()` は文字列全体の完全一致しか見ない。

```text
DIFF      retired=True
DIFFRACE  retired=False
RACEDIFF  retired=False
```

direct wrapper は option/dataspec matrix も検査しないため、`DIFFRACE` を COM へ渡せる。
この場合は旧幅と現行 RACE が同じ stream に入り得る。PR #161 の fail-closed 境界は単一
ID にしか成立していない。

## JVOpen dataspec / option 監査

現行 JV-Data Excel の行を正本とした場合の official matrix は次の通り。

- option 1: `TOKU,RACE,DIFF,BLOD,SNAP,SLOP,WOOD,YSCH,HOSE,HOYU,COMM,MING,DIFN,BLDN,SNPN,HOSN`
- option 2: `TOKU,RACE,TCOV,RCOV,SNAP,TCVN,RCVN,SNPN`
- option 3/4: option 1 と同じ

判定:

- `SNPN + option 2`、`COMM/MING + option 1` は現行コードどおりでよい。
- `O1`～`O6` は RACE 等から返る record ID であり JVOpen dataspec ではない。コードが
  option 1/3/4 に追加しているため、実サービスでは `-111` または `-116` となる。
- 公式は複数ID連結を許すが、validator は単一完全一致しか受けない。CLI が明示的に単一
  IDだけを製品契約にするならよいが、public wrapper も同じ制約を検査・文書化すべきである。
- validator は current dataspec の大小文字を正規化せず、retired guard だけが大小文字を
  無視する。重要度は低いが、public API 契約が非対称である。

## JV-Link 状態・戻り値監査

### High: `-2` を no-data success に変えている

公式で `JVOpen/JVRTOpen = -2` は「setup dialog でキャンセル」であり、no data は `-1`
だけである。wrapper/bridge は `-1` と `-2` を同じ no-data とし、stream open 状態にする。
ユーザー取消とデータなしを区別できない。

### High: native `JVRead/JVGets = -3` を回復不能例外にする

公式 `-3` は「対象ファイルをダウンロード中。少し待って再開」である。bridge は返すが、
native wrapper は例外にする。公式コミュニティの動作例も `-3` を sleep/retry している:
<https://developer.jra-van.jp/t/topic/632>。

### High: bridge の download 完了条件が逆

公式 `JVStatus` はダウンロード済みファイル数を返し、`downloadcount` と一致した後も
`JVClose` までその値を返す。`HistoricalFetcher._wait_for_download()` は正しいが、bridge の
public `wait_for_download()` は「正数になった後0へ戻る」まで待つため、実サービスでは timeout
する。公式コミュニティ教材も `status == downloadcount` を完了条件にする:
<https://developer.jra-van.jp/t/topic/606>。

### High: decode failure を plausible data に変える

native `jv_read()` / `jv_gets()` は U+FFFD を ASCII `0`、その他の encode 不能文字を `?`
へ置換する。壊れた transport byte が数値 `0` に変わると schema validation を通る可能性が
あり、fail-open である。raw byte を復元できなければ record 全体を不合格にすべきである。

### Medium: setup resume を実装していない

公式は setup 読込の中断再開に `JVRead/JVGets` が返した filename と `JVSkip` を使う。
コードに `JVSkip` はなく、setup の file-level resume を提供しない。全件を読むだけなら必須
ではないが、大規模 setup の再開機能としては未対応である。コミュニティでも filename/
skip の扱いに関する実運用上の質問が繰り返されている:
<https://developer.jra-van.jp/t/topic/732>、
<https://developer.jra-van.jp/t/topic/860>。

## 全38レコード current-format matrix

凡例:

- `current-shape`: 現行長の主要 offset/配列分解が実装されている。ただし実 Windows raw
  record での完全一致を証明するものではなく、弱い length/delimiter 検査は別 risk。
- `partial`: 現行レコードの繰返しまたは末尾を捨てる。
- `wrong`: 別構造または旧 offset を current として扱う。
- `undocumented fallback`: current branch に加え、公式根拠のない短い形も受理する。

| ID | 公式長 | 実装判定 | 主要根拠 |
|---|---:|---|---|
| TK | 21657 | partial | 300頭配列の先頭付近、公開長727 |
| RA | 1272 | current-shape | 全配列、現行長/CRLFを厳密検査、856byteを拒否 |
| SE | 555 | current-shape | byte slice、現行長とCRLFを厳密検査 |
| HR | 719 | current-shape / weak gate | 払戻全配列を展開するが100byte以上を受理 |
| H1 | 28955 | current-shape + undocumented fallback | full配列に加え317byteを受理 |
| H6 | 102890 | current-shape + undocumented fallback | full配列に加え78byteを受理 |
| O1 | 962 | current-shape / weak gate | full配列、短い record も続行 |
| O2 | 2042 | current-shape / weak gate | 同上 |
| O3 | 2654 | current-shape / weak gate | 同上 |
| O4 | 4031 | current-shape / weak gate | 同上 |
| O5 | 12293 | current-shape / weak gate | 同上 |
| O6 | 83285 | current-shape / weak gate | 同上 |
| UM | 1609 | current-shape | currentのみ、厳密長/CRLF |
| KS | 4173 | partial | 成績配列を途中で終了、公開長772 |
| CH | 3862 | current-shape / normalized | 最近重賞3件＋成績3件をheader 1行/成績3行へ原子的に保存、厳密長/type/CRLF |
| BR | 545 | current-shape | 全位置・全成績配列・厳密長/type/CRLF |
| BN | 477 | current-shape | 本年・累計成績を全展開、現行長/type/CRLFを厳密検査、413/387byteを拒否 |
| HN | 251 | current-shape | currentのみ、全フィールドの現行位置と長さ/CRLFを厳密検査 |
| SK | 208 | current-shape | currentのみ、14件血統と長さ/CRLFを厳密検査 |
| CK | 6870 | current-shape / weak gate | byte-first修正済み、旧長の明示拒否なし |
| RC | 501 | partial | 3頭ブロックを途中で終了、公開長241 |
| HC | 60 | current-shape / weak gate | 現行末尾まで |
| HS | 200 | current-shape / weak gate | 2023 current幅 |
| HY | 123 | current-shape / weak gate | 現行末尾まで |
| YS | 382 | partial | 競走案内3件の一部、公開長146 |
| BT | 6889 | current-shape / weak gate | byte-first修正済み、旧長の明示拒否なし |
| CS | 6829 | current-shape / delimiter caveat | 説明が実質末尾、BaseParserでCRLF検査不能 |
| DM | 303 | current-shape / expanded | 18頭をnative 18行、standard `MINING` 1行へ保存。厳密長/type/CRLF、訂正upsert、0削除を検査 |
| TM | 141 | current-shape / expanded | 18頭をnative 18行、standard `TAISENGATA_MINING` 1行へ保存。厳密長/type/CRLF、訂正upsert、0削除を検査 |
| WF | 7215 | current-shape | full配列を展開 |
| JG | 80 | current-shape / weak gate | 現行末尾まで |
| WC | 105 | current-shape / delimiter caveat | numeric中心、現行末尾まで |
| WH | 847 | current-shape | 18頭を全展開し、現行長/CRLFを厳密検査 |
| WE | 42 | current-shape / delimiter caveat | 現行末尾まで |
| AV | 78 | current-shape | byte slice override |
| JC | 161 | current-shape / weak gate | byte-first修正済み、長さ/CRLF gateは弱い |
| TC | 45 | current-shape / delimiter caveat | CRLF以外の43byteを定義 |
| CC | 50 | current-shape / delimiter caveat | CRLF以外の48byteを定義 |

`scripts/validate_schema_parser.py` は動的に生成する配列 key を静的に認識できず、HR/WF
等に false positive を含む。この表は validator 出力をそのまま採用せず、公式 offset、
parser の loop、schema、合成 record の実測を個別に照合した結果である。

## DataKubun と realtime 更新

公式で `DataKubun=9` は RA/SE/HR/H1/H6/O1～O6/WF などにおけるレース・重勝式の
中止状態であり、汎用の「行を物理削除」ではない。updater は RA/SE/WF だけを例外扱い
し、HR/H1/H6/O1～O6 の `9` を delete dispatch へ送る。schema には DataKubun があるのに
中止 record を消すため、状態の意味を失う。

AV の `1=出走取消`, `2=競走除外` は汎用 new/update と同じ数値だが、update handler は
upsert なので両方とも行自体は残る。ここは値の意味を schema に保持しており、今回の
blocking data loss とはしない。

0B14 の snapshot replacement は、background updater では全 response を materialize して
から transaction 内で置換し、daily updater も例外時 rollback する。今回確認した範囲では
この新しい一括置換契約は fail-closed である。

## それ以前・それ以後の仕様変更

### 物理長が変わった古い record

- 2003年: SE `547→555`、BR `467→537`、BN `413→477` 等。
- これらを layout version / dataspec / record length で dispatch する共通機構はない。
- 現行 setup が現行形へ正規化する経路だけを製品契約にするなら、古い raw cache/fixture を
  明示拒否する必要がある。現在、多くの parser は短い record を warning 後も parse する。
- BNは現行477バイトだけを受理し、旧公式413バイトと旧repositoryの387バイトを明示拒否する。

### 同じ長さで意味が変わった UM（2006年）

馬名欧字80byteが60byteへ縮小し、20byte reserve の先頭が JRA施設在厩flag になった。
現行 parser は60byte + flag + reserve を読むため、新 setup で正規化された record には対応
する。一方、旧物理 record の80byte英字名を直接入れると末尾20byteを flag/reserve と誤認し、
同じ record 長なので長さ検査だけでは発見できない。cache provenance または generation
metadata が必要である。

### code/初期値だけが変わったもの

- 2019年 Grade `L`、騎手見習コードの説明・記号追加は TEXT として保存し、enum 拒否を
  していないため対応できる。
- 2021年 AV 事由区分の初期値 `0→space` も文字列として受け、両方で field shift は起きない。
- 2024年の RA/SE 外国・地方レースにおける「設定される/されない」表修正は物理 offset の
  変更ではない。code は値を hard reject しないため、今回確認した箇所に矛盾はない。

公式は将来 dataspec 内に未知 record type が増えた場合に読み飛ばせるよう求めている。
Factory は未知 type を `None` にするが、fetcher は parser failure と数えて response/cache を
不完全扱いする。データ破壊を避ける fail-closed ではあるが、公式の forward-compatibility
推奨どおりの「skipして既知recordを継続」にはなっていない。

## Realtime / 時系列仕様で整合している点

次は current master と公式仕様が整合するため、今回の finding にはしない。

- `0B11`～`0B17`, `0B20`, `0B30`～`0B36`, `0B41`, `0B42`, `0B51` の ID 対応。
- `0B41/0B42` は1年保持の時系列、`0B30`～`0B36` は1週間保持の速報として分離。
- レース key は公式の12桁 `YYYYMMDDJJRR` と16桁 `YYYYMMDDJJKKHHRR` の双方が有効。
  production helper が12桁を使うこと自体は誤りではない。
- 0B14 を追加差分ではなく最新 snapshot として置換する方針。
- JVRead buffer 262144 byte は最大 H6 102890 byte + NULL を十分収容する。

競馬場 helper が01～10だけを列挙することと海外発売レースの realtime key については、
一次資料から product の intended scope を確定できなかった。欠陥と推測せず evidence gap とする。

## コミュニティ掲示板照合

掲示板は一次仕様の代用にせず、スタッフ回答または再現例として用いた。

- スタッフ回答: 新 setup は過去分も新構造へ変換し、旧新 store を混ぜない:
  <https://developer.jra-van.jp/t/topic/215>
- スタッフ回答: 2023-08-07以前の通常更新は旧構造、以後はN付き新構造:
  <https://developer.jra-van.jp/t/topic/221>
- スタッフ回答: UM の登録番号/生産者 code/name の幅変更を明示:
  <https://developer.jra-van.jp/t/topic/214>
- 2026年公式アナウンス: 2023-08-08以後の蓄積情報は DIFN:
  <https://developer.jra-van.jp/t/topic/898>
- スタッフ回答: 現行仕様書にも履歴漏れ・TCVN/RCVN setup誤記がある:
  <https://developer.jra-van.jp/t/topic/457>
- コミュニティ実行例: pywin32 の6引数 JVOpen と JVRead `-3` retry:
  <https://developer.jra-van.jp/t/topic/632>
- コミュニティ事例: SNAP のままでは新しい出走別着度数が取れず SNPN が必要:
  <https://developer.jra-van.jp/t/topic/148>

掲示板で報告される「取れない」「古い構造が返る」は、旧ID、新ID、通常、setup を区別しない
と互いに矛盾して見える。今回の code 判定では topic 215/221 の3経路を基準に整理した。

## 実行した検証

対象 full SHA:
`d6f8f70e4976e053f636dc1d136a3214fa6996ad`

```text
python3 -m pytest -q \
  tests/test_jvdata490_layouts.py \
  tests/test_parser_compatibility.py \
  tests/test_ra_parser_jravan.py \
  tests/test_jvlink_constants.py \
  tests/test_jvlink_wrapper.py \
  tests/unit/test_jvlink_bridge.py \
  tests/test_error_scenarios.py
```

結果: exit 0、22 skipped。Windows-only wrapper test が skip され、残る mock/fixture は現行の
誤ったシグネチャと短い互換長を契約化しているため、この green は公式準拠の証拠にならない。

```text
python3 scripts/validate_schema_parser.py
```

結果: exit 1、7 mismatches、16 errors。動的配列 parser に false positive を含むため、上記
findings はこの出力だけではなく個別に再現したものに限定した。

追加の read-only counterexample:

- current CK 6870byte に全角馬名と後続9桁賞金を配置し、賞金が6桁へ崩れることを確認。
- `is_retired_data_spec('DIFFRACE') is False` を確認。
- current/previous Excel を列比較し、2023年の長さ変更が7種であることを確認。
- 全38種について official record length と parser/schema の終端・loop count を比較。

後続PR #163～#166でtransport contract、authenticated realtime record、positive-download
`JVOpen/JVStatus/JVRead/JVClose`、byte-first coreの実環境またはfocused evidenceを得た。
それでも、次のrelease gateは未完了である。

- 最終マージ済みrelease candidate full SHAを実際の対応JV-Link環境へstagingし、providerから
  fresh dataを新規取得して、acquisition、parse、DB保存、件数、key、代表値を検証する。
- provenance付きraw recordによる全38種end-to-end coverageを確認する。

古いSHAのsmoke、mock、合成fixture、保存済みdataの再読込はfresh acquisitionの代替にしない。
credential/Windows/JV-Link runtimeが必要であり、実行不能ならreleaseしない。

## 推奨する修正イテレーション

後戻りを抑えるため、次の順で別PRにする。

1. **残る現行 layout/schema の再生成**
   残る4 partial recordを公式 Excel から再実装する。偽 delimiter とDB再構築 fixture
   を公式raw扱いしない。
2. **2023 generation boundary**
   staff 推奨の new-only rebuild 方針を維持し、連結 token、cache、raw import の全入口で旧物理
   record を拒否する。7種すべての current positive と old negative を置く。true dual parser を
   選ぶ場合だけ、明示 version dispatcher を別設計する。
3. **dataspec / updater semantics**
   O1～O6を JVOpen matrix から除き、単一/連結 public API 契約を統一し、中止 `9` を物理削除
   せず domain state として保存する。
4. **fixture provenance / resume / forward compatibility**
   provenance付き raw fixture、未知 record skip policy、JVSkip setup resume を独立して整備する。

各検査・validator の修正では、不正 record/シグネチャが修正前に実際に赤になることを先に
確認する。上記 blocker を一つずつ直してレビューを毎回再実行するのではなく、各PR内で
関連 finding を集約して一括修正・focused test・最終レビューを行う。

## 最終判定

- 2023年の新 dataspec への移行方針: **妥当**。
- 変更前と変更後の物理 layout の両対応: **未達**。
- new-only 方針として旧 layout を全入口で拒否: **未達**。
- 現行4.9.0.1の全38種 parse/schema対応: **未達**。
- JV-Link public API/状態機械: **transport契約は解消済み**（最終SHAのfresh acquisitionは未実施）。
- realtime ID/時系列保持区分の定義: **概ね整合**（WH実体はPR #167で解消済み）。
- 個別blocker修正のmerge: **対象scopeのgate通過時のみ可**。
- コード全体を仕様準拠としてリリース: **不可**。
