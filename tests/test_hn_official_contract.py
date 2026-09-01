"""Executable official HN storage and erase contract."""

import os
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.database.dual_handler import DualDatabase
from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import (
    DataImporter,
    convert_record_types,
    validate_hn_record,
    validate_import_record_header,
    verify_hn_storage_schema,
)
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.hn_parser import HNParser
from tests.test_hn_parser_layout import build_record


def hn_record(
    *,
    data_kubun: str = "1",
    hansyoku_num: str = "1234567890",
    bamei: str = "テスト繁殖馬",
) -> dict:
    """Return one current-layout, official-domain HN dictionary."""

    raw = bytearray(build_record())
    raw[2:3] = data_kubun.encode("ascii")
    raw[11:21] = hansyoku_num.encode("ascii")
    raw[21:29] = b"00000000"
    raw[39:40] = b"0"
    raw[204:205] = b"1"
    parsed = HNParser().parse(bytes(raw))
    assert parsed is not None
    parsed["Bamei"] = bamei
    return parsed


def official_domain_record() -> bytearray:
    """Return one current HN record whose official-domain spans are all valid."""

    raw = bytearray(build_record())
    raw[21:29] = b"00000000"
    raw[39:40] = b"0"
    raw[204:205] = b"1"
    return raw


@pytest.mark.parametrize(
    ("offset", "value"),
    (
        pytest.param(11, b"12345A7890", id="non-digit-key"),
        pytest.param(204, b"8", id="invalid-mochi-code"),
    ),
)
def test_hn_parser_rejects_official_domain_violations(offset: int, value: bytes) -> None:
    raw = official_domain_record()
    raw[offset : offset + len(value)] = value
    assert HNParser().parse(bytes(raw)) is None


@pytest.mark.parametrize(
    ("offset", "value", "field_name", "expected"),
    (
        pytest.param(21, b"00000001", "reserved", "00000001", id="nonzero-reserved"),
        pytest.param(21, b"        ", "reserved", "", id="blank-reserved"),
        pytest.param(39, b"1", "DelKubun", "1", id="nonzero-reserved-code"),
        pytest.param(39, b" ", "DelKubun", "", id="blank-reserved-code"),
    ),
)
def test_hn_parser_keeps_reserved_spans_without_interpreting_them(
    offset: int, value: bytes, field_name: str, expected: str
) -> None:
    """The official layout defines no item for these spans, so any content is kept."""

    raw = official_domain_record()
    raw[offset : offset + len(value)] = value
    parsed = HNParser().parse(bytes(raw))
    assert parsed is not None
    assert parsed[field_name] == expected


def test_hn_status_zero_raw_body_is_opaque_but_live_body_remains_strict() -> None:
    erase = bytearray(build_record())
    erase[2:3] = b"0"
    erase[40:42] = b"\x81\x20"
    parsed = HNParser().parse(bytes(erase))
    assert parsed is not None
    assert parsed["HansyokuNum"] == "1234567891"

    live = bytearray(erase)
    live[2:3] = b"1"
    assert HNParser().parse(bytes(live)) is None


@pytest.mark.parametrize(
    "change",
    (
        pytest.param({"HansyokuNum": "12345A7890"}, id="non-digit-key"),
        pytest.param({"Bamei": None}, id="missing-required-body"),
        pytest.param({"Bamei": "　"}, id="whitespace-only-required-body"),
        pytest.param({"FHansyokuNum": "12345A7890"}, id="invalid-parent-key"),
        pytest.param({"reserved": "0" * 9}, id="reserved-exceeds-its-span"),
        pytest.param({"DelKubun": "00"}, id="reserved-code-exceeds-its-span"),
        pytest.param(
            {"MochiKubun": "1", "HansyokuMochiKubun": "2"},
            id="conflicting-standard-alias",
        ),
    ),
)
def test_hn_caller_values_are_rejected_before_coercion(change: dict) -> None:
    record = hn_record()
    record.update(change)
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(record)


def test_hn_standard_only_aliases_are_rejected_for_native_storage_before_dml(tmp_path) -> None:
    alias_only = hn_record()
    for native_name, standard_name in (
        ("MochiKubun", "HansyokuMochiKubun"),
        ("FHansyokuNum", "HansyokuFNum"),
        ("MHansyokuNum", "HansyokuMNum"),
    ):
        alias_only[standard_name] = alias_only.pop(native_name)

    assert validate_hn_record(dict(alias_only), "HANSYOKU") is True

    database = SQLiteDatabase({"path": str(tmp_path / "alias-only-native.db")})
    with database:
        database.execute(SCHEMAS["NL_HN"])
        database.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(database).import_records(iter([alias_only]))
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_HN") == {"count": 0}


