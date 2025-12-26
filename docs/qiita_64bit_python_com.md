# 64bit Pythonから32bit COM DLL（JV-Link/UmaConn）を使う方法

## はじめに

JRA-VAN の JV-Link や地方競馬DATAの UmaConn（NV-Link）は、競馬データを取得するための COM API を提供しています。しかし、これらは **32bit DLL** として提供されているため、通常は 32bit Python からしか利用できません。

本記事では、**DLL Surrogate** というWindowsの機能を使って、64bit Python から 32bit COM DLL にアクセスする方法を解説します。

## 動作確認環境

- Windows 11
- Python 3.13 (64-bit)
- JV-Link（JRA公式データ）
- UmaConn/NV-Link（地方競馬DATA）

## DLL Surrogate とは

DLL Surrogate は、32bit の COM DLL を別プロセス（dllhost.exe）で動作させ、64bit アプリケーションからアクセスできるようにする Windows の機能です。

```
┌─────────────────┐     ┌──────────────────────┐
│  64-bit Python  │────▶│  dllhost.exe (32-bit)│
│                 │ COM │  ┌──────────────────┐│
│  win32com       │◀────│  │ JV-Link DLL      ││
└─────────────────┘     │  │ NV-Link DLL      ││
                        │  └──────────────────┘│
                        └──────────────────────┘
```

## 必要なレジストリ設定

DLL Surrogate を有効にするには、以下のレジストリキーを設定する必要があります。

### JV-Link (CLSID: {2AB1774D-0C41-11D7-916F-0003479BEB3F})

```reg
Windows Registry Editor Version 5.00

; 64bit側の設定
[HKEY_CLASSES_ROOT\CLSID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}]
"AppID"="{2AB1774D-0C41-11D7-916F-0003479BEB3F}"

[HKEY_CLASSES_ROOT\AppID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}]
"DllSurrogate"=""

; 32bit側の設定（Wow6432Node）
[HKEY_CLASSES_ROOT\Wow6432Node\CLSID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}]
"AppID"="{2AB1774D-0C41-11D7-916F-0003479BEB3F}"

[HKEY_CLASSES_ROOT\Wow6432Node\AppID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}]
"DllSurrogate"=""
```

### NV-Link/UmaConn (CLSID: {F726BBA6-5784-4529-8C67-26E152D49D73})

```reg
Windows Registry Editor Version 5.00

; 64bit側の設定
[HKEY_CLASSES_ROOT\CLSID\{F726BBA6-5784-4529-8C67-26E152D49D73}]
"AppID"="{F726BBA6-5784-4529-8C67-26E152D49D73}"

[HKEY_CLASSES_ROOT\AppID\{F726BBA6-5784-4529-8C67-26E152D49D73}]
"DllSurrogate"=""

; 32bit側の設定（Wow6432Node）
[HKEY_CLASSES_ROOT\Wow6432Node\CLSID\{F726BBA6-5784-4529-8C67-26E152D49D73}]
"AppID"="{F726BBA6-5784-4529-8C67-26E152D49D73}"

[HKEY_CLASSES_ROOT\Wow6432Node\AppID\{F726BBA6-5784-4529-8C67-26E152D49D73}]
"DllSurrogate"=""
```

## NV-Link特有の注意点

NV-Link（UmaConn）のインストーラーは、AppID に `RunAs = "Interactive User"` を設定します。この設定は DLL Surrogate と**競合**するため、削除が必要です。

```reg
; RunAs値を削除（-は削除を意味する）
[HKEY_CLASSES_ROOT\AppID\{F726BBA6-5784-4529-8C67-26E152D49D73}]
"RunAs"=-

[HKEY_CLASSES_ROOT\Wow6432Node\AppID\{F726BBA6-5784-4529-8C67-26E152D49D73}]
"RunAs"=-
```

## 自動設定スクリプト

レジストリ設定を自動で確認・修正するPythonスクリプトを用意しました。

### 使用方法

```bash
# 現在の状態を確認（管理者権限不要）
python check_dll_surrogate.py

# COM接続テストも実行
python check_dll_surrogate.py --test

# 設定を修正（管理者権限必要）
python check_dll_surrogate.py --fix
```

