# インストール

## 必要要件

- **OS**: Windows 10/11（JV-Link COM APIはWindowsのみ対応）
- **Python**: 3.10以上
- **JRA-VAN**: DataLab会員登録が必要

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
| psycopg | >=3.1 | PostgreSQL接続 |
| duckdb | >=1.0.0 | DuckDBデータベース |
| pandas | >=2.0.0 | データ操作 |
| pyyaml | >=6.0 | 設定ファイル |
| click | >=8.1 | CLI |
| rich | >=13.0 | コンソールUI |

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
