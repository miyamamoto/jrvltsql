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
# Reference: EveryDB2 表5.1-1 https://everydb.iwinz.net/edb2_manual/
# Note: "N" suffix variants (DIFN, BLDN, HOSN) are aliases used in EveryDB2 documentation
DATA_SPEC_RACE = "RACE"  # レースデータ (RA, SE, HR, WF, JG)
DATA_SPEC_DIFF = "DIFF"  # マスタデータ (UM, KS, CH, BR, BN, HN, SK, RC, HC)
DATA_SPEC_DIFN = "DIFN"  # マスタデータ (DIFF の別名、EveryDB2表記)
DATA_SPEC_YSCH = "YSCH"  # 開催スケジュール
DATA_SPEC_TOKU = "TOKU"  # 特別登録馬
DATA_SPEC_SNAP = "SNAP"  # 出馬表
DATA_SPEC_SLOP = "SLOP"  # 坂路調教
DATA_SPEC_BLOD = "BLOD"  # 血統情報
DATA_SPEC_BLDN = "BLDN"  # 血統情報 (BLOD の別名、EveryDB2表記)
DATA_SPEC_HOYU = "HOYU"  # 馬名の意味由来
DATA_SPEC_HOSE = "HOSE"  # 競走馬市場取引価格
DATA_SPEC_HOSN = "HOSN"  # 競走馬市場取引価格 (HOSE の別名、EveryDB2表記)

# Additional Data Specifications (EveryDB2)
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
# Reference: EveryDB2 https://everydb.iwinz.net/edb2_manual/
# 速報系データ: レース確定情報（結果が確定したら更新）
# 時系列データ: 継続更新情報（レース中に随時更新）

# 速報系データ (0B1x系) - レース結果・確定情報
# Row D in EveryDB2 table
JVRTOPEN_SPEED_REPORT_SPECS = {
    "0B11": "開催情報",           # WE: 開催情報
    "0B12": "レース情報",         # RA, SE: レース詳細・馬毎レース情報
    "0B13": "データマイニング予想",  # DM: タイム型データマイニング
    "0B14": "出走取消・競走除外",   # AV: 場外発売情報
    "0B15": "払戻情報",           # HR: 払戻
    "0B16": "馬体重",             # WH: 馬体重
    "0B17": "対戦型データマイニング予想",  # TM: 対戦型データマイニング
    "0B41": "騎手変更情報",        # RC: 騎手変更 (Row D, E両方)
    "0B42": "調教師変更情報",      # TC: 調教師変更 (Row D, E両方)
}

# 時系列データ (0B2x-0B3x系) - 継続更新オッズ・票数
# Row E in EveryDB2 table
JVRTOPEN_TIME_SERIES_SPECS = {
    "0B20": "票数情報",           # H1, H6: 票数
    "0B30": "単勝オッズ",         # O1: 単勝
    "0B31": "複勝・枠連オッズ",    # O1, O2: 複勝・枠連
    "0B32": "馬連オッズ",         # O3: 馬連
    "0B33": "ワイドオッズ",       # O4: ワイド
    "0B34": "馬単オッズ",         # O5: 馬単
    "0B35": "3連複オッズ",        # O6: 3連複
    "0B36": "3連単オッズ",        # O6: 3連単
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
DATA_SPEC_RT_RACE = "0B12"     # 速報レース情報
DATA_SPEC_RT_WEIGHT = "0B16"   # 速報馬体重 (0B15→0B16に修正)
DATA_SPEC_RT_PAYOUT = "0B15"   # 速報払戻
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


# JVOpen データ種別とoption対応表
# Reference: EveryDB2 表5.1-1 https://everydb.iwinz.net/edb2_manual/
# Option: 1=通常データ(Row A), 2=今週データ(Row B), 3/4=セットアップ(Row C)
JVOPEN_VALID_COMBINATIONS = {
    # Option 1 (通常データ/Row A): TOKU, RACE, DIFN, BLDN, MING, SLOP, WOOD, YSCH, HOSN, HOYU, COMM
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
    # Option 2 (今週データ/Row B): TOKU, RACE, TCVN, RCVN のみ
    2: [
        "TOKU",          # 特別登録馬
        "RACE",          # レースデータ
        "TCVN",          # 調教師変更情報
        "RCVN",          # 騎手変更情報
    ],
    # Option 3, 4 (セットアップ/Row C): Option 1と同じ
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
