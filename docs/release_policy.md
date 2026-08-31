# リリース運用方針

この文書は、`jrvltsql` の変更を通常リリースと緊急 hotfix に分け、
運用中の環境を pull request ごとに更新しないための正本です。

## 3つの操作を分離する

次の3つは別の操作です。前の操作が成功しても、次の操作を自動的に行いません。

1. **merge**: pull request の変更をソース管理へ統合する。
2. **release**: 検証済みの不変commitからtagと配布artifactを作る。
3. **adopt**: 特定の運用環境が、そのreleaseを明示的に採用する。

`master`へのmergeはreleaseでもdeployでもありません。運用環境は`master`、branch名、
短縮SHA、または`:latest`を追従せず、正式tag、full commit SHA、artifact hashを固定します。

## リリース経路

| 経路 | 対象 | 統合先 | 公開単位 |
| --- | --- | --- | --- |
| 通常リリース | 機能、性能改善、リファクタ、観測性、緊急でないbug fix | `master` | 複数PRをまとめた予定release |
| 緊急 hotfix | 運用中releaseの重大な障害に対する最小修正 | 対応する`stable/X.Y` | patch release |

分類が決まらない場合は通常リリースとして扱います。緊急性はテストやレビューを省略する
理由ではなく、無関係な変更を混ぜずに検証範囲を絞る理由です。

## ブランチとtag

| 名前 | 用途 | 規則 |
| --- | --- | --- |
| `master` | 通常開発の統合 | release候補品質を保つが、mergeだけでは公開・採用しない |
| `release/X.Y.Z` | 通常releaseの安定化 | `master`の選定commitから作る一時branch。release blocker以外を追加しない |
| `stable/X.Y` | 運用中のrelease系列 | 対応するGA tagから作り、承認済みhotfixだけを入れる |
| `hotfix/X.Y.Z-<name>` | 緊急修正 | 実際に採用中の正確なtagから作る一時branch |
| `vX.Y.ZrcN` | release candidate | 開発・検証用。運用中releaseを自動更新しない |
| `vX.Y.Z` | 正式release | merge後の不変commitだけに付ける |

`stable/X.Y`がまだ存在しない系列で初めてhotfixを行う場合は、現在採用中のGA tagから
作成します。branchの先端ではなく、採用中tagのcommitを起点として記録します。

## 通常リリース

通常変更はpull requestとして`master`へ統合します。各PRをmergeしてもreleaseしません。
予定したrelease単位で次の手順を実行します。

1. 対象PRとscopeを確定し、`master`のfull SHAから`release/X.Y.Z`を作る。
2. `vX.Y.Zrc1`などのcandidateを作り、wheel/sdistとhashを保存する。
3. unit/integration test、distribution smoke、SQLite/PostgreSQL、対象変更に応じた
   JV-Link/provider境界を検証する。
4. 開発用collectorへcandidateを明示的に導入し、収集・再取込・transaction・再起動を
   riskに応じて確認する。
5. release blockerだけを修正する。新機能や無関係な高速化は次の通常releaseへ送る。
6. cleanなmerge済みfull SHAから正式tagとartifactを作り、GitHub Releaseへ検証結果、
   既知の制約、移行、rollbackを記載する。
7. 運用環境は別の採用操作でtag、full SHA、artifact hashを固定する。

通常releaseは、月次または明示したmilestone単位を基本とします。変更が揃っていない場合は
日付だけを理由に公開しません。

## 緊急 hotfix

### hotfix候補になる障害

- 公式上正しいデータが取り込めず、運用中の収集が停止する。
- 保存データが削除、衝突、誤変換、部分commitなどにより破損する。
- 認証情報、個人情報、秘密値、配布物の安全性に重大な問題がある。
- 運用中releaseが起動不能、継続不能、または誤った外部操作を行う。
- 現在採用中のreleaseで再現する重大なcorrectness defectがある。

### hotfixにしない変更

- 機能追加、使い勝手の改善、通常のログ追加。
- 高速化、内部リファクタ、将来のための設計変更。
- 運用中releaseで再現していない仮説上の問題。
- 複数の独立した修正をまとめたもの。
- greenであることだけを理由に早く取り込みたいPR。

### hotfix手順

1. 影響を受ける採用中version、再現条件、severity、回避策の有無を記録する。
2. 採用中の正確な`vX.Y.Z`から`hotfix/<next-patch>-<name>`を作る
   （例: `v2.0.0`に対する`hotfix/2.0.1-import-loss`）。
