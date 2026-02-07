# Data Model: 地方競馬データ対応（UmaConn連携）

**Feature**: 001-local-racing-support
**Date**: 2025-12-15

## Overview

地方競馬対応では、既存のJRA-VANスキーマをそのまま再利用し、テーブル名に`_NAR`接尾辞を付与して区別する。

## New Entities

### 1. DataSource (Enum)

データソースを識別する列挙型。

```
DataSource
├── JRA    # 中央競馬 (JRA-VAN DataLab)
├── NAR    # 地方競馬 (地方競馬DATA / UmaConn)
└── ALL    # 両方（statusコマンド等で使用）
```

**Attributes**:
- `value`: str - "jra", "nar", "all"
- `display_name`: str - "中央競馬", "地方競馬", "全て"
- `com_prog_id`: str - "JVDTLab.JVLink" or "NVDTLabLib.NVLink"

---

### 2. NVLinkWrapper (Class)

UmaConn COM APIのラッパークラス。JVLinkWrapperと同一インターフェース。

```
NVLinkWrapper
├── sid: str                    # セッションID
├── _nvlink: COMObject         # NVDTLabLib.NVLink
├── _is_open: bool             # ストリームオープン状態
│
├── nv_init() -> int
├── nv_open(data_spec, fromtime, option) -> Tuple[int, int, int, str]
├── nv_rt_open(data_spec, key) -> Tuple[int, int]
├── nv_read() -> Tuple[int, Optional[bytes], Optional[str]]
├── nv_gets() -> Tuple[int, Optional[bytes]]
├── nv_close() -> int
├── nv_status() -> int
└── is_open() -> bool
```

**Relationships**:
- Mirrors `JVLinkWrapper` interface
- Used by `Fetcher` classes via `DataSource` selection

---

### 3. NAR Tables (64 tables)

既存のJRA-VANテーブルと同一スキーマ、`_NAR`接尾辞で区別。

#### 蓄積系 (NL_*_NAR): 38 tables

| Table | Description | Primary Key |
|-------|-------------|-------------|
| NL_RA_NAR | レース詳細 | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum |
| NL_SE_NAR | 馬毎レース情報 | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban |
| NL_HR_NAR | 払戻情報 | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum |
| NL_H1_NAR | 払戻詳細 | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum |
| NL_H6_NAR | 三連単払戻 | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, SanrentanKumi |
| NL_UM_NAR | 馬マスタ | KettoNum |
| NL_KS_NAR | 騎手マスタ | KisyuCode |
| NL_CH_NAR | 調教師マスタ | ChokyosiCode |
| NL_BN_NAR | 馬主マスタ | BanusiCode |
| NL_BR_NAR | 生産者マスタ | BreederCode |
| NL_O1_NAR | 単複枠オッズ | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban |
| NL_O2_NAR | 馬連オッズ | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Kumi |
| NL_O3_NAR | ワイドオッズ | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Kumi |
| NL_O4_NAR | 馬単オッズ | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Kumi |
| NL_O5_NAR | 三連複オッズ | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Kumi |
| NL_O6_NAR | 三連単オッズ | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Kumi |
| ... | (他32テーブル) | (JRA-VANと同一) |

#### 速報系 (RT_*_NAR): 20 tables

| Table | Description |
|-------|-------------|
| RT_RA_NAR | レース詳細（速報） |
| RT_SE_NAR | 馬毎レース情報（速報） |
| RT_HR_NAR | 払戻情報（速報） |
| RT_O1_NAR〜RT_O6_NAR | オッズ（速報） |
| ... | (他14テーブル) |

#### 時系列 (TS_*_NAR): 6 tables

| Table | Description |
|-------|-------------|
| TS_O1_NAR〜TS_O6_NAR | オッズ時系列 |

---

### 4. NAR Track Codes

地方競馬場コード（30-51）。JRA競馬場コード（01-10）と重複しない。

```
NAR_JYO_CODES = {
    "30": "門別",
    "33": "帯広",
    "35": "盛岡",
    "36": "水沢",
    "42": "浦和",
    "43": "船橋",
    "44": "大井",
    "45": "川崎",
    "46": "金沢",
    "47": "笠松",
    "48": "名古屋",
    "50": "園田",
    "51": "姫路",
    "54": "高知",
    "55": "佐賀",
}
```

---

## Entity Relationships

```
┌─────────────────┐
│   DataSource    │ ◄── CLI --source option
│   (JRA/NAR)     │
└────────┬────────┘
         │ selects
         ▼
┌─────────────────┐     ┌─────────────────┐
│ JVLinkWrapper   │     │ NVLinkWrapper   │
│ (JRA-VAN)       │     │ (UmaConn)       │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
┌─────────────────────────────────┐
│           Fetcher               │
│  (historical.py / realtime.py) │
└────────────────┬────────────────┘
                 │ uses same
                 ▼
┌─────────────────────────────────┐
│       Parser (38 types)         │
│    (RA, SE, HR, O1-O6, etc.)    │
└────────────────┬────────────────┘
                 │ outputs to
                 ▼
┌─────────────────────────────────┐
│          Database               │
│  NL_RA / NL_RA_NAR (by source)  │
└─────────────────────────────────┘
```

---

## Validation Rules

### DataSource Selection
- `--source`省略時: `DataSource.JRA` (後方互換性)
- `--source jra`: `DataSource.JRA`
- `--source nar`: `DataSource.NAR`
- `--source all`: `DataSource.ALL` (status等の読み取り専用コマンドのみ)

### NVLinkWrapper
- UmaConn DLLインストール必須
- 地方競馬DATAサービスキー設定必須

### Table Naming
- JRA: `{PREFIX}_{RECORD_TYPE}` (例: NL_RA)
- NAR: `{PREFIX}_{RECORD_TYPE}_NAR` (例: NL_RA_NAR)
- スキーマは完全同一（フィールド、型、インデックス）

---

## State Transitions

### Fetch Process State

```
[Idle] ──fetch──> [Initializing] ──init──> [Opening]
                                              │
                                              ▼
                                         [Reading] ◄──────┐
                                              │           │
                                              ├── data ───┤
                                              │           │
                                              ▼           │
                                         [Parsing] ───────┘
                                              │
                                              │ EOF
                                              ▼
                                         [Closing] ──> [Complete]
```

State transitions are identical for JRA and NAR; only the wrapper class differs.
