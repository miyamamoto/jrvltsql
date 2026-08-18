#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全パーサーの単体テストスイート

このモジュールは全38パーサー（38 JRA）に対する包括的なテストを提供します。
各パーサーで以下をテスト:
- パーサーインスタンスの作成
- RECORD_TYPE, RECORD_LENGTHの定義確認
- サンプルバイトデータでのパース成功
- 出力フィールドの存在確認
- 空データ/不正データでのエラーハンドリング
"""

import pytest

from src.parser.factory import ALL_RECORD_TYPES, ParserFactory
from tests.fixtures.record_factory import (
    make_hn_record,
    make_hr_record,
    make_ra_record,
    make_se_record,
)

EXPANDED_RECORD_TYPES = {
    "DM", "H1", "H6", "O1", "O2", "O3", "O4", "O5", "O6", "TM", "WH"
}


def _first_record_or_none(result):
    """Normalize parser output for expanded odds parsers."""
    if isinstance(result, list):
        return result[0] if result else None
    return result


class TestParserFactory:
    """ParserFactoryのテスト"""

    @pytest.fixture
    def parser_factory(self):
        """ParserFactoryインスタンスを返すフィクスチャ"""
        return ParserFactory()

    def test_factory_initialization(self, parser_factory):
        """ファクトリの初期化テスト"""
        assert parser_factory is not None
        assert isinstance(parser_factory, ParserFactory)

    def test_supported_types(self, parser_factory):
        """サポートされているレコードタイプの確認"""
        supported = parser_factory.supported_types()
        assert len(supported) == 38  # 38 JRA
        assert supported == ALL_RECORD_TYPES

    def test_get_parser_invalid_type(self, parser_factory):
        """無効なレコードタイプでのパーサー取得テスト"""
        parser = parser_factory.get_parser("ZZ")
        assert parser is None

    def test_get_parser_empty_type(self, parser_factory):
        """空のレコードタイプでのパーサー取得テスト"""
        parser = parser_factory.get_parser("")
        assert parser is None

    def test_get_parser_none_type(self, parser_factory):
        """Noneのレコードタイプでのパーサー取得テスト"""
        parser = parser_factory.get_parser(None)
        assert parser is None


class TestIndividualParsers:
    """個別パーサーのテスト"""

    @pytest.fixture
    def parser_factory(self):
        """ParserFactoryインスタンスを返すフィクスチャ"""
        return ParserFactory()

    @pytest.fixture
    def sample_data(self, parser_factory):
        """各レコードタイプのサンプルデータを返すフィクスチャ"""
        # Every parser receives its exact declared physical length and CRLF.
        # Domain-specific master/array fields are populated below where a
        # blank official envelope is not itself a valid positive fixture.
        samples = {}

        for record_type in ALL_RECORD_TYPES:
            parser = parser_factory.get_parser(record_type)
            length = parser.RECORD_LENGTH
            # RecordSpec(2) + DataKubun(1) + MakeDate(8) = 11バイト + 残りをスペースで埋める
            data = record_type.encode('cp932')  # RecordSpec (2 bytes)
            # H1/H6 do not define status 1 in the official current contract.
            data += b"2" if record_type in {"H1", "H6"} else b"1"
            data += b'20240601'  # MakeDate (8 bytes)
            # 残りのフィールドをスペースで埋める
            remaining = length - len(data)
            data += b' ' * remaining
            data = data[:-2] + b"\r\n"
            if record_type == "SE":
                data = make_se_record(
                    make_date="20240601",
                    year="2024",
                    month_day="0601",
                    jyo_cd="06",
                    kaiji="03",
                    nichiji="08",
                    race_num="11",
                    umaban="01",
                    kettonum="2024012345",
                )
            if record_type == "HR":
                data = make_hr_record(
                    make_date="20240601",
                    year="2024",
                    month_day="0601",
                    jyo_cd="05",
                    kaiji="03",
                    nichiji="08",
                    race_num="11",
                )
            if record_type == "HN":
                data = make_hn_record(make_date="20240601")
            if record_type == "HS":
                # HS requires all three official key fields and a complete
                # current 200-byte body; a blank envelope is not positive.
                mutable = bytearray(data)
                mutable[11:21] = b"2022100105"
                mutable[21:31] = b"12345678  "
                mutable[31:41] = b"0000000000"
                mutable[41:45] = b"2022"
                mutable[45:51] = b"011001"
                mutable[171:179] = b"20240601"
                mutable[179:187] = b"20240602"
                mutable[187:188] = b"2"
                mutable[188:198] = b"0000000100"
                data = bytes(mutable)
            if record_type == "HC":
                # HC requires its complete four-part identity and all seven
                # fixed numeric time spans; a blank envelope is not valid.
                mutable = bytearray(data)
                mutable[11:12] = b"0"
                mutable[12:20] = b"20240601"
                mutable[20:24] = b"0630"
                mutable[24:34] = b"2020000001"
                mutable[34:38] = b"0480"
                mutable[38:41] = b"120"
                mutable[41:45] = b"0360"
                mutable[45:48] = b"120"
                mutable[48:52] = b"0240"
                mutable[52:55] = b"120"
                mutable[55:58] = b"120"
                data = bytes(mutable)
            if record_type == "AV":
                mutable = bytearray(data)
                mutable[11:15] = b"2024"
                mutable[15:19] = b"0601"
                mutable[19:21] = b"05"
                mutable[21:23] = b"03"
                mutable[23:25] = b"08"
                mutable[25:27] = b"11"
                mutable[27:35] = b"06010930"
                mutable[35:37] = b"01"
                mutable[37:73] = "テスト馬".encode("cp932").ljust(36, b" ")
                mutable[73:76] = b"001"
                data = bytes(mutable)
            if record_type == "DM":
                mutable = bytearray(data)
                mutable[11:15] = b"2024"
                mutable[15:19] = b"0601"
                mutable[19:21] = b"05"
                mutable[21:23] = b"03"
                mutable[23:25] = b"08"
                mutable[25:27] = b"11"
                mutable[27:31] = b"0930"
                mutable[31:33] = b"01"
                mutable[33:38] = b"10001"
                mutable[38:42] = b"0101"
                mutable[42:46] = b"0201"
                data = bytes(mutable)
            if record_type == "KS":
                mutable = bytearray(data)
                for start, size in (
                    (11, 5), (16, 1), (17, 8), (25, 8), (33, 8),
                    (227, 1), (228, 1), (229, 1), (230, 1), (251, 5),
                    (264, 16), (280, 2), (282, 10), (328, 2), (330, 1),
                    (331, 16), (347, 2), (349, 10), (395, 2), (397, 1),
                    (398, 16), (414, 2), (416, 10),
                    (462, 16), (478, 2), (480, 10),
                    (526, 16), (641, 2), (643, 10),
                    (689, 16), (804, 2), (806, 10),
                    (852, 16), (967, 2), (969, 10),
                ):
                    mutable[start : start + size] = b"0" * size
                mutable[1015:4171] = b"0" * 3156
                data = bytes(mutable)
            if record_type == "CK":
                mutable = bytearray(data)
                mutable[11:15] = b"2024"
                mutable[15:19] = b"0601"
                mutable[19:21] = b"05"
                mutable[21:23] = b"01"
                mutable[23:25] = b"01"
                mutable[25:27] = b"01"
                mutable[27:37] = b"2024000001"
                for start, end in (
                    (73, 1384),
                    (1423, 3863),
                    (3902, 6342),
                    (6476, 6596),
                    (6748, 6868),
                ):
                    mutable[start:end] = b"0" * (end - start)
                data = bytes(mutable)
            if record_type == "CS":
                # CS requires all four official key fields. A generic
                # space-filled record is not a valid positive fixture.
                mutable = bytearray(data)
                mutable[11:13] = b"08"
                mutable[13:17] = b"2400"
                mutable[17:19] = b"18"
                mutable[19:27] = b"20100101"
                mutable[27:33] = b"course"
                data = bytes(mutable)
            if record_type == "JG":
                # JG has fixed-width official key/code domains; a generic
                # space-filled record is not a valid positive fixture.
                mutable = bytearray(data)
                mutable[11:15] = b"2024"
                mutable[15:19] = b"0601"
                mutable[19:21] = b"05"
                mutable[21:23] = b"03"
                mutable[23:25] = b"08"
                mutable[25:27] = b"00"
                mutable[27:37] = b"2024000001"
                mutable[37:73] = "テスト除外馬".encode("cp932").ljust(36, b" ")
                mutable[73:76] = b"001"
                mutable[76:77] = b"1"
                mutable[77:78] = b"0"
                data = bytes(mutable)
            if record_type == "WC":
                # WC has a four-part fixed-width key, code domains, and 19
                # numeric timing fields; blanks are not a positive fixture.
                mutable = bytearray(data)
                mutable[11:12] = b"0"
                mutable[12:20] = b"20240601"
                mutable[20:24] = b"0630"
                mutable[24:34] = b"2020000001"
                mutable[34:35] = b"0"
                mutable[35:36] = b"0"
                mutable[36:37] = b"0"
                mutable[37:103] = b"0" * 66
                data = bytes(mutable)
            if record_type == "WE":
                # WE requires its complete seven-part key and one of the
                # official body shapes; a blank envelope is not a positive.
                mutable = bytearray(data)
                mutable[11:15] = b"2024"
                mutable[15:19] = b"0601"
                mutable[19:21] = b"05"
                mutable[21:23] = b"03"
                mutable[23:25] = b"08"
                mutable[25:33] = b"06010930"
                mutable[33:40] = b"1111000"
                data = bytes(mutable)
            if record_type == "TC":
                # TC requires its complete six-part race key plus valid
                # announcement and before/after start times.
                mutable = bytearray(data)
                mutable[11:15] = b"2024"
                mutable[15:19] = b"0601"
                mutable[19:21] = b"05"
                mutable[21:23] = b"03"
                mutable[23:25] = b"08"
                mutable[25:27] = b"11"
                mutable[27:35] = b"06010930"
                mutable[35:39] = b"1015"
                mutable[39:43] = b"1005"
                data = bytes(mutable)
            if record_type == "CC":
                # CC requires its complete six-part race key plus valid
                # announcement, distance, track, and reason fields.
                mutable = bytearray(data)
                mutable[11:15] = b"2024"
                mutable[15:19] = b"0601"
                mutable[19:21] = b"05"
                mutable[21:23] = b"03"
                mutable[23:25] = b"08"
                mutable[25:27] = b"11"
                mutable[27:35] = b"06010930"
                mutable[35:39] = b"2000"
                mutable[39:41] = b"18"
                mutable[41:45] = b"1800"
                mutable[45:47] = b"17"
                mutable[47:48] = b"1"
                data = bytes(mutable)
            if record_type == "TK":
                mutable = bytearray(data)
                mutable[11:15] = b"2024"
                mutable[15:19] = b"0601"
                mutable[19:21] = b"05"
                mutable[21:23] = b"03"
                mutable[23:25] = b"08"
                mutable[25:27] = b"11"
                mutable[652:655] = b"000"
                data = bytes(mutable)
            if record_type == "WF":
                # WF requires a real event-date key, five race composites,
                # initial-value flags, and the initial carryover amount even
                # for the status-1 announcement; blanks are not a positive
                # fixture. Sales/votes/balance/payouts keep their initial value.
                mutable = bytearray(data)
                mutable[11:15] = b"2024"
                mutable[15:19] = b"0602"
                mutable[19:21] = b"00"
                for slot in range(5):
                    start = 21 + slot * 8
                    mutable[start:start + 8] = b"05" + b"03" + b"08" + f"{slot + 8:02d}".encode()
                mutable[61:67] = b"000000"
                mutable[133:136] = b"000"
                mutable[136:151] = b"000000000000000"
                data = bytes(mutable)
            if record_type == "TM":
                mutable = bytearray(data)
                mutable[11:15] = b"2024"
                mutable[15:19] = b"0601"
                mutable[19:21] = b"05"
                mutable[21:23] = b"03"
                mutable[23:25] = b"08"
                mutable[25:27] = b"11"
                mutable[27:31] = b"0930"
                mutable[31:33] = b"01"
                mutable[33:37] = b"0101"
                data = bytes(mutable)
            if record_type == "WH":
                mutable = bytearray(data)
                mutable[11:15] = b"2024"
                mutable[15:19] = b"0601"
                mutable[19:21] = b"05"
                mutable[21:23] = b"03"
                mutable[23:25] = b"08"
                mutable[25:27] = b"11"
                mutable[27:35] = b"06010930"
                mutable[35:37] = b"01"
                mutable[37:73] = "テスト馬".encode("cp932").ljust(36, b" ")
                mutable[73:76] = b"480"
                mutable[76:77] = b"+"
                mutable[77:80] = b"005"
                data = bytes(mutable)
            if record_type == "JC":
                # JC requires the complete eight-part announcement identity
                # and both official before/after rider blocks. A blank body is
                # not a valid current positive fixture.
                mutable = bytearray(data)
                mutable[11:15] = b"2024"
                mutable[15:19] = b"0601"
                mutable[19:21] = b"05"
                mutable[21:23] = b"03"
                mutable[23:25] = b"08"
                mutable[25:27] = b"11"
                mutable[27:35] = b"06010930"
                mutable[35:37] = b"01"
                mutable[37:73] = "テスト馬".encode("cp932").ljust(36, b" ")
                mutable[73:76] = b"550"
                mutable[76:81] = b"01234"
                mutable[81:115] = "新騎手".encode("cp932").ljust(34, b" ")
                mutable[115:116] = b"0"
                mutable[116:119] = b"560"
                mutable[119:124] = b"05678"
                mutable[124:158] = "旧騎手".encode("cp932").ljust(34, b" ")
                mutable[158:159] = b"9"
                data = bytes(mutable)
            samples[record_type] = data

        return samples

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_creation(self, parser_factory, record_type):
        """パーサーインスタンスの作成テスト"""
        parser = parser_factory.get_parser(record_type)
        assert parser is not None, f"{record_type}パーサーの作成に失敗"

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_has_record_type(self, parser_factory, record_type):
        """RECORD_TYPE属性の存在確認"""
        parser = parser_factory.get_parser(record_type)
        # RECORD_TYPE または record_type 属性をチェック
        has_rt = hasattr(parser, 'RECORD_TYPE') or hasattr(parser, 'record_type')
        assert has_rt, f"{record_type}パーサーにRECORD_TYPE/record_type属性がない"

        actual_type = getattr(parser, 'RECORD_TYPE', None) or getattr(parser, 'record_type', None)
        # Aliased record types (e.g., NK -> KS) use the base parser's RECORD_TYPE
        from src.parser.factory import PARSER_ALIASES
        expected = PARSER_ALIASES.get(record_type, record_type)
        assert actual_type == expected, f"{record_type}パーサーのRECORD_TYPEが正しくない (got {actual_type}, expected {expected})"

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_has_record_length(self, parser_factory, record_type):
        """RECORD_LENGTH属性の存在確認（オプション）"""
        parser = parser_factory.get_parser(record_type)
        # RECORD_LENGTH属性はオプション（BaseParserベースのパーサーには無い場合がある）
        # ただし、自動生成パーサー（RA, SE等）には存在する
        if hasattr(parser, 'RECORD_LENGTH'):
            assert parser.RECORD_LENGTH > 0, f"{record_type}パーサーのRECORD_LENGTHが不正"

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_parse_method_exists(self, parser_factory, record_type):
        """parseメソッドの存在確認"""
        parser = parser_factory.get_parser(record_type)
        assert hasattr(parser, 'parse'), f"{record_type}パーサーにparseメソッドがない"
        assert callable(parser.parse), f"{record_type}パーサーのparseメソッドが呼び出し可能でない"

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_parse_sample_data(self, parser_factory, sample_data, record_type):
        """サンプルデータでのパース成功テスト"""
        parser = parser_factory.get_parser(record_type)
        data = sample_data[record_type]

        result = parser.parse(data)
        assert result is not None, f"{record_type}パーサーがサンプルデータのパースに失敗"
        if record_type in EXPANDED_RECORD_TYPES:
            assert isinstance(result, list), f"{record_type}パーサーの戻り値がリストでない"
            assert all(isinstance(row, dict) for row in result), f"{record_type}パーサーのリスト要素が辞書でない"
        else:
            assert isinstance(result, dict), f"{record_type}パーサーの戻り値が辞書でない"

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_output_has_common_fields(self, parser_factory, sample_data, record_type):
        """共通フィールドの存在確認"""
        parser = parser_factory.get_parser(record_type)
        data = sample_data[record_type]

        result = parser.parse(data)
        assert result is not None
        record = _first_record_or_none(result)
        if record is None:
            assert record_type in EXPANDED_RECORD_TYPES
            return

        # 共通フィールドの確認（すべてのパーサーにRecordSpecがあるはず）
        assert 'RecordSpec' in record, f"{record_type}パーサーの出力にRecordSpecがない"
        # DataKubunは基本的に全パーサーにあるはず
        assert 'DataKubun' in record, f"{record_type}パーサーの出力にDataKubunがない"
        # MakeDateはほとんどのパーサーにあるが、一部（AV等）にはないので省略

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_output_record_spec_value(self, parser_factory, sample_data, record_type):
        """RecordSpecの値が正しいことを確認"""
        parser = parser_factory.get_parser(record_type)
        data = sample_data[record_type]

        result = parser.parse(data)
        assert result is not None
        record = _first_record_or_none(result)
        if record is None:
            assert record_type in EXPANDED_RECORD_TYPES
            return
        assert record['RecordSpec'] == record_type, \
            f"{record_type}パーサーのRecordSpecの値が正しくない: {record.get('RecordSpec')}"

class TestParserFactoryParseMethod:
    """ParserFactoryのparseメソッドのテスト"""

    @pytest.fixture
    def parser_factory(self):
        """ParserFactoryインスタンスを返すフィクスチャ"""
        return ParserFactory()

    @pytest.fixture
    def sample_ra_record(self):
        """RAレコードのサンプルデータ"""
        return make_ra_record(make_date="20240601")

    def test_factory_parse_valid_record(self, parser_factory, sample_ra_record):
        """有効なレコードのパーステスト"""
        result = parser_factory.parse(sample_ra_record)
        assert result is not None
        assert isinstance(result, dict)
        assert result['RecordSpec'] == 'RA'

    def test_factory_parse_empty_record(self, parser_factory):
        """空レコードのパーステスト"""
        result = parser_factory.parse(b'')
        assert result is None

    def test_factory_parse_short_record(self, parser_factory):
        """短すぎるレコードのパーステスト"""
        result = parser_factory.parse(b'R')
        assert result is None

    def test_factory_parse_invalid_record_type(self, parser_factory):
        """無効なレコードタイプのパーステスト"""
        data = b'ZZ' + b'1' + b'20240601' + b' ' * 100
        result = parser_factory.parse(data)
        assert result is None


class TestParserCaching:
    """パーサーキャッシングのテスト"""

    @pytest.fixture
    def parser_factory(self):
        """ParserFactoryインスタンスを返すフィクスチャ"""
        return ParserFactory()

    def test_parser_caching(self, parser_factory):
        """同じパーサーが再利用されることを確認"""
        parser1 = parser_factory.get_parser('RA')
        parser2 = parser_factory.get_parser('RA')

        # 同じインスタンスが返されることを確認
        assert parser1 is parser2

    def test_different_parsers_are_different(self, parser_factory):
        """異なるパーサーが異なるインスタンスであることを確認"""
        parser_ra = parser_factory.get_parser('RA')
        parser_se = parser_factory.get_parser('SE')

        # 異なるインスタンスが返されることを確認
        assert parser_ra is not parser_se
        assert parser_ra.RECORD_TYPE == 'RA'
        assert parser_se.RECORD_TYPE == 'SE'


class TestParserFieldExtraction:
    """フィールド抽出の詳細テスト"""

    @pytest.fixture
    def parser_factory(self):
        """ParserFactoryインスタンスを返すフィクスチャ"""
        return ParserFactory()

    def test_ra_parser_field_extraction(self, parser_factory):
        """RAパーサーのフィールド抽出テスト"""
        parser = parser_factory.get_parser('RA')

        data = make_ra_record(
            make_date="20240601",
            year="2024",
            month_day="0601",
            jyo_cd="06",
            kaiji="03",
            nichiji="08",
            race_num="11",
        )

        result = parser.parse(data)

        assert result is not None
        assert result['RecordSpec'] == 'RA'
        assert result['DataKubun'] == '1'
        assert result['MakeDate'] == '20240601'
        assert result['Year'] == '2024'
        assert result['MonthDay'] == '0601'
        assert result['JyoCD'] == '06'
        assert result['RaceNum'] == '11'

    def test_se_parser_field_extraction(self, parser_factory):
        """SEパーサーのフィールド抽出テスト"""
        parser = parser_factory.get_parser('SE')

        # より詳細なサンプルデータを作成
        data = b'SE'  # RecordSpec (1-2)
        data += b'1'  # DataKubun (3)
        data += b'20240601'  # MakeDate (4-11)
        data += b'2024'  # Year (12-15)
        data += b'0601'  # MonthDay (16-19)
        data += b'06'  # JyoCD (20-21)
        data += b'03'  # Kaiji (22-23)
        data += b'08'  # Nichiji (24-25)
        data += b'11'  # RaceNum (26-27)
        data += b'1'  # Wakuban (28)
        data += b'01'  # Umaban (29-30)
        data += b'2024012345'  # KettoNum (31-40)
        data += b' ' * (555 - len(data) - 2) + b'\r\n'

        result = parser.parse(data)

        assert result is not None
        assert result['RecordSpec'] == 'SE'
        assert result['DataKubun'] == '1'
        assert result['MakeDate'] == '20240601'
        assert result['Year'] == '2024'
        assert result['Wakuban'] == '1'
        assert result['Umaban'] == '01'


class TestParserEncodingHandling:
    """エンコーディング処理のテスト"""

    @pytest.fixture
    def parser_factory(self):
        """ParserFactoryインスタンスを返すフィクスチャ"""
        return ParserFactory()

    def test_shift_jis_encoding(self, parser_factory):
        """CP932エンコーディングのテスト"""
        parser = parser_factory.get_parser('RA')

        race_name = 'テストレース'
        data = make_ra_record(make_date="20240601", hondai=race_name)

        result = parser.parse(data)

        assert result is not None
        assert result['RecordSpec'] == 'RA'
        assert 'Hondai' in result
        assert result['Hondai'] == 'テストレース'


class TestParserRobustness:
    """パーサーの堅牢性テスト"""

    @pytest.fixture
    def parser_factory(self):
        """ParserFactoryインスタンスを返すフィクスチャ"""
        return ParserFactory()

    @pytest.mark.parametrize("record_type", ['RA', 'SE', 'HR', 'UM', 'BN', 'BR', 'CH'])
    def test_parser_handles_exact_length(self, parser_factory, record_type):
        """正確な長さのデータを処理できることを確認"""
        parser = parser_factory.get_parser(record_type)

        # 正確な長さのデータを作成
        if record_type == "SE":
            data = make_se_record(make_date="20240601")
        elif record_type == "HR":
            data = make_hr_record(make_date="20240601")
        else:
            data = record_type.encode('cp932')
            data += b'1'
            data += b'20240601'
            data += b' ' * (parser.RECORD_LENGTH - len(data))
            data = data[:-2] + b"\r\n"

        assert len(data) == parser.RECORD_LENGTH

        result = parser.parse(data)
        assert result is not None
        assert result['RecordSpec'] == record_type

    @pytest.mark.parametrize("record_type", ['RA', 'SE', 'HR'])
    def test_parser_rejects_extra_length(self, parser_factory, record_type):
        """Trailing bytes cannot be accepted as an official fixed record."""
        parser = parser_factory.get_parser(record_type)

        # Keep every other physical-record condition valid so this regression
        # isolates the oversized length rather than also failing on CRLF.
        data = record_type.encode('cp932')
        data += b'1'
        data += b'20240601'
        data += b' ' * (parser.RECORD_LENGTH + 100 - len(data) - 2)
        data += b'\r\n'

        assert len(data) == parser.RECORD_LENGTH + 100

        result = parser.parse(data)
        assert result is None


class TestAllParsersComprehensive:
    """全パーサーの包括的テスト"""

    @pytest.fixture
    def parser_factory(self):
        """ParserFactoryインスタンスを返すフィクスチャ"""
        return ParserFactory()

    def test_all_parsers_can_be_loaded(self, parser_factory):
        """全38パーサーが正常にロードできることを確認"""
        loaded_count = 0
        failed_parsers = []

        for record_type in ALL_RECORD_TYPES:
            parser = parser_factory.get_parser(record_type)
            if parser is not None:
                loaded_count += 1
            else:
                failed_parsers.append(record_type)

        assert loaded_count == 38, \
            f"ロードできなかったパーサー: {failed_parsers}"
        assert len(failed_parsers) == 0

    def test_all_parsers_have_consistent_interface(self, parser_factory):
        """全パーサーが一貫したインターフェースを持つことを確認"""
        for record_type in ALL_RECORD_TYPES:
            parser = parser_factory.get_parser(record_type)

            # 必須属性の確認（RECORD_TYPE または record_type）
            has_rt = hasattr(parser, 'RECORD_TYPE') or hasattr(parser, 'record_type')
            assert has_rt, f"{record_type}パーサーにRECORD_TYPE/record_type属性がない"

            # parseメソッドは必須
            assert hasattr(parser, 'parse'), f"{record_type}パーサーにparseメソッドがない"

            # メソッドが呼び出し可能であることを確認
            assert callable(parser.parse), f"{record_type}パーサーのparseメソッドが呼び出し可能でない"


if __name__ == '__main__':
    # pytestを実行
    pytest.main([__file__, '-v', '--tb=short'])
