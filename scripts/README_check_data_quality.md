# データ品質検証ツール

## 概要

`check_data_quality.py` は、JRA-VANデータベースのデータ品質を検証するツールです。

## 主な機能

### 1. テーブル統計情報の出力
- レコード数
- 日付範囲（Year, MonthDay）
- NULL値の割合（重要カラム）
- コードフィールドの有効性チェック

### 2. データ検証項目

#### 日付フィールド検証
- `Year`: 1900-2100の範囲内か
- `MonthDay`: MMDD形式（4桁）、月1-12、日1-31の範囲内か

#### コードフィールド検証
以下のコードが有効な範囲内かチェック：
- `JyoCD`: 競馬場コード（01-99）
- `Kaiji`: 開催回次（1-10）
- `Nichiji`: 日次（1-12）
- `RaceNum`: レース番号（1-12）
- `Umaban`: 馬番（1-28）
- `TrackCD`: トラックコード（10-59）

#### NULL値チェック
重要カラムのNULL値割合をチェック：
- `NL_RA`: Year, MonthDay, JyoCD, RaceNum, RaceName
- `NL_SE`: Year, MonthDay, JyoCD, RaceNum, Umaban, KettoNum
- `NL_UM`: KettoNum, Bamei
- `NL_KS`: KisyuCode, KisyuName
- `NL_CH`: ChokyosiCode, ChokyosiName

#### 重複チェック
PRIMARY KEY制約に基づく重複レコードの検出

#### 参照整合性チェック
- `NL_SE` → `NL_RA`: 成績レコードが対応するレースを参照しているか
- `NL_SE` → `NL_UM`: 成績レコードが有効な馬（KettoNum）を参照しているか
- レース対成績の比率チェック（1レースあたりの出走頭数）

### 3. レポート出力

#### コンソール出力例
```
================================================================================
Data Quality Report
================================================================================
Database: data/keiba.db
Generated: 2025-11-30 20:00:00

Tables: 58

[NL_RA] レース詳細
  Records: 150,000
  Date Range: 2020-01-01 ~ 2024-11-30
  Quality: GOOD

[NL_SE] 成績
  Records: 2,500,000
  Quality: GOOD

...

================================================================================
Cross-Table Integrity Checks
================================================================================

  NL_SE → NL_RA: 99.8% linked (2,495,000/2,500,000)
  NL_SE → NL_UM: 95.2% linked (2,380,000/2,500,000)
  Race to Results Ratio: 16.7 results per race

================================================================================
Summary
================================================================================
Total Issues Found: 3

Issues by Severity:
  CRITICAL: 0
  WARNING:  2
  INFO:     1

Top Issues:
  1. [WARNING] NL_TK: 15 records (0.3%) with invalid JyoCD (競馬場コード (01-99))
  2. [WARNING] NL_SE: 120,000 records (4.8%) reference non-existent horses (KettoNum)
  3. [INFO] NL_RA/NL_SE: Unusually low results per race: 4.2 (expected ~8-18)
```

#### JSON出力例
```json
{
  "database": "data/keiba.db",
  "generated_at": "2025-11-30T20:00:00",
  "total_tables": 58,
  "total_issues": 3,
  "table_stats": {
    "NL_RA": {
      "record_count": 150000,
      "quality": "GOOD",
      "checks": {
        "date_fields": "CHECKED",
        "code_JyoCD": "CHECKED",
        "null_values": "CHECKED",
        "duplicates": "CHECKED"
      }
    },
    "NL_SE": {
      "record_count": 2500000,
      "quality": "WARNING",
      "checks": {
        "date_fields": "CHECKED",
        "code_JyoCD": "CHECKED",
        "null_values": "CHECKED",
        "duplicates": "CHECKED"
      }
    }
  },
  "issues": [
    {
      "table": "NL_TK",
      "message": "15 records (0.3%) with invalid JyoCD (競馬場コード (01-99))",
      "severity": "WARNING",
      "timestamp": "2025-11-30T20:00:00"
    }
  ]
}
```

