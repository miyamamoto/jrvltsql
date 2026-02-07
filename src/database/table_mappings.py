"""Table name mapping: jltsql -> JRA-VAN Standard.

This module provides comprehensive mapping between JRA-VAN standard table names
and jrvltsql table names, covering all 38 supported record types for both JRA
and NAR (地方競馬) data sources.

JRA Mappings:
- JRAVAN_TO_JLTSQL: JRA-VAN standard names -> jrvltsql table names
- RECORD_TYPE_TO_TABLE: Two-character record type codes -> table names
- JLTSQL_TO_JRAVAN: Reverse mapping (jrvltsql -> JRA-VAN standard)

NAR Mappings:
- NAR_JRAVAN_TO_JLTSQL: JRA-VAN standard names -> NAR table names (_NAR suffix)
- NAR_RECORD_TYPE_TO_TABLE: Record type codes -> NAR table names
- JLTSQL_NAR_TO_JRAVAN: Reverse mapping (NAR tables -> JRA-VAN standard)

Helper Functions:
- get_table_name_for_source(): Get table name based on record type and source
- get_jravan_table_name(): Get table from JRA-VAN standard name and source
- get_record_type_from_table(): Extract record type from table name
- is_nar_table(): Check if a table is a NAR table
"""

from typing import Dict, Optional


# JRA-VAN標準名 → jrvltsqlテーブル名
JRAVAN_TO_JLTSQL: Dict[str, str] = {
    # マスタデータ (Master Data)
    "UMA": "NL_UM",           # 競走馬マスタ (Horse Master)
    "KISYU": "NL_KS",         # 騎手マスタ (Jockey Master)
    "CHOKYO": "NL_CH",        # 調教師マスタ (Trainer Master)
    "BANUSI": "NL_BN",        # 馬主マスタ (Owner Master)
    "BREEDER": "NL_BR",       # 生産者マスタ (Breeder Master)
    "HANSYOKU": "NL_HN",      # 繁殖馬マスタ (Breeding Horse Master)

    # レースデータ (Race Data)
    "RACE": "NL_RA",          # レース詳細 (Race Details)
    "UMA_RACE": "NL_SE",      # 馬毎レース情報 (Horse Race Results)
    "HARAI": "NL_HR",         # 払戻 (Refund)
    "JOCKEY_CHANGE": "NL_JC", # 騎手変更 (Jockey Change)

    # オッズ (Odds)
    "ODDS_TANPUKU": "NL_O1",  # 単複オッズ (Win/Place Odds)
    "ODDS_UMAREN": "NL_O2",   # 馬連オッズ (Quinella Odds)
    "ODDS_WIDE": "NL_O3",     # ワイドオッズ (Wide Odds)
    "ODDS_UMATAN": "NL_O4",   # 馬単オッズ (Exacta Odds)
    "ODDS_SANRENPUKU": "NL_O5", # 三連複オッズ (Trio Odds)
    "ODDS_SANRENTAN": "NL_O6", # 三連単オッズ (Trifecta Odds)

    # 票数 (Vote Counts)
    "HYO_TANPUKU": "NL_H1",   # 単複票数 (Win/Place Votes)
    "HYO_SANRENTAN": "NL_H6", # 三連単票数 (Trifecta Votes)

    # スケジュール・その他 (Schedule & Others)
    "SCHEDULE": "NL_YS",      # 開催スケジュール (Race Schedule)
    "TOKUBETSU": "NL_TK",     # 特別登録馬 (Special Registration)
    "COURSE": "NL_CS",        # コース情報 (Course Information)
    "WEATHER": "NL_WE",       # 天候情報 (Weather Information)
    "BABA": "NL_WH",          # 馬場状態 (Track Condition)

    # 追加データ (Additional Data)
    "HANSYOKU_UMA": "NL_SK",  # 産駒マスタ (Progeny Master)
    "RECORD": "NL_RC",        # レコード (Record)
    "SAKURO": "NL_HS",        # 坂路調教 (Hill Training)
    "AVOIDENCE": "NL_AV",     # 出走取消 (Scratched Horse)
    "BLOOD": "NL_BT",         # 血統情報 (Bloodline)
    "COMMENT": "NL_TC",       # コメント (Training Comment)
    "CHOKYO_DETAIL": "NL_CK", # 調教詳細 (Training Details)
    "TIME_MASTER": "NL_TM",   # タイムマスタ (Time Master)
    "DATA_MASTER": "NL_DM",   # データマスタ (Data Master)
    "WIN5": "NL_WF",          # WIN5
    "COURSE_CHANGE": "NL_CC", # コース変更 (Course Change)
    "HAICHI": "NL_HC",        # 配置 (Position)
    "MEANING": "NL_HY",       # 馬名の意味由来 (Horse Name Meaning)
    "WEIGHT_CHANGE": "NL_JG", # 重量変更 (Weight Change)
    "WOOD": "NL_WC",          # ウッドチップ調教 (Woodchip Training)
}

