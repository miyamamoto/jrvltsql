#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""JLTSQL バックグラウンド更新サービス

蓄積系データの定期更新と速報系データのリアルタイム監視を行います。

機能:
1. 蓄積系データ定期更新 (JVOpen option=2) - 差分データを定期取得
2. 速報系データ監視 (JVRTOpen) - 開催日はレース時刻に応じて高頻度更新
3. HTTP API - 外部サービスからの強制更新トリガー

更新スケジュール:
- 開催日・レース30分前〜発走: 30秒毎
- 開催日・レース1時間前〜30分前: 1分毎
- 開催日・発売中〜1時間前: 5分毎
- 開催日・レース後: 10分毎（払戻確認まで）
- 非開催日: 速報系更新なし、蓄積系は60分毎

HTTP API (デフォルト: http://localhost:8765):
- GET /trigger              - 全データ強制更新
- GET /trigger/historical   - 蓄積系のみ強制更新
- GET /trigger/realtime     - 速報系のみ強制更新
- GET /status               - 現在の状態取得

使用例:
    python scripts/background_updater.py
    python scripts/background_updater.py --interval 60
    python scripts/background_updater.py --api-port 9000
    python scripts/background_updater.py --no-api
"""

import argparse
import io
import json
import os
import signal
import socketserver
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import List, Optional, Tuple

# Windows cp932対策
if sys.platform == "win32" and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ログ設定: コンソールにはERROR以上のみ表示、それ以外はファイルに出力
from src.utils.logger import setup_logging, get_logger
from src.utils.lock_manager import ProcessLock, ProcessLockError
setup_logging(level="DEBUG", console_level="ERROR", log_to_file=True, log_to_console=True)

logger = get_logger(__name__)


def send_trigger(mode: str = "all") -> bool:
    """強制更新トリガーを送信

    Args:
        mode: "all", "historical", or "realtime"

    Returns:
        bool: 成功したかどうか
    """
    trigger_path = project_root / "data" / "trigger_update"

    # dataディレクトリが存在しない場合は作成
    trigger_path.parent.mkdir(parents=True, exist_ok=True)

    # トリガーファイルを作成
    trigger_path.write_text(mode)

    print(f"強制更新トリガーを送信しました (mode={mode})")
    print(f"トリガーファイル: {trigger_path}")
    return True


class TriggerAPIHandler(BaseHTTPRequestHandler):
    """HTTP APIリクエストハンドラ"""

    # サーバーへの参照（サーバー起動時に設定）
    updater = None
    rate_limiter: Optional["RateLimiter"] = None  # 前方参照

    def log_message(self, format, *args):
        """アクセスログを抑制（必要に応じてloggerに出力）"""
        logger.debug(f"API request: {args[0]}")

    def _send_json_response(self, status_code: int, data: dict):
        """JSONレスポンスを送信"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        response = json.dumps(data, ensure_ascii=False, default=str)
        self.wfile.write(response.encode("utf-8"))

    def do_OPTIONS(self):
        """CORSプリフライトリクエストに対応"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """GETリクエストを処理"""
        path = self.path.rstrip("/")

        if path == "" or path == "/":
            # ルート: ヘルプ
            self._send_json_response(200, {
                "service": "JLTSQL Background Updater API",
                "endpoints": {
                    "/trigger": "全データ強制更新 (all)",
                    "/trigger/all": "全データ強制更新",
                    "/trigger/historical": "蓄積系のみ強制更新",
                    "/trigger/realtime": "速報系のみ強制更新",
                    "/status": "現在の状態取得",
                }
            })

        elif path == "/trigger" or path == "/trigger/all":
            self._handle_trigger("all")

        elif path == "/trigger/historical":
            self._handle_trigger("historical")

        elif path == "/trigger/realtime":
            self._handle_trigger("realtime")

        elif path == "/status":
            self._handle_status()

        else:
            self._send_json_response(404, {
                "error": "Not Found",
                "message": f"Unknown endpoint: {path}"
            })

    def do_POST(self):
        """POSTリクエストを処理（GETと同じ）"""
        self.do_GET()

    def _handle_trigger(self, mode: str):
        """トリガーリクエストを処理"""
        if not self.updater:
            self._send_json_response(503, {
                "error": "Service Unavailable",
                "message": "Updater not initialized"
            })
            return

        # レート制限チェック
        if self.rate_limiter:
            allowed, error_msg = self.rate_limiter.is_allowed()
            if not allowed:
                retry_after = max(1, int((self.rate_limiter._timestamps[0] + self.rate_limiter.short_term_window - time.time()) if self.rate_limiter._timestamps else 0))
                limits_info = {
                    "short_term": {
                        "limit": self.rate_limiter.short_term_limit,
                        "window": self.rate_limiter.short_term_window,
                        "remaining": max(0, self.rate_limiter.short_term_limit - sum(
                            1 for ts in self.rate_limiter._timestamps
                            if time.time() - ts <= self.rate_limiter.short_term_window
                        ))
                    },
                    "long_term": {
                        "limit": self.rate_limiter.long_term_limit,
                        "window": self.rate_limiter.long_term_window,
                        "remaining": max(0, self.rate_limiter.long_term_limit - sum(
                            1 for ts in self.rate_limiter._timestamps
                            if time.time() - ts <= self.rate_limiter.long_term_window
                        ))
                    }
                }
                self._send_json_response(429, {
                    "error": "Too Many Requests",
                    "message": error_msg,
                    "retry_after": retry_after,
                    "limits": limits_info
                })
                logger.warning(f"Rate limit exceeded: {error_msg}")
                return

            # 許可された場合、呼び出しを記録
            self.rate_limiter.record_call()

        # トリガーファイルを作成
        success = send_trigger(mode)

        if success:
            now = datetime.now()
            print(f"[{now.strftime('%H:%M:%S')}] API: 強制更新トリガー受信 ({mode})")
            logger.info(f"API trigger received: {mode}")

            self._send_json_response(200, {
                "success": True,
                "message": f"Trigger sent: {mode}",
                "mode": mode,
                "timestamp": now.isoformat()
            })
        else:
            self._send_json_response(500, {
                "success": False,
                "error": "Failed to send trigger"
            })

    def _handle_status(self):
        """ステータスリクエストを処理"""
        if not self.updater:
            self._send_json_response(503, {
                "error": "Service Unavailable",
                "message": "Updater not initialized"
            })
            return

        updater = self.updater
        schedule = updater.schedule_manager

        # 次のレース情報
        next_race = schedule.get_next_race()
        next_race_info = None
        if next_race:
            next_race_info = {
                "venue": next_race["jyo_name"],
                "race_number": next_race["race_num"],
                "time": next_race["time_str"],
                "minutes_until": int((next_race["race_time"] - datetime.now()).total_seconds() // 60)
            }

        # 更新間隔
        interval, reason = schedule.get_update_interval()

        # レート制限情報
        rate_limit_status = None
        if self.rate_limiter:
            rate_limit_status = self.rate_limiter.get_status()

        response_data = {
            "running": updater._running,
            "started_at": updater._stats["started_at"],
            "is_race_day": schedule.is_race_day(),
            "races_today": len(schedule._today_races),
            "next_race": next_race_info,
            "update_interval_seconds": interval,
            "update_reason": reason,
            "statistics": {
                "historical_updates": updater._stats["historical_updates"],
                "historical_errors": updater._stats["historical_errors"],
                "realtime_updates": updater._stats["realtime_updates"],
                "realtime_errors": updater._stats["realtime_errors"],
                "forced_updates": updater._stats["forced_updates"],
                "last_historical_update": updater._stats["last_historical_update"],
                "last_realtime_update": updater._stats["last_realtime_update"],
            }
        }

        if rate_limit_status:
            response_data["rate_limit"] = rate_limit_status

        self._send_json_response(200, response_data)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """スレッド対応HTTPサーバー"""
    allow_reuse_address = True
    daemon_threads = True


class RateLimiter:
    """APIレート制限クラス

    短期的（バースト）と長期的な呼び出し制限を管理します。
    スライディングウィンドウ方式で実装され、スレッドセーフです。
    """

    def __init__(
        self,
        short_term_limit: int = 5,      # 短期: 最大呼び出し回数
        short_term_window: int = 60,     # 短期: ウィンドウ（秒）
        long_term_limit: int = 30,       # 長期: 最大呼び出し回数
        long_term_window: int = 3600,    # 長期: ウィンドウ（秒）
    ):
        """初期化

        Args:
            short_term_limit: 短期間の最大呼び出し回数
            short_term_window: 短期間のウィンドウサイズ（秒）
            long_term_limit: 長期間の最大呼び出し回数
            long_term_window: 長期間のウィンドウサイズ（秒）
        """
        self.short_term_limit = short_term_limit
        self.short_term_window = short_term_window
        self.long_term_limit = long_term_limit
        self.long_term_window = long_term_window

        self._timestamps: List[float] = []  # 呼び出しタイムスタンプ
        self._lock = threading.Lock()

    def is_allowed(self) -> Tuple[bool, Optional[str]]:
        """呼び出しが許可されるかチェック

        タイムスタンプは記録せず、チェックのみを行います。
        許可される場合は、別途record_call()を呼び出してください。

        Returns:
            Tuple[bool, Optional[str]]: (許可されるか, エラーメッセージ)
                許可される場合: (True, None)
                拒否される場合: (False, エラーメッセージ)
        """
        with self._lock:
            now = time.time()

            # 古いタイムスタンプを削除
            self._cleanup_old_timestamps(now)

            # 短期制限チェック（1分以内）
            short_term_count = sum(
                1 for ts in self._timestamps
                if now - ts <= self.short_term_window
            )

            if short_term_count >= self.short_term_limit:
                return (
                    False,
                    f"Rate limit exceeded: max {self.short_term_limit} requests per minute"
                )

            # 長期制限チェック（1時間以内）
            long_term_count = sum(
                1 for ts in self._timestamps
                if now - ts <= self.long_term_window
            )

            if long_term_count >= self.long_term_limit:
                return (
                    False,
                    f"Rate limit exceeded: max {self.long_term_limit} requests per hour"
                )

            return (True, None)

    def record_call(self):
        """呼び出しを記録

        is_allowed()でチェックが通った後に呼び出してください。
        """
        with self._lock:
            now = time.time()
            self._timestamps.append(now)
            self._cleanup_old_timestamps(now)

    def get_status(self) -> dict:
        """現在のレート制限状態を取得

        Returns:
            dict: レート制限の状態情報
                - short_term_remaining: 短期間の残り回数
                - short_term_reset_in: 短期リセットまでの秒数
                - long_term_remaining: 長期間の残り回数
                - long_term_reset_in: 長期リセットまでの秒数
                - total_calls: 記録された総呼び出し数
        """
        with self._lock:
            now = time.time()
            self._cleanup_old_timestamps(now)

            # 短期ウィンドウ内の呼び出し
            short_term_timestamps = [
                ts for ts in self._timestamps
                if now - ts <= self.short_term_window
            ]
            short_term_count = len(short_term_timestamps)
            short_term_remaining = max(0, self.short_term_limit - short_term_count)

            # 短期リセットまでの時間（最も古いタイムスタンプ基準）
            if short_term_timestamps:
                oldest_short = min(short_term_timestamps)
                short_term_reset_in = int(self.short_term_window - (now - oldest_short))
            else:
                short_term_reset_in = 0

            # 長期ウィンドウ内の呼び出し
            long_term_timestamps = [
                ts for ts in self._timestamps
                if now - ts <= self.long_term_window
            ]
            long_term_count = len(long_term_timestamps)
            long_term_remaining = max(0, self.long_term_limit - long_term_count)

            # 長期リセットまでの時間（最も古いタイムスタンプ基準）
            if long_term_timestamps:
                oldest_long = min(long_term_timestamps)
                long_term_reset_in = int(self.long_term_window - (now - oldest_long))
            else:
                long_term_reset_in = 0

            return {
                "short_term_remaining": short_term_remaining,
                "short_term_reset_in": short_term_reset_in,
                "long_term_remaining": long_term_remaining,
                "long_term_reset_in": long_term_reset_in,
                "total_calls": len(self._timestamps),
            }

    def _cleanup_old_timestamps(self, now: float = None):
        """古いタイムスタンプを削除

        長期ウィンドウを超えたタイムスタンプを削除します。

        Args:
            now: 現在時刻（省略時はtime.time()）
        """
        if now is None:
            now = time.time()

        # 長期ウィンドウを超えたタイムスタンプを削除
        cutoff = now - self.long_term_window
        self._timestamps = [ts for ts in self._timestamps if ts > cutoff]


class TriggerAPIServer:
    """HTTP APIサーバー管理クラス"""

    def __init__(
        self,
        updater: "BackgroundUpdater",
        port: int = 8765,
        enable_rate_limit: bool = True,
        rate_limit_short_term: int = 5,
        rate_limit_long_term: int = 30
    ):
        """初期化

        Args:
            updater: BackgroundUpdaterインスタンス
            port: リッスンポート
            enable_rate_limit: レート制限を有効にするか
            rate_limit_short_term: 短期制限（回/分）
            rate_limit_long_term: 長期制限（回/時）
        """
        self.updater = updater
        self.port = port
        self.enable_rate_limit = enable_rate_limit
        self.rate_limit_short_term = rate_limit_short_term
        self.rate_limit_long_term = rate_limit_long_term
        self.server: Optional[ThreadedHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.rate_limiter: Optional[RateLimiter] = None

        # レート制限を作成
        if enable_rate_limit:
            self.rate_limiter = RateLimiter(
                short_term_limit=rate_limit_short_term,
                short_term_window=60,
                long_term_limit=rate_limit_long_term,
                long_term_window=3600
            )

    def start(self) -> bool:
        """サーバーを開始

        Returns:
            bool: 起動成功したかどうか
        """
        try:
            # ハンドラにupdaterとrate_limiterを設定
            TriggerAPIHandler.updater = self.updater
            TriggerAPIHandler.rate_limiter = self.rate_limiter

            # サーバー作成
            self.server = ThreadedHTTPServer(("0.0.0.0", self.port), TriggerAPIHandler)

            # 別スレッドで起動
            self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self._thread.start()

            logger.info(f"API server started on port {self.port}")
            return True

        except OSError as e:
            if e.errno == 10048 or "Address already in use" in str(e):
                logger.error(f"Port {self.port} is already in use")
                print(f"  [警告] ポート {self.port} は使用中です。APIサーバーは起動しませんでした。")
            else:
                logger.error(f"Failed to start API server: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            return False

    def stop(self):
        """サーバーを停止"""
        if self.server:
            self.server.shutdown()
            self.server = None
            logger.info("API server stopped")


class RaceScheduleManager:
    """レーススケジュール管理クラス"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._today_races: List[dict] = []
        self._today_race_count: int = 0  # 発走時刻不明含む全レース数
        self._last_schedule_update: Optional[datetime] = None

    def update_schedule(self) -> bool:
        """本日のレーススケジュールを更新"""
        try:
            if not self.db_path.exists():
                logger.warning(f"Database not found: {self.db_path}")
                return False

            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            today = datetime.now().strftime("%Y%m%d")

            # NL_RAテーブルから本日のレース情報を取得
            # Year + MonthDay でフィルタ、HassoTimeで発走時刻を取得
            cursor.execute("""
                SELECT
                    Year, MonthDay, JyoCD, RaceNum, HassoTime,
                    CASE
                        WHEN JyoCD = '01' THEN '札幌'
                        WHEN JyoCD = '02' THEN '函館'
                        WHEN JyoCD = '03' THEN '福島'
                        WHEN JyoCD = '04' THEN '新潟'
                        WHEN JyoCD = '05' THEN '東京'
                        WHEN JyoCD = '06' THEN '中山'
                        WHEN JyoCD = '07' THEN '中京'
                        WHEN JyoCD = '08' THEN '京都'
                        WHEN JyoCD = '09' THEN '阪神'
                        WHEN JyoCD = '10' THEN '小倉'
                        ELSE JyoCD
                    END as JyoName
                FROM NL_RA
                WHERE Year || MonthDay = ?
                ORDER BY HassoTime
            """, (today,))

            rows = cursor.fetchall()
            conn.close()

            self._today_race_count = len(rows)  # 全レース数（発走時刻不明含む）
            self._today_races = []
            for row in rows:
                try:
                    # HassoTime: HHMM形式
                    time_str = row['HassoTime'] or ''
                    if len(time_str) >= 4:
                        hour = int(time_str[:2])
                        minute = int(time_str[2:4])
                        race_time = datetime.now().replace(
                            hour=hour, minute=minute, second=0, microsecond=0
                        )
                    else:
                        continue

                    self._today_races.append({
                        'jyo_cd': row['JyoCD'],
                        'jyo_name': row['JyoName'],
                        'race_num': row['RaceNum'],
                        'race_time': race_time,
                        'time_str': time_str,
                    })
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to parse race time: {e}")
                    continue

            self._last_schedule_update = datetime.now()
            logger.info(f"Updated race schedule: {len(self._today_races)} races today")
            return True

        except Exception as e:
            logger.error(f"Failed to update race schedule: {e}")
            return False

    def is_race_day(self) -> bool:
        """本日が開催日かどうか"""
        if self._last_schedule_update is None:
            self.update_schedule()
        return self._today_race_count > 0

    def get_next_race(self) -> Optional[dict]:
        """次のレースを取得"""
        now = datetime.now()
        for race in self._today_races:
            if race['race_time'] > now:
                return race
        return None

    def get_current_race(self) -> Optional[dict]:
        """現在進行中または直近のレースを取得"""
        now = datetime.now()
        current = None
        for race in self._today_races:
            # レース後30分以内なら「進行中」とみなす
            if race['race_time'] <= now <= race['race_time'] + timedelta(minutes=30):
                return race
            if race['race_time'] <= now:
                current = race
        return current

    def get_update_interval(self) -> Tuple[int, str]:
        """現在の状況に応じた更新間隔（秒）と理由を返す"""
        if not self.is_race_day():
            return (0, "非開催日")  # 0 = 速報系更新なし

        now = datetime.now()
        next_race = self.get_next_race()
        current_race = self.get_current_race()

        # 次のレースまでの時間を計算
        if next_race:
            time_to_race = (next_race['race_time'] - now).total_seconds()
            race_info = f"{next_race['jyo_name']}{next_race['race_num']}R"

            if time_to_race <= 30 * 60:  # 30分以内
                return (30, f"レース30分前 ({race_info} {next_race['time_str']})")
            elif time_to_race <= 60 * 60:  # 1時間以内
                return (60, f"レース1時間前 ({race_info})")
            else:
                return (300, f"発売中 ({race_info})")

        # 次のレースがない場合（全レース終了後）
        if current_race:
            time_since_race = (now - current_race['race_time']).total_seconds()
            if time_since_race <= 30 * 60:  # レース後30分以内
                return (60, f"レース後 ({current_race['jyo_name']}{current_race['race_num']}R)")
            else:
                return (600, "払戻確認中")

        return (600, "開催終了待ち")

    def get_status_display(self) -> str:
        """現在の状態を表示用文字列で返す"""
        if not self.is_race_day():
            return "非開催日"

        interval, reason = self.get_update_interval()
        next_race = self.get_next_race()

        if next_race:
            now = datetime.now()
            time_to_race = next_race['race_time'] - now
            minutes = int(time_to_race.total_seconds() // 60)
            if minutes > 0:
                return f"{next_race['jyo_name']}{next_race['race_num']}R まで {minutes}分"

        return reason


class BackgroundUpdater:
    """バックグラウンド更新サービス"""

    # 蓄積系の更新対象スペック（option=2で差分更新）
    # 注意: Option 2（今週データ）はRACE, TOKU, TCVN, RCVNのみ対応
    # DIFF, BLOD, YSCH, SNAPはOption 1（通常データ）でのみ取得可能
    HISTORICAL_SPECS = [
        ("RACE", "レース情報"),
        ("TOKU", "特別登録馬"),
    ]

    # 速報系の更新対象スペック (JVRTOpen)
    # 表5.1-1 D行: 速報系データ-速報系データ (→速報系テーブル群)
    #   0B11: 開催情報 (WE)
    #   0B12: レース情報 (RA, SE)
    #   0B15: 払戻情報 (HR)
    #   0B16: 馬体重 (WH)
    # 表5.1-1 E行: 速報系データ-時系列データ (→蓄積系テーブル群)
    #   0B31: 複勝・枠連オッズ (O1, O2)
    #   0B32: 馬連オッズ (O3)
    #   0B33: ワイドオッズ (O4)
    REALTIME_SPECS = [
        # 速報系データ（日付単位キー）
        ("0B11", "開催情報"),
        ("0B12", "レース情報"),
        ("0B15", "払戻情報"),
        ("0B16", "馬体重"),
        # 時系列データ（レース単位キー）
        ("0B31", "複勝・枠連オッズ"),
        ("0B32", "馬連オッズ"),
        ("0B33", "ワイドオッズ"),
    ]

    def __init__(
        self,
        update_historical: bool = True,
        monitor_realtime: bool = True,
        historical_interval_minutes: int = 30,
        enable_api: bool = True,
        api_port: int = 8765,
        enable_rate_limit: bool = True,
        rate_limit_short_term: int = 5,
        rate_limit_long_term: int = 30,
    ):
        """初期化

        Args:
            update_historical: 蓄積系データを定期更新するか
            monitor_realtime: 速報系データを監視するか
            historical_interval_minutes: 蓄積系更新の間隔（分）
            enable_api: HTTP APIサーバーを有効にするか
            api_port: APIサーバーのポート番号
            enable_rate_limit: レート制限を有効にするか
            rate_limit_short_term: 短期制限（回/分）
            rate_limit_long_term: 長期制限（回/時）
        """
        self.update_historical = update_historical
        self.monitor_realtime = monitor_realtime
        self.historical_interval_minutes = historical_interval_minutes
        self.enable_api = enable_api
        self.api_port = api_port
        self.enable_rate_limit = enable_rate_limit
        self.rate_limit_short_term = rate_limit_short_term
        self.rate_limit_long_term = rate_limit_long_term
        self.project_root = project_root

        # データベースパス
        self.db_path = self.project_root / "data" / "keiba.db"

        # レーススケジュール管理
        self.schedule_manager = RaceScheduleManager(self.db_path)

        # APIサーバー
        self._api_server: Optional[TriggerAPIServer] = None

        self._running = False
        self._stop_event = threading.Event()
        self._threads = []

        # JV-Link排他制御（蓄積系と速報系の同時実行を防止）
        self._jvlink_lock = threading.Lock()

        # 更新中フラグ（多重起動防止）
        self._historical_updating = threading.Event()
        self._realtime_updating = threading.Event()

        # 統計
        self._stats = {
            "started_at": None,
            "historical_updates": 0,
            "historical_errors": 0,
            "realtime_updates": 0,
            "realtime_errors": 0,
            "forced_updates": 0,
            "api_requests": 0,
            "last_historical_update": None,
            "last_realtime_update": None,
        }

    def start(self):
        """サービス開始"""
        self._running = True
        self._stats["started_at"] = datetime.now()

        # シグナルハンドラ設定
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # スケジュール更新
        self.schedule_manager.update_schedule()

        # APIサーバー起動
        api_status = "無効"
        if self.enable_api:
            self._api_server = TriggerAPIServer(
                self,
                self.api_port,
                enable_rate_limit=self.enable_rate_limit,
                rate_limit_short_term=self.rate_limit_short_term,
                rate_limit_long_term=self.rate_limit_long_term
            )
            if self._api_server.start():
                api_status = f"http://localhost:{self.api_port}"
            else:
                api_status = "起動失敗"

        print("=" * 70)
        print("JLTSQL バックグラウンド更新サービス")
        print("=" * 70)
        print(f"  蓄積系更新: {'有効' if self.update_historical else '無効'} (間隔: {self.historical_interval_minutes}分)")
        print(f"  速報系監視: {'有効' if self.monitor_realtime else '無効'} (動的間隔)")
        print(f"  HTTP API:   {api_status}")
        if self.enable_api and self.enable_rate_limit:
            print(f"  レート制限: {self.rate_limit_short_term}回/分, {self.rate_limit_long_term}回/時")
        print(f"  開催状況:   {self.schedule_manager.get_status_display()}")
        print(f"  本日レース: {self.schedule_manager._today_race_count}件")
        print(f"  開始時刻:   {self._stats['started_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()
        print("停止するには Ctrl+C を押してください")
        print()

        logger.info(
            "Background updater started",
            update_historical=self.update_historical,
            monitor_realtime=self.monitor_realtime,
            historical_interval=self.historical_interval_minutes,
            enable_api=self.enable_api,
            api_port=self.api_port,
            is_race_day=self.schedule_manager.is_race_day(),
            races_today=len(self.schedule_manager._today_races),
        )

        # 蓄積系更新スレッド
        if self.update_historical:
            thread = threading.Thread(target=self._historical_update_loop, daemon=True)
            thread.start()
            self._threads.append(thread)

        # 速報系監視スレッド
        if self.monitor_realtime:
            thread = threading.Thread(target=self._realtime_update_loop, daemon=True)
            thread.start()
            self._threads.append(thread)

        # ステータス表示スレッド
        thread = threading.Thread(target=self._status_display_loop, daemon=True)
        thread.start()
        self._threads.append(thread)

        # トリガー監視スレッド
        thread = threading.Thread(target=self._trigger_monitor_loop, daemon=True)
        thread.start()
        self._threads.append(thread)

        # メインループ（ブロック）
        try:
            while self._running and not self._stop_event.is_set():
                self._stop_event.wait(timeout=1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """サービス停止"""
        if not self._running:
            return

        print("\nサービスを停止中...")
        logger.info("Stopping background updater")

        self._running = False
        self._stop_event.set()

        # APIサーバー停止
        if self._api_server:
            self._api_server.stop()
            self._api_server = None

        # スレッド終了待ち
        for thread in self._threads:
            thread.join(timeout=5)

        print("サービスを停止しました")
        logger.info("Background updater stopped", **self._stats)

    def _signal_handler(self, signum, frame):
        """シグナルハンドラ"""
        logger.info(f"Received signal {signum}")
        self.stop()

    def _status_display_loop(self):
        """ステータス表示ループ"""
        last_display = datetime.now()
        display_interval = 60  # 60秒毎に表示

        while self._running and not self._stop_event.is_set():
            now = datetime.now()

            # 1分毎にスケジュールを更新（日付変更対応）
            if (now - last_display).total_seconds() >= display_interval:
                # 日付が変わったらスケジュール更新
                if self.schedule_manager._last_schedule_update:
                    if self.schedule_manager._last_schedule_update.date() != now.date():
                        self.schedule_manager.update_schedule()

                interval, reason = self.schedule_manager.get_update_interval()
                status = self.schedule_manager.get_status_display()
                print(f"[{now.strftime('%H:%M:%S')}] 状態: {status} | 速報更新間隔: {interval}秒 | 蓄積={self._stats['historical_updates']} 速報={self._stats['realtime_updates']}")
                last_display = now

            self._stop_event.wait(timeout=10)

    def _historical_update_loop(self):
        """蓄積系更新ループ"""
        logger.info("Historical update loop started")

        # 初回は即実行
        first_run = True

        while self._running and not self._stop_event.is_set():
            if first_run:
                first_run = False
            else:
                # 開催日かどうかで間隔を変える
                if self.schedule_manager.is_race_day():
                    wait_minutes = self.historical_interval_minutes
                else:
                    wait_minutes = 60  # 非開催日は60分毎

                wait_seconds = wait_minutes * 60
                logger.info(f"Waiting {wait_minutes} minutes until next historical update")
                if self._stop_event.wait(timeout=wait_seconds):
                    break

            if not self._running:
                break

            # 蓄積系データ更新を実行
            self._run_historical_update()

        logger.info("Historical update loop ended")

    def _realtime_update_loop(self):
        """速報系更新ループ（動的間隔）"""
        logger.info("Realtime update loop started")

        # 初回は蓄積系更新と競合しないよう少し待機
        if self._stop_event.wait(timeout=10):
            return

        while self._running and not self._stop_event.is_set():
            # 更新間隔を取得
            interval, reason = self.schedule_manager.get_update_interval()

            if interval == 0:
                # 非開催日は5分毎にチェックのみ
                logger.debug("Non-race day, skipping realtime update")
                if self._stop_event.wait(timeout=300):
                    break
                continue

            # 速報系データ更新を実行
            self._run_realtime_update(reason)

            # 次の更新まで待機
            if self._stop_event.wait(timeout=interval):
                break

        logger.info("Realtime update loop ended")

    def _trigger_monitor_loop(self):
        """トリガーファイル監視ループ"""
        logger.info("Trigger monitor loop started")

        while self._running and not self._stop_event.is_set():
            # トリガーファイルをチェック
            if self._check_and_process_trigger():
                now = datetime.now()
                print(f"[{now.strftime('%H:%M:%S')}] 強制更新完了")

            # 1秒間隔でチェック
            if self._stop_event.wait(timeout=1):
                break

        logger.info("Trigger monitor loop ended")

    def _check_and_process_trigger(self) -> bool:
        """トリガーファイルをチェックして処理

        Returns:
            bool: トリガーが処理されたかどうか
        """
        trigger_path = self.project_root / "data" / "trigger_update"
        if not trigger_path.exists():
            return False

        # ファイル内容を読み取ってモードを判定
        try:
            content = trigger_path.read_text().strip().lower()
            if not content:
                content = "all"
        except Exception as e:
            logger.warning(f"Failed to read trigger file: {e}")
            content = "all"

        # トリガーファイルを削除
        try:
            trigger_path.unlink()
        except Exception as e:
            logger.error(f"Failed to delete trigger file: {e}")
            return False

        # モードを正規化
        if content not in ["all", "historical", "realtime"]:
            logger.warning(f"Unknown trigger mode '{content}', using 'all'")
            content = "all"

        # トリガー検出ログ
        now = datetime.now()
        print(f"\n[{now.strftime('%H:%M:%S')}] 強制更新トリガーを検出 ({content})")
        logger.info(f"Forced update trigger detected: {content}")

        self._stats["forced_updates"] += 1

        # モードに応じて更新を実行
        if content in ["all", "historical"]:
            self._run_historical_update()

        if content in ["all", "realtime"]:
            reason = "強制更新"
            self._run_realtime_update(reason)

        return True

    def _run_historical_update(self):
        """蓄積系データの差分更新を実行"""
        # 多重起動防止チェック
        if self._historical_updating.is_set():
            logger.warning("Historical update already in progress, skipping")
            print("  [スキップ] 蓄積系更新が既に実行中です")
            return

        # JV-Link排他制御ロック取得
        if not self._jvlink_lock.acquire(blocking=False):
            logger.warning("JV-Link is busy (locked by another operation), skipping historical update")
            print("  [スキップ] JV-Linkが他の処理で使用中です")
            return

        try:
            self._historical_updating.set()

            now = datetime.now()
            today = now.strftime("%Y%m%d")
            # データ欠損防止: to_dateを1年先に設定（差分更新で未来データも取得可能にする）
            future_date = (now + timedelta(days=365)).strftime("%Y%m%d")
            print(f"\n[{now.strftime('%H:%M:%S')}] 蓄積系データ更新を開始...")
            logger.info("Starting historical data update", from_date=today, to_date=future_date)

            success_count = 0
            error_count = 0

            for spec, description in self.HISTORICAL_SPECS:
                if not self._running:
                    break

                print(f"  {spec}: {description}...", end=" ", flush=True)

                process = None
                try:
                    # subprocess.Popenを使用（タイムアウト時にプロセスをkillできるように）
                    process = subprocess.Popen(
                        [
                            sys.executable, "-m", "src.cli.main",
                            "fetch",
                            "--spec", spec,
                            "--from", today,
                            "--to", future_date,  # 未来日付を使用
                            "--option", "2",
                        ],
                        cwd=self.project_root,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                    )

                    try:
                        stdout, stderr = process.communicate(timeout=600)
                        returncode = process.returncode
                    except subprocess.TimeoutExpired:
                        # タイムアウト時はプロセスをkill
                        logger.warning(f"Process timeout for {spec}, killing process")
                        process.kill()
                        process.wait()  # ゾンビプロセス防止
                        print("タイムアウト")
                        error_count += 1
                        continue

                    if returncode == 0:
                        print("OK")
                        success_count += 1
                    else:
                        if "no data" in stdout.lower() or "データなし" in stdout:
                            print("(データなし)")
                            success_count += 1
                        else:
                            print("NG")
                            error_count += 1
                            logger.error(f"Failed to update {spec}", stderr=stderr[:200] if stderr else "")

                except Exception as e:
                    print(f"エラー: {e}")
                    error_count += 1
                    logger.error(f"Exception during historical update for {spec}", error=str(e))
                    # プロセスがまだ動いていたらkill
                    if process and process.poll() is None:
                        process.kill()
                        process.wait()

            self._stats["historical_updates"] += 1
            self._stats["historical_errors"] += error_count
            self._stats["last_historical_update"] = datetime.now()

            print(f"  完了: 成功={success_count}, エラー={error_count}")
            logger.info("Historical update completed", success=success_count, errors=error_count)

            # スケジュール更新（YSCHが更新された可能性）
            self.schedule_manager.update_schedule()

        finally:
            self._historical_updating.clear()
            self._jvlink_lock.release()

    def _run_realtime_update(self, reason: str):
        """速報系データの更新を実行"""
        # 多重起動防止チェック
        if self._realtime_updating.is_set():
            logger.warning("Realtime update already in progress, skipping")
            return

        # JV-Link排他制御ロック取得
        if not self._jvlink_lock.acquire(blocking=False):
            logger.warning("JV-Link is busy (locked by another operation), skipping realtime update")
            return

        try:
            self._realtime_updating.set()

            now = datetime.now()
            logger.info(f"Starting realtime update: {reason}")

            success_count = 0
            error_count = 0

            for spec, description in self.REALTIME_SPECS:
                if not self._running:
                    break

                try:
                    # RealtimeFetcherを使用
                    from src.fetcher.realtime import RealtimeFetcher
                    from src.database.sqlite_handler import SQLiteDatabase
                    from src.importer.importer import DataImporter

                    db = SQLiteDatabase({"path": str(self.db_path)})

                    with db:
                        fetcher = RealtimeFetcher(sid="BGUPDATE")
                        importer = DataImporter(db, batch_size=1000)

                        records = []
                        try:
                            for record in fetcher.fetch(data_spec=spec, continuous=False):
                                records.append(record)
                        except Exception as e:
                            error_str = str(e)
                            # 契約外エラーはスキップ (-111, -114, -115など)
                            if '-111' in error_str or '-114' in error_str or '-115' in error_str:
                                continue
                            if '契約' in error_str:
                                continue
                            if 'no data' in error_str.lower():
                                continue
                            raise

                        if records:
                            importer.import_records(iter(records), auto_commit=True)
                            success_count += len(records)

                except Exception as e:
                    error_count += 1
                    # エラーログレベルをdebugからwarningに変更
                    logger.warning(f"Realtime update error for {spec}: {e}")

            self._stats["realtime_updates"] += 1
            self._stats["realtime_errors"] += error_count
            self._stats["last_realtime_update"] = datetime.now()

            if success_count > 0:
                print(f"[{now.strftime('%H:%M:%S')}] 速報更新: {success_count}件 ({reason})")

            logger.info("Realtime update completed", records=success_count, errors=error_count, reason=reason)

        finally:
            self._realtime_updating.clear()
            self._jvlink_lock.release()


def main():
    parser = argparse.ArgumentParser(
        description="JLTSQL バックグラウンド更新サービス",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
更新スケジュール:
  開催日・レース30分前〜: 30秒毎（オッズ集中監視）
  開催日・レース1時間前〜: 1分毎
  開催日・発売中: 5分毎
  開催日・レース後: 10分毎（払戻確認）
  非開催日: 速報系更新なし

HTTP API エンドポイント (デフォルト: http://localhost:8765):
  GET /trigger              全データ強制更新
  GET /trigger/historical   蓄積系のみ強制更新
  GET /trigger/realtime     速報系のみ強制更新
  GET /status               現在の状態取得

使用例:
  python scripts/background_updater.py              # サービス起動
  python scripts/background_updater.py --api-port 9000  # ポート指定
  python scripts/background_updater.py --no-api     # APIなしで起動
  python scripts/background_updater.py --trigger    # 全データ強制更新
  python scripts/background_updater.py --trigger historical  # 蓄積系のみ
  python scripts/background_updater.py --trigger realtime    # 速報系のみ

外部からのAPI呼び出し例:
  curl http://localhost:8765/trigger              # 全データ更新
  curl http://localhost:8765/trigger/realtime     # 速報系のみ
  curl http://localhost:8765/status               # 状態確認
        """
    )

    parser.add_argument(
        "--interval", type=int, default=30,
        help="蓄積系データの更新間隔（分、デフォルト: 30）"
    )
    parser.add_argument(
        "--no-historical", action="store_true",
        help="蓄積系データの定期更新を無効化"
    )
    parser.add_argument(
        "--no-realtime", action="store_true",
        help="速報系データの監視を無効化"
    )
    parser.add_argument(
        "--api-port", type=int, default=8765,
        help="HTTP APIサーバーのポート番号（デフォルト: 8765）"
    )
    parser.add_argument(
        "--no-api", action="store_true",
        help="HTTP APIサーバーを無効化"
    )
    parser.add_argument(
        "--no-rate-limit", action="store_true",
        help=argparse.SUPPRESS  # 隠しオプション（開発者用）
    )
    parser.add_argument(
        "--rate-limit-short", type=int, default=5,
        help="短期レート制限（回/分、デフォルト: 5）"
    )
    parser.add_argument(
        "--rate-limit-long", type=int, default=30,
        help="長期レート制限（回/時、デフォルト: 30）"
    )
    parser.add_argument(
        "--trigger",
        nargs="?",
        const="all",
        choices=["all", "historical", "realtime"],
        help="強制更新トリガーを送信（all=両方, historical=蓄積系, realtime=速報系）"
    )

    args = parser.parse_args()

    # トリガーモードの場合
    if args.trigger:
        success = send_trigger(args.trigger)
        sys.exit(0 if success else 1)

    # 通常のサービス起動
    try:
        with ProcessLock("background_updater"):
            updater = BackgroundUpdater(
                update_historical=not args.no_historical,
                monitor_realtime=not args.no_realtime,
                historical_interval_minutes=args.interval,
                enable_api=not args.no_api,
                api_port=args.api_port,
                enable_rate_limit=not args.no_rate_limit,
                rate_limit_short_term=args.rate_limit_short,
                rate_limit_long_term=args.rate_limit_long,
            )
            updater.start()
    except ProcessLockError as e:
        print(f"[エラー] {e}")
        print("既に別のバックグラウンド更新プロセスが実行中です。")
        sys.exit(1)


if __name__ == "__main__":
    main()
