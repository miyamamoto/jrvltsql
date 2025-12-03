# JRVLTSQL

JRA-VAN DataLabの競馬データをSQLiteにインポートするツール

## インストール

### 必要要件

- Windows 10/11
- Python 3.10+ **(32bit版)**
- JRA-VAN DataLab会員

### セットアップ

```bash
# インストール
pip install git+https://github.com/miyamamoto/jrvltsql.git

# 初期セットアップ（対話形式）
python scripts/quickstart.py
```

`quickstart.py` が対話形式でセットアップオプションを案内します。

### Python 32bit版について

JV-Link APIは32bit専用です。64bit版Pythonでは動作しません。

```bash
# 確認方法
python -c "import struct; print(struct.calcsize('P') * 8, 'bit')"
```

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

## データ構造

- **NL_テーブル**: 蓄積系データ（レース、馬、騎手など）
- **RT_テーブル**: 速報系データ（リアルタイムオッズなど）
- **TS_テーブル**: 時系列オッズ

## ライセンス

Apache License 2.0

取得データは[JRA-VAN利用規約](https://jra-van.jp/info/rule.html)に従ってください。
