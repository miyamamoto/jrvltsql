# リアルタイムモニタリング

レース当日のリアルタイムデータ取得について説明します。

## 概要

リアルタイム機能では以下のデータを取得できます：

- レース結果・払戻（速報）
- オッズ情報（随時更新）
- 出走取消・騎手変更

## リアルタイム仕様

| 仕様コード | 説明 | 更新頻度 |
|-----------|------|---------|
| `0B12` | レース結果・払戻 | レース確定後 |
| `0B15` | レース情報 | 随時 |
| `0B30` | 単勝オッズ | 数分毎 |
| `0B31` | 枠連オッズ | 数分毎 |
| `0B32` | 馬連オッズ | 数分毎 |
| `0B33` | ワイドオッズ | 数分毎 |
| `0B34` | 馬単オッズ | 数分毎 |
| `0B35` | 三連複オッズ | 数分毎 |
| `0B36` | 三連単オッズ | 数分毎 |

## 基本的な使い方

### 監視の開始

```bash
# 結果とオッズを監視
jltsql realtime start --specs 0B12,0B30

# すべてのオッズを監視
jltsql realtime start --specs 0B30,0B31,0B32,0B33,0B34,0B35,0B36
```

### 状態確認

```bash
jltsql realtime status
```

出力例：
```
Realtime Monitor Status
=======================
Status: Running
Started: 2024-06-01 09:00:00
Uptime: 3h 45m 30s
Records imported: 15,234
Specs monitored: 0B12, 0B30
```

### 監視の停止

```bash
jltsql realtime stop
```

## 時系列オッズ

オッズの時間推移を記録する場合は、時系列モードを使用します：

```bash
# 過去の時系列データを取得
jltsql realtime timeseries --spec 0B30 --from 20240601 --to 20240601
```

時系列データは`TS_O1`〜`TS_O6`テーブルに格納されます。

### 時系列テーブル

| テーブル | 内容 |
|---------|------|
| TS_O1 | 単勝・複勝オッズ推移 |
| TS_O2 | 馬連オッズ推移 |
| TS_O3 | ワイドオッズ推移 |
| TS_O4 | 馬単オッズ推移 |
| TS_O5 | 三連複オッズ推移 |
| TS_O6 | 三連単オッズ推移 |

### 時系列データの活用

```sql
-- オッズの推移を確認
SELECT
    HassoTime,
    TanOdds,
    TanNinki
FROM TS_O1
WHERE Year = 2024
  AND MonthDay = 601
  AND JyoCD = '05'
  AND RaceNum = 11
  AND Umaban = 1
ORDER BY HassoTime;
```

## レース当日の運用フロー

### 朝の準備

```bash
# 1. 最新データを取得
jltsql fetch --from 20240601 --to 20240601 --spec RACE --option 2

# 2. リアルタイム監視開始
jltsql realtime start --specs 0B12,0B15,0B30
```

### レース中

```bash
# 状態確認
jltsql realtime status

# 最新オッズをクエリ
sqlite3 data/keiba.db "
SELECT Umaban, TanOdds, TanNinki
FROM RT_O1
WHERE Year=2024 AND MonthDay=601 AND RaceNum=11
ORDER BY Umaban
"
```

### 終了後

```bash
# 監視停止
jltsql realtime stop

# 確定データを取得
jltsql fetch --from 20240601 --to 20240601 --spec RACE --option 1
```

## Python APIでの利用

```python
from src.database.sqlite_handler import SQLiteDatabase
from src.services.realtime_monitor import RealtimeMonitor

# データベース接続
db = SQLiteDatabase({"path": "data/keiba.db"})

with db:
    # モニター作成
    monitor = RealtimeMonitor(
        database=db,
        data_specs=["0B12", "0B30"],
        sid="JLTSQL"
    )

    # 開始
    monitor.start()

    # 状態確認
    status = monitor.get_status()
    print(f"Running: {status['is_running']}")
    print(f"Records: {status['records_imported']}")

    # 停止
    monitor.stop()
```

## NAR（地方競馬）対応状況

!!! info "NAR リアルタイムデータ"
    現在、リアルタイム監視機能は **JRA（中央競馬）のみ対応** です。
    NAR（地方競馬）のリアルタイムデータ（NV-Link経由）は今後のバージョンで対応予定です。
    NARの蓄積系データ（レース結果・マスタデータ等）は `jltsql fetch --source nar` で取得可能です。

## 注意事項

!!! warning "データ提供時間"
    リアルタイムデータはレース開催日のみ提供されます。
    平日や非開催日は新しいデータが取得できません。

!!! info "データの遅延"
    オッズデータは数分の遅延がある場合があります。
    公式サイトの最新情報と異なる場合があります。

!!! tip "メモリ使用"
    長時間の監視ではメモリ使用量が増加する場合があります。
    定期的に再起動することを推奨します。
