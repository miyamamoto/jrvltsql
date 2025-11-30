# 統合テスト (Integration Tests)

## 概要

`test_integration.py` は、パーサー → インポーター → SQLiteの一連の流れを検証する統合テストです。

## テスト項目

### 1. テーブル作成テスト

#### `test_create_all_tables`
- `create_all_tables()` で全58テーブルが作成されることを確認
- 各テーブルが正しく存在することを検証
- 冪等性のテスト（複数回実行してもエラーにならない）

#### `test_table_column_counts`
- 主要テーブルのカラム数を確認
  - NL_RA: 48列 (レース詳細)
  - NL_SE: 70列 (馬毎レース情報)
  - NL_UM: 58列 (馬マスター)
  - NL_KS: 70列 (騎手マスター)
  - NL_HR: 95列 (払戻)
  - NL_O1: 25列 (オッズ)

### 2. データインポートテスト

#### `test_parse_and_import_ra_record`
- RAレコード（レース詳細）のパースとインポート
- データベースへのINSERT成功確認
- SELECTでデータ取得確認

#### `test_parse_and_import_se_record`
- SEレコード（馬毎レース情報）のパースとインポート
- 型変換の確認（文字列 → INTEGER/REAL）

### 3. 重複処理テスト

#### `test_duplicate_handling_with_replace`
- 同一主キーのレコードをINSERT OR REPLACEで処理
- 重複エラーが発生しないことを確認
- レコードが更新されることを確認（複製されない）

### 4. バッチインポートテスト

#### `test_batch_import_with_transactions`
- 50件のレコードをバッチインポート
- トランザクション処理の確認
- 統計情報（imported, failed, batches）の検証

#### `test_mixed_record_types_batch_import`
- 異なるレコードタイプ（RA, SE, HR）の混在インポート
- 各レコードが正しいテーブルに格納されることを確認

### 5. 型変換の統合テスト

#### `test_type_conversion_integration`
- INTEGER型への変換（Year, MonthDay, Kaiji等）
- REAL型への変換と10除算（Futan, BaTaijyu, Time, Odds等）
- TEXT型の保持
- NULL値の処理

### 6. エラーハンドリングテスト

#### `test_transaction_rollback_on_error`
- バッチ失敗時のロールバック
- 個別レコードでのリトライ
- 成功レコードと失敗レコードの統計確認

### 7. 主キー制約テスト

#### `test_primary_key_enforcement`
- 主キー制約の存在確認
- INSERT OR REPLACEの動作確認

### 8. エンドツーエンドテスト

#### `test_end_to_end_workflow`
- パース → インポート → クエリの一連の流れ
- 実際のワークフローシミュレーション

## 実行方法

### Windows（バッチファイル）

```bash
run_integration_tests.bat
```

### 直接実行

```bash
# py launcherを使用
py -3 -m pytest tests/test_integration.py -v

# pythonコマンドを使用
python -m pytest tests/test_integration.py -v

# 特定のテストのみ実行
pytest tests/test_integration.py::TestIntegration::test_create_all_tables -v

# カバレッジ付き実行
pytest tests/test_integration.py --cov=src --cov-report=term
```

### CI/CD環境

GitHub Actionsで自動実行されます：
```yaml
- name: Run comprehensive tests
  run: |
    pytest tests/test_comprehensive_integration.py tests/test_realtime.py tests/test_error_scenarios.py -v --cov=src --cov-report=xml --cov-report=term
```

## テストデータ

テストでは、以下のような簡略化されたレコードを使用します：

```python
# RAレコード例
{
    "headRecordSpec": "RA",
    "RecordSpec": "RA",
    "Year": "2024",
    "MonthDay": "0601",
    "JyoCD": "06",
    "RaceNum": "11",
    "Hondai": "テストレース",
    "Kyori": "2000",
}

# SEレコード例
{
    "headRecordSpec": "SE",
    "RecordSpec": "SE",
    "Year": "2024",
    "Umaban": "01",
    "KettoNum": "2024012345",
    "Bamei": "テスト馬",
    "Futan": "550",    # → 55.0 kgに変換
    "Odds": "0015",    # → 1.5に変換
}
```

## 一時データベース

各テストは独立した一時データベースを使用します：
- `tempfile.NamedTemporaryFile` で自動生成
- テスト終了後に自動削除
- テスト間の干渉を防止

## 重要な検証ポイント

### 1. PRIMARY KEY制約

以下のテーブルにPRIMARY KEY制約が定義されています：

- **NL_RA, RT_RA** (レース詳細)
  ```sql
  PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)
  ```

- **NL_SE, RT_SE** (馬毎レース情報)
  ```sql
  PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban)
  ```

- **NL_UM** (馬マスター)
  ```sql
  PRIMARY KEY (KettoNum)
  ```

### 2. INSERT OR REPLACE

DataImporterはデフォルトで `INSERT OR REPLACE` を使用：
- 同一主キーのレコードは上書き
- 重複エラーが発生しない
- データ再インポートが安全

### 3. 型変換ルール

#### INTEGER型
- Year, MonthDay, Kaiji, Nichiji, RaceNum, Umaban等
- 文字列から整数に変換

#### REAL型（10で割る）
- TanOdds, FukuOdds, Odds (オッズ系)
- Time, HaronTime (タイム系)
- Futan, BaTaijyu, ZogenSa (重量系)

#### REAL型（そのまま）
- Honsyokin, Fukasyokin (賞金系)
- HyoTotal (票数系)

## トラブルシューティング

### pytest not found
```bash
pip install pytest
```

### Import errors
```bash
# プロジェクトルートから実行
cd C:\Users\mitsu\work\jrvltsql
pytest tests/test_integration.py -v
```

### Database locked errors
- 一時DBファイルが残っている可能性
- `C:\Users\{user}\AppData\Local\Temp\` 配下の `.db` ファイルを削除

## 参考資料

- [pytest公式ドキュメント](https://docs.pytest.org/)
- [SQLite公式ドキュメント](https://www.sqlite.org/docs.html)
- [JV-Data仕様書 Ver.4.9.0.1](https://jra-van.jp/)
