# Scripts Directory

このディレクトリには、JLTSQLプロジェクトのセットアップ、検証、メンテナンスに使用するユーティリティスクリプトが含まれています。

## 目次

- [セットアップスクリプト](#セットアップスクリプト)
- [検証スクリプト](#検証スクリプト)
- [メンテナンススクリプト](#メンテナンススクリプト)
- [開発・テストスクリプト](#開発テストスクリプト)

---

## セットアップスクリプト

### quickstart.py - インタラクティブセットアップウィザード

JLTSQLの完全自動セットアップを実行します。対話形式で設定を選択し、データベースの初期化からデータ取得まで一括で実行できます。

**機能:**
- JV-Linkサービスキーの自動確認
- プロジェクト初期化
- テーブル・インデックス作成
- データ取得（蓄積系・速報系）
- バックグラウンド更新サービスの起動
- Windows起動時の自動起動設定

**セットアップモード:**
- **簡易 (simple)**: レース結果と馬情報のみ (RACE, DIFF)
- **標準 (standard)**: 簡易 + 血統・調教・スケジュール等 (BLOD, YSCH, TOKU, SNAP, SLOP, HOYU, HOSE, COMM, MING, WOOD)
- **フル (full)**: 標準 + 確定オッズ (O1-O6)
- **更新 (update)**: 前回セットアップ以降の差分データのみ取得

**使用例:**

```bash
# 対話形式で実行（推奨）
python scripts/quickstart.py

# または、ダブルクリックで起動
quickstart.bat

# 非対話モード - 簡易セットアップ
python scripts/quickstart.py --mode simple -y

# 標準セットアップ + 速報系データ + バックグラウンド更新
python scripts/quickstart.py --mode standard --include-realtime --background -y

# 過去3年分のみ取得
python scripts/quickstart.py --mode standard --years 3 -y

# カスタム期間指定
python scripts/quickstart.py --mode full --from-date 20200101 --to-date 20231231 -y
```

**オプション:**

| オプション | 説明 |
|-----------|------|
| `--mode {simple,standard,full,update}` | セットアップモード |
| `--include-realtime` | 速報系データも取得（過去約1週間分） |
| `--background` | バックグラウンド更新を開始 |
| `--db-path PATH` | データベースファイルパス（デフォルト: data/keiba.db） |
| `--from-date YYYYMMDD` | 取得開始日（デフォルト: 19860101） |
| `--to-date YYYYMMDD` | 取得終了日（デフォルト: 今日） |
| `--years N` | 取得期間（年数）- from-dateを上書き |
| `--no-odds` | オッズデータ(O1-O6)を除外 |
| `--log-file PATH` | ログファイルパス（指定するとログ出力有効） |
| `-y, --yes` | 確認スキップ（非対話モード） |
| `-i, --interactive` | 対話モード（デフォルト） |

---

### background_updater.py - バックグラウンド更新サービス

蓄積系データの定期更新と速報系データのリアルタイム監視を行います。

**機能:**
1. 蓄積系データ定期更新 (JVOpen option=2) - 差分データを定期取得
2. 速報系データ監視 (JVRTOpen) - 開催日はレース時刻に応じて高頻度更新
3. HTTP API - 外部サービスからの強制更新トリガー

**更新スケジュール:**
- 開催日・レース30分前〜発走: 30秒毎
- 開催日・レース1時間前〜30分前: 1分毎
- 開催日・発売中〜1時間前: 5分毎
- 開催日・レース後: 10分毎（払戻確認まで）
- 非開催日: 速報系更新なし、蓄積系は60分毎

**HTTP API (デフォルト: http://localhost:8765):**
- `GET /trigger` - 全データ強制更新
- `GET /trigger/historical` - 蓄積系のみ強制更新
- `GET /trigger/realtime` - 速報系のみ強制更新
- `GET /status` - 現在の状態取得

**使用例:**

```bash
# デフォルト設定で起動
python scripts/background_updater.py

# 更新間隔を60分に設定
python scripts/background_updater.py --interval 60

# APIポートを変更
python scripts/background_updater.py --api-port 9000

# APIを無効化
python scripts/background_updater.py --no-api
```

---

## 検証スクリプト

### validate_schema_parser.py - スキーマ・パーサー整合性チェック

全57パーサーと58テーブルスキーマの整合性を自動検証します。パーサーの出力フィールドとデータベーステーブルのカラム定義を比較し、不一致を検出します。

**検証項目:**
- パーサーが出力するフィールドがスキーマに存在するか
- スキーマで定義されたカラムがパーサーから出力されるか
- フィールド名の命名規則の一貫性

**使用例:**

```bash
# 基本的な検証（サマリー表示）
python scripts/validate_schema_parser.py

# 詳細表示
python scripts/validate_schema_parser.py --verbose

# すべての問題を表示（警告含む）
python scripts/validate_schema_parser.py --all

# JSON形式で出力
python scripts/validate_schema_parser.py --json
python scripts/validate_schema_parser.py --json > validation_report.json
```

**オプション:**

| オプション | 説明 |
|-----------|------|
| `--json` | JSON形式で出力 |
| `--all` | すべての問題を表示（警告含む） |
| `--verbose` | 詳細な情報を表示 |

---

### check_data_quality.py - データ品質検証

データベース内のデータ品質を総合的にチェックします。

**検証項目:**
1. レコード数チェック - 各テーブルのレコード数
2. NULL値検証 - 重要カラムのNULL値比率
3. 日付フィールド検証 - Year, MonthDayの妥当性
4. コードフィールド検証 - JyoCD, TrackCD等の値範囲チェック
5. 参照整合性チェック - KettoNum等の外部参照
6. レコード一貫性検証 - レースと結果データの対応等

**使用例:**

```bash
# 基本的な品質チェック
python scripts/check_data_quality.py --db data/keiba.db

# 詳細表示
python scripts/check_data_quality.py --db data/keiba.db --verbose

# JSON形式でレポート出力
python scripts/check_data_quality.py --db data/keiba.db --json
python scripts/check_data_quality.py --db data/keiba.db --json > quality_report.json
```

**オプション:**

| オプション | 説明 |
|-----------|------|
| `--db PATH` | データベースファイルパス（必須） |
| `--json` | JSON形式で出力 |
| `--verbose` | 詳細な情報を表示 |

---

## メンテナンススクリプト

### quick_stats.py - データベース統計表示

データベース内の各テーブルのレコード数を一覧表示します。データ取得状況を素早く確認するのに便利です。

**使用例:**

```bash
python scripts/quick_stats.py
```

**出力例:**
```
================================================================================
データベース統計
================================================================================
Table                          Records
------------------------------------------
NL_AV                              234
NL_BR                            3,456
NL_RA                           45,678
...
------------------------------------------
合計                            123,456

データを持つテーブル: 32/58
```

---

### add_unique_constraints.py - UNIQUE制約追加

データベーステーブルにUNIQUE制約を追加します。データの重複を防ぎ、整合性を向上させます。

**使用例:**

```bash
python scripts/add_unique_constraints.py
```

---

### update_h_schemas.py - H系テーブルスキーマ更新

H1〜H6（票数）テーブルのスキーマを更新します。

**使用例:**

```bash
python scripts/update_h_schemas.py
```

---

## 開発・テストスクリプト

### test_postgresql_connection.py - PostgreSQL接続テスト

PostgreSQLデータベースへの接続をテストします。

**使用例:**

```bash
python scripts/test_postgresql_connection.py
```

---

### fill_empty_postgresql_tables.py - PostgreSQLテーブルデータ移行

SQLiteからPostgreSQLへデータを移行します。

**使用例:**

```bash
python scripts/fill_empty_postgresql_tables.py
```

---

### test_ysch_performance.py - YSCHパフォーマンステスト

YSCHパーサーのパフォーマンスをテストします。

**使用例:**

```bash
python scripts/test_ysch_performance.py
```

---

### validate_quality_checker.py - 品質チェッカーの検証

check_data_quality.pyスクリプト自体の動作を検証します。

**使用例:**

```bash
python scripts/validate_quality_checker.py
```

---

### test_quality_check.py - 品質チェックのテスト

データ品質チェック機能のテストを実行します。

**使用例:**

```bash
python scripts/test_quality_check.py
```

---

## 推奨ワークフロー

### 初回セットアップ

1. **quickstart.py** で初期セットアップを実行
   ```bash
   python scripts/quickstart.py
   # または
   quickstart.bat
   ```

2. **quick_stats.py** でデータ取得状況を確認
   ```bash
   python scripts/quick_stats.py
   ```

3. **check_data_quality.py** でデータ品質を検証
   ```bash
   python scripts/check_data_quality.py --db data/keiba.db
   ```

### 定期メンテナンス

1. **background_updater.py** を常時起動してデータを最新に保つ
   - quickstart.pyでWindows起動時の自動起動を設定可能

2. 定期的に **check_data_quality.py** でデータ品質をモニタリング

3. 問題があれば **validate_schema_parser.py** でスキーマとパーサーの整合性を確認

### 開発時

1. **validate_schema_parser.py** でパーサーとスキーマの整合性を確認
   ```bash
   python scripts/validate_schema_parser.py --verbose
   ```

2. 変更後は **test_quality_check.py** でテストを実行

---

## トラブルシューティング

### データが取得できない

1. JV-Linkサービスキーが設定されているか確認
   - JRA-VAN DataLabソフトウェアで設定
   - quickstart.pyが自動チェックします

2. データ種別が契約に含まれているか確認
   - quickstart.pyのログで "契約外" エラーを確認

### データ品質に問題がある

1. **check_data_quality.py** で詳細を確認
   ```bash
   python scripts/check_data_quality.py --db data/keiba.db --verbose
   ```

2. 特定のテーブルに問題がある場合は、そのテーブルのデータを再取得

### パーサーエラーが発生する

1. **validate_schema_parser.py** でスキーマとパーサーの整合性を確認
   ```bash
   python scripts/validate_schema_parser.py --all
   ```

2. 不一致がある場合は、パーサーまたはスキーマを修正

---

## 関連ドキュメント

- [プロジェクトREADME](../README.md) - プロジェクト全体の概要
- [設定ファイル](../config/config.yaml) - JLTSQLの設定
- [スキーマ定義](../src/database/schema.py) - データベーススキーマ
- [パーサー](../src/parser/) - 各データ種別のパーサー実装

---

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
