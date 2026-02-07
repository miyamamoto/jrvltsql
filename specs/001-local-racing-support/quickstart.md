# Quickstart: 地方競馬データ対応

このガイドでは、JRVLTSQLで地方競馬DATA（UmaConn）を使用する方法を説明します。

## 前提条件

1. **地方競馬DATA会員登録**: https://www.keiba-data.com/ で登録
2. **UmaConnインストール**: 地方競馬DATAソフトウェアをインストール
3. **サービスキー設定**: 地方競馬DATA設定ツールでサービスキーを設定

**Note**: UmaConnはJV-Linkと同様のCOM API設計のため、64bit Pythonで動作します。

## 1. 地方競馬データの取得

### 基本的な取得

```bash
# レースデータを取得
jltsql fetch --source nar --spec RACE

# マスタデータ（馬、騎手、調教師等）を取得
jltsql fetch --source nar --spec DIFF

# オッズデータを取得
jltsql fetch --source nar --spec O1
```

### セットアップ（初回取得）

初回は大量データのダウンロードが必要です：

```bash
# セットアップモード（ダイアログ表示あり）
jltsql fetch --source nar --spec RACE --option 3
```

## 2. ステータス確認

```bash
# 地方競馬のみ
jltsql status --source nar

# 中央競馬と地方競馬の両方
jltsql status --source all
```

出力例：
```
=== JRVLTSQL Status ===

[JRA-VAN DataLab]
  状態: 接続可能
  最終更新: 2025-12-15 10:30:00
  テーブル数: 64
  レコード数: 1,234,567

[地方競馬DATA]
  状態: 接続可能
  最終更新: 2025-12-15 10:25:00
  テーブル数: 64
  レコード数: 987,654
```

## 3. リアルタイム監視

```bash
# 地方競馬のリアルタイムオッズを監視
jltsql monitor --source nar
```

## 4. データベースクエリ

### 地方競馬データのみ

```sql
-- 地方競馬のレース一覧
SELECT * FROM NL_RA_NAR WHERE Year = 2024;

-- 大井競馬場のレース
SELECT * FROM NL_RA_NAR WHERE JyoCD = '44';
```

### 中央・地方横断クエリ

```sql
-- 全競馬場のレース（中央+地方）
SELECT * FROM NL_RA
UNION ALL
SELECT * FROM NL_RA_NAR
WHERE Year = 2024;
```

## 5. 競馬場コード

### 中央競馬（01-10）
| コード | 競馬場 |
|--------|--------|
| 01 | 札幌 |
| 02 | 函館 |
| 03 | 福島 |
| 04 | 新潟 |
| 05 | 東京 |
| 06 | 中山 |
| 07 | 中京 |
| 08 | 京都 |
| 09 | 阪神 |
| 10 | 小倉 |

### 地方競馬（30-55）
| コード | 競馬場 |
|--------|--------|
| 30 | 門別 |
| 33 | 帯広 |
| 35 | 盛岡 |
| 36 | 水沢 |
| 42 | 浦和 |
| 43 | 船橋 |
| 44 | 大井 |
| 45 | 川崎 |
| 46 | 金沢 |
| 47 | 笠松 |
| 48 | 名古屋 |
| 50 | 園田 |
| 51 | 姫路 |
| 54 | 高知 |
| 55 | 佐賀 |

## 6. トラブルシューティング

### エラー: UmaConnがインストールされていません

```
エラー: UmaConn (地方競馬DATA) がインストールされていません。
```

**解決策**: 地方競馬DATAのソフトウェアをインストールしてください。

### エラー: サービスキーが設定されていません

```
エラー: 地方競馬DATAのサービスキーが設定されていません。
```

**解決策**: 地方競馬DATA設定ツールでサービスキーを設定してください。

## 7. 既存ユーザー向け

既存のコマンドは従来通り動作します：

```bash
# 以下は同等
jltsql fetch --spec RACE
jltsql fetch --source jra --spec RACE
```

`--source`オプションを省略すると、デフォルトで中央競馬（JRA）が選択されます。