def test_hn_status_zero_validates_only_header_and_exact_key() -> None:
    class ExplodingBody:
        def __str__(self) -> str:
            raise RuntimeError("opaque HN body was inspected")

    erase = {
        "RecordSpec": "HN",
        "DataKubun": "0",
        "MakeDate": "20260818",
        "HansyokuNum": "1234567890",
        "Bamei": ExplodingBody(),
    }
    assert validate_import_record_header(erase) == ("HN", "0")


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
def test_hn_blank_optional_text_remains_an_empty_provider_value(
    tmp_path,
    use_standard: bool,
) -> None:
    table_name = "HANSYOKU" if use_standard else "NL_HN"
    schema = JRAVAN_SCHEMAS[table_name] if use_standard else SCHEMAS[table_name]
    record = hn_record()
    for field_name in ("BameiKana", "BameiEng", "SanchiName"):
        record[field_name] = ""

    database = SQLiteDatabase({"path": str(tmp_path / f"blank-{table_name}.db")})
    with database:
        database.execute(schema)
        database.commit()
        stats = DataImporter(database, use_jravan_schema=use_standard).import_records(
            iter([record])
        )
        assert stats["records_imported"] == 1
        assert database.fetch_one(f"SELECT BameiKana, BameiEng, SanchiName FROM {table_name}") == {
            "BameiKana": "",
            "BameiEng": "",
            "SanchiName": "",
        }


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
def test_hn_blank_reserved_spans_survive_every_sqlite_import_path(
    tmp_path,
    use_standard: bool,
    entrypoint: str,
) -> None:
    """Validated blank reserved bytes stay provider strings, never SQL NULL."""

    table_name = "HANSYOKU" if use_standard else "NL_HN"
    schema = JRAVAN_SCHEMAS[table_name] if use_standard else SCHEMAS[table_name]
    raw = official_domain_record()
    raw[21:29] = b"        "
    raw[39:40] = b" "
    record = HNParser().parse(bytes(raw))
    assert record is not None

    database = SQLiteDatabase({"path": str(tmp_path / f"reserved-{table_name}-{entrypoint}.db")})
    with database:
        database.execute(schema)
        database.commit()
        if entrypoint == "single":
            assert DataImporter(database, use_jravan_schema=use_standard).import_single_record(
                record
            )
        else:
            importer_class = (
                OptimizedDataImporter if entrypoint == "optimized-batch" else DataImporter
            )
            stats = importer_class(database, use_jravan_schema=use_standard).import_records(
                iter([record])
            )
            assert stats["records_imported"] == 1
            assert stats["records_failed"] == 0
        assert database.fetch_one(f"SELECT reserved, DelKubun FROM {table_name}") == {
            "reserved": "",
            "DelKubun": "",
        }


