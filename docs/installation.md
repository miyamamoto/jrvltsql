# インストールガイド

このガイドでは、JLTSQLのインストール手順を詳しく説明します。

## 目次

1. [システム要件](#システム要件)
2. [事前準備](#事前準備)
3. [インストール手順](#インストール手順)
4. [初期設定](#初期設定)
5. [動作確認](#動作確認)
6. [トラブルシューティング](#トラブルシューティング)
7. [アンインストール](#アンインストール)

---

## システム要件

### 必須要件

- **OS**: Windows 10 (64-bit) 以降 または Windows 11
  - JV-Link COM APIはWindows専用です
  - macOS/Linuxでは動作しません

- **Python**: 3.10以上
  - 推奨: Python 3.10.11 または 3.11.x
  - Python 3.12も動作しますが、一部のライブラリで警告が出る場合があります

- **JRA-VAN DataLab会員登録**
  - 月額2,090円（税込）
  - 公式サイト: https://jra-van.jp/dlb/

### 推奨要件

- **CPU**: Intel Core i5 以上 または同等のAMD CPU
- **メモリ**: 4GB以上（8GB推奨）
- **ストレージ**: 10GB以上の空き容量
  - 全期間のデータを保存する場合は50GB以上推奨
- **ネットワーク**: 常時インターネット接続（データ取得時）

### 必要なソフトウェア

- **Git**: バージョン管理用（オプション）
- **テキストエディタ**: 設定ファイル編集用
  - Visual Studio Code、Notepad++、Sublime Text など

---

## 事前準備

### 1. JRA-VAN DataLab会員登録

1. [JRA-VAN DataLab公式サイト](https://jra-van.jp/dlb/)にアクセス
2. 「新規会員登録」をクリック
3. 必要事項を入力して登録完了
4. 月額料金（2,090円）が発生します

### 2. JV-Link SDKのインストール

1. [JRA-VAN開発者サイト](https://jra-van.jp/dlb/sdv/index.html)にアクセス
2. 「JV-Link」をダウンロード
3. インストーラーを実行
4. 指示に従ってインストール

**確認方法**:
- スタートメニューから「JV-Link設定」を検索
- アプリが起動すればインストール成功

### 3. サービスキーの取得

1. JRA-VAN DataLabにログイン
2. マイページ → サービスキー管理
3. 「新規発行」をクリック
4. サービスキーをメモ（後で使用）

**注意**: サービスキーは他人に見せないでください。

### 4. Pythonのインストール

#### Pythonがインストールされているか確認

```cmd
python --version
```

#### Pythonのインストール（必要な場合）

1. [Python公式サイト](https://www.python.org/downloads/)にアクセス
2. Python 3.10以降をダウンロード
3. インストーラーを実行
4. **重要**: 「Add Python to PATH」にチェックを入れる
5. 「Install Now」をクリック

#### インストール確認

```cmd
python --version
pip --version
```

両方のコマンドでバージョンが表示されればOKです。

---

## インストール手順

### 方法1: Git経由でインストール（推奨）

#### 1. リポジトリをクローン

```cmd
git clone https://github.com/miyamamoto/jltsql.git
cd jltsql
```

#### 2. 仮想環境の作成

```cmd
python -m venv venv
```

#### 3. 仮想環境の有効化

```cmd
venv\Scripts\activate
```

プロンプトに `(venv)` が表示されれば成功です。

#### 4. 依存パッケージのインストール

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

インストールには数分かかる場合があります。

### 方法2: ZIPファイルからインストール

#### 1. ZIPファイルをダウンロード

1. [GitHubリリースページ](https://github.com/miyamamoto/jltsql/releases)にアクセス
2. 最新版のZIPファイルをダウンロード
3. 適当なフォルダに解凍

#### 2. 解凍したフォルダに移動

```cmd
cd C:\path\to\jltsql
```

#### 3. 仮想環境の作成と有効化

```cmd
python -m venv venv
venv\Scripts\activate
```

#### 4. 依存パッケージのインストール

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 初期設定

### 1. プロジェクトの初期化

```cmd
python -m src.cli.main init
```

または

```cmd
jltsql init
```

以下のファイル/フォルダが作成されます:
- `config/config.yaml` - 設定ファイル
- `data/` - データベースファイル保存先
- `logs/` - ログファイル保存先

### 2. 設定ファイルの編集

`config/config.yaml` をテキストエディタで開きます。

#### 最小構成の例:

```yaml
jvlink:
  sid: "JLTSQL"
  service_key: "YOUR_SERVICE_KEY_HERE"  # ←ここに取得したサービスキーを入力

database:
  type: "sqlite"  # sqlite, duckdb, postgresql から選択
  path: "data/keiba.db"

logging:
  level: "INFO"
  file: "logs/jltsql.log"
```

#### 重要な設定項目:

- **jvlink.service_key**: JRA-VANから取得したサービスキー（必須）
- **database.type**: 使用するデータベース（sqlite推奨）
- **database.path**: データベースファイルの保存先

### 3. データベーステーブルの作成

```cmd
jltsql create-tables
```

全57テーブル（NL_* 38テーブル + RT_* 19テーブル）が作成されます。

進捗バーが表示され、すべてのテーブルが作成されれば成功です。

### 4. インデックスの作成（オプション、推奨）

```cmd
jltsql create-indexes
```

データベース検索を高速化するインデックス（120+）が作成されます。

---

## 動作確認

### 1. バージョン確認

```cmd
jltsql version
```

出力例:
```
JLTSQL version 1.0.0-rc1
Python version: 3.10.11
```

### 2. ステータス確認

```cmd
jltsql status
```

出力例:
```
JLTSQL Status
Version: 1.0.0-rc1
Status: Ready
```

### 3. 設定確認

```cmd
jltsql config
```

設定がツリー形式で表示されます。

### 4. テストデータの取得

```cmd
jltsql fetch --from 20241101 --to 20241107 --spec YSCH
```

1週間分のスケジュールデータを取得します。

**期待される出力**:
```
Fetching historical data from JRA-VAN...

  Date range: 20241101 → 20241107
  Data spec:  YSCH
  Database:   sqlite

Processing data...

✓ Fetch complete!

Statistics:
  Fetched:  XXX
  Parsed:   XXX
  Imported: XXX
  Failed:   0
```

### 5. データの確認

SQLiteの場合、以下のツールでデータを確認できます:

- [DB Browser for SQLite](https://sqlitebrowser.org/)
- [DBeaver](https://dbeaver.io/)
- [SQLite Viewer (VS Code拡張機能)](https://marketplace.visualstudio.com/items?itemName=qwtel.sqlite-viewer)

データベースファイル: `data/keiba.db`

---

## トラブルシューティング

### エラー: "JV-Link initialization failed"

**原因**: JV-Link SDKが正しくインストールされていない、またはサービスキーが間違っている

**解決方法**:
1. JV-Link SDKが正しくインストールされているか確認
2. サービスキーが正しいか確認（config/config.yaml）
3. JV-Link設定アプリでサービスキーを登録

### エラー: "ModuleNotFoundError: No module named 'xxx'"

**原因**: 必要なPythonパッケージがインストールされていない

**解決方法**:
```cmd
pip install -r requirements.txt
```

### エラー: "Permission denied" or "Access denied"

**原因**: ファイルやディレクトリの権限が不足している

**解決方法**:
1. 管理者権限でコマンドプロンプトを起動
2. または、別のディレクトリにインストール

### エラー: "Database is locked"

**原因**: 別のプロセスがデータベースを使用中

**解決方法**:
1. 他のjltsqlプロセスを終了
2. DB Browserなどのツールを閉じる
3. `tasklist | findstr python` でPythonプロセスを確認

### Python 3.9でインストールできない

**原因**: Python 3.10以降が必要

**解決方法**:
1. Python 3.10以降をインストール
2. 仮想環境を再作成

### JV-Linkが "Error: -201" を返す

**原因**: サービスキーの期限切れまたは無効

**解決方法**:
1. JRA-VANマイページで契約状況を確認
2. 料金が未払いでないか確認
3. 新しいサービスキーを発行

### データが取得できない

**原因**: ネットワーク接続の問題、またはJRA-VANサーバーの問題

**解決方法**:
1. インターネット接続を確認
2. ファイアウォール設定を確認
3. JRA-VAN公式サイトでメンテナンス情報を確認

---

## アンインストール

### 1. 仮想環境の削除

```cmd
deactivate  # 仮想環境を無効化
cd ..
rmdir /s /q jltsql
```

### 2. JV-Link SDKのアンインストール（必要な場合）

1. コントロールパネル → プログラムと機能
2. 「JV-Link」を選択
3. アンインストール

### 3. データの削除

データベースファイルやログファイルも削除する場合:

```cmd
rmdir /s /q jltsql\data
rmdir /s /q jltsql\logs
```

---

## 次のステップ

インストールが完了したら、以下のドキュメントを参照してください:

- [ユーザーガイド](user_guide.md) - 基本的な使い方
- [APIリファレンス](api_reference.md) - 詳細な機能説明
- [アーキテクチャ](architecture.md) - システム構造の理解

---

## サポート

- **バグ報告**: [GitHub Issues](https://github.com/miyamamoto/jltsql/issues)
- **質問**: [GitHub Discussions](https://github.com/miyamamoto/jltsql/discussions)
- **JRA-VAN関連**: [JRA-VAN開発者コミュニティ](https://developer.jra-van.jp/)

---

**最終更新**: 2025-11-14
**バージョン**: 1.0.0-rc1
