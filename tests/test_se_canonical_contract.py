from hashlib import sha256

import pytest

from src.importer.importer import convert_record_types
from src.parser.canonical import canonicalize_se_fields
from src.parser.se_parser import SEParser
from tests.fixtures.record_factory import make_se_record


def _record(**fields: str) -> bytes:
    raw = bytearray(make_se_record())
    positions = {
        "Futan": (288, 291),
        "FutanBefore": (291, 294),
        "BaTaijyu": (324, 327),
        "ZogenFugo": (327, 328),
        "ZogenSa": (328, 331),
        "Time": (338, 342),
        "Odds": (359, 363),
        "Honsyokin": (365, 373),
        "Fukasyokin": (373, 381),
        "HaronTimeL4": (387, 390),
        "HaronTimeL3": (390, 393),
        "TimeDiff": (531, 535),
        "DMTime": (537, 542),
        "DMGosaP": (542, 546),
        "DMGosaM": (546, 550),
    }
    for name, value in fields.items():
        start, end = positions[name]
        encoded = value.encode("ascii")
        assert len(encoded) == end - start
        raw[start:end] = encoded
    return bytes(raw)


def test_se_canonical_units_and_import_schema() -> None:
    raw = _record(
        Futan="570",
        FutanBefore="560",
        BaTaijyu="508",
        ZogenFugo="+",
        ZogenSa="003",
        Time="1351",
        Odds="0070",
        Honsyokin="00008000",
        Fukasyokin="00000012",
        HaronTimeL4="482",
        HaronTimeL3="355",
        TimeDiff="+008",
        DMTime="11350",
        DMGosaP="0123",
        DMGosaM="0045",
    )
    parsed = SEParser().parse(raw)
    assert parsed is not None
    assert sha256(raw).hexdigest() == "d56a31980c3c35663736fd9f6da4098b84a1d2b1ea41450af1ba208972157df7"
    assert parsed["Futan"] == "570"
    assert parsed["BaTaijyu"] == "508"
    assert parsed["Time"] == "1351"
    assert parsed["ProviderBaTaijyuRaw"] == "508"
    assert parsed["ProviderRaceTimeRaw"] == "1351"
    assert parsed["ParserContractVersion"] == 2
    assert parsed["FutanKg"] == 57.0
    assert parsed["FutanBeforeKg"] == 56.0
    assert parsed["BaTaijyuKg"] == 508
    assert parsed["ZogenSaKg"] == 3
    assert parsed["RaceTimeSeconds"] == 95.1
    assert parsed["OddsMultiplier"] == 7.0
    assert parsed["HonsyokinYen"] == 800_000
    assert parsed["FukasyokinYen"] == 1_200
    assert parsed["HaronTimeL4Seconds"] == 48.2
    assert parsed["HaronTimeL3Seconds"] == 35.5
    assert parsed["TimeDiffSeconds"] == 0.8
    assert parsed["DMTimeSeconds"] == 73.5
    assert parsed["DMGosaPSeconds"] == 1.23
    assert parsed["DMGosaMSeconds"] == 0.45

    converted = convert_record_types(parsed, "NL_SE")
    for name in (
        "FutanKg",
        "BaTaijyuKg",
        "RaceTimeSeconds",
        "HonsyokinYen",
        "HaronTimeL3Seconds",
        "ProviderBaTaijyuRaw",
        "ProviderRaceTimeRaw",
    ):
        assert converted[name] == parsed[name]


@pytest.mark.parametrize(
    ("field", "value", "canonical"),
    [
        ("BaTaijyu", "999", "BaTaijyuKg"),
        ("BaTaijyu", "000", "BaTaijyuKg"),
        ("BaTaijyu", "26C", "BaTaijyuKg"),
        ("Time", "1999", "RaceTimeSeconds"),
        ("Time", "26C1", "RaceTimeSeconds"),
        ("HaronTimeL3", "***", "HaronTimeL3Seconds"),
        ("Odds", "----", "OddsMultiplier"),
    ],
)
def test_se_canonical_malformed_values_fail_closed(
    field: str, value: str, canonical: str
) -> None:
    assert canonicalize_se_fields({field: value})[canonical] is None


