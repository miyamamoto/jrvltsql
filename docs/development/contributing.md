# コントリビュートガイド

JRVLTSQLへの貢献方法について説明します。

## 開発環境のセットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/miyamamoto/jrvltsql.git
cd jrvltsql
```

### 2. 仮想環境の作成

```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 3. 開発用依存関係のインストール

```bash
pip install -e ".[dev]"
```

### 4. pre-commitフックの設定

```bash
pre-commit install
```

## コーディング規約

### スタイルガイド

- **フォーマッター**: Black
- **リンター**: Ruff
- **型チェック**: mypy

```bash
# フォーマット
black src/ tests/

# リント
ruff check src/ tests/

# 型チェック
mypy src/
```

### 設定

`pyproject.toml`に定義されています：

```toml
[tool.black]
line-length = 100

[tool.ruff]
line-length = 100
select = ["E", "W", "F", "I", "B", "C4", "UP"]
```

## テスト

### テストの実行

```bash
# 全テスト
pytest tests/ -v

# 特定のテスト
pytest tests/test_parser.py -v

# カバレッジ付き
pytest tests/ --cov=src --cov-report=html
```

### テストの構造

```
tests/
├── test_parser.py          # パーサーテスト
├── test_database.py        # データベーステスト
├── test_importer.py        # インポーターテスト
├── test_duckdb_handler.py  # DuckDBテスト
├── integration/            # 統合テスト
└── conftest.py             # pytest設定
```

### 新しいテストの追加

```python
import pytest
from src.parser.factory import get_parser_factory

class TestNewFeature:
    def test_basic_functionality(self):
        # Arrange
        factory = get_parser_factory()

        # Act
        result = factory.get_parser("RA")

        # Assert
        assert result is not None
```

## プルリクエスト

### 1. ブランチの作成

```bash
git checkout -b feature/new-feature
```

### 命名規則

- `feature/` - 新機能
- `fix/` - バグ修正
- `docs/` - ドキュメント
- `refactor/` - リファクタリング

### 2. 変更のコミット

```bash
git add .
git commit -m "feat: 新機能の説明"
```

### コミットメッセージ形式

```
<type>: <description>

[optional body]
```

| type | 説明 |
|------|------|
| feat | 新機能 |
| fix | バグ修正 |
| docs | ドキュメント |
| refactor | リファクタリング |
| test | テスト |
| chore | その他 |

### 3. プッシュとPR作成

```bash
git push origin feature/new-feature
```

GitHubでPull Requestを作成してください。

## イシュー

### バグ報告

以下の情報を含めてください：

- 再現手順
- 期待する動作
- 実際の動作
- 環境情報（Python版、OS等）

### 機能リクエスト

- 機能の説明
- ユースケース
- 提案する実装方法（あれば）

## ドキュメント

### ドキュメントの更新

```bash
# ローカルでプレビュー
pip install mkdocs-material
mkdocs serve

# http://localhost:8000 でプレビュー
```

### ドキュメントの構造

```
docs/
├── index.md                 # トップページ
├── getting-started/         # 入門
├── user-guide/              # ユーザーガイド
├── api/                     # APIリファレンス
├── development/             # 開発者向け
└── reference/               # 参考資料
```

## リリースプロセス

1. CHANGELOGの更新
2. バージョン番号の更新（`pyproject.toml`）
3. タグの作成
4. GitHubリリースの作成

```bash
git tag v2.3.0
git push origin v2.3.0
```

## 質問・サポート

- **Issues**: バグ報告・機能リクエスト
- **Discussions**: 質問・議論
- **Email**: oracle.datascientist@gmail.com

## ライセンス

コントリビューションはApache License 2.0の下でライセンスされます。
