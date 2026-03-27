# JRVLTSQL

JRA-VAN DataLab の競馬データを SQLite・PostgreSQL にインポートするツール。

## 特徴

- **中央競馬 (JRA)**: JRA-VAN DataLab (JV-Link) 対応 — 38種のパーサー
- **データベース**: SQLite（セットアップ不要）/ PostgreSQL 対応
- **リアルタイム監視**: オッズ・速報データの自動取得
- **quickstart.bat**: ダブルクリックで対話形式セットアップ

## 必要要件

| 項目 | 要件 |
|------|------|
| OS | Windows 10 / 11 |
| Python | 3.12以上 **（32-bit 必須）** |

> ⚠️ **64-bit Python は非対応です。** JV-Link の COM DLL が 32-bit のため、32-bit Python が必要です。詳細は [技術詳細](docs/TECHNICAL.md) を参照してください。
>
> ⚠️ **Windows 専用です。** JV-Link は Windows COM コンポーネントとして提供されており、macOS や Linux 上では動作しません。Wine・WSL・COM Surrogate 等による代替手段もかなり検証しましたが、現時点では安定動作に至っていません。

## 🚀 ワンコマンドインストール

PowerShell で以下を実行するだけ！Python・仮想環境・依存パッケージすべて自動でセットアップされます。

```powershell
irm https://raw.githubusercontent.com/miyamamoto/jrvltsql/master/install.ps1 | iex
```

> 📦 32-bit Python の自動検出、仮想環境作成、パッケージインストールまで一括で行います。

### 手動インストール

```bash
pip install git+https://github.com/miyamamoto/jrvltsql.git
```

## クイックスタート

**`quickstart.bat` をダブルクリック**するだけで、対話形式のセットアップが始まります。

- 32-bit Python を自動検出（`py -3.12-32` → `py -32` → フォールバック）
- テーブル作成 → データ取得 → リアルタイム監視まで一括実行

コマンドラインオプション:

```bash
python scripts/quickstart.py              # 対話形式
python scripts/quickstart.py --years 5    # 過去5年分
python scripts/quickstart.py --no-odds    # オッズ除外
python scripts/quickstart.py -y           # 確認スキップ
```

## 中央競馬 (JRA) セットアップ

1. [JRA-VAN DataLab](https://jra-van.jp/dlb/) で会員登録し、サービスキーを取得
2. JV-Link ソフトウェアをインストール
3. `config/config.yaml` にサービスキーを設定:

```yaml
jvlink:
  service_key: "XXXX-XXXX-XXXX-XXXX-X"
```

4. `quickstart.bat` を実行、または:

```bash
jltsql fetch --source jra --from 20240101 --to 20241231
```

## CLI コマンド

```bash
jltsql status                    # ステータス確認
jltsql fetch --spec RA           # 個別データ取得
jltsql fetch --db postgresql     # PostgreSQL に出力
jltsql monitor                   # リアルタイム監視
```

## データベース

| DB | 説明 |
|----|------|
| SQLite | デフォルト。セットアップ不要。`data/keiba.db` に保存 |
| PostgreSQL | `--db postgresql` で指定。pg8000 ドライバ使用 |

## 対応パーサー（38種）

### 中央競馬 — 38パーサー

レース(RA), 競走馬(SE), 払戻(HR), 票数(H1,H6), オッズ(O1-O6), 騎手(KS), 調教師(CH), 馬主(BN), 繁殖馬(HN), 産駒(SK), 競馬場(JC), コース(CC), レコード(RC), 重勝式(WF), 他

## ドキュメント

- [技術詳細](docs/TECHNICAL.md) — 32-bit制約、JV-Link設定、トラブルシューティング
- [アーキテクチャ](docs/ARCHITECTURE_DESIGN.md) — 設計ドキュメント
- [CLI リファレンス](docs/CLI.md) — コマンド詳細
- [設定](docs/CONFIGURATION.md) — 設定ファイルの詳細

## 更新履歴

詳細は [CHANGELOG.md](CHANGELOG.md) を参照してください。

### v1.1.0 (2025-02-08)
- **#43** テストカバレッジ拡充の修正
- **#42** テスト3件の失敗修正（wrapper挙動との整合性）
- **#41** テストカバレッジ拡充（CLI、インストーラー）
- **#38** クロスプラットフォーム検証の注記追加
- **#37** Windows専用であることをREADMEに明記
- **#36** ワンコマンドインストーラーをREADMEに追加
- **#35** v1.1.0 リリース準備
- **#34** H1/H6パーサーのフルストラクト対応
- **#33** ワンコマンドインストーラーと自動アップデート機能

### v1.0.0 以前
- **#28** JRA実データテストフィクスチャ（27パーサー, 81レコード）
- **#20** quickstart.py UI文言・表示の修正
- **#14** 32-bit Python 必須に変更
- **#9** README 再構成、技術詳細を docs/TECHNICAL.md に分離

## ライセンス

- 非商用利用: Apache License 2.0
- 商用利用: 事前にお問い合わせください → oracle.datascientist@gmail.com

取得データは [JRA-VAN利用規約](https://jra-van.jp/info/rule.html) に従ってください。