スクリプトは以下のGistからダウンロードできます：
👉 [check_dll_surrogate.py](https://gist.github.com/miyamamoto/d71445a0e992d7e34372fb5cf10c42fe)

## 動作確認

設定後、64bit Python から COM 接続できることを確認します。

```python
import win32com.client
import struct

# アーキテクチャ確認
arch = struct.calcsize("P") * 8
print(f"Python: {arch}-bit")

# JV-Link 接続テスト
try:
    jv = win32com.client.Dispatch("JVDTLab.JVLink")
    print("JV-Link: OK")
except Exception as e:
    print(f"JV-Link: NG - {e}")

# NV-Link 接続テスト
try:
    nv = win32com.client.Dispatch("NVDTLabLib.NVLink")
    rc = nv.NVInit("UNKNOWN")
    print(f"NV-Link: OK (NVInit={rc})")
    nv.NVClose()
except Exception as e:
    print(f"NV-Link: NG - {e}")
```

出力例：
```
Python: 64-bit
JV-Link: OK
NV-Link: OK (NVInit=0)
```

## 64bit Python を使うメリット

1. **DuckDB が使える** - 高速な分析用データベース（64bit専用）
2. **メモリ制限がない** - 32bit の 2GB 制限を超えられる
3. **最新ライブラリ** - 一部のライブラリは 64bit のみ対応

## レジストリ設定の削除

DLL Surrogate 設定を削除して元に戻したい場合は、以下のスクリプトを使用します。

```bash
# 削除プレビュー（dry-run）
python remove_dll_surrogate.py

# 実際に削除（管理者権限必要）
python remove_dll_surrogate.py --force
```

スクリプトは以下のGistからダウンロードできます：
👉 [remove_dll_surrogate.py](https://gist.github.com/miyamamoto/2ce62fdcb64567901ef7ef3b000be039)

### 手動で削除する場合

以下の .reg ファイルを管理者権限で実行します：

```reg
Windows Registry Editor Version 5.00

; JV-Link DLL Surrogate 削除
[HKEY_CLASSES_ROOT\CLSID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}]
"AppID"=-

[HKEY_CLASSES_ROOT\AppID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}]
"DllSurrogate"=-

[HKEY_CLASSES_ROOT\Wow6432Node\CLSID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}]
"AppID"=-

[HKEY_CLASSES_ROOT\Wow6432Node\AppID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}]
"DllSurrogate"=-

; NV-Link DLL Surrogate 削除
[HKEY_CLASSES_ROOT\CLSID\{F726BBA6-5784-4529-8C67-26E152D49D73}]
"AppID"=-

[HKEY_CLASSES_ROOT\AppID\{F726BBA6-5784-4529-8C67-26E152D49D73}]
"DllSurrogate"=-

[HKEY_CLASSES_ROOT\Wow6432Node\CLSID\{F726BBA6-5784-4529-8C67-26E152D49D73}]
"AppID"=-

[HKEY_CLASSES_ROOT\Wow6432Node\AppID\{F726BBA6-5784-4529-8C67-26E152D49D73}]
"DllSurrogate"=-
```

## トラブルシューティング

### エラー: REGDB_E_CLASSNOTREG (-2147221164)

DLL Surrogate 設定が不足しています。`check_dll_surrogate.py --fix` を管理者権限で実行してください。

### エラー: クラス文字列が無効です (-2147221005)

ProgID が間違っている可能性があります。

| コンポーネント | 正しいProgID |
|---------------|-------------|
| JV-Link | `JVDTLab.JVLink` |
| NV-Link | `NVDTLabLib.NVLink` |

**注意**: NV-Link の ProgID は `NVDTLab.NVLink` ではなく `NVDTLabLib.NVLink` です。

### NV-Linkだけ動かない

NV-Link の AppID に `RunAs` 値が設定されていると DLL Surrogate と競合します。`check_dll_surrogate.py --fix` で自動削除されます。

## 参考資料

- [64bitアプリから32bitのCOM DLLを利用する方法](https://note.com/jyon_choko/n/nb5336b4332d0)
- [JRA-VAN Data Lab.](https://jra-van.jp/dlb/)
- [地方競馬DATA](https://www.keiba-data.net/)

## まとめ

DLL Surrogate を使えば、64bit Python から JV-Link や UmaConn を利用できます。これにより、DuckDB などの 64bit 専用ライブラリと組み合わせて、高速なデータ分析が可能になります。

設定は少し複雑ですが、本記事のスクリプトを使えば簡単に設定・削除できます。
