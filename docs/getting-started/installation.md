# インストール

## 必要要件

- **OS**: Windows 10/11（JV-Link COM APIはWindowsのみ対応）
- **Python**: 3.12 (32-bit) - 地方競馬DATA対応のため必須
- **JRA-VAN**: DataLab会員登録が必要

## Python 3.12 (32-bit) のインストール

地方競馬DATA (UmaConn) APIは32-bit DLLとして提供されており、32-bit Python環境が必須です。

### インストール手順

1. [Python 3.12 公式サイト](https://www.python.org/downloads/)にアクセス
2. **Windows installer (32-bit)** をダウンロード
   - 注意: 64-bit版ではなく、必ず32-bit版をダウンロードしてください
3. インストーラーを実行
   - 「Add Python to PATH」に必ずチェック
   - 「Install Now」をクリック
4. インストール後、確認：
   ```bash
   # バージョン確認
   python --version
   # 出力例: Python 3.12.0

   # 32-bit/64-bit の確認
   python -c "import struct; print(struct.calcsize('P') * 8)"
   # 出力: 32 (32-bitの場合)
   ```

### なぜ32-bit Pythonが必要か

- **UmaConn (地方競馬DATA) API**: 32-bit COM DLLとして提供
- **64-bit Python + DllSurrogate**: 理論上可能だが、DAX Errorなど不安定な動作を確認
- **32-bit Python**: APIと直接通信可能で、安定動作を確認済み

JRA-VAN (JV-Link) のみを使用する場合は64-bit Pythonでも動作しますが、地方競馬対応を考慮し32-bit環境を推奨します。

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
| pywin32 | >=305 | JV-Link/UmaConn COM API連携 |
| pyyaml | >=6.0 | 設定ファイル |
| click | >=8.1 | CLI |
| rich | >=13.0 | コンソールUI |
| structlog | >=23.0 | ログ出力 |
| tenacity | >=8.2 | リトライ処理 |

### データベース

JRVLTSQLは**SQLite**を使用します。32-bit Python環境で安定動作するよう設計されています。

- **標準ライブラリ**: Python標準のsqlite3モジュールを使用
- **追加インストール不要**: Pythonに同梱
- **軽量・高速**: セットアップ不要で即座に利用可能

## JRA-VAN DataLabのセットアップ

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

**解決策**: JRA-VAN DataLabがインストールされているか確認してください。

### サービスキーエラー

```
JVLinkError: Service key not set
```

**解決策**: DataLabソフトウェアでサービスキーを設定してください。
