"""Parser for HR (Payout) records.

This module parses HR record type which contains payout information.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class HRParser(BaseParser):
    """Parser for HR (Payout) record type.

    HR records contain race payout information for all bet types:
    - Win (単勝)
    - Place (複勝)
    - Bracket Quinella (枠連)
    - Quinella (馬連)
    - Wide (ワイド)
    - Exacta (馬単)
    - Trio (3連複)
    - Trifecta (3連単)

    Record Format:
        - Record type: "HR"
        - Fixed-length format (Shift_JIS encoding)
        - Total length: varies (typically 800+ bytes)

    Examples:
        >>> parser = HRParser()
        >>> record = b"HR1202406010603081..."  # Raw JV-Data
        >>> data = parser.parse(record)
        >>> print(f"Win payout: {data['TansyoHaraimodosi1']} yen")
    """

    record_type = "HR"

    def _define_fields(self) -> List[FieldDef]:
        """Define HR record field structure.

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
            # 単勝 (27-45)
            FieldDef("TansyoUmaban1", 27, 2, description="単勝馬番1"),
            FieldDef("TansyoHaraimodosi1", 29, 9, "int", "単勝払戻金1"),
            FieldDef("TansyoNinki1", 38, 2, "int", "単勝人気順1"),
            # 複勝 (40-106)
            FieldDef("FukusyoUmaban1", 40, 2, description="複勝馬番1"),
            FieldDef("FukusyoHaraimodosi1", 42, 9, "int", "複勝払戻金1"),
            FieldDef("FukusyoNinki1", 51, 2, "int", "複勝人気順1"),
            FieldDef("FukusyoUmaban2", 53, 2, description="複勝馬番2"),
            FieldDef("FukusyoHaraimodosi2", 55, 9, "int", "複勝払戻金2"),
            FieldDef("FukusyoNinki2", 64, 2, "int", "複勝人気順2"),
            FieldDef("FukusyoUmaban3", 66, 2, description="複勝馬番3"),
            FieldDef("FukusyoHaraimodosi3", 68, 9, "int", "複勝払戻金3"),
            FieldDef("FukusyoNinki3", 77, 2, "int", "複勝人気順3"),
            FieldDef("FukusyoUmaban4", 79, 2, description="複勝馬番4"),
            FieldDef("FukusyoHaraimodosi4", 81, 9, "int", "複勝払戻金4"),
            FieldDef("FukusyoNinki4", 90, 2, "int", "複勝人気順4"),
            FieldDef("FukusyoUmaban5", 92, 2, description="複勝馬番5"),
            FieldDef("FukusyoHaraimodosi5", 94, 9, "int", "複勝払戻金5"),
            FieldDef("FukusyoNinki5", 103, 2, "int", "複勝人気順5"),
            # 枠連 (105-264) - 3組まで
            FieldDef("WakurenWakuban1_1", 105, 1, description="枠連枠番1-1"),
            FieldDef("WakurenWakuban1_2", 106, 1, description="枠連枠番1-2"),
            FieldDef("WakurenHaraimodosi1", 107, 9, "int", "枠連払戻金1"),
            FieldDef("WakurenNinki1", 116, 2, "int", "枠連人気順1"),
            FieldDef("WakurenWakuban2_1", 118, 1, description="枠連枠番2-1"),
            FieldDef("WakurenWakuban2_2", 119, 1, description="枠連枠番2-2"),
            FieldDef("WakurenHaraimodosi2", 120, 9, "int", "枠連払戻金2"),
            FieldDef("WakurenNinki2", 129, 2, "int", "枠連人気順2"),
            FieldDef("WakurenWakuban3_1", 131, 1, description="枠連枠番3-1"),
            FieldDef("WakurenWakuban3_2", 132, 1, description="枠連枠番3-2"),
            FieldDef("WakurenHaraimodosi3", 133, 9, "int", "枠連払戻金3"),
            FieldDef("WakurenNinki3", 142, 2, "int", "枠連人気順3"),
            # 馬連 (144-303) - 3組まで
            FieldDef("UmarenUmaban1_1", 144, 2, description="馬連馬番1-1"),
            FieldDef("UmarenUmaban1_2", 146, 2, description="馬連馬番1-2"),
            FieldDef("UmarenHaraimodosi1", 148, 9, "int", "馬連払戻金1"),
            FieldDef("UmarenNinki1", 157, 3, "int", "馬連人気順1"),
            FieldDef("UmarenUmaban2_1", 160, 2, description="馬連馬番2-1"),
            FieldDef("UmarenUmaban2_2", 162, 2, description="馬連馬番2-2"),
            FieldDef("UmarenHaraimodosi2", 164, 9, "int", "馬連払戻金2"),
            FieldDef("UmarenNinki2", 173, 3, "int", "馬連人気順2"),
            FieldDef("UmarenUmaban3_1", 176, 2, description="馬連馬番3-1"),
            FieldDef("UmarenUmaban3_2", 178, 2, description="馬連馬番3-2"),
            FieldDef("UmarenHaraimodosi3", 180, 9, "int", "馬連払戻金3"),
            FieldDef("UmarenNinki3", 189, 3, "int", "馬連人気順3"),
            # ワイド (192-351) - 7組まで (簡略化: 3組)
            FieldDef("WideUmaban1_1", 192, 2, description="ワイド馬番1-1"),
            FieldDef("WideUmaban1_2", 194, 2, description="ワイド馬番1-2"),
            FieldDef("WideHaraimodosi1", 196, 9, "int", "ワイド払戻金1"),
            FieldDef("WideNinki1", 205, 3, "int", "ワイド人気順1"),
            FieldDef("WideUmaban2_1", 208, 2, description="ワイド馬番2-1"),
            FieldDef("WideUmaban2_2", 210, 2, description="ワイド馬番2-2"),
            FieldDef("WideHaraimodosi2", 212, 9, "int", "ワイド払戻金2"),
            FieldDef("WideNinki2", 221, 3, "int", "ワイド人気順2"),
            FieldDef("WideUmaban3_1", 224, 2, description="ワイド馬番3-1"),
            FieldDef("WideUmaban3_2", 226, 2, description="ワイド馬番3-2"),
            FieldDef("WideHaraimodosi3", 228, 9, "int", "ワイド払戻金3"),
            FieldDef("WideNinki3", 237, 3, "int", "ワイド人気順3"),
            # 馬単 (352-511) - 6組まで (簡略化: 3組)
            FieldDef("UmatanUmaban1_1", 352, 2, description="馬単馬番1-1"),
            FieldDef("UmatanUmaban1_2", 354, 2, description="馬単馬番1-2"),
            FieldDef("UmatanHaraimodosi1", 356, 9, "int", "馬単払戻金1"),
            FieldDef("UmatanNinki1", 365, 3, "int", "馬単人気順1"),
            FieldDef("UmatanUmaban2_1", 368, 2, description="馬単馬番2-1"),
            FieldDef("UmatanUmaban2_2", 370, 2, description="馬単馬番2-2"),
            FieldDef("UmatanHaraimodosi2", 372, 9, "int", "馬単払戻金2"),
            FieldDef("UmatanNinki2", 381, 3, "int", "馬単人気順2"),
            FieldDef("UmatanUmaban3_1", 384, 2, description="馬単馬番3-1"),
            FieldDef("UmatanUmaban3_2", 386, 2, description="馬単馬番3-2"),
            FieldDef("UmatanHaraimodosi3", 388, 9, "int", "馬単払戻金3"),
            FieldDef("UmatanNinki3", 397, 3, "int", "馬単人気順3"),
            # 3連複 (512-671) - 3組まで
            FieldDef("Sanrenpuku3Umaban1_1", 512, 2, description="3連複馬番1-1"),
            FieldDef("Sanrenpuku3Umaban1_2", 514, 2, description="3連複馬番1-2"),
            FieldDef("Sanrenpuku3Umaban1_3", 516, 2, description="3連複馬番1-3"),
            FieldDef("Sanrenpuku3Haraimodosi1", 518, 9, "int", "3連複払戻金1"),
            FieldDef("Sanrenpuku3Ninki1", 527, 3, "int", "3連複人気順1"),
            FieldDef("Sanrenpuku3Umaban2_1", 530, 2, description="3連複馬番2-1"),
            FieldDef("Sanrenpuku3Umaban2_2", 532, 2, description="3連複馬番2-2"),
            FieldDef("Sanrenpuku3Umaban2_3", 534, 2, description="3連複馬番2-3"),
            FieldDef("Sanrenpuku3Haraimodosi2", 536, 9, "int", "3連複払戻金2"),
            FieldDef("Sanrenpuku3Ninki2", 545, 3, "int", "3連複人気順2"),
            FieldDef("Sanrenpuku3Umaban3_1", 548, 2, description="3連複馬番3-1"),
            FieldDef("Sanrenpuku3Umaban3_2", 550, 2, description="3連複馬番3-2"),
            FieldDef("Sanrenpuku3Umaban3_3", 552, 2, description="3連複馬番3-3"),
            FieldDef("Sanrenpuku3Haraimodosi3", 554, 9, "int", "3連複払戻金3"),
            FieldDef("Sanrenpuku3Ninki3", 563, 3, "int", "3連複人気順3"),
            # 3連単 (672-831) - 6組まで (簡略化: 3組)
            FieldDef("Sanrentan3Umaban1_1", 672, 2, description="3連単馬番1-1"),
            FieldDef("Sanrentan3Umaban1_2", 674, 2, description="3連単馬番1-2"),
            FieldDef("Sanrentan3Umaban1_3", 676, 2, description="3連単馬番1-3"),
            FieldDef("Sanrentan3Haraimodosi1", 678, 10, "int", "3連単払戻金1"),
            FieldDef("Sanrentan3Ninki1", 688, 4, "int", "3連単人気順1"),
            FieldDef("Sanrentan3Umaban2_1", 692, 2, description="3連単馬番2-1"),
            FieldDef("Sanrentan3Umaban2_2", 694, 2, description="3連単馬番2-2"),
            FieldDef("Sanrentan3Umaban2_3", 696, 2, description="3連単馬番2-3"),
            FieldDef("Sanrentan3Haraimodosi2", 698, 10, "int", "3連単払戻金2"),
            FieldDef("Sanrentan3Ninki2", 708, 4, "int", "3連単人気順2"),
            FieldDef("Sanrentan3Umaban3_1", 712, 2, description="3連単馬番3-1"),
            FieldDef("Sanrentan3Umaban3_2", 714, 2, description="3連単馬番3-2"),
            FieldDef("Sanrentan3Umaban3_3", 716, 2, description="3連単馬番3-3"),
            FieldDef("Sanrentan3Haraimodosi3", 718, 10, "int", "3連単払戻金3"),
            FieldDef("Sanrentan3Ninki3", 728, 4, "int", "3連単人気順3"),
        ]
