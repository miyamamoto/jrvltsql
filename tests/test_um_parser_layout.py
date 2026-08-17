#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""UMパーサーの 1609 バイトレイアウト検証

JV-Data仕様書 Ver.4.9.0.1「フォーマット」シート １３．競走馬マスタ の配置どおりに
レコードを組み立て、parse() が全項目を正しい位置から取り出すことを確認する。

レコードは**このファイルが組み立てた合成データ**で、JRA-VAN のデータは含まない
（実在する馬・馬主・生産者・調教師の情報は入っていない）。フォーマットだけが本物。
"""

import os
from uuid import uuid4

import pytest

from src.database.dual_handler import DualDatabase
from src.database.migration import SchemaMigrationError
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_types import get_table_column_types, get_table_primary_key_columns
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter, translate_standard_field_names
from src.importer.importer_optimized import OptimizedDataImporter
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
CHAKU = [
    "".join(f"{group * 6 + rank:03d}" for rank in range(1, 7))
    for group in range(27)
]

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
    "SogoChaku",
    "ChuoGokeiChaku",
    "SibaChokuChaku",
    "SibaMigiChaku",
    "SibaHidariChaku",
    "DirtChokuChaku",
    "DirtMigiChaku",
    "DirtHidariChaku",
    "SyogaiChaku",
    "SibaRyoChaku",
    "SibaYayaomoChaku",
    "SibaOmoChaku",
    "SibaFuryoChaku",
    "DirtRyoChaku",
    "DirtYayaomoChaku",
    "DirtOmoChaku",
    "DirtFuryoChaku",
    "SyogaiRyoChaku",
    "SyogaiYayaomoChaku",
    "SyogaiOmoChaku",
    "SyogaiFuryoChaku",
    "SibaShortChaku",
    "SibaMiddleChaku",
    "SibaLongChaku",
    "DirtShortChaku",
    "DirtMiddleChaku",
    "DirtLongChaku",
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


def build_record(
    *,
    data_kubun: str = "2",
    ketto_num: str = "2019900001",
    bamei: str = "テストウマアルファ",
):
    """仕様書の位置どおりに 1609 バイトを組み立てる（すき間があれば落ちる）。"""
    replacements = {
        "DataKubun": data_kubun.encode("ascii"),
        "KettoNum": ketto_num.encode("ascii"),
        "Bamei": _pad(bamei, 36, zenkaku=True),
    }
    record = bytearray()
    for name, position, size, value in FIELDS:
        value = replacements.get(name, value)
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
        delimiter = self.record[UMParser.RECORD_DELIMITER_START : UMParser.RECORD_LENGTH]
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


def parsed_record(**kwargs):
    parsed = UMParser().parse(build_record(**kwargs))
    assert parsed is not None
    return parsed


def test_um_standard_schema_preserves_the_official_registration_key():
    column_types = get_table_column_types("UMA")
    assert column_types["KettoNum"] == "TEXT"
    assert column_types["TorokuRaceSu"] == "TEXT"
    assert get_table_primary_key_columns("UMA") == ["KettoNum"]
    database = SQLiteDatabase({"path": ":memory:"})
    with database:
        database.execute(JRAVAN_SCHEMAS["UMA"])
        declared_types = {
            row["name"]: row["type"] for row in database.fetch_all("PRAGMA table_info(UMA)")
        }
    assert declared_types["KettoNum"] == "VARCHAR(10)"
    assert declared_types["DelDate"] == "VARCHAR(8)"
    assert declared_types["TorokuRaceSu"] == "VARCHAR(3)"


def test_um_standard_translation_covers_every_schema_field():
    translated = translate_standard_field_names(parsed_record(), "UMA")
    schema_columns = set(get_table_column_types("UMA"))
    assert set(translated) - {"Reserved_1608"} == schema_columns
    assert all(name not in translated for name in CHAKU_NAMES)
    assert "KyakusituKeiko" not in translated

    expected_prefixes = (
        "Sogo",
        "Chuo",
        "Ba1",
        "Ba2",
        "Ba3",
        "Ba4",
        "Ba5",
        "Ba6",
        "Ba7",
        "Jyotai1",
        "Jyotai2",
        "Jyotai3",
        "Jyotai4",
        "Jyotai5",
        "Jyotai6",
        "Jyotai7",
        "Jyotai8",
        "Jyotai9",
        "Jyotai10",
        "Jyotai11",
        "Jyotai12",
        "Kyori1",
        "Kyori2",
        "Kyori3",
        "Kyori4",
        "Kyori5",
        "Kyori6",
    )
    for group, prefix in enumerate(expected_prefixes):
        assert [translated[f"{prefix}Chakukaisu{index}"] for index in range(1, 7)] == [
            f"{group * 6 + rank:03d}" for rank in range(1, 7)
        ]
    assert [translated[f"Kyakusitu{index}"] for index in range(1, 5)] == [
        "001",
        "002",
        "003",
        "004",
    ]
    assert translated["TorokuRaceSu"] == "042"


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_um_standard_storage_keeps_distinct_keys_and_updates_exact_key(
    tmp_path,
    importer_class,
):
    database = SQLiteDatabase({"path": str(tmp_path / f"{importer_class.__name__}.db")})
    with database:
        database.create_table("UMA", JRAVAN_SCHEMAS["UMA"])
        importer = importer_class(database, use_jravan_schema=True)
        created = importer.import_records(
            iter(
                [
                    parsed_record(ketto_num="2019900001", bamei="第一登録馬"),
                    parsed_record(ketto_num="2019900002", bamei="第二登録馬"),
                ]
            )
        )
        updated = importer.import_records(
            iter(
                [
                    parsed_record(
                        data_kubun="2",
                        ketto_num="2019900001",
                        bamei="第一更新馬",
                    )
                ]
            )
        )
        rows = database.fetch_all(
            "SELECT KettoNum, Bamei, DelDate, SogoChakukaisu1, "
            "SogoChakukaisu6, Ba4Chakukaisu1, Jyotai12Chakukaisu6, "
            "Kyori6Chakukaisu6, Kyakusitu1, Kyakusitu4, TorokuRaceSu "
            "FROM UMA ORDER BY KettoNum"
        )

    assert created["records_imported"] == 2
    assert created["records_failed"] == 0
    assert updated["records_imported"] == 1
    assert updated["records_failed"] == 0
    assert rows == [
        {
            "KettoNum": "2019900001",
            "Bamei": "第一更新馬",
            "DelDate": "00000000",
            "SogoChakukaisu1": "001",
            "SogoChakukaisu6": "006",
            "Ba4Chakukaisu1": "031",
            "Jyotai12Chakukaisu6": "126",
            "Kyori6Chakukaisu6": 162,
            "Kyakusitu1": "001",
            "Kyakusitu4": "004",
            "TorokuRaceSu": "042",
        },
        {
            "KettoNum": "2019900002",
            "Bamei": "第二登録馬",
            "DelDate": "00000000",
            "SogoChakukaisu1": "001",
            "SogoChakukaisu6": "006",
            "Ba4Chakukaisu1": "031",
            "Jyotai12Chakukaisu6": "126",
            "Kyori6Chakukaisu6": 162,
            "Kyakusitu1": "001",
            "Kyakusitu4": "004",
            "TorokuRaceSu": "042",
        },
    ]


OBSOLETE_STANDARD_UMA_SCHEMA = """
    CREATE TABLE UMA (
        RecordSpec CHAR(2),
        DataKubun CHAR(1),
        MakeDate DATE,
        Bamei VARCHAR(36),
        PRIMARY KEY (Bamei)
    )
