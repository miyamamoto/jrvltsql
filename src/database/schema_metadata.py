"""Schema metadata for MCP (Model Context Protocol) integration.

This module provides detailed descriptions of tables and columns
for LLM-based applications to understand the database schema. ``nullable``
describes the portable logical contract, including primary-key non-nullability
even where SQLite's raw catalog flag differs. ``indexes`` is the distinct
physical-column union used by configured secondary indexes, not an export of
complete index definitions.
"""

import re
from copy import deepcopy
from typing import Dict, List, TypedDict

from src.database.indexes import INDEXES
from src.database.schema_types import (
    get_all_executable_tables,
    get_table_column_nullability,
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.table_mappings import JRAVAN_TO_JLTSQL, TABLE_TO_RECORD_TYPE


class ColumnMetadata(TypedDict):
    """Column metadata definition."""
    name: str
    type: str
    description: str
    example: str
    nullable: bool


class TableMetadata(TypedDict):
    """Table metadata definition."""
    table_name: str
    record_type: str
    description: str
    purpose: str
    columns: List[ColumnMetadata]
    primary_key: List[str]
    indexes: List[str]


def _schema_backed_metadata(
    table_name: str,
    *,
    record_type: str,
    description: str,
    purpose: str,
    indexes: List[str],
) -> TableMetadata:
    """Build metadata from the executable schema so public names cannot drift."""

    primary_key = get_table_primary_key_columns(table_name)
    nullability = get_table_column_nullability(table_name)
    return {
        "table_name": table_name,
        "record_type": record_type,
        "description": description,
        "purpose": purpose,
        "columns": [
            {
                "name": column_name,
                "type": column_type,
                "description": column_name,
                "example": "",
                "nullable": nullability[column_name],
            }
            for column_name, column_type in get_table_column_types(table_name).items()
        ],
        "primary_key": primary_key,
        "indexes": indexes,
    }


# 主要テーブルのメタデータ定義
TABLE_METADATA: Dict[str, TableMetadata] = {
    "NL_RA": {
        "table_name": "NL_RA",
        "record_type": "RA",
        "description": "レース詳細情報",
        "purpose": "各レースの基本情報（日時、競馬場、距離、馬場状態、天候、グレードなど）を格納",
        "columns": [
            {
                "name": "レコード種別ID",
                "type": "TEXT",
                "description": "レコード種別識別子（常に'RA'）",
                "example": "RA",
                "nullable": False
            },
            {
                "name": "データ区分",
                "type": "TEXT",
                "description": (
                    "レース詳細のデータ区分（1～7=提供段階、A=地方、B=海外、"
                    "9=レース中止、0=提供ミス等による該当レコード削除）"
                ),
                "example": "1",
                "nullable": False
            },
            {
                "name": "データ作成年月日",
                "type": "TEXT",
                "description": "データ作成日（YYYYMMDD形式）",
                "example": "20240601",
                "nullable": False
            },
            {
                "name": "開催年月日",
                "type": "TEXT",
                "description": "レース開催日（YYYYMMDD形式）",
                "example": "20240601",
                "nullable": False
            },
            {
                "name": "競馬場コード",
                "type": "TEXT",
                "description": "競馬場コード（01=札幌、02=函館、03=福島、04=新潟、05=東京、06=中山、07=中京、08=京都、09=阪神、10=小倉）",
                "example": "05",
                "nullable": False
            },
            {
                "name": "レース番号",
                "type": "TEXT",
                "description": "その日の何レース目か（01-12）",
                "example": "11",
                "nullable": False
            },
            {
                "name": "レース名",
                "type": "TEXT",
                "description": "レース名称（例：東京優駿（日本ダービー）、天皇賞（秋））",
                "example": "東京優駿（日本ダービー）",
                "nullable": True
            },
            {
                "name": "グレードコード",
                "type": "TEXT",
                "description": "グレード（A=GⅠ、B=GⅡ、C=GⅢ、D=重賞、E=OP特別、F=L、G=3勝クラス、H=2勝クラス、I=1勝クラス、J=未勝利、K=新馬）",
                "example": "A",
                "nullable": True
            },
            {
                "name": "距離",
                "type": "TEXT",
                "description": "レース距離（メートル）",
                "example": "2400",
                "nullable": False
            },
            {
                "name": "トラックコード",
                "type": "TEXT",
                "description": "トラック種別（10=芝、23=ダート、29=障害芝）+ 回り方向（内=0、外=1、直線=2）",
                "example": "10",
                "nullable": False
            },
            {
                "name": "馬場状態コード",
                "type": "TEXT",
                "description": "馬場状態（1=良、2=稍重、3=重、4=不良）",
                "example": "1",
                "nullable": True
            },
            {
                "name": "天候コード",
                "type": "TEXT",
                "description": "天候（1=晴、2=曇、3=雨、4=小雨、5=雪、6=小雪）",
                "example": "1",
                "nullable": True
            },
            {
                "name": "発走時刻",
                "type": "TEXT",
                "description": "発走時刻（HHMM形式）",
                "example": "1540",
                "nullable": True
            },
            {
                "name": "頭数",
                "type": "TEXT",
                "description": "出走頭数",
                "example": "18",
                "nullable": True
            }
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日", "グレードコード", "距離"]
    },

    "NL_SE": {
        "table_name": "NL_SE",
        "record_type": "SE",
        "description": "馬毎レース情報",
        "purpose": "各レースにおける各馬の成績（着順、タイム、騎手、オッズ、人気など）を格納",
        "columns": [
            {
                "name": "レコード種別ID",
                "type": "TEXT",
                "description": "レコード種別識別子（常に'SE'）",
                "example": "SE",
                "nullable": False
            },
            {
                "name": "データ区分",
                "type": "TEXT",
                "description": "データ区分（0=該当レコード削除、1〜7/9/A/B=公式提供状態）",
                "example": "1",
                "nullable": False
            },
            {
                "name": "開催年月日",
                "type": "TEXT",
                "description": "レース開催日（YYYYMMDD形式）",
                "example": "20240601",
                "nullable": False
            },
            {
                "name": "競馬場コード",
                "type": "TEXT",
                "description": "競馬場コード",
                "example": "05",
                "nullable": False
            },
            {
                "name": "レース番号",
                "type": "TEXT",
                "description": "レース番号",
                "example": "11",
                "nullable": False
            },
            {
                "name": "馬番",
                "type": "TEXT",
                "description": "馬番（ゼッケン番号）",
                "example": "03",
                "nullable": False
            },
            {
                "name": "血統登録番号",
                "type": "TEXT",
                "description": "馬の血統登録番号（10桁）",
                "example": "2021101234",
                "nullable": False
            },
            {
                "name": "馬名",
                "type": "TEXT",
                "description": "馬名",
                "example": "ディープインパクト",
                "nullable": True
            },
            {
                "name": "確定着順",
                "type": "TEXT",
                "description": "確定着順（00=中止、01-18=着順）",
                "example": "01",
                "nullable": True
            },
            {
                "name": "走破タイム",
                "type": "TEXT",
                "description": "走破タイム（秒.1/10秒、例：1234=123.4秒）",
                "example": "1234",
                "nullable": True
            },
            {
                "name": "騎手コード",
                "type": "TEXT",
                "description": "騎手コード（5桁）",
                "example": "01234",
                "nullable": True
            },
            {
                "name": "騎手名",
                "type": "TEXT",
                "description": "騎手名",
                "example": "武豊",
                "nullable": True
            },
            {
                "name": "単勝オッズ",
                "type": "TEXT",
                "description": "単勝オッズ（1/10倍、例：15=1.5倍）",
                "example": "15",
                "nullable": True
            },
            {
                "name": "単勝人気順",
                "type": "TEXT",
                "description": "単勝人気順（01-18）",
                "example": "01",
                "nullable": True
            },
            {
                "name": "馬体重",
                "type": "TEXT",
                "description": "馬体重（kg）",
                "example": "482",
                "nullable": True
            },
            {
                "name": "馬体重増減",
                "type": "TEXT",
                "description": "前走からの馬体重増減（+/-kg、例：+6、-4）",
                "example": "+6",
                "nullable": True
            }
        ],
        "primary_key": [
            "Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji",
            "RaceNum", "Umaban", "KettoNum"
        ],
        "indexes": ["開催年月日", "血統登録番号", "騎手コード"]
    },

    "NL_HR": {
        "table_name": "NL_HR",
        "record_type": "HR",
        "description": "払戻情報",
        "purpose": "各レースの払戻金額（単勝、複勝、馬連、馬単、ワイド、3連複、3連単）を格納",
        "columns": [
            {
                "name": "レコード種別ID",
                "type": "TEXT",
                "description": "レコード種別識別子（常に'HR'）",
                "example": "HR",
                "nullable": False
            },
            {
                "name": "データ区分",
                "type": "TEXT",
                "description": "データ区分",
                "example": "1",
                "nullable": False
            },
            {
                "name": "開催年月日",
                "type": "TEXT",
                "description": "レース開催日（YYYYMMDD形式）",
                "example": "20240601",
                "nullable": False
            },
            {
                "name": "競馬場コード",
                "type": "TEXT",
                "description": "競馬場コード",
                "example": "05",
                "nullable": False
            },
            {
                "name": "レース番号",
                "type": "TEXT",
                "description": "レース番号",
                "example": "11",
                "nullable": False
            },
            {
                "name": "単勝馬番",
                "type": "TEXT",
                "description": "単勝的中馬番",
                "example": "03",
                "nullable": True
            },
            {
                "name": "単勝払戻金",
                "type": "TEXT",
                "description": "単勝100円当たり払戻金（円）",
                "example": "150",
                "nullable": True
            },
            {
                "name": "複勝馬番",
                "type": "TEXT",
                "description": "複勝的中馬番（最大3頭、カンマ区切り）",
                "example": "03,05,07",
                "nullable": True
            },
            {
                "name": "複勝払戻金",
                "type": "TEXT",
                "description": "複勝100円当たり払戻金（円、複数ある場合カンマ区切り）",
                "example": "110,180,250",
                "nullable": True
            },
            {
                "name": "馬連組番",
                "type": "TEXT",
                "description": "馬連的中組番（例：03-05）",
                "example": "03-05",
                "nullable": True
            },
            {
                "name": "馬連払戻金",
                "type": "TEXT",
                "description": "馬連100円当たり払戻金（円）",
                "example": "1200",
                "nullable": True
            },
            {
                "name": "馬単組番",
                "type": "TEXT",
                "description": "馬単的中組番（例：03-05、着順通り）",
                "example": "03-05",
                "nullable": True
            },
            {
                "name": "馬単払戻金",
                "type": "TEXT",
                "description": "馬単100円当たり払戻金（円）",
                "example": "2400",
                "nullable": True
            },
            {
                "name": "ワイド組番",
                "type": "TEXT",
                "description": "ワイド的中組番（最大3組、カンマ区切り）",
                "example": "03-05,03-07,05-07",
                "nullable": True
            },
            {
                "name": "ワイド払戻金",
                "type": "TEXT",
                "description": "ワイド100円当たり払戻金（円、カンマ区切り）",
                "example": "500,800,1200",
                "nullable": True
            },
            {
                "name": "3連複組番",
                "type": "TEXT",
                "description": "3連複的中組番（例：03-05-07）",
                "example": "03-05-07",
                "nullable": True
            },
            {
                "name": "3連複払戻金",
                "type": "TEXT",
                "description": "3連複100円当たり払戻金（円）",
                "example": "5000",
                "nullable": True
            },
            {
                "name": "3連単組番",
                "type": "TEXT",
                "description": "3連単的中組番（例：03-05-07、着順通り）",
                "example": "03-05-07",
                "nullable": True
            },
            {
                "name": "3連単払戻金",
                "type": "TEXT",
                "description": "3連単100円当たり払戻金（円）",
                "example": "15000",
                "nullable": True
            }
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日"]
    },

    "NL_UM": {
        "table_name": "NL_UM",
        "record_type": "UM",
        "description": "馬マスタ情報",
        "purpose": "競走馬の基本情報（血統登録番号、馬名、性別、毛色、生年月日、父馬、母馬など）を格納",
        "columns": [
            {
                "name": "レコード種別ID",
                "type": "TEXT",
                "description": "レコード種別識別子（常に'UM'）",
                "example": "UM",
                "nullable": False
            },
            {
                "name": "血統登録番号",
                "type": "TEXT",
                "description": "馬の血統登録番号（10桁）",
                "example": "2021101234",
                "nullable": False
            },
            {
                "name": "馬名",
                "type": "TEXT",
                "description": "馬名",
                "example": "ディープインパクト",
                "nullable": True
            },
            {
                "name": "性別コード",
                "type": "TEXT",
                "description": "性別（1=牡、2=牝、3=セン）",
                "example": "1",
                "nullable": True
            },
            {
                "name": "毛色コード",
                "type": "TEXT",
                "description": "毛色（1=栗毛、2=栃栗毛、3=鹿毛、4=黒鹿毛、5=青鹿毛、6=青毛、7=芦毛、8=栗粕毛、9=鹿粕毛、10=白毛）",
                "example": "3",
                "nullable": True
            },
            {
                "name": "生年月日",
                "type": "TEXT",
                "description": "生年月日（YYYYMMDD形式）",
                "example": "20210315",
                "nullable": True
            },
            {
                "name": "父馬血統登録番号",
                "type": "TEXT",
                "description": "父馬の血統登録番号",
                "example": "2002102123",
                "nullable": True
            },
            {
                "name": "父馬名",
                "type": "TEXT",
                "description": "父馬名",
                "example": "サンデーサイレンス",
                "nullable": True
            },
            {
                "name": "母馬血統登録番号",
                "type": "TEXT",
                "description": "母馬の血統登録番号",
                "example": "1995103456",
                "nullable": True
            },
            {
                "name": "母馬名",
                "type": "TEXT",
                "description": "母馬名",
                "example": "ウインドインハーヘア",
                "nullable": True
            },
            {
                "name": "母父馬血統登録番号",
                "type": "TEXT",
                "description": "母父馬の血統登録番号",
                "example": "1987104567",
                "nullable": True
            },
            {
                "name": "母父馬名",
                "type": "TEXT",
                "description": "母父馬名",
                "example": "Alzao",
                "nullable": True
            },
            {
                "name": "馬主コード",
                "type": "TEXT",
                "description": "馬主コード",
                "example": "012345",
                "nullable": True
            },
            {
                "name": "馬主名",
                "type": "TEXT",
                "description": "馬主名",
                "example": "金子真人ホールディングス",
                "nullable": True
            },
            {
                "name": "生産者コード",
                "type": "TEXT",
                "description": "生産者コード",
                "example": "006789",
                "nullable": True
            },
            {
                "name": "生産者名",
                "type": "TEXT",
                "description": "生産者名",
                "example": "ノーザンファーム",
                "nullable": True
            }
        ],
        "primary_key": ["血統登録番号"],
        "indexes": ["馬名", "父馬血統登録番号", "母馬血統登録番号"]
    },

    "NL_KS": _schema_backed_metadata(
        "NL_KS",
        record_type="KS",
        description="騎手マスタ基本情報",
        purpose="騎手の基本情報、初騎乗・初勝利、最近の重賞勝利3件を格納",
        indexes=["KisyuName", "TozaiCD"],
    ),
    "NL_KS_SEISEKI": _schema_backed_metadata(
        "NL_KS_SEISEKI",
        record_type="KS",
        description="騎手マスタ成績情報",
        purpose="騎手ごとの本年・前年・累計成績をNum=1,2,3の3行で格納",
        indexes=["KisyuCode", "SetYear"],
    ),

    "NL_YS": _schema_backed_metadata(
        "NL_YS",
        record_type="YS",
        description="開催スケジュール",
        purpose="開催日・曜日と最大3競走の重賞案内を格納",
        indexes=["Year", "MonthDay", "JyoCD", "YoubiCD"],
    ),

    # オッズ情報テーブル (Odds Tables)
    "NL_O1": {
        "table_name": "NL_O1",
        "record_type": "O1",
        "description": "単勝・複勝・枠連オッズ情報",
        "purpose": "単勝、複勝、枠連の各オッズデータと投票数を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'O1'）", "example": "O1", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日（YYYYMMDD形式）", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード（01-10）", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号（01-12）", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "オッズ発表時刻（MMDDHHmm形式）", "example": "06011430", "nullable": False},
            {"name": "単勝オッズ", "type": "TEXT", "description": "単勝オッズ（馬番順、1.0-999.9）", "example": "3.5", "nullable": True},
            {"name": "複勝オッズ", "type": "TEXT", "description": "複勝オッズ（下限-上限形式）", "example": "1.2-1.5", "nullable": True},
            {"name": "枠連オッズ", "type": "TEXT", "description": "枠連オッズ（枠番組合せ順）", "example": "12.3", "nullable": True},
            {"name": "単勝票数合計", "type": "TEXT", "description": "単勝投票総数", "example": "1234567", "nullable": True},
            {"name": "複勝票数合計", "type": "TEXT", "description": "複勝投票総数", "example": "987654", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "馬番", "組番"],
        "indexes": ["開催年月日", "発表月日時分"]
    },

    "NL_O2": {
        "table_name": "NL_O2",
        "record_type": "O2",
        "description": "馬連オッズ情報",
        "purpose": "馬連（2頭の組み合わせ）のオッズと投票数を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'O2'）", "example": "O2", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "オッズ発表時刻", "example": "06011430", "nullable": False},
            {"name": "馬連オッズ", "type": "TEXT", "description": "馬連オッズ（全組合せ）", "example": "45.6", "nullable": True},
            {"name": "馬連票数合計", "type": "TEXT", "description": "馬連投票総数", "example": "2345678", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "組番"],
        "indexes": ["開催年月日"]
    },

    "NL_O3": {
        "table_name": "NL_O3",
        "record_type": "O3",
        "description": "ワイドオッズ情報",
        "purpose": "ワイド（2頭が3着以内）のオッズと投票数を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'O3'）", "example": "O3", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "オッズ発表時刻", "example": "06011430", "nullable": False},
            {"name": "ワイドオッズ", "type": "TEXT", "description": "ワイドオッズ（下限-上限形式）", "example": "2.5-3.2", "nullable": True},
            {"name": "ワイド票数合計", "type": "TEXT", "description": "ワイド投票総数", "example": "1876543", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "組番"],
        "indexes": ["開催年月日"]
    },

    "NL_O4": {
        "table_name": "NL_O4",
        "record_type": "O4",
        "description": "馬単オッズ情報",
        "purpose": "馬単（1着→2着の順番指定）のオッズと投票数を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'O4'）", "example": "O4", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "オッズ発表時刻", "example": "06011430", "nullable": False},
            {"name": "馬単オッズ", "type": "TEXT", "description": "馬単オッズ（全組合せ・順番指定）", "example": "123.4", "nullable": True},
            {"name": "馬単票数合計", "type": "TEXT", "description": "馬単投票総数", "example": "3456789", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "組番"],
        "indexes": ["開催年月日"]
    },

    "NL_O5": {
        "table_name": "NL_O5",
        "record_type": "O5",
        "description": "3連複オッズ情報",
        "purpose": "3連複（3頭が3着以内、順不同）のオッズと投票数を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'O5'）", "example": "O5", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "オッズ発表時刻", "example": "06011430", "nullable": False},
            {"name": "3連複オッズ", "type": "TEXT", "description": "3連複オッズ（全組合せ）", "example": "456.7", "nullable": True},
            {"name": "3連複票数合計", "type": "TEXT", "description": "3連複投票総数", "example": "4567890", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "組番"],
        "indexes": ["開催年月日"]
    },

    "NL_O6": {
        "table_name": "NL_O6",
        "record_type": "O6",
        "description": "3連単オッズ情報",
        "purpose": "3連単（1着→2着→3着の順番指定）のオッズと投票数を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'O6'）", "example": "O6", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "オッズ発表時刻", "example": "06011430", "nullable": False},
            {"name": "3連単オッズ", "type": "TEXT", "description": "3連単オッズ（全組合せ・順番指定）", "example": "12345.6", "nullable": True},
            {"name": "3連単票数合計", "type": "TEXT", "description": "3連単投票総数", "example": "5678901", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "組番"],
        "indexes": ["開催年月日"]
    },

    # マスタ情報テーブル (Master Tables)
    "NL_BN": {
        "table_name": "NL_BN",
        "record_type": "BN",
        "description": "馬主マスタ情報",
        "purpose": "馬主の基本情報と成績データを格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'BN'）", "example": "BN", "nullable": False},
            {"name": "馬主コード", "type": "TEXT", "description": "馬主識別コード（6桁）", "example": "012345", "nullable": False},
            {"name": "馬主名法人格有", "type": "TEXT", "description": "馬主名（法人格付き、例：有限会社○○）", "example": "有限会社サンデーレーシング", "nullable": True},
            {"name": "馬主名法人格無", "type": "TEXT", "description": "馬主名（法人格なし）", "example": "サンデーレーシング", "nullable": True},
            {"name": "馬主名欧字", "type": "TEXT", "description": "馬主名（英語表記）", "example": "Sunday Racing", "nullable": True},
            {"name": "服色標示", "type": "TEXT", "description": "勝負服の色・柄パターン", "example": "青、赤たすき、赤袖", "nullable": True},
            {"name": "本年累計成績情報", "type": "TEXT", "description": "当年・累計の1着-着外回数と獲得賞金", "example": "10-8-7-25/123456789", "nullable": True}
        ],
        "primary_key": ["馬主コード"],
        "indexes": ["馬主名法人格無"]
    },

    "NL_BR": {
        "table_name": "NL_BR",
        "record_type": "BR",
        "description": "生産者マスタ情報",
        "purpose": "馬の生産者（ブリーダー）の基本情報と成績を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'BR'）", "example": "BR", "nullable": False},
            {"name": "生産者コード", "type": "TEXT", "description": "生産者識別コード（6桁）", "example": "098765", "nullable": False},
            {"name": "生産者名法人格有", "type": "TEXT", "description": "生産者名（法人格付き）", "example": "社台ファーム", "nullable": True},
            {"name": "生産者名法人格無", "type": "TEXT", "description": "生産者名（法人格なし）", "example": "社台ファーム", "nullable": True},
            {"name": "生産者名欧字", "type": "TEXT", "description": "生産者名（英語表記）", "example": "Shadai Farm", "nullable": True},
            {"name": "生産者住所自治省名", "type": "TEXT", "description": "生産牧場所在地（都道府県・市町村）", "example": "北海道勇払郡安平町", "nullable": True},
            {"name": "本年累計成績情報", "type": "TEXT", "description": "当年・累計の成績", "example": "15-12-10-30", "nullable": True}
        ],
        "primary_key": ["生産者コード"],
        "indexes": ["生産者名法人格無"]
    },

    "NL_BT": {
        "table_name": "NL_BT",
        "record_type": "BT",
        "description": "繁殖馬系統情報",
        "purpose": "繁殖馬の血統系統分類（サイアーライン）を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'BT'）", "example": "BT", "nullable": False},
            {"name": "繁殖登録番号", "type": "TEXT", "description": "繁殖馬登録番号（10桁）", "example": "1234567890", "nullable": False},
            {"name": "系統ID", "type": "TEXT", "description": "系統識別コード", "example": "101", "nullable": True},
            {"name": "系統名", "type": "TEXT", "description": "系統名称（例：ノーザンダンサー系、サンデーサイレンス系）", "example": "サンデーサイレンス系", "nullable": True},
            {"name": "系統説明", "type": "TEXT", "description": "系統の詳細説明・特徴", "example": "日本競馬に多大な影響を与えた系統", "nullable": True}
        ],
        "primary_key": ["繁殖登録番号"],
        "indexes": ["系統ID"]
    },

    "NL_CH": _schema_backed_metadata(
        "NL_CH",
        record_type="CH",
        description="調教師マスタ基本情報",
        purpose="調教師の基本情報、免許情報、所属、最近の重賞勝利3件を格納",
        indexes=["ChokyosiName", "TozaiCD"],
    ),
    "NL_CH_SEISEKI": _schema_backed_metadata(
        "NL_CH_SEISEKI",
        record_type="CH",
        description="調教師マスタ成績情報",
        purpose="調教師ごとの本年・前年・累計成績をNum=1,2,3の3行で格納",
        indexes=["ChokyosiCode", "SetYear"],
    ),

    "NL_HN": {
        "table_name": "NL_HN",
        "record_type": "HN",
        "description": "血統情報",
        "purpose": "繁殖馬の基本情報（名前、性別、品種、父母馬）を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'HN'）", "example": "HN", "nullable": False},
            {"name": "繁殖登録番号", "type": "TEXT", "description": "繁殖馬登録番号（10桁）", "example": "1234567890", "nullable": False},
            {"name": "馬名", "type": "TEXT", "description": "馬名（日本語）", "example": "ディープインパクト", "nullable": True},
            {"name": "馬名欧字", "type": "TEXT", "description": "馬名（英語表記）", "example": "Deep Impact", "nullable": True},
            {"name": "生年", "type": "TEXT", "description": "生年（YYYY形式）", "example": "2002", "nullable": True},
            {"name": "性別コード", "type": "TEXT", "description": "性別（1=牡、2=牝、3=セン）", "example": "1", "nullable": True},
            {"name": "品種コード", "type": "TEXT", "description": "品種（1=サラブレッド、2=アラブ等）", "example": "1", "nullable": True},
            {"name": "毛色コード", "type": "TEXT", "description": "毛色（01=栗毛、02=栃栗毛、03=鹿毛、04=黒鹿毛、05=青鹿毛、06=青毛、07=芦毛、08=栗粕毛、09=鹿粕毛、10=青粕毛、11=白毛）", "example": "03", "nullable": True},
            {"name": "父馬繁殖登録番号", "type": "TEXT", "description": "父馬の繁殖登録番号", "example": "0987654321", "nullable": True},
            {"name": "母馬繁殖登録番号", "type": "TEXT", "description": "母馬の繁殖登録番号", "example": "1122334455", "nullable": True}
        ],
        "primary_key": ["繁殖登録番号"],
        "indexes": ["馬名", "生年"]
    },

    # 変更・除外情報テーブル (Change/Exclusion Tables)
    "NL_AV": {
        "table_name": "NL_AV",
        "record_type": "AV",
        "description": "出走取消・競走除外情報",
        "purpose": "出走取消または競走除外となった馬と発表時刻・事由を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'AV'）", "example": "AV", "nullable": False},
            {"name": "データ区分", "type": "TEXT", "description": "データ区分（1=出走取消、2=競走除外）", "example": "1", "nullable": False},
            {"name": "データ作成年月日", "type": "TEXT", "description": "データ作成日", "example": "20240601", "nullable": False},
            {"name": "開催年", "type": "INTEGER", "description": "開催年", "example": "2024", "nullable": False},
            {"name": "開催月日", "type": "INTEGER", "description": "開催月日", "example": "0601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "開催回", "type": "INTEGER", "description": "開催回", "example": "3", "nullable": False},
            {"name": "開催日目", "type": "INTEGER", "description": "開催日目", "example": "8", "nullable": False},
            {"name": "レース番号", "type": "INTEGER", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "発表月日時分", "example": "06010930", "nullable": True},
            {"name": "馬番", "type": "INTEGER", "description": "該当馬番", "example": "3", "nullable": False},
            {"name": "馬名", "type": "TEXT", "description": "該当馬名", "example": "テストホース", "nullable": True},
            {"name": "事由区分", "type": "TEXT", "description": "事由区分（001=疾病、002=事故、003=その他）", "example": "001", "nullable": True},
            {"name": "レコード区切り", "type": "TEXT", "description": "レコード区切り文字", "example": "\\r\\n", "nullable": True}
        ],
        "primary_key": ["開催年", "開催月日", "競馬場コード", "開催回", "開催日目", "レース番号", "馬番"],
        "indexes": ["開催年", "開催月日", "競馬場コード", "レース番号"]
    },

    "NL_CC": {
        "table_name": "NL_CC",
        "record_type": "CC",
        "description": "コース変更情報",
        "purpose": "レースのコース（距離・トラック種別）変更情報を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'CC'）", "example": "CC", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "変更後_距離", "type": "TEXT", "description": "変更後の距離（メートル）", "example": "2000", "nullable": True},
            {"name": "変更後_トラックコード", "type": "TEXT", "description": "変更後のトラック（10-23=芝、24-29=ダート）", "example": "10", "nullable": True},
            {"name": "変更前_距離", "type": "TEXT", "description": "変更前の距離", "example": "2400", "nullable": True},
            {"name": "変更前_トラックコード", "type": "TEXT", "description": "変更前のトラック", "example": "10", "nullable": True},
            {"name": "事由区分", "type": "TEXT", "description": "変更理由", "example": "1", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日"]
    },

    "NL_DM": {
        "table_name": "NL_DM",
        "record_type": "DM",
        "description": "タイム型データマイニング予想",
        "purpose": "公式DM予想を1レース・1馬ごとの行へ展開して格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'DM'）", "example": "DM", "nullable": False},
            {"name": "データ区分", "type": "TEXT", "description": "1=前日、2=当日、3=直前、7=成績、0=削除", "example": "3", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "開催回", "type": "INTEGER", "description": "第N回開催", "example": "3", "nullable": False},
            {"name": "開催日目", "type": "INTEGER", "description": "N日目", "example": "8", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "馬番", "type": "TEXT", "description": "馬番", "example": "05", "nullable": False},
            {"name": "予想走破タイム", "type": "TEXT", "description": "公式5桁表現（9分99秒99）", "example": "10501", "nullable": False},
            {"name": "予想誤差＋", "type": "TEXT", "description": "早くなる方向の百分秒4桁", "example": "0101", "nullable": False},
            {"name": "予想誤差－", "type": "TEXT", "description": "遅くなる方向の百分秒4桁", "example": "0201", "nullable": False}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "開催回", "開催日目", "レース番号", "馬番"],
        "indexes": ["開催年月日"]
    },

    "NL_JC": _schema_backed_metadata(
        "NL_JC",
        record_type="JC",
        description="騎手変更詳細情報",
        purpose=(
            "開催6列・発表月日時分・馬番の公式8列キーで複数の騎手変更発表を"
            "共存させ、負担重量はkgへ正規化して格納"
        ),
        indexes=["Year", "MonthDay", "JyoCD", "RaceNum", "HappyoTime"],
    ),

    "NL_JG": _schema_backed_metadata(
        "NL_JG",
        record_type="JG",
        description="競走馬除外情報",
        purpose=(
            "出馬投票で受け付けた馬ごとの出走区分・除外状態区分を、公式8列キー"
            "（開催キー6列＋血統登録番号＋出馬投票受付順番）で格納"
        ),
        indexes=["Year", "MonthDay", "JyoCD", "RaceNum"],
    ),

    "NL_TC": {
        "table_name": "NL_TC",
        "record_type": "TC",
        "description": "発走時刻変更情報",
        "purpose": "レースの発走時刻変更情報を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'TC'）", "example": "TC", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "変更後_発走時刻", "type": "TEXT", "description": "変更後の発走時刻（HHmm形式）", "example": "1530", "nullable": True},
            {"name": "変更前_発走時刻", "type": "TEXT", "description": "変更前の発走時刻", "example": "1520", "nullable": True},
            {"name": "発表月日時分", "type": "TEXT", "description": "変更発表日時", "example": "06011200", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日"]
    },

    "NL_WE": _schema_backed_metadata(
        "NL_WE",
        record_type="WE",
        description="天候・馬場状態変更情報",
        purpose=(
            "開催・発表月日時分・変更識別の公式7要素キーで、初期値と複数の"
            "天候・馬場発表履歴を共存させる"
        ),
        indexes=[],
    ),

    "NL_WH": {
        "table_name": "NL_WH",
        "record_type": "WH",
        "description": "馬体重情報",
        "purpose": "速報馬体重の18頭配列を馬ごとの最新行として格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'WH'）", "example": "WH", "nullable": False},
            {"name": "開催年", "type": "INTEGER", "description": "レース開催年", "example": "2024", "nullable": False},
            {"name": "開催月日", "type": "INTEGER", "description": "レース開催月日（MMDD）", "example": "601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "開催回", "type": "INTEGER", "description": "第N回開催", "example": "3", "nullable": False},
            {"name": "開催日目", "type": "INTEGER", "description": "第N日目", "example": "8", "nullable": False},
            {"name": "レース番号", "type": "INTEGER", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "体重発表日時（MMDDhhmm）", "example": "06011000", "nullable": True},
            {"name": "馬番", "type": "INTEGER", "description": "馬番（01〜18）", "example": "1", "nullable": False},
            {"name": "馬名", "type": "TEXT", "description": "馬名", "example": "テストホース", "nullable": True},
            {"name": "馬体重", "type": "INTEGER", "description": "馬体重kg（000=出走取消、999=計量不能）", "example": "480", "nullable": True},
            {"name": "増減符号", "type": "TEXT", "description": "増加+、減少-、その他は空白", "example": "+", "nullable": True},
            {"name": "増減差", "type": "INTEGER", "description": "増減kg（000=前差なし、999=計量不能）", "example": "5", "nullable": True}
        ],
        "primary_key": ["開催年", "開催月日", "競馬場コード", "開催回", "開催日目", "レース番号", "馬番"],
        "indexes": ["開催年", "開催月日", "競馬場コード", "レース番号", "発表月日時分"]
    },

    # 払戻・配当情報テーブル (Payoff Tables)
    "NL_H1": {
        "table_name": "NL_H1",
        "record_type": "H1",
        "description": "票数1（全賭式）情報",
        "purpose": "単勝・複勝・枠連・馬連・ワイド・馬単・3連複の票数と人気順を組番ごとに格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'H1'）", "example": "H1", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "賭式", "type": "TEXT", "description": "展開後の賭式", "example": "Tansyo", "nullable": False},
            {"name": "組番", "type": "TEXT", "description": "賭式ごとの馬番・組番", "example": "0102", "nullable": False},
            {"name": "票数", "type": "BIGINT", "description": "該当組番の投票数", "example": "12345", "nullable": True},
            {"name": "人気", "type": "INTEGER", "description": "該当組番の人気順", "example": "1", "nullable": True},
            {"name": "単勝票数合計", "type": "TEXT", "description": "単勝総投票数", "example": "1234567", "nullable": True},
            {"name": "複勝票数合計", "type": "TEXT", "description": "複勝総投票数", "example": "987654", "nullable": True},
            {"name": "返還馬番情報", "type": "TEXT", "description": "返還対象馬番リスト", "example": "03,07", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "賭式", "組番"],
        "indexes": ["開催年月日"]
    },

    "NL_H6": {
        "table_name": "NL_H6",
        "record_type": "H6",
        "description": "票数6（三連単）情報",
        "purpose": "三連単の票数と人気順を組番ごとに格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'H6'）", "example": "H6", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "三連単組番", "type": "TEXT", "description": "三連単の組番", "example": "010203", "nullable": False},
            {"name": "三連単票数", "type": "BIGINT", "description": "該当組番の投票数", "example": "12345", "nullable": True},
            {"name": "三連単人気", "type": "INTEGER", "description": "該当組番の人気順", "example": "1", "nullable": True},
            {"name": "三連単票数合計", "type": "BIGINT", "description": "三連単総投票数", "example": "5678901", "nullable": True},
            {"name": "三連単返還票数合計", "type": "BIGINT", "description": "三連単返還票数合計", "example": "0", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "三連単組番"],
        "indexes": ["開催年月日"]
    },

    # その他補足情報テーブル (Supplementary Tables)
    "NL_CK": {
        "table_name": "NL_CK",
        "record_type": "CK",
        "description": "競走馬詳細成績情報",
        "purpose": "各レースにおける馬の詳細成績と調教師・馬主・生産者情報を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'CK'）", "example": "CK", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "血統登録番号", "type": "TEXT", "description": "馬の血統登録番号", "example": "2020123456", "nullable": False},
            {"name": "累計獲得賞金", "type": "TEXT", "description": "通算獲得賞金（円）", "example": "123456789", "nullable": True},
            {"name": "脚質傾向", "type": "TEXT", "description": "脚質（1=逃げ、2=先行、3=差し、4=追込）", "example": "2", "nullable": True},
            {"name": "調教師コード", "type": "TEXT", "description": "担当調教師コード", "example": "01234", "nullable": True},
            {"name": "馬主コード", "type": "TEXT", "description": "馬主コード", "example": "012345", "nullable": True},
            {"name": "生産者コード", "type": "TEXT", "description": "生産者コード", "example": "098765", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "血統登録番号"],
        "indexes": ["開催年月日", "血統登録番号"]
    },

    "NL_CS": _schema_backed_metadata(
        "NL_CS",
        record_type="CS",
        description="コース仕様情報",
        purpose=(
            "競馬場・距離・トラック・改修後初開催日の公式キーごとに、"
            "6,800バイトのコース説明を格納"
        ),
        indexes=["JyoCD", "Kyori"],
    ),

    "NL_HC": {
        "table_name": "NL_HC",
        "record_type": "HC",
        "description": "調教タイム情報",
        "purpose": "坂路調教時の走破タイムとラップタイムを格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'HC'）", "example": "HC", "nullable": False},
            {"name": "データ区分", "type": "TEXT", "description": "データ区分", "example": "1", "nullable": False},
            {"name": "データ作成年月日", "type": "TEXT", "description": "データ作成日", "example": "20240525", "nullable": False},
            {"name": "トレセン区分", "type": "TEXT", "description": "トレーニングセンター（0=美浦、1=栗東）", "example": "1", "nullable": False},
            {"name": "調教年月日", "type": "TEXT", "description": "調教実施日", "example": "20240525", "nullable": False},
            {"name": "調教時刻", "type": "TEXT", "description": "調教実施時刻", "example": "0630", "nullable": False},
            {"name": "血統登録番号", "type": "TEXT", "description": "馬の血統登録番号", "example": "2020123456", "nullable": False},
            {"name": "4F走破タイム", "type": "REAL", "description": "4ハロン走破タイム（秒）", "example": "52.3", "nullable": True},
            {"name": "800M-600Mラップ", "type": "REAL", "description": "800M～600Mのラップタイム（秒）", "example": "13.8", "nullable": True},
            {"name": "3F走破タイム", "type": "REAL", "description": "3ハロン走破タイム（秒）", "example": "38.5", "nullable": True},
            {"name": "600M-400Mラップ", "type": "REAL", "description": "600M～400Mのラップタイム（秒）", "example": "13.0", "nullable": True},
            {"name": "2F走破タイム", "type": "REAL", "description": "2ハロン走破タイム（秒）", "example": "25.5", "nullable": True},
            {"name": "400M-200Mラップ", "type": "REAL", "description": "400M～200Mのラップタイム（秒）", "example": "12.8", "nullable": True},
            {"name": "200M-0Mラップ", "type": "REAL", "description": "200M～0Mのラップタイム（秒）", "example": "12.7", "nullable": True}
        ],
        "primary_key": ["トレセン区分", "調教年月日", "調教時刻", "血統登録番号"],
        "indexes": ["血統登録番号", "調教年月日"]
    },

    "NL_HS": {
        "table_name": "NL_HS",
        "record_type": "HS",
        "description": "競走馬市場取引価格情報",
        "purpose": "競走馬の市場取引価格、セール主催者、市場名、開催期間を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'HS'）", "example": "HS", "nullable": False},
            {"name": "データ区分", "type": "TEXT", "description": "データ区分", "example": "1", "nullable": False},
            {"name": "データ作成年月日", "type": "TEXT", "description": "データ作成日", "example": "20240601", "nullable": False},
            {"name": "血統登録番号", "type": "TEXT", "description": "馬の血統登録番号", "example": "2020123456", "nullable": False},
            {"name": "父馬繁殖登録番号", "type": "TEXT", "description": "父馬の繁殖登録番号", "example": "1234567890", "nullable": True},
            {"name": "母馬繁殖登録番号", "type": "TEXT", "description": "母馬の繁殖登録番号", "example": "0987654321", "nullable": True},
            {"name": "生年", "type": "TEXT", "description": "生年", "example": "2021", "nullable": True},
            {"name": "主催者・市場コード", "type": "TEXT", "description": "主催者・市場コード", "example": "000001", "nullable": False},
            {"name": "セール主催者名", "type": "TEXT", "description": "セール主催者名", "example": "JRAブリーズアップセール", "nullable": True},
            {"name": "セール名", "type": "TEXT", "description": "市場の名称", "example": "2024 JRAブリーズアップセール", "nullable": True},
            {"name": "市場開始日", "type": "TEXT", "description": "市場の開催期間開始日", "example": "20240423", "nullable": False},
            {"name": "市場終了日", "type": "TEXT", "description": "市場の開催期間終了日", "example": "20240423", "nullable": True},
            {"name": "馬齢", "type": "INTEGER", "description": "取引時の競走馬の年齢", "example": "2", "nullable": True},
            {"name": "取引価格", "type": "BIGINT", "description": "取引価格", "example": "12000000", "nullable": True}
        ],
        "primary_key": ["血統登録番号", "主催者・市場コード", "市場開始日"],
        "indexes": ["血統登録番号", "主催者・市場コード", "市場開始日"]
    },

    "NL_HY": {
        "table_name": "NL_HY",
        "record_type": "HY",
        "description": "馬名意味由来情報",
        "purpose": "馬名の意味・由来を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'HY'）", "example": "HY", "nullable": False},
            {"name": "血統登録番号", "type": "TEXT", "description": "馬の血統登録番号", "example": "2020123456", "nullable": False},
            {"name": "馬名", "type": "TEXT", "description": "馬名", "example": "ディープインパクト", "nullable": True},
            {"name": "馬名の意味由来", "type": "TEXT", "description": "馬名の意味・由来の説明", "example": "深い衝撃という意味", "nullable": True}
        ],
        "primary_key": ["血統登録番号"],
        "indexes": ["血統登録番号", "馬名"]
    },

    "NL_RC": {
        "table_name": "NL_RC",
        "record_type": "RC",
        "description": "レコードマスタ",
        "purpose": "コース・G1レコード履歴と最大3頭の同着保持馬情報を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'RC'）", "example": "RC", "nullable": False},
            {"name": "レコード識別区分", "type": "TEXT", "description": "1:コース、2:G1", "example": "1", "nullable": False},
            {"name": "開催年", "type": "INTEGER", "description": "レコード樹立レースの開催年", "example": "2026", "nullable": False},
            {"name": "開催月日", "type": "INTEGER", "description": "レコード樹立レースの開催月日", "example": "816", "nullable": False},
            {"name": "特別競走番号", "type": "TEXT", "description": "G1レコードの識別番号", "example": "1234", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "開催回", "type": "INTEGER", "description": "開催回", "example": "3", "nullable": False},
            {"name": "開催日目", "type": "INTEGER", "description": "開催日目", "example": "8", "nullable": False},
            {"name": "レース番号", "type": "INTEGER", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "競走種別コード", "type": "TEXT", "description": "競走年齢・障害区分", "example": "13", "nullable": False},
            {"name": "距離", "type": "INTEGER", "description": "コース距離", "example": "2400", "nullable": False},
            {"name": "トラックコード", "type": "TEXT", "description": "トラック種別", "example": "10", "nullable": False},
            {"name": "レコードタイム", "type": "TEXT", "description": "公式4桁のレコードタイム", "example": "2221", "nullable": True},
            {"name": "レコード保持馬1～3", "type": "TEXT", "description": "同着を含む全保持馬・調教師・負担重量・騎手", "example": "○○○○", "nullable": True}
        ],
        "primary_key": ["レコード識別区分", "開催年", "開催月日", "競馬場コード", "開催回", "開催日目", "レース番号", "特別競走番号", "競走種別コード", "距離", "トラックコード"],
        "indexes": ["競馬場コード"]
    },

    "NL_SK": _schema_backed_metadata(
        "NL_SK",
        record_type="SK",
        description="馬3代血統詳細情報",
        purpose="競走馬の3代血統（父母・祖父母・曽祖父母）詳細を格納",
        indexes=["KettoNum", "FNum", "MNum"],
    ),

    "NL_TK_RACE": _schema_backed_metadata(
        "NL_TK_RACE",
        record_type="TK",
        description="特別登録馬レースヘッダー",
        purpose="ハンデ発表前後の特別登録レース情報と登録頭数を格納",
        indexes=["Year", "MonthDay", "JyoCD", "RaceNum"],
    ),
    "NL_TK": _schema_backed_metadata(
        "NL_TK",
        record_type="TK",
        description="特別登録馬明細",
        purpose="特別登録レースごとの全登録馬を公式連番単位で格納",
        indexes=["Year", "MonthDay", "JyoCD", "RaceNum", "KettoNum"],
    ),

    "NL_TM": {
        "table_name": "NL_TM",
        "record_type": "TM",
        "description": "対戦型データマイニング予想情報",
        "purpose": "馬ごとの対戦型予測スコアを格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'TM'）", "example": "TM", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "開催回", "type": "INTEGER", "description": "その競馬場での開催回", "example": "3", "nullable": False},
            {"name": "開催日目", "type": "INTEGER", "description": "開催回内の日次", "example": "8", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "データ作成時分", "type": "TEXT", "description": "データ作成時分", "example": "0900", "nullable": True},
            {"name": "馬番", "type": "INTEGER", "description": "該当馬番", "example": "01", "nullable": False},
            {"name": "予測スコア", "type": "TEXT", "description": "小数点を省略した4桁の対戦型予測スコア", "example": "0753", "nullable": False}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "開催回", "開催日目", "レース番号", "馬番"],
        "indexes": ["開催年月日"]
    },

    "NL_WC": _schema_backed_metadata(
        "NL_WC",
        record_type="WC",
        description="ウッドチップ調教詳細タイム情報",
        purpose=(
            "トレセン・調教日時・血統登録番号を公式キーとして、200m刻みの"
            "全ラップタイムを格納"
        ),
        indexes=["KettoNum", "ChokyoDate"],
    ),

    "NL_WF": _schema_backed_metadata(
        "NL_WF",
        record_type="WF",
        description="重勝式（WIN5）発売・払戻情報",
        purpose=(
            "開催年・開催月日を公式キーとして、対象5レース、発売票数、有効票数5件、"
            "各フラグ、キャリーオーバー金額、払戻情報243枠（PayoutsJson）を1行で格納"
        ),
        indexes=["Year", "MonthDay"],
    ),

    # 速報系テーブル (Realtime Tables) - リアルタイム更新用
    "RT_AV": {
        "table_name": "RT_AV",
        "record_type": "AV",
        "description": "出走取消・競走除外情報（速報）",
        "purpose": "リアルタイムでの出走取消・競走除外情報を格納（NL_AVと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'AV'）", "example": "AV", "nullable": False},
            {"name": "データ区分", "type": "TEXT", "description": "データ区分（1=出走取消、2=競走除外）", "example": "1", "nullable": False},
            {"name": "データ作成年月日", "type": "TEXT", "description": "データ作成日", "example": "20240601", "nullable": False},
            {"name": "開催年", "type": "INTEGER", "description": "開催年", "example": "2024", "nullable": False},
            {"name": "開催月日", "type": "INTEGER", "description": "開催月日", "example": "0601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "開催回", "type": "INTEGER", "description": "開催回", "example": "3", "nullable": False},
            {"name": "開催日目", "type": "INTEGER", "description": "開催日目", "example": "8", "nullable": False},
            {"name": "レース番号", "type": "INTEGER", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "発表月日時分", "example": "06010930", "nullable": True},
            {"name": "馬番", "type": "INTEGER", "description": "該当馬番", "example": "3", "nullable": False},
            {"name": "馬名", "type": "TEXT", "description": "該当馬名", "example": "テストホース", "nullable": True},
            {"name": "事由区分", "type": "TEXT", "description": "事由区分（001=疾病、002=事故、003=その他）", "example": "001", "nullable": True},
            {"name": "レコード区切り", "type": "TEXT", "description": "レコード区切り文字", "example": "\\r\\n", "nullable": True}
        ],
        "primary_key": ["開催年", "開催月日", "競馬場コード", "開催回", "開催日目", "レース番号", "馬番"],
        "indexes": ["開催年", "開催月日", "競馬場コード", "レース番号"]
    },

    "RT_CC": {
        "table_name": "RT_CC",
        "record_type": "CC",
        "description": "コース変更情報（速報）",
        "purpose": "リアルタイムでのコース変更情報を格納（NL_CCと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'CC'）", "example": "CC", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "変更後_距離", "type": "TEXT", "description": "変更後の距離", "example": "2000", "nullable": True},
            {"name": "変更後_トラックコード", "type": "TEXT", "description": "変更後のトラック", "example": "10", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日"]
    },

    "RT_DM": {
        "table_name": "RT_DM",
        "record_type": "DM",
        "description": "タイム型データマイニング予想（速報）",
        "purpose": "0B13の公式DM予想を1レース・1馬ごとの行へ展開して格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'DM'）", "example": "DM", "nullable": False},
            {"name": "データ区分", "type": "TEXT", "description": "1=前日、2=当日、3=直前、0=削除", "example": "3", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "開催回", "type": "INTEGER", "description": "第N回開催", "example": "3", "nullable": False},
            {"name": "開催日目", "type": "INTEGER", "description": "N日目", "example": "8", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "馬番", "type": "TEXT", "description": "馬番", "example": "05", "nullable": False},
            {"name": "予想走破タイム", "type": "TEXT", "description": "公式5桁表現（9分99秒99）", "example": "10501", "nullable": False},
            {"name": "予想誤差＋", "type": "TEXT", "description": "早くなる方向の百分秒4桁", "example": "0101", "nullable": False},
            {"name": "予想誤差－", "type": "TEXT", "description": "遅くなる方向の百分秒4桁", "example": "0201", "nullable": False}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "開催回", "開催日目", "レース番号", "馬番"],
        "indexes": ["開催年月日"]
    },

    "RT_H1": {
        "table_name": "RT_H1",
        "record_type": "H1",
        "description": "票数1（全賭式）情報（速報）",
        "purpose": "リアルタイムでの票数1情報を格納（NL_H1と同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'H1'）", "example": "H1", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "賭式", "type": "TEXT", "description": "展開後の賭式", "example": "Tansyo", "nullable": False},
            {"name": "組番", "type": "TEXT", "description": "賭式ごとの馬番・組番", "example": "0102", "nullable": False},
            {"name": "票数", "type": "BIGINT", "description": "該当組番の投票数", "example": "12345", "nullable": True},
            {"name": "人気", "type": "INTEGER", "description": "該当組番の人気順", "example": "1", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "賭式", "組番"],
        "indexes": ["開催年月日"]
    },

    "RT_H6": {
        "table_name": "RT_H6",
        "record_type": "H6",
        "description": "票数6（三連単）情報（速報）",
        "purpose": "リアルタイムでの三連単票数情報を格納（NL_H6と同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'H6'）", "example": "H6", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "三連単組番", "type": "TEXT", "description": "三連単の組番", "example": "010203", "nullable": False},
            {"name": "三連単票数", "type": "BIGINT", "description": "該当組番の投票数", "example": "12345", "nullable": True},
            {"name": "三連単人気", "type": "INTEGER", "description": "該当組番の人気順", "example": "1", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "三連単組番"],
        "indexes": ["開催年月日"]
    },

    "RT_HR": {
        "table_name": "RT_HR",
        "record_type": "HR",
        "description": "払戻情報（速報）",
        "purpose": "リアルタイムでの全払戻情報を格納（NL_HRと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'HR'）", "example": "HR", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "単勝払戻金", "type": "TEXT", "description": "単勝払戻金", "example": "350", "nullable": True},
            {"name": "複勝払戻金", "type": "TEXT", "description": "複勝払戻金", "example": "120,150,180", "nullable": True},
            {"name": "枠連払戻金", "type": "TEXT", "description": "枠連払戻金", "example": "1230", "nullable": True},
            {"name": "馬連払戻金", "type": "TEXT", "description": "馬連払戻金", "example": "4560", "nullable": True},
            {"name": "ワイド払戻金", "type": "TEXT", "description": "ワイド払戻金", "example": "250,320,450", "nullable": True},
            {"name": "馬単払戻金", "type": "TEXT", "description": "馬単払戻金", "example": "12340", "nullable": True},
            {"name": "3連複払戻金", "type": "TEXT", "description": "3連複払戻金", "example": "4567", "nullable": True},
            {"name": "3連単払戻金", "type": "TEXT", "description": "3連単払戻金", "example": "123450", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日"]
    },

    "RT_JC": _schema_backed_metadata(
        "RT_JC",
        record_type="JC",
        description="騎手変更詳細情報（速報）",
        purpose=(
            "0B14/0B16の騎手変更発表を公式8列キーで格納し、同一馬の複数発表を"
            "発表月日時分ごとに保持"
        ),
        indexes=["Year", "MonthDay", "JyoCD", "RaceNum", "HappyoTime"],
    ),

    "RT_O1": {
        "table_name": "RT_O1",
        "record_type": "O1",
        "description": "単勝・複勝・枠連オッズ情報（速報）",
        "purpose": "リアルタイムでの単勝・複勝・枠連オッズを格納（NL_O1と同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'O1'）", "example": "O1", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "オッズ発表時刻", "example": "06011430", "nullable": False},
            {"name": "単勝オッズ", "type": "TEXT", "description": "単勝オッズ", "example": "3.5", "nullable": True},
            {"name": "複勝オッズ", "type": "TEXT", "description": "複勝オッズ", "example": "1.2-1.5", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "馬番", "組番"],
        "indexes": ["開催年月日", "発表月日時分"]
    },

    "RT_O2": {
        "table_name": "RT_O2",
        "record_type": "O2",
        "description": "馬連オッズ情報（速報）",
        "purpose": "リアルタイムでの馬連オッズを格納（NL_O2と同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'O2'）", "example": "O2", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "オッズ発表時刻", "example": "06011430", "nullable": False},
            {"name": "馬連オッズ", "type": "TEXT", "description": "馬連オッズ", "example": "45.6", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "組番"],
        "indexes": ["開催年月日"]
    },

    "RT_O3": {
        "table_name": "RT_O3",
        "record_type": "O3",
        "description": "ワイドオッズ情報（速報）",
        "purpose": "リアルタイムでのワイドオッズを格納（NL_O3と同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'O3'）", "example": "O3", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "オッズ発表時刻", "example": "06011430", "nullable": False},
            {"name": "ワイドオッズ", "type": "TEXT", "description": "ワイドオッズ", "example": "2.5-3.2", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "組番"],
        "indexes": ["開催年月日"]
    },

    "RT_O4": {
        "table_name": "RT_O4",
        "record_type": "O4",
        "description": "馬単オッズ情報（速報）",
        "purpose": "リアルタイムでの馬単オッズを格納（NL_O4と同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'O4'）", "example": "O4", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "オッズ発表時刻", "example": "06011430", "nullable": False},
            {"name": "馬単オッズ", "type": "TEXT", "description": "馬単オッズ", "example": "123.4", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "組番"],
        "indexes": ["開催年月日"]
    },

    "RT_O5": {
        "table_name": "RT_O5",
        "record_type": "O5",
        "description": "3連複オッズ情報（速報）",
        "purpose": "リアルタイムでの3連複オッズを格納（NL_O5と同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'O5'）", "example": "O5", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "オッズ発表時刻", "example": "06011430", "nullable": False},
            {"name": "3連複オッズ", "type": "TEXT", "description": "3連複オッズ", "example": "456.7", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "組番"],
        "indexes": ["開催年月日"]
    },

    "RT_O6": {
        "table_name": "RT_O6",
        "record_type": "O6",
        "description": "3連単オッズ情報（速報）",
        "purpose": "リアルタイムでの3連単オッズを格納（NL_O6と同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'O6'）", "example": "O6", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "オッズ発表時刻", "example": "06011430", "nullable": False},
            {"name": "3連単オッズ", "type": "TEXT", "description": "3連単オッズ", "example": "12345.6", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "組番"],
        "indexes": ["開催年月日"]
    },

    "RT_RA": {
        "table_name": "RT_RA",
        "record_type": "RA",
        "description": "レース詳細情報（速報）",
        "purpose": "リアルタイムでのレース詳細情報を格納（NL_RAと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'RA'）", "example": "RA", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "レース名", "type": "TEXT", "description": "レース名称", "example": "東京優駿（日本ダービー）", "nullable": True},
            {"name": "グレードコード", "type": "TEXT", "description": "グレード", "example": "A", "nullable": True},
            {"name": "距離", "type": "TEXT", "description": "レース距離", "example": "2400", "nullable": False},
            {"name": "発走時刻", "type": "TEXT", "description": "発走時刻", "example": "1540", "nullable": True},
            {"name": "天候コード", "type": "TEXT", "description": "天候", "example": "1", "nullable": True},
            {"name": "馬場状態コード", "type": "TEXT", "description": "馬場状態", "example": "1", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日", "グレードコード"]
    },

    "RT_SE": {
        "table_name": "RT_SE",
        "record_type": "SE",
        "description": "馬毎レース情報（速報）",
        "purpose": "リアルタイムでの馬毎レース結果を格納（NL_SEと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'SE'）", "example": "SE", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "馬番", "type": "TEXT", "description": "馬番", "example": "05", "nullable": False},
            {"name": "血統登録番号", "type": "TEXT", "description": "血統登録番号", "example": "2020123456", "nullable": False},
            {"name": "馬名", "type": "TEXT", "description": "馬名", "example": "○○○○", "nullable": True},
            {"name": "確定着順", "type": "TEXT", "description": "確定着順", "example": "01", "nullable": True},
            {"name": "走破タイム", "type": "TEXT", "description": "走破タイム", "example": "2:22.1", "nullable": True},
            {"name": "単勝オッズ", "type": "TEXT", "description": "単勝オッズ", "example": "3.5", "nullable": True},
            {"name": "単勝人気順", "type": "TEXT", "description": "単勝人気順位", "example": "02", "nullable": True}
        ],
        "primary_key": [
            "Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji",
            "RaceNum", "Umaban", "KettoNum"
        ],
        "indexes": ["開催年月日", "血統登録番号", "確定着順"]
    },

    "RT_TC": {
        "table_name": "RT_TC",
        "record_type": "TC",
        "description": "発走時刻変更情報（速報）",
        "purpose": "リアルタイムでの発走時刻変更情報を格納（NL_TCと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'TC'）", "example": "TC", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "変更後_発走時刻", "type": "TEXT", "description": "変更後の発走時刻", "example": "1530", "nullable": True},
            {"name": "変更前_発走時刻", "type": "TEXT", "description": "変更前の発走時刻", "example": "1520", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日"]
    },

    "RT_TM": {
        "table_name": "RT_TM",
        "record_type": "TM",
        "description": "対戦型データマイニング予想情報（速報）",
        "purpose": "速報の馬ごとの対戦型予測スコアを格納（NL_TMと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'TM'）", "example": "TM", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "開催回", "type": "INTEGER", "description": "その競馬場での開催回", "example": "3", "nullable": False},
            {"name": "開催日目", "type": "INTEGER", "description": "開催回内の日次", "example": "8", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "馬番", "type": "INTEGER", "description": "該当馬番", "example": "01", "nullable": False},
            {"name": "予測スコア", "type": "TEXT", "description": "小数点を省略した4桁の対戦型予測スコア", "example": "0753", "nullable": False}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "開催回", "開催日目", "レース番号", "馬番"],
        "indexes": ["開催年月日"]
    },

    "RT_WE": _schema_backed_metadata(
        "RT_WE",
        record_type="WE",
        description="天候・馬場状態変更情報（速報）",
        purpose=(
            "NL_WEと同じ公式7要素キーで、発表時刻ごとの速報天候・馬場状態を格納"
        ),
        indexes=[],
    ),

    "RT_WF": _schema_backed_metadata(
        "RT_WF",
        record_type="WF",
        description="重勝式（WIN5）発売・払戻情報（速報）",
        purpose=(
            "0B51 速報重勝式を開催年・開催月日をキーに1行で格納（NL_WFと同構造）。"
            "データ区分9の中止状態は保持し、0のみ物理削除"
        ),
        indexes=["Year", "MonthDay"],
    ),

    "RT_WH": {
        "table_name": "RT_WH",
        "record_type": "WH",
        "description": "馬体重情報（速報）",
        "purpose": "リアルタイムの18頭馬体重配列を馬ごとの最新行として格納（NL_WHと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'WH'）", "example": "WH", "nullable": False},
            {"name": "開催年", "type": "INTEGER", "description": "レース開催年", "example": "2024", "nullable": False},
            {"name": "開催月日", "type": "INTEGER", "description": "レース開催月日（MMDD）", "example": "601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "開催回", "type": "INTEGER", "description": "第N回開催", "example": "3", "nullable": False},
            {"name": "開催日目", "type": "INTEGER", "description": "第N日目", "example": "8", "nullable": False},
            {"name": "レース番号", "type": "INTEGER", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "体重発表日時（MMDDhhmm）", "example": "06011000", "nullable": True},
            {"name": "馬番", "type": "INTEGER", "description": "馬番（01〜18）", "example": "1", "nullable": False},
            {"name": "馬名", "type": "TEXT", "description": "馬名", "example": "テストホース", "nullable": True},
            {"name": "馬体重", "type": "INTEGER", "description": "馬体重kg（000=出走取消、999=計量不能）", "example": "480", "nullable": True},
            {"name": "増減符号", "type": "TEXT", "description": "増加+、減少-、その他は空白", "example": "+", "nullable": True},
            {"name": "増減差", "type": "INTEGER", "description": "増減kg（000=前差なし、999=計量不能）", "example": "5", "nullable": True}
        ],
        "primary_key": ["開催年", "開催月日", "競馬場コード", "開催回", "開催日目", "レース番号", "馬番"],
        "indexes": ["開催年", "開催月日", "競馬場コード", "レース番号", "発表月日時分"]
    },
    "RT_RC": {
        "table_name": "RT_RC",
        "record_type": "RC",
        "description": "騎手変更情報（速報）",
        "purpose": "リアルタイムでの騎手変更情報を格納",
        "columns": [
            {"name": "RecordSpec", "type": "TEXT", "description": "レコード種別識別子", "example": "RC", "nullable": False},
            {"name": "Year", "type": "INTEGER", "description": "開催年", "example": "2024", "nullable": False},
            {"name": "MonthDay", "type": "INTEGER", "description": "月日（MMDD形式）", "example": "601", "nullable": False},
            {"name": "JyoCD", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "RaceNum", "type": "INTEGER", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "Umaban", "type": "TEXT", "description": "馬番", "example": "01", "nullable": False},
            {"name": "KisyuCode", "type": "TEXT", "description": "変更後騎手コード", "example": "01234", "nullable": True},
            {"name": "KisyuName", "type": "TEXT", "description": "変更後騎手名", "example": "ルメール", "nullable": True},
            {"name": "MaeKisyuCode", "type": "TEXT", "description": "変更前騎手コード", "example": "01235", "nullable": True},
            {"name": "MaeKisyuName", "type": "TEXT", "description": "変更前騎手名", "example": "武豊", "nullable": True}
        ],
        "primary_key": ["Year", "MonthDay", "JyoCD", "RaceNum", "Umaban"],
        "indexes": ["Year", "MonthDay"]
    },
    "TS_O1": {
        "table_name": "TS_O1",
        "record_type": "O1",
        "description": "単勝・複勝・枠連オッズ（時系列）",
        "purpose": "単勝・複勝・枠連オッズの時間推移を記録するテーブル。HassoTimeをキーに含め複数時点のデータを保持",
        "columns": [
            {"name": "RecordSpec", "type": "TEXT", "description": "レコード種別識別子", "example": "O1", "nullable": False},
            {"name": "Year", "type": "INTEGER", "description": "開催年", "example": "2024", "nullable": False},
            {"name": "MonthDay", "type": "INTEGER", "description": "月日（MMDD形式）", "example": "601", "nullable": False},
            {"name": "JyoCD", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "RaceNum", "type": "INTEGER", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "HassoTime", "type": "TEXT", "description": "発走時刻", "example": "1540", "nullable": False},
            {"name": "Umaban", "type": "INTEGER", "description": "馬番", "example": "1", "nullable": False},
            {"name": "TanOdds", "type": "REAL", "description": "単勝オッズ", "example": "3.5", "nullable": True},
            {"name": "TanNinki", "type": "INTEGER", "description": "単勝人気順", "example": "1", "nullable": True},
            {"name": "CollectedAt", "type": "TEXT", "description": "collector保存時刻（UTC ISO-8601）", "example": "2026-05-10T12:34:56.789012+00:00", "nullable": True}
        ],
        "primary_key": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban", "Kumi", "HassoTime"],
        "indexes": ["Year", "MonthDay", "HassoTime"]
    },
    "TS_O2": {
        "table_name": "TS_O2",
        "record_type": "O2",
        "description": "馬連オッズ（時系列）",
        "purpose": "馬連オッズの時間推移を記録するテーブル。HassoTimeをキーに含め複数時点のデータを保持",
        "columns": [
            {"name": "RecordSpec", "type": "TEXT", "description": "レコード種別識別子", "example": "O2", "nullable": False},
            {"name": "Year", "type": "INTEGER", "description": "開催年", "example": "2024", "nullable": False},
            {"name": "MonthDay", "type": "INTEGER", "description": "月日（MMDD形式）", "example": "601", "nullable": False},
            {"name": "JyoCD", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "RaceNum", "type": "INTEGER", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "HassoTime", "type": "TEXT", "description": "発走時刻", "example": "1540", "nullable": False},
            {"name": "Kumi", "type": "TEXT", "description": "組み合わせ", "example": "0102", "nullable": False},
            {"name": "Odds", "type": "REAL", "description": "馬連オッズ", "example": "12.5", "nullable": True},
            {"name": "Ninki", "type": "INTEGER", "description": "人気順", "example": "3", "nullable": True},
            {"name": "CollectedAt", "type": "TEXT", "description": "collector保存時刻（UTC ISO-8601）", "example": "2026-05-10T12:34:56.789012+00:00", "nullable": True}
        ],
        "primary_key": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
        "indexes": ["Year", "MonthDay", "HassoTime"]
    },
    "TS_O3": {
        "table_name": "TS_O3",
        "record_type": "O3",
        "description": "ワイドオッズ（時系列）",
        "purpose": "ワイドオッズの時間推移を記録するテーブル。HassoTimeをキーに含め複数時点のデータを保持",
        "columns": [
            {"name": "RecordSpec", "type": "TEXT", "description": "レコード種別識別子", "example": "O3", "nullable": False},
            {"name": "Year", "type": "INTEGER", "description": "開催年", "example": "2024", "nullable": False},
            {"name": "MonthDay", "type": "INTEGER", "description": "月日（MMDD形式）", "example": "601", "nullable": False},
            {"name": "JyoCD", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "RaceNum", "type": "INTEGER", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "HassoTime", "type": "TEXT", "description": "発走時刻", "example": "1540", "nullable": False},
            {"name": "Kumi", "type": "TEXT", "description": "組み合わせ", "example": "0102", "nullable": False},
            {"name": "OddsLow", "type": "REAL", "description": "ワイドオッズ下限", "example": "2.5", "nullable": True},
            {"name": "OddsHigh", "type": "REAL", "description": "ワイドオッズ上限", "example": "4.5", "nullable": True},
            {"name": "CollectedAt", "type": "TEXT", "description": "collector保存時刻（UTC ISO-8601）", "example": "2026-05-10T12:34:56.789012+00:00", "nullable": True}
        ],
        "primary_key": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
        "indexes": ["Year", "MonthDay", "HassoTime"]
    },
    "TS_O4": {
        "table_name": "TS_O4",
        "record_type": "O4",
        "description": "馬単オッズ（時系列）",
        "purpose": "馬単オッズの時間推移を記録するテーブル。HassoTimeをキーに含め複数時点のデータを保持",
        "columns": [
            {"name": "RecordSpec", "type": "TEXT", "description": "レコード種別識別子", "example": "O4", "nullable": False},
            {"name": "Year", "type": "INTEGER", "description": "開催年", "example": "2024", "nullable": False},
            {"name": "MonthDay", "type": "INTEGER", "description": "月日（MMDD形式）", "example": "601", "nullable": False},
            {"name": "JyoCD", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "RaceNum", "type": "INTEGER", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "HassoTime", "type": "TEXT", "description": "発走時刻", "example": "1540", "nullable": False},
            {"name": "Kumi", "type": "TEXT", "description": "組み合わせ", "example": "0102", "nullable": False},
            {"name": "Odds", "type": "REAL", "description": "馬単オッズ", "example": "25.0", "nullable": True},
            {"name": "Ninki", "type": "INTEGER", "description": "人気順", "example": "5", "nullable": True},
            {"name": "CollectedAt", "type": "TEXT", "description": "collector保存時刻（UTC ISO-8601）", "example": "2026-05-10T12:34:56.789012+00:00", "nullable": True}
        ],
        "primary_key": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
        "indexes": ["Year", "MonthDay", "HassoTime"]
    },
    "TS_O5": {
        "table_name": "TS_O5",
        "record_type": "O5",
        "description": "三連複オッズ（時系列）",
        "purpose": "三連複オッズの時間推移を記録するテーブル。HassoTimeをキーに含め複数時点のデータを保持",
        "columns": [
            {"name": "RecordSpec", "type": "TEXT", "description": "レコード種別識別子", "example": "O5", "nullable": False},
            {"name": "Year", "type": "INTEGER", "description": "開催年", "example": "2024", "nullable": False},
            {"name": "MonthDay", "type": "INTEGER", "description": "月日（MMDD形式）", "example": "601", "nullable": False},
            {"name": "JyoCD", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "RaceNum", "type": "INTEGER", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "HassoTime", "type": "TEXT", "description": "発走時刻", "example": "1540", "nullable": False},
            {"name": "Kumi", "type": "TEXT", "description": "組み合わせ", "example": "010203", "nullable": False},
            {"name": "Odds", "type": "REAL", "description": "三連複オッズ", "example": "45.0", "nullable": True},
            {"name": "Ninki", "type": "INTEGER", "description": "人気順", "example": "8", "nullable": True},
            {"name": "CollectedAt", "type": "TEXT", "description": "collector保存時刻（UTC ISO-8601）", "example": "2026-05-10T12:34:56.789012+00:00", "nullable": True}
        ],
        "primary_key": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
        "indexes": ["Year", "MonthDay", "HassoTime"]
    },
    "TS_O6": {
        "table_name": "TS_O6",
        "record_type": "O6",
        "description": "三連単オッズ（時系列）",
        "purpose": "三連単オッズの時間推移を記録するテーブル。HassoTimeをキーに含め複数時点のデータを保持",
        "columns": [
            {"name": "RecordSpec", "type": "TEXT", "description": "レコード種別識別子", "example": "O6", "nullable": False},
            {"name": "Year", "type": "INTEGER", "description": "開催年", "example": "2024", "nullable": False},
            {"name": "MonthDay", "type": "INTEGER", "description": "月日（MMDD形式）", "example": "601", "nullable": False},
            {"name": "JyoCD", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "RaceNum", "type": "INTEGER", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "HassoTime", "type": "TEXT", "description": "発走時刻", "example": "1540", "nullable": False},
            {"name": "Kumi", "type": "TEXT", "description": "組み合わせ", "example": "010203", "nullable": False},
            {"name": "Odds", "type": "REAL", "description": "三連単オッズ", "example": "150.0", "nullable": True},
            {"name": "Ninki", "type": "INTEGER", "description": "人気順", "example": "15", "nullable": True},
            {"name": "CollectedAt", "type": "TEXT", "description": "collector保存時刻（UTC ISO-8601）", "example": "2026-05-10T12:34:56.789012+00:00", "nullable": True}
        ],
        "primary_key": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
        "indexes": ["Year", "MonthDay", "HassoTime"]
    }
}


