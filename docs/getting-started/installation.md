# インストール

## 必要要件

- **OS**: Windows 10/11
- **Python**: 3.10 以上
- **JRA-VAN**: DataLab 会員登録

## Python の用意

現在の Windows バッチ導線は、まず repo 内の仮想環境を探します。

1. `venv32\Scripts\python.exe`
2. `.venv\Scripts\python.exe`
3. `PYTHON`
4. `py`
5. `python`

既存の 32-bit Python 環境がある場合はそのまま利用できます。  
新規セットアップでは、まず通常の Python 3.10+ を入れ、必要なら repo 内に `.venv` を作る運用を推奨します。

### インストール確認

```bat
python --version
py --version
```

## インストール方法

### pipでインストール

```bash
pip install git+https://github.com/miyamamoto/jrvltsql.git
```

### 開発用インストール

```bash
git clone https://github.com/miyamamoto/jrvltsql.git
cd jrvltsql
pip install -e ".[dev]"
```

## 依存パッケージ

JRVLTSQLは以下のパッケージに依存しています：

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| pywin32 | >=305 | JV-Link COM API連携 |
| pyyaml | >=6.0 | 設定ファイル |
| click | >=8.1 | CLI |
| rich | >=13.0 | コンソールUI |
| structlog | >=23.0 | ログ出力 |
| tenacity | >=8.2 | リトライ処理 |

### データベース

JRVLTSQLは**SQLite**（デフォルト）と**PostgreSQL**に対応しています。

- **SQLite**: Python標準の`sqlite3`モジュールを使用。追加インストール不要
- **PostgreSQL**: マルチユーザー/サーバーデプロイ向け。`pg8000` または `psycopg` が必要

## JRA-VAN DataLab (JV-Link) のセットアップ

1. [JRA-VAN DataLab](https://jra-van.jp/)で会員登録
2. DataLabソフトウェアをインストール
3. サービスキーを取得

!!! warning "注意"
    JV-Link APIはWindowsでのみ動作します。Linux/macOSでは使用できません。

## 動作確認

```bash
# バージョン確認
jltsql version

# ヘルプ表示
jltsql --help
```

## トラブルシューティング

### COM APIエラー

```
pywintypes.com_error: (-2147221005, 'Invalid class string', None, None)
```

**解決策**: JRA-VAN DataLab がインストールされているか確認してください。

### サービスキーエラー

```
JVLinkError: Service key not set
```

**解決策**: DataLabソフトウェアでサービスキーを設定してください。

### 日次同期をタスク登録したい

```powershell
powershell -ExecutionPolicy Bypass -File .\install_tasks.ps1 -Force
```

`JRVLTSQL_DailySync` が毎日 `06:30` に登録されます。
