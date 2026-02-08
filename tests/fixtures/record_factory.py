#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Factory for creating test record data matching JV-Data / NV-Data specifications.

Creates properly formatted byte sequences for parser testing.
Based on JV-Data仕様書 Ver.4.9.0.1 and kmy-keiba structures.cs.

All data is synthetic/anonymized - no real racing data.
"""


def _pad(value: str, length: int, encoding: str = "cp932") -> bytes:
    """Encode and right-pad string to exact byte length."""
    encoded = value.encode(encoding)
    if len(encoded) > length:
        encoded = encoded[:length]
    return encoded.ljust(length, b' ')


def _num(value, length: int) -> bytes:
    """Format number as zero-padded ASCII string."""
    return str(value).zfill(length).encode('ascii')[:length]


def make_record_header(record_spec: str, data_kubun: str = "1",
                       make_date: str = "20260101") -> bytes:
    """Create 11-byte record header."""
    return _pad(record_spec, 2) + _pad(data_kubun, 1) + _pad(make_date, 8)


def make_ra_record(
    data_kubun="1", make_date="20260101",
    year="2026", month_day="0101", jyo_cd="05",
    kaiji="01", nichiji="01", race_num="01",
    youbi_cd="0", toku_num="0000",
    hondai="テストレース", kyori="1600",
    track_cd="11", hasso_time="1510",
    toroku_tosu="16", syusso_tosu="14", nyusen_tosu="14",
    tenko_cd="1", siba_baba_cd="1", dirt_baba_cd="0",
    **kwargs,
) -> bytes:
    """Create RA record (856 bytes)."""
    data = bytearray(856)
    data[0:2] = _pad("RA", 2)
    data[2:3] = _pad(data_kubun, 1)
    data[3:11] = _pad(make_date, 8)
    data[11:15] = _pad(year, 4)
    data[15:19] = _pad(month_day, 4)
    data[19:21] = _pad(jyo_cd, 2)
    data[21:23] = _pad(kaiji, 2)
    data[23:25] = _pad(nichiji, 2)
    data[25:27] = _pad(race_num, 2)
    data[27:28] = _pad(youbi_cd, 1)
    data[28:32] = _pad(toku_num, 4)
    data[32:92] = _pad(hondai, 60)
    data[697:701] = _pad(kyori, 4)
    data[705:707] = _pad(track_cd, 2)
    data[745:749] = _pad(hasso_time, 4)
    data[753:755] = _pad(toroku_tosu, 2)
    data[755:757] = _pad(syusso_tosu, 2)
    data[757:759] = _pad(nyusen_tosu, 2)
    data[759:760] = _pad(tenko_cd, 1)
    data[760:761] = _pad(siba_baba_cd, 1)
    data[761:762] = _pad(dirt_baba_cd, 1)
    data[854:856] = b'\r\n'
    return bytes(data)


def make_se_record(
    data_kubun="1", make_date="20260101",
    year="2026", month_day="0101", jyo_cd="05",
    kaiji="01", nichiji="01", race_num="01",
    umaban="01", kettonum="0000000001", bamei="テストウマ",
    **kwargs,
) -> bytes:
    """Create SE record (463 bytes)."""
    data = bytearray(463)
    data[0:2] = _pad("SE", 2)
    data[2:3] = _pad(data_kubun, 1)
    data[3:11] = _pad(make_date, 8)
    data[11:15] = _pad(year, 4)
    data[15:19] = _pad(month_day, 4)
    data[19:21] = _pad(jyo_cd, 2)
    data[21:23] = _pad(kaiji, 2)
    data[23:25] = _pad(nichiji, 2)
    data[25:27] = _pad(race_num, 2)
    data[27:28] = _pad("1", 1)       # Wakuban
    data[28:30] = _pad(umaban, 2)
    data[30:40] = _pad(kettonum, 10)
    data[40:76] = _pad(bamei, 36)
    data[461:463] = b'\r\n'
    return bytes(data)


def make_h1_record_full(
    data_kubun="4", make_date="20260101",
    year="2026", month_day="0101", jyo_cd="05",
    kaiji="01", nichiji="01", race_num="01",
    toroku_tosu="12", syusso_tosu="10",
    **kwargs,
) -> bytes:
    """Create full H1 record (28955 bytes) matching JV_H1_HYOSU_ZENKAKE."""
    data = bytearray(28955)
    data[0:2] = _pad("H1", 2)
    data[2:3] = _pad(data_kubun, 1)
    data[3:11] = _pad(make_date, 8)
    data[11:15] = _pad(year, 4)
    data[15:19] = _pad(month_day, 4)
    data[19:21] = _pad(jyo_cd, 2)
    data[21:23] = _pad(kaiji, 2)
    data[23:25] = _pad(nichiji, 2)
    data[25:27] = _pad(race_num, 2)
    data[27:29] = _pad(toroku_tosu, 2)
    data[29:31] = _pad(syusso_tosu, 2)
    for i in range(7):
        data[31 + i] = ord('7')
    data[38] = ord('3')
    for i in range(28):
        data[39 + i] = ord('0')
    for i in range(8):
        data[67 + i] = ord('0')
    for i in range(8):
        data[75 + i] = ord('0')
    num_horses = int(syusso_tosu)
    for i in range(28):
        offset = 83 + (15 * i)
        if i < num_horses:
            data[offset:offset + 2] = _num(i + 1, 2)
            data[offset + 2:offset + 13] = _num(1000 * (num_horses + 1 - i), 11)
            data[offset + 13:offset + 15] = _num(i + 1, 2)
        else:
            data[offset:offset + 15] = b' ' * 15
    for i in range(28):
        offset = 503 + (15 * i)
        if i < num_horses:
            data[offset:offset + 2] = _num(i + 1, 2)
            data[offset + 2:offset + 13] = _num(500 * (num_horses + 1 - i), 11)
            data[offset + 13:offset + 15] = _num(i + 1, 2)
        else:
            data[offset:offset + 15] = b' ' * 15
    for i in range(14):
        offset = 28799 + (11 * i)
        data[offset:offset + 11] = _num(0, 11)
    data[28953:28955] = b'\r\n'
    return bytes(data)


def make_h1_record_flat(
    data_kubun="4", make_date="20260101",
    year="2026", month_day="0101", jyo_cd="05",
    kaiji="01", nichiji="01", race_num="01",
    toroku_tosu="12", syusso_tosu="10",
    tan_uma="01", tan_hyo="00000010000",
    **kwargs,
) -> bytes:
    """Create flat H1 record (317 bytes) matching current parser."""
    data = bytearray(317)
    data[0:2] = _pad("H1", 2)
    data[2:3] = _pad(data_kubun, 1)
    data[3:11] = _pad(make_date, 8)
    data[11:15] = _pad(year, 4)
    data[15:19] = _pad(month_day, 4)
    data[19:21] = _pad(jyo_cd, 2)
    data[21:23] = _pad(kaiji, 2)
    data[23:25] = _pad(nichiji, 2)
    data[25:27] = _pad(race_num, 2)
    data[27:29] = _pad(toroku_tosu, 2)
    data[29:31] = _pad(syusso_tosu, 2)
    for i in range(7):
        data[31 + i] = ord('7')
    data[38] = ord('3')
    for i in range(3):
        data[39 + i] = ord('0')
    data[42:44] = _pad(tan_uma, 2)
    data[44:55] = _pad(tan_hyo, 11)
    data[55:57] = _pad("01", 2)
    data[315:317] = b'\r\n'
    return bytes(data)


def make_hr_record(
    data_kubun="1", make_date="20260101",
    year="2026", month_day="0101", jyo_cd="05",
    kaiji="01", nichiji="01", race_num="01",
    **kwargs,
) -> bytes:
    """Create HR record (719 bytes)."""
    data = bytearray(719)
    data[0:2] = _pad("HR", 2)
    data[2:3] = _pad(data_kubun, 1)
    data[3:11] = _pad(make_date, 8)
    data[11:15] = _pad(year, 4)
    data[15:19] = _pad(month_day, 4)
    data[19:21] = _pad(jyo_cd, 2)
    data[21:23] = _pad(kaiji, 2)
    data[23:25] = _pad(nichiji, 2)
    data[25:27] = _pad(race_num, 2)
    data[717:719] = b'\r\n'
    return bytes(data)


def make_wf_record(data_kubun="1", make_date="20260101", **kwargs) -> bytes:
    """Create WF record (169 bytes)."""
    data = bytearray(169)
    data[0:2] = _pad("WF", 2)
    data[2:3] = _pad(data_kubun, 1)
    data[3:11] = _pad(make_date, 8)
    data[167:169] = b'\r\n'
    return bytes(data)


def make_bn_record(data_kubun="1", make_date="20260101", **kwargs) -> bytes:
    """Create BN record (387 bytes)."""
    data = bytearray(387)
    data[0:2] = _pad("BN", 2)
    data[2:3] = _pad(data_kubun, 1)
    data[3:11] = _pad(make_date, 8)
    data[385:387] = b'\r\n'
    return bytes(data)


def make_ra_record_nar(**kwargs) -> bytes:
    """Create NAR RA record (same format, NAR jyo_cd)."""
    kwargs.setdefault("jyo_cd", "55")
    return make_ra_record(**kwargs)


def make_h1_record_nar_full(**kwargs) -> bytes:
    """Create NAR H1 full record (same format, NAR jyo_cd)."""
    kwargs.setdefault("jyo_cd", "55")
    return make_h1_record_full(**kwargs)
