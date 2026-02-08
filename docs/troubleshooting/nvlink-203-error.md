# NVLink -203 エラー詳細調査レポート

**作成日**: 2025-12-22
**対象**: UmaConn/NVLink (地方競馬DATA) の -203 エラー

## 概要

NVLink (UmaConn) API の `NVStatus` が継続的に `-203` エラーを返す問題について調査し、解決策を実装しました。

## 問題の詳細

### 症状

```
NVOpen: result=-301 (ダウンロード中), download_count=1
NVStatus: -203 (継続的に返される)
NVRead: -203 エラー
```

- `NVOpen` は成功（result=-301, download_count=1）
- しかし `NVStatus` が継続的に `-203` を返す
- その結果、`NVRead` も `-203` エラーで失敗

### -203 エラーコードの意味

**定義**: `JV_RT_OTHER_ERROR = -203` (その他エラー)

**JV-Link (JRA) の場合**: ネットワーク接続エラー
**NV-Link (NAR) の場合**: 以下の3つの原因が考えられる：

1. **NVDTLab の初回セットアップ未完了** (最も多い原因)
2. **データキャッシュの破損**
3. **option=1 (差分データモード) での既知の問題**

## 根本原因

### 1. NVDTLab セットアップ不完全

UmaConn (地方競馬DATA) では、初回データ取得前に NVDTLab 設定ツールでの「データダウンロード」が必須です。このセットアップが完了していない状態で `NVOpen` を呼び出すと：

- `NVOpen` は `-301` (ダウンロード中) を返す
- しかし内部的にダウンロード処理が失敗
- `NVStatus` が `-203` (その他エラー) を返し続ける

### 2. option=1 の互換性問題

NAR (NV-Link) では `option=1` (差分データ取得) が正常動作しません：

```python
# quickstart.py (行 3492-3498)
# NAR (NV-Link) では option 1 が正常動作しない（NVStatusが-203を返す既知の問題）
if data_source_str == 'nar':
    if option == 1 or option == 2:
        option = 4  # NAR: 強制的にセットアップモード（-203エラー回避）
```

**理由**: NV-Link API は JV-Link API と同じインターフェースを持ちますが、内部実装が異なるため、一部の option パラメータで動作が異なります。

### 3. エラーコード定義の不整合

調査時点では `nvlink/constants.py` の `ERROR_MESSAGES` 辞書に `-203` の定義がありませんでした。これにより、エラーメッセージが `"不明なエラーコード: -203"` となり、ユーザーが原因を特定できない状態でした。

## 実装した解決策

### 1. エラーコード定義の追加

**ファイル**: `src/nvlink/constants.py`

```python
ERROR_MESSAGES = {
    # ...
    # System Error Codes
    -201: "データベースエラー",
    -202: "ファイルエラー（ストリームが既にオープン中、または前回のCloseが呼ばれていません）",
    -203: "その他のエラー（NVDTLabのセットアップ不完全、またはキャッシュの問題）",
    # ...
}
```

### 2. エラーメッセージの改善

**ファイル**: `src/fetcher/historical.py` (行 354-364)

```python
if status == -203:
    raise FetcherError(
        f"NV-Linkダウンロードエラー (code: {status}): "
        "地方競馬DATAのセットアップが完了していないか、キャッシュに問題があります。\n"
        "対処方法:\n"
        "1. NVDTLab設定ツールを起動し、「データダウンロード」タブで初回セットアップを実行\n"
        "2. セットアップ完了後も問題が続く場合は、キャッシュをクリアして再試行\n"
        "3. アプリケーション(UmaConn/地方競馬DATA)を再起動\n"
        "注: NAR データ取得には option=3 (セットアップモード) の使用が推奨されます"
    )
```

### 3. リトライロジックの明確化

**ファイル**: `src/fetcher/historical.py` (行 286-295)

```python
# Retryable error codes (temporary errors that may resolve)
# -201: Database error (might be busy)
# -202: File error (might be busy)
# -203: Other error (NAR: often indicates incomplete NVDTLab setup or cache issue)
#       For NV-Link (NAR), -203 typically means:
#       1. Initial NVDTLab setup not completed
#       2. Cache corruption
#       3. option=1 (differential mode) not working properly
#       Best practice: Use option=3 (setup mode) for NAR data
retryable_errors = {-201, -202, -203}
```

- `-203` エラーは自動的に **5回までリトライ**
- リトライ間隔は通常の2倍 (1秒) に延長
- 5回リトライ後も解決しない場合は、詳細なエラーメッセージを表示

### 4. ドキュメントの追加

#### a. エラーコードリファレンス

**ファイル**: `docs/reference/error-codes.md`

NVLink -203 エラー専用のセクションを追加：
- 原因の説明
- 4段階の対処法
- JRA-VAN との違いの注意書き

#### b. README トラブルシューティング

