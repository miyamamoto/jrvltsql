# CLI Interface Contract: 地方競馬データ対応

**Feature**: 001-local-racing-support
**Date**: 2025-12-15

## Overview

既存のCLIコマンドに`--source`オプションを追加し、JRA（中央競馬）とNAR（地方競馬）のデータソースを選択可能にする。

## Global Option

### `--source`

```
Option: --source
Type: Choice [jra, nar, all]
Default: jra
Required: No
Help: データソースを選択（jra=中央競馬, nar=地方競馬, all=両方）
```

**Behavior**:
- `jra`: JRA-VAN DataLab (JVLink) を使用
- `nar`: 地方競馬DATA (UmaConn/NVLink) を使用
- `all`: 両方のデータソース（statusコマンド等の読み取り専用操作のみ）

---

## Command Contracts

### 1. `jltsql fetch`

蓄積データを取得してデータベースにインポート。

```bash
jltsql fetch [OPTIONS]
```

**Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--source` | Choice | jra | データソース選択 |
| `--spec` | String | RACE | データ種別（RACE, DIFF等） |
| `--from` | DateTime | (自動) | 取得開始日時 |
| `--option` | Int | 1 | JVOpen/NVOpenオプション |
| `--db` | Choice | sqlite | データベース種別 |

**Examples**:
```bash
# 中央競馬（従来通り）
jltsql fetch --spec RACE

# 地方競馬
jltsql fetch --source nar --spec RACE

# 地方競馬のマスタデータ
jltsql fetch --source nar --spec DIFF
```

**Exit Codes**:
- 0: 成功
- 1: 一般エラー
- 2: 使用方法エラー

---

### 2. `jltsql status`

データベースと接続状態を表示。

```bash
jltsql status [OPTIONS]
```

**Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--source` | Choice | jra | データソース選択（allで両方表示） |
| `--json` | Flag | False | JSON形式で出力 |

**Examples**:
```bash
# 中央競馬のみ
jltsql status

# 地方競馬のみ
jltsql status --source nar

# 両方
jltsql status --source all
```

**Output (Human)**:
```
=== JRVLTSQL Status ===

[JRA-VAN DataLab]
  状態: 接続可能
  最終更新: 2025-12-15 10:30:00
  テーブル数: 64
  レコード数: 1,234,567

[地方競馬DATA]
  状態: 接続可能
  最終更新: 2025-12-15 10:25:00
  テーブル数: 64
  レコード数: 987,654
```

**Output (JSON)**:
```json
{
  "jra": {
    "status": "available",
    "last_updated": "2025-12-15T10:30:00",
    "tables": 64,
    "records": 1234567
  },
  "nar": {
    "status": "available",
    "last_updated": "2025-12-15T10:25:00",
    "tables": 64,
    "records": 987654
  }
}
```

---

### 3. `jltsql monitor`

リアルタイムデータを監視。

```bash
jltsql monitor [OPTIONS]
```

**Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--source` | Choice | jra | データソース選択 |
| `--date` | Date | (今日) | 監視対象日 |
| `--spec` | String | 0B12 | リアルタイムデータ種別 |

**Examples**:
```bash
# 中央競馬のリアルタイム監視
jltsql monitor

# 地方競馬のリアルタイム監視
jltsql monitor --source nar
```

**Note**: `--source all`は非対応（リアルタイム監視は単一ソースのみ）

---

### 4. `jltsql version`

バージョン情報を表示。

```bash
jltsql version
```

**Output**:
```
JRVLTSQL v2.3.0

対応データソース:
  - JRA-VAN DataLab (JV-Link): 利用可能
  - 地方競馬DATA (UmaConn): 利用可能

Python: 3.11.0 (64-bit)
Platform: Windows 10
```

---

## Error Messages

### UmaConn Not Installed

```
エラー: UmaConn (地方競馬DATA) がインストールされていません。

解決方法:
  1. 地方競馬DATAの会員登録を行ってください
  2. UmaConnソフトウェアをインストールしてください
  3. サービスキーを設定してください

詳細: https://www.keiba-data.com/
```

### Service Key Not Set

```
エラー: 地方競馬DATAのサービスキーが設定されていません。

解決方法:
  1. 地方競馬DATA設定ツールを起動
  2. サービスキーを入力
  3. 設定を保存

サービスキーは地方競馬DATAの契約時に発行されます。
```

---

## Backward Compatibility

| 既存コマンド | 新動作 |
|-------------|--------|
| `jltsql fetch` | `jltsql fetch --source jra`と同等 |
| `jltsql status` | `jltsql status --source jra`と同等 |
| `jltsql monitor` | `jltsql monitor --source jra`と同等 |

すべての既存コマンドは`--source`オプションなしで従来通り動作する。
