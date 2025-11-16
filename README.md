# JLTSQL - JRA-VAN Link To SQL

JRA-VAN DataLabの競馬データをDuckDB/SQLite/PostgreSQLにインポートするPythonツール

[![Tests](https://github.com/miyamamoto/jltsql/actions/workflows/test.yml/badge.svg)](https://github.com/miyamamoto/jltsql/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## 特徴

- **全38レコードタイプ対応**: 1986年以降の全競馬データ
- **DuckDB標準**: 高速OLAP処理（SQLite、PostgreSQLも対応）
- **レジストリー不要**: 設定ファイル/環境変数でサービスキーを管理
- **バッチ処理最適化**: 1000件/batch + 50+インデックス

## 必要要件

- Windows 10/11（JV-Link COM API）
- Python 3.10+
- JRA-VAN DataLab会員（月額2,090円）

## インストール

```bash
git clone https://github.com/miyamamoto/jltsql.git
cd jltsql
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 設定

`config/config.yaml`を作成してサービスキーを設定：

```yaml
jvlink:
  service_key: "XXXX-XXXX-XXXX-XXXX-X"
```

または環境変数で設定：

```bash
set JVLINK_SERVICE_KEY=XXXX-XXXX-XXXX-XXXX-X
```

**重要**: レジストリーを使用せず、設定ファイル/環境変数から読み込みます。

## 使い方

### クイックスタート

```bash
# 1. 初期化
jltsql init

# 2. テーブル作成（38テーブル）
jltsql create-tables

# 3. インデックス作成（50+インデックス）
jltsql create-indexes

# 4. データ取得
jltsql fetch --from 20240101 --to 20241231 --spec RACE
```

### 自動セットアップ

```bash
# 直近10年間の全データを一括セットアップ + リアルタイム監視開始（デフォルト）
python scripts/quickstart.py

# オプション
python scripts/quickstart.py --years 5                       # 過去5年間のデータ取得
python scripts/quickstart.py --years 20                      # 過去20年間のデータ取得
python scripts/quickstart.py --from 20200101 --to 20241231  # 期間を直接指定
python scripts/quickstart.py --no-odds                       # オッズデータを除外
python scripts/quickstart.py --no-monitor                    # 監視を開始しない
python scripts/quickstart.py -y                              # 確認なしで実行
```

自動セットアップで実行される処理：
1. プロジェクト初期化（DB作成）
2. テーブル作成（38テーブル）
3. インデックス作成（50+インデックス）
4. 全データ取得（8基本データ + 4オッズデータ）
   - DIFN（マスタ情報）、BLDN（血統）、RACE（レース）、YSCH（スケジュール）
   - TOKU（特別登録）、HOSN（市場取引）、COMM（解説）、SNPN（速報）
   - SLOP（単複オッズ）、HOYU（馬連ワイド）、WOOD（調教）、MING（当日発表）
5. リアルタイム監視開始（デーモンプロセス）

## 主要コマンド

```bash
jltsql init                    # 初期化
jltsql create-tables           # テーブル作成
jltsql create-indexes          # インデックス作成
jltsql fetch --spec RACE       # データ取得
jltsql status                  # ステータス確認
jltsql config                  # 設定確認
```

詳細: `jltsql --help`

## データベーススキーマ

全38テーブル（NL_*）:

| カテゴリ | テーブル | 説明 |
|---------|---------|------|
| レース | RA, SE, HR, JG | レース詳細、出馬表、払戻、重賞 |
| マスタ | UM, KS, CH, BR, BN | 馬、騎手、調教師、生産者、馬主 |
| オッズ | O1-O6 | 単勝、馬連、ワイド、枠連、馬単、3連複/単 |
| その他 | H1, H6, WF, YS等 | 払戻、天候、スケジュール等 |

対応レコードタイプ: AV, BN, BR, BT, CC, CH, CK, CS, DM, H1, H6, HC, HN, HR, HS, HY, JC, JG, KS, O1-O6, RA, RC, SE, SK, TC, TK, TM, UM, WC, WE, WF, WH, YS

## ライセンス

Apache License 2.0

**JRA-VAN Data Lab利用規約**:
- データの再配布禁止
- 個人利用・自社内利用のみ
- 詳細: https://jra-van.jp/dlb/about/rule.html

## リンク

- [JRA-VAN DataLab](https://jra-van.jp/dlb/)
- [開発者コミュニティ](https://developer.jra-van.jp/)
- [Issues](https://github.com/miyamamoto/jltsql/issues)
