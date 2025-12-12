# 変更履歴

JRVLTSQLのバージョン履歴です。

## v2.2.0 (2024-12-12)

### 新機能

- **JVGetsメソッド追加**: JV-Link APIの高速読み取りに対応

### パフォーマンス改善

- **スキーマ型定義を全面的に最適化**（TEXT→INTEGER/BIGINT/REAL）
  - Year, MonthDay, Kaiji, Nichiji, RaceNum → INTEGER
  - 各種賞金フィールド → BIGINT
  - オッズ、タイムフィールド → REAL
- INTEGER型によるインデックス効率の向上
- PRIMARY KEY検証の高速化

### バグ修正

- DuckDB型変換エラーを修正（無効な値のクレンジング追加）
- SQLクエリのMonthDay型エラーを修正
- セットアップモードの所要時間見積もりを修正
- option=4非対応スペック(COMM,PARA等)のエラー修正
- 進捗表示の更新頻度を4Hzに増加
- NL_HRスキーマにHenkanDoWaku5-8カラムを追加
- DuckDBハンドラーの識別子クォートとUPSERT対応

### ドキュメント

- API.mdのMonthDay型を更新
- DUPLICATE_HANDLING.mdのCREATE TABLE例を更新

### その他

- DuckDBを標準依存関係に変更（オプションから昇格）
- 全64テーブルのメタデータを完備

## v2.1.0 (2024-11)

### 新機能

- DuckDBサポートを追加
- PostgreSQLサポートを追加
- マルチデータベース対応

### 改善

- バッチ処理の効率化
- エラーハンドリングの強化

## v2.0.0 (2024-10)

### 破壊的変更

- 設定ファイル形式をYAMLに変更
- CLI引数の整理

### 新機能

- リアルタイムモニタリング機能
- データエクスポート機能
- 進捗表示の改善

### 改善

- パーサーの高速化
- メモリ使用量の最適化

## v1.0.0 (2024-09)

### 初回リリース

- JV-Link連携機能
- 38種のパーサー実装
- SQLiteサポート
- 蓄積データ取得（fetch）
- 基本的なCLI

## アップグレード方法

### v2.1.x → v2.2.0

```bash
pip install --upgrade jrvltsql
```

DuckDBが標準でインストールされるようになりました。

### v1.x → v2.x

設定ファイルの形式が変更されています。

```bash
# 古い設定をバックアップ
cp config.ini config.ini.bak

# 新しい設定を生成
jltsql init
```

## 将来の計画

- [ ] Web UI追加
- [ ] REST API追加
- [ ] より詳細な統計機能
- [ ] クラウドストレージ連携