def test_se_record_length_and_crlf_are_strict() -> None:
    raw = _record()
    parser = SEParser()
    assert parser.parse(raw) is not None
    assert parser.parse(raw[:-1]) is None
    assert parser.parse(raw + b" ") is None
    assert parser.parse(raw[:-2] + b"  ") is None


def test_maximum_odds_is_not_mistaken_for_a_sentinel() -> None:
    parsed = SEParser().parse(_record(Odds="9999"))
    assert parsed is not None
    assert parsed["OddsMultiplier"] == pytest.approx(999.9)


@pytest.mark.parametrize(("raw", "seconds"), [("+008", 0.8), ("-008", -0.8)])
def test_time_difference_sign_is_preserved(raw: str, seconds: float) -> None:
    parsed = SEParser().parse(_record(TimeDiff=raw))
    assert parsed is not None
    assert parsed["TimeDiffSeconds"] == seconds


def test_unsigned_time_difference_and_initial_dm_error_are_missing() -> None:
    parsed = SEParser().parse(_record(TimeDiff="0008", DMGosaP="0000", DMGosaM="0000"))
    assert parsed is not None
    assert parsed["TimeDiffSeconds"] is None
    assert parsed["DMGosaPSeconds"] is None
    assert parsed["DMGosaMSeconds"] is None


def test_jravan_uma_race_schema_keeps_canonical_and_audit_fields() -> None:
    parsed = SEParser().parse(_record(Futan="570", BaTaijyu="508", Time="1351"))
    assert parsed is not None
    converted = convert_record_types(parsed, "UMA_RACE")
    assert converted["FutanKg"] == 57.0
    assert converted["BaTaijyuKg"] == 508
    assert converted["RaceTimeSeconds"] == 95.1
    assert converted["ProviderRaceTimeRaw"] == "1351"


def test_maximum_prize_value_uses_64_bit_yen_domain() -> None:
    parsed = SEParser().parse(_record(Honsyokin="99999999"))
    assert parsed is not None
    assert parsed["HonsyokinYen"] == 9_999_999_900


def test_haron_cancellation_sentinel_is_missing() -> None:
    parsed = SEParser().parse(_record(HaronTimeL4="999", HaronTimeL3="999"))
    assert parsed is not None
    assert parsed["HaronTimeL4Seconds"] is None
    assert parsed["HaronTimeL3Seconds"] is None


def test_existing_jravan_table_is_additively_migrated(tmp_path) -> None:
    from src.database.sqlite_handler import SQLiteDatabase
    from src.importer.importer import DataImporter

    db = SQLiteDatabase({"path": str(tmp_path / "legacy-jravan.db")})
    with db:
        db.execute(
            "CREATE TABLE UMA_RACE (Year INTEGER, MonthDay INTEGER, JyoCD TEXT, "
            "Kaiji INTEGER, Nichiji INTEGER, RaceNum INTEGER, Umaban INTEGER, "
            "DataKubun TEXT, Time TEXT, PRIMARY KEY "
            "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban))"
        )
        db.execute(
            "INSERT INTO UMA_RACE "
            "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban, DataKubun, Time) "
            "VALUES (2026, 718, '05', 1, 1, 1, 1, '7', '1148')"
        )
        DataImporter(db, use_jravan_schema=True)
        columns = {row["name"] for row in db.fetch_all('PRAGMA table_info("UMA_RACE")')}
        migrated = db.fetch_one(
            "SELECT ParserContractVersion, RaceTimeSeconds FROM UMA_RACE"
        )

    assert {"ParserContractVersion", "RaceTimeSeconds", "ProviderRaceTimeRaw"} <= columns
    # Legacy JRA columns were already numerically normalized by the old
    # importer, so reconstructing fixed-width raw values would be ambiguous.
    # Existing rows remain explicitly unversioned until setup data is reimported.
    assert migrated == {"ParserContractVersion": None, "RaceTimeSeconds": None}


