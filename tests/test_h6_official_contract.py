"""Executable official H6 (票数６・3連単) storage and erase contract.

Layout facts come from JV-Data Ver.4.9.0.1 「フォーマット」 ６．票数6（3連単）
(102,890 bytes) and are pinned byte-for-byte by ``tests/test_jvdata490_layouts.py``.
This module owns the storage contract on top of that layout: the official
``DataKubun`` domain (``0``/``2``/``4``/``5``/``9``), the official sale-flag
domain (``0``/``1``/``3``/``7``), the 18 positional refund flags, the non-numeric
人気順 markers (``----`` 発売前取消 / ``****`` 発売後取消 / spaces 登録なし),
caller body validation, status-0 physical erase across every H6 table, the strict
native/standard/realtime schema contract, and realtime routing to ``RT_H6``.
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
    validate_h6_record,
    verify_h6_storage_schema,
)
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.h6_parser import H6Parser
from src.realtime.updater import RealtimeUpdater

STANDARD_TABLES = ("HYOSU2", "HYOSU_SANRENTAN")
NATIVE_TABLES = ("NL_H6", "RT_H6")
ENTRY_BASE = 50
ENTRY_WIDTH = 21
TOTAL_OFFSET = 102866


def h6_raw(
    *,
    data_kubun: str = "4",
    race_num: bytes = b"11",
    populated: bool = True,
    total: bytes = b"00000123456",
    henkan_total: bytes = b"00000000789",
    hyo: bytes = b"00000000101",
    ninki: bytes = b"0001",
    entries: int = 3,
) -> bytes:
    """Build one official 102,890-byte H6 record."""

    data = bytearray(b" " * H6Parser.RECORD_LENGTH)
    data[0:2] = b"H6"
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
    data[31:32] = b"7" if populated else b"0"
    data[32:50] = b"1" + b"0" * 17
    if populated:
        for index in range(entries):
            offset = ENTRY_BASE + ENTRY_WIDTH * index
            data[offset : offset + 6] = f"0102{index + 3:02d}".encode("ascii")
            data[offset + 6 : offset + 17] = hyo
            data[offset + 17 : offset + 21] = ninki
        data[TOTAL_OFFSET : TOTAL_OFFSET + 11] = total
        data[TOTAL_OFFSET + 11 : TOTAL_OFFSET + 22] = henkan_total
    data[-2:] = b"\r\n"
    return bytes(data)


def h6_rows(**kwargs) -> list[dict]:
    parsed = H6Parser().parse(h6_raw(**kwargs))
    assert parsed, "the official record must expand to at least one row"
    return [dict(row) for row in parsed]


def h6_erase(*, race_num: str = "11") -> list[dict]:
    """The official status-0 command carries the race key and no body."""

    return h6_rows(data_kubun="0", populated=False, race_num=race_num.encode("ascii"))


def h6_row(**overrides) -> dict:
    row = dict(h6_rows()[0])
    row.update(overrides)
    return row


def _canonical(table_name: str) -> str:
    return SCHEMAS.get(table_name) or JRAVAN_SCHEMAS[table_name]


def _create(database, tables) -> None:
    for table_name in tables:
        database.execute(_canonical(table_name))
    database.commit()


def _tables(use_standard: bool) -> tuple[str, ...]:
    return STANDARD_TABLES if use_standard else ("NL_H6",)


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
        pytest.param({"SyussoTosu": None}, id="missing-starter-count"),
        pytest.param({"HatubaiFlag": "Z"}, id="non-official-sale-flag"),
        pytest.param({"HatubaiFlag": "2"}, id="undefined-sale-flag-value"),
        pytest.param({"HenkanUma": "1" * 17}, id="short-refund-horse-span"),
        pytest.param({"HenkanUma": "0" * 17 + "X"}, id="non-flag-refund-horse-span"),
        pytest.param({"HenkanUma": None}, id="missing-refund-horse-span"),
        pytest.param({"SanrentanKumi": "0102"}, id="short-combination"),
        pytest.param({"SanrentanKumi": "01020X"}, id="non-digit-combination"),
        pytest.param({"SanrentanKumi": None}, id="missing-combination"),
        pytest.param({"SanrentanHyo": "123"}, id="short-vote-count"),
        pytest.param({"SanrentanHyo": "0000000010A"}, id="non-digit-vote-count"),
        pytest.param({"SanrentanNinki": "xxxx"}, id="non-official-favourite-marker"),
        pytest.param({"SanrentanNinki": "--"}, id="two-character-cancel-marker"),
        pytest.param({"SanrentanNinki": "00001"}, id="wide-favourite-order"),
        pytest.param({"SanrentanHyoTotal": "123"}, id="short-vote-total"),
        pytest.param({"SanrentanHenkanHyoTotal": None}, id="missing-refund-vote-total"),
    ),
)
def test_h6_caller_values_are_rejected_before_coercion(change: dict) -> None:
    with pytest.raises(SchemaMigrationError):
        validate_h6_record(h6_row(**change), "NL_H6")


@pytest.mark.parametrize("data_kubun", ("2", "4", "5", "9"))
def test_h6_accepts_every_official_live_status(data_kubun: str) -> None:
    for row in h6_rows(data_kubun=data_kubun):
        assert validate_h6_record(row, "NL_H6") is True


@pytest.mark.parametrize("sale_flag", ("0", "1", "3", "7"))
def test_h6_accepts_every_official_sale_flag(sale_flag: str) -> None:
    assert validate_h6_record(h6_row(HatubaiFlag=sale_flag), "NL_H6") is True


@pytest.mark.parametrize(
    "ninki",
    (
        pytest.param("----", id="pre-sale-cancel"),
        pytest.param("****", id="post-sale-cancel"),
        pytest.param("", id="unregistered"),
        pytest.param("0001", id="numeric-order"),
    ),
)
def test_h6_accepts_the_official_favourite_markers(ninki: str) -> None:
    row = h6_row(SanrentanNinki=ninki, SanrentanHyo="00000000000")
    assert validate_h6_record(row, "NL_H6") is True


def test_h6_accepts_only_the_canonical_blank() -> None:
    """Only the parsed blank (empty string) is a provider blank."""

    assert validate_h6_record(h6_row(SanrentanNinki=""), "NL_H6") is True
    for malformed in (" ", "  ", "\t"):
        with pytest.raises(SchemaMigrationError):
            validate_h6_record(h6_row(SanrentanNinki=malformed), "NL_H6")
        with pytest.raises(SchemaMigrationError):
            validate_h6_record(h6_row(SanrentanHyoTotal=malformed), "NL_H6")


def test_h6_validation_binds_the_record_type_to_h6_storage() -> None:
    with pytest.raises(SchemaMigrationError):
        validate_h6_record({"RecordSpec": "H1", "DataKubun": "4"}, "NL_H6")
    assert validate_h6_record({"RecordSpec": "H1", "DataKubun": "4"}) is False
    assert validate_h6_record(h6_row(), "NL_H1") is False


def test_h6_status_zero_validates_only_the_header_and_race_key() -> None:
    """A deletion carries no body, so only the header and key are official."""

    for row in h6_erase():
        row["SanrentanHyo"] = object()
        row["SanrentanNinki"] = object()
        row["SanrentanHyoTotal"] = object()
        assert validate_h6_record(row, "NL_H6") is True


@pytest.mark.parametrize("marker", ("----", "****", ""))
@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
def test_h6_official_favourite_markers_survive_storage(
    tmp_path: Path,
    marker: str,
    use_standard: bool,
) -> None:
    """`----`/`****`/spaces are official 人気順 values, not missing numbers."""

    tables = _tables(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"marker-{use_standard}-{len(marker)}.db")})
    with database:
        _create(database, tables)
        stats = DataImporter(database, use_jravan_schema=use_standard).import_records(
            iter(
                h6_rows(
                    hyo=b"00000000000",
                    ninki=marker.ljust(4).encode("ascii"),
                )
            )
        )
        assert stats["records_failed"] == 0
        if use_standard:
            assert database.fetch_one("SELECT Ninki FROM HYOSU_SANRENTAN") == {"Ninki": marker}
        else:
            assert database.fetch_one("SELECT SanrentanNinki FROM NL_H6") == {
                "SanrentanNinki": marker
            }


def test_h6_records_without_a_sold_combination_keep_the_official_totals() -> None:
    """組番のない snapshot も合計だけの1行になり、native の identity を持つ。"""

    rows = h6_rows(data_kubun="9", populated=False)
    assert len(rows) == 1
    row = rows[0]
    assert row["SanrentanKumi"] == H6Parser.TOTAL_COMBINATION
    assert row["SanrentanHyoTotal"] == ""
    assert validate_h6_record(row, "NL_H6") is True


@pytest.mark.parametrize(
    "field_name, value",
    (
        ("SanrentanHyo", "00000000101"),
        ("SanrentanNinki", "0001"),
        ("SanrentanNinki", "----"),
    ),
)
def test_h6_totals_only_row_rejects_combination_values(field_name: str, value: str) -> None:
    """合計行は組番票数も人気順も持たないため、提供値があれば拒否する。"""

    row = h6_rows(data_kubun="9", populated=False)[0]
    row[field_name] = value
    with pytest.raises(SchemaMigrationError):
        validate_h6_record(row, "NL_H6")


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
def test_h6_totals_only_snapshot_is_stored_once_per_race(
    tmp_path: Path,
    use_standard: bool,
) -> None:
    """A cancelled/unsold race keeps its totals and is replaced, not duplicated."""

    tables = _tables(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"totals-{use_standard}.db")})
    with database:
        _create(database, tables)
        importer = DataImporter(database, use_jravan_schema=use_standard)
        cancelled = h6_rows(data_kubun="9", populated=False)
        for _ in range(2):
            assert importer.import_records(iter(list(cancelled)))["records_failed"] == 0
        if use_standard:
            assert database.fetch_one("SELECT COUNT(*) AS count FROM HYOSU2") == {"count": 1}
            assert database.fetch_one("SELECT COUNT(*) AS count FROM HYOSU_SANRENTAN") == {
                "count": 0
            }
        else:
            assert database.fetch_all(
                "SELECT SanrentanKumi, SanrentanHyoTotal FROM NL_H6"
            ) == [{"SanrentanKumi": "TOTAL", "SanrentanHyoTotal": None}]


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_h6_batch_erase_is_physical_and_provider_ordered(
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
            *h6_rows(data_kubun="2"),
            *h6_rows(data_kubun="4", race_num=b"12"),
            *h6_rows(data_kubun="5"),
            *h6_erase(),
        ]
        stats = importer.import_records(iter(records), auto_commit=auto_commit)
        assert stats["records_failed"] == 0
        for table_name in tables:
            remaining = database.fetch_all(f"SELECT RaceNum FROM {table_name}")
            assert remaining, table_name
            assert all(row["RaceNum"] in (12, "12") for row in remaining), table_name
        if not auto_commit:
            database.commit()


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
def test_h6_single_record_erase_is_physical(
    tmp_path: Path,
    auto_commit: bool,
    use_standard: bool,
) -> None:
    tables = _tables(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"single-{use_standard}-{auto_commit}.db")})
    with database:
        _create(database, tables)
        importer = DataImporter(database, use_jravan_schema=use_standard)
        for row in h6_rows():
            assert importer.import_single_record(row, auto_commit=auto_commit)
        for row in h6_erase():
            assert importer.import_single_record(row, auto_commit=auto_commit)
        for table_name in tables:
            assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {
                "count": 0
            }, table_name
        if not auto_commit:
            database.commit()


def test_h6_erase_mapping_names_only_real_storage_tables() -> None:
    """A mapping entry that names no table silently erases nothing."""

    mapped = _OFFICIAL_ERASE_STORAGE_TABLES["H6"]
    unknown = sorted(
        table for table in mapped if table not in SCHEMAS and table not in JRAVAN_SCHEMAS
    )
    assert unknown == []
    assert {*NATIVE_TABLES, *STANDARD_TABLES} <= set(mapped)


@pytest.mark.parametrize("table_name", STANDARD_TABLES)
def test_h6_standard_family_accepts_only_the_official_key_index(
    tmp_path: Path,
    table_name: str,
) -> None:
    """`verify_standard_vote_tables` creates the official-key index; nothing else."""

    database = SQLiteDatabase({"path": str(tmp_path / f"index-{table_name}.db")})
    with database:
        _create(database, STANDARD_TABLES)
        DataImporter(database, use_jravan_schema=True).import_records(iter(h6_rows()))
        assert verify_h6_storage_schema(database, table_name) is True

        probe_column = "MakeDate" if table_name == "HYOSU2" else "Kumi"
        database.execute(
            f"CREATE UNIQUE INDEX jltsql_h6_probe ON {table_name} ({probe_column})"
        )
        database.commit()
        with pytest.raises(SchemaMigrationError):
            verify_h6_storage_schema(database, table_name)


def test_h6_rejects_a_partial_official_key_index(tmp_path: Path) -> None:
    """A predicate means the official key is not unique for every race."""

    database = SQLiteDatabase({"path": str(tmp_path / "partial.db")})
    with database:
        _create(database, STANDARD_TABLES)
        database.execute(
            "CREATE UNIQUE INDEX jltsql_h6_partial ON HYOSU2 "
            "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum) WHERE Kaiji = 1"
        )
        database.commit()
        with pytest.raises(SchemaMigrationError):
            verify_h6_storage_schema(database, "HYOSU2")


def _drop_not_null(schema: str, column: str) -> str:
    pattern = re.compile(rf"^(\s+{column}\s+\S+) NOT NULL", re.MULTILINE)
    patched, count = pattern.subn(r"\1", schema)
    assert count == 1, (column, count)
    return patched


def _add_clause(schema: str, clause: str) -> str:
    """Insert one table-level clause, whether or not a PRIMARY KEY is declared."""

    primary_key = re.search(r"PRIMARY KEY \([^)]*\)", schema)
    if primary_key is not None:
        return schema.replace(primary_key.group(0), f"{clause}, {primary_key.group(0)}")
    body, closing, tail = schema.rstrip().rpartition(")")
    assert closing == ")" and not tail.strip(), schema
    # A leading comma keeps the clause out of the previous column's trailing comment.
    return f"{body.rstrip()}\n            , {clause}\n        )\n"


def _defective_schema(defect: str, table_name: str = "NL_H6") -> str:
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


@pytest.mark.parametrize("table_name", (*NATIVE_TABLES, *STANDARD_TABLES))
def test_h6_missing_storage_fails_closed(tmp_path: Path, table_name: str) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"missing-{table_name}.db")})
    with database:
        with pytest.raises(SchemaMigrationError):
            verify_h6_storage_schema(database, table_name)


def test_h6_verifier_declines_storage_outside_the_official_family(tmp_path: Path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "outside.db")})
    with database:
        assert verify_h6_storage_schema(database, "NL_H1") is False


def test_h6_owner_verification_covers_every_child_table(tmp_path: Path) -> None:
    """One physical record spans the owner and its child, so both are verified."""

    for missing in STANDARD_TABLES[1:]:
        database = SQLiteDatabase({"path": str(tmp_path / f"child-{missing}.db")})
        with database:
            for table_name in STANDARD_TABLES:
                if table_name != missing:
                    database.execute(_canonical(table_name))
            database.commit()
            with pytest.raises(SchemaMigrationError):
                verify_h6_storage_schema(database, "HYOSU2")


@pytest.mark.parametrize("table_name", (*NATIVE_TABLES, *STANDARD_TABLES))
@pytest.mark.parametrize("defect", DEFECTS)
def test_h6_schema_verifier_rejects_each_unsafe_contract(
    tmp_path: Path,
    defect: str,
    table_name: str,
) -> None:
    unsafe = _defective_schema(defect, table_name)
    canonical = _canonical(table_name)
    assert unsafe != canonical, defect
    family = (table_name, *(STANDARD_TABLES if table_name == "HYOSU2" else ()))
    database = SQLiteDatabase({"path": str(tmp_path / f"verify-{table_name}-{defect}.db")})
    with database:
        for created in dict.fromkeys(family):
            database.execute(_canonical(created))
        database.commit()
        assert verify_h6_storage_schema(database, table_name) is True

    database = SQLiteDatabase({"path": str(tmp_path / f"unsafe-{table_name}-{defect}.db")})
    with database:
        for created in dict.fromkeys(family):
            database.execute(unsafe if created == table_name else _canonical(created))
        database.commit()
        with pytest.raises(SchemaMigrationError):
            verify_h6_storage_schema(database, table_name)


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("defect", DEFECTS)
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_h6_importer_paths_reject_each_unsafe_contract_before_dml(
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
            database.execute(
                _defective_schema(defect, table_name)
                if table_name == unsafe_table
                else _canonical(table_name)
            )
        database.commit()
        importer = importer_class(database, use_jravan_schema=use_standard)
        with pytest.raises(SchemaMigrationError):
            importer.import_records(iter(h6_rows()))
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {unsafe_table}") == {"count": 0}


@pytest.mark.parametrize("defect", DEFECTS)
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
def test_h6_single_record_path_rejects_each_unsafe_contract_before_dml(
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
            importer.import_single_record(h6_row(), auto_commit=auto_commit)
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_H6") == {"count": 0}


def test_h6_dual_rejects_either_unsafe_target_before_mutation(tmp_path: Path) -> None:
    for unsafe_target in ("primary", "secondary"):
        primary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-primary.db")})
        secondary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-secondary.db")})
        with primary, secondary:
            unsafe = _defective_schema("extra-unique")
            primary.execute(unsafe if unsafe_target == "primary" else SCHEMAS["NL_H6"])
            secondary.execute(unsafe if unsafe_target == "secondary" else SCHEMAS["NL_H6"])
            primary.commit()
            secondary.commit()
            importer = DataImporter(DualDatabase(primary, secondary))
            with pytest.raises(SchemaMigrationError):
                importer.import_records(iter(h6_rows()))
            assert primary.fetch_one("SELECT COUNT(*) AS count FROM NL_H6") == {"count": 0}
            assert secondary.fetch_one("SELECT COUNT(*) AS count FROM NL_H6") == {"count": 0}


@pytest.mark.parametrize("defect", ("nullable-key", "extra-unique"))
def test_h6_schema_manager_refuses_to_migrate_an_unsafe_existing_table(
    tmp_path: Path,
    defect: str,
) -> None:
    from src.database.schema import SchemaManager

    database = SQLiteDatabase({"path": str(tmp_path / f"manager-{defect}.db")})
    with database:
        database.execute(_defective_schema(defect))
        database.commit()
        before = database.fetch_all('PRAGMA table_xinfo("NL_H6")')
        manager = SchemaManager(database)
        assert manager.create_table("NL_H6") is False
        assert manager.create_all_tables()["NL_H6"] is False
        assert database.fetch_all('PRAGMA table_xinfo("NL_H6")') == before


def test_h6_migration_preflight_covers_the_standard_family(tmp_path: Path) -> None:
    """A drifted standard owner/child stops unrelated additive migration."""

    from src.database.schema import STRICT_H6_STORAGE_TABLES, _preflight_existing_strict_storage

    assert {*NATIVE_TABLES, "HYOSU2"} <= STRICT_H6_STORAGE_TABLES

    database = SQLiteDatabase({"path": str(tmp_path / "preflight-standard.db")})
    with database:
        for table_name in STANDARD_TABLES:
            database.execute(
                _defective_schema("nullable-key", table_name)
                if table_name == "HYOSU_SANRENTAN"
                else _canonical(table_name)
            )
        database.commit()
        before = database.fetch_all('PRAGMA table_xinfo("HYOSU_SANRENTAN")')
        with pytest.raises(SchemaMigrationError):
            _preflight_existing_strict_storage(database)
        assert database.fetch_all('PRAGMA table_xinfo("HYOSU_SANRENTAN")') == before


def test_h6_realtime_routing_preserves_the_official_markers(tmp_path: Path) -> None:
    """H6 is a realtime record; RT_H6 must keep the same official values."""

    assert RealtimeUpdater.RECORD_TYPE_TABLE["H6"] == "RT_H6"
    database = SQLiteDatabase({"path": str(tmp_path / "realtime.db")})
    with database:
        database.execute(SCHEMAS["RT_H6"])
        database.commit()
        updater = RealtimeUpdater(database)
        assert updater.process_record(h6_raw(hyo=b"00000000000", ninki=b"****")) is not None
        assert database.fetch_one("SELECT SanrentanNinki FROM RT_H6") == {
            "SanrentanNinki": "****"
        }


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from scripts.setup_pg_test_db import postgresql_test_config
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_h6_{uuid4().hex[:12]}"
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
def test_h6_postgresql_provider_order_and_exact_erase(
    postgresql_db,
    importer_class,
    use_standard: bool,
) -> None:
    tables = _tables(use_standard)
    for table_name in tables:
        postgresql_db.execute(_canonical(table_name))
    postgresql_db.commit()
    importer = importer_class(postgresql_db, batch_size=1, use_jravan_schema=use_standard)
    stats = importer.import_records(
        iter(
            [
                *h6_rows(data_kubun="2"),
                *h6_rows(data_kubun="4", race_num=b"12"),
                *h6_rows(data_kubun="5"),
                *h6_erase(),
            ]
        )
    )
    assert stats["records_failed"] == 0
    for table_name in tables:
        rows = postgresql_db.fetch_all(f'SELECT racenum AS "RaceNum" FROM {table_name}')
        assert rows, table_name
        assert all(str(row["RaceNum"]) == "12" for row in rows), table_name
    postgresql_db.commit()


@pytest.mark.parametrize("table_name", NATIVE_TABLES)
def test_h6_postgresql_rejects_deferrable_primary_key(postgresql_db, table_name: str) -> None:
    canonical = _canonical(table_name)
    primary_key = re.search(r"PRIMARY KEY \([^)]*\)", canonical).group(0)
    postgresql_db.execute(canonical.replace(primary_key, f"{primary_key} DEFERRABLE"))
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        verify_h6_storage_schema(postgresql_db, table_name)


@pytest.mark.parametrize(
    "index_sql",
    (
        "CREATE UNIQUE INDEX jltsql_h6_expr ON HYOSU2 "
        "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, (Kaiji + 1))",
        "CREATE UNIQUE INDEX jltsql_h6_partial ON HYOSU2 "
        "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum) WHERE Kaiji = 1",
    ),
)
def test_h6_postgresql_rejects_expression_and_partial_unique_indexes(
    postgresql_db,
    index_sql: str,
) -> None:
    """An expression or predicate does not make the official key unique."""

    for table_name in STANDARD_TABLES:
        postgresql_db.execute(_canonical(table_name))
    postgresql_db.execute(index_sql)
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        verify_h6_storage_schema(postgresql_db, "HYOSU2")


def test_h6_postgresql_standard_family_accepts_only_the_official_key_index(
    postgresql_db,
) -> None:
    """The importer's official-key index is allowed; any other UNIQUE is not."""

    for table_name in STANDARD_TABLES:
        postgresql_db.execute(_canonical(table_name))
    postgresql_db.execute(
        "CREATE UNIQUE INDEX jltsql_uq_hyosu2 ON HYOSU2 "
        "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)"
    )
    postgresql_db.commit()
    assert verify_h6_storage_schema(postgresql_db, "HYOSU2") is True

    postgresql_db.execute("CREATE UNIQUE INDEX jltsql_h6_probe ON HYOSU2 (MakeDate)")
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        verify_h6_storage_schema(postgresql_db, "HYOSU2")
