"""Schema metadata for MCP (Model Context Protocol) integration.

This module provides detailed descriptions of tables and columns
for LLM-based applications to understand the database schema.
"""

from typing import Dict, List, TypedDict


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
                "description": "データ区分（1=通常、2=訂正、3=削除、9=レコード削除）",
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
                "description": "データ区分（1=通常、2=訂正、3=削除）",
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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "馬番"],
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

    "NL_KS": {
        "table_name": "NL_KS",
        "record_type": "KS",
        "description": "騎手マスタ情報",
        "purpose": "騎手の基本情報（騎手コード、騎手名、所属、初免許年など）を格納",
        "columns": [
            {
                "name": "レコード種別ID",
                "type": "TEXT",
                "description": "レコード種別識別子（常に'KS'）",
                "example": "KS",
                "nullable": False
            },
            {
                "name": "騎手コード",
                "type": "TEXT",
                "description": "騎手コード（5桁）",
                "example": "01234",
                "nullable": False
            },
            {
                "name": "騎手名漢字",
                "type": "TEXT",
                "description": "騎手名（漢字）",
                "example": "武豊",
                "nullable": True
            },
            {
                "name": "騎手名カナ",
                "type": "TEXT",
                "description": "騎手名（カタカナ）",
                "example": "タケユタカ",
                "nullable": True
            },
            {
                "name": "騎手名欧字",
                "type": "TEXT",
                "description": "騎手名（ローマ字）",
                "example": "Y.TAKE",
                "nullable": True
            },
            {
                "name": "所属コード",
                "type": "TEXT",
                "description": "所属（1=栗東、2=美浦、3=地方、4=海外）",
                "example": "1",
                "nullable": True
            },
            {
                "name": "初免許年",
                "type": "TEXT",
                "description": "騎手免許取得年（西暦4桁）",
                "example": "1987",
                "nullable": True
            },
            {
                "name": "見習い区分",
                "type": "TEXT",
                "description": "見習い区分（0=通常、1=見習い）",
                "example": "0",
                "nullable": True
            },
            {
                "name": "削除フラグ",
                "type": "TEXT",
                "description": "削除フラグ（0=有効、1=削除）",
                "example": "0",
                "nullable": True
            }
        ],
        "primary_key": ["騎手コード"],
        "indexes": ["騎手名漢字", "所属コード"]
    },

    "NL_YS": {
        "table_name": "NL_YS",
        "record_type": "YS",
        "description": "予想データ",
        "purpose": "JRA公式の予想データ（調教タイム、追い切り評価、専門家予想など）を格納",
        "columns": [
            {
                "name": "レコード種別ID",
                "type": "TEXT",
                "description": "レコード種別識別子（常に'YS'）",
                "example": "YS",
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
                "description": "馬番",
                "example": "03",
                "nullable": False
            },
            {
                "name": "調教タイム",
                "type": "TEXT",
                "description": "最終追い切りタイム（秒.1/10秒）",
                "example": "678",
                "nullable": True
            },
            {
                "name": "調教評価",
                "type": "TEXT",
                "description": "調教評価（A-E、A=非常に良い、E=悪い）",
                "example": "A",
                "nullable": True
            },
            {
                "name": "馬体評価",
                "type": "TEXT",
                "description": "馬体評価（A-E）",
                "example": "B",
                "nullable": True
            },
            {
                "name": "気配評価",
                "type": "TEXT",
                "description": "気配評価（A-E）",
                "example": "A",
                "nullable": True
            },
            {
                "name": "専門家印",
                "type": "TEXT",
                "description": "専門家印（◎=本命、○=対抗、▲=単穴、△=連下、×=消し）",
                "example": "◎",
                "nullable": True
            }
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "馬番"],
        "indexes": ["開催年月日", "調教評価"]
    },

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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "発表月日時分"],
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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "発表月日時分"],
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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "発表月日時分"],
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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "発表月日時分"],
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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "発表月日時分"],
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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "発表月日時分"],
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

    "NL_CH": {
        "table_name": "NL_CH",
        "record_type": "CH",
        "description": "調教師マスタ情報",
        "purpose": "調教師の基本情報、免許情報、所属、成績を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'CH'）", "example": "CH", "nullable": False},
            {"name": "調教師コード", "type": "TEXT", "description": "調教師識別コード（5桁）", "example": "01234", "nullable": False},
            {"name": "調教師名", "type": "TEXT", "description": "調教師氏名", "example": "藤沢和雄", "nullable": True},
            {"name": "調教師免許交付年月日", "type": "TEXT", "description": "調教師免許取得日", "example": "19800401", "nullable": True},
            {"name": "調教師免許抹消年月日", "type": "TEXT", "description": "調教師免許失効日（引退時）", "example": "20200331", "nullable": True},
            {"name": "生年月日", "type": "TEXT", "description": "調教師の生年月日", "example": "19540101", "nullable": True},
            {"name": "調教師東西所属コード", "type": "TEXT", "description": "所属（1=美浦（関東）、2=栗東（関西））", "example": "1", "nullable": False},
            {"name": "本年累計成績情報", "type": "TEXT", "description": "当年・累計の1着-着外回数と獲得賞金", "example": "50-45-40-120", "nullable": True}
        ],
        "primary_key": ["調教師コード"],
        "indexes": ["調教師名", "調教師東西所属コード"]
    },

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
        "description": "競走除外馬情報",
        "purpose": "レースから除外された馬とその理由を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'AV'）", "example": "AV", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "馬番", "type": "TEXT", "description": "除外馬の馬番", "example": "03", "nullable": False},
            {"name": "馬名", "type": "TEXT", "description": "除外馬の馬名", "example": "○○○○", "nullable": True},
            {"name": "事由区分", "type": "TEXT", "description": "除外理由（1=疾病、2=事故、3=その他）", "example": "1", "nullable": True},
            {"name": "発表月日時分", "type": "TEXT", "description": "除外発表日時", "example": "06010900", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "馬番"],
        "indexes": ["開催年月日"]
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
        "description": "騎手変更情報",
        "purpose": "騎手の変更・乗り替わり情報を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'DM'）", "example": "DM", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "馬番", "type": "TEXT", "description": "馬番", "example": "05", "nullable": False},
            {"name": "変更後騎手コード", "type": "TEXT", "description": "変更後の騎手コード", "example": "01234", "nullable": True},
            {"name": "変更前騎手コード", "type": "TEXT", "description": "変更前の騎手コード", "example": "05678", "nullable": True},
            {"name": "マイニング予想", "type": "TEXT", "description": "AI予想データ（ネスト構造）", "example": "...", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "馬番"],
        "indexes": ["開催年月日"]
    },

    "NL_JC": {
        "table_name": "NL_JC",
        "record_type": "JC",
        "description": "騎手変更詳細情報",
        "purpose": "騎手変更の詳細（馬名、負担重量含む）を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'JC'）", "example": "JC", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "馬番", "type": "TEXT", "description": "馬番", "example": "05", "nullable": False},
            {"name": "馬名", "type": "TEXT", "description": "馬名", "example": "○○○○", "nullable": True},
            {"name": "負担重量", "type": "TEXT", "description": "負担重量（kg、0.5kg単位）", "example": "58.0", "nullable": True},
            {"name": "騎手名", "type": "TEXT", "description": "変更後騎手名", "example": "武豊", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "馬番"],
        "indexes": ["開催年月日", "騎手名"]
    },

    "NL_JG": {
        "table_name": "NL_JG",
        "record_type": "JG",
        "description": "除外馬詳細情報",
        "purpose": "出馬投票から除外された馬の詳細情報を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'JG'）", "example": "JG", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "血統登録番号", "type": "TEXT", "description": "除外馬の血統登録番号", "example": "2020123456", "nullable": False},
            {"name": "馬名", "type": "TEXT", "description": "除外馬の馬名", "example": "○○○○", "nullable": True},
            {"name": "除外状態区分", "type": "TEXT", "description": "除外理由区分", "example": "1", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "血統登録番号"],
        "indexes": ["開催年月日", "馬名"]
    },

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

    "NL_WE": {
        "table_name": "NL_WE",
        "record_type": "WE",
        "description": "天候・馬場状態変更情報",
        "purpose": "天候と馬場状態の変更情報を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'WE'）", "example": "WE", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "発表月日時分", "type": "TEXT", "description": "発表日時", "example": "06010900", "nullable": False},
            {"name": "天候状態", "type": "TEXT", "description": "天候（1=晴、2=曇、3=雨、4=小雨、5=雪、6=小雪）", "example": "1", "nullable": True},
            {"name": "馬場状態_芝", "type": "TEXT", "description": "芝馬場状態（1=良、2=稍重、3=重、4=不良）", "example": "1", "nullable": True},
            {"name": "馬場状態_ダート", "type": "TEXT", "description": "ダート馬場状態（1=良、2=稍重、3=重、4=不良）", "example": "2", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "発表月日時分"],
        "indexes": ["開催年月日"]
    },

    "NL_WH": {
        "table_name": "NL_WH",
        "record_type": "WH",
        "description": "馬体重情報",
        "purpose": "レース直前の馬体重と増減情報を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'WH'）", "example": "WH", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "馬体重情報", "type": "TEXT", "description": "各馬の体重と増減（ネスト構造、馬番:体重:増減符号:増減kg）", "example": "01:480:+:05", "nullable": True},
            {"name": "発表月日時分", "type": "TEXT", "description": "体重発表日時", "example": "06011000", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日"]
    },

    # 払戻・配当情報テーブル (Payoff Tables)
    "NL_H1": {
        "table_name": "NL_H1",
        "record_type": "H1",
        "description": "単勝・複勝払戻情報",
        "purpose": "単勝・複勝の払戻金額と返還情報を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'H1'）", "example": "H1", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "単勝払戻金", "type": "TEXT", "description": "単勝100円あたり払戻金", "example": "350", "nullable": True},
            {"name": "複勝払戻金", "type": "TEXT", "description": "複勝100円あたり払戻金（最大3頭分）", "example": "120,150,180", "nullable": True},
            {"name": "単勝票数合計", "type": "TEXT", "description": "単勝総投票数", "example": "1234567", "nullable": True},
            {"name": "複勝票数合計", "type": "TEXT", "description": "複勝総投票数", "example": "987654", "nullable": True},
            {"name": "返還馬番情報", "type": "TEXT", "description": "返還対象馬番リスト", "example": "03,07", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日"]
    },

    "NL_H6": {
        "table_name": "NL_H6",
        "record_type": "H6",
        "description": "3連単払戻情報",
        "purpose": "3連単の払戻金額と投票数情報を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'H6'）", "example": "H6", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "3連単払戻金", "type": "TEXT", "description": "3連単100円あたり払戻金", "example": "123450", "nullable": True},
            {"name": "3連単票数合計", "type": "TEXT", "description": "3連単総投票数", "example": "5678901", "nullable": True},
            {"name": "3連単的中票数", "type": "TEXT", "description": "3連単的中票数", "example": "123", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
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

    "NL_CS": {
        "table_name": "NL_CS",
        "record_type": "CS",
        "description": "コース仕様情報",
        "purpose": "競馬場の各コースの仕様・特性を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'CS'）", "example": "CS", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "距離", "type": "TEXT", "description": "コース距離（メートル）", "example": "2400", "nullable": False},
            {"name": "トラックコード", "type": "TEXT", "description": "トラック種別コード", "example": "10", "nullable": False},
            {"name": "コース改修年月日", "type": "TEXT", "description": "コース改修日", "example": "20150401", "nullable": True},
            {"name": "コース説明", "type": "TEXT", "description": "コースの特徴・説明", "example": "最後の直線が長く、末脚が活きやすい", "nullable": True}
        ],
        "primary_key": ["競馬場コード", "距離", "トラックコード", "コース改修年月日"],
        "indexes": ["競馬場コード", "距離"]
    },

    "NL_HC": {
        "table_name": "NL_HC",
        "record_type": "HC",
        "description": "調教タイム情報",
        "purpose": "調教時の走破タイムとラップタイムを格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'HC'）", "example": "HC", "nullable": False},
            {"name": "トレセン区分", "type": "TEXT", "description": "トレーニングセンター（1=美浦、2=栗東）", "example": "1", "nullable": False},
            {"name": "調教年月日", "type": "TEXT", "description": "調教実施日", "example": "20240525", "nullable": False},
            {"name": "調教時刻", "type": "TEXT", "description": "調教実施時刻", "example": "0630", "nullable": False},
            {"name": "血統登録番号", "type": "TEXT", "description": "馬の血統登録番号", "example": "2020123456", "nullable": False},
            {"name": "4F走破タイム", "type": "TEXT", "description": "4ハロン走破タイム（秒）", "example": "52.3", "nullable": True},
            {"name": "3F走破タイム", "type": "TEXT", "description": "3ハロン走破タイム（秒）", "example": "38.5", "nullable": True}
        ],
        "primary_key": ["トレセン区分", "調教年月日", "調教時刻", "血統登録番号"],
        "indexes": ["血統登録番号", "調教年月日"]
    },

    "NL_HS": {
        "table_name": "NL_HS",
        "record_type": "HS",
        "description": "馬成績サマリ情報",
        "purpose": "競走馬の累計成績サマリ（着順別回数、賞金）を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'HS'）", "example": "HS", "nullable": False},
            {"name": "血統登録番号", "type": "TEXT", "description": "馬の血統登録番号", "example": "2020123456", "nullable": False},
            {"name": "平地本賞金", "type": "TEXT", "description": "平地競走での獲得本賞金（千円）", "example": "123456", "nullable": True},
            {"name": "障害本賞金", "type": "TEXT", "description": "障害競走での獲得本賞金（千円）", "example": "12345", "nullable": True},
            {"name": "総合着回数", "type": "TEXT", "description": "1着-2着-3着-着外の回数", "example": "5-3-2-10", "nullable": True},
            {"name": "脚質傾向", "type": "TEXT", "description": "主な脚質（1=逃げ、2=先行、3=差し、4=追込）", "example": "2", "nullable": True}
        ],
        "primary_key": ["血統登録番号"],
        "indexes": ["血統登録番号"]
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
        "description": "レースレコード情報",
        "purpose": "コース別レコードタイムと保持馬情報を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'RC'）", "example": "RC", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "距離", "type": "TEXT", "description": "コース距離", "example": "2400", "nullable": False},
            {"name": "トラックコード", "type": "TEXT", "description": "トラック種別", "example": "10", "nullable": False},
            {"name": "レコードタイム", "type": "TEXT", "description": "レコードタイム（分秒形式）", "example": "2:22.1", "nullable": True},
            {"name": "レコード保持馬", "type": "TEXT", "description": "レコード保持馬名", "example": "○○○○", "nullable": True},
            {"name": "レコード樹立年月日", "type": "TEXT", "description": "レコード樹立日", "example": "20180527", "nullable": True}
        ],
        "primary_key": ["競馬場コード", "距離", "トラックコード"],
        "indexes": ["競馬場コード"]
    },

    "NL_SK": {
        "table_name": "NL_SK",
        "record_type": "SK",
        "description": "馬3代血統詳細情報",
        "purpose": "競走馬の3代血統（父・母・祖父母）詳細を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'SK'）", "example": "SK", "nullable": False},
            {"name": "血統登録番号", "type": "TEXT", "description": "馬の血統登録番号", "example": "2020123456", "nullable": False},
            {"name": "父馬繁殖登録番号", "type": "TEXT", "description": "父馬の繁殖登録番号", "example": "1234567890", "nullable": True},
            {"name": "母馬繁殖登録番号", "type": "TEXT", "description": "母馬の繁殖登録番号", "example": "0987654321", "nullable": True},
            {"name": "父父繁殖登録番号", "type": "TEXT", "description": "父父（父の父）繁殖登録番号", "example": "1111111111", "nullable": True},
            {"name": "父母繁殖登録番号", "type": "TEXT", "description": "父母（父の母）繁殖登録番号", "example": "2222222222", "nullable": True},
            {"name": "母父繁殖登録番号", "type": "TEXT", "description": "母父（母の父）繁殖登録番号", "example": "3333333333", "nullable": True},
            {"name": "母母繁殖登録番号", "type": "TEXT", "description": "母母（母の母）繁殖登録番号", "example": "4444444444", "nullable": True}
        ],
        "primary_key": ["血統登録番号"],
        "indexes": ["血統登録番号", "父馬繁殖登録番号", "母馬繁殖登録番号"]
    },

    "NL_TK": {
        "table_name": "NL_TK",
        "record_type": "TK",
        "description": "登録馬情報",
        "purpose": "レース登録時の馬情報（出馬投票段階）を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'TK'）", "example": "TK", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "登録頭数", "type": "TEXT", "description": "登録馬頭数", "example": "18", "nullable": True},
            {"name": "登録馬毎情報", "type": "TEXT", "description": "各登録馬の詳細情報（ネスト構造）", "example": "...", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日"]
    },

    "NL_TM": {
        "table_name": "NL_TM",
        "record_type": "TM",
        "description": "タイム型マイニング予想情報",
        "purpose": "AI/マイニング予想データ（タイム型）を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'TM'）", "example": "TM", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "データ作成時分", "type": "TEXT", "description": "データ作成日時", "example": "202406010900", "nullable": True},
            {"name": "マイニング予想", "type": "TEXT", "description": "AI予想データ（ネスト構造）", "example": "...", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日"]
    },

    "NL_WC": {
        "table_name": "NL_WC",
        "record_type": "WC",
        "description": "調教詳細タイム情報",
        "purpose": "調教時の詳細ラップタイム（200m刻み）を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'WC'）", "example": "WC", "nullable": False},
            {"name": "トレセン区分", "type": "TEXT", "description": "トレーニングセンター", "example": "1", "nullable": False},
            {"name": "調教年月日", "type": "TEXT", "description": "調教実施日", "example": "20240525", "nullable": False},
            {"name": "調教時刻", "type": "TEXT", "description": "調教実施時刻", "example": "0630", "nullable": False},
            {"name": "血統登録番号", "type": "TEXT", "description": "馬の血統登録番号", "example": "2020123456", "nullable": False},
            {"name": "2000M通過タイム", "type": "TEXT", "description": "2000m地点通過タイム", "example": "120.5", "nullable": True},
            {"name": "1800M通過タイム", "type": "TEXT", "description": "1800m地点通過タイム", "example": "108.2", "nullable": True},
            {"name": "200M通過タイム", "type": "TEXT", "description": "200m地点通過タイム", "example": "12.1", "nullable": True}
        ],
        "primary_key": ["トレセン区分", "調教年月日", "調教時刻", "血統登録番号"],
        "indexes": ["血統登録番号", "調教年月日"]
    },

    "NL_WF": {
        "table_name": "NL_WF",
        "record_type": "WF",
        "description": "重勝式（Win5等）発売情報",
        "purpose": "重勝式馬券（複数レース的中予想）の発売・払戻情報を格納",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'WF'）", "example": "WF", "nullable": False},
            {"name": "開催年", "type": "TEXT", "description": "開催年", "example": "2024", "nullable": False},
            {"name": "開催月日", "type": "TEXT", "description": "開催月日", "example": "0601", "nullable": False},
            {"name": "重勝式対象レース情報", "type": "TEXT", "description": "対象レース情報（ネスト構造）", "example": "...", "nullable": True},
            {"name": "重勝式発売票数", "type": "TEXT", "description": "総投票数", "example": "12345678", "nullable": True},
            {"name": "キャリーオーバー残高", "type": "TEXT", "description": "繰越金残高（円）", "example": "234567890", "nullable": True},
            {"name": "重勝式払戻情報", "type": "TEXT", "description": "払戻金額情報（ネスト構造）", "example": "...", "nullable": True}
        ],
        "primary_key": ["開催年", "開催月日"],
        "indexes": ["開催年", "開催月日"]
    },

    # 速報系テーブル (Realtime Tables) - リアルタイム更新用
    "RT_AV": {
        "table_name": "RT_AV",
        "record_type": "AV",
        "description": "競走除外馬情報（速報）",
        "purpose": "リアルタイムでの競走除外馬情報を格納（NL_AVと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'AV'）", "example": "AV", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "馬番", "type": "TEXT", "description": "除外馬の馬番", "example": "03", "nullable": False},
            {"name": "馬名", "type": "TEXT", "description": "除外馬の馬名", "example": "○○○○", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "馬番"],
        "indexes": ["開催年月日"]
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
        "description": "騎手変更情報（速報）",
        "purpose": "リアルタイムでの騎手変更情報を格納（NL_DMと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'DM'）", "example": "DM", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "馬番", "type": "TEXT", "description": "馬番", "example": "05", "nullable": False},
            {"name": "変更後騎手コード", "type": "TEXT", "description": "変更後の騎手コード", "example": "01234", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "馬番"],
        "indexes": ["開催年月日"]
    },

    "RT_H1": {
        "table_name": "RT_H1",
        "record_type": "H1",
        "description": "単勝・複勝払戻情報（速報）",
        "purpose": "リアルタイムでの単勝・複勝払戻情報を格納（NL_H1と同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'H1'）", "example": "H1", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "単勝払戻金", "type": "TEXT", "description": "単勝100円あたり払戻金", "example": "350", "nullable": True},
            {"name": "複勝払戻金", "type": "TEXT", "description": "複勝100円あたり払戻金", "example": "120,150,180", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日"]
    },

    "RT_H6": {
        "table_name": "RT_H6",
        "record_type": "H6",
        "description": "3連単払戻情報（速報）",
        "purpose": "リアルタイムでの3連単払戻情報を格納（NL_H6と同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'H6'）", "example": "H6", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "3連単払戻金", "type": "TEXT", "description": "3連単100円あたり払戻金", "example": "123450", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
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

    "RT_JC": {
        "table_name": "RT_JC",
        "record_type": "JC",
        "description": "騎手変更詳細情報（速報）",
        "purpose": "リアルタイムでの騎手変更詳細情報を格納（NL_JCと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'JC'）", "example": "JC", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "馬番", "type": "TEXT", "description": "馬番", "example": "05", "nullable": False},
            {"name": "騎手名", "type": "TEXT", "description": "変更後騎手名", "example": "武豊", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "馬番"],
        "indexes": ["開催年月日"]
    },

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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "発表月日時分"],
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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "発表月日時分"],
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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "発表月日時分"],
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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "発表月日時分"],
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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "発表月日時分"],
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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "発表月日時分"],
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
        "primary_key": ["開催年月日", "競馬場コード", "レース番号", "馬番"],
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
        "description": "タイム型マイニング予想情報（速報）",
        "purpose": "リアルタイムでのAI予想データを格納（NL_TMと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'TM'）", "example": "TM", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "マイニング予想", "type": "TEXT", "description": "AI予想データ", "example": "...", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日"]
    },

    "RT_WE": {
        "table_name": "RT_WE",
        "record_type": "WE",
        "description": "天候・馬場状態変更情報（速報）",
        "purpose": "リアルタイムでの天候・馬場状態変更を格納（NL_WEと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'WE'）", "example": "WE", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "天候状態", "type": "TEXT", "description": "天候", "example": "1", "nullable": True},
            {"name": "馬場状態_芝", "type": "TEXT", "description": "芝馬場状態", "example": "1", "nullable": True},
            {"name": "馬場状態_ダート", "type": "TEXT", "description": "ダート馬場状態", "example": "2", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード"],
        "indexes": ["開催年月日"]
    },

    "RT_WH": {
        "table_name": "RT_WH",
        "record_type": "WH",
        "description": "馬体重情報（速報）",
        "purpose": "リアルタイムでの馬体重情報を格納（NL_WHと同構造）",
        "columns": [
            {"name": "レコード種別ID", "type": "TEXT", "description": "レコード種別識別子（'WH'）", "example": "WH", "nullable": False},
            {"name": "開催年月日", "type": "TEXT", "description": "レース開催日", "example": "20240601", "nullable": False},
            {"name": "競馬場コード", "type": "TEXT", "description": "競馬場コード", "example": "05", "nullable": False},
            {"name": "レース番号", "type": "TEXT", "description": "レース番号", "example": "11", "nullable": False},
            {"name": "馬体重情報", "type": "TEXT", "description": "各馬の体重と増減", "example": "01:480:+:05", "nullable": True}
        ],
        "primary_key": ["開催年月日", "競馬場コード", "レース番号"],
        "indexes": ["開催年月日"]
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
            {"name": "TanNinki", "type": "INTEGER", "description": "単勝人気順", "example": "1", "nullable": True}
        ],
        "primary_key": ["Year", "MonthDay", "JyoCD", "RaceNum", "Umaban", "HassoTime"],
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
            {"name": "Ninki", "type": "INTEGER", "description": "人気順", "example": "3", "nullable": True}
        ],
        "primary_key": ["Year", "MonthDay", "JyoCD", "RaceNum", "Kumi", "HassoTime"],
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
            {"name": "OddsHigh", "type": "REAL", "description": "ワイドオッズ上限", "example": "4.5", "nullable": True}
        ],
        "primary_key": ["Year", "MonthDay", "JyoCD", "RaceNum", "Kumi", "HassoTime"],
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
            {"name": "Ninki", "type": "INTEGER", "description": "人気順", "example": "5", "nullable": True}
        ],
        "primary_key": ["Year", "MonthDay", "JyoCD", "RaceNum", "Kumi", "HassoTime"],
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
            {"name": "Ninki", "type": "INTEGER", "description": "人気順", "example": "8", "nullable": True}
        ],
        "primary_key": ["Year", "MonthDay", "JyoCD", "RaceNum", "Kumi", "HassoTime"],
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
            {"name": "Ninki", "type": "INTEGER", "description": "人気順", "example": "15", "nullable": True}
        ],
        "primary_key": ["Year", "MonthDay", "JyoCD", "RaceNum", "Kumi", "HassoTime"],
        "indexes": ["Year", "MonthDay", "HassoTime"]
    }
}


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
        "version": "1.0.0",
        "description": "JRA-VAN JV-Data database schema",
        "tables": TABLE_METADATA
    }