def test_initial_card_prize_zero_is_missing_but_settled_zero_is_real() -> None:
    initial = canonicalize_se_fields(
        {"DataKubun": "1", "Honsyokin": "00000000", "Fukasyokin": "00000000"}
    )
    settled = canonicalize_se_fields(
        {"DataKubun": "7", "Honsyokin": "00000000", "Fukasyokin": "00000000"}
    )
    assert initial["HonsyokinYen"] is None
    assert initial["FukasyokinYen"] is None
    assert settled["HonsyokinYen"] == 0
    assert settled["FukasyokinYen"] == 0


@pytest.mark.parametrize("data_kubun", ["0", "1", "2", "3", "4", "5", "6", "9", "A", "B"])
def test_prize_zero_is_missing_outside_fully_settled_status(data_kubun: str) -> None:
    canonical = canonicalize_se_fields(
        {
            "DataKubun": data_kubun,
            "Honsyokin": "00000000",
            "Fukasyokin": "00000000",
        }
    )
    assert canonical["HonsyokinYen"] is None
    assert canonical["FukasyokinYen"] is None


def test_optimized_importer_cleans_transport_fields_and_keeps_canonical(tmp_path) -> None:
    from src.database.schema import create_all_tables
    from src.database.sqlite_handler import SQLiteDatabase
    from src.importer.importer_optimized import OptimizedDataImporter

    record = SEParser().parse(_record(Time="1148", Honsyokin="00008000"))
    assert record is not None
    db = SQLiteDatabase({"path": str(tmp_path / "optimized.db")})
    with db:
        create_all_tables(db)
        stats = OptimizedDataImporter(db).import_records(iter([record]))
        stored = db.fetch_one("SELECT RaceTimeSeconds, HonsyokinYen FROM NL_SE")

    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 0
    assert stored == {"RaceTimeSeconds": 74.8, "HonsyokinYen": 800_000}


def test_optimized_importer_rejects_null_primary_key_after_conversion(tmp_path) -> None:
    from src.database.schema import create_all_tables
    from src.database.sqlite_handler import SQLiteDatabase
    from src.importer.importer_optimized import OptimizedDataImporter

    raw = bytearray(_record())
    raw[11:15] = b"****"
    record = SEParser().parse(bytes(raw))
    assert record is not None
    db = SQLiteDatabase({"path": str(tmp_path / "invalid-key.db")})
    with db:
        create_all_tables(db)
        stats = OptimizedDataImporter(db).import_records(iter([record]))
        count = db.fetch_one("SELECT COUNT(*) AS count FROM NL_SE")

    assert stats["records_imported"] == 0
    assert stats["records_failed"] == 1
    assert count == {"count": 0}


@pytest.mark.parametrize("optimized", [False, True])
def test_jravan_importers_reject_null_semantic_primary_key(
    tmp_path, optimized: bool
) -> None:
    from src.database.sqlite_handler import SQLiteDatabase
    from src.importer.importer import DataImporter
    from src.importer.importer_optimized import OptimizedDataImporter

    raw = bytearray(_record())
    raw[11:15] = b"****"
    record = SEParser().parse(bytes(raw))
    assert record is not None
    db = SQLiteDatabase({"path": str(tmp_path / f"jravan-{optimized}.db")})
    with db:
        db.execute(
            "CREATE TABLE UMA_RACE (Year INTEGER, MonthDay INTEGER, JyoCD TEXT, "
            "Kaiji INTEGER, Nichiji INTEGER, RaceNum INTEGER, Umaban INTEGER, "
            "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban))"
        )
        importer_class = OptimizedDataImporter if optimized else DataImporter
        stats = importer_class(db, use_jravan_schema=True).import_records(iter([record]))
        count = db.fetch_one("SELECT COUNT(*) AS count FROM UMA_RACE")

    assert stats["records_imported"] == 0
    assert stats["records_failed"] == 1
    assert count == {"count": 0}
