"""Executable official SK (産駒マスタ) storage and erase contract."""

import os
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest

from src.database.dual_handler import DualDatabase
from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import (
    DataImporter,
    validate_import_record_header,
    validate_sk_record,
    verify_sk_storage_schema,
)
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.sk_parser import SKParser
from src.realtime.updater import RealtimeUpdater
from tests.test_sk_parser_layout import PEDIGREE_FIELDS, build_current_record

KETTO_NUM = "2024100001"
OTHER_KETTO_NUM = "2024100002"
ZENKAKU_SPACE = b"\x81\x40"


def sk_record(
    *,
    data_kubun: str = "1",
    ketto_num: str = KETTO_NUM,
    sanchi_name: str | None = None,
) -> dict:
    """Return one current-layout, official-domain SK dictionary."""

    raw = bytearray(build_current_record())
    raw[2:3] = data_kubun.encode("ascii")
    raw[11:21] = ketto_num.encode("ascii")
    parsed = SKParser().parse(bytes(raw))
    assert parsed is not None
    if sanchi_name is not None:
        parsed["SanchiName"] = sanchi_name
    return parsed


def sk_erase(ketto_num: str = KETTO_NUM) -> dict:
    """Return the caller-built official delete command for one key."""

    return {
        "RecordSpec": "SK",
        "DataKubun": "0",
        "MakeDate": "20260819",
        "KettoNum": ketto_num,
    }


def _table(use_standard: bool) -> tuple[str, str]:
    table_name = "SANKU" if use_standard else "NL_SK"
    schema = JRAVAN_SCHEMAS[table_name] if use_standard else SCHEMAS[table_name]
    return table_name, schema


@pytest.mark.parametrize(
    ("offset", "value"),
    (
        pytest.param(11, b"20241A0001", id="non-digit-key"),
        pytest.param(21, b"20240231", id="impossible-birth-date"),
        pytest.param(29, b"A", id="non-digit-sex-code"),
        pytest.param(33, b"9", id="hn-only-mochi-code"),
        pytest.param(34, b"20 5", id="non-digit-import-year"),
        pytest.param(38, b"BR000039", id="non-digit-breeder-code"),
        pytest.param(66, b"11000000A1", id="non-digit-pedigree"),
        pytest.param(196, b" " * 10, id="blank-last-pedigree"),
    ),
)
def test_sk_parser_rejects_official_domain_violations(offset: int, value: bytes) -> None:
    raw = bytearray(build_current_record())
    raw[offset : offset + len(value)] = value
    assert SKParser().parse(bytes(raw)) is None


def test_sk_parser_accepts_official_initial_and_blank_values() -> None:
    raw = bytearray(build_current_record())
    raw[29:30] = b"0"
    raw[30:31] = b"0"
    raw[31:33] = b"00"
    raw[33:34] = b"0"
    raw[34:38] = b"0000"
    raw[38:46] = b"00000000"
    raw[46:66] = ZENKAKU_SPACE * 10
    raw[66:206] = b"0" * 140
    parsed = SKParser().parse(bytes(raw))
    assert parsed is not None
    assert parsed["KettoNum"] == KETTO_NUM
    assert parsed["ImportYear"] == "0000"
    assert parsed["BreederCode"] == "00000000"
    assert parsed["SanchiName"] == ""
    assert [parsed[name] for name in PEDIGREE_FIELDS] == ["0" * 10] * 14
    for mochi in ("1", "2", "3"):
        raw[33:34] = mochi.encode("ascii")
        assert SKParser().parse(bytes(raw))["SankuMochiKubun"] == mochi


def test_sk_status_zero_raw_body_is_opaque_but_live_body_remains_strict() -> None:
    erase = bytearray(build_current_record())
    erase[2:3] = b"0"
    erase[46:48] = b"\x81\x20"
    parsed = SKParser().parse(bytes(erase))
    assert parsed is not None
    assert parsed["KettoNum"] == KETTO_NUM

    live = bytearray(erase)
    live[2:3] = b"1"
    assert SKParser().parse(bytes(live)) is None