def _ensure_column_metadata(table_name: str, column: ColumnMetadata) -> None:
    """Add missing metadata for columns referenced by generated table keys."""

    columns = TABLE_METADATA[table_name]["columns"]
    if not any(existing["name"] == column["name"] for existing in columns):
        columns.append(column)


_KAIJI_COLUMN: ColumnMetadata = {
    "name": "Kaiji",
    "type": "INTEGER",
    "description": "開催回次",
    "example": "3",
    "nullable": False,
}
_NICHIJI_COLUMN: ColumnMetadata = {
    "name": "Nichiji",
    "type": "INTEGER",
    "description": "開催日次",
    "example": "8",
    "nullable": False,
}
_KUMI_COLUMN: ColumnMetadata = {
    "name": "Kumi",
    "type": "TEXT",
    "description": "組み合わせ。単勝・複勝行では主キー安定化のため00を使用",
    "example": "0102",
    "nullable": False,
}
_UMABAN_JA_COLUMN: ColumnMetadata = {
    "name": "馬番",
    "type": "INTEGER",
    "description": "馬番。枠連行では0を使用",
    "example": "1",
    "nullable": False,
}
_KUMI_JA_COLUMN: ColumnMetadata = {
    "name": "組番",
    "type": "TEXT",
    "description": "組み合わせ。単勝・複勝行では00を使用",
    "example": "0102",
    "nullable": False,
}


