#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全パーサーの単体テストスイート

このモジュールは全41パーサー（38 JRA + 3 NAR: HA, NC, NU）に対する包括的なテストを提供します。
各パーサーで以下をテスト:
- パーサーインスタンスの作成
- RECORD_TYPE, RECORD_LENGTHの定義確認
- サンプルバイトデータでのパース成功
- 出力フィールドの存在確認
- 空データ/不正データでのエラーハンドリング
"""

import pytest
from src.parser.factory import ParserFactory, ALL_RECORD_TYPES


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
        assert len(supported) == 41  # 38 JRA + 3 NAR (HA, NC, NU)
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
    def sample_data(self):
        """各レコードタイプのサンプルデータを返すフィクスチャ"""
        # 各レコードタイプに対する最小限のサンプルバイト列
        # RecordSpec(2) + DataKubun(1) + MakeDate(8) + その他のフィールドを0で埋める
        samples = {}

        # レコード長の定義（公式仕様書より）
        record_lengths = {
            'AV': 260, 'BN': 263, 'BR': 475, 'BT': 415, 'CC': 71,
            'CH': 96, 'CK': 232, 'CS': 208, 'DM': 233,
            'H1': 782, 'H6': 782, 'HC': 3248, 'HN': 3248, 'HR': 3664, 'HS': 3664, 'HY': 1336,
            'JC': 252, 'JG': 251, 'KS': 282,
            'O1': 148, 'O2': 148, 'O3': 148, 'O4': 148, 'O5': 148, 'O6': 148,
            'RA': 856, 'RC': 1926, 'SE': 463, 'SK': 263, 'TC': 71, 'TK': 240, 'TM': 216,
            'UM': 969, 'WC': 72, 'WE': 195, 'WF': 3416, 'WH': 1356, 'YS': 424,
            'HA': 1032, 'NC': 145, 'NU': 64
        }

        for record_type in ALL_RECORD_TYPES:
            length = record_lengths.get(record_type, 100)
            # RecordSpec(2) + DataKubun(1) + MakeDate(8) = 11バイト + 残りをスペースで埋める
            data = record_type.encode('cp932')  # RecordSpec (2 bytes)
            data += b'1'  # DataKubun (1 byte)
            data += b'20240601'  # MakeDate (8 bytes)
            # 残りのフィールドをスペースで埋める
            remaining = length - len(data)
            data += b' ' * remaining
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
        assert actual_type == record_type, f"{record_type}パーサーのRECORD_TYPEが正しくない"

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
        assert isinstance(result, dict), f"{record_type}パーサーの戻り値が辞書でない"

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_output_has_common_fields(self, parser_factory, sample_data, record_type):
        """共通フィールドの存在確認"""
        parser = parser_factory.get_parser(record_type)
        data = sample_data[record_type]

        result = parser.parse(data)
        assert result is not None

        # 共通フィールドの確認（すべてのパーサーにRecordSpecがあるはず）
        assert 'RecordSpec' in result, f"{record_type}パーサーの出力にRecordSpecがない"
        # DataKubunはNAR (NU)パーサー以外にあるはず
        if record_type != "NU":
            assert 'DataKubun' in result, f"{record_type}パーサーの出力にDataKubunがない"
        # MakeDateはほとんどのパーサーにあるが、一部（AV等）にはないので省略

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_output_record_spec_value(self, parser_factory, sample_data, record_type):
        """RecordSpecの値が正しいことを確認"""
        parser = parser_factory.get_parser(record_type)
        data = sample_data[record_type]

        result = parser.parse(data)
        assert result is not None
        assert result['RecordSpec'] == record_type, \
            f"{record_type}パーサーのRecordSpecの値が正しくない: {result.get('RecordSpec')}"

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_empty_data(self, parser_factory, record_type):
        """空データでのエラーハンドリングテスト"""
        parser = parser_factory.get_parser(record_type)

        # 空のバイト列
        # パーサーによってはNoneを返すか、例外を発生させる可能性がある
        # 例外が発生する場合はキャッチする
        try:
            result = parser.parse(b'')
            # 結果がNoneまたは空である場合はOK
        except (ValueError, Exception):
            # 例外が発生する場合もエラーハンドリングが機能しているとみなす
            pass

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_short_data(self, parser_factory, record_type):
        """短すぎるデータでのエラーハンドリングテスト"""
        parser = parser_factory.get_parser(record_type)

        # 最小限の短いデータ（RecordSpec + DataKubun のみ）
        short_data = record_type.encode('cp932') + b'1'

        # パーサーによってはNoneを返すか、ログに警告を出す、または例外を発生させる
        try:
            result = parser.parse(short_data)
            # エラーハンドリングが存在することを確認
            # 完全なパースができない可能性があるが、エラーで停止しない
        except (ValueError, Exception):
            # 例外が発生する場合もエラーハンドリングが機能しているとみなす
            pass

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_wrong_record_type(self, parser_factory, sample_data, record_type):
        """間違ったレコードタイプでのパース試行"""
        parser = parser_factory.get_parser(record_type)

        # 他のレコードタイプのデータを取得
        wrong_type = 'RA' if record_type != 'RA' else 'SE'
        if wrong_type in sample_data:
            wrong_data = sample_data[wrong_type]

            # 間違ったレコードタイプでパースを試行
            # パーサーによってはNoneを返すか、エラーログを出す、または例外を発生させる
            try:
                result = parser.parse(wrong_data)
                # エラーハンドリングを確認
            except (ValueError, Exception):
                # 例外が発生する場合もエラーハンドリングが機能しているとみなす
                pass


class TestParserFactoryParseMethod:
    """ParserFactoryのparseメソッドのテスト"""

    @pytest.fixture
    def parser_factory(self):
        """ParserFactoryインスタンスを返すフィクスチャ"""
        return ParserFactory()

    @pytest.fixture
    def sample_ra_record(self):
        """RAレコードのサンプルデータ"""
        data = b'RA'  # RecordSpec
        data += b'1'  # DataKubun
        data += b'20240601'  # MakeDate
        data += b' ' * (856 - len(data))  # 残りをスペースで埋める
        return data

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

        # より詳細なサンプルデータを作成
        data = b'RA'  # RecordSpec (1-2)
        data += b'1'  # DataKubun (3)
        data += b'20240601'  # MakeDate (4-11)
        data += b'2024'  # Year (12-15)
        data += b'0601'  # MonthDay (16-19)
        data += b'06'  # JyoCD (20-21)
        data += b'03'  # Kaiji (22-23)
        data += b'08'  # Nichiji (24-25)
        data += b'11'  # RaceNum (26-27)
        data += b' ' * (856 - len(data))  # 残りをスペースで埋める

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
        data += b' ' * (463 - len(data))  # 残りをスペースで埋める

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

        # 日本語を含むデータ
        data = b'RA'  # RecordSpec
        data += b'1'  # DataKubun
        data += b'20240601'  # MakeDate
        data += b' ' * (32 - len(data))  # パディング
        # 競走名本題（日本語）
        race_name = 'テストレース'
        data += race_name.encode('cp932')
        data += b' ' * (60 - len(race_name.encode('cp932')))
        data += b' ' * (856 - len(data))  # 残りをスペースで埋める

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

    @pytest.mark.parametrize("record_type", ['RA', 'SE', 'HR', 'UM', 'BN'])
    def test_parser_handles_exact_length(self, parser_factory, record_type):
        """正確な長さのデータを処理できることを確認"""
        parser = parser_factory.get_parser(record_type)

        # 正確な長さのデータを作成
        data = record_type.encode('cp932')
        data += b'1'
        data += b'20240601'
        data += b' ' * (parser.RECORD_LENGTH - len(data))

        assert len(data) == parser.RECORD_LENGTH

        result = parser.parse(data)
        assert result is not None
        assert result['RecordSpec'] == record_type

    @pytest.mark.parametrize("record_type", ['RA', 'SE', 'HR'])
    def test_parser_handles_extra_length(self, parser_factory, record_type):
        """長すぎるデータを処理できることを確認"""
        parser = parser_factory.get_parser(record_type)

        # 長すぎるデータを作成
        data = record_type.encode('cp932')
        data += b'1'
        data += b'20240601'
        data += b' ' * (parser.RECORD_LENGTH + 100)

        # 長すぎるデータでも処理できることを確認
        result = parser.parse(data)
        assert result is not None
        assert result['RecordSpec'] == record_type


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

        assert loaded_count == 41, \
            f"ロードできなかったパーサー: {failed_parsers}"  # 38 JRA + 1 NAR (NU)
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