@pytest.mark.parametrize(
    "change",
    (
        pytest.param({"KettoNum": "20241A0001"}, id="non-digit-key"),
        pytest.param({"BirthDate": None}, id="missing-required-body"),
        pytest.param({"SankuMochiKubun": "9"}, id="hn-only-mochi-code"),
        pytest.param({"MMMNum": "12345"}, id="short-pedigree"),
        pytest.param({"SanchiName": None}, id="missing-blankable-text"),
        pytest.param({"headRecordSpec": "HN"}, id="conflicting-record-type-alias"),
        pytest.param({"headDataKubun": "2"}, id="conflicting-status-alias"),
        pytest.param({"DataKubun": ""}, id="missing-status"),
    ),
)
def test_sk_caller_values_are_rejected_before_coercion(change: dict) -> None:
    record = sk_record()
    record.update(change)
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(record)


def test_sk_status_zero_validates_only_header_and_exact_key() -> None:
    class ExplodingBody:
        def __str__(self) -> str:
            raise RuntimeError("opaque SK body was inspected")

    erase = {**sk_erase(), "BirthDate": ExplodingBody()}
    assert validate_import_record_header(erase) == ("SK", "0")
    assert validate_sk_record(dict(erase), "NL_SK") is True
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header({**erase, "KettoNum": "123"})


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
def test_sk_blank_sanchi_name_remains_an_empty_provider_value(
    tmp_path,
    use_standard: bool,
) -> None:
    table_name, schema = _table(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"blank-{table_name}.db")})
    with database:
        database.execute(schema)
        database.commit()
        stats = DataImporter(database, use_jravan_schema=use_standard).import_records(
            iter([sk_record(sanchi_name="")])
        )
        assert stats["records_imported"] == 1
        assert database.fetch_one(f"SELECT SanchiName FROM {table_name}") == {"SanchiName": ""}


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_sk_batch_erase_is_physical_and_provider_ordered(
    tmp_path,
    importer_class,
    auto_commit: bool,
    use_standard: bool,
) -> None:
    table_name, schema = _table(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"{importer_class.__name__}.db")})
    with database:
        database.execute(schema)
        database.commit()
        importer = importer_class(database, batch_size=1, use_jravan_schema=use_standard)
        stats = importer.import_records(
            iter(
                [
                    sk_record(sanchi_name="登録産地"),
                    sk_record(ketto_num=OTHER_KETTO_NUM, sanchi_name="別馬"),
                    sk_record(data_kubun="2", sanchi_name="更新産地"),
                    sk_erase(),
                ]
            ),
            auto_commit=auto_commit,
        )
        rows = database.fetch_all(f"SELECT KettoNum, SanchiName FROM {table_name}")
        assert rows == [{"KettoNum": OTHER_KETTO_NUM, "SanchiName": "別馬"}]
        if not auto_commit:
            database.commit()

    assert stats["records_imported"] == 4
    assert stats["records_failed"] == 0


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
def test_sk_same_key_update_replaces_body_and_caller_owned_rollback_holds(
    tmp_path,
    use_standard: bool,
) -> None:
    table_name, schema = _table(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"update-{table_name}.db")})
    with database:
        database.execute(schema)
        database.commit()
        importer = DataImporter(database, use_jravan_schema=use_standard)
        importer.import_records(iter([sk_record(sanchi_name="旧産地")]))
        importer.import_records(iter([sk_record(data_kubun="2", sanchi_name="新産地")]))
        assert database.fetch_all(f"SELECT DataKubun, SanchiName FROM {table_name}") == [
            {"DataKubun": "2", "SanchiName": "新産地"}
        ]

        stats = importer.import_records(
            iter([sk_record(ketto_num=OTHER_KETTO_NUM)]),
            auto_commit=False,
        )
        assert stats["records_imported"] == 1
        database.rollback()
        assert database.fetch_all(f"SELECT KettoNum FROM {table_name}") == [
            {"KettoNum": KETTO_NUM}
        ]


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
def test_sk_single_record_erase_is_physical(
    tmp_path,
    auto_commit: bool,
    use_standard: bool,
) -> None:
    table_name, schema = _table(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"single-{table_name}.db")})
    with database:
        database.execute(schema)
        database.commit()
        importer = DataImporter(database, use_jravan_schema=use_standard)
        assert importer.import_single_record(sk_record(), auto_commit=auto_commit)
        assert importer.import_single_record(
            sk_record(data_kubun="2", sanchi_name="更新産地"),
            auto_commit=auto_commit,
        )
        assert importer.import_single_record(sk_erase(), auto_commit=auto_commit)
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}
        if not auto_commit:
            database.commit()

    assert importer.get_statistics()["records_imported"] == 3


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_sk_unsafe_extra_required_column_is_rejected_before_dml(
    tmp_path,
    importer_class,
    use_standard: bool,
) -> None:
    table_name, canonical = _table(use_standard)
    unsafe = canonical.replace(
        "PRIMARY KEY (KettoNum)",
        "ExternalRequired TEXT NOT NULL, PRIMARY KEY (KettoNum)",
    )
    database = SQLiteDatabase({"path": str(tmp_path / f"unsafe-{table_name}.db")})
    with database:
        database.execute(unsafe)
        database.commit()
        before_columns = database.fetch_all(f'PRAGMA table_xinfo("{table_name}")')
        with pytest.raises(SchemaMigrationError):
            importer_class(database, use_jravan_schema=use_standard).import_records(
                iter([deepcopy(sk_record())])
            )
        after_columns = database.fetch_all(f'PRAGMA table_xinfo("{table_name}")')
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}
    assert after_columns == before_columns


