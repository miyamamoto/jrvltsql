# Wine / Docker で JV-Link を動かす

JV-Link は 32-bit の Windows COM コンポーネントなので、公式の実行環境は Windows
である。Linux で動かす場合は Wine 上の 32-bit プロセスから COM を呼ぶ必要があり、
本リポジトリはそのための最小構成（Docker イメージ・ネイティブ bridge・
起動スクリプト）を同梱している。

利用登録は人が行う。手順は
[JV-Link を手作業でインストールし利用登録する](jvlink_manual_registration.md)。

## 構成

```text
tools/jvlink-bridge/bridge_native.c   32-bit Windows 実行体。JV-Link の COM を呼び
                                      1行1メッセージの JSON で stdin/stdout を話す
scripts/build_jvlink_bridge_native.sh mingw-w64 でその実行体をビルドする
Dockerfile                            上記を multi-stage でビルドし、Wine と
                                      Xvfb/noVNC を含む実行イメージを作る
scripts/docker-entrypoint.sh          表示を用意し、prefix を初期化し、32-bit
                                      対応を検証してから CMD を exec する
docker-compose.yml                    prefix を永続 mount した起動例
```

Python 側は `src/jvlink/bridge.py` がこの実行体を子プロセスとして起動する。
Windows では直接起動し、それ以外のホストでは `JVLINK_BRIDGE_RUNNER` に指定された
外部ランナー（Docker イメージでは `wine`）経由で起動する。ランナーを推測は
しない。指定が無ければ理由を述べて失敗する。

## 環境変数

| 変数 | 既定 | 意味 |
| --- | --- | --- |
| `JVLINK_BRIDGE_EXE` | イメージ内の絶対パス | bridge 実行体 |
| `JVLINK_BRIDGE_RUNNER` | `wine`（イメージ） | 非 Windows での外部ランナー |
| `JVLINK_WINEPREFIX` | `/wineprefix` | JV-Link を含む Wine prefix |
| `JVLINK_WINEARCH` | `win64` | prefix の種別（32-bit 側が必須） |
| `JVLINK_OPEN_TIMEOUT_SECONDS` | `120` | `JVOpen` 応答待ちの上限秒（1〜7200） |

サービスキーを設定する環境変数は持たない。登録は noVNC 上で人が行う。

## 32-bit を壊さないこと

`WINEARCH=win64` の prefix は 64-bit と 32-bit の両方を含む。`wineboot --init` に
X 表示が見えていると 32-bit 側の生成に失敗し、`drive_c/windows/syswow64` が
実質空（実測 846 ファイル → 1 ファイル）になる。この状態でも Wine 自体は動くため
気づきにくく、32-bit の bridge は応答も stderr も返さずに固まる。

そのため entrypoint は、prefix を作るときだけ `DISPLAY` を外して `wineboot` を
実行し、その後 `syswow64/kernel32.dll` の存在を確認して、無ければ理由を出して
`exit 1` する。fail closed にしないと、収集プロセスは起動成功として振る舞い、
失敗は取得時の不透明なタイムアウトとしてしか現れない。

## プロセスの回収

Wine は `wineserver`・`winedevice.exe`・JV-Link 自身のエージェントなど複数の
子プロセスを残す。PID 1 がそれらを回収しないとゾンビが溜まり続けるので、
イメージは `tini` を PID 1 として使う（実測: 無しで bridge 起動ごとに 12 個の
ゾンビが残り、`tini` 導入後は 1 個で安定）。

## ARM（Apple Silicon）では動かない

JV-Link と bridge は 32-bit x86 バイナリで、Rosetta 2 は x86_64 のみを扱う。
ARM ホストで 32-bit x86 を Wine 経由で実行する経路は無いので、x86_64 の
ホストを使うこと。
