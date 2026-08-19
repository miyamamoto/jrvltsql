"""Executable official H1 (票数１・全掛式) storage and erase contract.

Layout facts come from JV-Data Ver.4.9.0.1 「フォーマット」 ５．票数１ (28,955
bytes) and are pinned byte-for-byte by ``tests/test_jvdata490_layouts.py``. This
module owns the storage contract on top of that layout: the official
``DataKubun`` domain (``0``/``2``/``4``/``5``/``9``), the official sale-flag and
payout-key domains, the non-numeric 人気順 markers (``--`` 発売前取消 / ``**``
発売後取消 / spaces 登録なし), caller body validation, status-0 physical erase
across every H1 table, the strict native/standard/realtime schema contract, and
the realtime routing that H1 (unlike the accumulated masters) does have.
"""

import os
import re
from pathlib import Path
from uuid import uuid4

import pytest

from src.database.dual_handler import DualDatabase
from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import (
    _OFFICIAL_ERASE_STORAGE_TABLES,
    DataImporter,
    validate_h1_record,
    verify_h1_storage_schema,
)
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.h1_parser import H1Parser
from src.realtime.updater import RealtimeUpdater

STANDARD_TABLES = (
    "HYOSU",
    "HYOSU_TANPUKU",
    "HYOSU_WAKU",
    "HYOSU_UMARENWIDE",
    "HYOSU_UMATAN",
    "HYOSU_SANREN",
)
RACE_KEY = ("Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum")
# (offset, kumi bytes, hyo bytes, ninki bytes) of the first entry of each array.
_FIRST_ENTRIES = (
    (83, b"01", b"00000000101", b"01"),
    (503, b"01", b"00000000202", b"02"),
    (923, b"12", b"00000000303", b"03"),
    (1463, b"0102", b"00000000404", b"004"),
    (4217, b"0102", b"00000000505", b"005"),
    (6971, b"0102", b"00000000606", b"006"),
    (12479, b"010203", b"00000000707", b"007"),
)


def h1_raw(
    *,
    data_kubun: str = "4",
    race_num: bytes = b"11",
    populated: bool = True,
    total_start: int = 1000,
    tan_hyo: bytes | None = None,
    tan_ninki: bytes | None = None,
) -> bytes:
    """Build one official 28,955-byte H1 record."""

    data = bytearray(b" " * H1Parser.RECORD_LENGTH)
    data[0:2] = b"H1"
    data[2:3] = data_kubun.encode("ascii")
    data[3:11] = b"20260419"
    data[11:15] = b"2026"
    data[15:19] = b"0419"
    data[19:21] = b"06"
    data[21:23] = b"03"
    data[23:25] = b"08"
    data[25:27] = race_num
    data[27:29] = b"18"
    data[29:31] = b"18"
    data[31:38] = b"7777777" if populated else b"0000000"
    data[38:39] = b"3"
    data[39:67] = b"10" + b"0" * 26
    data[67:75] = b"01000000"
    data[75:83] = b"00100000"
    if populated:
        for offset, kumi, hyo, ninki in _FIRST_ENTRIES:
            if offset == 83:
                hyo = tan_hyo or hyo
                ninki = tan_ninki or ninki
            data[offset : offset + len(kumi)] = kumi
            data[offset + len(kumi) : offset + len(kumi) + 11] = hyo
            start = offset + len(kumi) + 11
            data[start : start + len(ninki)] = ninki
    for index in range(14):
        data[28799 + index * 11 : 28810 + index * 11] = (
            f"{total_start + index:011d}".encode("ascii")
        )
    data[-2:] = b"\r\n"
    return bytes(data)


def h1_rows(**kwargs) -> list[dict]:
    parsed = H1Parser().parse(h1_raw(**kwargs))
    assert parsed, "the official record must expand to at least one row"
    return [dict(row) for row in parsed]


def h1_erase(*, race_num: str = "11") -> list[dict]:
    """The official status-0 command carries the race key and no body."""

    return h1_rows(data_kubun="0", populated=False, race_num=race_num.encode("ascii"))


def h1_row(**overrides) -> dict:
    row = next(row for row in h1_rows() if row.get("BetType") == "Tansyo")
    row.update(overrides)
    return row


def _create(database, tables) -> None:
    for table_name in tables:
        database.execute(SCHEMAS.get(table_name) or JRAVAN_SCHEMAS[table_name])
    database.commit()