# レコード種別コード → テーブル名 (Record Type Code -> Table Name)
# All 38 supported record types from JV-Data specification
RECORD_TYPE_TO_TABLE: Dict[str, str] = {
    "RA": "NL_RA",  # レース詳細 (Race Details)
    "SE": "NL_SE",  # 馬毎レース情報 (Horse Race Results)
    "UM": "NL_UM",  # 競走馬マスタ (Horse Master)
    "KS": "NL_KS",  # 騎手マスタ (Jockey Master)
    "CH": "NL_CH",  # 調教師マスタ (Trainer Master)
    "BN": "NL_BN",  # 馬主マスタ (Owner Master)
    "BR": "NL_BR",  # 生産者マスタ (Breeder Master)
    "HN": "NL_HN",  # 繁殖馬マスタ (Breeding Horse Master)
    "SK": "NL_SK",  # 産駒マスタ (Progeny Master)
    "HR": "NL_HR",  # 払戻 (Refund)
    "O1": "NL_O1",  # 単複オッズ (Win/Place Odds)
    "O2": "NL_O2",  # 馬連オッズ (Quinella Odds)
    "O3": "NL_O3",  # ワイドオッズ (Wide Odds)
    "O4": "NL_O4",  # 馬単オッズ (Exacta Odds)
    "O5": "NL_O5",  # 三連複オッズ (Trio Odds)
    "O6": "NL_O6",  # 三連単オッズ (Trifecta Odds)
    "H1": "NL_H1",  # 単複票数 (Win/Place Votes)
    "H6": "NL_H6",  # 三連単票数 (Trifecta Votes)
    "YS": "NL_YS",  # 開催スケジュール (Race Schedule)
    "TK": "NL_TK",  # 特別登録馬 (Special Registration)
    "CS": "NL_CS",  # コース情報 (Course Information)
    "WE": "NL_WE",  # 天候情報 (Weather Information)
    "WH": "NL_WH",  # 馬場状態 (Track Condition)
    "RC": "NL_RC",  # レコード (Record)
    "HS": "NL_HS",  # 坂路調教 (Hill Training)
    "AV": "NL_AV",  # 出走取消 (Scratched Horse)
    "BT": "NL_BT",  # 血統情報 (Bloodline)
    "TC": "NL_TC",  # コメント (Training Comment)
    "CK": "NL_CK",  # 調教詳細 (Training Details)
    "TM": "NL_TM",  # タイムマスタ (Time Master)
    "DM": "NL_DM",  # データマスタ (Data Master)
    "WF": "NL_WF",  # WIN5
    "CC": "NL_CC",  # コース変更 (Course Change)
    "HC": "NL_HC",  # 配置 (Position)
    "HY": "NL_HY",  # 馬名の意味由来 (Horse Name Meaning)
    "JG": "NL_JG",  # 重量変更 (Weight Change)
    "JC": "NL_JC",  # 騎手変更 (Jockey Change)
    "WC": "NL_WC",  # ウッドチップ調教 (Woodchip Training)
}

