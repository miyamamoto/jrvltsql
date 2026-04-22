# jrvltsql v1.3.0 リリースノート

## 主要な変更

### 🗄️ Dual-write mode
- SQLite を primary にしつつ PostgreSQL へ同時書き込み
- DDL / migration も mirror 側へ反映
- PostgreSQL 併用時の移行パスを標準化

### 🔄 PostgreSQL migration 整備
- schema migration の PostgreSQL 対応を追加
- migration テストを拡充
- batch / realtime の書き込み経路を調整

### 🧪 品質改善
- DDL mirror の反映漏れを修正
- realtime / verify 周辺の false positive を解消
- dual-write / migration まわりのテストを追加

## 対象ユーザー

- Windows 上で JV-Link から JRA データを取り込みたい運用者
- SQLite から PostgreSQL mirror / 移行へ進めたい運用者
- race day の realtime 監視を安定化したい利用者

## システム要件
- Windows 10/11
- Python 3.12（32-bit）
- JV-Link（中央競馬）

## インストール / アップデート
```powershell
irm https://raw.githubusercontent.com/miyamamoto/jrvltsql/master/install.ps1 | iex
```

## 主な差分

- `src/database/dual_handler.py`
- `src/database/migration.py`
- `src/services/realtime_monitor.py`
- `src/cli/main.py`

## 補足

- 本リリースは **JRA 専用** です
- NAR 取り込みは `jrvltsql-nar` 側で分離管理します
