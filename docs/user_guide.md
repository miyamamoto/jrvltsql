# ユーザーガイド

このガイドでは、JLTSQLの基本的な使い方から高度な機能まで、実践的な使用例を交えて説明します。

## 目次

1. [基本的なワークフロー](#基本的なワークフロー)
2. [データ取得](#データ取得)
3. [リアルタイム監視](#リアルタイム監視)
4. [データエクスポート](#データエクスポート)
5. [データベース管理](#データベース管理)
6. [高度な使い方](#高度な使い方)
7. [ベストプラクティス](#ベストプラクティス)
8. [よくある質問](#よくある質問)

---

## 基本的なワークフロー

### 1. 初回セットアップ

```bash
# プロジェクト初期化
jltsql init

# 設定ファイル編集
notepad config\config.yaml

# テーブル作成
jltsql create-tables

# インデックス作成（推奨）
jltsql create-indexes
```

### 2. データ取得の開始

```bash
# 過去1年分のレースデータ取得
jltsql fetch --from 20230101 --to 20231231 --spec RACE

# マスタデータ取得
jltsql fetch --from 20230101 --to 20231231 --spec DIFF
```

### 3. リアルタイム監視

```bash
# リアルタイムデータ監視開始
jltsql monitor --daemon
```

---

## データ取得

### データ仕様（data_spec）の理解

JV-Dataには複数のデータ仕様があります。主なものは：

#### RACE - レース詳細データ
- レース情報（NL_RA）
- 出走馬情報（NL_SE）
- 払戻情報（NL_HR）
- その他レース関連データ

```bash
jltsql fetch --from 20240101 --to 20241231 --spec RACE
```

#### DIFF - マスタ差分データ
- 競走馬マスタ（NL_UM）
- 騎手マスタ（NL_KS）
- 調教師マスタ（NL_CH）
- その他マスタデータ

```bash
jltsql fetch --from 20240101 --to 20241231 --spec DIFF
```

#### YSCH - スケジュールデータ
- 開催スケジュール（NL_YS）
- 除外馬情報（NL_JG）

```bash
jltsql fetch --from 20240101 --to 20241231 --spec YSCH
```

#### O1～O6 - オッズデータ
- O1: 単勝・複勝オッズ
- O2: 馬連オッズ
- O3: ワイドオッズ
- O4: 枠連オッズ
- O5: 馬単オッズ
- O6: 3連複・3連単オッズ

```bash
# 単勝・複勝オッズ取得
jltsql fetch --from 20241101 --to 20241130 --spec O1

# 3連単オッズ取得
jltsql fetch --from 20241101 --to 20241130 --spec O6
```

### 効率的なデータ取得

#### 月単位でのデータ取得

```bash
# 2024年1月のデータ取得
jltsql fetch --from 20240101 --to 20240131 --spec RACE

# 2024年2月のデータ取得
jltsql fetch --from 20240201 --to 20240229 --spec RACE
```

#### 年単位でのデータ取得

```bash
# 2024年全体のデータ取得
jltsql fetch --from 20240101 --to 20241231 --spec RACE
```

**注意**: 大量のデータを一度に取得すると時間がかかります。月単位での取得を推奨します。

#### 複数のデータ仕様を取得

```bash
# レースデータ取得
jltsql fetch --from 20240101 --to 20241231 --spec RACE

# マスタデータ取得
jltsql fetch --from 20240101 --to 20241231 --spec DIFF

# オッズデータ取得
jltsql fetch --from 20240101 --to 20241231 --spec O1
jltsql fetch --from 20240101 --to 20241231 --spec O2
```

### バッチサイズの調整

デフォルトのバッチサイズは1000ですが、メモリやパフォーマンスに応じて調整できます。

```bash
# バッチサイズを500に設定（メモリ節約）
jltsql fetch --from 20240101 --to 20241231 --spec RACE --batch-size 500

# バッチサイズを2000に設定（高速化）
jltsql fetch --from 20240101 --to 20241231 --spec RACE --batch-size 2000
```

---

## リアルタイム監視

### 基本的な使い方

```bash
# フォアグラウンドで実行（Ctrl+Cで停止）
jltsql monitor

# バックグラウンドで実行
jltsql monitor --daemon
```

### ポーリング間隔の調整

```bash
# 30秒ごとにチェック（デフォルト: 60秒）
jltsql monitor --interval 30

# 120秒ごとにチェック（負荷軽減）
jltsql monitor --interval 120
```

### 特定のデータ仕様を監視

```bash
# オッズデータのみ監視
jltsql monitor --spec O1 --interval 15

# レースデータのみ監視
jltsql monitor --spec RACE --interval 60
```

### 監視の停止

```bash
# 監視プロセスの停止
jltsql stop
```

または、フォアグラウンド実行の場合は `Ctrl+C` で停止できます。

---

## データエクスポート

### CSV形式でエクスポート

```bash
# レースデータをCSVでエクスポート
jltsql export --table NL_RA --output races.csv

# 出走馬データをCSVでエクスポート
jltsql export --table NL_SE --output horses.csv
```

### JSON形式でエクスポート

```bash
# レースデータをJSONでエクスポート
jltsql export --table NL_RA --format json --output races.json
```

### Parquet形式でエクスポート

```bash
# レースデータをParquetでエクスポート
jltsql export --table NL_RA --format parquet --output races.parquet
```

**注意**: Parquet形式を使用するには、`pandas`と`pyarrow`のインストールが必要です。

```bash
pip install pandas pyarrow
```

### WHERE句でフィルタリング

#### 日付範囲でフィルタ

```bash
# 2024年のレースのみエクスポート
jltsql export --table NL_RA \
  --where "開催年月日 >= 20240101 AND 開催年月日 <= 20241231" \
  --output 2024_races.csv
```

#### 特定の競馬場のデータ

```bash
# 東京競馬場のレースのみエクスポート
jltsql export --table NL_RA \
  --where "競馬場コード = '05'" \
  --output tokyo_races.csv
```

#### 特定のグレードのレース

```bash
# G1レースのみエクスポート
jltsql export --table NL_RA \
  --where "グレードコード = 'A'" \
  --output g1_races.csv
```

### 複数のテーブルをエクスポート

```bash
# レース情報
jltsql export --table NL_RA --output data\races.csv

# 出走馬情報
jltsql export --table NL_SE --output data\horses.csv

# 払戻情報
jltsql export --table NL_HR --output data\payouts.csv

# オッズ情報
jltsql export --table NL_O1 --output data\odds_tansho.csv
```

---

## データベース管理

### データベースタイプの切り替え

#### SQLiteを使用

```yaml
# config/config.yaml
database:
  type: "sqlite"
  path: "data/keiba.db"
```

```bash
jltsql create-tables --db sqlite
jltsql fetch --from 20240101 --to 20241231 --spec RACE --db sqlite
```

#### DuckDBを使用

```yaml
# config/config.yaml
database:
  type: "duckdb"
  path: "data/keiba.duckdb"
```

```bash
jltsql create-tables --db duckdb
jltsql fetch --from 20240101 --to 20241231 --spec RACE --db duckdb
```

#### PostgreSQLを使用

```yaml
# config/config.yaml
database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  database: "keiba"
  user: "keiba_user"
  password: "your_password"
```

```bash
jltsql create-tables --db postgresql
jltsql fetch --from 20240101 --to 20241231 --spec RACE --db postgresql
```

### テーブルの選択的作成

```bash
# 蓄積系テーブル（NL_*）のみ作成
jltsql create-tables --nl-only

# 速報系テーブル（RT_*）のみ作成
jltsql create-tables --rt-only
```

### インデックスの管理

```bash
# すべてのインデックスを作成
jltsql create-indexes

# 特定のテーブルのみインデックス作成
jltsql create-indexes --table NL_RA
```

### データベースファイルのバックアップ

```bash
# SQLiteの場合
copy data\keiba.db data\backup\keiba_20241114.db

# DuckDBの場合
copy data\keiba.duckdb data\backup\keiba_20241114.duckdb
```

---

## 高度な使い方

### 設定管理

#### 設定の確認

```bash
# 全設定を表示
jltsql config

# 特定の設定を取得
jltsql config --get database.type
jltsql config --get jvlink.sid
```

#### 複数の設定ファイルを使用

```bash
# 開発環境用
jltsql --config config/dev.yaml fetch --from 20240101 --to 20241231 --spec RACE

# 本番環境用
jltsql --config config/prod.yaml fetch --from 20240101 --to 20241231 --spec RACE
```

### 詳細ログの出力

```bash
# 詳細ログを有効にして実行
jltsql --verbose fetch --from 20240101 --to 20240131 --spec RACE
```

ログファイル: `logs/jltsql.log`

### データの検証

#### SQLiteの場合

```sql
-- DB Browser for SQLiteなどで実行

-- レース数の確認
SELECT COUNT(*) FROM NL_RA;

-- 2024年のレース数
SELECT COUNT(*) FROM NL_RA WHERE 開催年月日 BETWEEN 20240101 AND 20241231;

-- 競馬場別のレース数
SELECT 競馬場コード, COUNT(*) as レース数
FROM NL_RA
GROUP BY 競馬場コード
ORDER BY レース数 DESC;
```

---

## ベストプラクティス

### 1. 段階的なデータ取得

最初から全期間のデータを取得せず、段階的に取得することを推奨します。

```bash
# ステップ1: 直近1ヶ月のデータで動作確認
jltsql fetch --from 20241101 --to 20241130 --spec RACE

# ステップ2: 問題なければ直近1年を取得
jltsql fetch --from 20240101 --to 20241231 --spec RACE

# ステップ3: さらに必要なら過去データを追加
jltsql fetch --from 20230101 --to 20231231 --spec RACE
```

### 2. バックアップの定期実行

```bash
# バックアップスクリプト（backup.bat）
@echo off
set BACKUP_DIR=data\backup
set DATE=%date:~0,4%%date:~5,2%%date:~8,2%

mkdir %BACKUP_DIR% 2>nul
copy data\keiba.db %BACKUP_DIR%\keiba_%DATE%.db

echo Backup completed: keiba_%DATE%.db
```

### 3. リアルタイム監視の運用

```bash
# レース開催日のみ監視（土日）
# タスクスケジューラで土日の8:00に起動、19:00に停止を設定

# 起動スクリプト（start_monitor.bat）
@echo off
cd C:\path\to\jltsql
venv\Scripts\activate
jltsql monitor --daemon --interval 30
```

### 4. ログファイルのローテーション

```yaml
# config/config.yaml
logging:
  level: "INFO"
  file: "logs/jltsql.log"
  rotation:
    max_bytes: 10485760  # 10MB
    backup_count: 5
```

### 5. メモリ管理

大量のデータを処理する場合、バッチサイズを調整してメモリ使用量を管理します。

```bash
# メモリが少ない環境
jltsql fetch --from 20240101 --to 20241231 --spec RACE --batch-size 500

# メモリが十分にある環境
jltsql fetch --from 20240101 --to 20241231 --spec RACE --batch-size 2000
```

---

## よくある質問

### Q1: データ取得に時間がかかりすぎる

**A**: 以下の方法で改善できます：
- バッチサイズを大きくする（--batch-size 2000）
- インデックスを作成する（create-indexes）
- 日付範囲を狭くする（月単位で取得）

### Q2: データベースファイルが大きくなりすぎる

**A**: 以下の対策があります：
- 不要な古いデータを削除
- DuckDBを使用（圧縮率が高い）
- PostgreSQLを使用（エンタープライズ向け）

### Q3: リアルタイム監視が動作しない

**A**: 以下を確認してください：
- インターネット接続
- JRA-VANのサービスが有効か
- サービスキーの有効期限
- ファイアウォール設定

### Q4: エクスポートしたCSVが文字化けする

**A**: UTF-8対応のエディタで開いてください：
- Excel: データタブ → CSVからのインポート
- VS Code、Notepad++: デフォルトでUTF-8対応

### Q5: 複数のPCで同じデータベースを使いたい

**A**: PostgreSQLを使用してください：
```yaml
database:
  type: "postgresql"
  host: "192.168.1.100"
  database: "keiba"
```

### Q6: 過去の全データを取得したい

**A**: 段階的に取得することを推奨します：

```bash
# 年単位で取得（例: 2020-2024）
jltsql fetch --from 20200101 --to 20201231 --spec RACE
jltsql fetch --from 20210101 --to 20211231 --spec RACE
jltsql fetch --from 20220101 --to 20221231 --spec RACE
jltsql fetch --from 20230101 --to 20231231 --spec RACE
jltsql fetch --from 20240101 --to 20241231 --spec RACE
```

---

## 次のステップ

- [APIリファレンス](api_reference.md) - 詳細な技術仕様
- [アーキテクチャ](architecture.md) - システム構造の理解
- [コントリビューションガイド](../CONTRIBUTING.md) - プロジェクトへの貢献

---

## サポート

- **質問・相談**: [GitHub Discussions](https://github.com/miyamamoto/jltsql/discussions)
- **バグ報告**: [GitHub Issues](https://github.com/miyamamoto/jltsql/issues)
- **JRA-VAN関連**: [JRA-VAN開発者コミュニティ](https://developer.jra-van.jp/)

---

**最終更新**: 2025-11-14
**バージョン**: 1.0.0-rc1
