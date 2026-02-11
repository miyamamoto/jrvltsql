#!/usr/bin/env python3
"""NV-Link バックグラウンドダウンローダー
open→即close→再openサイクルでDL。statusポーリングを排除し、ブロックを回避。
-421エラー時は同一接続でsleep→リトライ。接続断の場合のみ再接続。
"""
import socket, json, time, sys, os, datetime

LOG_FILE = os.path.join(os.path.expanduser("~"), "work", "nv_dl_background.log")
RECV_TIMEOUT = 60  # recv応答待ちタイムアウト(秒)

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def recv_line(sock):
    buf = b""
    while b"\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("closed")
        buf += chunk
    return json.loads(buf.decode())

def send_cmd(sock, cmd):
    sock.settimeout(RECV_TIMEOUT)
    try:
        sock.sendall(json.dumps(cmd).encode() + b"\n")
        return recv_line(sock)
    except socket.timeout:
        raise ConnectionError(f"send_cmd timeout ({RECV_TIMEOUT}s) for {cmd.get('cmd', '?')}")

def connect_bridge():
    s = socket.socket()
    s.settimeout(RECV_TIMEOUT)
    s.connect(("127.0.0.1", 8901))
    g = recv_line(s)
    log(f"Connected: v{g.get('version')} ({g.get('backend')})")
    r = send_cmd(s, {"cmd": "init", "sid": "UNKNOWN"})
    log(f"Init: code={r.get('initResult')}")
    return s

def do_download_cycle(sock):
    """1回のDLサイクル: open→即close。statusチェックなし。
    Returns: (dl_remaining, error_code)
    """
    r = send_cmd(sock, {"cmd": "open", "dataspec": "RACE", "date_from": "20200101000000", "option": 2})
    code = r.get("code", -999)
    rc = r.get("readcount", 0)
    dl = r.get("downloadcount", 0)
    log(f"Open: code={code} rc={rc} dl={dl}")

    if code < 0 and code != -1:
        log(f"Open error: {code}")
        try:
            send_cmd(sock, {"cmd": "close"})
        except Exception:
            pass
        return max(dl, 9999), code

    if dl == 0:
        log("DL完了! 全データローカルにあり")
        r = send_cmd(sock, {"cmd": "read"})
        read_code = r.get("code", -999)
        log(f"Read test: code={read_code}")
        send_cmd(sock, {"cmd": "close"})
        return 0, 0

    # DLがある場合: 即closeして次サイクルへ
    log(f"DL残: {dl}ファイル, 即close")
    send_cmd(sock, {"cmd": "close"})
    return dl, 0

def main():
    log("=" * 50)
    log("NV-Link バックグラウンドDL開始 (v3: same-conn retry)")
    log("=" * 50)

    max_cycles = 500
    consecutive_errors = 0
    max_consecutive_errors = 10
    total_cycles = 0
    wait_sec = 10

    sock = connect_bridge()

    for cycle in range(max_cycles):
        total_cycles = cycle + 1
        log(f"\n--- サイクル {total_cycles} ---")

        try:
            dl, error_code = do_download_cycle(sock)
        except (ConnectionError, socket.error, json.JSONDecodeError) as e:
            log(f"接続エラー: {e}")
            try:
                sock.close()
            except Exception:
                pass
            consecutive_errors += 1
            if consecutive_errors >= max_consecutive_errors:
                log("連続エラー上限到達、終了")
                break
            log(f"30秒待機後に再接続... (連続エラー: {consecutive_errors})")
            time.sleep(30)
            try:
                sock = connect_bridge()
            except Exception as e2:
                log(f"再接続失敗: {e2}")
                time.sleep(60)
                try:
                    sock = connect_bridge()
                except Exception:
                    log("再接続2回目も失敗、終了")
                    break
            continue

        if error_code != 0 and dl == 0:
            dl = 9999

        if error_code == 0 and dl == 0:
            log("全ファイルDL完了!")
            break

        if error_code == 0:
            consecutive_errors = 0
            log(f"残りDL: {dl}ファイル, {wait_sec}秒後に次サイクル")
            time.sleep(wait_sec)
        elif error_code == -502:
            # DL失敗、同一接続で30秒後リトライ
            consecutive_errors = 0
            log(f"残りDL: {dl}ファイル, -502 DL失敗, 30秒後リトライ")
            time.sleep(30)
        elif error_code == -421:
            # サーバーエラー、同一接続で3分後リトライ
            consecutive_errors += 1
            log(f"-421サーバーエラー, 3分待機後リトライ (連続エラー: {consecutive_errors})")
            time.sleep(180)
        else:
            consecutive_errors += 1
            log(f"エラー code={error_code}, 60秒待機 (連続エラー: {consecutive_errors})")
            time.sleep(60)

        if consecutive_errors >= max_consecutive_errors:
            log("連続エラー上限到達、終了")
            break

    log(f"\n完了: {total_cycles}サイクル実行")
    try:
        send_cmd(sock, {"cmd": "quit"})
        sock.close()
    except Exception:
        pass
    log("=== バックグラウンドDL終了 ===")

if __name__ == "__main__":
    main()
