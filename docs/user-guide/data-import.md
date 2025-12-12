# データインポート

JV-Linkからデータを取得してデータベースにインポートする方法を説明します。

## データ仕様の理解

### 蓄積系データ (NL_)

| 仕様 | 説明 | 主なテーブル |
|------|------|-------------|
| RACE | レース情報・成績 | NL_RA, NL_SE, NL_HR |
| DIFF | マスターデータ | NL_UM, NL_KS, NL_CH |
| YSCH | 開催スケジュール | NL_YS |
| SNAP | 出馬表 | NL_TK |
| BLOD | 血統情報 | NL_BT |

### 速報系データ (RT_)

| 仕様 | 説明 | 主なテーブル |
|------|------|-------------|
| 0B12 | 結果・払戻速報 | RT_HR, RT_H1 |
| 0B15 | レース情報速報 | RT_RA, RT_SE |
| 0B30-36 | オッズ速報 | RT_O1〜RT_O6 |

## インポートの種類

### 初回インポート（セットアップ）

初めてデータを取得する場合は、セットアップモードを使用します：

```bash
# 全データ取得（確認ダイアログあり）
jltsql fetch --from 20200101 --to 20241231 --spec RACE --option 3

# マスターデータも取得
jltsql fetch --from 20200101 --to 20241231 --spec DIFF --option 3
```

!!! warning "注意"
    セットアップモード（option 3/4）は大量のデータをダウンロードします。
    初回は数時間かかる場合があります。

### 差分更新

日常的な更新には差分モードを使用します：

```bash
# 差分更新（前回からの変更分のみ）
jltsql fetch --from 20240101 --to 20241231 --spec RACE --option 1
```

### 今週データ

今週のデータのみ取得する場合：

```bash
jltsql fetch --from 20240101 --to 20241231 --spec RACE --option 2
```

## バッチサイズの調整

メモリ使用量と速度のバランスを調整できます：

```bash
# 大きなバッチ（高速だがメモリ多め）
jltsql fetch --from 20240101 --to 20241231 --spec RACE --batch-size 5000

# 小さなバッチ（低メモリ）
jltsql fetch --from 20240101 --to 20241231 --spec RACE --batch-size 500
```

## 重複データの処理

JRVLTSQLはINSERT OR REPLACE（UPSERT）を使用します：

- **PRIMARY KEY**に基づいて重複を検出
- 同じキーのデータは上書き更新
- 再実行しても重複レコードは作成されない

```sql
-- 例：NL_RAテーブルのPRIMARY KEY
PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)
```

## インポートの監視

### 進捗表示

```bash
# 進捗バー表示（デフォルト）
jltsql fetch --from 20240101 --to 20241231 --spec RACE --progress

# 進捗非表示
jltsql fetch --from 20240101 --to 20241231 --spec RACE --no-progress
```

### ログ確認

```bash
# 詳細ログを有効化
jltsql fetch --from 20240101 --to 20241231 --spec RACE -v

# ログファイル確認
tail -f logs/jltsql.log
```

## エラー対処

### 接続エラー

```
JVLinkError: Failed to connect to JV-Link
```

**対処法**:
1. JRA-VAN DataLabがインストールされているか確認
2. サービスキーが設定されているか確認
3. DataLabソフトウェアを一度起動して確認

### タイムアウト

```
DatabaseError: Connection timeout
```

**対処法**:
```yaml
# config/config.yaml
databases:
  sqlite:
    timeout: 60.0  # タイムアウトを延長
```

### メモリ不足

```
MemoryError: Unable to allocate...
```

**対処法**:
```bash
# バッチサイズを小さくする
jltsql fetch --from 20240101 --to 20241231 --spec RACE --batch-size 200
```

## 推奨インポート手順

### 1. 初回セットアップ

```bash
# テーブル作成
jltsql create-tables

# レースデータ（過去5年）
jltsql fetch --from 20200101 --to 20241231 --spec RACE --option 3

# マスターデータ
jltsql fetch --from 20200101 --to 20241231 --spec DIFF --option 3

# 血統データ
jltsql fetch --from 20200101 --to 20241231 --spec BLOD --option 3
```

### 2. 日次更新（cronなど）

```bash
#!/bin/bash
# daily_update.sh

TODAY=$(date +%Y%m%d)
YEAR_START=$(date +%Y0101)

jltsql fetch --from $YEAR_START --to $TODAY --spec RACE --option 1
jltsql fetch --from $YEAR_START --to $TODAY --spec DIFF --option 1
```

### 3. データ確認

```bash
# ステータス確認
jltsql status

# SQLで件数確認
sqlite3 data/keiba.db "SELECT COUNT(*) FROM NL_RA WHERE Year = 2024"
```
