# -*- coding: utf-8 -*-
"""HR parser regression test: all payout array entries must be extracted.

Background: the parser previously extracted only the first entry of each
payout array (same defect as jrvltsql-nar#6). Fukusho pays up to 5 horses
and wide up to 7 combinations, so roughly two thirds of winning
place-ticket payouts were dropped, corrupting every downstream
fukusho/wide evaluation on 2026 JRA data.
"""

from src.parser.hr_parser import HRParser


def _field(value: str, width: int) -> bytes:
    return value.ljust(width).encode("cp932")


def _num(value: int, width: int) -> bytes:
    return str(value).zfill(width).encode("cp932")


def build_record() -> bytes:
    buf = b""
    buf += _field("HR", 2)            # RecordSpec
    buf += _field("7", 1)             # DataKubun
    buf += _field("20260611", 8)      # MakeDate
    buf += _field("2026", 4)          # Year
    buf += _field("0611", 4)          # MonthDay
    buf += _field("05", 2)            # JyoCD
    buf += _field("03", 2)            # Kaiji
    buf += _field("08", 2)            # Nichiji
    buf += _field("11", 2)            # RaceNum
    buf += _field("16", 2)            # TorokuTosu
    buf += _field("16", 2)            # SyussoTosu
    buf += b"0" * 9                   # FuseirituFlag1-9
    buf += b"0" * 9                   # TokubaraiFlag1-9
    buf += b"0" * 9                   # HenkanFlag1-9
    buf += b"0" * 28                  # HenkanUma1-28
    buf += b"0" * 8                   # HenkanWaku1-8
    buf += b"0" * 8                   # HenkanDoWaku1-8
    assert len(buf) == 102

    # 単勝 3件: 1件のみ実データ
    buf += _field("07", 2) + _num(310, 9) + _field("01", 2)
    for _ in range(2):
        buf += _field("", 2) + _num(0, 9) + _field("", 2)

    # 複勝 5件: 3件実データ
    fuku = [("07", 150, "01"), ("03", 280, "04"), ("11", 540, "08")]
    for uma, pay, ninki in fuku:
        buf += _field(uma, 2) + _num(pay, 9) + _field(ninki, 2)
    for _ in range(2):
        buf += _field("", 2) + _num(0, 9) + _field("", 2)

    # 枠連 3件
    buf += _field("45", 2) + _num(890, 9) + _field("03", 2)
    for _ in range(2):
        buf += _field("", 2) + _num(0, 9) + _field("", 2)

    # 馬連 3件
    buf += _field("0307", 4) + _num(1240, 9) + _field("005", 3)
    for _ in range(2):
        buf += _field("", 4) + _num(0, 9) + _field("", 3)

    # ワイド 7件: 3件実データ
    wide = [("0307", 420, "004"), ("0711", 1370, "015"), ("0311", 980, "011")]
    for kumi, pay, ninki in wide:
        buf += _field(kumi, 4) + _num(pay, 9) + _field(ninki, 3)
    for _ in range(4):
        buf += _field("", 4) + _num(0, 9) + _field("", 3)

    # 予備 3件 (48 bytes)
    buf += b" " * 48

    # 馬単 6件
    buf += _field("0703", 4) + _num(2150, 9) + _field("008", 3)
    for _ in range(5):
        buf += _field("", 4) + _num(0, 9) + _field("", 3)

    # 三連複 3件
    buf += _field("030711", 6) + _num(3580, 9) + _field("012", 3)
    for _ in range(2):
        buf += _field("", 6) + _num(0, 9) + _field("", 3)

    # 三連単 6件
    buf += _field("070311", 6) + _num(15800, 9) + _field("0042", 4)
    for _ in range(5):
        buf += _field("", 6) + _num(0, 9) + _field("", 4)

    # レコード区切
    buf += _field("", 2)
    assert len(buf) == 719, len(buf)
    return buf


def test_all_payout_entries_extracted():
    record = build_record()
    result = HRParser().parse(record)
    assert result is not None

    # 1件目 (後方互換: 接尾辞なし)
    assert result["FukuUmaban"] == "07"
    assert result["FukuPay"] == "000000150"
    # 2件目以降 (修正で追加)
    assert result["FukuUmaban2"] == "03"
    assert result["FukuPay2"] == "000000280"
    assert result["FukuUmaban3"] == "11"
    assert result["FukuPay3"] == "000000540"
    assert result["FukuUmaban4"].strip() == ""

    assert result["WideKumi"] == "0307"
    assert result["WideKumi2"] == "0711"
    assert result["WidePay2"] == "000001370"
    assert result["WideKumi3"] == "0311"
    assert result["WideKumi4"].strip() == ""

    # 配列直後のフィールドが位置ずれしていないこと
    assert result["TanUmaban"] == "07"
    assert result["UmarenKumi"] == "0307"
    assert result["UmatanKumi"] == "0703"
    assert result["SanrenfukuKumi"] == "030711"
    assert result["SanrentanKumi"] == "070311"
    assert result["SanrentanPay"] == "000015800"
