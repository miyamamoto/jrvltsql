"""JV-Link constants and definitions."""

# JV-Link Return Codes
JV_RT_SUCCESS = 0  # 正常終了
JV_RT_ERROR = -1  # エラー
JV_RT_NO_MORE_DATA = -2  # データなし
JV_RT_FILE_NOT_FOUND = -3  # ファイルが見つからない
JV_RT_INVALID_PARAMETER = -4  # 無効なパラメータ
JV_RT_DOWNLOAD_FAILED = -5  # ダウンロード失敗

# Service Key Related Error Codes
JV_RT_SERVICE_KEY_NOT_SET = -100  # サービスキー未設定
JV_RT_SERVICE_KEY_INVALID = -101  # サービスキーが無効
JV_RT_SERVICE_KEY_EXPIRED = -102  # サービスキー有効期限切れ
JV_RT_SERVICE_UNAVAILABLE = -103  # サービス利用不可

# Data Specification Error Codes
JV_RT_UNSUBSCRIBED_DATA = -111  # 契約外データ種別
JV_RT_UNSUBSCRIBED_DATA_WARNING = -114  # 契約外データ種別（警告レベル）
JV_RT_DATA_SPEC_UNUSED = -115  # データ種別未使用

# System Error Codes
JV_RT_DATABASE_ERROR = -201  # データベースエラー
JV_RT_FILE_ERROR = -202  # ファイルエラー
JV_RT_OTHER_ERROR = -203  # その他エラー

# Download Status Codes
JV_RT_DOWNLOADING = -301  # ダウンロード中
JV_RT_DOWNLOAD_WAITING = -302  # ダウンロード待ち

# Internal Error Codes
JV_RT_INTERNAL_ERROR = -401  # 内部エラー

# Resource Error Codes
JV_RT_OUT_OF_MEMORY = -501  # メモリ不足

# JVRead Return Codes
JV_READ_SUCCESS = 0  # 読み込み成功（データあり）
JV_READ_NO_MORE_DATA = -1  # これ以上データなし
JV_READ_ERROR = -2  # エラー

# Data Specification Codes
# Note: "N" suffix variants (DIFN, BLDN, HOSN) are aliases
DATA_SPEC_RACE = "RACE"  # レースデータ (RA, SE, HR, WF, JG)
DATA_SPEC_DIFF = "DIFF"  # マスタデータ (UM, KS, CH, BR, BN, HN, SK, RC, HC)
DATA_SPEC_DIFN = "DIFN"  # マスタデータ (DIFF の別名)
DATA_SPEC_YSCH = "YSCH"  # 開催スケジュール
DATA_SPEC_TOKU = "TOKU"  # 特別登録馬
DATA_SPEC_SNAP = "SNAP"  # 出馬表
DATA_SPEC_SLOP = "SLOP"  # 坂路調教
DATA_SPEC_BLOD = "BLOD"  # 血統情報
DATA_SPEC_BLDN = "BLDN"  # 血統情報 (BLOD の別名)
DATA_SPEC_HOYU = "HOYU"  # 馬名の意味由来
DATA_SPEC_HOSE = "HOSE"  # 競走馬市場取引価格
DATA_SPEC_HOSN = "HOSN"  # 競走馬市場取引価格 (HOSE の別名)

# Additional Data Specifications
DATA_SPEC_MING = "MING"  # データマイニング予想
DATA_SPEC_WOOD = "WOOD"  # ウッドチップ調教
DATA_SPEC_COMM = "COMM"  # コメント情報

# Trainer/Jockey Change Specifications (option 2 only)
DATA_SPEC_TCVN = "TCVN"  # 調教師変更情報
DATA_SPEC_RCVN = "RCVN"  # 騎手変更情報

# Odds Data Specifications
DATA_SPEC_O1 = "O1"  # 単勝・複勝・枠連オッズ
DATA_SPEC_O2 = "O2"  # 馬連オッズ
DATA_SPEC_O3 = "O3"  # ワイドオッズ
DATA_SPEC_O4 = "O4"  # 馬単オッズ
DATA_SPEC_O5 = "O5"  # 3連複オッズ
DATA_SPEC_O6 = "O6"  # 3連単オッズ

# Real-time Data Specifications (JVRTOpen用)
# 速報系データ: レース確定情報（結果が確定したら更新）
# 時系列データ: 継続更新情報（レース中に随時更新）

