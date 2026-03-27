# 技術詳細

## Python環境

**32-bit Pythonが必須です。**

JV-Link のCOM DLLは32-bitのため、32-bit Pythonから直接呼び出す必要があります。

### なぜ64-bitを採用しないか

DLL Surrogateを設定すれば64-bit Pythonからも利用可能ですが、以下の問題があります：

- `option=3/4`（セットアップモード）がアウトプロセス通信でハングする
- 取得できるデータに差はない（32-bitと同一）
- 追加のレジストリ設定が必要で運用が複雑になる

**32-bitで全機能が利用可能**なため、64-bit対応は不要です。

## トラブルシューティング

### -203 エラー

JV-Linkの -203 エラーはネットワーク接続エラーを意味します。DataLabを再起動して再試行してください。

### COM E_UNEXPECTED

読み取り完了のサイン。正常終了（return code 0）として処理されます。

## パーサー一覧

### JRA (38種)

AV, BN, BR, BT, CC, CH, CK, CS, DM, H1, H6, HC, HN, HR, HS, HY, JC, JG, KS, O1, O2, O3, O4, O5, O6, RA, RC, SE, SK, TC, TK, TM, UM, WC, WE, WF, WH, YS

## データベース

### SQLite

セットアップ不要。デフォルトのデータベース。

### PostgreSQL

pg8000（純Python製ドライバ）を使用。32-bit Python環境でも動作。

```bash
# Docker でセットアップ
docker run -d --name jrvltsql-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15
```