def _defective_native_schema(defect: str) -> str:
    schema = SCHEMAS["NL_SK"]
    primary_key = "PRIMARY KEY (KettoNum)"
    if defect == "nullable-key":
        return schema.replace("KettoNum TEXT NOT NULL", "KettoNum TEXT")
    if defect == "wrong-body-type":
        return schema.replace("ImportYear INTEGER NOT NULL", "ImportYear TEXT NOT NULL")
    if defect == "extra-unique":
        return schema.replace(primary_key, f"UNIQUE (BreederCode), {primary_key}")
    if defect == "extra-check":
        return schema.replace(primary_key, f"CHECK (ImportYear <= 2000), {primary_key}")
    if defect == "extra-foreign-key":
        return schema.replace(
            primary_key,
            f"FOREIGN KEY (BreederCode) REFERENCES EXTERNAL_BREEDER(BreederCode), {primary_key}",
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
def test_sk_sqlite_schema_verifier_rejects_each_unsafe_contract(
    tmp_path: Path,
    defect: str,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{defect}.db")})
    with database:
        database.execute(_defective_native_schema(defect))
        database.commit()
        before = database.fetch_all('PRAGMA table_xinfo("NL_SK")')
        with pytest.raises(SchemaMigrationError):
            verify_sk_storage_schema(database, "NL_SK")
        after = database.fetch_all('PRAGMA table_xinfo("NL_SK")')
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_SK") == {"count": 0}
    assert after == before


def test_sk_dual_rejects_either_unsafe_target_before_mutation(tmp_path: Path) -> None:
    for unsafe_target in ("primary", "secondary"):
        primary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-primary.db")})
        secondary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-secondary.db")})
        with primary, secondary:
            primary.execute(
                _defective_native_schema("extra-unique")
                if unsafe_target == "primary"
                else SCHEMAS["NL_SK"]
            )
            secondary.execute(
                _defective_native_schema("extra-unique")
                if unsafe_target == "secondary"
                else SCHEMAS["NL_SK"]
            )
            primary.commit()
            secondary.commit()
            importer = DataImporter(DualDatabase(primary, secondary))
            with pytest.raises(SchemaMigrationError):
                importer.import_records(iter([sk_record()]))
            assert importer.get_statistics()["records_imported"] == 0
            assert primary.fetch_one("SELECT COUNT(*) AS count FROM NL_SK") == {"count": 0}
            assert secondary.fetch_one("SELECT COUNT(*) AS count FROM NL_SK") == {"count": 0}


def test_sk_is_accumulated_only_and_never_routed_to_realtime(tmp_path: Path) -> None:
    class CacheProbe:
        def __init__(self) -> None:
            self.calls = 0

        def write_rt_record(self, *_args) -> None:
            self.calls += 1

    assert "RT_SK" not in SCHEMAS
    assert "SK" not in RealtimeUpdater.RECORD_TYPE_TABLE
    cache = CacheProbe()
    database = SQLiteDatabase({"path": str(tmp_path / "realtime-sk.db")})
    with database:
        updater = RealtimeUpdater(database, cache_manager=cache)
        assert updater.process_record(build_current_record()) is None
        assert cache.calls == 0
        assert not database.table_exists("RT_SK")
        assert not database.table_exists("NL_SK")


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from scripts.setup_pg_test_db import postgresql_test_config
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_sk_{uuid4().hex[:12]}"
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
def test_sk_postgresql_provider_order_exact_erase_and_operation_statistics(
    postgresql_db,
    importer_class,
    auto_commit: bool,
    use_standard: bool,
) -> None:
    table_name, schema = _table(use_standard)
    postgresql_db.execute(schema)
    postgresql_db.commit()
    stats = importer_class(
        postgresql_db,
        batch_size=1000,
        use_jravan_schema=use_standard,
    ).import_records(
        iter(
            [
                sk_record(sanchi_name="登録産地"),
                sk_record(ketto_num=OTHER_KETTO_NUM, sanchi_name=""),
                sk_record(data_kubun="2", sanchi_name="更新産地"),
                sk_erase(),
            ]
        ),
        auto_commit=auto_commit,
    )
    # PostgreSQL folds unquoted identifiers to lower case; alias for one shape.
    assert postgresql_db.fetch_all(
        f'SELECT KettoNum AS "KettoNum", SanchiName AS "SanchiName" FROM {table_name}'
    ) == [{"KettoNum": OTHER_KETTO_NUM, "SanchiName": ""}]
    if not auto_commit:
        postgresql_db.commit()
    assert stats["records_imported"] == 4
    assert stats["records_failed"] == 0
    assert stats["batches_processed"] == 2


def test_sk_postgresql_rejects_deferrable_primary_key(postgresql_db) -> None:
    unsafe = SCHEMAS["NL_SK"].replace(
        "PRIMARY KEY (KettoNum)",
        "PRIMARY KEY (KettoNum) DEFERRABLE INITIALLY DEFERRED",
    )
    postgresql_db.execute(unsafe)
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        verify_sk_storage_schema(postgresql_db, "NL_SK")


@pytest.mark.parametrize("unsafe_on_postgresql", (False, True), ids=("sqlite", "postgresql"))
def test_sk_mixed_dual_rejects_unsafe_target_before_either_mutates(
    tmp_path: Path,
    postgresql_db,
    unsafe_on_postgresql: bool,
) -> None:
    sqlite = SQLiteDatabase({"path": str(tmp_path / "mixed-dual.db")})
    safe = SCHEMAS["NL_SK"]
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
            importer.import_records(iter([sk_record()]))
        assert importer.get_statistics()["records_imported"] == 0
        assert dual.secondary_in_sync is True
        assert sqlite.fetch_one("SELECT COUNT(*) AS count FROM NL_SK") == {"count": 0}
        assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM NL_SK") == {"count": 0}