# 速報系データ (0B1x系) - JRA-VAN公式仕様に基づく
# 参照: JV-Data仕様書、EveryDB2マニュアル表5.1-1
# 注意: 速報系はYYYYMMDD形式のkeyを使用（日付単位）
JVRTOPEN_SPEED_REPORT_SPECS = {
    "0B11": "速報馬体重",              # WH: 馬体重情報
    "0B12": "速報レース情報・払戻",     # RA, SE, HR: 成績確定後
    "0B13": "データマイニング予想",     # DM: タイム型データマイニング
    "0B14": "速報開催情報・一括",       # WE, AV, JC, TC, CC: 開催日単位
    "0B15": "速報レース情報",          # RA, SE, HR: 出走馬名表～
    "0B16": "速報開催情報・変更",       # WE, AV, JC, TC, CC: 騎手変更等
    "0B17": "対戦型データマイニング予想", # TM: 対戦型データマイニング
    "0B41": "騎手変更情報",            # RC: 騎手変更（個別）
    "0B42": "調教師変更情報",          # TC: 調教師変更（個別）
    "0B51": "コース情報",              # CS: コース情報
}
# 注意: 0B30, 0B31 はオッズデータで、YYYYMMDDJJRR形式のkeyが必要（時系列データ）
# 速報系のYYYYMMDD形式では-114エラーになるため、時系列専用として定義

# 時系列データ (0B2x-0B3x系) - 継続更新オッズ・票数
# 注意: 時系列データはYYYYMMDDJJRR形式のkeyが必要（レース単位）
#
# 公式情報 (https://developer.jra-van.jp/t/topic/112):
#   - 公式提供期間: 過去1年間
#   - 実際の遡及可能期間: 2003年10月4日まで（保証外）
#   - JV-Link速報系データ: 1週間分のみ保存
#   - 多くのユーザーは独自に蓄積している
JVRTOPEN_TIME_SERIES_SPECS = {
    "0B20": "票数情報",           # H1, H6: 票数
    "0B30": "単勝オッズ",         # O1: 単勝
    "0B31": "複勝・枠連オッズ",    # O1, O2: 複勝+枠連
    "0B32": "馬連オッズ",         # O2: 馬連  ※O3ではない
    "0B33": "ワイドオッズ",       # O3: ワイド ※O4ではない
    "0B34": "馬単オッズ",         # O4: 馬単  ※O5ではない
    "0B35": "3連複オッズ",        # O5: 3連複 ※O6ではない
    "0B36": "3連単オッズ",        # O6: 3連単
}

# JVRTOpen keyパラメータ形式
# 速報系(0B1x): YYYYMMDD形式（日付単位）
# 時系列(0B2x-0B3x): YYYYMMDDJJRR形式（レース単位）
#   - JJ: 競馬場コード (01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京, 06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉)
#   - RR: レース番号 (01-12)
JVRTOPEN_KEY_FORMAT_DATE = "YYYYMMDD"      # 速報系用（8桁）
JVRTOPEN_KEY_FORMAT_RACE = "YYYYMMDDJJRR"  # 時系列用（12桁）

# 競馬場コード
JYO_CODES = {
    "01": "札幌",
    "02": "函館",
    "03": "福島",
    "04": "新潟",
    "05": "東京",
    "06": "中山",
    "07": "中京",
    "08": "京都",
    "09": "阪神",
    "10": "小倉",
}

# 変更情報データ (0B4x系) - 騎手・調教師変更
# Row D, E 両方で利用可能
JVRTOPEN_CHANGE_SPECS = {
    "0B41": "騎手変更情報",        # RC: 騎手変更
    "0B42": "調教師変更情報",      # TC: 調教師変更
}

# 全JVRTOpenデータ種別 (後方互換性のため残す)
# Note: 0B41, 0B42 は SPEED_REPORT に含まれているため、重複を避ける
JVRTOPEN_DATA_SPECS = (
    list(JVRTOPEN_SPEED_REPORT_SPECS.keys()) +
    list(JVRTOPEN_TIME_SERIES_SPECS.keys())
)

# 便利な定数
DATA_SPEC_RT_RACE = "0B12"     # 速報レース情報・払戻
DATA_SPEC_RT_WEIGHT = "0B11"   # 速報馬体重 (WH)
DATA_SPEC_RT_EVENT = "0B14"    # 速報開催情報・一括
DATA_SPEC_RT_ODDS = "0B30"     # 時系列オッズ（単勝）
DATA_SPEC_RT_VOTES = "0B20"    # 時系列票数


def is_speed_report_spec(data_spec: str) -> bool:
    """Check if data_spec is a speed report (速報系) specification."""
    return data_spec in JVRTOPEN_SPEED_REPORT_SPECS


def is_time_series_spec(data_spec: str) -> bool:
    """Check if data_spec is a time series (時系列) specification."""
    return data_spec in JVRTOPEN_TIME_SERIES_SPECS


