# ローカル統合テスト

`tests/test_integration.py` は、parserが返す辞書と importer / SQLite の境界を
検証します。JV-Linkからの実取得テストではありません。

## 主な契約

- 全schemaを作成でき、再実行しても壊れない
- 主要native tableの現在の列契約が一致する
- RA/SE/HRなどを正しいtableへ保存してSQLで再読込できる
- 同一主キーの更新で重複行を作らない
- mixed record batchとtransaction統計が一致する
- 不正recordが成功件数へ混ざらない

テスト内のparsed dictionaryはimporter境界用の入力です。公式raw recordの
代用品ではなく、parser offset/lengthの証明には使いません。物理レコード契約は
`test_current_record_validation.py`と各`test_*_official_contract.py`が担当します。

## 実行

```bash
python -m pytest tests/test_integration.py -q --no-cov \
  --basetemp=.pytest-tmp-integration
```

PostgreSQL固有のmigration、key、transactionは対応するPostgreSQL test selectionを
別途実行します。実JV-Linkの取得・parse・格納は
`tests/integration/test_jvlink_real.py`を認証済みWindows環境で明示的に有効化します。

## 判定上の注意

- SQLiteの合成row保存だけでrelease acquisitionをgreenにしない
- 固定の列数・テスト総数を文書へ複製せず、test code/schemaを正本にする
- temporary DBを使い、テスト間でwriterや`--basetemp`を共有しない
- credential、raw payload、private runtime identityを出力しない
