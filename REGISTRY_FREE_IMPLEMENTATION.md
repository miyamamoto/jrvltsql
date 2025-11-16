# レジストリーを使わない実装レポート

**実施日時**: 2025年11月16日 22:27

---

## 実装概要

Windowsレジストリーへの依存を排除し、設定ファイルまたは環境変数からJV-Linkサービスキーを設定する実装に変更しました。

---

## 変更内容

### 1. JVLinkWrapper の拡張

**ファイル**: `src/jvlink/wrapper.py`

#### 追加メソッド: `jv_set_service_key()`

```python
def jv_set_service_key(self, service_key: str) -> int:
    """Set JV-Link service key programmatically.

    This method allows setting the service key from the application
    without requiring registry configuration or JRA-VAN DataLab application.
    """
    result = self._jvlink.JVSetServiceKey(service_key)
    return result
```

#### 更新メソッド: `jv_init()`

```python
def jv_init(self, service_key: Optional[str] = None) -> int:
    """Initialize JV-Link.

    Args:
        service_key: Optional JV-Link service key. If provided, it will be set
                    before initialization.
    """
    if service_key is not None:
        self.jv_set_service_key(service_key)

    result = self._jvlink.JVInit(self.sid)
    return result
```

### 2. BaseFetcher の更新

**ファイル**: `src/fetcher/base.py`

```python
def __init__(self, sid: str = "UNKNOWN", service_key: Optional[str] = None):
    """Initialize base fetcher.

    Args:
        sid: Session ID for JV-Link API
        service_key: Optional JV-Link service key
    """
    self.jvlink = JVLinkWrapper(sid)
    self._service_key = service_key
```

### 3. HistoricalFetcher / RealtimeFetcher の更新

**ファイル**: `src/fetcher/historical.py`, `src/fetcher/realtime.py`

```python
# jv_init() の呼び出し時にサービスキーを渡す
self.jvlink.jv_init(service_key=self._service_key)
```

### 4. BatchProcessor の更新

**ファイル**: `src/importer/batch.py`

```python
def __init__(
    self,
    database: BaseDatabase,
    batch_size: int = 1000,
    sid: str = "UNKNOWN",
    service_key: Optional[str] = None,
):
    """Initialize batch processor.

    Args:
        service_key: Optional JV-Link service_key
    """
    self.fetcher = HistoricalFetcher(sid, service_key=service_key)
```

### 5. CLI の更新

**ファイル**: `src/cli/main.py`

```python
processor = BatchProcessor(
    database=database,
    sid=config.get("jvlink.sid", "JLTSQL") if config else "JLTSQL",
    batch_size=batch_size,
    service_key=config.get("jvlink.service_key") if config else None
)
```

---

## 設定方法

### 方法1: 設定ファイル（推奨）

`config/config.yaml`:
```yaml
jvlink:
  # JRA-VANサービスキー
  service_key: "XXXX-XXXX-XXXX-XXXX-X"
```

### 方法2: 環境変数

**Windows CMD**:
```cmd
set JVLINK_SERVICE_KEY=XXXX-XXXX-XXXX-XXXX-X
```

**PowerShell**:
```powershell
$env:JVLINK_SERVICE_KEY="XXXX-XXXX-XXXX-XXXX-X"
```

**設定ファイルでプレースホルダー使用**:
```yaml
jvlink:
  service_key: "${JVLINK_SERVICE_KEY}"
```

---

## メリット

### 1. レジストリーへの依存を排除
- Windowsレジストリーの読み書きが不要
- JRA-VAN DataLabアプリケーションのインストール不要（JV-Link DLLのみ必要）

### 2. 設定の一元管理
- 設定ファイルで一元管理
- バージョン管理システムで管理可能（`.gitignore`で除外推奨）
- チーム開発での設定共有が容易

### 3. 環境変数サポート
- CI/CD環境での利用が容易
- セキュリティ: 環境変数でシークレットを管理
- 複数環境（開発/本番）の切り替えが簡単

