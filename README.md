# JRVLTSQL

JRA-VAN DataLabの競馬データをSQLiteにインポートするツール

## インストール

### 必要要件

- Windows 10/11
- **Python 3.12 (32-bit)** - 地方競馬DATA対応のため必須
- JRA-VAN DataLab会員

### Python 3.12 (32-bit) のインストール

地方競馬DATA (UmaConn) APIは32-bit Pythonでのみ動作するため、32-bit版のインストールが必要です：

1. [Python 3.12 公式サイト](https://www.python.org/downloads/)から **Windows installer (32-bit)** をダウンロード
2. インストール時に「Add Python to PATH」にチェック
3. インストール後、コマンドプロンプトで確認：
   ```bash
   python --version  # Python 3.12.x と表示されることを確認
   python -c "import struct; print(struct.calcsize('P') * 8)"  # 32 と表示されることを確認
   ```

### セットアップ

```bash
pip install git+https://github.com/miyamamoto/jrvltsql.git
```

**quickstart.bat をダブルクリック** で対話形式のセットアップが始まります。

## 使い方

### quickstartオプション

```bash
python scripts/quickstart.py              # 対話形式
python scripts/quickstart.py --years 5    # 過去5年分
python scripts/quickstart.py --no-odds    # オッズ除外
python scripts/quickstart.py -y           # 確認スキップ
```

### CLIコマンド

```bash
jltsql status           # ステータス確認
jltsql fetch --spec RA  # 個別データ取得
jltsql monitor          # リアルタイム監視
```

### データベース

JRVLTSQLは32-bit Python環境でSQLiteまたはPostgreSQLデータベースを使用します。

```bash
jltsql fetch --db sqlite      # SQLite（デフォルト、セットアップ不要）
jltsql fetch --db postgresql  # PostgreSQL（pg8000ドライバ使用）
```

**注意**: 32-bit Python環境ではpg8000（純Python製PostgreSQLドライバ）を使用します。

## 地方競馬DATA対応 (NAR Support)

JRVLTSQLは地方競馬DATA（UmaConn）にも対応しています。

### 必要条件

- 地方競馬DATA会員登録（https://www.keiba-data.com/）
- UmaConnソフトウェアのインストール
- サービスキーの設定

### 使用方法

```bash
# 地方競馬データの取得
jltsql fetch --source nar --from 20240101 --to 20241231 --spec RACE

# 地方競馬リアルタイム監視
jltsql monitor --source nar

# ステータス確認（JRAと地方競馬両方）
jltsql status --source all
```

### トラブルシューティング

**-203 エラーが発生する場合**:

```
FetcherError: NV-Linkダウンロードエラー (code: -203)
```

このエラーは NVDTLab の初回セットアップが未完了の場合に発生します：

1. **NVDTLab設定ツールを起動**
2. **「データダウンロード」タブを選択**
3. **初回セットアップを実行**（全データのダウンロード）
4. **セットアップ完了後、再度データ取得を実行**

詳細は [エラーコードリファレンス](docs/reference/error-codes.md#nvlink--203-エラー-地方競馬data) を参照してください。

### データベーステーブル

地方競馬データは `_NAR` サフィックス付きのテーブルに保存されます：

| 中央競馬 | 地方競馬 |
|---------|---------|
| NL_RA | NL_RA_NAR |
| NL_SE | NL_SE_NAR |
| RT_O1 | RT_O1_NAR |

### 横断検索

```sql
-- 中央・地方両方のレース情報を検索
SELECT * FROM NL_RA
UNION ALL
SELECT * FROM NL_RA_NAR
WHERE Year = 2024;
```

## データ構造

- **NL_テーブル**: 蓄積系データ（レース、馬、騎手など）
- **RT_テーブル**: 速報系データ（リアルタイムオッズなど）
- **TS_テーブル**: 時系列オッズ

## 技術的な制約

### なぜ32-bit Pythonが必要か

地方競馬DATA (UmaConn) のCOM APIは32-bit DLLとして提供されており、以下の理由から32-bit Python環境が必須です：

- **64-bit Python + DllSurrogate**: 理論上は可能だが、実際には`DAX Error`など不安定な動作が発生
- **32-bit Python**: UmaConn APIと直接通信でき、安定動作を確認済み

JRA-VAN (JV-Link) のみを使用する場合は64-bit Pythonでも動作可能ですが、将来的な地方競馬対応を考慮し、32-bit環境での開発を推奨します。

## ライセンス

- 非商用利用: Apache License 2.0
- 商用利用: 事前にお問い合わせください → oracle.datascientist@gmail.com

取得データは[JRA-VAN利用規約](https://jra-van.jp/info/rule.html)に従ってください。
