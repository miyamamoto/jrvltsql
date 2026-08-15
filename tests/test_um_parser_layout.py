#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""UMパーサーの 1609 バイトレイアウト検証

JV-Data仕様書 Ver.4.9.0.1「フォーマット」シート １３．競走馬マスタ の配置どおりに
レコードを組み立て、parse() が全項目を正しい位置から取り出すことを確認する。

レコードは**このファイルが組み立てた合成データ**で、JRA-VAN のデータは含まない
（実在する馬・馬主・生産者・調教師の情報は入っていない）。フォーマットだけが本物。
"""

import pytest

from src.parser.um_parser import UMParser

ZENKAKU_SPACE = b"\x81\x40"


def _pad(value, size, zenkaku=False):
    """cp932 に符号化して size バイトへ詰める。"""
    encoded = value.encode("cp932")
    assert len(encoded) <= size, f"{value!r} is {len(encoded)} bytes, over {size}"
    filler = ZENKAKU_SPACE if zenkaku else b" "
    remainder = size - len(encoded)
    assert remainder % len(filler) == 0, f"{value!r} cannot be padded to {size}"
    return encoded + filler * (remainder // len(filler))


# 項番 -> (フィールド名, 位置(1始まり), バイト数, 値)。仕様書の「位置」をそのまま持つ。
PEDIGREE = [(f"112990{i:04d}", f"テストケットウ{i:02d}") for i in range(1, 15)]
CHAKU = [f"{i:03d}" * 6 for i in range(1, 28)]

FIELDS = [
    ("RecordSpec", 1, 2, b"UM"),
    ("DataKubun", 3, 1, b"2"),
    ("MakeDate", 4, 8, b"20260801"),
    ("KettoNum", 12, 10, b"2019900001"),
    ("DelKubun", 22, 1, b"3"),
    ("RegDate", 23, 8, b"20210401"),
    ("DelDate", 31, 8, b"00000000"),
    ("BirthDate", 39, 8, b"20190315"),
    ("Bamei", 47, 36, _pad("テストウマアルファ", 36, zenkaku=True)),
    ("BameiKana", 83, 36, _pad("ﾃｽﾄｳﾏｱﾙﾌｧ", 36)),
    ("BameiEng", 119, 60, _pad("Test Horse Alpha", 60)),
    ("ZaikyuFlag", 179, 1, b"4"),
    ("Reserved", 180, 19, _pad("RESERVED-180", 19)),
    ("UmaKigoCD", 199, 2, b"00"),
    ("SexCD", 201, 1, b"5"),
    ("HinsyuCD", 202, 1, b"6"),
    ("KeiroCD", 203, 2, b"01"),
]
# 項番18 <3代血統情報> 位置205 繰返14 46バイト（繁殖登録番号10 + 馬名36）
for slot, (num, name) in enumerate(PEDIGREE, start=1):
    base = 205 + (slot - 1) * 46
    FIELDS.append((f"Ketto3InfoHansyokuNum{slot}", base, 10, num.encode("ascii")))
    FIELDS.append((f"Ketto3InfoBamei{slot}", base + 10, 36, _pad(name, 36, zenkaku=True)))
FIELDS += [
    ("TozaiCD", 849, 1, b"7"),
    ("ChokyosiCode", 850, 5, b"99001"),
    ("ChokyosiRyakusyo", 855, 8, _pad("テスト師", 8, zenkaku=True)),
    ("Syotai", 863, 20, _pad("招待地域", 20, zenkaku=True)),
    ("BreederCode", 883, 8, b"99900001"),
    ("BreederName", 891, 72, _pad("テスト牧場", 72, zenkaku=True)),
    ("SanchiName", 963, 20, _pad("テスト町", 20, zenkaku=True)),
    ("BanusiCode", 983, 6, b"990001"),
    ("BanusiName", 989, 64, _pad("テスト馬主", 64, zenkaku=True)),
    ("RuikeiHonsyoHeiti", 1053, 9, b"000123401"),
    ("RuikeiHonsyoSyogai", 1062, 9, b"000123402"),
    ("RuikeiFukaHeichi", 1071, 9, b"000123403"),
    ("RuikeiFukaSyogai", 1080, 9, b"000123404"),
    ("RuikeiSyutokuHeichi", 1089, 9, b"000123405"),
    ("RuikeiSyutokuSyogai", 1098, 9, b"000123406"),
]
CHAKU_NAMES = [
    "SogoChaku", "ChuoGokeiChaku",
    "SibaChokuChaku", "SibaMigiChaku", "SibaHidariChaku",
    "DirtChokuChaku", "DirtMigiChaku", "DirtHidariChaku", "SyogaiChaku",
    "SibaRyoChaku", "SibaYayaomoChaku", "SibaOmoChaku", "SibaFuryoChaku",
    "DirtRyoChaku", "DirtYayaomoChaku", "DirtOmoChaku", "DirtFuryoChaku",
    "SyogaiRyoChaku", "SyogaiYayaomoChaku", "SyogaiOmoChaku", "SyogaiFuryoChaku",
    "SibaShortChaku", "SibaMiddleChaku", "SibaLongChaku",
    "DirtShortChaku", "DirtMiddleChaku", "DirtLongChaku",
]
# 項番34-60 着回数 位置1107 から 18バイトずつ。値を項番ごとに変えて、
# 1つずれたら別の数字が出るようにする。
for index, (name, value) in enumerate(zip(CHAKU_NAMES, CHAKU)):
    FIELDS.append((name, 1107 + index * 18, 18, value.encode("ascii")))
FIELDS += [
    ("KyakusituKeiko", 1593, 12, b"001002003004"),
    ("TorokuRaceSu", 1605, 3, b"042"),
    ("Reserved_1608", 1608, 2, b"\r\n"),
]


def build_record():
    """仕様書の位置どおりに 1609 バイトを組み立てる（すき間があれば落ちる）。"""
    record = bytearray()
    for name, position, size, value in FIELDS:
        assert len(value) == size, f"{name}: {len(value)} != {size}"
        assert len(record) == position - 1, f"{name}: gap at {len(record)} (want {position - 1})"
        record += value
    assert len(record) == UMParser.RECORD_LENGTH, len(record)
    return bytes(record)


EXPECTED = {name: value.decode("cp932").strip() for name, _, _, value in FIELDS}


class TestUMParserLayout:
    """仕様書の位置と parse() の読み出し位置が一致していることの検証"""

    def setup_method(self):
        self.parser = UMParser()
        self.record = build_record()

    def test_record_length_matches_the_spec(self):
        assert UMParser.RECORD_LENGTH == 1609
        assert len(self.record) == UMParser.RECORD_LENGTH

    def test_record_delimiter_closes_the_layout(self):
        delimiter = self.record[UMParser.RECORD_DELIMITER_START:UMParser.RECORD_LENGTH]
        assert delimiter == b"\r\n"

    def test_every_field_uses_a_distinct_decoded_sentinel(self):
        assert len(set(EXPECTED.values())) == len(EXPECTED)

    @pytest.mark.parametrize("field_name", sorted(EXPECTED))
    def test_every_field_is_read_from_its_spec_position(self, field_name):
        row = self.parser.parse(self.record)
        assert row[field_name] == EXPECTED[field_name]

    def test_parser_emits_exactly_the_spec_fields(self):
        assert set(self.parser.parse(self.record)) == set(EXPECTED)


class TestUMParserExactLayoutEnforcement:
    """長さ 1609・終端 CRLF ちょうどのレコードだけを受理することの検証

    旧仕様（1577 バイト）や区切りずれのレコードを部分抽出してしまうと、
    壊れた競走馬マスタ行が黙って取り込まれるため、None で拒否する。
    """

    def setup_method(self):
        self.parser = UMParser()
        self.record = build_record()

    def test_exact_1609_byte_crlf_record_is_accepted(self):
        row = self.parser.parse(self.record)
        assert row is not None
        assert row["KettoNum"] == EXPECTED["KettoNum"]

    @pytest.mark.parametrize(
        "mutate",
        [
            pytest.param(lambda r: r[:1575] + b"\r\n", id="legacy-1577-crlf"),
            pytest.param(lambda r: r[:1608], id="short-1608"),
            pytest.param(lambda r: r + b" ", id="long-1610"),
            pytest.param(lambda r: r[:1607] + b"\n\r", id="delimiter-lfcr"),
            pytest.param(lambda r: r[:1607] + b"  ", id="delimiter-spaces"),
        ],
    )
    def test_unsupported_record_returns_none(self, mutate):
        assert self.parser.parse(mutate(self.record)) is None