"""

UNSAFE_UNIQUE_STANDARD_UMA_SCHEMA = JRAVAN_SCHEMAS["UMA"].replace(
    "PRIMARY KEY (KettoNum)",
    "PRIMARY KEY (KettoNum), UNIQUE (DelDate)",
)


def _import_standard_um_records(database, entrypoint, records, auto_commit):
    if entrypoint == "data-batch":
        return DataImporter(database, use_jravan_schema=True).import_records(
            iter(records), auto_commit=auto_commit
        )
    if entrypoint == "optimized-batch":
        return OptimizedDataImporter(database, use_jravan_schema=True).import_records(
            iter(records), auto_commit=auto_commit
        )
    importer = DataImporter(database, use_jravan_schema=True)
    return [importer.import_single_record(record, auto_commit=auto_commit) for record in records]


@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
def test_um_standard_extra_unique_is_rejected_before_mutation(tmp_path, entrypoint, auto_commit):
    primary = SQLiteDatabase({"path": str(tmp_path / f"unique-{entrypoint}.db")})
    with primary:
        primary.execute(UNSAFE_UNIQUE_STANDARD_UMA_SCHEMA)
        primary.commit()
        before = primary.fetch_all(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type IN ('table', 'index') ORDER BY type, name"
        )
        with pytest.raises(SchemaMigrationError, match="UNIQUE"):
            _import_standard_um_records(
                primary,
                entrypoint,
                [
                    parsed_record(ketto_num="2019900001"),
                    parsed_record(ketto_num="2019900002"),
                ],
                auto_commit,
            )
        assert (
            primary.fetch_all(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type IN ('table', 'index') ORDER BY type, name"
            )
            == before
        )
        assert primary.fetch_one("SELECT COUNT(*) AS count FROM UMA")["count"] == 0


@pytest.mark.parametrize("unsafe_target", ("primary", "secondary"))
def test_um_standard_dual_rejects_extra_unique_on_either_backend(
    tmp_path, unsafe_target
):
    primary = SQLiteDatabase(
        {"path": str(tmp_path / f"{unsafe_target}-primary.db")}
    )
    secondary = SQLiteDatabase(
        {"path": str(tmp_path / f"{unsafe_target}-secondary.db")}
    )
    with primary, secondary:
        primary.execute(
            UNSAFE_UNIQUE_STANDARD_UMA_SCHEMA
            if unsafe_target == "primary"
            else JRAVAN_SCHEMAS["UMA"]
        )
        secondary.execute(
            UNSAFE_UNIQUE_STANDARD_UMA_SCHEMA
            if unsafe_target == "secondary"
            else JRAVAN_SCHEMAS["UMA"]
        )
        primary.commit()
        secondary.commit()
        dual = DualDatabase(primary, secondary)
        with pytest.raises(SchemaMigrationError, match="UNIQUE"):
            DataImporter(dual, use_jravan_schema=True).import_records(iter([parsed_record()]))
        assert primary.fetch_one("SELECT COUNT(*) AS count FROM UMA")["count"] == 0
        assert secondary.fetch_one("SELECT COUNT(*) AS count FROM UMA")["count"] == 0


@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize(
    "invalid_key",
    ("123456789", "12345678901", "ABCDEFGHIJ", "１２３４５６７８９０"),
    ids=("short", "long", "letters", "non-ascii"),
)
def test_um_standard_invalid_official_key_is_rejected_before_mutation(
    tmp_path, entrypoint, invalid_key
):
    database = SQLiteDatabase({"path": str(tmp_path / f"invalid-{entrypoint}.db")})
    record = parsed_record()
    record["KettoNum"] = invalid_key
    with database:
        database.execute(JRAVAN_SCHEMAS["UMA"])
        database.commit()
        with pytest.raises(SchemaMigrationError, match="KettoNum"):
            _import_standard_um_records(database, entrypoint, [record], True)
        assert database.fetch_one("SELECT COUNT(*) AS count FROM UMA")["count"] == 0


def test_um_standard_malformed_compact_body_is_rejected_before_mutation(tmp_path):
    database = SQLiteDatabase({"path": str(tmp_path / "malformed-body.db")})
    record = parsed_record()
    record["SogoChaku"] = "001"
    with database:
        database.execute(JRAVAN_SCHEMAS["UMA"])
        database.commit()
        with pytest.raises(SchemaMigrationError, match="SogoChaku"):
            DataImporter(database, use_jravan_schema=True).import_records(iter([record]))
        assert database.fetch_one("SELECT COUNT(*) AS count FROM UMA")["count"] == 0


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(
        {
            "host": os.getenv("POSTGRES_HOST") or os.getenv("PGHOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT") or os.getenv("PGPORT", "5432")),
            "database": os.getenv("POSTGRES_DB") or os.getenv("PGDATABASE", "jltsql_test"),
            "user": os.getenv("POSTGRES_USER") or os.getenv("PGUSER", "jltsql"),
            "password": os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD", ""),
            "connect_timeout": 5,
        }
    )
    schema_name = f"jlt_um_{uuid4().hex[:12]}"
    database.connect()
    try:
        database.execute(f"CREATE SCHEMA {schema_name}")
        database.execute(f"SET search_path TO {schema_name}")
        database.commit()
        yield database
    finally:
        try:
            database.rollback()
            database.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
            database.commit()
        finally:
            database.disconnect()


@pytest.mark.parametrize(
    ("replacement", "message"),
    (
        pytest.param(
            "PRIMARY KEY (KettoNum), UNIQUE (DelDate)",
            "UNIQUE",
            id="extra-unique",
        ),
        pytest.param(
            "PRIMARY KEY (KettoNum) DEFERRABLE INITIALLY DEFERRED",
            "primary key",
            id="deferrable-primary-key",
        ),
    ),
)
def test_um_postgresql_constraint_drift_is_rejected_before_mutation(
    postgresql_db, replacement, message
):
    postgresql_db.execute(JRAVAN_SCHEMAS["UMA"].replace("PRIMARY KEY (KettoNum)", replacement))
    postgresql_db.commit()
    before = postgresql_db.fetch_all(
        "SELECT contype AS type, condeferrable AS deferrable, "
        "condeferred AS deferred, pg_get_constraintdef(oid) AS definition "
        "FROM pg_constraint WHERE conrelid = to_regclass(?) ORDER BY contype, conname",
        ("uma",),
    )
    with pytest.raises(SchemaMigrationError, match=message):
        DataImporter(postgresql_db, use_jravan_schema=True).import_records(iter([parsed_record()]))
    postgresql_db.rollback()
    assert (
        postgresql_db.fetch_all(
            "SELECT contype AS type, condeferrable AS deferrable, "
            "condeferred AS deferred, pg_get_constraintdef(oid) AS definition "
            "FROM pg_constraint WHERE conrelid = to_regclass(?) "
            "ORDER BY contype, conname",
            ("uma",),
        )
        == before
    )
    assert postgresql_db.fetch_one('SELECT COUNT(*) AS "count" FROM uma')["count"] == 0


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_um_standard_wrong_key_is_rejected_before_any_mutation(tmp_path, importer_class):
    database = SQLiteDatabase({"path": str(tmp_path / f"legacy-{importer_class.__name__}.db")})
    with database:
        database.execute(OBSOLETE_STANDARD_UMA_SCHEMA)
        database.execute(
            "INSERT INTO UMA (RecordSpec, DataKubun, MakeDate, Bamei) VALUES (?, ?, ?, ?)",
            ("UM", "1", "20000101", "legacy-row"),
        )
        database.commit()
        before_columns = database.fetch_all("PRAGMA table_info(UMA)")
        before_rows = database.fetch_all("SELECT * FROM UMA")

        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database, use_jravan_schema=True).import_records(iter([parsed_record()]))

        assert database.fetch_all("PRAGMA table_info(UMA)") == before_columns
        assert database.fetch_all("SELECT * FROM UMA") == before_rows


def test_um_standard_single_record_respects_the_caller_transaction(tmp_path):
    database = SQLiteDatabase({"path": str(tmp_path / "single.db")})
    with database:
        database.create_table("UMA", JRAVAN_SCHEMAS["UMA"])
        importer = DataImporter(database, use_jravan_schema=True)

        database.begin_transaction()
        assert importer.import_single_record(parsed_record(), auto_commit=False) is True
        assert database.fetch_one("SELECT COUNT(*) AS count FROM UMA")["count"] == 1
        database.rollback()
        assert database.fetch_one("SELECT COUNT(*) AS count FROM UMA")["count"] == 0

        assert importer.import_single_record(parsed_record(), auto_commit=True) is True
        assert database.fetch_one(
            "SELECT KettoNum, DelDate, SogoChakukaisu1, Jyotai12Chakukaisu6, "
            "Kyori6Chakukaisu6, Kyakusitu4, TorokuRaceSu FROM UMA"
        ) == {
            "KettoNum": "2019900001",
            "DelDate": "00000000",
            "SogoChakukaisu1": "001",
            "Jyotai12Chakukaisu6": "126",
            "Kyori6Chakukaisu6": 162,
            "Kyakusitu4": "004",
            "TorokuRaceSu": "042",
        }


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_um_postgresql_standard_key_roundtrip_and_legacy_preflight(
    postgresql_db,
    importer_class,
):
    postgresql_db.execute(JRAVAN_SCHEMAS["UMA"])
    postgresql_db.commit()
    importer = importer_class(postgresql_db, use_jravan_schema=True)

    created = importer.import_records(
        iter(
            [
                parsed_record(ketto_num="2019900001", bamei="第一登録馬"),
                parsed_record(ketto_num="2019900002", bamei="第二登録馬"),
            ]
        )
    )
    updated = importer.import_records(
        iter([parsed_record(ketto_num="2019900001", bamei="第一更新馬")])
    )
    rows = postgresql_db.fetch_all(
        'SELECT kettonum AS "KettoNum", bamei AS "Bamei", '
        'deldate AS "DelDate", sogochakukaisu1 AS "SogoChakukaisu1", '
        'jyotai12chakukaisu6 AS "Jyotai12Chakukaisu6", '
        'kyori6chakukaisu6 AS "Kyori6Chakukaisu6", '
        'kyakusitu4 AS "Kyakusitu4", torokuracesu AS "TorokuRaceSu" '
        "FROM uma ORDER BY kettonum"
    )

    assert created["records_imported"] == 2
    assert created["records_failed"] == 0
    assert updated["records_imported"] == 1
    assert updated["records_failed"] == 0
    assert rows == [
        {
            "KettoNum": "2019900001",
            "Bamei": "第一更新馬",
            "DelDate": "00000000",
            "SogoChakukaisu1": "001",
            "Jyotai12Chakukaisu6": "126",
            "Kyori6Chakukaisu6": 162,
            "Kyakusitu4": "004",
            "TorokuRaceSu": "042",
        },
        {
            "KettoNum": "2019900002",
            "Bamei": "第二登録馬",
            "DelDate": "00000000",
            "SogoChakukaisu1": "001",
            "Jyotai12Chakukaisu6": "126",
            "Kyori6Chakukaisu6": 162,
            "Kyakusitu4": "004",
            "TorokuRaceSu": "042",
        },
    ]

    postgresql_db.execute("DROP TABLE uma")
    postgresql_db.execute(OBSOLETE_STANDARD_UMA_SCHEMA)
    postgresql_db.execute(
        "INSERT INTO uma (RecordSpec, DataKubun, MakeDate, Bamei) VALUES (?, ?, ?, ?)",
        ("UM", "1", "20000101", "legacy-row"),
    )
    postgresql_db.commit()
    before_columns = postgresql_db.fetch_all(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = 'uma' "
        "ORDER BY ordinal_position"
    )
    before_rows = postgresql_db.fetch_all("SELECT * FROM uma")

    with pytest.raises(SchemaMigrationError, match="primary key"):
        importer_class(postgresql_db, use_jravan_schema=True).import_records(
            iter([parsed_record()])
        )

    assert (
        postgresql_db.fetch_all(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = 'uma' "
            "ORDER BY ordinal_position"
        )
        == before_columns
    )
    assert postgresql_db.fetch_all("SELECT * FROM uma") == before_rows


def test_um_postgresql_single_record_preserves_expanded_body(postgresql_db):
    postgresql_db.execute(JRAVAN_SCHEMAS["UMA"])
    postgresql_db.commit()
    importer = DataImporter(postgresql_db, use_jravan_schema=True)

    assert importer.import_single_record(parsed_record(), auto_commit=True) is True
    assert postgresql_db.fetch_one(
        'SELECT kettonum AS "KettoNum", deldate AS "DelDate", '
        'sogochakukaisu1 AS "SogoChakukaisu1", '
        'jyotai12chakukaisu6 AS "Jyotai12Chakukaisu6", '
        'kyakusitu4 AS "Kyakusitu4", torokuracesu AS "TorokuRaceSu" FROM uma'
    ) == {
        "KettoNum": "2019900001",
        "DelDate": "00000000",
        "SogoChakukaisu1": "001",
        "Jyotai12Chakukaisu6": "126",
        "Kyakusitu4": "004",
        "TorokuRaceSu": "042",
    }