# 逆マッピング: jrvltsqlテーブル名 → JRA-VAN標準名
JLTSQL_TO_JRAVAN: Dict[str, str] = {
    v: k for k, v in JRAVAN_TO_JLTSQL.items()
}

# テーブル名 → レコード種別コード逆マッピング
TABLE_TO_RECORD_TYPE: Dict[str, str] = {
    v: k for k, v in RECORD_TYPE_TO_TABLE.items()
}

# 時系列オッズ専用マッピング (TS_O1-O6)
# 時系列データ取得時にHassoTimeを含むPRIMARY KEYでデータを保存
# これにより複数時点のオッズ推移を記録可能
TIMESERIES_RECORD_TYPE_TO_TABLE: Dict[str, str] = {
    "O1": "TS_O1",  # 単複オッズ時系列
    "O2": "TS_O2",  # 馬連オッズ時系列
    "O3": "TS_O3",  # ワイドオッズ時系列
    "O4": "TS_O4",  # 馬単オッズ時系列
    "O5": "TS_O5",  # 三連複オッズ時系列
    "O6": "TS_O6",  # 三連単オッズ時系列
}

# NAR (地方競馬) テーブルマッピング
# JRAと同じレコード種別コードだが、テーブル名に _NAR サフィックスを付与
NAR_RECORD_TYPE_TO_TABLE: Dict[str, str] = {
    # NL_ tables (蓄積データ) - NAR versions
    "RA": "NL_RA_NAR",  # レース詳細 (Race Details)
    "SE": "NL_SE_NAR",  # 馬毎レース情報 (Horse Race Results)
    "HR": "NL_HR_NAR",  # 払戻 (Refund)
    "HA": "NL_HA_NAR",  # 地方競馬 払戻 (NAR Payout)
    "JG": "NL_JG_NAR",  # 重量変更 (Weight Change)
    "H1": "NL_H1_NAR",  # 単複票数 (Win/Place Votes)
    "H6": "NL_H6_NAR",  # 三連単票数 (Trifecta Votes)
    "O1": "NL_O1_NAR",  # 単複オッズ (Win/Place Odds)
    "O2": "NL_O2_NAR",  # 馬連オッズ (Quinella Odds)
    "O3": "NL_O3_NAR",  # ワイドオッズ (Wide Odds)
    "O4": "NL_O4_NAR",  # 馬単オッズ (Exacta Odds)
    "O5": "NL_O5_NAR",  # 三連複オッズ (Trio Odds)
    "O6": "NL_O6_NAR",  # 三連単オッズ (Trifecta Odds)
    "YS": "NL_YS_NAR",
    "NU": "NL_NU_NAR",  # 馬基本データ (Horse Master)  # 開催スケジュール (Race Schedule)
    "UM": "NL_UM_NAR",  # 競走馬マスタ (Horse Master)
    "KS": "NL_KS_NAR",  # 騎手マスタ (Jockey Master)
    "CH": "NL_CH_NAR",  # 調教師マスタ (Trainer Master)
    "BR": "NL_BR_NAR",  # 生産者マスタ (Breeder Master)
    "BN": "NL_BN_NAR",  # 馬主マスタ (Owner Master)
    "HN": "NL_HN_NAR",  # 繁殖馬マスタ (Breeding Horse Master)
    "SK": "NL_SK_NAR",  # 産駒マスタ (Progeny Master)
    "RC": "NL_RC_NAR",  # レコード (Record)
    "CC": "NL_CC_NAR",  # コース変更 (Course Change)
    "TC": "NL_TC_NAR",  # コメント (Training Comment)
    "CS": "NL_CS_NAR",  # コース情報 (Course Information)
    "CK": "NL_CK_NAR",  # 調教詳細 (Training Details)
    "WC": "NL_WC_NAR",  # ウッドチップ調教 (Woodchip Training)
    "AV": "NL_AV_NAR",  # 出走取消 (Scratched Horse)
    "JC": "NL_JC_NAR",  # 騎手変更 (Jockey Change)
    "HC": "NL_HC_NAR",  # 配置 (Position)
    "HS": "NL_HS_NAR",  # 坂路調教 (Hill Training)
    "HY": "NL_HY_NAR",  # 馬名の意味由来 (Horse Name Meaning)
    "WE": "NL_WE_NAR",  # 天候情報 (Weather Information)
    "WF": "NL_WF_NAR",  # WIN5
    "WH": "NL_WH_NAR",  # 馬場状態 (Track Condition)
    "TM": "NL_TM_NAR",  # タイムマスタ (Time Master)
    "TK": "NL_TK_NAR",  # 特別登録馬 (Special Registration)
    "BT": "NL_BT_NAR",  # 血統情報 (Bloodline)
    "DM": "NL_DM_NAR",  # データマスタ (Data Master)
}

