# リアルタイム同期メカニズムの仕組み

**作成日**: 2025年11月16日

---

## 質問

> リアルタイム同期を実施した場合って差分のデータはどのように更新されますか？

## 回答サマリ

**JLTSQLのリアルタイム同期は、差分データを「更新」ではなく「追加（INSERT）」で処理します。**

- ✅ 新しいデータは **追加（APPEND）** されます
- ❌ 既存データは **更新（UPDATE）** されません
- ⚠️ 同じデータを複数回取得すると **重複レコード** が発生する可能性があります

---

## 詳細説明

### 1. データ挿入メカニズム

#### 1.1 INSERT方式（UPSERTではない）

**コード**: `src/database/base.py:198`
```python
sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders})"
```

JLTSQLは `INSERT` のみを使用し、`INSERT OR REPLACE`（UPSERT）は使用していません。

#### 1.2 PRIMARY KEY / UNIQUE制約なし

**調査結果**: `src/database/schema.py`
```bash
$ grep "PRIMARY KEY\|UNIQUE" src/database/schema.py
# 結果: 0件
```

全38テーブルに **PRIMARY KEY** や **UNIQUE制約が一切定義されていません**。

これにより：
- データベースは重複レコードを拒否しません
- 同じレコードを複数回挿入しても、すべて受け入れられます
- 制約違反エラーは発生しません

---

### 2. リアルタイム監視の動作

#### 2.1 監視フロー

**コード**: `src/services/realtime_monitor.py:276-293`

```python
while not self._stop_event.is_set():
    # 速報データを連続取得
    for record in fetcher.fetch(data_spec=data_spec, continuous=True):
        # レコードを挿入（UPDATEではない）
        success = importer.import_single_record(record)

        # 統計更新
        if success:
            self.status.records_imported += 1
        else:
            self.status.records_failed += 1
```

#### 2.2 処理ステップ

1. **JVRTOpen** でリアルタイムストリームを開く
2. **連続ポーリング**: 1秒ごとに新しいデータをチェック（`time.sleep(1)`）
3. **INSERT**: 新しいレコードをそのまま追加
4. **繰り返し**: ストリームが開いている限り継続

**コード**: `src/fetcher/realtime.py:166-168`
```python
# データがない場合は待機
if record_count == 0:
    logger.debug("No new data available, waiting...")
    time.sleep(1)  # 1秒ごとにポーリング
```

---

### 3. 差分データの扱い

#### 3.1 JV-Link APIの動作

JV-Link API（`JVRTOpen`）は：
- **差分データのみ**を返す（すでに取得済みのデータは返さない）
- **内部で管理**: JV-Link DLLが最後に取得した位置を記憶
- **新着データのみ通知**: ポーリングごとに新しいデータだけを返す

#### 3.2 データベースでの処理

| ケース | JV-Link API | データベース処理 | 結果 |
|--------|-------------|------------------|------|
| 新しいレコード | 返す | INSERT | ✅ 追加 |
| 既存レコードの更新 | 返す（更新後のデータ） | INSERT | ⚠️ 新しい行として追加（旧データは残る） |
| 変更なし | 返さない | - | 何もしない |

#### 3.3 重複レコードの可能性

以下の場合、重複レコードが発生します：

**ケース1: 監視の再起動**
```bash
# 1回目の監視
jltsql monitor --daemon
# → レコードA, B, C を取得

# 監視を停止
jltsql monitor --stop

# 2回目の監視（同じ期間を指定）
jltsql monitor --daemon
# → 再度レコードA, B, C を取得（重複！）
```

**ケース2: データの訂正**
```
元のデータ: レースID=12345, 馬番=1, 騎手="武豊"
訂正後: レースID=12345, 馬番=1, 騎手="M.デムーロ"
```
→ データベースには **両方のレコードが保存されます**（旧レコードは削除されない）

---

### 4. 実装の理由

#### 4.1 なぜUPSERTを使わないのか？

1. **シンプルさ**: INSERTのみの方が実装が単純
2. **履歴保存**: 訂正前後のデータを両方保存できる（監査証跡）
3. **パフォーマンス**: UPSERTは PRIMARY KEY チェックが必要で遅い
4. **JV-Data仕様**: JV-Link APIが差分データを管理するため、アプリ側で重複排除する必要がない（通常の使い方では）

#### 4.2 トレードオフ

| メリット | デメリット |
|---------|-----------|
| ✅ シンプルな実装 | ❌ 重複レコードの可能性 |
| ✅ 高速なINSERT | ❌ ディスク容量の増加 |
| ✅ 履歴保存（訂正前後） | ❌ 最新データの特定が複雑 |
| ✅ PRIMARY KEY不要 | ❌ データ整合性チェックなし |

---

## 推奨される使い方

### 1. リアルタイム監視の正しい運用

```bash
# 1. 初回セットアップ（過去10年のデータ取得）
python scripts/quickstart.py

# 2. リアルタイム監視が自動的に開始される
# → 継続的に新しいデータを追加し続ける

# 3. 監視ステータス確認
jltsql status
```

### 2. 重複レコードを避ける方法

#### 方法1: 監視を止めない
```bash
# ✅ 推奨: 監視を継続
jltsql monitor --daemon  # 一度起動したら止めない

# ❌ 非推奨: 頻繁に再起動
jltsql monitor --stop
jltsql monitor --daemon  # 重複の原因
```

#### 方法2: クエリで最新データのみ抽出

重複がある場合、SQLで最新レコードを取得：

```sql
-- MakeDate（作成日時）が最新のレコードのみ抽出
WITH RankedRecords AS (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY レースID, 馬番  -- 一意性を決めるキー
           ORDER BY MakeDate DESC        -- 最新順
         ) as rn
  FROM NL_SE
)
SELECT * FROM RankedRecords WHERE rn = 1;
```