## 使用方法

### 基本的な使い方

```bash
# Windows（バッチファイル経由）
check_quality.bat --db-path data/keiba.db

# 直接実行
python scripts/check_data_quality.py --db-path data/keiba.db
```

### オプション

```bash
# 詳細出力モード
python scripts/check_data_quality.py --db-path data/keiba.db --verbose

# JSON レポート出力
python scripts/check_data_quality.py --db-path data/keiba.db --output report.json

# すべてのオプションを使用
python scripts/check_data_quality.py --db-path data/keiba.db --output report.json --verbose
```

### コマンドライン引数

- `--db-path`: チェックするSQLiteデータベースファイルのパス（デフォルト: `data/keiba.db`）
- `--output`: 詳細JSONレポートの出力先ファイルパス（オプション）
- `--verbose`: 詳細な出力を有効化（NULL値の割合など）

## 品質評価基準

### CRITICAL（重大）
- PRIMARY KEY の重複が検出された場合

### WARNING（警告）
- 10%以上のレコードに重要フィールドのNULL値がある
- 1%以上のコードフィールドが無効な範囲
- 1%以上のレコードで参照整合性が破綻
- 5%以上の馬（KettoNum）参照が存在しない

### INFO（情報）
- レース対成績比率が異常（5頭未満など）

### GOOD（良好）
- 上記の問題が検出されなかった場合

## テスト実行

```bash
# テストスクリプトで動作確認
python scripts/test_quality_check.py
```

## 実装詳細

### 対応テーブル
すべてのテーブルを自動検出してチェックします。

### 検証対象の主要テーブル
- `NL_RA` / `RT_RA`: レース詳細
- `NL_SE` / `RT_SE`: 馬毎レース情報（成績）
- `NL_UM`: 馬マスター
- `NL_KS`: 騎手マスター
- `NL_CH`: 調教師マスター
- `NL_BN`: 馬主マスター
- `NL_BR`: 繁殖馬マスター
- `NL_O1` - `NL_O6`: オッズ各種
- `NL_H1`, `NL_H6`: 単複オッズ
- `NL_HR`: 払戻

### アルゴリズム

1. **テーブル一覧取得**: `sqlite_master` から全テーブルを取得
2. **個別テーブルチェック**: 各テーブルに対して
   - レコード数カウント
   - 日付フィールド検証（Year, MonthDay）
   - コードフィールド検証（JyoCD, Kaiji等）
   - NULL値チェック（重要カラム）
   - 重複チェック（PRIMARY KEY）
3. **クロステーブルチェック**:
   - NL_SE → NL_RA の参照整合性
   - NL_SE → NL_UM の参照整合性
   - レース対成績比率
4. **レポート生成**: 問題点をリスト化して出力

## 制限事項

- SQLiteデータベースのみ対応（PostgreSQLは未対応）
- 一部のコード値の有効性チェックは代表的な値のみ
- 大規模データベース（1億レコード以上）では実行時間が長くなる可能性

## トラブルシューティング

### データベースファイルが見つからない
```
Error: Database file not found: data/keiba.db
```
→ `--db-path` で正しいパスを指定してください

### 実行権限エラー
```
Permission denied: data/keiba.db
```
→ データベースファイルの読み取り権限を確認してください

### メモリ不足
大規模DBでメモリ不足になる場合は、一部のチェックを無効化するか、より小さいDBで試してください。

## 今後の拡張予定

- [ ] PostgreSQL対応
- [ ] カスタム検証ルールの追加
- [ ] HTML レポート出力
- [ ] 経時的な品質モニタリング
- [ ] 自動修復機能
- [ ] パフォーマンス最適化（並列処理）

## ライセンス

このツールはJLTSQLプロジェクトの一部です。
