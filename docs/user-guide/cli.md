# CLIリファレンス

JRVLTSQLのコマンドラインインターフェースの完全なリファレンスです。

## 基本コマンド

### init

プロジェクトの初期化を行います。

```bash
jltsql init
```

作成されるもの：
- `config/config.yaml` - 設定ファイル
- `data/` - データディレクトリ
- `logs/` - ログディレクトリ

### create-tables

データベースにテーブルを作成します。

```bash
jltsql create-tables [--db TYPE]
```

| オプション | 説明 |
|-----------|------|
| `--db` | データベースタイプ (sqlite/postgresql) |

### fetch

JV-Linkからデータを取得してインポートします。

```bash
jltsql fetch --from YYYYMMDD --to YYYYMMDD --spec SPEC [OPTIONS]
```

**必須オプション**:

| オプション | 説明 |
|-----------|------|
| `--from` | 開始日 (YYYYMMDD) |
| `--to` | 終了日 (YYYYMMDD) |
| `--spec` | データ仕様 (下記参照) |

**任意オプション**:

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--source` | データソース (jra/nar/all) | jra |
| `--option` | JVOpen/NVOpenオプション (1-4) | 1 |
| `--db` | データベースタイプ | 設定ファイル |
| `--batch-size` | バッチサイズ | 1000 |
| `--progress/--no-progress` | 進捗表示 | --progress |

**データ仕様 (--spec)**:

| 仕様 | 説明 | テーブル |
|------|------|---------|
| `RACE` | レースデータ | NL_RA, NL_SE, NL_HR, NL_WF, NL_JG |
| `DIFF` | マスターデータ | NL_UM, NL_KS, NL_CH, NL_BR, NL_BN, NL_HN, NL_SK, NL_RC, NL_HC |
| `YSCH` | 開催スケジュール | NL_YS |
| `SNAP` | 出馬表 | NL_TK |
| `BLOD` | 血統情報 | NL_BT |

**JVOpen/NVOpenオプション (--option)**:

| 値 | JV-Link (JRA) | NV-Link (NAR) |
|----|---------------|---------------|
| 1 | 通常データ（差分更新） | 動作不安定（-203エラーの可能性） |
| 2 | 今週データ | 未サポート |
| 3 | セットアップ（全データ、確認ダイアログあり） | **推奨**（安定動作） |
| 4 | 分割セットアップ | 動作確認中 |

**使用例**:

```bash
# 2024年のレースデータを取得
jltsql fetch --from 20240101 --to 20241231 --spec RACE

# マスターデータを差分更新
jltsql fetch --from 20240101 --to 20241231 --spec DIFF --option 1

# PostgreSQLに取り込み
jltsql fetch --from 20240101 --to 20241231 --spec RACE --db postgresql

# 地方競馬データを取得（option=3推奨）
jltsql fetch --from 20240101 --to 20241231 --spec RACE --source nar --option 3
```

### export

データをファイルにエクスポートします。

```bash
jltsql export --table TABLE --output FILE [--format FORMAT] [--where CONDITION]
```

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--table` | テーブル名 | 必須 |
| `--output` | 出力ファイル | 必須 |
| `--format` | 出力形式 (csv/json/parquet) | csv |
| `--where` | WHERE句 | なし |

```bash
# CSVエクスポート
jltsql export --table NL_RA --output races.csv

# 条件付きJSONエクスポート
jltsql export --table NL_SE --output results.json --format json --where "Year=2024"

# Parquet形式（分析用）
jltsql export --table NL_O1 --output odds.parquet --format parquet
```

### status

アプリケーションの状態を表示します。

```bash
jltsql status
```

### version

バージョン情報を表示します。

```bash
jltsql version
```

## リアルタイムコマンド

### realtime start

リアルタイム監視を開始します。

```bash
jltsql realtime start [--specs SPEC1,SPEC2,...] [--db TYPE]
```

**リアルタイム仕様**:

| 仕様 | 説明 |
|------|------|
| `0B12` | レース結果・払戻（速報） |
| `0B15` | レース情報（速報） |
| `0B30` | 単勝オッズ |
| `0B31` | 枠連オッズ |
| `0B32` | 馬連オッズ |
| `0B33` | ワイドオッズ |
| `0B34` | 馬単オッズ |
| `0B35` | 三連複オッズ |
| `0B36` | 三連単オッズ |

### realtime status

監視状態を確認します。

```bash
jltsql realtime status
```

### realtime stop

監視を停止します。

```bash
jltsql realtime stop
```

### realtime specs

利用可能な仕様一覧を表示します。

```bash
jltsql realtime specs
```

### realtime timeseries

時系列オッズデータを取得します。

```bash
jltsql realtime timeseries --spec SPEC --from YYYYMMDD --to YYYYMMDD
```

## グローバルオプション

すべてのコマンドで使用できるオプション：

| オプション | 説明 |
|-----------|------|
| `--config, -c` | 設定ファイルパス |
| `--verbose, -v` | DEBUGログを有効化 |
| `--help` | ヘルプを表示 |

## 使用例

### 初回セットアップ

```bash
# 1. 初期化
jltsql init

# 2. テーブル作成
jltsql create-tables

# 3. 過去5年分のデータ取得
jltsql fetch --from 20200101 --to 20241231 --spec RACE --option 3
jltsql fetch --from 20200101 --to 20241231 --spec DIFF --option 3
```

### 日次更新

```bash
# 差分更新
jltsql fetch --from 20240101 --to 20241231 --spec RACE --option 1
jltsql fetch --from 20240101 --to 20241231 --spec DIFF --option 1
```

### レース当日の運用

```bash
# リアルタイム監視開始
jltsql realtime start --specs 0B12,0B30

# 状態確認
jltsql realtime status

# 終了時
jltsql realtime stop
```

詳細は[CLI.md](https://github.com/miyamamoto/jrvltsql/blob/master/docs/CLI.md)を参照してください。