def is_valid_jvrtopen_spec(data_spec: str) -> bool:
    """Check if data_spec is valid for JVRTOpen."""
    return data_spec in JVRTOPEN_DATA_SPECS


def generate_time_series_key(date: str, jyo_code: str, race_num: int) -> str:
    """Generate YYYYMMDDJJRR format key for time series data (simplified format).

    NOTE: This simplified format (12 digits) may not work for batch retrieval.
    For batch retrieval of time series odds, use generate_time_series_full_key()
    which includes Kaiji and Nichiji (16 digits).

    Args:
        date: Date in YYYYMMDD format (e.g., "20251130")
        jyo_code: Track code (01-10)
        race_num: Race number (1-12)

    Returns:
        Key in YYYYMMDDJJRR format (e.g., "202511300511")

    Raises:
        ValueError: If parameters are invalid

    Examples:
        >>> generate_time_series_key("20251130", "05", 11)
        '202511300511'
    """
    # Validate date format
    if not isinstance(date, str) or len(date) != 8 or not date.isdigit():
        raise ValueError(f"Invalid date format: {date}. Must be YYYYMMDD format.")

    # Validate jyo_code
    if jyo_code not in JYO_CODES:
        raise ValueError(f"Invalid jyo_code: {jyo_code}. Must be 01-10.")

    # Validate race_num
    if not isinstance(race_num, int) or not (1 <= race_num <= 12):
        raise ValueError(f"Invalid race_num: {race_num}. Must be integer 1-12.")

    return f"{date}{jyo_code}{race_num:02d}"


def generate_time_series_full_key(
    date: str,
    jyo_code: str,
    kaiji: int,
    nichiji: int,
    race_num: int
) -> str:
    """Generate YYYYMMDDJJKKNNNRR format key for time series data (full format).

    Based on JVLinkToSQLite implementation, this is the correct key format
    for JVRTOpen batch retrieval of time series odds.

    Format: YYYYMMDD + JyoCD + Kaiji + Nichiji + RaceNum
    Example: 20251130 + 05 + 05 + 08 + 11 = 2025113005050811

    Args:
        date: Date in YYYYMMDD format (e.g., "20251130")
        jyo_code: Track code (01-10)
        kaiji: 回次 (meeting number, 01-99)
        nichiji: 日次 (day number within meeting, 01-12)
        race_num: Race number (1-12)

    Returns:
        Key in 16-digit format (e.g., "2025113005050811")

    Raises:
        ValueError: If parameters are invalid

    Examples:
        >>> generate_time_series_full_key("20251130", "05", 5, 8, 11)
        '2025113005050811'
    """
    # Validate date format
    if not isinstance(date, str) or len(date) != 8 or not date.isdigit():
        raise ValueError(f"Invalid date format: {date}. Must be YYYYMMDD format.")

    # Validate jyo_code
    if jyo_code not in JYO_CODES:
        raise ValueError(f"Invalid jyo_code: {jyo_code}. Must be 01-10.")

    # Validate kaiji (typically 01-05 for most tracks)
    if not isinstance(kaiji, int) or not (1 <= kaiji <= 99):
        raise ValueError(f"Invalid kaiji: {kaiji}. Must be integer 1-99.")

    # Validate nichiji (typically 01-12)
    if not isinstance(nichiji, int) or not (1 <= nichiji <= 12):
        raise ValueError(f"Invalid nichiji: {nichiji}. Must be integer 1-12.")

    # Validate race_num
    if not isinstance(race_num, int) or not (1 <= race_num <= 12):
        raise ValueError(f"Invalid race_num: {race_num}. Must be integer 1-12.")

    return f"{date}{jyo_code}{kaiji:02d}{nichiji:02d}{race_num:02d}"


def get_all_race_keys_for_date(date: str) -> list:
    """Generate all possible race keys for a given date.

    Generates keys for all 10 tracks and 12 races each.

    Args:
        date: Date in YYYYMMDD format

    Returns:
        List of 120 keys in YYYYMMDDJJRR format

    Examples:
        >>> keys = get_all_race_keys_for_date("20251130")
        >>> len(keys)
        120
        >>> keys[0]
        '202511300101'
    """
    keys = []
    for jyo_code in sorted(JYO_CODES.keys()):
        for race_num in range(1, 13):
            keys.append(generate_time_series_key(date, jyo_code, race_num))
    return keys