3. 修正前に最小の回帰testが赤になることを確認し、その失敗をPRへ記録する。
4. 修正を障害原因と回帰testに必要な範囲へ限定する。schema変更、性能改善、整理を便乗させない。
5. focused testに加え、影響するDB/provider/transaction/runtime境界を実測する。
6. unresolved review threadを0件にし、cleanなfull SHAを凍結する。
7. 対応する`stable/X.Y`へmergeし、patch candidate、smoke、正式patch releaseの順で公開する。
8. 同じrepairを別PRで`master`へforward-portし、release記録から双方を参照する。
9. 運用環境はrollback可能な状態でpatch releaseを明示採用する。

原因が分からない、再現できない、または修正が複数領域へ広がる場合は、緊急という理由で
mergeせず、回避策を優先して通常の調査・release経路へ戻します。

## PRの分類とラベル

maintainerはPRの調査開始時にrelease trackとriskを記録します。推奨ラベルは次のとおりです。

| ラベル | 意味 |
| --- | --- |
| `release:normal` | 通常releaseへ入れる変更 |
| `release:hotfix-candidate` | 緊急性を調査中。まだhotfix承認ではない |
| `release:hotfix-approved` | 再現・severity・最小scopeが確認済み |
| `release:blocker` | candidateの公開または採用を止める問題 |
| `backport:X.Y` | 対象stable系列へbackportする変更 |
| `risk:data-integrity` | key、delete、型変換、完全性、transactionに影響 |
| `risk:provider` | JV-Link、COM、取得、buffer、dialogに影響 |
| `risk:database` | SQLite/PostgreSQL schemaまたはDMLに影響 |
| `risk:security` | credential、path、artifact、権限に影響 |
| `risk:performance` | 性能を目的とし、意味不変性とbenchmarkが必要 |

`release:hotfix-candidate`は優先調査の印であり、検証前のmerge許可ではありません。

## 必須gate

| gate | 通常release | 緊急 hotfix |
| --- | --- | --- |
| 対象full SHAとclean worktree | 必須 | 必須 |
| 修正前に赤となる最小回帰test | validator/bug fixで必須 | 必須 |
| 変更領域のfocused test | 必須 | 必須 |
| workflow相当のtest/lint/build | 必須 | 必須 |
| SQLite/PostgreSQL実測 | DBに影響する場合 | DBに影響する場合 |
| JV-Link/provider実測 | 取得経路に影響する場合 | 取得経路に影響する場合 |
| 性能benchmark | 性能主張がある場合 | hotfixへ性能変更を混ぜない |
| release notes、移行、rollback | 必須 | 必須 |
| unresolved review thread | 0件 | 0件 |
| RC/開発環境smoke | 必須 | 範囲を絞って必須 |

測定できない項目は合格ではありません。releaseに必要な環境やcredentialが無い場合は、
未実施理由と実行すべきcommandを記録し、その証拠が必要なriskなら公開・採用を止めます。

## versionと配布物

- 後方互換のbug fixはpatch、後方互換の機能追加はminor、互換性を壊す変更はmajorを上げます。
- 緊急か通常かはversion番号ではなくrelease経路の違いです。予定されたbug-fix releaseも
  patch versionになる場合があります。
- wheel、sdist、GitHub Release、source version、CLI versionは同じversionでなければなりません。
- 配布物はmerge後のfull SHAから再構築し、candidate branchで作った古いartifactを流用しません。
- release記録にはtag、full SHA、artifact SHA-256、検証結果、既知の制約を残します。

## 運用環境への採用とrollback

release公開後も運用環境を自動更新しません。採用時には現在版、採用版、artifact hash、
DB移行要否、backup、smoke、rollback先を記録します。

rollbackは以前の不変tag/artifactを再採用して行います。schemaや保存形式が変わるreleaseでは、
コードだけを戻せると仮定せず、事前backup、互換性、再構築またはrestore手順をrelease notesへ
明記します。

## 現在のreleaseを確認する

GitHub上の最新commitやopen PRではなく、次を区別して確認します。

- 開発中candidateのfull SHA。
- GitHubへmerge済みのfull SHA。
- 公開済みの正式tagとartifact hash。
- 各運用環境が実際に採用しているversionとfull SHA。

どの版を使ったか特定できない実行結果は、releaseまたはhotfixの検証証拠に使いません。
