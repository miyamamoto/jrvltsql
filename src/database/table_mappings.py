"""Table name mapping: jltsql -> JRA-VAN Standard.

This module provides comprehensive mapping between JRA-VAN standard table names
and jrvltsql table names, covering all 38 supported record types.

Mappings:
- JRAVAN_TO_JLTSQL: JRA-VAN standard names -> jrvltsql table names
- RECORD_TYPE_TO_TABLE: Two-character record type codes -> table names
- JLTSQL_TO_JRAVAN: Reverse mapping (jrvltsql -> JRA-VAN standard)
"""

from typing import Dict


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