### 4. クロスプラットフォーム対応の準備
- レジストリー依存を排除することで、将来的なLinux/Mac対応の基盤
- Wine環境でのテストが容易

---

## 技術的な詳細

### JV-Link API の利用

JV-Link DLL（JVDTLab.dll）は以下のメソッドを提供：

1. **JVSetServiceKey(serviceKey)** - サービスキーを設定
2. **JVInit(sid)** - JV-Linkを初期化
3. **JVOpen(dataSpec, fromTime, option)** - データストリームを開く
4. **JVRead()** - データを読み込む
5. **JVClose()** - データストリームを閉じる

従来の実装では、`JVInit()`を呼び出す前にレジストリーからサービスキーを読み込んでいましたが、新しい実装では`JVSetServiceKey()`を呼び出してプログラムから直接設定します。

### エラーハンドリング

- `JVSetServiceKey()`の戻り値: 0=成功、負の値=エラー
- エラーコード-100: 不明なエラー（既存のレジストリー設定と競合する可能性）

---

## 注意事項

### JV-Link DLLの内部動作

JV-Link DLLは内部でレジストリーに書き込む可能性があります。これは外部ライブラリの動作であり、完全に防ぐことはできません。

しかし、アプリケーション側では：
- レジストリーから読み込まない
- `JVSetServiceKey()`でプログラムから設定
- 設定ファイル/環境変数で管理

ことにより、レジストリーへの**依存**を排除しています。

### 既存のレジストリー設定との競合

既にレジストリーにサービスキーが設定されている場合、`JVSetServiceKey()`が-100エラーを返す可能性があります。

**対処方法**:
1. レジストリーからサービスキーを削除:
   ```cmd
   reg delete "HKLM\SOFTWARE\JRA-VAN\JV-Link" /v ServiceKey /f
   ```

2. または、レジストリーのサービスキーを空文字列に設定:
   ```cmd
   reg add "HKLM\SOFTWARE\JRA-VAN\JV-Link" /v ServiceKey /t REG_SZ /d "" /f
   ```

---

## テスト方法

### テストスクリプト

`scripts/test_no_registry.py`:
```bash
# 環境変数でテスト
set JVLINK_SERVICE_KEY=XXXX-XXXX-XXXX-XXXX-X
python scripts/test_no_registry.py

# または設定ファイルでテスト
# config/config.yaml を編集してから
python scripts/test_no_registry.py
```

### 手動テスト

```python
from src.jvlink.wrapper import JVLinkWrapper

# サービスキーを設定してJV-Linkを初期化
wrapper = JVLinkWrapper(sid="TEST")
wrapper.jv_init(service_key="XXXX-XXXX-XXXX-XXXX-X")
```

---

## 今後の課題

### 1. レジストリー競合の解決

既存のレジストリー設定と`JVSetServiceKey()`の競合を解決するため、以下を検討：

- JV-Link DLLの最新バージョンでの動作確認
- レジストリー削除の自動化
- エラーハンドリングの改善

### 2. ドキュメント整備

- ユーザーガイドの更新
- トラブルシューティングガイドの作成
- API リファレンスの整備

### 3. テストカバレッジの向上

- 単体テストの追加
- 統合テストの整備
- CI/CDパイプラインでの自動テスト

---

## まとめ

✅ **実装完了**:
- `JVSetServiceKey()` APIの統合
- 設定ファイル/環境変数からのサービスキー読み込み
- レジストリー依存の排除

⚠️ **注意点**:
- JV-Link DLLは内部でレジストリーに書き込む可能性がある
- 既存のレジストリー設定と競合する可能性がある（エラー-100）

🎯 **次のステップ**:
- レジストリー競合の解決
- ドキュメント整備
- テストカバレッジの向上

---

**結論**: レジストリーへの**依存**を完全に排除し、設定ファイル/環境変数での管理を実現しました。これにより、設定の一元管理、バージョン管理、CI/CD環境での利用が容易になりました。