def _tables(use_standard: bool) -> tuple[str, ...]:
    return STANDARD_TABLES if use_standard else ("NL_H1",)


@pytest.mark.parametrize(
    "change",
    (
        pytest.param({"DataKubun": "1"}, id="non-official-status-1"),
        pytest.param({"DataKubun": "3"}, id="non-official-status-3"),
        pytest.param({"MakeDate": "20260230"}, id="impossible-make-date"),
        pytest.param({"Year": "abcd"}, id="non-digit-year"),
        pytest.param({"MonthDay": "1332"}, id="impossible-month-day"),
        pytest.param({"JyoCD": "X"}, id="short-course-code"),
        pytest.param({"Kaiji": None}, id="missing-meeting-number"),
        pytest.param({"RaceNum": "999"}, id="wide-race-number"),
        pytest.param({"TorokuTosu": "ab"}, id="non-digit-registered-count"),
        pytest.param({"HatubaiFlag1": "Z"}, id="non-official-sale-flag"),
        pytest.param({"HatubaiFlag7": "2"}, id="undefined-sale-flag-value"),
        pytest.param({"FukuChakuBaraiKey": "9"}, id="non-official-payout-key"),
        pytest.param({"HenkanUma": "1" * 27}, id="short-refund-horse-span"),
        pytest.param({"HenkanWaku": "0000000X"}, id="non-flag-refund-bracket-span"),
        pytest.param({"HenkanDoWaku": None}, id="missing-refund-same-bracket-span"),
        pytest.param({"BetType": "Bogus"}, id="unknown-bet-type"),
        pytest.param({"Kumi": "1"}, id="short-combination"),
        pytest.param({"Kumi": None}, id="missing-combination"),
        pytest.param({"Hyo": "123"}, id="short-vote-count"),
        pytest.param({"Hyo": "0000000010A"}, id="non-digit-vote-count"),
        pytest.param({"Ninki": "xx"}, id="non-official-favourite-marker"),
        pytest.param({"TanHyoTotal": "123"}, id="short-vote-total"),
        pytest.param({"SanrenfukuHenkanHyoTotal": None}, id="missing-vote-total"),
    ),
)
def test_h1_caller_values_are_rejected_before_coercion(change: dict) -> None:
    with pytest.raises(SchemaMigrationError):
        validate_h1_record(h1_row(**change), "NL_H1")


@pytest.mark.parametrize("data_kubun", ("2", "4", "5", "9"))
def test_h1_accepts_every_official_live_status(data_kubun: str) -> None:
    for row in h1_rows(data_kubun=data_kubun):
        assert validate_h1_record(row, "NL_H1") is True


@pytest.mark.parametrize(
    "ninki,hyo",
    (
        pytest.param("--", "00000000000", id="pre-sale-cancel"),
        pytest.param("**", "00000000000", id="post-sale-cancel"),
        pytest.param("", "00000000000", id="unregistered"),
        pytest.param("01", "00000000000", id="all-zero-votes"),
    ),
)
def test_h1_accepts_the_official_favourite_markers(ninki: str, hyo: str) -> None:
    assert validate_h1_record(h1_row(Ninki=ninki, Hyo=hyo), "NL_H1") is True


def test_h1_validation_binds_the_record_type_to_h1_storage() -> None:
    with pytest.raises(SchemaMigrationError):
        validate_h1_record({"RecordSpec": "UM", "DataKubun": "1"}, "NL_H1")
    assert validate_h1_record({"RecordSpec": "UM", "DataKubun": "1"}) is False
    assert validate_h1_record(h1_row(), "NL_UM") is False


def test_h1_status_zero_validates_only_the_header_and_race_key() -> None:
    """A deletion carries no body, so only the header and key are official."""

    for row in h1_erase():
        row["Hyo"] = object()
        row["Ninki"] = object()
        row["TanHyoTotal"] = object()
        assert validate_h1_record(row, "NL_H1") is True


