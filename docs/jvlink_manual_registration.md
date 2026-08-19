# JV-Link を手作業でインストールし利用登録する（Docker/Wine）

JRA-VAN Data Lab の JV-Link は、**インストーラを画面で進め、利用規約に同意し、
サービスキーを入力する**ことを前提に作られている。無人で完了させる公式手段は
無く、本リポジトリも用意しない。ここではコンテナの noVNC デスクトップ上で人が
その操作を行う手順を示す。

一度登録すれば、状態は Wine prefix（`/wineprefix`）の中に残る。prefix を
ホスト側の永続ディレクトリに bind mount しておけば、コンテナを作り直しても
再登録は不要。

## 前提

- x86_64 の Linux ホスト（32-bit の JV-Link を Wine で動かすため。ARM Mac では
  32-bit x86 を実行できず、この構成は使えない）
- JRA-VAN Data Lab の**有効な利用契約とサービスキー**
- ブラウザ（noVNC を開く）

## 1. インストーラを用意する

JRA-VAN の会員ページから Data Lab の JV-Link インストーラを取得する。会員
ログインが必要なので、この入手作業も自動化できない。ホスト側の任意の
ディレクトリに置き、コンテナから読める場所に mount する。

```bash
mkdir -p ./jvlink-installers
# 取得した JVLinkSetup 等をここに置く
```

`docker-compose.yml` に読み取り専用の mount を足す（既定では mount しない）。

```yaml
    volumes:
      - ./wineprefix:/wineprefix
      - ./jvlink-installers:/installers:ro
```

## 2. コンテナを起動する

```bash
docker compose up -d jltsql
docker compose logs jltsql | tail -20
```

起動時に entrypoint が行うのは次の3つだけで、**インストールも登録もしない**。

1. Xvfb・fluxbox・x11vnc・noVNC を起動する
2. `system.reg` が無ければ `wineboot --init` で prefix を作る（`DISPLAY` を
   外して実行する。X 表示があると win64 prefix の 32-bit 側が作られず
   `syswow64` が空になり、32-bit の JV-Link と bridge が動かなくなる）
3. `syswow64/kernel32.dll` の存在を確認する。無ければ理由を出して `exit 1`

JV-Link が未インストールなら「installed by hand on the noVNC desktop」という
案内を出すが、コンテナは起動したままになる。取得は fail closed で失敗する。

## 3. ブラウザで noVNC を開く

Docker を動かしている箱で作業しているなら、そのまま localhost で開く。

```text
http://localhost:6080/vnc.html
```

パスワードは設定していない（`x11vnc -nopw`）。**外部に公開しないこと。**
別の箱（開発サーバ等）でコンテナを動かしているなら、公開せずに SSH ポート
転送を使う。

```bash
ssh -L 6080:localhost:6080 <コンテナを動かしている箱>
# → 手元のブラウザで http://localhost:6080/vnc.html
```

## 4. インストーラを実行する（人の操作）

noVNC の画面で端末が無い構成なので、インストーラの起動だけホスト側から行う。

```bash
docker compose exec jltsql wine /installers/JVLinkSetup.exe
```

以後はブラウザに映った Wine デスクトップ上で、インストーラの画面を**人が**
進める。

## 5. 利用規約に同意し、サービスキーを入力する（人の操作）

JV-Link の設定画面で次を行う。

1. 「ご注意事項」＝利用規約の本文を開き、内容を読む
2. 同意のチェックを入れる
3. サービスキーを入力して保存する

この3つは意思表示なので、自動クリックは実装しない（`AUTO_INSTALL_JVLINK`、
`JVLINK_AUTO_ACCEPT_TERMS`、`AUTO_DISMISS_JVLINK_DIALOGS` に相当する機能は
このリポジトリには無い）。同様に、サービスキーを書き込む API 呼び出しも
提供しない。既存の登録を上書きしてしまう事故を避けるためである。

## 6. 登録できたことを確認する

```bash
docker compose exec jltsql jltsql status
```

`JV-Link transport: 利用可能` は bridge が起動できることしか意味しない。
実際の登録状態は `JVInit` が `0` を返すかどうかで決まる。取得を1本流して
確認する。

```bash
docker compose exec jltsql jltsql fetch \
    --from 20260810 --to 20260817 --spec RACE --option 1
```

## 7. 取得中に出るダイアログは人が押す

**JV-Link は新しいバージョンを見つけると、`JVOpen` の途中で
「現在のバージョンより新しいバージョン(x.y.z)の JV-Link が存在します。
ダウンロードしますか？」というダイアログを出して、押されるまで戻ってこない。**
実測では `JVOpen` が 1,008 秒ブロックし、noVNC で「いいえ」を押した直後に
`0`（48ファイル）を返した。

つまり、この構成では**取得の途中でも画面を見る必要がある**。

- 更新しないなら「いいえ」。JV-Link の版はそのまま
- 更新するなら「はい」。インストーラが動くので、以後の画面も人が進める
- 「今後表示しない」を付けるかどうかも運用判断（prefix に設定が残る）

既定ではこのダイアログに対して何も押さない。無人運転したい場合は、この確認を
人が済ませた prefix を使い、`JVOpen` に十分な `JVLINK_OPEN_TIMEOUT_SECONDS` を
与えること。それでも無人で流したい場合に限り `JVLINK_AUTO_CLOSE_DIALOGS=1` を
明示すると、既知のダイアログだけを Escape で**拒否**する（更新や規約を承諾する
入力は送らない。未知のダイアログには触らない）。既定 `0` のままなら、提供元の
問いかけは必ず人に届く。

## トラブルシューティング

| 症状 | 原因 | 対処 |
| --- | --- | --- |
| entrypoint が `has no 32-bit support` で `exit 1` | prefix の `syswow64` に `kernel32.dll` が無い | prefix を作り直す（`DISPLAY` 無しで `wineboot --init`） |
| bridge が `CoCreateInstance failed (0x80040154)` | JV-Link が未インストール | 手順4・5を実施する |
| `JVInit` が `-301`/`-302`/`-303` | 認証・契約・キー未設定 | JRA-VAN の契約とサービスキーを確認する |
| `JVOpen` が返らない | 版更新ダイアログ待ち | noVNC で応答する（手順7） |
| `wine: '/wineprefix' is not owned by you` | prefix の所有者と実行 uid が違う | prefix の所有 uid でコンテナを実行する（entrypoint は mount の uid に合わせる） |
