# jltsql v1.0.0 🏇

JRA-VAN DataLab / 地方競馬DATA の競馬データを SQLite・PostgreSQL にインポートするツールの初回安定リリースです。

## ✨ 主要機能

### データ取得
- **JV-Link (中央競馬)** — 全データ種別の取得・パース・インポート
- **NV-Link (地方競馬)** — NAR対応、-502エラー自動リトライ、COM自動再起動

### パーサー
- **41パーサー** (38 JRA + 3 NAR専用)
  - JRA: レース情報、馬情報、騎手情報、調教師情報、オッズ全種、払戻、成績など
  - NAR専用: NC (競馬場マスタ)、NU (出馬表)、HA (払戻データ)
- NAR日付分割ダウンロード（1日ずつチャンクで-502エラー回避）

### データベース
- **SQLite** — デフォルト、軽量セットアップ
- **PostgreSQL** — 大規模データ対応 (`pg8000`)

### ツール
- ワンコマンドインストーラー
- 自動アップデート機能
- Quickstart ウィザード
- CLI によるデータ管理

### 品質
- **384+ テスト** (27パーサーの実データフィクスチャ含む)

## 📦 インストール

```powershell
irm https://raw.githubusercontent.com/miyamamoto/jrvltsql/master/install.ps1 | iex
```

## 💻 システム要件

| 項目 | 要件 |
|------|------|
| OS | Windows 10/11 |
| Python | 3.12 (32-bit 必須) |
| JV-Link | JRA-VAN DataLab 会員 |
| NV-Link | 地方競馬DATA 会員 (NAR利用時) |

## 🚀 クイックスタート

```bash
jltsql quickstart   # セットアップウィザード
jltsql fetch        # データ取得
jltsql status       # 状態確認
```

## 📝 全変更履歴

[CHANGELOG.md](./CHANGELOG.md) を参照してください。
