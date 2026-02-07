# Research: 地方競馬データ対応（UmaConn連携）

**Feature**: 001-local-racing-support
**Date**: 2025-12-15

## 1. UmaConn API仕様

### Decision
UmaConn APIはJV-Link APIの「JV」→「NV」置換で対応可能。COM ProgIDは`NVDTLabLib.NVLink`。

### Rationale
- 公開されている情報（Qiita記事、kmy-keibaソースコード）から、APIメソッドは以下の対応関係:
  - `JVInit` → `NVInit`
  - `JVOpen` → `NVOpen`
  - `JVRead` → `NVRead`
  - `JVGets` → `NVGets`
  - `JVClose` → `NVClose`
  - `JVRTOpen` → `NVRTOpen`
- パラメータと戻り値の構造も同一
- エラーコードも同一パターン（-1=データなし、-100系=認証エラー等）

### Alternatives Considered
1. **スクレイピング**: 却下。利用規約違反、データ品質不安定
2. **地方競馬公式API**: 存在しない
3. **第三者サービス**: 却下。データの即時性・網羅性で劣る

### References
- [Qiita: Pythonで地方競馬DATAのデータを取得する](https://qiita.com/masachaco/items/7aa4afa4ca70d4eb93d9)
- [GitHub: kmy-keiba](https://github.com/kmycode/kmy-keiba) - C#実装参考

---

## 2. データ形式互換性

### Decision
地方競馬のレコード形式はJRA-VANと互換性があり、既存の38種パーサーをそのまま再利用可能。

### Rationale
- PC-KEIBAでの検証により、データ構造は「jvd_」→「nvd_」の置換で対応
- レコード種別（RA, SE, HR, O1-O6等）は同一
- フィールド定義も同一（Year, MonthDay, JyoCD等）
- Shift-JIS (cp932) エンコーディングも同一

### Key Differences
| 項目 | JRA-VAN | 地方競馬DATA |
|------|---------|--------------|
| 競馬場コード | 01-10 | 30-51 |
| 開催スケジュール(YS) | 提供あり | 提供なし（RAから集計要） |
| 脚質データ | 提供あり | 提供なし |
| データマイニング予想 | 提供あり | 提供なし |

### Alternatives Considered
1. **専用パーサー作成**: 却下。差分が競馬場コードのみでコスト対効果低い
2. **パーサー継承**: 却下。変更箇所がないため不要

---

## 3. テーブル命名規則

### Decision
NAR（地方競馬）テーブルは既存テーブル名に`_NAR`接尾辞を付与。

### Rationale
- `NL_RA` → `NL_RA_NAR`（地方競馬レース詳細）
- `NL_SE` → `NL_SE_NAR`（地方競馬馬毎レース情報）
- 同一データベース内でJRAとNARを共存可能
- SQLクエリで`SELECT * FROM NL_RA UNION ALL SELECT * FROM NL_RA_NAR`のような横断検索が可能
- スキーマ定義は完全同一（PRIMARY KEY、INDEX含む）

### Alternatives Considered
1. **プレフィックス（NAR_NL_RA）**: 却下。既存命名規則（NL_, RT_, TS_）との一貫性低下
2. **別データベースファイル**: 却下。横断クエリが複雑化
3. **JyoCDで区別**: 却下。01-10と30-51で重複なしだが、クエリが煩雑

---

## 4. 地方競馬場コード

### Decision
地方競馬場コード30-51を`nvlink/constants.py`に定義。

### Rationale
JRA競馬場コード（01-10）と重複しないため、同一データベースで共存可能。

```python
NAR_JYO_CODES = {
    "30": "門別",
    "31": "北見（廃止）",
    "32": "岩見沢（廃止）",
    "33": "帯広",
    "34": "旭川（廃止）",
    "35": "盛岡",
    "36": "水沢",
    "37": "上山（廃止）",
    "38": "三条（廃止）",
    "39": "足利（廃止）",
    "40": "宇都宮（廃止）",
    "41": "高崎（廃止）",
    "42": "浦和",
    "43": "船橋",
    "44": "大井",
    "45": "川崎",
    "46": "金沢",
    "47": "笠松",
    "48": "名古屋",
    "49": "中京（廃止）",
    "50": "園田",
    "51": "姫路",
    "52": "益田（廃止）",
    "53": "福山（廃止）",
    "54": "高知",
    "55": "佐賀",
    "56": "荒尾（廃止）",
    "57": "中津（廃止）",
}
```

---

## 5. Python環境（64bit対応）

### Decision
UmaConnはJV-Linkと同様にCOM API経由でアクセスするため、64bit Pythonで動作可能。

### Rationale
- JV-Link (JVDTLab.JVLink) が64bit Pythonで動作している実績あり
- UmaConn (NVDTLabLib.NVLink) も同様のCOM API設計
- Windows COM はプロセス間通信で32bit/64bitの違いを吸収
- pywin32の`win32com.client.Dispatch()`はCOMサロゲートを自動的に処理

### Implementation
- JVLinkWrapperと同一の実装パターンを使用
- 特別なアーキテクチャチェックは不要
- 既存の64bit Python環境でそのまま動作

```python
# JVLinkWrapperと同様の実装
import win32com.client
self._nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
```

### Note
古い情報（2020年頃）では32bit制限が報告されていたが、現在のUmaConnは64bit環境でも動作する。JV-Linkと同様のCOM API設計を採用しているため、pywin32経由で問題なくアクセス可能。

---

## 6. CLIオプション設計

### Decision
`--source {jra|nar|all}`オプションを全コマンドに追加。デフォルトは`jra`。

### Rationale
- 後方互換性維持: オプション省略時は従来通りJRA
- 統一インターフェース: 同じコマンド体系で両方操作
- 拡張性: 将来的な他データソース追加に対応可能

### Implementation
```bash
# 既存動作（JRAデフォルト）
jltsql fetch --spec RACE

# 地方競馬データ
jltsql fetch --source nar --spec RACE

# 両方のステータス
jltsql status --source all

# リアルタイム監視
jltsql monitor --source nar
```

---

## 7. エラーハンドリング

### Decision
UmaConn固有のエラーメッセージを日本語で提供。

### Error Cases
| エラー | メッセージ |
|--------|----------|
| UmaConn未インストール | `UmaConn (地方競馬DATA) がインストールされていません。地方競馬DATAのセットアップを完了してください。` |
| サービスキー未設定 | `地方競馬DATAのサービスキーが設定されていません。NVDTLab設定ツールで設定してください。` |
| 契約外データ | `このデータ種別は地方競馬DATAの契約に含まれていません。` |

---

## Summary

| 項目 | 決定事項 |
|------|----------|
| API | NVDTLabLib.NVLink (JV→NV置換) |
| パーサー | 既存38種をそのまま再利用 |
| テーブル | _NAR接尾辞で区別 |
| 競馬場コード | 30-51 |
| Python | 64bit対応（JV-Link同様） |
| CLI | `--source {jra|nar|all}` |
| デフォルト | JRA（後方互換性） |