@pytest.mark.parametrize("marker", ("--", "**", ""))
@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
def test_h1_official_favourite_markers_survive_storage(
    tmp_path: Path,
    marker: str,
    use_standard: bool,
) -> None:
    """`--`/`**`/spaces are official 人気順 values, not missing numbers."""

    tables = _tables(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"marker-{use_standard}-{len(marker)}.db")})
    with database:
        _create(database, tables)
        stats = DataImporter(database, use_jravan_schema=use_standard).import_records(
            iter(
                h1_rows(
                    tan_hyo=b"00000000000",
                    tan_ninki=marker.ljust(2).encode("ascii"),
                )
            )
        )
        assert stats["records_failed"] == 0
        if use_standard:
            assert database.fetch_one("SELECT TanNinki FROM HYOSU_TANPUKU") == {
                "TanNinki": marker
            }
        else:
            assert database.fetch_one(
                "SELECT Ninki FROM NL_H1 WHERE BetType = 'Tansyo'"
            ) == {"Ninki": marker}


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_h1_batch_erase_is_physical_and_provider_ordered(
    tmp_path: Path,
    importer_class,
    auto_commit: bool,
    use_standard: bool,
) -> None:
    """Provider order 2 → 4 → 5 → 0 leaves no tombstone for the erased race."""

    tables = _tables(use_standard)
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"erase-{importer_class.__name__}-{use_standard}-{auto_commit}.db")}
    )
    with database:
        _create(database, tables)
        importer = importer_class(database, batch_size=1, use_jravan_schema=use_standard)
        records = [
            *h1_rows(data_kubun="2"),
            *h1_rows(data_kubun="4", race_num=b"12", total_start=2000),
            *h1_rows(data_kubun="5", total_start=3000),
            *h1_erase(),
        ]
        stats = importer.import_records(iter(records), auto_commit=auto_commit)
        assert stats["records_failed"] == 0
        for table_name in tables:
            remaining = database.fetch_all(f"SELECT RaceNum FROM {table_name}")
            assert all(row["RaceNum"] in (12, "12") for row in remaining), table_name
            assert remaining, table_name
        if not auto_commit:
            database.commit()


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
def test_h1_single_record_erase_is_physical(
    tmp_path: Path,
    auto_commit: bool,
    use_standard: bool,
) -> None:
    tables = _tables(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"single-{use_standard}-{auto_commit}.db")})
    with database:
        _create(database, tables)
        importer = DataImporter(database, use_jravan_schema=use_standard)
        for row in h1_rows():
            assert importer.import_single_record(row, auto_commit=auto_commit)
        for row in h1_erase():
            assert importer.import_single_record(row, auto_commit=auto_commit)
        for table_name in tables:
            assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {
                "count": 0
            }, table_name
        if not auto_commit:
            database.commit()


def test_h1_erase_mapping_names_only_real_storage_tables() -> None:
    """A mapping entry that names no table silently erases nothing."""

    mapped = _OFFICIAL_ERASE_STORAGE_TABLES["H1"]
    unknown = sorted(
        table for table in mapped if table not in SCHEMAS and table not in JRAVAN_SCHEMAS
    )
    assert unknown == []
    assert {"NL_H1", "RT_H1", *STANDARD_TABLES} <= set(mapped)


@pytest.mark.parametrize("table_name", ("HYOSU", "HYOSU_TANPUKU"))
def test_h1_standard_family_accepts_only_the_official_key_index(
    tmp_path: Path,
    table_name: str,
) -> None:
    """`verify_standard_vote_tables` creates the official-key index; nothing else."""

    database = SQLiteDatabase({"path": str(tmp_path / f"index-{table_name}.db")})
    with database:
        for created in STANDARD_TABLES:
            database.execute(SCHEMAS.get(created) or JRAVAN_SCHEMAS[created])
        database.commit()
        DataImporter(database, use_jravan_schema=True).import_records(iter(h1_rows()))
        assert verify_h1_storage_schema(database, table_name) is True

        database.execute(f"CREATE UNIQUE INDEX jltsql_h1_probe ON {table_name} (MakeDate)")
        database.commit()
        with pytest.raises(SchemaMigrationError):
            verify_h1_storage_schema(database, table_name)


def test_h1_rejects_a_partial_official_key_index(tmp_path: Path) -> None:
    """A predicate means the official key is not unique for every race."""

    database = SQLiteDatabase({"path": str(tmp_path / "partial.db")})
    with database:
        for created in STANDARD_TABLES:
            database.execute(_canonical(created))
        database.execute(
            "CREATE UNIQUE INDEX jltsql_h1_partial ON HYOSU "
            "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum) WHERE Kaiji = 1"
        )
        database.commit()
        with pytest.raises(SchemaMigrationError):
            verify_h1_storage_schema(database, "HYOSU")


