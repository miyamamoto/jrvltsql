# インストール

## 必要要件

- **OS**: Windows 10/11（JV-Link / NV-Link COM APIはWindowsのみ対応）
- **Python**: 3.12 (32-bit) — NV-Link (地方競馬DATA) 対応のため必須
- **JRA-VAN**: DataLab会員登録が必要（中央競馬データ利用時）
- **地方競馬DATA**: サービス契約が必要（地方競馬データ利用時）

## Python 3.12 (32-bit) のインストール

NV-Link (地方競馬DATA) APIは32-bit COM DLLとして提供されており、**32-bit Python環境が必須**です。

### インストール手順

1. [Python 3.12 公式サイト](https://www.python.org/downloads/)にアクセス
2. **Windows installer (32-bit)** をダウンロード
   - 注意: 64-bit版ではなく、必ず**32-bit版**をダウンロードしてください
3. インストーラーを実行
   - 「Add Python to PATH」に必ずチェック
   - 「Install Now」をクリック
4. インストール後、確認：
   ```bash
   # バージョン確認
   python --version
   # 出力例: Python 3.12.x

   # 32-bit であることを確認
   python -c "import struct; print(struct.calcsize('P') * 8)"
   # 出力: 32 (32-bitの場合)
   ```

### なぜ32-bit Pythonが必要か

- **NV-Link (地方競馬DATA)**: `NVDTLabLib.NVLink` — 32-bit COM DLLとして提供
- **64-bit Python + DllSurrogate**: 理論上可能だが、DAX Errorなど不安定な動作を確認
- **32-bit Python**: APIと直接通信可能で、安定動作を確認済み

JRA-VAN (JV-Link) のみを使用する場合は64-bit Pythonでも動作しますが、地方競馬対応を考慮し**32-bit環境を推奨**します。

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
| pywin32 | >=305 | JV-Link / NV-Link COM API連携 |
| pyyaml | >=6.0 | 設定ファイル |
| click | >=8.1 | CLI |
| rich | >=13.0 | コンソールUI |
| structlog | >=23.0 | ログ出力 |
| tenacity | >=8.2 | リトライ処理 |

### データベース

JRVLTSQLは**SQLite**（デフォルト）と**PostgreSQL**に対応しています。

- **SQLite**: Python標準の`sqlite3`モジュールを使用。追加インストール不要
- **PostgreSQL**: マルチユーザー/サーバーデプロイ向け。`psycopg2`が必要

## JRA-VAN DataLab (JV-Link) のセットアップ

1. [JRA-VAN DataLab](https://jra-van.jp/)で会員登録
2. DataLabソフトウェアをインストール
3. サービスキーを取得

## 地方競馬DATA (NV-Link) のセットアップ

1. 地方競馬DATAサービスに契約
2. NV-Link (NVDTLabLib) ソフトウェアをインストール
3. サービスキーを取得
4. `config/config.yaml`で`initialization_key: "UNKNOWN"`を設定（デフォルト値。変更すると-301認証エラーが発生します）

!!! warning "注意"
    JV-Link / NV-Link APIはWindowsでのみ動作します。Linux/macOSでは使用できません。

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

**解決策**: JRA-VAN DataLab または NV-Link がインストールされているか確認してください。

### NV-Link ProgIDエラー

NV-Linkは `NVDTLabLib.NVLink` をProgIDとして使用します。登録されていない場合は `regsvr32 NVDTLab.dll` を実行してください。

### サービスキーエラー

```
JVLinkError: Service key not set
```

**解決策**: DataLabソフトウェアでサービスキーを設定してください。

### NV-Link 認証エラー (-301)

```
NVLinkError: -301
```

**解決策**: `config/config.yaml`の`initialization_key`が`"UNKNOWN"`であることを確認してください。他の値を設定すると認証エラーが発生します。