# NAR JRA-VAN標準名 → jrvltsqlテーブル名 (NAR版)
NAR_JRAVAN_TO_JLTSQL: Dict[str, str] = {
    # マスタデータ (Master Data)
    "UMA": "NL_UM_NAR",           # 競走馬マスタ (Horse Master)
    "KISYU": "NL_KS_NAR",         # 騎手マスタ (Jockey Master)
    "CHOKYO": "NL_CH_NAR",        # 調教師マスタ (Trainer Master)
    "BANUSI": "NL_BN_NAR",        # 馬主マスタ (Owner Master)
    "BREEDER": "NL_BR_NAR",       # 生産者マスタ (Breeder Master)
    "HANSYOKU": "NL_HN_NAR",      # 繁殖馬マスタ (Breeding Horse Master)

    # レースデータ (Race Data)
    "RACE": "NL_RA_NAR",          # レース詳細 (Race Details)
    "UMA_RACE": "NL_SE_NAR",      # 馬毎レース情報 (Horse Race Results)
    "HARAI": "NL_HR_NAR",         # 払戻 (Refund)
    "JOCKEY_CHANGE": "NL_JC_NAR", # 騎手変更 (Jockey Change)

    # オッズ (Odds)
    "ODDS_TANPUKU": "NL_O1_NAR",  # 単複オッズ (Win/Place Odds)
    "ODDS_UMAREN": "NL_O2_NAR",   # 馬連オッズ (Quinella Odds)
    "ODDS_WIDE": "NL_O3_NAR",     # ワイドオッズ (Wide Odds)
    "ODDS_UMATAN": "NL_O4_NAR",   # 馬単オッズ (Exacta Odds)
    "ODDS_SANRENPUKU": "NL_O5_NAR", # 三連複オッズ (Trio Odds)
    "ODDS_SANRENTAN": "NL_O6_NAR", # 三連単オッズ (Trifecta Odds)

    # 票数 (Vote Counts)
    "HYO_TANPUKU": "NL_H1_NAR",   # 単複票数 (Win/Place Votes)
    "HYO_SANRENTAN": "NL_H6_NAR", # 三連単票数 (Trifecta Votes)

    # スケジュール・その他 (Schedule & Others)
    "SCHEDULE": "NL_YS_NAR",      # 開催スケジュール (Race Schedule)
    "TOKUBETSU": "NL_TK_NAR",     # 特別登録馬 (Special Registration)
    "COURSE": "NL_CS_NAR",        # コース情報 (Course Information)
    "WEATHER": "NL_WE_NAR",       # 天候情報 (Weather Information)
    "BABA": "NL_WH_NAR",          # 馬場状態 (Track Condition)

    # 追加データ (Additional Data)
    "HANSYOKU_UMA": "NL_SK_NAR",  # 産駒マスタ (Progeny Master)
    "RECORD": "NL_RC_NAR",        # レコード (Record)
    "SAKURO": "NL_HS_NAR",        # 坂路調教 (Hill Training)
    "AVOIDENCE": "NL_AV_NAR",     # 出走取消 (Scratched Horse)
    "BLOOD": "NL_BT_NAR",         # 血統情報 (Bloodline)
    "COMMENT": "NL_TC_NAR",       # コメント (Training Comment)
    "CHOKYO_DETAIL": "NL_CK_NAR", # 調教詳細 (Training Details)
    "TIME_MASTER": "NL_TM_NAR",   # タイムマスタ (Time Master)
    "DATA_MASTER": "NL_DM_NAR",   # データマスタ (Data Master)
    "WIN5": "NL_WF_NAR",          # WIN5
    "COURSE_CHANGE": "NL_CC_NAR", # コース変更 (Course Change)
    "HAICHI": "NL_HC_NAR",        # 配置 (Position)
    "MEANING": "NL_HY_NAR",       # 馬名の意味由来 (Horse Name Meaning)
    "WEIGHT_CHANGE": "NL_JG_NAR", # 重量変更 (Weight Change)
    "WOOD": "NL_WC_NAR",          # ウッドチップ調教 (Woodchip Training)
}