def test_h1_accepts_only_the_canonical_blank(tmp_path: Path) -> None:
    """Only the parsed blank (empty string) is a provider blank."""

    assert validate_h1_record(h1_row(Ninki="", Hyo="00000000000"), "NL_H1") is True
    for malformed in (" ", "  ", "\t"):
        with pytest.raises(SchemaMigrationError):
            validate_h1_record(h1_row(Ninki=malformed, Hyo="00000000000"), "NL_H1")
    total = next(row for row in h1_rows() if row.get("BetType") == "Total")
    total["TanHyoTotal"] = ""
    assert validate_h1_record(total, "NL_H1") is True
    total["TanHyoTotal"] = " "
    with pytest.raises(SchemaMigrationError):
        validate_h1_record(total, "NL_H1")


def _drop_not_null(schema: str, column: str) -> str:
    pattern = re.compile(rf"^(\s+{column}\s+\S+) NOT NULL", re.MULTILINE)
    patched, count = pattern.subn(r"\1", schema)
    assert count == 1, (column, count)
    return patched


def _canonical(table_name: str) -> str:
    return SCHEMAS.get(table_name) or JRAVAN_SCHEMAS[table_name]


def _add_clause(schema: str, clause: str) -> str:
    """Insert one table-level clause, whether or not a PRIMARY KEY is declared."""

    primary_key = re.search(r"PRIMARY KEY \([^)]*\)", schema)
    if primary_key is not None:
        return schema.replace(primary_key.group(0), f"{clause}, {primary_key.group(0)}")
    body, closing, tail = schema.rstrip().rpartition(")")
    assert closing == ")" and not tail.strip(), schema
    # A leading comma keeps the clause out of the previous column's trailing comment.
    return f"{body.rstrip()}\n            , {clause}\n        )\n"


def _defective_schema(defect: str, table_name: str = "NL_H1") -> str:
    schema = _canonical(table_name)
    if defect == "nullable-key":
        return _drop_not_null(schema, "JyoCD")
    if defect == "truncated-key":
        primary_key = re.search(r"PRIMARY KEY \([^)]*\)", schema)
        if primary_key is None:
            pytest.skip(f"{table_name} declares no PRIMARY KEY to truncate")
        return schema.replace(primary_key.group(0), primary_key.group(0).rsplit(",", 1)[0] + ")")
    if defect == "wrong-body-type":
        patched, count = re.subn(r"MakeDate( +)(TEXT|DATE)\b", r"MakeDate\1INTEGER", schema)
        assert count == 1, count
        return patched
    if defect == "extra-unique":
        return _add_clause(schema, "UNIQUE (MakeDate)")
    if defect == "extra-check":
        return _add_clause(schema, "CHECK (Year > 1000)")
    if defect == "extra-foreign-key":
        return _add_clause(schema, "FOREIGN KEY (JyoCD) REFERENCES EXTERNAL_COURSE(JyoCD)")
    if defect == "extra-generated":
        return _add_clause(
            schema, "ExternalRequired TEXT GENERATED ALWAYS AS (NULL) VIRTUAL NOT NULL"
        )
    if defect == "extra-required-column":
        return _add_clause(schema, "ExternalRequired TEXT NOT NULL")
    raise AssertionError(defect)


DEFECTS = (
    "nullable-key",
    "truncated-key",
    "wrong-body-type",
    "extra-unique",
    "extra-check",
    "extra-foreign-key",
    "extra-generated",
    "extra-required-column",
)


@pytest.mark.parametrize("table_name", ("NL_H1", "RT_H1", "HYOSU", "HYOSU_TANPUKU"))
def test_h1_missing_storage_fails_closed(tmp_path: Path, table_name: str) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"missing-{table_name}.db")})
    with database:
        with pytest.raises(SchemaMigrationError):
            verify_h1_storage_schema(database, table_name)


def test_h1_verifier_declines_storage_outside_the_official_family(tmp_path: Path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "outside.db")})
    with database:
        assert verify_h1_storage_schema(database, "NL_UM") is False


def test_h1_owner_verification_covers_every_child_table(tmp_path: Path) -> None:
    """One physical record spans the owner and all children, so all are verified."""

    for missing in STANDARD_TABLES[1:]:
        database = SQLiteDatabase({"path": str(tmp_path / f"child-{missing}.db")})
        with database:
            for table_name in STANDARD_TABLES:
                if table_name != missing:
                    database.execute(_canonical(table_name))
            database.commit()
            with pytest.raises(SchemaMigrationError):
                verify_h1_storage_schema(database, "HYOSU")


