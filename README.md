# JRVLTSQL

JRA-VAN DataLab / 地方競馬DATA の競馬データをSQLite・PostgreSQLにインポートするツール

## 特徴

- **中央競馬 (JRA)**: JRA-VAN DataLab (JV-Link) 対応
- **地方競馬 (NAR)**: 地方競馬DATA UmaConn (NV-Link) 対応
- **41種のパーサー**: 38 JRA + 3 NAR (HA, NU, BN) に対応
- **データベース**: SQLite（セットアップ不要）/ PostgreSQL 対応
- **リアルタイム監視**: オッズ・速報データの自動取得
- **64-bit Python対応**: DLL Surrogateによる64-bit環境サポート

## インストール

### 必要要件

- Windows 10/11
- Python 3.12以上
- JRA-VAN DataLab会員（中央競馬を使う場合）
- 地方競馬DATA会員（地方競馬を使う場合）

### Python環境

**推奨: 64-bit Python 3.12+**

DLL Surrogateを使うことで、64-bit Pythonから32-bit COM DLL（JV-Link / NV-Link）を利用できます。

```bash
# DLL Surrogateのセットアップ（管理者権限のPowerShell/コマンドプロンプトで実行）
python docs/gists/check_dll_surrogate.py --fix
# 詳細は docs/qiita_64bit_python_com.md を参照
```

**32-bit Pythonでも動作します**（COM DLLと直接通信）。

### セットアップ

```bash
pip install git+https://github.com/miyamamoto/jrvltsql.git
```

## 使い方

### クイックスタート

**quickstart.bat をダブルクリック** で対話形式のセットアップが始まります。

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

SQLiteまたはPostgreSQLを選択できます。

```bash
jltsql fetch --db sqlite      # SQLite（デフォルト、セットアップ不要）
jltsql fetch --db postgresql  # PostgreSQL（pg8000ドライバ使用）
```

## 地方競馬DATA対応 (NAR)

### 必要条件

- [地方競馬DATA](https://www.keiba-data.com/) 会員登録
- UmaConnソフトウェアのインストール
- サービスキーの設定
- `config/config.yaml` に `initialization_key: "UNKNOWN"` を設定

### 使用方法

```bash
# 地方競馬データの取得
jltsql fetch --source nar --from 20240101 --to 20241231 --spec RACE

# 地方競馬リアルタイム監視
jltsql monitor --source nar

# ステータス確認（JRAと地方競馬両方）
jltsql status --source all
```

### NAR対応レコード

| レコード | 内容 |
|---------|------|
| RA | レース情報 |
| SE | 馬情報 |
| HR | 払戻情報 |
| H1 | 票数情報 |
| H6 | 票数情報(6) |
| O1-O6 | オッズ |
| HA | 払戻情報(NAR独自) |
| WF | 重勝式(WIN5) |
| BN | 馬主マスタ |

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

## 技術的な詳細

### DLL Surrogate (64-bit Python対応)

JV-Link / NV-Link のCOM DLLは32-bitですが、DLL Surrogateを設定することで64-bit Pythonから利用可能です。

```
# レジストリに以下を設定（AppID + DllSurrogate=""）
# JV-Link CLSID: {2AB1774D-0C41-11D7-916F-0003479BEB3F}
# NV-Link CLSID: {F726BBA6-5784-4529-8C67-26E152D49D73}
```

**注意**: DLL Surrogate経由では `option=2`（未読データ取得）を推奨。`option=3/4` はアウトプロセス通信でハングする場合があります。

### NV-Link 初期化

NV-Linkの初期化キーは `"UNKNOWN"` を使用してください。他のキーでは `-301` 認証エラーが発生します。

### トラブルシューティング

**-203 エラー（初回セットアップ未完了）**:

NVDTLab設定ツールを起動し、初回セットアップ（全データダウンロード）を実行してください。

**-3 エラー（ファイル未検出）**:

`option=2` で既読データを再取得しようとした場合に発生します。`fromtime` を新しいタイムスタンプに更新してください。

**-116 エラー（未提供データスペック）**:

NV-Linkで未対応のデータスペック（例: DIFF）を指定した場合に発生します。

## ライセンス

- 非商用利用: Apache License 2.0
- 商用利用: 事前にお問い合わせください → oracle.datascientist@gmail.com

取得データは[JRA-VAN利用規約](https://jra-van.jp/info/rule.html)に従ってください。
