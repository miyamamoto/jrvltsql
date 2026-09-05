# 変更履歴

このプロジェクトの主な変更点をこのファイルに記録します。

形式は [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) を参考にし、
バージョン番号は [Semantic Versioning](https://semver.org/spec/v2.0.0.html) に従います。

## [Unreleased]

該当なし。

## [2.1.2] - 2026-09-05

### 2.1.2

- 発走時刻window指定時の時系列オッズ対象選択で、同一フルキー（Year,
  MonthDay, JyoCD, Kaiji, Nichiji, RaceNum）のレースをライフサイクル
  ソース優先で1系列に選ぶ。`RT_RA`行が存在するキーはDataKubunに関わらず
  `RT_RA`が所有し、`NL_RA`は`RT_RA`に無いキーだけに使う（`RT_RA` table
  不在時は`NL_RA`が全キーを所有）。古い`NL_RA`発走時刻と当日`RT_RA`改定
  時刻の同居を曖昧性と誤検知してbatch全体を中断し、後続due raceの公式
  O1/O2捕捉を失う障害（2026-09-05）を修正した。
- 選択された現行行のDataKubunを公式RA domain（`src/parser/status_domain.py`）
  で検証し、欠落・空白・domain外は対象レースキーを名指ししてfail closed
  （何も開かない）。検証後、所有ソースを問わずDataKubun=9（中止）のキーは
  収集対象から除外し、隠れた行へfallbackしない。選択ソース内で12桁キーの
  発走時刻が衝突する真の曖昧性は従来どおりfail closedを維持する。
- window統計に`omitted_canceled_keys`を常時追加し（中止なしでも0を報告）、
  `window_kept_keys`を中止除外後の実際に開く対象数と一致させた。
- 下流runtimeが機械parseするCLI進捗を拡張した: `Window:`行に`canceled=`、
  `Keys:`行に`nonempty=`（実レコードを1行以上返したキー数。ok=成功キーの
  代用にしない）を追加し、window指定時は対象0件でも終端
  `Keys: 0/0 ...`サマリを必ず1行出力する。`nonempty_keys`はfetcherの全
  progress callbackと完了logにも常時含まれる（0でも省略しない）。
- windowなしの対象選択query・schema・保存形式・provider書き込みは変更なし。
  windowなし出力の変更はキー処理時のCLI `Keys:`行に`nonempty=`が加わる
  ことのみ。

## [2.1.1] - 2026-09-02

### 2.1.1

- `realtime odds-timeseries`に公式長期時系列spec限定の`--spec`と
  `--post-time-within-minutes` / `--post-time-not-past-minutes`を公開し、generic
  `timeseries`へそのまま転送する。未指定時は従来どおり0B41/0B42・発走時刻filter
  なしとし、0B30〜0B36を含む非対応specは全日取得へfallbackせずnonzeroで拒否する。

## [2.1.0] - 2026-09-02

### 2.1.0

- generic `realtime timeseries`に`--post-time-within-minutes` /
  `--post-time-not-past-minutes`を追加し、発走前のレースだけを対象に公式
  時系列オッズ（0B41/0B42）を取得できるようにした。発走時刻は`NL_RA`/`RT_RA`
  から解決し、欠損・不正・曖昧な発走時刻はfail closedする。
- 時系列オッズtableのupsertで`CollectedAt`を最初の捕捉時刻として保持する
  （再取得で上書きしない）。SQLiteとPostgreSQLで同一挙動。
- 速報oddsのPKをpublication identityへ修正。既存行の集約はDELETEを伴うため
  起動時の暗黙実行をやめ、operator専用コマンド（既定dry-run、`--apply`で適用）
  に分離した。

## [2.0.0] - 2026-08-27

### 2.0.0

- `SE`（馬毎レース情報）の公式取消・除外レコードで、`MakeDate`の公式初期値
  `00000000`を受理する。実在日付とexact `00000000`以外は引き続きrejectする。
  標準名`UMA_RACE.MakeDate`も`DATE`から`VARCHAR(8)`へ揃え、旧`DATE` tableを
  mutation前に拒否する。1.xまたは旧2.0 prerelease DBはbackup後に
  rebuild/reimportする
- 下記`dev0`〜`dev6`で段階検証した公式record、schema、transaction、transport、
  packaging契約を1つのmajor releaseとして確定する。開発用prereleaseの個別履歴は
  監査証跡として残す

### 2.0.0.dev6 (開発検証用prerelease)

- pywin32がCOMのbinary bufferを文字列として返す経路で、Latin-1相当・CP1252・
  CP932の各投影から元のbyte列を復元する。末尾のCOM NULだけを除去し、期待長と
  完全一致する候補同士が一致した場合だけ採用する。oversized prefixや複数候補が
  異なる曖昧なbufferはfail closedで拒否し、公式fixed-width recordを文字化けした
  byte列としてparserへ渡さない
- 実providerでrange引数が有効と確認できた`RACE` option 1だけを暦年単位の
  `JVOpen`へ分割し、長期間取得を有限なchunkとして実行する。各chunkは次へ進む前に
  必ずcloseし、primary処理とcloseが同時に失敗した場合はprimary例外を保持する。
  provider `-402`からの再開はactive chunkですでに送出したprefixだけを再生する。
  option 2とsetup option 3/4、および未検証data specは従来どおりstart-onlyとする

### 2.0.0.dev5 (開発検証用prerelease)

- 実登録済みproviderの5年setupで後から確認できたH6レース中止形に対応する。
  `DataKubun=9`で既知の3連単組番を保持し、票数欄だけを公式の11バイト空白で
  返す場合に限り、parserでは`SanrentanHyo=""`、native数値票数列ではSQL
  `NULL`として保存する。`DataKubun=2/4/5`の空値、tabを混ぜた物理値、
  callerの`None`や空白値はmutation前に拒否する。速報のraw・parsed-record・
  batch入口にも同じ検証を適用する。既存のexpanded caller契約ではstatus 9の
  `SanrentanHyo=""`も受理するため、caller-created mappingへraw provenanceを
  主張しない
- H6 `DataKubun=0`はkey-onlyの物理eraseであり、非key本文が非canonicalまたは
  decode不能でもrace key・固定長・CRLFが正しければ本文検証で削除を抑止しない。
  live statusは引き続き本文全体をstrictに検証する

### 2.0.0.dev4 (開発検証用prerelease)

- 実登録済みproviderの5年setupで確認したH1レース中止形に対応する。
  `DataKubun=9`で既知の組番を保持し、票数欄だけを公式の11バイト空白で
  返す場合に限り、parserでは`Hyo=""`、native数値票数列ではSQL `NULL`
  として保存する。`DataKubun=2/4/5`の空値とtabなど11 spaces以外の
  空白は引き続きmutation前に拒否する。既存のexpanded caller契約では
  `DataKubun=9`の`Hyo=""`もSQL `NULL`として受理するため、raw由来の
  provenance保証とは表現しない
- H6は同様の形を推測で許可しない。公式資料、現行RACE cache、開発DBを
  独立監査したが組番付きstatus 9の空票数実例を確認できなかったため、
  組番付きlive rowは11桁数字を要求するfail-closed契約を維持する

### 2.0.0.dev3 (開発検証用prerelease)

- 公式 option 3/4 の historical setup tail は終了時刻で上限を切れないため、
  setup を年単位に再帰して後続tailを反復しない。要求開始日を包含する
  start-only `JVOpen` を1回だけ使い、`--to` はclient-side filterとして扱う
- 複数年setupを有限に監視できるよう `JVLINK_OPEN_TIMEOUT_SECONDS` の許容範囲を
  1〜86,400秒へ拡張する（既定120秒は維持、非有限値と範囲外はfail closed）
- setup開始境界の修正前に作られたNL cache schema-v2完了markerをschema v3で
  失効する。`cache build/rebuild`も日付範囲をcache lookup/clearより先に検証する

### 2.0.0.dev2 (開発検証用prerelease)

実デプロイ設定を読み込んだ結果の修正。

- `JVOpen` の応答待ちを `JVLINK_OPEN_TIMEOUT_SECONDS`（既定120秒、1〜7200秒）で
  指定できるようにした。従来は120秒固定で、版更新ダイアログ待ち（実測1,008秒）や
  setup取得を必ず timeout として捨てていた。読めない値は既定へ落とさず error にする

### 2.0.0.dev1 (開発検証用prerelease)

実登録済みJV-Linkでの実測を反映する。

- 実provider取得→parse→保存を通した（`JVOpen(RACE, 20260810, option=1)`=0、
  48ファイル、864,827件をSQLiteへ保存、失敗0件）
- 実データが暴いた契約欠陥2件を修正。H1の人気順取消マーカーは項目幅ぶん埋まる
  （3桁賭式は`***`）。O1〜O6の発表月日時分は中間オッズのみ設定され、確定オッズは
  公式初期値の`00000000`。どちらも提供値のまま保存する
- realtimeの`JVRTOpen`はno-data/error時にも`JVClose`する（次のkeyが`-202`で
  失敗していた）。当日対象は`NL_RA`に加えて`RT_RA`も見る
- Wine/Docker実行層（32-bit native bridge・image・entrypoint）と、noVNC上で人が
  インストールと利用登録を行う手順書を同梱。承認を代行する経路は持たず、
  JV-Linkのダイアログも既定では人に回す（`JVLINK_AUTO_CLOSE_DIALOGS=1`で明示的に
  opt-inしたときだけ既知のものを拒否する）

### Removed

- `JVLinkWrapper.jv_set_service_key` / `JVLinkBridge.jv_set_service_key` と、
  レジストリをプログラムから変更する経路を削除。利用登録はDataLabで行う
- O1〜O6を単独JVOpen data specのように見せる重複定数を削除。これらはRACEに
  含まれるrecord typeであり、`RECORD_TYPE_O1`〜`RECORD_TYPE_O6`を使用する

### Changed

- 非Windowsのbridge起動は暗黙の実装選択を廃止し、外部runnerを
  `JVLINK_BRIDGE_RUNNER`で明示する。公開propertyは
  `uses_external_runner`へ変更
- CLIの既定config/log/dataはinstalled package配下ではなく実行時の作業場所と
  user stateを使う。`jltsql init`はカレントディレクトリをSQLite-onlyの安全な
  既定で初期化し、`--config`との併用は曖昧さを避けるため拒否する
- JV-Link SDK 5.0.0 で公式 64-bit 版が追加されたことを文書へ反映。ただし
  jrvltsql の 64-bit 実行経路は未検証であり、x64 SDK の実導入・取得・parse・
  DB保存を完了するまでは対応済みとしない。インストーラとランチャーは、
  リリース検証済みの 32-bit Python / JV-Link 経路を既定として維持
- Python の実行要件を `pyproject.toml` と一致する 3.12 以上へ統一
- 公式 64-bit 版と競合し得る旧レジストリ回避ツールを削除
- 公式 fixed-width parser、DataKubun、primary key、native/standard child
  schema を現行契約へ揃え、SQLite/PostgreSQL の transaction recovery と
  durable statistics を fail closed 化
- 1.x DB は事前 backup のうえ v2 schema で rebuild/reimport し、件数・key・
  取消・readback を確認する。rollback は部分移行DBの再利用ではなく、backup と
  旧releaseの復元で行う。詳細は `docs/data_support.md` と v2 release notes を参照

### Fixed

- `O1`〜`O6` の保存が公式提供値を落としていた欠陥を修正。native `NL_O1`〜`NL_O6`・
  速報 `RT_O1`〜`RT_O6`・標準名 `ODDS_*` 子 table のオッズ列・人気順列は
  `REAL`/`INTEGER`/`DECIMAL`/`SMALLINT` だったため、公式の発売前取消（`-` の並び）・
  発売後取消（`*` の並び）が `NULL` へ落ちて「登録なし」と区別できず、無投票
  （`0` の並び）は数値 `0` になっていた。文字列列へ改め、公式提供値をそのまま保存する
- `O1`〜`O6` の native・速報が 1 レース 1 時点の完全 snapshot をレース単位で
  置換していなかった欠陥を修正。組合せが減った snapshot（実測: `filled=3` の
  次に `filled=2` を取り込むと `0104` が残存）や合計のみの snapshot のあとに
  前の snapshot の組合せが残っていた。通常・最適化・単発・速報の全経路で
  レース単位に全行を置換する
- `O1`〜`O6` のレースキーと組番が nullable だった問題を修正し、公式ドメイン検証と
  strict schema preflight を storage 経路（通常 importer・最適化 importer・
  単発取込・`DualDatabase`・SQLite / PostgreSQL）へ接続。公式キーの欠落・
  nullable なキー・公式主キー以外の追加 `UNIQUE`（部分・式・exclusion を含む）・
  遅延主キー・記号値を保存できない列型・所有表や子 table の欠落・未承認の
  `CHECK` / `FOREIGN KEY` を DML の前に拒否する

- `O1`〜`O6`（オッズ1〜6）の parser が、公式の提供値である無投票
  （`000000` など `0` の並び）・発売前取消（`-` の並び）・発売後取消（`*` の並び）・
  登録なし（空白）のオッズを持つ組合せを捨てていた欠陥を修正。組番を持つ行は
  保持し、組番を持たない（空白の）スロットだけを行にしない。あわせて組合せを
  1 件も持たない snapshot（レース中止・削除など）で公式の票数合計が失われて
  いた問題を、H1/H6 と同じ合計行（`Kumi=TOTAL`）で保持する形に修正した
  （標準名では合計は header table に入るため、合計行の子 table 行は作らない）
- `O1`〜`O6` に公式ドメイン検証（`validate_current_fields`）を追加。データ区分
  `0/1/2/3/4/5/9`、発売フラグ `0/1/3/7`、`O1` の複勝着払キー `0/2/3`、実在する
  `MakeDate` とレース日、2 桁の場・回・日・レース番号、登録/出走頭数、レコード
  ごとの組番桁数（2/4/6）、オッズと人気順の桁数および取消マーカー（桁落ちした
  `--` や `***` は拒否）、11 バイトの票数合計を公式仕様どおりに検証する
- 時系列オッズ table のメタデータが `HassoTime` を「発走時刻」（例 `1540`）と
  説明していた誤りを、公式の「発表月日時分」（`MMDDhhmm`）へ修正

- JG・RC・WC の storage 検証が、公式主キー以外の追加 `UNIQUE`/exclusion 制約と
  PostgreSQL の遅延主キーを検査していなかった fail-open を修正。drift した既存表
  では、別キーの行が置換で消えても両方の取込が成功と報告されていた（実測で 2 行
  投入後 1 行）。mutation 前に拒否する

- `H1`（票数１・全掛式）を公式現行28,955バイト配置へ結び付け、native `NL_H1`・
  速報 `RT_H1`・標準名 `HYOSU` 系でレース単位snapshot置換、`DataKubun=0`の物理
  exact erase（従来の消去表は存在しない別名 `HYO_TANPUKU` を指しており、標準名
  header/子tableが消去対象から漏れていた）、caller validation（公式データ区分
  `0/2/4/5/9`、実在する`MakeDate`とレース日、2桁の場・回・日・レース番号、
  登録/出走頭数、発売フラグ`0/1/3/7`、複勝着払キー`0/2/3`、位置ごとの返還
  フラグ28/8/8桁、賭式ごとの2/4/6桁組番、11桁票数、賭式ごとの2/3桁人気順、
  11桁×14の票数合計）、SQLite/PostgreSQL/Dualのstrict schema preflightを
  一致させた。公式の人気順は数値ではなく`--`（発売前取消）・`**`（発売後取消）・
  空白（登録なし）も取るため、`NL_H1`/`RT_H1`の`Ninki`を`INTEGER`から`TEXT`へ、
  標準名`HYOSU_WAKU`/`HYOSU_UMATAN`/`HYOSU_SANREN`の`Ninki`を`SMALLINT`から
  `VARCHAR`へ変更し（従来は取消マーカーが`NULL`に落ちていた）、空白は`NULL`では
  なく空文字で保持する（`HYOSU_TANPUKU.TanNinki`/`FukuNinki`と
  `HYOSU_UMARENWIDE.UmarenNinki`/`WideNinki`は以前から文字列列で、同じ
  マーカー契約の対象）。key列は`NOT NULL`にし、標準名子tableでは公式キー以外の
  `UNIQUE` indexも拒否する。既存tableは自動移行せず、backup・rebuild・`RACE`
  reimportを要求する
- `H6`（票数６・3連単）を公式現行102,890バイト配置へ結び付け、native `NL_H6`・
  速報 `RT_H6`・標準名 `HYOSU2`/`HYOSU_SANRENTAN` でレース単位snapshot置換、
  `DataKubun=0`の物理exact erase（従来の消去表は存在しない別名 `HYO_SANRENTAN`
  を指しており、標準名header/子tableが消去対象から漏れていた）、caller
  validation（公式データ区分`0/2/4/5/9`、実在する`MakeDate`とレース日、2桁の
  場・回・日・レース番号、登録/出走頭数、発売フラグ`0/1/3/7`、18桁の位置ごとの
  返還馬番フラグ、6桁組番、11桁票数、4桁人気順、11桁×2の票数合計）、
  SQLite/PostgreSQL/Dualのstrict schema preflightを一致させた。公式の人気順は
  数値ではなく`----`（発売前取消）・`****`（発売後取消）・空白（登録なし）も
  取るため、`NL_H6`/`RT_H6`の`SanrentanNinki`を`INTEGER`から`TEXT`へ、標準名
  `HYOSU_SANRENTAN.Ninki`を`SMALLINT`から`VARCHAR(4)`へ変更し（従来は取消
  マーカーが`NULL`に落ちていた）、空白は`NULL`ではなく空文字で保持する。key列は
  `NOT NULL`にし、標準名では公式キー以外の`UNIQUE` indexも拒否する。組番が1件も
  無いsnapshot（発売なし・レース中止）はnativeの置換キーを満たせず、公式の票数
  合計ごと取り込みに失敗していた（`records_failed`）。H1の総計行と同じ
  `SanrentanKumi=TOTAL`の1行として保持する。既存tableは
  自動移行せず（列の自動追加も行わない）、backup・rebuild・`RACE` reimportを
  要求する
- native `NL_UM` の保存経路にも標準名 `UMA` と同じ置換キー検証を追加し、公式主キー
  以外の `UNIQUE`/exclusion 制約、PostgreSQL の `ON CONFLICT` に使えない遅延
  主キー、`KettoNum` 以外の主キーや keyless、テーブル欠落を持つ既存 `NL_UM` を、
  行の置換前に `SchemaMigrationError` で拒否する（`docs/record_contracts.md` の
  UM 契約どおり。兄弟レコードと同じ検証器を同じ位置で呼ぶだけで、parser の挙動と
  標準名 `UMA` の既存 preflight は変えない）
- `UM`を公式現行1609バイト配置の本文domainへ結び付け、native `NL_UM`と標準名
  `UMA`でprovider順のstatus 1/2/3/4/9更新、status 0の物理exact erase（従来は
  両tableにstatus 0のtombstone行が残っていた）、caller validation（実在する
  `RegDate`/`DelDate`/`BirthDate`、抹消区分`0/1`、在きゅうフラグ`0/1`または空欄、
  2/1/1/2/1桁の馬記号/性別/品種/毛色/東西所属コード、5/8/6桁の調教師/生産者/
  馬主コード、9桁×6の累積賞金、18桁×27の着回数、12桁の脚質傾向、3桁の登録
  レース数、14個の10桁繁殖登録番号）、SQLite/PostgreSQL/Dualのstrict schema
  preflightを一致させた。公式に空欄になり得るテキスト項目は`NULL`ではなく空文字
  で保持する。`NL_UM.ZaikyuFlag`は公式の空欄を保持するため`INTEGER`から`TEXT`へ
  変更し、両tableの全列を`NOT NULL`にした。nullable/keyless/wrong-type/追加
  UNIQUE/CHECK/FKを持つ既存tableは自動移行せず、backup・rebuild・`DIFN`
  reimportを要求する。UMは蓄積系masterだけであり、`RT_UM`を追加しない
- `SK`を公式現行208バイト配置と10桁`KettoNum` identityへ結び付け、native
  `NL_SK`と標準名`SANKU`でprovider順のstatus 1/2更新、status 0 exact erase、
  caller validation（実在する`BirthDate`、1/1/2桁の性別/品種/毛色コード、
  産駒持込区分`0/1/2/3`、4桁輸入年、8桁生産者コード、14個の10桁繁殖登録番号）、
  SQLite/PostgreSQL/Dualのstrict schema preflightを一致させた。公式に空欄に
  なり得る`SanchiName`は`NULL`ではなく空文字で保持する。PR #175の208バイト
  layoutと14個の血統値はそのまま保持し、旧178バイト配置とnullable/keyless/
  wrong-type/extended tableは自動移行せず、backup・rebuild・`BLDN` reimportを
  要求する。SKは蓄積系masterだけであり、`RT_SK`を追加しない
- `HN`を公式現行251バイト配置と10桁`HansyokuNum` identityへ結び付け、native
  `NL_HN`と標準名`HANSYOKU`でprovider順のstatus 1/2更新、status 0 exact erase、
  caller validation、SQLite/PostgreSQLのstrict schema preflightを一致させた。
  公式に空欄になり得る`BameiKana`/`BameiEng`/`SanchiName`は`NULL`ではなく
  空文字で保持する。
  旧245バイト配置とnullable/keyless/wrong-type/extended tableは自動移行せず、
  backup・rebuild・`BLDN` reimportを要求する。HNは蓄積系masterだけであり、
  `RT_HN`を追加しない
- `CC`を公式50バイト配置と6項目race keyへ結び付け、発表`MMDDhhmm`、変更前後の
  4桁距離・track code、事由区分をlosslessに検証・保存する。native `NL_CC`、
  速報`RT_CC`、標準名`COURSE_CHANGE`でprovider順の改訂を1行へ反映し、current
  status 1以外、不正日付/競馬場/track/reason、nullable・keyless・wrong-type・
  追加constraintをmutation前に拒否する。status 0 deleteは作らず、`0B14`の
  正常完了後だけ日単位の完全snapshot置換を行う。旧unsafe tableはbackup・
  rebuild・reimportを要求する
- `TC`を公式45バイト配置と6項目race keyへ結び付け、発表`MMDDhhmm`と変更前後
  `HHmm`をlosslessに検証・保存する。native `NL_TC`、速報`RT_TC`、標準名
  `HASSOU_JIKOKU_CHANGE`でprovider順の改訂を1行へ反映し、current status 1以外、
  不正日付/競馬場/時刻、nullable・keyless・wrong-type・追加constraintをmutation前に
  拒否する。TCにはstatus 0 deleteを作らず、`0B14`の正常完了後だけ日単位の完全
  snapshot置換を行う。旧unsafe tableと旧標準名`COMMENT`はbackup・rebuild・
  reimportを要求する
- `HC`を公式現行60バイト配置と4項目キーへ結び付け、native `NL_HC`と標準名
  `HANRO`で7つの走破・lap time fieldを0.1秒単位で保持し、provider順の更新、
  status 0 exact delete、caller validation、SQLite/PostgreSQLのstrict schema
  preflightを一致させた。
  旧nullable/keyless/wrong-key tableや未承認の追加列・constraintは自動移行せず
  backup・rebuild・`SLOP` reimportを要求し、HCは蓄積系のみであることを明記した
- `HS`を現行HOSNの公式200バイト配置と3項目キーへ結び付け、native `NL_HS`と
  標準名`SALE`でprovider順の更新・exact delete・operation統計を一致させた。
  旧196バイトHOSEは引き続き拒否し、v2以前の既存tableは空でも値長から推測せず
  backup・rebuild・現行sourceからのreimportを要求する（現行互換の空`NL_HS`で
  marker/delimiterだけが欠ける場合を除く）。過去の馬齢は公式setup済み値を再解釈せず、
  市場名は当時表記を保持する。live本文はcoercion前に検証し、
  status 0の非key本文だけはexact eraseを妨げないopaque project policyとした
- `HR`を公式719バイト・6項目キーへ結び付け、3件の予備領域を数値化せず文字列で
  保持する全repeatを
  native/速報/JRA-VAN標準名`HARAI`へ保存。`HARAI`の払戻NULL化・重複行、
  coercion前validation欠落、unsafe schemaの見逃し、PostgreSQL同一キー操作の
  統計過少計上を修正。2004-08-14より前の同長114バイト領域は三連単と誤解釈せず
  hexでlossless保持し、現行三連単列と区別する。公式に本文値の規定がない中止状態9も
  本文を払戻として意味変換せず、raw監査値とキー・状態を保持する
- `AV`を公式78バイト・7項目キーへ結び付け、native/速報/JRA-VAN標準名の
  主キーを`NOT NULL`で統一。旧status 0はexact delete、現行status 1/2と
  2021年前後の事由blank/000〜003を両立し、旧`AVOIDENCE`単独構成、不正key・
  本文・unsafe schemaをSQLite/PostgreSQLのmutation前に拒否
- `SE`の現行555バイト全sliceをSDK 5.0.0 manifestへ結び付け、native/速報/
  JRA-VAN標準名の主キーを公式8項目（末尾`KettoNum`）へ統一。旧7項目・keyless・
  不正型・追加一意制約・deferrable主キーはmutation前に拒否し、個別取消、4予約領域、
  馬体重/増減の整数kg、status Aの本賞金0円をSQLite/PostgreSQLで保持
- MCP向け`TABLE_METADATA`をnative 80表とJRA-VAN標準54表の全134実DDLへ
  結び付け、列名・型・論理NULL可否・主キー・索引対象が実在する物理列と一致する
  よう修正。適用前に各backendの実catalogを照合し、SQLiteは旧版の表示専用疑似列を
  除去、PostgreSQLは物理列へcommentを適用、Dualは各backend固有の構文で処理する。
  MCP exportは破壊的な物理metadata契約を明示するversion 2.0.0へ更新
- JV-Link COM class 未登録時の診断を、公式SDKが提供する同じbit数のJV-Linkと、
  jrvltsqlでリリース検証済みの32-bit経路を区別する案内へ修正
- `NL_SK` の公開メタデータに欠けていた曽祖父母8頭の繁殖登録番号を追加し、
  parser が保持する3代14頭分の血統番号と一致

## [1.6.10] - 2026-08-11

### Fixed

- write-through cache への書き込みを parsed record 単位ではなく `jv_read` buffer
  単位に変更。full-struct parser（H1 は 28,955 byte の buffer から 1,485 行、
  H6 は 102,890 byte から 4,896 行）は 1 つの buffer を多数の行に展開し、各行が
  同一の `_raw` を持つため、同じ blob が行数分だけ追記されていた。実測（RACE/option=4）
  では、約 10 分間で 21.8 GB・99.9% が重複（同一範囲の実データは約 80 MB）。
  書き込みレートは別計測で 4,230 MB/min、修正後に同一範囲を再実行すると
  10.17 MB/min・重複 0% になった（2 つは別々の計測で、一方から他方は導出できない）。
  `_raw` の契約と yield される record の形は変更なし
- `JVRead` の `-402`（0 byte の破損ファイル）を、`JVRead` が返した exact filename
  だけを `JVFiledelete` で削除し、同一の `JVOpen` context を再オープンして自己修復。
  再ダウンロード完了・file count・`last_file_timestamp` の一致を確認し、既に caller へ
  返した prefix を読み飛ばして重複なしで継続する。再試行は最大 2 回で、確認できない
  条件はすべて fail closed。`-403` は同一ファイルの一部 record を既に返している
  可能性があるため、best-effort 削除のうえ fail closed とし、危険な位置再開はしない
- append-only の raw cache を fetch 開始前の byte checkpoint へ rollback するよう変更。
  generator の途中放棄、replay 不完了、index 更新失敗でも半端な cache を残さない。
  複数日 range の complete index は一時ファイルからの atomic replace で一括確定する
- `--from/--to` と cache 完全性の意味を安全側へ統一。option=2 は `JVOpen` が
  `--from` を取得範囲として扱わないため、既存 NL cache を含めて cache をバイパスし、
  `cache build/rebuild --option 2` は誤った完全範囲を作る前に fail loud する
- HC/WC を日付なし master として扱わず、時系列の `ChokyoDate` で `--to` filter と
  cache 日付を判定。対応する event date を持たない master 行を検出した場合は完全
  cache marker を付けず、同一取得の部分 cache append も rollback する
- setup開始境界の修正前に作成された schema v2 の完全性 marker を schema v3 で
  失効させ、旧 raw と active raw を分離

### Changed

- `fetch --option 2` の説明と `--from` の help を公式仕様に合わせて修正。`fromtime`
  は任意の過去週を選択するものではなく、現在の開催サイクル内の継続性を管理する
  ものであること、日曜・月曜は 2 つの開催サイクルにまたがりうることを明記
  （ドキュメントと help のみの変更で、取得と cache の挙動は変更なし）
- `config/config.yaml.example` の `databases.postgresql` に `connect_timeout` と
  `sslmode` を built-in 既定と同じ値（10 / prefer）で追記

### Added

- `tests/test_historical_cache_write_through.py`（新規）: buffer 単位の cache 書き込み
  回帰テスト。5 ケース中 4 ケースは本修正前には失敗する
- `tests/test_jvd_self_repair.py`（新規）: `JVRead` `-402`/`-403` の自己修復と
  fail-closed 条件の網羅テスト

## [1.6.9] - 2026-07-21

### Fixed

- PostgreSQL の `_get_existing_primary_key_columns()` / `_get_primary_key_columns()` /
  `table_exists()` を `to_regclass()` ベースに統一し、search_path 外のスキーマにある
  同名テーブルとの誤結合・`UndefinedTable` 例外を修正
- JV-Link 戻り値 `-100` を JVOpen/JVRTOpen 関連として誤配置していたのを修正
  （公式仕様書では `-100` は JVSetUIProperties/JVSetServiceKey 等の戻り値で、
  JVOpen/JVRTOpen の戻り値ではない）
- `scripts/quickstart.py` が JVInit の戻り値 `-100`〜`-103` を「サービスキー未設定/無効/
  期限切れ」と誤解釈していたのを修正。JVInit は `-101`〜`-103` のみを返し、いずれも
  sid パラメータの形式エラーであり、サービスキー状態（`-301`〜`-303`、JVOpen/JVRTOpen
  の戻り値）とは無関係
- `src/fetcher/base.py`・`src/fetcher/historical.py` の `-201`/`-202`/`-203` に関する
  誤ったコメント（「データベースビジー」「ファイルビジー」「セットアップ未完了」）を、
  公式仕様書に基づく正しい説明に修正（リトライ対象コードの集合自体は変更なし）

### Added

- `tests/test_jvlink_constants.py`（新規）: エラーコード定数とメッセージの網羅テスト
- `tests/test_postgresql.py`: search_path 切り替え時の `table_exists()`/`_get_existing_columns()`/
  `_get_existing_primary_key_columns()` 解決を検証する統合テスト
- `tests/test_quickstart_cli.py::TestAnalyzeErrorJVInitCodes`: JVInit vs JVOpen/JVRTOpen
  のエラーコード判定の回帰テスト

## [1.6.8] - 2026-07-18

### Added

- JRA SE の raw 固定幅値を保持したまま、走破タイム、上がり3F、馬体重、増減、着順、馬番の canonical 数値列を追加
- SQLite/PostgreSQL の additive migration と primary-key 検証、および実レコード例を固定した parser contract test を追加

## [1.6.7] - 2026-07-15

### Fixed

- 速報・蓄積ストリーム中の `JVRead -2` をデータなしとして扱わず、途中まで取得した応答を正常終了として commit しないよう修正

## [1.6.6] - 2026-07-15

### Fixed

- dual mode で secondary PostgreSQL が接続不能な場合は migration/verification 対象から除外し、documented best-effort 動作どおり primary の収集を継続

## [1.6.5] - 2026-07-15

### Fixed

- `JVRead` が正の長さと空バッファを返した不完全な速報取得を失敗として扱い、0B14 の既存 snapshot を空または部分データで置換しないよう修正
- dual SQLite/PostgreSQL の additive schema migration を各 backend へ個別適用し、PostgreSQL の小文字 table identifier を誤って引用して追加列移行が止まる問題を修正

## [1.6.4] - 2026-07-15

### Fixed

- 非対話 `daily_update.py` でも外部 bridge の未購読例外を正常な spec スキップとして扱い、0B14/0B51 など任意購読 feed が未契約でも他 feed の収集を継続するよう修正

## [1.6.3] - 2026-07-15

### Fixed

- 外部 bridge の `JVLinkBridgeError` を未購読・busy の正常なリトライ判定に含め、任意 spec の未購読で同一 polling cycle の正常データを rollback しないよう修正
- JVRead の回復可能エラーも不完全取得として追跡し、欠損した 0B14 応答で既存の開催変更 snapshot を置換しないよう修正
- 外部 bridge 初期化失敗時に realtime monitor の health を停止状態へ更新するよう修正

## [1.6.2] - 2026-07-15

### Fixed

- `DataKubun=9` を RA/SE/WF の中止状態として保持しつつ、オッズ・票数など他レコードでは削除命令として処理するよう修正
- 0B14 のパース失敗を検知した場合、不完全な速報開催情報スナップショットで既存行を置換しないよう fail-closed 化
- 一時的な JV-Link / DB エラー後も background realtime polling を継続するよう修正
- 再利用される historical/realtime fetcher の統計を呼び出しごとに初期化し、前回の失敗が次の spec/key に混入しないよう修正
- realtime polling 中の全スキーマ準備を常駐プロセスにつき一度に制限し、締切前ポーリングの不要な DDL/metadata 負荷を削減

## [1.6.1] - 2026-07-15

### Fixed

- 非対話の JRA daily sync 経路で、坂路調教 `SLOP` / `NL_HC` とウッドチップ調教 `WOOD` / `NL_WC` を通常差分として毎日取得するよう修正
- `daily_sync.bat` の既定 `JRA_DAILY_UPDATE_SPECS` に `SLOP,WOOD` を追加し、Windows タスクスケジューラ実行でも調教データが初回セットアップ後に stale にならないよう修正
- MING、速報開催情報、WIN5 の定期収集と購読エラー処理を修正
- RA/SE の公式拡張レイアウトとマイニング領域の位置を修正し、不正レコードを fail-closed に変更
- WIN5 (`WF`) を公式7,215-byte形式へ更新し、有効票数5件と払戻243件を欠落なく保存
- SQLite/PostgreSQL の速報取り込みをトランザクション単位で原子的にし、途中失敗時は全件 rollback
- 0B16 を `JVWatchEvent` のイベントキー専用として日付指定ポーリングから除外

### Notes

- 公開リリースには外部 collector ランタイム変更を含めていません
- `NL_WF` / `RT_WF` に公式WF形式の列を追加する additive migration を含みます

## [1.6.0] - 2026-06-16

### Fixed

- JV-Data490 の HC / AV / H6 / O1〜O6 レイアウト不整合を修正
- 展開済みオッズ・払戻行を保持できるよう保存キーと不完全な primary-key 行の扱いを修正
- SQLite / PostgreSQL import、PostgreSQL batch insert grouping、migration metadata、realtime expanded-record storage を堅牢化

### Notes

- 既存 DB に旧 O1 / H6 / HC / AV 関連テーブル定義がある場合は、対象レコードの再 import 前に table recreation または migration を確認してください

## [1.5.0] - 2026-06-11

### Added

- HR の主要払戻配列を複数エントリ抽出へ拡張
  （3件の予備領域を含む完全化と標準名保存は2.0.0で実施）
- コーナー通過順位を最大4セットの配列として収集
- `0B12` / `0B15` の daily sync 統合を追加
- JVOpen/JVRTOpen の対応データ種別、レコード種別、保存先テーブル、運用コマンドをまとめた `docs/data_support.md` を追加
- 初回ユーザー向けの実行順序をまとめた `docs/getting_started.md` を追加
- SQLite / PostgreSQL 共通の範囲指定つき時系列 quickstart `quickstart_timeseries.bat` を追加

### Changed

- 運用環境固有のバックアップ除外設定を `.gitignore` に追加
- 公開ドキュメントを日本語表記へ統一
- README と MkDocs ホームを、初回導線・目的別コマンド・重要なデータ区分が一目で分かる構成へ整理
- `quickstart.bat --yes --include-timeseries` の既定取得範囲をドキュメントに明記
- `quickstart.bat` は SQLite 既定の通常セットアップに戻し、PostgreSQL 専用の `quickstart_postgres_timeseries.bat` 呼び出しを削除
- SQLite でも `quickstart.bat --yes --include-timeseries` または `jltsql realtime odds-timeseries --db sqlite` で公式 `TS_O1/TS_O2` を保存できることを明記
- `quickstart.bat` 完了時に SQLite 用 `daily_sync.bat` の Windows タスクスケジューラ登録を確認するよう変更
- `quickstart_postgres_timeseries.bat` 完了時に Windows タスクスケジューラ登録を確認するよう変更
- `install_tasks.ps1` で `daily_sync.bat` の DB 種別・日付窓・PostgreSQL 環境変数永続化を指定可能に変更

## [1.4.1] - 2026-06-08

### Fixed

- Windowsタスクからの日次同期で実行場所を正しく復元し、非対話更新の失敗を
  呼び出し元へ返すように修正

## [1.4.0] - 2026-05-03

### Added

- PostgreSQL 向け JRA-VAN 時系列オッズ取得導線を追加
  - `quickstart_postgres_timeseries.bat`
  - `fetch_timeseries_postgres.bat`
  - `daily_sync.bat`
- 公式1年保持の `0B41/0B42` を `TS_O1/TS_O2` に保存する導線を整理
- 開催週の速報オッズ `0B30` 系から `TS_O1`〜`TS_O6` を蓄積する導線を追加
- 展開済みオッズ行の直接保存と PostgreSQL 複数行 INSERT を追加
- JRA データコレクタ単体のアーキテクチャ / PostgreSQL / 時系列オッズ / スクリプトのドキュメントを追加

### Fixed

- JRA-VAN 時系列オッズキーの生成を修正
- 空欄・未発売系オッズ値を PostgreSQL 保存前に正規化
- O1〜O6 の展開済みパーサー出力をテスト側でも正しく扱うよう修正
- PostgreSQL 複数行 INSERT のプレースホルダ生成を修正

### Changed

- PostgreSQL 時系列オッズのクイックスタート名をデータコレクタ汎用名へ変更
  - 新しい名前: `quickstart_postgres_timeseries.bat`
- 古いスクリプト README を削除し、現行ドキュメントへ集約
- 公開ドキュメントから下流システム固有の表現と内部パス例を削除

## [1.3.0] - 2026-04-22

### Added

- **二重書き込みモード** を追加
  - SQLite を primary としつつ PostgreSQL へ同時書き込み
  - `src/database/dual_handler.py` を新設
- **PostgreSQL 移行支援** を追加
  - 既存 SQLite スキーマの PostgreSQL 側反映と移行経路を整備
- migration / dual-write 向けテストを追加
  - `tests/test_migration.py`

### Fixed

- DDL が dual-write 時に mirror 側へ確実に反映されない問題を修正
- realtime / verify 周辺の false positive とメッセージ不整合を修正
- batch importer / realtime updater の PostgreSQL 併用時の整合性を改善

### Changed

- CLI と database 初期化フローを dual-write / PostgreSQL mirror 前提で整理
- realtime monitor の DB 書き込み経路を見直し
- config example を PostgreSQL 併用前提に更新

## [1.2.0] - 2026-04-17

### ⚠️ Breaking Changes

- **地方競馬（NAR）サポートを廃止** — NAR/NV-Link 関連機能をすべて削除。本ツールは JRA（中央競馬）専用となります。

### Added

- レースデー監視ツール群
  - `scripts/raceday_verify.py` — 17項目の自動検証（スキーマ・RT_・NL_・オッズ・払戻・smoke test）
  - `scripts/raceday_scheduler.py` — 各レース後に自動検証を実行するスケジューラ（12R + 事後チェック）
  - `scripts/raceday_tmux.sh` — tmux 3ウィンドウ構成の一発起動スクリプト
- Claude Code `/loop` との連携 — 検証レポートを読んで問題があれば自動でコード修正・PR作成
- NL_SE / RT_SE インデックス追加（`idx_nl_se_date`, `idx_rt_se_date` など）
- テストカバレッジ大幅拡充（1,256件: 1,256 pass）
  - `test_cache_manager.py` — CacheManager 全API（NL_/RT_ 読み書き、インデックス、スレッドセーフ）
  - `test_utils_config.py` — Config.get、環境変数展開、バリデーション
  - `test_utils_lock_manager.py` — acquire/release、競合検出、stale lock 自動削除

### Fixed

- `quickstart.py`: `BatchProcessor` に削除済み `data_source` 引数を渡していたクラッシュを修正
- `raceday_verify.py`: `--date` 引数の長さ検証を追加
- `updater.py`: INSERT OR REPLACE で UPSERT が正常動作していたにもかかわらず誤解を招くTODOコメントを削除

### Changed

- `quickstart.bat`: `--option` を `--mode` に修正、S3キャッシュ同期ステップを追加
- `pyproject.toml`: pytest `--basetemp=C:/tmp/pytest-jrvl` 追加（Windows AppData 権限エラー対策）

### Documentation

- README.md を全面書き直し（要件・クイックスタート・CLI・レースデーワークフロー・キャッシュ構造）

## [1.1.0] - 2025-02-08

### Added
- ワンコマンドインストーラー (`install.ps1`) — `irm ... | iex` で一発セットアップ
- 自動アップデート機能 (`jltsql update`, `jltsql version --check`)
- H1/H6パーサーのフルストラクト対応（28,955 / 102,890バイト）
- quickstart.bat で JRA-VAN 契約ページの自動オープン
- テストカバレッジ大幅拡充（1,247件: 1,239 pass, 8 skip）
- JRA実データテストフィクスチャ（27パーサー, 81レコード）

### Changed
- 32-bit Python 必須に変更（64-bit非対応を明確化）

### Fixed
- H1/H6パーサーのフルストラクト解析の不具合修正
- テスト3件の失敗修正（wrapper挙動との整合性）

### Documentation
- Windows専用であることを明確化
- ワンコマンドインストーラーをREADMEに追加
- クロスプラットフォーム検証の注記追加
- 入門 / リファレンス / ユーザーガイドを最新仕様に更新

## [1.0.0] - 2025-02-07

### Added
- 初回公開リリース
- JRA-VAN DataLab (JV-Link) 対応 — 38種パーサー
- SQLite / PostgreSQL データベース対応
- リアルタイムオッズ・速報データ監視
- quickstart.py 対話形式セットアップウィザード
- CLI コマンド（fetch, status, monitor, init）

[Unreleased]: https://github.com/miyamamoto/jrvltsql/compare/v2.1.2...HEAD
[2.1.2]: https://github.com/miyamamoto/jrvltsql/compare/v2.1.1...v2.1.2
[2.1.1]: https://github.com/miyamamoto/jrvltsql/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/miyamamoto/jrvltsql/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.10...v2.0.0
[1.6.10]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.9...v1.6.10
[1.6.9]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.8...v1.6.9
[1.6.8]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.7...v1.6.8
[1.6.7]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.6...v1.6.7
[1.6.6]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.5...v1.6.6
[1.6.5]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.4...v1.6.5
[1.6.4]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.3...v1.6.4
[1.6.3]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.2...v1.6.3
[1.6.2]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.1...v1.6.2
[1.6.1]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/miyamamoto/jrvltsql/releases/tag/v1.6.0
[1.5.0]: https://github.com/miyamamoto/jrvltsql/releases/tag/v1.5.0
[1.4.1]: https://github.com/miyamamoto/jrvltsql/releases/tag/v1.4.1
[1.4.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/miyamamoto/jrvltsql/releases/tag/v1.0.0
