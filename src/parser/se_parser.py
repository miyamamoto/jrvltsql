"""Parser for SE (Race-Horse) records.

This module parses SE record type which contains horse-by-race information.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class SEParser(BaseParser):
    """Parser for SE (Race-Horse) record type.

    SE records contain detailed information for each horse in a race:
    - Race identification (links to RA record)
    - Horse identification (blood registration number)
    - Horse basic info (name, age, sex, trainer, owner)
    - Starting info (post position, horse number, weight assignment)
    - Jockey information
    - Race results (finish position, time, margin)
    - Odds and popularity
    - Horse weight
    - Prize money

    Record Format:
        - Record type: "SE"
        - Fixed-length format (Shift_JIS encoding)
        - Total length: varies (typically 1500+ bytes)

    Examples:
        >>> parser = SEParser()
        >>> record = b"SE1202406010603081..."  # Raw JV-Data
        >>> data = parser.parse(record)
        >>> print(f"Horse: {data['Bamei']}, Position: {data['KakuteiJyuni']}")
    """

    record_type = "SE"

    def _define_fields(self) -> List[FieldDef]:
        """Define SE record field structure.

        Field positions are based on JV-Data specification version 4.9+.

        Returns:
            List of field definitions
        """
        return [
            # レコードヘッダー (0-13)
            FieldDef("headRecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("headDataKubun", 2, 1, description="データ区分"),
            FieldDef("headMakeDate", 3, 8, description="データ作成年月日"),
            # レース識別情報 (11-27)
            FieldDef("idYear", 11, 4, description="開催年"),
            FieldDef("idMonthDay", 15, 4, description="開催月日"),
            FieldDef("idJyoCD", 19, 2, description="競馬場コード"),
            FieldDef("idKaiji", 21, 2, description="開催回"),
            FieldDef("idNichiji", 23, 2, description="開催日目"),
            FieldDef("idRaceNum", 25, 2, description="レース番号"),
            # 馬識別情報 (27-63)
            FieldDef("KettoNum", 27, 10, description="血統登録番号"),
            FieldDef("Bamei", 37, 36, description="馬名"),
            # 馬基本情報 (73-)
            FieldDef("UmaKigoCD", 73, 2, description="馬記号コード"),
            FieldDef("SexCD", 75, 1, description="性別コード"),
            FieldDef("Barei", 76, 2, description="馬齢"),
            FieldDef("TozaiCD", 78, 1, description="東西所属コード"),
            FieldDef("ChokyosiCode", 79, 5, description="調教師コード"),
            FieldDef("ChokyosiRyakusyo", 84, 12, description="調教師名略称"),
            FieldDef("BanusiCode", 96, 6, description="馬主コード"),
            FieldDef("BanusiName", 102, 64, description="馬主名"),
            FieldDef("KeiroCD", 166, 2, description="毛色コード"),
            # 出走情報 (168-)
            FieldDef("Wakuban", 168, 1, description="枠番"),
            FieldDef("Umaban", 169, 2, description="馬番"),
            FieldDef("Futan", 171, 3, "float", "負担重量"),
            FieldDef("BlinkerCD", 174, 1, description="ブリンカー使用区分"),
            # 騎手情報 (175-)
            FieldDef("KisyuCode", 175, 5, description="騎手コード"),
            FieldDef("KisyuRyakusyo", 180, 12, description="騎手名略称"),
            FieldDef("MinaraiCD", 192, 1, description="見習区分"),
            # レース成績 (193-)
            FieldDef("KakuteiJyuni", 193, 2, "int", "確定着順"),
            FieldDef("TimeDiff", 195, 4, description="着差"),
            FieldDef("Jyuni", 199, 2, "int", "入線順位"),
            FieldDef("IjyoKubun", 201, 1, description="異常区分"),
            FieldDef("Time", 202, 4, description="走破タイム"),
            FieldDef("Tyakusa", 206, 3, description="着差詳細"),
            FieldDef("TyakusaCDP", 209, 3, description="着差コードプラス"),
            FieldDef("TyakusaCDPP", 212, 3, description="着差コードプラスプラス"),
            # コーナー順位 (215-)
            FieldDef("CornerJyuni1", 215, 2, description="1コーナー順位"),
            FieldDef("CornerJyuni2", 217, 2, description="2コーナー順位"),
            FieldDef("CornerJyuni3", 219, 2, description="3コーナー順位"),
            FieldDef("CornerJyuni4", 221, 2, description="4コーナー順位"),
            # オッズ・人気 (223-)
            FieldDef("Odds", 223, 6, "float", "単勝オッズ"),
            FieldDef("Ninki", 229, 2, "int", "単勝人気順"),
            # 馬体重情報 (231-)
            FieldDef("Bataiju", 231, 3, "int", "馬体重"),
            FieldDef("BataijuZoka", 234, 3, description="馬体重増減"),
            # 賞金 (237-)
            FieldDef("HondaiSyogaku", 237, 9, "int", "本賞金"),
            FieldDef("FukaSyogaku", 246, 9, "int", "付加賞金"),
            # タイム詳細 (255-)
            FieldDef("Time1F", 255, 3, description="ハロンタイム1"),
            FieldDef("Time2F", 258, 3, description="ハロンタイム2"),
            FieldDef("Time3F", 261, 3, description="ハロンタイム3"),
            FieldDef("Time4F", 264, 3, description="ハロンタイム後半4F"),
            FieldDef("Time5F", 267, 3, description="ハロンタイム後半5F"),
            # 上がり3ハロン (270-)
            FieldDef("Agari3F", 270, 3, description="上がり3ハロン"),
            # レースペース (273-)
            FieldDef("ZenpanPace", 273, 1, description="前半ペース"),
            FieldDef("KohanPace", 274, 1, description="後半ペース"),
            # 血統情報 (275-)
            FieldDef("Ketto3Info0", 275, 10, description="父馬繁殖登録番号"),
            FieldDef("Ketto3Info1", 285, 10, description="母馬繁殖登録番号"),
            FieldDef("Ketto3Info2", 295, 10, description="父父繁殖登録番号"),
            FieldDef("Ketto3Info3", 305, 10, description="父母繁殖登録番号"),
            FieldDef("Ketto3Info4", 315, 10, description="母父繁殖登録番号"),
            FieldDef("Ketto3Info5", 325, 10, description="母母繁殖登録番号"),
            # その他 (335-)
            FieldDef("KakuteiKyakusituKubun", 335, 1, description="確定脚質区分"),
            FieldDef("SohaKubunCD", 336, 1, description="走破区分コード"),
            FieldDef("SohaKubun", 337, 2, description="走破区分"),
            FieldDef("TenkoCD", 339, 1, description="天候コード"),
            FieldDef("BabaCD", 340, 2, description="馬場状態コード"),
            # Additional fields for completeness
            FieldDef("RecordUpKubun", 342, 1, description="レコード更新区分"),
        ]