for _table_name in ("NL_O1", "RT_O1"):
    TABLE_METADATA[_table_name]["primary_key"] = ["開催年月日", "競馬場コード", "レース番号", "馬番", "組番"]
    _ensure_column_metadata(_table_name, _UMABAN_JA_COLUMN)
    _ensure_column_metadata(_table_name, _KUMI_JA_COLUMN)

for _table_name in (
    "NL_O2",
    "NL_O3",
    "NL_O4",
    "NL_O5",
    "NL_O6",
    "RT_O2",
    "RT_O3",
    "RT_O4",
    "RT_O5",
    "RT_O6",
):
    TABLE_METADATA[_table_name]["primary_key"] = ["開催年月日", "競馬場コード", "レース番号", "組番"]
    _ensure_column_metadata(_table_name, _KUMI_JA_COLUMN)


for _table_name in ("TS_O1", "TS_O2", "TS_O3", "TS_O4", "TS_O5", "TS_O6"):
    _ensure_column_metadata(_table_name, _KAIJI_COLUMN)
    _ensure_column_metadata(_table_name, _NICHIJI_COLUMN)
_ensure_column_metadata("TS_O1", _KUMI_COLUMN)


for _source_table, _target_table in (
    ("TS_O1", "TS_SOKUHO_O1"),
    ("TS_O2", "TS_SOKUHO_O2"),
    ("TS_O3", "TS_SOKUHO_O3"),
    ("TS_O4", "TS_SOKUHO_O4"),
    ("TS_O5", "TS_SOKUHO_O5"),
    ("TS_O6", "TS_SOKUHO_O6"),
):
    _metadata = deepcopy(TABLE_METADATA[_source_table])
    _metadata["table_name"] = _target_table
    _metadata["description"] = _metadata["description"].replace("（時系列）", "（速報時系列）")
    _metadata["purpose"] = (
        _metadata["purpose"].replace("時間推移を記録する", "開催週速報オッズの時間推移を記録する")
        + "。SourceSpecをキーに含め、0B30と0B31-0B36の上書きを避ける"
    )
    _metadata["columns"].insert(
        1,
        {
            "name": "SourceSpec",
            "type": "TEXT",
            "description": "取得元データ仕様コード",
            "example": "0B30",
            "nullable": False,
        },
    )
    _metadata["primary_key"] = [*_metadata["primary_key"], "SourceSpec", "CollectedAt"]
    TABLE_METADATA[_target_table] = _metadata


