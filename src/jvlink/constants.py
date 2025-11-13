"""JV-Link constants and definitions."""

# JV-Link Return Codes
JV_RT_SUCCESS = 0  # 正常終了
JV_RT_ERROR = -1  # エラー
JV_RT_NO_MORE_DATA = -2  # データなし
JV_RT_FILE_NOT_FOUND = -3  # ファイルが見つからない
JV_RT_INVALID_PARAMETER = -4  # 無効なパラメータ
JV_RT_DOWNLOAD_FAILED = -5  # ダウンロード失敗

# JVRead Return Codes
JV_READ_SUCCESS = 0  # 読み込み成功（データあり）
JV_READ_NO_MORE_DATA = -1  # これ以上データなし
JV_READ_ERROR = -2  # エラー

# Data Specification Codes
DATA_SPEC_RACE = "RACE"  # レースデータ (RA, SE, HR, WF, JG)
DATA_SPEC_DIFF = "DIFF"  # マスタデータ (UM, KS, CH, BR, BN, HN, SK, RC, HC)
DATA_SPEC_YSCH = "YSCH"  # 開催スケジュール
DATA_SPEC_TOKU = "TOKU"  # 特別登録馬
DATA_SPEC_SNAP = "SNAP"  # 出馬表
DATA_SPEC_SLOP = "SLOP"  # 坂路調教
DATA_SPEC_BLOD = "BLOD"  # 血統情報
DATA_SPEC_HOYU = "HOYU"  # 馬名の意味由来
DATA_SPEC_HOSE = "HOSE"  # 競走馬市場取引価格

# Odds Data Specifications
DATA_SPEC_O1 = "O1"  # 単勝・複勝・枠連オッズ
DATA_SPEC_O2 = "O2"  # 馬連オッズ
DATA_SPEC_O3 = "O3"  # ワイドオッズ
DATA_SPEC_O4 = "O4"  # 馬単オッズ
DATA_SPEC_O5 = "O5"  # 3連複オッズ
DATA_SPEC_O6 = "O6"  # 3連単オッズ

# Real-time Data Specifications
DATA_SPEC_RT_RACE = "0B12"  # 速報レース情報
DATA_SPEC_RT_WEIGHT = "0B15"  # 速報馬体重
DATA_SPEC_RT_ODDS = "0B20"  # 速報オッズ
DATA_SPEC_RT_PAYOUT = "0B31"  # 速報払戻

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
JVOPEN_OPTION_NORMAL = 0  # 通常
JVOPEN_OPTION_SETUP = 1  # セットアップ
JVOPEN_OPTION_UPDATE = 2  # 更新

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


def get_error_message(error_code: int) -> str:
    """Get error message for JV-Link return code.

    Args:
        error_code: JV-Link return code

    Returns:
        Error message string
    """
    error_messages = {
        JV_RT_SUCCESS: "Success",
        JV_RT_ERROR: "Error occurred",
        JV_RT_NO_MORE_DATA: "No more data available",
        JV_RT_FILE_NOT_FOUND: "File not found",
        JV_RT_INVALID_PARAMETER: "Invalid parameter",
        JV_RT_DOWNLOAD_FAILED: "Download failed",
        JV_READ_SUCCESS: "Read success",
        JV_READ_NO_MORE_DATA: "No more data to read",
        JV_READ_ERROR: "Read error",
    }
    return error_messages.get(error_code, f"Unknown error code: {error_code}")


def get_track_name(track_code: str) -> str:
    """Get track name from track code.

    Args:
        track_code: Track code (01-10)

    Returns:
        Track name in Japanese
    """
    return TRACK_NAMES.get(track_code, f"Unknown track: {track_code}")
