# JLTSQL - JRA-VAN Link To SQL

JRA-VAN DataLabの競馬データをDuckDB/SQLite/PostgreSQLにインポートするPythonツール

[![Tests](https://github.com/miyamamoto/jltsql/actions/workflows/test.yml/badge.svg)](https://github.com/miyamamoto/jltsql/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## 概要

JRA-VAN DataLab (JV-Link) の競馬データを、DuckDB（標準）/SQLite/PostgreSQLにインポートするツールです。

### 主な機能

- **全38レコードタイプ対応**: 1986年以降の全競馬データ（57テーブル）
- **リアルタイム更新**: オッズ、馬体重、レース結果の即時取得
- **DuckDB標準**: 高速OLAP処理に最適化（SQLite、PostgreSQLも対応）
- **高速処理**: バッチ処理（1000件/batch）+ 最適化インデックス（120+）

## 動作環境

- **OS**: Windows 10/11 (JV-Link COM API)
- **Python**: 3.10+
- **必須**: JRA-VAN DataLab会員（月額2,090円）

## インストール

```bash
# リポジトリクローン
git clone https://github.com/yourusername/jltsql.git
cd jltsql

# 仮想環境作成
python -m venv venv
venv\Scripts\activate

# 依存パッケージインストール
pip install -r requirements.txt

# 設定ファイル作成
copy config\config.yaml.example config\config.yaml
```

`config\config.yaml` にJRA-VANサービスキーを設定してください。

## クイックスタート

### 完全自動セットアップ（最も簡単）

```bash
# 2024年以降の全データ（全オッズO1-O6含む）+ リアルタイム監視まで一括セットアップ
python scripts/setup_full_data.py --from-year 2024 --start-monitor

# オッズデータを除外する場合
python scripts/setup_full_data.py --from-year 2024 --without-odds --start-monitor
```

### 基本セットアップのみ

```bash
# 初期セットアップ (init + create-tables + create-indexes)
python scripts/quickstart.py

# サンプルデータ取得
python scripts/quickstart.py --fetch --from 20240101 --to 20240131 --spec RACE
```

### 手動セットアップ

```bash
# 1. プロジェクト初期化
jltsql init

# 2. テーブル作成（全57テーブル）
jltsql create-tables

# 3. インデックス作成（120+インデックス）
jltsql create-indexes

# 4. 過去データ取得
jltsql fetch --from 20240101 --to 20241231 --spec RACE

# 5. リアルタイム監視開始
jltsql monitor --daemon

# 6. ステータス確認
jltsql status
```

## データベーススキーマ

### 蓄積系テーブル (NL_*): 38テーブル

- **NL_RA**: レース詳細
- **NL_SE**: 馬毎レース情報
- **NL_HR**: 払戻情報
- **NL_UM**: 競走馬マスタ
- **NL_KS**: 騎手マスタ
- **NL_CH**: 調教師マスタ
- **NL_O1～O6**: オッズ（単勝、馬連、ワイド、枠連、馬単、3連複/単）
- その他27テーブル

### 速報系テーブル (RT_*): 19テーブル

リアルタイム更新用（RT_RA, RT_SE, RT_HR, RT_O1～O6など）

### 対応レコードタイプ（全38種）

```
AV, BN, BR, BT, CC, CH, CK, CS, DM,
H1, H6, HC, HN, HR, HS, HY,
JC, JG, KS,
O1, O2, O3, O4, O5, O6,
RA, RC, SE, SK,
TC, TK, TM,
UM,
WC, WE, WF, WH,
YS
```

## 主要コマンド

```bash
# データ取得
jltsql fetch --from YYYYMMDD --to YYYYMMDD --spec SPEC

# リアルタイム監視
jltsql monitor [--daemon]

# データエクスポート
jltsql export --table TABLE --output FILE [--format csv|json|parquet]

# 設定確認
jltsql config

# ステータス
jltsql status
```

詳細は `jltsql --help` または各コマンドの `--help` を参照してください。

## 開発

```bash
# 開発環境セットアップ
pip install -r requirements-dev.txt

# テスト実行
pytest

# コードフォーマット
black src tests
ruff check src tests
```

## ライセンス

Apache License 2.0

### JRA-VAN Data Lab利用規約

- データの再配布禁止
- 個人利用・自社内利用のみ
- 商用利用は別途契約必要
- 詳細: https://jra-van.jp/dlb/about/rule.html

## 参考リンク

- [JRA-VAN DataLab公式](https://jra-van.jp/dlb/)
- [JRA-VAN開発者コミュニティ](https://developer.jra-van.jp/)

## サポート

- バグ報告: [GitHub Issues](https://github.com/yourusername/jltsql/issues)
- 質問: [GitHub Discussions](https://github.com/yourusername/jltsql/discussions)