def _ensure_all_executable_metadata() -> None:
    """Create a metadata owner for every executable storage table."""

    for table_name in get_all_executable_tables():
        if table_name in TABLE_METADATA:
            continue

        native_owner = JRAVAN_TO_JLTSQL.get(table_name)
        owner_metadata = TABLE_METADATA.get(native_owner or "")
        record_type = (
            owner_metadata["record_type"]
            if owner_metadata is not None
            else TABLE_TO_RECORD_TYPE.get(table_name, table_name.removeprefix("NL_"))
        )
        if owner_metadata is not None:
            description = f"{owner_metadata['description']}（JRA-VAN標準）"
            purpose = (
                f"{owner_metadata['purpose']}。"
                "JRA-VAN標準レイアウトの実行可能テーブル"
            )
        else:
            description = f"実行可能テーブル {table_name}"
            purpose = "jrvltsqlが作成・参照する実行可能な物理テーブル"

        TABLE_METADATA[table_name] = _schema_backed_metadata(
            table_name,
            record_type=record_type,
            description=description,
            purpose=purpose,
            indexes=[],
        )


_INDEX_COLUMNS_PATTERN = re.compile(
    r'\bON\s+(?P<table>[^\s(]+)\s*\((?P<columns>[^)]*)\)',
    re.IGNORECASE,
)


