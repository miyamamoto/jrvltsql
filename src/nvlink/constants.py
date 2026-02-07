"""NV-Link (UmaConn) constants and definitions.

This module provides constants for the NV-Link (地方競馬DATA) COM API,
which mirrors the JV-Link API with 'JV' -> 'NV' naming.
"""

# NV-Link Return Codes (same as JV-Link)
NV_RT_SUCCESS = 0  # 正常終了
NV_RT_ERROR = -1  # エラー
NV_RT_NO_MORE_DATA = -2  # データなし
NV_RT_FILE_NOT_FOUND = -3  # ファイルが見つからない
NV_RT_INVALID_PARAMETER = -4  # 無効なパラメータ
NV_RT_DOWNLOAD_FAILED = -5  # ダウンロード失敗

# Service Key Related Error Codes
NV_RT_SERVICE_KEY_NOT_SET = -100  # サービスキー未設定
NV_RT_SERVICE_KEY_INVALID = -101  # サービスキーが無効
NV_RT_SERVICE_KEY_EXPIRED = -102  # サービスキー有効期限切れ
NV_RT_SERVICE_UNAVAILABLE = -103  # サービス利用不可

# Data Specification Error Codes
NV_RT_UNSUBSCRIBED_DATA = -111  # 契約外データ種別
NV_RT_UNSUBSCRIBED_DATA_WARNING = -114  # 契約外データ種別（警告レベル）
NV_RT_UNSUPPORTED_DATA_SPEC = -116  # 未提供データ種別（NV-Linkでサポートされていない）

# Stream State Error Codes
NV_RT_STREAM_ALREADY_OPEN = -202  # ストリームが既にオープン中（前回のCloseが呼ばれていない）

# Authentication Error Codes (kmy-keiba JVLinkLoadResultに準拠)
NV_RT_AUTHENTICATION_ERROR = -301  # 認証エラー（サーバー認証失敗）
NV_RT_LICENCE_KEY_EXPIRED = -302  # 利用キーが不正（有効期限切れ等）
NV_RT_LICENCE_KEY_NOT_SET = -303  # 利用キーが設定されていません

# NVRead Return Codes
NV_READ_SUCCESS = 0  # 読み込み成功（データあり）
NV_READ_NO_MORE_DATA = -1  # これ以上データなし
NV_READ_ERROR = -2  # エラー

# NAR競馬場コード (30-57)
# Note: Many tracks are closed (廃止)
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

# Active NAR tracks (現役競馬場)
NAR_ACTIVE_TRACKS = {
    "30": "門別",
    "33": "帯広",
    "35": "盛岡",
    "36": "水沢",
    "42": "浦和",
    "43": "船橋",
    "44": "大井",
    "45": "川崎",
    "46": "金沢",
    "47": "笠松",
    "48": "名古屋",
    "50": "園田",
    "51": "姫路",
    "54": "高知",
    "55": "佐賀",
}

# Encoding (same as JV-Link)
ENCODING_NVDATA = "cp932"  # NV-Data encoding (Shift_JIS)

# Buffer Sizes (same as JV-Link)
BUFFER_SIZE_NVREAD = 50000  # NVRead buffer size (bytes)


