# JLTSQL テスト戦略

## テスト3層構造

```
┌─────────────────────────────────────────────────┐
│  Layer 3: E2E テスト (実機 A6, COM API 必須)    │  手動実行
│  tests/e2e/                                      │  VNC/RDP 経由
├─────────────────────────────────────────────────┤
│  Layer 2: 統合テスト (実機 A6, COM API 必須)    │  手動実行
│  tests/integration/                              │  pytest 形式
├─────────────────────────────────────────────────┤
│  Layer 1: ユニットテスト (モック/フィクスチャ)   │  CI (GitHub Actions)
│  tests/test_*.py                                 │  自動実行
└─────────────────────────────────────────────────┘
```

## Layer 1: ユニットテスト（CI で自動実行）

| テストファイル | 対象 |
|---------------|------|
| `test_parser.py`, `test_parsers.py` | JV-Data 固定長パーサー |
| `test_ra_parser_jravan.py` | RA レコードパーサー |
| `test_nu_parser.py` | NU レコードパーサー |
| `test_converters.py` | 型変換ユーティリティ |
| `test_database.py` | DB ハンドラ (SQLite, mock) |
| `test_importer.py` | データインポーター |
| `test_all_schemas.py` | スキーマ定義の整合性 |
| `test_all_databases.py` | 複数DB対応 |
| `test_jra_fixtures.py` | JRA フィクスチャデータ検証 |
| `test_error_scenarios.py` | エラーパターン |
| `test_nar_502_recovery.py` | -502 エラーリカバリ (モック) |
| `test_historical_502.py` | 502 履歴テスト |
| `test_updater.py` | バックグラウンド更新 |
| `test_quickstart_cli.py` | CLI 引数パース |
| `test_log_rotation.py` | ログローテーション |
| `test_indexes.py` | インデックス定義 |
| `test_installer.py` | インストーラー |
| `test_realtime.py` | リアルタイムフェッチャー |
| `test_metadata_application.py` | メタデータ適用 |
| `test_performance_benchmarks.py` | パフォーマンス |
| `test_coverage_expansion.py` | カバレッジ拡張 |
| `test_e2e_comprehensive.py` | 疑似E2E (モック) |
| `test_comprehensive_integration.py` | 疑似統合 (モック) |

**実行方法:** `pytest tests/test_*.py -v`

**特徴:**
- COM API 不要（モック/フィクスチャベース）
- macOS/Linux/Windows で実行可
- GitHub Actions で自動実行

## Layer 2: 統合テスト（A6 手動実行）

| テストファイル | 対象 |
|---------------|------|
| `integration/test_jvlink_real.py` | JV-Link 実接続・取得・パース・格納 |

**実行方法:** A6 上で `pytest tests/integration/ -v -s`

**特徴:**
- 実際の COM API を使用
- pytest 形式（`-s` でリアルタイム出力必須）
- `JVLINK_SERVICE_KEY` 環境変数が必要

## Layer 3: E2E テスト（A6 手動実行）

| テストファイル | 対象 |
|---------------|------|
| `e2e/e2e_jra_smoke.py` | JRA 全フロー: 取得→パース→DB→クエリ検証 |
| `e2e/e2e_nar_smoke.py` | NAR 全フロー: 取得→パース→DB→クエリ検証 |
| `e2e/e2e_error_recovery.py` | エラーリカバリ（未来日、-502、再初期化） |
| `e2e/e2e_edge_cases.py` | 異常レース検証（既存DB読取専用、COM API不要） |

**実行方法:** A6 上で VNC/RDP 経由、スタンドアロン Python スクリプト

**特徴:**
- pytest 不要（スタンドアロン実行可能）
- PASS/FAIL サマリ出力
- テスト用 DB は自動作成・自動削除
- `-502` 発生時はスキップ扱い

## CI vs 手動テスト

| テスト | CI (GitHub Actions) | A6 手動 |
|--------|:-------------------:|:-------:|
| Layer 1: ユニットテスト | ✅ | ✅ |
| Layer 2: 統合テスト | ❌ (COM API 必須) | ✅ |
| Layer 3: E2E テスト | ❌ (COM API 必須) | ✅ |

## テスト実行チェックリスト

### リリース前チェック

- [ ] **CI パス確認**: GitHub Actions の全テストが緑
- [ ] **JRA E2E**: `e2e_jra_smoke.py` が PASS
- [ ] **NAR E2E**: `e2e_nar_smoke.py` が PASS
- [ ] **エラーリカバリ**: `e2e_error_recovery.py` が PASS
- [ ] **既存DB検証**: `data/keiba.db` の主要テーブルにレコードが存在

### 月次チェック（推奨）

- [ ] `scripts/check_data_quality.py` でデータ品質確認
- [ ] 統合テスト (`tests/integration/`) を最新データで実行

## 異常レース・エッジケース検証項目

`e2e_edge_cases.py` で検証する項目一覧:

### データ区分と異常区分コード

| コード | IJyoCD 意味 | keiba.db 件数 | 検証内容 |
|--------|-------------|--------------|---------|
| 0 | 正常 | ~2,577K | 馬名・タイム・着順が非空 |
| 1 | 出走取消 | ~9.2K | 着順=0、タイム=空 |
| 2 | 発走除外 | ~1.4K | 着順=0 |
| 3 | 競走中止 | ~3.4K | - |
| 4 | 失格 | ~10.9K | - |
| 5 | 落馬(再騎乗) | ~384 | - |

| DataKubun | 意味 | 件数 | 検証内容 |
|-----------|------|------|---------|
| 9 | 中止レース | 296 | 払戻データなし/空 |

### 検証シナリオ

1. **出走取消 (IJyoCD=1)**: 着順・タイムが空であること、同一レースの正常馬データが正しいこと
2. **発走除外 (IJyoCD=2)**: 着順が空であること
3. **中止レース (DataKubun=9)**: 払戻 (HR) が空/なしであること
4. **大量取消レース**: 2005/10/05 B6 R10 (7頭取消) — 払戻・返還フラグの整合性
5. **1頭立てレース**: 不成立フラグ (FuseirituFlag) の確認
6. **東日本大震災 (2011/03)**: 震災前後のレース数推移、DataKubun 分布
7. **NL_NU テーブル**: 出走取消・競走除外専用テーブルの有無（DIFF spec で取得）
8. **RA-SE-HR クロス整合性**: 孤立レコード (RA のみ、SE のみ) の検出
9. **NULL・空文字**: 正常馬の馬名非空、完走馬のタイム非空

### 既知の所見

- **SyussoTosu (出走頭数)**: NL_RA の大半で `0` (歴史的データでは未設定)
- **NL_NU テーブル**: 現時点で未作成。RACE spec には含まれず、DIFF spec で取得される
- **NyusenTosu (入線頭数)**: 空の場合が多い

## 今後の改善案

1. **NARテーブル追加**: 現在 `keiba.db` に NAR テーブル (NN_*) が無い → NAR E2E で確認
2. **データスナップショット**: E2E テスト結果の件数を記録し、回帰検知
3. **自動化検討**: A6 上でタスクスケジューラ + バッチファイルによる定期実行
4. **既存DBクエリテスト**: `keiba.db` (1.4GB, JRA 131テーブル) に対するクエリ正当性テスト追加