def _get_executable_index_columns(table_name: str) -> List[str]:
    """Return distinct physical columns referenced by configured SQL indexes."""

    physical_columns = get_table_column_types(table_name)
    result: List[str] = []
    for statement in INDEXES.get(table_name, []):
        match = _INDEX_COLUMNS_PATTERN.search(statement)
        if match is None:
            raise ValueError(f"Unrecognized index definition for {table_name}")
        index_table = match.group("table").strip().strip('`"[]')
        if index_table.lower() != table_name.lower():
            raise ValueError(
                f"Index for {table_name} targets a different table: {index_table}"
            )
        for raw_column in match.group("columns").split(','):
            column_name = raw_column.strip().strip('`"[]')
            if column_name not in physical_columns:
                raise ValueError(
                    f"Index for {table_name} references unknown column {column_name}"
                )
            if column_name not in result:
                result.append(column_name)
    return result


def _bind_all_metadata_to_executable_schemas() -> None:
    """Replace display-only column labels with the complete executable schema."""

    for table_name, metadata in TABLE_METADATA.items():
        column_types = get_table_column_types(table_name)
        nullability = get_table_column_nullability(table_name)
        if not column_types or set(column_types) != set(nullability):
            raise ValueError(f"Executable metadata schema is unavailable for {table_name}")

        existing_columns = {
            column["name"]: column for column in metadata.get("columns", [])
        }
        bound_columns: List[ColumnMetadata] = []
        for column_name, column_type in column_types.items():
            existing = existing_columns.get(column_name)
            if existing is None:
                bound_columns.append({
                    "name": column_name,
                    "type": column_type,
                    "description": column_name,
                    "example": "",
                    "nullable": nullability[column_name],
                })
                continue

            bound_column = deepcopy(existing)
            bound_column["type"] = column_type
            bound_column["nullable"] = nullability[column_name]
            bound_columns.append(bound_column)

        metadata["columns"] = bound_columns
        metadata["primary_key"] = get_table_primary_key_columns(table_name)
        metadata["indexes"] = _get_executable_index_columns(table_name)