**ファイル**: `README.md`

地方競馬DATA対応セクションに「トラブルシューティング」サブセクションを追加：
- -203 エラーの簡単な対処法
- エラーコードリファレンスへのリンク

#### c. 詳細調査レポート

**ファイル**: `docs/troubleshooting/nvlink-203-error.md` (このファイル)

## 対処法（ユーザー向け）

### 手順1: 初回セットアップの実行

1. **NVDTLab設定ツールを起動**
2. **「データダウンロード」タブを選択**
3. **初回セットアップを実行**
   - 全データのダウンロードが開始されます（数分～数十分かかります）
4. **セットアップ完了を待つ**

### 手順2: データ取得コマンドの実行

```bash
# quickstart.py は自動的に option=3 を使用（推奨）
python scripts/quickstart.py

# または CLI で明示的に NAR を指定
jltsql fetch --source nar --spec RACE --from 20240101 --to 20241231
```

### 手順3: キャッシュクリア（上記で解決しない場合）

1. **NVDTLab設定ツールを起動**
2. **キャッシュクリアを実行**
3. **アプリケーション (UmaConn/地方競馬DATA) を再起動**
4. **手順2を再実行**

## 技術的な詳細

### NVOpen と NVStatus の動作

```
[正常な流れ]
NVOpen("RACE", "20241201000000", option=3)
  -> result=-301 (ダウンロード中), download_count=1

NVStatus() (0.5秒ごとにポーリング)
  -> status=1000 (10%)
  -> status=2000 (20%)
  -> ...
  -> status=10000 (100%)
  -> status=0 (完了)

NVRead() (レコード読み取り開始)
  -> データ取得成功

[異常な流れ - セットアップ不完全]
NVOpen("RACE", "20241201000000", option=1)
  -> result=-301 (ダウンロード中), download_count=1

NVStatus() (0.5秒ごとにポーリング)
  -> status=-203 (その他エラー) ← 継続的に返される
  -> 5回リトライ後、FetcherError 発生

NVRead() (呼び出されない)
```

### -3（ダウンロード中）エラー

`NVRead` / `NVGets` が `-3` を返す場合、該当ファイルがまだサーバーからダウンロードされていないことを意味します。

```
NVGets: result=-3 (ダウンロード中です)
```

**対処法**: しばらく待ってから再試行するか、`option=3`（セットアップモード）で全データを事前ダウンロードしてください。

### -502 リトライ

`-502`（ダウンロード失敗）は一時的なネットワークエラーです。JRVLTSQLでは `-203`, `-402`, `-403`, `-502`, `-503` をリカバラブルエラーとして扱い、ファイルを削除（`NVDelete`）して読み取りを継続します。

```python
# wrapper.py の処理
# -203, -402, -403, -502, -503: リカバラブルエラー（ファイル削除して継続）
elif result in (-203, -402, -403, -502, -503):
    self._nvlink.NVDelete(filename)  # 問題のあるファイルを削除
    # 次のレコードの読み取りを継続
```

### option パラメータの違い

| option | JV-Link (JRA) | NV-Link (NAR) |
|--------|---------------|---------------|
| 1 | 差分データ取得 (正常動作) | **動作不安定** (-203エラー発生) |
| 2 | 今週データ | 未サポート |
| 3 | セットアップ (ダイアログあり) | **推奨** (安定動作、全データDL) |
| 4 | セットアップ (ダイアログなし) | 動作確認中 |

**推奨設定**: NAR データ取得には `option=3` を使用

### 既存の回避策

`quickstart.py` では既に以下の回避策が実装されています：

```python
# NAR の場合、option=1/2 を自動的に option=4 に変換
if data_source_str == 'nar':
    if option == 1 or option == 2:
        option = 4
```

これにより、ユーザーが明示的に option を指定しなくても、自動的に安定動作するモードが選択されます。

## 今後の課題

1. **NVDTLab セットアップ状態の事前チェック**
   - `NVInit` 後、`NVOpen` 前にセットアップ完了状態を確認するAPI調査
   - セットアップ未完了の場合、わかりやすいエラーメッセージを表示

2. **option=1 の動作調査**
   - UmaConn/NVDTLab の開発元に問い合わせ
   - option=1 を使用可能にする条件を特定

3. **自動セットアップ機能**
   - プログラムから NVDTLab のセットアップを自動実行する方法を調査
   - ユーザーの手動操作を不要にする

## 参考情報

- [UmaConn公式サイト](https://www.keiba-data.com/)
- [NVDTLab ドキュメント](https://www.keiba-data.com/nvdtlab/)
- [jrvltsql エラーコードリファレンス](../reference/error-codes.md)
- [jrvltsql 地方競馬DATA対応ドキュメント](../../README.md#地方競馬data対応-nar-support)

## 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2025-12-22 | 初版作成、-203 エラー対策実装 |