### 3. 定期的なクリーンアップ

```bash
# 重複レコードを削除するスクリプト（今後実装予定）
# python scripts/deduplicate_records.py
```

---

## JV-Link API の差分管理メカニズム

### JVRTOpenの内部動作

**JV-Link DLL（JVDTLab.dll）** は内部で以下を管理：

1. **最終取得位置**: どこまでデータを取得したかを記録
2. **ファイルタイムスタンプ**: 最後に読んだファイルの時刻
3. **差分検出**: 新しいファイルのみを返す

**コード**: `src/fetcher/realtime.py:116`
```python
# リアルタイムストリームを開く
ret, read_count = self.jvlink.jv_rt_open(data_spec, key)
```

**JV-Link内部の動作**:
```
[1回目の呼び出し]
JVRTOpen("0B12", "")
  → 内部: "最後のファイル = (なし)"
  → 返却: すべての未取得データ

[2回目の呼び出し（1秒後）]
JVRTOpen("0B12", "")
  → 内部: "最後のファイル = 20251116120000.jvd"
  → 返却: 20251116120001.jvd 以降のみ
```

---

## まとめ

### リアルタイム同期の差分データ処理

1. **JV-Link API**: 差分データ（新規・更新）のみを返す
2. **JLTSQL**: 受け取ったデータを **すべてINSERTで追加**
3. **結果**:
   - ✅ 新しいデータは正しく追加される
   - ⚠️ 更新データは新しい行として追加される（旧データは残る）
   - ⚠️ 監視を再起動すると重複する可能性がある

### ベストプラクティス

1. **監視を継続運用**: 一度起動したらなるべく止めない
2. **クエリで最新データ抽出**: `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY MakeDate DESC)`
3. **定期的なクリーンアップ**: 重複レコードを削除（実装予定）

### 今後の改善案

- [ ] PRIMARY KEYの追加（一意性制約）
- [ ] UPSERT（INSERT OR REPLACE）の実装
- [ ] 重複レコード削除スクリプトの提供
- [ ] データ整合性チェック機能

---

## Q&A: 具体的なシナリオ

### Q: 2024年10月までのデータがDBにある。2025年10月にリアルタイム監視を開始したらどうなる？

**A: ギャップ（2024年10月～2025年10月）は埋まりません。**

#### シナリオ詳細

**状況**:
- 現在のDB: 2024年10月までのデータ（NL_テーブル）
- 実行日: 2025年10月
- コマンド: `jltsql monitor --daemon`

**動作**:

```
[2025年10月 監視開始]
│
├─ JVRTOpen("RACE") 呼び出し
│  └─ fromtime パラメータなし → 「今この瞬間以降」のみ監視
│
├─ 過去データ（2024/10～2025/10）は取得されない ← ❌
│
└─ 2025年10月以降の新着データのみを RT_テーブルに追加 ← ✅
```

**結果**:

| 期間 | NL_テーブル（蓄積系） | RT_テーブル（速報系） |
|------|-------------------|------------------|
| ～2024/10 | ✅ データあり | - |
| 2024/11～2025/9 | ❌ **ギャップ（データなし）** | - |
| 2025/10～ | - | ✅ 新着データ |

#### 重要な発見

1. **RT_テーブルとNL_テーブルは別物**
   - NL_テーブル: 蓄積系（`jltsql fetch`で取得）
   - RT_テーブル: 速報系（`jltsql monitor`で取得）
   - 完全に分離されている

2. **リアルタイム監視は時刻指定なし**
   - `JVRTOpen(data_spec)` は fromtime パラメータを受け取らない
   - 「今この瞬間以降」の新着データのみを監視
   - 過去のギャップは埋まらない

3. **UPDATE/DELETE 実装は未完**
   - `headDataKubun="2"`（更新）でも INSERT している
   - 訂正データは新しい行として追加される
   - 旧データは削除されない → 重複の可能性

#### 正しい対処方法

**推奨**: `python scripts/quickstart.py` で両方実行

```bash
# quickstart.py は以下を実行:
# [5/7] 全データ取得
#   → jltsql fetch --from 20151001 --to 20251001
#   → NL_テーブルにギャップを含む全データを格納

# [6/7] リアルタイム監視開始
#   → jltsql monitor --daemon
#   → RT_テーブルに速報データを追加
```

**手動の場合**:

```bash
# ステップ1: ギャップを埋める（蓄積系データ取得）
jltsql fetch --from 20241101 --to 20251001 --spec RACE
# → NL_RA テーブルに格納

# ステップ2: リアルタイム監視開始
jltsql monitor --daemon
# → RT_RA テーブルに格納
```

**クエリ例（NL_とRT_を結合）**:

```sql
-- 全期間のレースデータを取得
SELECT * FROM NL_RA   -- 蓄積系（～2025/10）
WHERE MakeDate <= '20251001'
UNION ALL
SELECT * FROM RT_RA   -- 速報系（2025/10～）
WHERE MakeDate > '20251001'
ORDER BY MakeDate;
```

---

**参考コード**:
- `src/database/base.py:176-200` - INSERT実装
- `src/database/schema.py` - テーブル定義（PRIMARY KEY なし）
- `src/services/realtime_monitor.py:259-320` - リアルタイム監視ループ
- `src/fetcher/realtime.py:146-181` - 連続取得メカニズム
- `src/realtime/monitor.py:98` - JVRTOpen呼び出し（時刻指定なし）
- `src/realtime/updater.py:41-72` - RT_テーブルマッピング
- `src/realtime/updater.py:198-200` - UPDATE未実装（INSERTで代替）