def test_hn_blank_reserved_spans_remain_text_in_postgresql_bindings(monkeypatch) -> None:
    """The PostgreSQL adapter must receive empty provider text, never SQL NULL."""

    import src.database.postgresql_handler as postgresql_handler

    monkeypatch.setattr(postgresql_handler, "DRIVER", "psycopg")
    raw = official_domain_record()
    raw[21:29] = b"        "
    raw[39:40] = b" "
    record = HNParser().parse(bytes(raw))
    assert record is not None
    converted = convert_record_types(record, "NL_HN")

    database = postgresql_handler.PostgreSQLDatabase({})
    database._connection = MagicMock()
    database._cursor = MagicMock()
    database._get_primary_key_columns = MagicMock(return_value=["hansyokunum"])

    assert database.insert_many("NL_HN", [converted]) == 1

    _, values = database._cursor.execute.call_args.args
    bound = dict(zip(converted, values, strict=True))
    assert bound["reserved"] == ""
    assert bound["DelKubun"] == ""


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_hn_batch_erase_is_physical_and_provider_ordered(
    tmp_path,
    importer_class,
    auto_commit: bool,
    use_standard: bool,
) -> None:
    table_name = "HANSYOKU" if use_standard else "NL_HN"
    schema = JRAVAN_SCHEMAS[table_name] if use_standard else SCHEMAS[table_name]
    database = SQLiteDatabase({"path": str(tmp_path / f"{importer_class.__name__}.db")})
    with database:
        database.execute(schema)
        database.commit()
        importer = importer_class(database, batch_size=1, use_jravan_schema=use_standard)
        stats = importer.import_records(
            iter(
                [
                    hn_record(bamei="登録馬"),
                    hn_record(data_kubun="2", bamei="更新馬"),
                    {
                        "RecordSpec": "HN",
                        "DataKubun": "0",
                        "MakeDate": "20260818",
                        "HansyokuNum": "1234567890",
                    },
                ]
            ),
            auto_commit=auto_commit,
        )
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}
        if not auto_commit:
            database.commit()

    assert stats["records_imported"] == 3
    assert stats["records_failed"] == 0


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
def test_hn_single_record_erase_is_physical(
    tmp_path,
    auto_commit: bool,
    use_standard: bool,
) -> None:
    table_name = "HANSYOKU" if use_standard else "NL_HN"
    schema = JRAVAN_SCHEMAS[table_name] if use_standard else SCHEMAS[table_name]
    database = SQLiteDatabase({"path": str(tmp_path / f"single-{table_name}.db")})
    with database:
        database.execute(schema)
        database.commit()
        importer = DataImporter(database, use_jravan_schema=use_standard)
        assert importer.import_single_record(hn_record(), auto_commit=auto_commit)
        assert importer.import_single_record(
            hn_record(data_kubun="2", bamei="更新馬"),
            auto_commit=auto_commit,
        )
        assert importer.import_single_record(
            {
                "RecordSpec": "HN",
                "DataKubun": "0",
                "MakeDate": "20260818",
                "HansyokuNum": "1234567890",
            },
            auto_commit=auto_commit,
        )
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}
        if not auto_commit:
            database.commit()

    assert importer.get_statistics()["records_imported"] == 3


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_hn_unsafe_extra_required_column_is_rejected_before_dml(
    tmp_path,
    importer_class,
    use_standard: bool,
) -> None:
    table_name = "HANSYOKU" if use_standard else "NL_HN"
    canonical = JRAVAN_SCHEMAS[table_name] if use_standard else SCHEMAS[table_name]
    unsafe = canonical.replace(
        "PRIMARY KEY (HansyokuNum)",
        "ExternalRequired TEXT NOT NULL, PRIMARY KEY (HansyokuNum)",
    )
    database = SQLiteDatabase({"path": str(tmp_path / f"unsafe-{table_name}.db")})
    with database:
        database.execute(unsafe)
        database.commit()
        before_columns = database.fetch_all(f'PRAGMA table_xinfo("{table_name}")')
        with pytest.raises(SchemaMigrationError):
            importer_class(database, use_jravan_schema=use_standard).import_records(
                iter([deepcopy(hn_record())])
            )
        after_columns = database.fetch_all(f'PRAGMA table_xinfo("{table_name}")')
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}
    assert after_columns == before_columns


def _defective_native_schema(defect: str) -> str:
    schema = SCHEMAS["NL_HN"]
    primary_key = "PRIMARY KEY (HansyokuNum)"
    if defect == "nullable-key":
        return schema.replace("HansyokuNum TEXT NOT NULL", "HansyokuNum TEXT")
    if defect == "wrong-body-type":
        return schema.replace("BirthYear INTEGER NOT NULL", "BirthYear TEXT NOT NULL")
    if defect == "extra-unique":
        return schema.replace(primary_key, f"UNIQUE (KettoNum), {primary_key}")
    if defect == "extra-check":
        return schema.replace(primary_key, f"CHECK (BirthYear <= 2000), {primary_key}")
    if defect == "extra-foreign-key":
        return schema.replace(
            primary_key,
            f"FOREIGN KEY (KettoNum) REFERENCES EXTERNAL_HORSE(KettoNum), {primary_key}",
        )
    if defect == "extra-generated":
        return schema.replace(
            primary_key,
            f"ExternalRequired TEXT GENERATED ALWAYS AS (NULL) VIRTUAL NOT NULL, {primary_key}",
        )
    raise AssertionError(defect)


