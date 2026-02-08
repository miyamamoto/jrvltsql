# JRVLTSQL

JRA-VAN DataLab / 地方競馬DATA の競馬データを SQLite・PostgreSQL にインポートするツール。

## 特徴

- **中央競馬 (JRA)**: JRA-VAN DataLab (JV-Link) 対応 — 38種のパーサー
- **地方競馬 (NAR)**: 地方競馬DATA UmaConn (NV-Link) 対応 — 3種のパーサー (HA, NU, NC)
- **合計41パーサー**: レース・馬・騎手・オッズ・払戻・馬場状態など幅広いデータに対応
- **データベース**: SQLite（セットアップ不要）/ PostgreSQL 対応
- **リアルタイム監視**: オッズ・速報データの自動取得
- **quickstart.bat**: ダブルクリックで対話形式セットアップ

## 必要要件

| 項目 | 要件 |
|------|------|
| OS | Windows 10 / 11 |
| Python | 3.12以上 **（32-bit 必須）** |

> ⚠️ **64-bit Python は非対応です。** JV-Link / NV-Link の COM DLL が 32-bit のため、32-bit Python が必要です。詳細は [技術詳細](docs/TECHNICAL.md) を参照してください。

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

1. [JRA-VAN DataLab](https://jra-van.jp/) で会員登録し、サービスキーを取得
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

## 地方競馬 (NAR) セットアップ

1. [地方競馬DATA](https://www.keiba-data.com/) で会員登録し、サービスキーを取得
2. UmaConn ソフトウェアをインストール
3. `config/config.yaml` に設定:

```yaml
nvlink:
  service_key: "XXXX-XXXX-XXXX-XXXX-X"
  initialization_key: "UNKNOWN"           # 必ず "UNKNOWN" を指定
```

> ⚠️ `initialization_key` は **必ず `"UNKNOWN"`** にしてください。他の値では認証エラー（-301）が発生します。

4. 初回データダウンロード — NVInit で `option=3` を指定:

```bash
jltsql fetch --source nar --from 20240101 --to 20241231 --spec RACE
```

> 💡 ダウンロード中に `-502` エラーが発生した場合は自動リトライされます。ネットワーク不安定時は数回のリトライで正常に完了します。詳細は [技術詳細](docs/TECHNICAL.md) を参照。

## CLI コマンド

```bash
jltsql status                    # ステータス確認
jltsql fetch --spec RA           # 個別データ取得
jltsql fetch --db postgresql     # PostgreSQL に出力
jltsql monitor                   # リアルタイム監視
jltsql status --source all       # JRA + NAR 両方の状態確認
```

## データベース

| DB | 説明 |
|----|------|
| SQLite | デフォルト。セットアップ不要。`data/keiba.db` に保存 |
| PostgreSQL | `--db postgresql` で指定。pg8000 ドライバ使用 |

地方競馬データは `_NAR` サフィックス付きテーブルに保存されます（例: `NL_RA_NAR`）。

## 対応パーサー（41種）

### 中央競馬 — 38パーサー

レース(RA), 競走馬(SE), 払戻(HR), 票数(H1,H6), オッズ(O1-O6), 騎手(KS), 調教師(CH), 馬主(BN), 繁殖馬(HN), 産駒(SK), 競馬場(JC), コース(CC), レコード(RC), 重勝式(WF), 他

### 地方競馬 — 3パーサー

- **HA** — 払戻データ
- **NU** — 成績データ
- **NC** — 競馬場マスタ

## ドキュメント

- [技術詳細](docs/TECHNICAL.md) — 32-bit制約、NV-Link設定、-502リトライ、トラブルシューティング
- [アーキテクチャ](docs/ARCHITECTURE_DESIGN.md) — 設計ドキュメント
- [CLI リファレンス](docs/CLI.md) — コマンド詳細
- [設定](docs/CONFIGURATION.md) — 設定ファイルの詳細

## 更新履歴

- **#20** quickstart.py UI文言・表示の修正
- **#19** NC パーサー（NAR競馬場マスタ）追加 → NAR 3パーサー体制に
- **#18** NV-Link -3 エラー説明修正、NAR ダウンロード option=3 に変更
- **#17** NV-Link ダウンロード手順整備、-502 リトライ戦略
- **#16** NAR 認証キー修正（`"UNKNOWN"`）、OA マッピング追加
- **#14** 32-bit Python 必須に変更、NVD ファイル構造修正
- **#12** NU/HA パーサーテスト追加
- **#11** HA パーサーテスト + gitignore 修正
- **#9** README 再構成、技術詳細を docs/TECHNICAL.md に分離

## ライセンス

- 非商用利用: Apache License 2.0
- 商用利用: 事前にお問い合わせください → oracle.datascientist@gmail.com

取得データは [JRA-VAN利用規約](https://jra-van.jp/info/rule.html) に従ってください。