@pytest.mark.parametrize("table_name", ("NL_H1", "RT_H1", "HYOSU", "HYOSU_TANPUKU"))
@pytest.mark.parametrize("defect", DEFECTS)
def test_h1_schema_verifier_rejects_each_unsafe_contract(
    tmp_path: Path,
    defect: str,
    table_name: str,
) -> None:
    unsafe = _defective_schema(defect, table_name)
    canonical = _canonical(table_name)
    assert unsafe != canonical, defect
    family = (table_name, *(STANDARD_TABLES if table_name == "HYOSU" else ()))
    database = SQLiteDatabase({"path": str(tmp_path / f"verify-{table_name}-{defect}.db")})
    with database:
        for created in dict.fromkeys(family):
            database.execute(_canonical(created))
        database.commit()
        assert verify_h1_storage_schema(database, table_name) is True

    database = SQLiteDatabase({"path": str(tmp_path / f"unsafe-{table_name}-{defect}.db")})
    with database:
        for created in dict.fromkeys(family):
            database.execute(unsafe if created == table_name else _canonical(created))
        database.commit()
        with pytest.raises(SchemaMigrationError):
            verify_h1_storage_schema(database, table_name)


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("defect", DEFECTS)
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_h1_importer_paths_reject_each_unsafe_contract_before_dml(
    tmp_path: Path,
    importer_class,
    defect: str,
    use_standard: bool,
) -> None:
    tables = _tables(use_standard)
    unsafe_table = tables[0]
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"dml-{importer_class.__name__}-{unsafe_table}-{defect}.db")}
    )
    with database:
        for table_name in tables:
            canonical = SCHEMAS.get(table_name) or JRAVAN_SCHEMAS[table_name]
            database.execute(
                _defective_schema(defect, table_name) if table_name == unsafe_table else canonical
            )
        database.commit()
        importer = importer_class(database, use_jravan_schema=use_standard)
        with pytest.raises(SchemaMigrationError):
            importer.import_records(iter(h1_rows()))
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {unsafe_table}") == {"count": 0}


@pytest.mark.parametrize("defect", DEFECTS)
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
def test_h1_single_record_path_rejects_each_unsafe_contract_before_dml(
    tmp_path: Path,
    defect: str,
    auto_commit: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"single-unsafe-{defect}-{auto_commit}.db")})
    with database:
        database.execute(_defective_schema(defect))
        database.commit()
        importer = DataImporter(database)
        with pytest.raises(SchemaMigrationError):
            importer.import_single_record(h1_row(), auto_commit=auto_commit)
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_H1") == {"count": 0}


def test_h1_dual_rejects_either_unsafe_target_before_mutation(tmp_path: Path) -> None:
    for unsafe_target in ("primary", "secondary"):
        primary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-primary.db")})
        secondary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-secondary.db")})
        with primary, secondary:
            unsafe = _defective_schema("extra-unique")
            primary.execute(unsafe if unsafe_target == "primary" else SCHEMAS["NL_H1"])
            secondary.execute(unsafe if unsafe_target == "secondary" else SCHEMAS["NL_H1"])
            primary.commit()
            secondary.commit()
            importer = DataImporter(DualDatabase(primary, secondary))
            with pytest.raises(SchemaMigrationError):
                importer.import_records(iter(h1_rows()))
            assert primary.fetch_one("SELECT COUNT(*) AS count FROM NL_H1") == {"count": 0}
            assert secondary.fetch_one("SELECT COUNT(*) AS count FROM NL_H1") == {"count": 0}


@pytest.mark.parametrize("defect", ("nullable-key", "extra-unique"))
def test_h1_schema_manager_refuses_to_migrate_an_unsafe_existing_table(
    tmp_path: Path,
    defect: str,
) -> None:
    from src.database.schema import SchemaManager

    database = SQLiteDatabase({"path": str(tmp_path / f"manager-{defect}.db")})
    with database:
        database.execute(_defective_schema(defect))
        database.commit()
        before = database.fetch_all('PRAGMA table_xinfo("NL_H1")')
        manager = SchemaManager(database)
        assert manager.create_table("NL_H1") is False
        assert manager.create_all_tables()["NL_H1"] is False
        assert database.fetch_all('PRAGMA table_xinfo("NL_H1")') == before


