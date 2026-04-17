# jrvltsql v1.1.0 リリースノート

## 主要な新機能

### 🔧 H1/H6パーサーのフルストラクト対応
- H1（票数1）: 28,955バイトのフルストラクトを正しくパース
- H6（3連単票数）: 102,900バイトのフルストラクトを正しくパース
- 賭式×組番に展開してDBに格納

### 📦 ワンコマンドインストーラー
```powershell
irm https://raw.githubusercontent.com/miyamamoto/jrvltsql/master/install.ps1 | iex
```

### 🔄 自動アップデート
- `jltsql update` — ワンコマンドでアップデート
- `jltsql version --check` — 最新版チェック
- 起動時の自動チェック（設定可能）

### 📚 ドキュメント整備
- Getting Started, Reference, UserGuide を最新仕様に更新

### 🧹 リポジトリ整理
- 不要ファイル10個削除（7,178行削減）
- .gitignore整備

## システム要件
- Windows 10/11
- Python 3.12（32-bit）
- JV-Link（中央競馬）

## インストール
```powershell
irm https://raw.githubusercontent.com/miyamamoto/jrvltsql/master/install.ps1 | iex
```

## テスト
- 1,247 テストケース（1,239 pass, 8 skip）
