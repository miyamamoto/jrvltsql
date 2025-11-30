# JRVLTSQL - JRA-VAN Link To SQL

JRA-VAN DataLabの競馬データをSQLite/PostgreSQLにインポートするPythonツール

[![Tests](https://github.com/miyamamoto/jrvltsql/actions/workflows/test.yml/badge.svg)](https://github.com/miyamamoto/jrvltsql/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10+%20(32bit)-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](https://github.com/miyamamoto/jrvltsql/releases)

## What's New in v2.0.0

### Complete Data Integrity
- **全58テーブルにPRIMARY KEY制約を追加**: データの一意性を保証
- **スキーマ/パーサー完全一致**: 57/57パーサーがスキーマと整合（100%）
- **404ユニットテスト**: 全43パーサーを網羅的にテスト
- **11統合テスト**: エンドツーエンドの動作を検証

### New Tools
- **`scripts/validate_schema_parser.py`**: スキーマとパーサーの整合性チェックツール
- **`scripts/check_data_quality.py`**: データ品質検証ツール
- **`tests/test_parsers.py`**: 全パーサーの包括的なユニットテスト
- **`tests/test_integration.py`**: 統合テストスイート

### quickstart.py Improvements
- **新オプション追加**: `--db-path`, `--from-date`, `--to-date`, `--years`, `--no-odds`, `--no-monitor`, `--log-file`
- **対話形式のサービスキー入力**: より使いやすいセットアップ体験
- **Claude Code風モダンUI**: 視覚的に分かりやすいインターフェース

### Quality Assurance
- **100% スキーマ/パーサー整合性**: 57/57パーサーが検証済み
- **完全テストカバレッジ**: 全パーサーをユニット/統合テストで検証
- **データ品質検証**: 自動的なデータ整合性チェック

---

## 特徴

- **全38レコードタイプ対応**: 1986年以降の全競馬データ
- **58テーブル**: NL_38（蓄積系）+ RT_20（速報系）
- **完全なデータ整合性**: 全テーブルにPRIMARY KEY制約
- **SQLite標準**: 軽量・高速（PostgreSQLも対応）
- **レジストリー不要**: 設定ファイル/環境変数でサービスキーを管理
- **バッチ処理最適化**: 1000件/batch + 61インデックス
- **JV-Link API完全対応**: JVOpen/JVRTOpen の全データ種別に対応
- **品質保証**: 404ユニットテスト + 11統合テスト

## クイックスタート

### 1. インストール

```bash
pip install git+https://github.com/miyamamoto/jrvltsql.git
```

### 2. セットアップ

```bash
# 対話形式で初期設定（サービスキー入力 → 過去10年分のデータ取得）
jltsql quickstart
```

これだけで完了です。

## 必要要件

| 項目 | 要件 |
|------|------|
| OS | Windows 10/11 |
| Python | 3.10+ **(32bit版のみ)** |
| 会員 | JRA-VAN DataLab（月額2,090円） |

### Python 32bit版について

JV-Link COM APIは32bit専用のため、**Python 32bit版が必須**です。

```bash
# ビット数を確認
python -c "import struct; print(struct.calcsize('P') * 8, 'bit')"
```

64bit版しかない場合は、[Python公式サイト](https://www.python.org/downloads/windows/)から「Windows installer (32-bit)」をダウンロードしてください。

## 設定

サービスキーは以下のいずれかで設定：

```bash
# 環境変数（推奨）
set JVLINK_SERVICE_KEY=XXXX-XXXX-XXXX-XXXX-X
```

```yaml
# config/config.yaml
jvlink:
  service_key: "XXXX-XXXX-XXXX-XXXX-X"
```

## コマンド一覧

```bash
jltsql quickstart              # 対話形式で初期セットアップ
jltsql quickstart --years 5    # 過去5年分のデータ取得
jltsql quickstart --no-odds    # オッズデータを除外
jltsql quickstart --no-monitor # セットアップ後の監視をスキップ
jltsql init                    # 初期化のみ
jltsql create-tables           # テーブル作成
jltsql create-indexes          # インデックス作成
jltsql fetch --spec RACE       # データ取得
jltsql monitor                 # リアルタイム監視
jltsql status                  # ステータス確認
```

### quickstart オプション（v2.0.0新機能）
```bash
--db-path PATH       # データベースファイルパス（デフォルト: data/jrvltsql.db）
--from-date DATE     # 開始日（YYYYMMDD形式）
--to-date DATE       # 終了日（YYYYMMDD形式）
--years N            # 過去N年分のデータ取得（デフォルト: 10）
--no-odds            # オッズデータ（O1-O6）を除外
--no-monitor         # セットアップ後のリアルタイム監視をスキップ
--log-file PATH      # ログファイルパス
```

詳細: `jltsql --help`

## データベース構造

### NL_テーブル（蓄積系: 38テーブル）

| カテゴリ | テーブル | 説明 |
|---------|---------|------|
| レース | RA, SE, HR, JG, WF | レース詳細、出馬表、払戻、重賞、WIN5 |
| マスタ | UM, KS, CH, BR, BN, HN, SK | 馬、騎手、調教師、生産者、馬主、繁殖馬、産駒 |
| オッズ | O1-O6, H1, H6 | 単勝〜3連単オッズ、票数 |
| 調教 | WC, HS | ウッドチップ調教、坂路調教 |
| 成績 | JC, CC, TC, RC | 騎手成績、競走馬成績、調教師/騎手変更 |
| その他 | DM, TM, AV, YS, TK | データマイニング、場外発売、スケジュール、特別登録 |

### RT_テーブル（速報系: 20テーブル）

JVRTOpenで取得するリアルタイムデータ。`jltsql monitor`で監視。

| カテゴリ | テーブル | 説明 |
|---------|---------|------|
| 速報系（0B1x, 0B4x） | RA, SE, HR, WE, WH, DM, TM, AV, RC, TC | レース結果、馬体重、騎手/調教師変更 |
| 時系列（0B2x-0B3x） | O1-O6, H1, H6 | オッズ変動、票数推移 |

## 対応データ種別（JVOpen）

JV-Link API仕様に準拠。

| データ種別 | 説明 | Option 1 | Option 2 |
|-----------|------|----------|----------|
| TOKU | 特別登録馬 | o | o |
| RACE | レース情報 | o | o |
| DIFF/DIFN | マスタ情報 | o | - |
| BLOD/BLDN | 血統情報 | o | - |
| MING | データマイニング予想 | o | - |
| SLOP | 坂路調教 | o | - |
| WOOD | ウッドチップ調教 | o | - |
| YSCH | 開催スケジュール | o | - |
| HOSE/HOSN | 市場取引価格 | o | - |
| HOYU | 馬名の意味由来 | o | - |
| COMM | コメント情報 | o | - |
| TCVN | 調教師変更情報 | - | o |
| RCVN | 騎手変更情報 | - | o |
| O1-O6 | オッズ | o | - |

## 開発者向け

### 開発環境のセットアップ

```bash
git clone https://github.com/miyamamoto/jrvltsql.git
cd jrvltsql
pip install -e ".[dev]"
```

### データ品質検証ツール

#### スキーマ/パーサー整合性チェック
```bash
python scripts/validate_schema_parser.py
```
出力例: `✓ Schema/Parser validation: 57/57 parsers match (100.0%)`

#### データ品質チェック
```bash
python scripts/check_data_quality.py
```
全テーブルのPRIMARY KEY制約、データ整合性を検証

### テスト実行

#### パーサーユニットテスト（404テスト）
```bash
pytest tests/test_parsers.py -v
```
全43パーサーを網羅的にテスト

#### 統合テスト（11テスト）
パーサー → インポーター → SQLiteの一連の流れをテスト

```bash
# Windows
run_integration_tests.bat

# または直接実行
pytest tests/test_integration.py -v
```

統合テストの詳細は [tests/INTEGRATION_TESTS.md](tests/INTEGRATION_TESTS.md) を参照

#### 全テスト実行（415テスト）
```bash
pytest
```

#### カバレッジ付き実行
```bash
pytest --cov=src --cov-report=term --cov-report=html
```

## ライセンス

Apache License 2.0

### JRA-VAN利用規約

取得したデータは[JRA-VAN利用規約](https://jra-van.jp/info/rule.html)に従ってください。

- ✅ 個人的な競馬分析・研究
- ❌ データの再配布・第三者提供

## リンク

- [JRA-VAN DataLab](https://jra-van.jp/dlb/)
- [Issues](https://github.com/miyamamoto/jrvltsql/issues)