_ensure_all_executable_metadata()
_bind_all_metadata_to_executable_schemas()

for _hr_table in ("NL_HR", "RT_HR", "HARAI"):
    TABLE_METADATA[_hr_table]["purpose"] = (
        "公式719バイトHRの全払戻repeatを6項目レースキーで保持。"
        "2004-08-14より前の同長予備領域はhexでlossless保持"
    )
    for _column in TABLE_METADATA[_hr_table]["columns"]:
        if _column["name"] == "LegacyReserved604_717Hex":
            _column["description"] = (
                "三連単発売前の位置604-717を誤解釈せず保持する228文字hex"
            )
        elif _column["name"] == "OpaqueStatus9Body28_717Hex":
            _column["description"] = (
                "公式が本文値を規定しない中止状態9の位置28-717を保持する1380文字hex"
            )
        elif _column["name"].startswith("Yobi") or _column["name"].startswith(
            "PayReserved1"
        ):
            _column["description"] = (
                "公式予備領域PayReserved1の3反復を4/9/3バイトの文字列として保持"
            )

for _jc_table in ("NL_JC", "RT_JC"):
    for _column in TABLE_METADATA[_jc_table]["columns"]:
        if _column["name"] in {"AtoFutan", "MaeFutan"}:
            _column["description"] = (
                "負担重量（kg。JV-Dataの0.1kg単位整数から正規化）"
            )


def get_table_description(table_name: str) -> str:
    """Get table description for MCP.

    Args:
        table_name: Table name (e.g., "NL_RA")

    Returns:
        Table description string
    """
    if table_name in TABLE_METADATA:
        meta = TABLE_METADATA[table_name]
        return f"{meta['description']} - {meta['purpose']}"
    return f"テーブル {table_name}"


def get_column_descriptions(table_name: str) -> Dict[str, str]:
    """Get column descriptions for MCP.

    Args:
        table_name: Table name

    Returns:
        Dictionary mapping column names to descriptions
    """
    if table_name in TABLE_METADATA:
        meta = TABLE_METADATA[table_name]
        return {
            col["name"]: col["description"]
            for col in meta["columns"]
        }
    return {}


def export_schema_for_mcp() -> Dict:
    """Export complete schema metadata for MCP integration.

    Returns:
        Dictionary containing all table and column metadata
    """
    return {
        "version": "2.0.0",
        "description": "JRA-VAN JV-Data database schema",
        "semantics": {
            "nullable": "logical portable schema contract",
            "indexes": "distinct physical columns used by configured secondary indexes",
        },
        "tables": TABLE_METADATA,
    }