# NAR 逆マッピング: jrvltsqlテーブル名 → JRA-VAN標準名
JLTSQL_NAR_TO_JRAVAN: Dict[str, str] = {
    v: k for k, v in NAR_JRAVAN_TO_JLTSQL.items()
}

# NAR テーブル名 → レコード種別コード逆マッピング
NAR_TABLE_TO_RECORD_TYPE: Dict[str, str] = {
    v: k for k, v in NAR_RECORD_TYPE_TO_TABLE.items()
}


# Helper functions for source-specific table name resolution

def get_table_name_for_source(record_type: str, source: str = "jra") -> Optional[str]:
    """Get table name for record type and data source.

    Args:
        record_type: Record type code (e.g., "RA", "SE")
        source: Data source ("jra" or "nar")

    Returns:
        Table name for the source, or None if not found

    Examples:
        >>> get_table_name_for_source("RA", "jra")
        'NL_RA'
        >>> get_table_name_for_source("RA", "nar")
        'NL_RA_NAR'
    """
    if source.lower() == "nar":
        return NAR_RECORD_TYPE_TO_TABLE.get(record_type)
    else:
        return RECORD_TYPE_TO_TABLE.get(record_type)


def get_jravan_table_name(standard_name: str, source: str = "jra") -> Optional[str]:
    """Get jrvltsql table name from JRA-VAN standard name.

    Args:
        standard_name: JRA-VAN standard table name (e.g., "RACE", "UMA_RACE")
        source: Data source ("jra" or "nar")

    Returns:
        jrvltsql table name for the source, or None if not found

    Examples:
        >>> get_jravan_table_name("RACE", "jra")
        'NL_RA'
        >>> get_jravan_table_name("RACE", "nar")
        'NL_RA_NAR'
    """
    if source.lower() == "nar":
        return NAR_JRAVAN_TO_JLTSQL.get(standard_name)
    else:
        return JRAVAN_TO_JLTSQL.get(standard_name)


def get_record_type_from_table(table_name: str) -> Optional[str]:
    """Get record type code from table name (supports both JRA and NAR).

    Args:
        table_name: Table name (e.g., "NL_RA", "NL_RA_NAR")

    Returns:
        Record type code, or None if not found

    Examples:
        >>> get_record_type_from_table("NL_RA")
        'RA'
        >>> get_record_type_from_table("NL_RA_NAR")
        'RA'
    """
    # Try NAR first (more specific)
    record_type = NAR_TABLE_TO_RECORD_TYPE.get(table_name)
    if record_type:
        return record_type

    # Fall back to JRA
    return TABLE_TO_RECORD_TYPE.get(table_name)


def is_nar_table(table_name: str) -> bool:
    """Check if a table name is a NAR table.

    Args:
        table_name: Table name to check

    Returns:
        True if the table is a NAR table, False otherwise

    Examples:
        >>> is_nar_table("NL_RA_NAR")
        True
        >>> is_nar_table("NL_RA")
        False
    """
    return table_name.endswith("_NAR")