def test_h1_migration_preflight_covers_the_standard_family(tmp_path: Path) -> None:
    """A drifted standard owner/child stops unrelated additive migration."""

    from src.database.schema import STRICT_H1_STORAGE_TABLES, _preflight_existing_strict_storage

    assert {"NL_H1", "RT_H1", "HYOSU"} <= STRICT_H1_STORAGE_TABLES

    database = SQLiteDatabase({"path": str(tmp_path / "preflight-standard.db")})
    with database:
        for table_name in STANDARD_TABLES:
            database.execute(
                _defective_schema("nullable-key", table_name)
                if table_name == "HYOSU_TANPUKU"
                else _canonical(table_name)
            )
        database.commit()
        before = database.fetch_all('PRAGMA table_xinfo("HYOSU_TANPUKU")')
        with pytest.raises(SchemaMigrationError):
            _preflight_existing_strict_storage(database)
        assert database.fetch_all('PRAGMA table_xinfo("HYOSU_TANPUKU")') == before


def test_h1_realtime_routing_preserves_the_official_markers(tmp_path: Path) -> None:
    """H1 is a realtime record; RT_H1 must keep the same official values."""

    assert RealtimeUpdater.RECORD_TYPE_TABLE["H1"] == "RT_H1"
    database = SQLiteDatabase({"path": str(tmp_path / "realtime.db")})
    with database:
        database.execute(SCHEMAS["RT_H1"])
        database.commit()
        updater = RealtimeUpdater(database)
        assert updater.process_record(h1_raw(tan_hyo=b"00000000000", tan_ninki=b"**")) is not None
        assert database.fetch_one("SELECT Ninki FROM RT_H1 WHERE BetType = 'Tansyo'") == {
            "Ninki": "**"
        }


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from scripts.setup_pg_test_db import postgresql_test_config
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_h1_{uuid4().hex[:12]}"
    database.connect()
    try:
        database.execute(f"CREATE SCHEMA {schema_name}")
        database.execute(f"SET search_path TO {schema_name}")
        database.commit()
        yield database
    finally:
        try:
            try:
                database.rollback()
            except Exception:
                pass
            database.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
            database.commit()
        finally:
            database.disconnect()


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_h1_postgresql_provider_order_and_exact_erase(
    postgresql_db,
    importer_class,
    use_standard: bool,
) -> None:
    tables = _tables(use_standard)
    for table_name in tables:
        postgresql_db.execute(SCHEMAS.get(table_name) or JRAVAN_SCHEMAS[table_name])
    postgresql_db.commit()
    importer = importer_class(postgresql_db, batch_size=1, use_jravan_schema=use_standard)
    stats = importer.import_records(
        iter(
            [
                *h1_rows(data_kubun="2"),
                *h1_rows(data_kubun="4", race_num=b"12", total_start=2000),
                *h1_rows(data_kubun="5", total_start=3000),
                *h1_erase(),
            ]
        )
    )
    assert stats["records_failed"] == 0
    for table_name in tables:
        rows = postgresql_db.fetch_all(f'SELECT racenum AS "RaceNum" FROM {table_name}')
        assert rows, table_name
        assert all(str(row["RaceNum"]) == "12" for row in rows), table_name
    postgresql_db.commit()


@pytest.mark.parametrize("table_name", ("NL_H1", "RT_H1"))
def test_h1_postgresql_rejects_deferrable_primary_key(postgresql_db, table_name: str) -> None:
    canonical = _canonical(table_name)
    primary_key = re.search(r"PRIMARY KEY \([^)]*\)", canonical).group(0)
    postgresql_db.execute(canonical.replace(primary_key, f"{primary_key} DEFERRABLE"))
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        verify_h1_storage_schema(postgresql_db, table_name)


@pytest.mark.parametrize(
    "index_sql",
    (
        "CREATE UNIQUE INDEX jltsql_h1_expr ON HYOSU "
        "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, (Kaiji + 1))",
        "CREATE UNIQUE INDEX jltsql_h1_partial ON HYOSU "
        "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum) WHERE Kaiji = 1",
    ),
)
def test_h1_postgresql_rejects_expression_and_partial_unique_indexes(
    postgresql_db,
    index_sql: str,
) -> None:
    """An expression or predicate does not make the official key unique."""

    for table_name in STANDARD_TABLES:
        postgresql_db.execute(_canonical(table_name))
    postgresql_db.execute(index_sql)
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        verify_h1_storage_schema(postgresql_db, "HYOSU")