# JVOpen データ種別とoption対応表
# Option: 1=通常データ, 2=今週データ, 3/4=セットアップ
JVOPEN_VALID_COMBINATIONS = {
    # Option 1 (通常データ): TOKU, RACE, DIFN, BLDN, MING, SLOP, WOOD, YSCH, HOSN, HOYU, COMM
    1: [
        "TOKU", "RACE",
        "DIFF", "DIFN",  # DIFF/DIFN are equivalent
        "BLOD", "BLDN",  # BLOD/BLDN are equivalent
        "MING",          # データマイニング予想
        "SLOP",          # 坂路調教
        "WOOD",          # ウッドチップ調教
        "YSCH",          # 開催スケジュール
        "HOSE", "HOSN",  # HOSE/HOSN are equivalent
        "HOYU",          # 馬名の意味由来
        "COMM",          # コメント情報
        "SNAP",          # 出馬表
        "O1", "O2", "O3", "O4", "O5", "O6",  # オッズ
    ],
    # Option 2 (今週データ): TOKU, RACE, TCVN, RCVN のみ
    2: [
        "TOKU",          # 特別登録馬
        "RACE",          # レースデータ
        "TCVN",          # 調教師変更情報
        "RCVN",          # 騎手変更情報
    ],
    # Option 3, 4 (セットアップ): Option 1と同じ
    3: [
        "TOKU", "RACE",
        "DIFF", "DIFN",
        "BLOD", "BLDN",
        "MING", "SLOP", "WOOD", "YSCH",
        "HOSE", "HOSN", "HOYU", "COMM",
        "SNAP",
        "O1", "O2", "O3", "O4", "O5", "O6",
    ],
    4: [
        "TOKU", "RACE",
        "DIFF", "DIFN",
        "BLOD", "BLDN",
        "MING", "SLOP", "WOOD", "YSCH",
        "HOSE", "HOSN", "HOYU", "COMM",
        "SNAP",
        "O1", "O2", "O3", "O4", "O5", "O6",
    ],
}


def is_valid_jvopen_combination(data_spec: str, option: int) -> bool:
    """Check if data_spec and option combination is valid for JVOpen.

    Args:
        data_spec: Data specification code (e.g., "RACE", "DIFF")
        option: JVOpen option (1, 2, 3, or 4)

    Returns:
        True if the combination is valid, False otherwise
    """
    if option not in JVOPEN_VALID_COMBINATIONS:
        return False
    return data_spec in JVOPEN_VALID_COMBINATIONS[option]


# Record Type Codes (レコード種別)
RECORD_TYPE_RA = "RA"  # レース詳細
RECORD_TYPE_SE = "SE"  # 馬毎レース情報
RECORD_TYPE_HR = "HR"  # 払戻
RECORD_TYPE_WE = "WE"  # 天候馬場状態
RECORD_TYPE_WH = "WH"  # 馬体重
RECORD_TYPE_WF = "WF"  # WIN5
RECORD_TYPE_JG = "JG"  # 競走除外馬

# Master Record Types
RECORD_TYPE_UM = "UM"  # 競走馬マスタ
RECORD_TYPE_KS = "KS"  # 騎手マスタ
RECORD_TYPE_CH = "CH"  # 調教師マスタ
RECORD_TYPE_BR = "BR"  # 生産者マスタ
RECORD_TYPE_BN = "BN"  # 馬主マスタ
RECORD_TYPE_HN = "HN"  # 繁殖馬マスタ
RECORD_TYPE_SK = "SK"  # 産駒マスタ
RECORD_TYPE_RC = "RC"  # レコードマスタ
RECORD_TYPE_HC = "HC"  # 配当マスタ

# Odds Record Types
RECORD_TYPE_O1 = "O1"  # 単勝・複勝・枠連オッズ
RECORD_TYPE_O2 = "O2"  # 馬連オッズ
RECORD_TYPE_O3 = "O3"  # ワイドオッズ
RECORD_TYPE_O4 = "O4"  # 馬単オッズ
RECORD_TYPE_O5 = "O5"  # 3連複オッズ
RECORD_TYPE_O6 = "O6"  # 3連単オッズ

# Other Record Types
RECORD_TYPE_YSCH = "YS"  # 開催スケジュール
RECORD_TYPE_TK = "TK"  # 特別登録馬
RECORD_TYPE_HS = "HS"  # 坂路調教
RECORD_TYPE_HY = "HY"  # 馬名の意味

# Data Kubun (データ区分)
DATA_KUBUN_NEW = "1"  # 新規
DATA_KUBUN_UPDATE = "2"  # 変更
DATA_KUBUN_REREGISTER = "3"  # 再登録
DATA_KUBUN_REFRESH = "4"  # 更新
DATA_KUBUN_DELETE = "9"  # 抹消
DATA_KUBUN_ERASE = "0"  # 削除