@pytest.mark.parametrize(
    "defect",
    (
        "nullable-key",
        "wrong-body-type",
        "extra-unique",
        "extra-check",
        "extra-foreign-key",
        "extra-generated",
    ),
)
def test_hn_sqlite_schema_verifier_rejects_each_unsafe_contract(
    tmp_path: Path,
    defect: str,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{defect}.db")})
    with database:
        database.execute(_defective_native_schema(defect))
        database.commit()
        before = database.fetch_all('PRAGMA table_xinfo("NL_HN")')
        with pytest.raises(SchemaMigrationError):
            verify_hn_storage_schema(database, "NL_HN")
        after = database.fetch_all('PRAGMA table_xinfo("NL_HN")')
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_HN") == {"count": 0}
    assert after == before


def test_hn_dual_rejects_either_unsafe_target_before_mutation(tmp_path: Path) -> None:
    for unsafe_target in ("primary", "secondary"):
        primary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-primary.db")})
        secondary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-secondary.db")})
        with primary, secondary:
            primary.execute(
                _defective_native_schema("extra-unique")
                if unsafe_target == "primary"
                else SCHEMAS["NL_HN"]
            )
            secondary.execute(
                _defective_native_schema("extra-unique")
                if unsafe_target == "secondary"
                else SCHEMAS["NL_HN"]
            )
            primary.commit()
            secondary.commit()
            importer = DataImporter(DualDatabase(primary, secondary))
            with pytest.raises(SchemaMigrationError):
                importer.import_records(iter([hn_record()]))
            assert importer.get_statistics()["records_imported"] == 0
            assert primary.fetch_one("SELECT COUNT(*) AS count FROM NL_HN") == {"count": 0}
            assert secondary.fetch_one("SELECT COUNT(*) AS count FROM NL_HN") == {"count": 0}


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from scripts.setup_pg_test_db import postgresql_test_config
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_hn_{uuid4().hex[:12]}"
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
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_hn_postgresql_provider_order_exact_erase_and_operation_statistics(
    postgresql_db,
    importer_class,
    auto_commit: bool,
    use_standard: bool,
) -> None:
    table_name = "HANSYOKU" if use_standard else "NL_HN"
    schema = JRAVAN_SCHEMAS[table_name] if use_standard else SCHEMAS[table_name]
    postgresql_db.execute(schema)
    postgresql_db.commit()
    stats = importer_class(
        postgresql_db,
        batch_size=1000,
        use_jravan_schema=use_standard,
    ).import_records(
        iter(
            [
                hn_record(bamei="登録馬"),
                hn_record(data_kubun="2", bamei="更新馬"),
                {
                    "RecordSpec": "HN",
                    "DataKubun": "0",
                    "MakeDate": "20260818",
                    "HansyokuNum": "1234567890",
                },
            ]
        ),
        auto_commit=auto_commit,
    )
    assert postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}
    if not auto_commit:
        postgresql_db.commit()
    assert stats["records_imported"] == 3
    assert stats["records_failed"] == 0
    assert stats["batches_processed"] == 2


def test_hn_postgresql_rejects_deferrable_primary_key(postgresql_db) -> None:
    unsafe = SCHEMAS["NL_HN"].replace(
        "PRIMARY KEY (HansyokuNum)",
        "PRIMARY KEY (HansyokuNum) DEFERRABLE INITIALLY DEFERRED",
    )
    postgresql_db.execute(unsafe)
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        verify_hn_storage_schema(postgresql_db, "NL_HN")


@pytest.mark.parametrize("unsafe_on_postgresql", (False, True), ids=("sqlite", "postgresql"))
def test_hn_mixed_dual_rejects_unsafe_target_before_either_mutates(
    tmp_path: Path,
    postgresql_db,
    unsafe_on_postgresql: bool,
) -> None:
    sqlite = SQLiteDatabase({"path": str(tmp_path / "mixed-dual.db")})
    safe = SCHEMAS["NL_HN"]
    unsafe = _defective_native_schema("extra-unique")
    with sqlite:
        sqlite.execute(safe if unsafe_on_postgresql else unsafe)
        postgresql_db.execute(unsafe if unsafe_on_postgresql else safe)
        sqlite.commit()
        postgresql_db.commit()
        dual = (
            DualDatabase(sqlite, postgresql_db)
            if unsafe_on_postgresql
            else DualDatabase(postgresql_db, sqlite)
        )
        importer = DataImporter(dual)
        with pytest.raises(SchemaMigrationError):
            importer.import_records(iter([hn_record()]))
        assert importer.get_statistics()["records_imported"] == 0
        assert dual.secondary_in_sync is True
        assert sqlite.fetch_one("SELECT COUNT(*) AS count FROM NL_HN") == {"count": 0}
        assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM NL_HN") == {"count": 0}