def test_h1_postgresql_standard_family_accepts_only_the_official_key_index(
    postgresql_db,
) -> None:
    """The importer's official-key index is allowed; any other UNIQUE is not."""

    for table_name in STANDARD_TABLES:
        postgresql_db.execute(_canonical(table_name))
    postgresql_db.execute(
        "CREATE UNIQUE INDEX jltsql_uq_hyosu ON HYOSU "
        "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)"
    )
    postgresql_db.commit()
    assert verify_h1_storage_schema(postgresql_db, "HYOSU") is True

    postgresql_db.execute("CREATE UNIQUE INDEX jltsql_h1_probe ON HYOSU (MakeDate)")
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        verify_h1_storage_schema(postgresql_db, "HYOSU")


@pytest.mark.parametrize(
    "bet_type,marker",
    (
        pytest.param("Tansyo", "--", id="tansyo-pre-sale-cancel"),
        pytest.param("Tansyo", "**", id="tansyo-post-sale-cancel"),
        pytest.param("Umaren", "---", id="umaren-pre-sale-cancel"),
        pytest.param("Umaren", "***", id="umaren-post-sale-cancel"),
        pytest.param("Wide", "***", id="wide-post-sale-cancel"),
        pytest.param("Umatan", "***", id="umatan-post-sale-cancel"),
        pytest.param("Sanrenpuku", "***", id="sanrenpuku-post-sale-cancel"),
    ),
)
def test_h1_cancel_markers_fill_the_official_field_width(
    bet_type: str, marker: str
) -> None:
    """A cancel marker occupies the whole 人気順 field, which is 2 or 3 wide.

    Live JV-Link RACE data carries '***' for the three-character bet types, so
    accepting only the two-character form rejects a real provider snapshot.
    """

    row = next(row for row in h1_rows() if row.get("BetType") == bet_type)
    row["Ninki"] = marker
    row["Hyo"] = "0" * len(row["Hyo"])
    assert validate_h1_record(row, "NL_H1") is True


@pytest.mark.parametrize(
    "bet_type,malformed",
    (
        pytest.param("Tansyo", "---", id="tansyo-too-wide-marker"),
        pytest.param("Umaren", "**", id="umaren-too-narrow-marker"),
        pytest.param("Umaren", "-*-", id="umaren-mixed-marker"),
        pytest.param("Umaren", "-1-", id="umaren-partial-digits"),
    ),
)
def test_h1_rejects_favourite_markers_that_do_not_match_the_field(
    bet_type: str, malformed: str
) -> None:
    row = next(row for row in h1_rows() if row.get("BetType") == bet_type)
    row["Ninki"] = malformed
    with pytest.raises(SchemaMigrationError):
        validate_h1_record(row, "NL_H1")


@pytest.mark.parametrize("marker", ("---", "***"))
@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
def test_h1_three_character_cancel_markers_survive_storage(
    tmp_path: Path,
    marker: str,
    use_standard: bool,
) -> None:
    """The 馬連 人気順 field is three wide, so its marker is three characters."""

    raw = bytearray(h1_raw())
    umaren_offset, kumi, _hyo, ninki = _FIRST_ENTRIES[3]
    start = umaren_offset + len(kumi) + 11
    raw[start : start + len(ninki)] = marker.encode("ascii")
    rows = [dict(row) for row in H1Parser().parse(bytes(raw))]
    assert any(row.get("Ninki") == marker for row in rows)

    tables = _tables(use_standard)
    # '*' is not a portable filename character, so name the file by the marker.
    marker_name = "pre-sale" if marker.startswith("-") else "post-sale"
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"wide-{use_standard}-{marker_name}.db")}
    )
    with database:
        _create(database, tables)
        stats = DataImporter(database, use_jravan_schema=use_standard).import_records(
            iter(rows)
        )
        assert stats["records_failed"] == 0
        if use_standard:
            assert database.fetch_one(
                "SELECT UmarenNinki FROM HYOSU_UMARENWIDE WHERE Kumi = '0102'"
            ) == {"UmarenNinki": marker}
        else:
            assert database.fetch_one(
                "SELECT Ninki FROM NL_H1 WHERE BetType = 'Umaren'"
            ) == {"Ninki": marker}