# JVOpen Options
# IMPORTANT: Option values start from 1, NOT 0
# Reference: https://keibasoft.memo.wiki/d/JVOpen
JVOPEN_OPTION_NORMAL = 1       # 通常データ取得（差分データ、蓄積系メンテナンス用）
JVOPEN_OPTION_THIS_WEEK = 2    # 今週データ取得（直近のレースのみ、非蓄積系用）
JVOPEN_OPTION_SETUP = 3        # セットアップデータ取得（ダイアログ表示あり）
JVOPEN_OPTION_SETUP_SPLIT = 4  # セットアップデータ取得（分割用、初回のみダイアログ）

# Race Track Codes (競馬場コード)
TRACK_SAPPORO = "01"  # 札幌
TRACK_HAKODATE = "02"  # 函館
TRACK_FUKUSHIMA = "03"  # 福島
TRACK_NIIGATA = "04"  # 新潟
TRACK_TOKYO = "05"  # 東京
TRACK_NAKAYAMA = "06"  # 中山
TRACK_CHUKYO = "07"  # 中京
TRACK_KYOTO = "08"  # 京都
TRACK_HANSHIN = "09"  # 阪神
TRACK_KOKURA = "10"  # 小倉

# Track Names
TRACK_NAMES = {
    TRACK_SAPPORO: "札幌",
    TRACK_HAKODATE: "函館",
    TRACK_FUKUSHIMA: "福島",
    TRACK_NIIGATA: "新潟",
    TRACK_TOKYO: "東京",
    TRACK_NAKAYAMA: "中山",
    TRACK_CHUKYO: "中京",
    TRACK_KYOTO: "京都",
    TRACK_HANSHIN: "阪神",
    TRACK_KOKURA: "小倉",
}

# Grade Codes
GRADE_G1 = "A"  # G1
GRADE_G2 = "B"  # G2
GRADE_G3 = "C"  # G3
GRADE_LISTED = "D"  # リステッド
GRADE_OPEN = "E"  # オープン
GRADE_1600 = "F"  # 1600万下
GRADE_1000 = "G"  # 1000万下
GRADE_500 = "H"  # 500万下
GRADE_UNGRADED = "I"  # 未勝利
GRADE_NEW_HORSE = "J"  # 新馬

# Sex Codes
SEX_MALE = "1"  # 牡
SEX_FEMALE = "2"  # 牝
SEX_GELDING = "3"  # セン

# Track Type Codes
TRACK_TYPE_TURF = "1"  # 芝
TRACK_TYPE_DIRT = "2"  # ダート
TRACK_TYPE_OBSTACLE_TURF = "3"  # 障害芝
TRACK_TYPE_OBSTACLE_DIRT = "4"  # 障害ダート

# Track Condition Codes
CONDITION_FIRM = "1"  # 良
CONDITION_GOOD = "2"  # 稍重
CONDITION_YIELDING = "3"  # 重
CONDITION_SOFT = "4"  # 不良

# Weather Codes
WEATHER_FINE = "1"  # 晴
WEATHER_CLOUDY = "2"  # 曇
WEATHER_RAINY = "3"  # 雨
WEATHER_LIGHT_RAIN = "4"  # 小雨
WEATHER_SNOW = "5"  # 雪
WEATHER_LIGHT_SNOW = "6"  # 小雪

# Encoding
ENCODING_JVDATA = "shift_jis"  # JV-Data encoding
ENCODING_DATABASE = "utf-8"  # Database encoding

# Buffer Sizes
BUFFER_SIZE_JVREAD = 50000  # JVRead buffer size (bytes)
MAX_RECORD_LENGTH = 20000  # Maximum record length


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
    -115: "使用されていないデータ種別です",
    # System Errors
    -201: "データベースエラーが発生しました",
    -202: "ファイルエラーが発生しました",
    -203: "その他のエラーが発生しました",
    # Download Status
    -301: "ダウンロード中です",
    -302: "ダウンロード待ちです",
    # Internal Errors
    -401: "内部エラーが発生しました",
    # Resource Errors
    -501: "メモリが不足しています",
}


def get_error_message(error_code: int) -> str:
    """Get error message for JV-Link return code.

    Args:
        error_code: JV-Link return code

    Returns:
        Error message string in Japanese
    """
    return ERROR_MESSAGES.get(error_code, f"不明なエラーコード: {error_code}")


def get_track_name(track_code: str) -> str:
    """Get track name from track code.

    Args:
        track_code: Track code (01-10)

    Returns:
        Track name in Japanese
    """
    return TRACK_NAMES.get(track_code, f"Unknown track: {track_code}")
