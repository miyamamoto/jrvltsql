# JLTSQL テスト戦略

## 3層構造

| 層 | 実行場所 | 主な対象 | 証明できないこと |
| --- | --- | --- | --- |
| ローカル/CI | Python 3.12、JV-Link不要 | parser、schema、importer、state machine、CLI、配布物 | 実SDKから取得できること |
| 実接続integration | 認証済みWindows/JV-Link | 初期化、取得、parse、SQLite格納、再読込 | 別architectureや別SHAの動作 |
| release E2E | exact release SHAを配置した認証済み環境 | 新規取得、SQLite/PostgreSQL格納、状態更新、close/cleanup | 未実行のレコード種別やruntime |

## ローカル/CI

代表的な契約:

- `test_current_record_validation.py`: 全38種の物理レコード境界
- `test_*_official_contract.py`: 実装済み形式の公式offset、配列、schema、保存契約
- `test_retired_data_specs.py`: 2023年変更前dataspecのfail-closed拒否
- `test_realtime.py`, `test_expanded_record_storage.py`: 速報の更新・取消状態
- `test_integration.py`: parsed rowからSQLiteへのrouting、upsert、transaction
- `test_distribution_contents.py`: wheel/sdistに公開対象外資料を入れない
- `test_quickstart_cli.py`: installer、launcher、公開support表現

実行例:

```bash
python -m pytest tests/ -q \
  --ignore=tests/integration/ \
  --ignore=tests/e2e/ \
  -m "not slow" \
  --basetemp=.pytest-tmp-local
```

固定の総テスト数は正本にしません。CIは上記のdeterministic test tree全体を
実行します。公式record別契約は現時点では全38形式を網羅しておらず、未実装分を
ローカルsuiteの緑で代替しません。coverage matrixとreleaseで追加する比例テストは
対象PRのworklogを正本にします。

`fixtures/reconstructed_db/` は既存DB行から再構成した値回帰用fixtureです。
providerの保存済みraw byteではないため、offset・長さ・初期値・availabilityの
公式仕様証拠には数えません。

## 実接続integration

`tests/integration/test_jvlink_real.py` は明示的なopt-in時だけ動作します。

```cmd
set JLTSQL_RUN_REAL_INTEGRATION=1
py -3.12-32 -m pytest tests\integration\test_jvlink_real.py -v -s --no-cov
```

サービスキーはJRA-VAN DataLab/JV-Linkの正規設定経路で登録します。値をcommand、
log、worklogへ出力しません。詳細は `tests/integration/README.md` を参照します。

## standalone E2E

現存するJRA用scriptは次のとおりです。

- `e2e/e2e_jra_smoke.py`: 新規取得→parse→SQLite格納→query
- `e2e/e2e_error_recovery.py`: 実接続のエラー処理
- `e2e/e2e_edge_cases.py`: 既存JRA DBのread-only整合性確認

実行要件と非公開にすべき証跡は `tests/e2e/README.md` に記載します。

## リリース前ゲート

- [ ] `origin/master`から作ったexact release candidate full SHAである
- [ ] local focused/full suite、syntax、docs、distribution gateがgreen
- [ ] 公式最新版、変更履歴、スタッフ回答と全実装を再監査済み
- [ ] Claude Codeの批判的レビューとCodexの独立判定が完了
- [ ] unresolved review threadが0件
- [ ] 認証済みJV-Linkから少なくとも1件を新規取得
- [ ] candidate codeでparseし、SQLiteと必要なPostgreSQL経路へ保存・再読込
- [ ] 更新/削除/中止状態を物理削除と取り違えない
- [ ] `JVClose`と一時資源cleanupを確認
- [ ] mock、cache replay、旧SHAを実取得の代替にしていない
- [ ] 公開文書にcredential、raw payload、private runtime identityがない

現在のリリース検証済みarchitectureは32-bit Python + 32-bit JV-Linkです。
公式SDKのx64版を対応範囲へ加えるには、x64 SDKを実際に導入し、上記の新規取得・
parse・DB保存E2Eをexact candidate SHAで完走させます。
