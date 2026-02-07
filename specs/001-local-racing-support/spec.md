# Feature Specification: 地方競馬データ対応（UmaConn連携）

**Feature Branch**: `001-local-racing-support`
**Created**: 2025-12-15
**Status**: Draft
**Input**: User description: "地方競馬にも対応したいです。すでにummaconnはインストール済み。ummacconnの設計に基づき、なるべく既存の実装を活用することを前提にソフトウェアを改変してください。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 地方競馬データの蓄積インポート (Priority: P1)

ユーザーとして、地方競馬DATAの蓄積データ（過去レース結果、馬情報、騎手情報など）を既存のJRA-VANデータと同じデータベースにインポートしたい。これにより中央競馬と地方競馬のデータを統合的に分析できるようになる。

**Why this priority**: 地方競馬対応の基本機能。蓄積データのインポートができなければ、他の機能（リアルタイム、分析等）が利用できない。

**Independent Test**: UmaConnがインストールされた環境で `jltsql fetch --source nar` コマンドを実行し、地方競馬のレースデータがデータベースに格納されることを確認。

**Acceptance Scenarios**:

1. **Given** UmaConnがインストールされている、**When** `jltsql fetch --source nar --spec RACE`を実行、**Then** 地方競馬のレースデータがNL_RA_NAR等のテーブルに格納される
2. **Given** UmaConnがインストールされている、**When** `jltsql fetch --source nar --spec DIFF`を実行、**Then** 地方競馬の馬・騎手マスタがNL_UM_NAR等のテーブルに格納される
3. **Given** UmaConnがインストールされていない、**When** `jltsql fetch --source nar`を実行、**Then** 明確なエラーメッセージが表示される

---

### User Story 2 - 統一されたCLIインターフェース (Priority: P2)

ユーザーとして、中央競馬（JRA）と地方競馬（NAR）のデータを同じCLIコマンド体系で操作したい。新しいコマンドを覚えることなく、既存の知識で地方競馬データを扱えるようになる。

**Why this priority**: ユーザー体験の一貫性。新しいコマンド体系を覚える学習コストを削減し、既存ユーザーがスムーズに地方競馬データを利用開始できる。

**Independent Test**: 既存の `jltsql fetch`, `jltsql status`, `jltsql monitor` コマンドに `--source nar` オプションを追加することで地方競馬データを操作できることを確認。

**Acceptance Scenarios**:

1. **Given** 既存のCLIコマンド、**When** `--source jra` または `--source nar` オプションを追加、**Then** それぞれ中央競馬または地方競馬のデータソースを操作できる
2. **Given** `--source` オプションなし、**When** コマンドを実行、**Then** デフォルトでJRA（中央競馬）として動作する（後方互換性）
3. **Given** `jltsql status` コマンド、**When** `--source all` オプション、**Then** JRAとNAR両方のステータスを表示

---

### User Story 3 - 地方競馬リアルタイムデータ取得 (Priority: P3)

ユーザーとして、地方競馬のレース当日のリアルタイムデータ（オッズ、馬体重、出走取消など）を監視したい。

**Why this priority**: リアルタイム機能は蓄積データの基盤が整った後に実装。地方競馬の投票判断に活用できる。

**Independent Test**: `jltsql monitor --source nar` コマンドでリアルタイムデータが更新されることを確認。

**Acceptance Scenarios**:

1. **Given** 地方競馬の開催日、**When** `jltsql monitor --source nar`を実行、**Then** リアルタイムオッズと馬体重が表示・更新される
2. **Given** 監視中、**When** 騎手変更が発生、**Then** 変更情報がリアルタイムで反映される

---

### Edge Cases

- UmaConnがインストールされていない環境でNARデータを要求した場合
- JRAとNAR両方のデータを同時に取得しようとした場合
- 地方競馬固有のデータ形式（JRAにない項目）の処理
- 地方競馬の競馬場コードとJRAの競馬場コードの重複回避

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: システムはUmaConn COM API（NVDTLabLib.NVLink）経由で地方競馬データを取得できなければならない
- **FR-002**: システムは既存のJV-Link Wrapper設計パターンを踏襲し、NVLinkWrapper クラスを提供しなければならない
- **FR-003**: システムはJRAとNARのデータを区別するためのテーブル命名規則（接尾辞_NAR）を適用しなければならない
- **FR-004**: システムは既存の38種のパーサーを地方競馬データにも再利用できなければならない（データ形式が同一の場合）
- **FR-005**: CLIコマンドは `--source {jra|nar|all}` オプションでデータソースを選択できなければならない
- **FR-006**: `--source` オプション省略時はJRAをデフォルトとし、既存ユーザーへの後方互換性を維持しなければならない
- **FR-007**: UmaConnが利用不可の場合、明確なエラーメッセージを表示しなければならない
- **FR-008**: 地方競馬固有の競馬場コード（30〜51）をサポートしなければならない

### Key Entities

- **NVLinkWrapper**: UmaConn COM APIのPythonラッパー。JVLinkWrapperと同一インターフェースを持ち、メソッド名の「JV」を「NV」に置換
- **DataSource**: データソースの種別を表す列挙型（JRA, NAR）
- **NL_RA_NAR / NL_SE_NAR等**: 地方競馬用テーブル。既存のNL_テーブルと同一スキーマを持ち、接尾辞で区別
- **地方競馬競馬場**: 門別、帯広、盛岡、水沢、浦和、船橋、大井、川崎、金沢、笠松、名古屋、園田、姫路、高知、佐賀等

### Assumptions

- UmaConnのAPI仕様はJV-Link APIの「JV」を「NV」に置き換えることで対応可能
- 地方競馬のレコード形式はJRA-VANのレコード形式と互換性がある（パーサー再利用可能）
- UmaConnは64bit Pythonで動作（JV-Linkと同様のCOM API設計）
- 地方競馬DATAの契約が別途必要

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 地方競馬の蓄積データ取得が中央競馬と同等の速度（5,000 records/sec以上）で動作する
- **SC-002**: 既存の中央競馬向けコマンドが `--source` オプションなしで従来通り動作する（後方互換性100%）
- **SC-003**: 地方競馬データ取得時のエラーメッセージが、原因と対処法を明示している
- **SC-004**: 新規ユーザーが5分以内に地方競馬データのインポートを開始できる
- **SC-005**: 中央競馬と地方競馬のデータを同一データベースで管理し、横断的なクエリが実行可能