# Error Messages Dictionary
ERROR_MESSAGES = {
    # Success and Basic Errors
    0: "成功",
    -1: "失敗",
    -2: "データなし",
    -3: "ファイルが見つかりません",
    -4: "無効なパラメータです",
    -5: "ダウンロードに失敗しました",
    # Service Key Related Errors
    -100: "サービスキーが設定されていません",
    -101: "サービスキーが無効です",
    -102: "サービスキーの有効期限が切れています",
    -103: "サービスが利用できません",
    # Data Specification Errors
    -111: "契約外のデータ種別です",
    -114: "契約外のデータ種別です（警告）",
    -116: "未提供のデータ種別です（NV-Linkでサポートされていません）",
    # System Error Codes (kmy-keiba JVLinkLoadResultに準拠)
    -201: "初期化が行われていません（NVInitが呼ばれていない）",
    -202: "すでに接続が開かれています（NVCloseを呼んでください）",
    -203: "接続が開かれていません（NVOpenが呼ばれていない、または失敗）",
    -211: "レジストリの値が不正です",
    # Authentication Error Codes (kmy-keiba JVLinkLoadResultに準拠)
    -301: "認証エラーです（サーバー認証失敗）",
    -302: "利用キーが不正です（有効期限切れ等）",
    -303: "利用キーが設定されていません",
    # Server Error Codes
    -401: "内部エラー",
    -411: "サーバーエラー（404 Not Found）",
    -412: "サーバーエラー（403 Forbidden）",
    -413: "サーバーエラー",
    -421: "サーバーの不正な応答",
    -431: "サーバーアプリケーションの不正な応答",
}


def get_error_message(error_code: int) -> str:
    """Get error message for NV-Link return code.

    Args:
        error_code: NV-Link return code

    Returns:
        Error message string in Japanese
    """
    return ERROR_MESSAGES.get(error_code, f"不明なエラーコード: {error_code}")


def get_nar_track_name(track_code: str) -> str:
    """Get NAR track name from track code.

    Args:
        track_code: Track code (30-57)

    Returns:
        Track name in Japanese
    """
    return NAR_JYO_CODES.get(track_code, f"Unknown track: {track_code}")


def is_active_nar_track(track_code: str) -> bool:
    """Check if NAR track is currently active.

    Args:
        track_code: Track code (30-57)

    Returns:
        True if track is active, False if closed
    """
    return track_code in NAR_ACTIVE_TRACKS


def generate_nar_time_series_full_key(
    date: str,
    jyo_code: str,
    kaiji: int,
    nichiji: int,
    race_num: int
) -> str:
    """Generate YYYYMMDDJJKKNNNRR format key for NAR time series data.

    Based on JV-Link format but adapted for NAR (地方競馬) racecourse codes.

    Format: YYYYMMDD + JyoCD + Kaiji + Nichiji + RaceNum
    Example: 20251215 + 44 + 03 + 05 + 08 = 2025121544030508

    Args:
        date: Date in YYYYMMDD format (e.g., "20251215")
        jyo_code: NAR Track code (30-57, e.g., "44" for 大井)
        kaiji: 回次 (meeting number, 01-99)
        nichiji: 日次 (day number within meeting, 01-12)
        race_num: Race number (1-12)

    Returns:
        Key in 16-digit format (e.g., "2025121544030508")

    Raises:
        ValueError: If parameters are invalid

    Examples:
        >>> generate_nar_time_series_full_key("20251215", "44", 3, 5, 8)
        '2025121544030508'
    """
    # Validate date format
    if not isinstance(date, str) or len(date) != 8 or not date.isdigit():
        raise ValueError(f"Invalid date format: {date}. Must be YYYYMMDD format.")

    # Validate jyo_code (NAR: 30-57)
    if jyo_code not in NAR_JYO_CODES:
        raise ValueError(f"Invalid NAR jyo_code: {jyo_code}. Must be 30-57.")

    # Validate kaiji
    if not isinstance(kaiji, int) or not (1 <= kaiji <= 99):
        raise ValueError(f"Invalid kaiji: {kaiji}. Must be integer 1-99.")

    # Validate nichiji
    if not isinstance(nichiji, int) or not (1 <= nichiji <= 99):
        raise ValueError(f"Invalid nichiji: {nichiji}. Must be integer 1-99.")

    # Validate race_num
    if not isinstance(race_num, int) or not (1 <= race_num <= 12):
        raise ValueError(f"Invalid race_num: {race_num}. Must be integer 1-12.")

    # Generate key: YYYYMMDD + JJ + KK + NN + RR
    return f"{date}{jyo_code}{kaiji:02d}{nichiji:02d}{race_num:02d}"
