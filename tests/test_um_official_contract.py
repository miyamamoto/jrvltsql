"""Executable official UM (競走馬マスタ) storage and erase contract.

Layout facts come from JV-Data Ver.4.9.0.1 「フォーマット」 １３．競走馬マスタ
(1609 bytes) and are pinned byte-for-byte by ``tests/test_um_parser_layout.py``.
This module owns the storage contract on top of that layout: the official
``DataKubun`` domain, caller body validation, status-0 physical erase in provider
order, the strict native/standard schema contract, and realtime being N/A.
"""

import os
import re
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
    validate_um_record,
    verify_um_storage_schema,
)
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.um_parser import UMParser
from src.realtime.updater import RealtimeUpdater
from tests.test_um_parser_layout import FIELDS, build_record

KETTO_NUM = "2019900001"
OTHER_KETTO_NUM = "2019900002"

# The layout module deliberately stores a distinct sentinel in every span to
# prove the offsets; several of those sentinels are outside the official code
# domain. The storage contract needs an officially valid body, so overwrite the
# domain-bearing spans with official values before parsing.
OFFICIAL_CODE_BYTES = {
    "DelKubun": b"0",
    "RegDate": b"20210401",
    "DelDate": b"00000000",
    "BirthDate": b"20190315",
    "ZaikyuFlag": b"1",
    "UmaKigoCD": b"01",
    "SexCD": b"1",
    "HinsyuCD": b"1",
    "KeiroCD": b"14",
    "TozaiCD": b"2",
}
_POSITIONS = {name: (position, size) for name, position, size, _ in FIELDS}


def um_record(
    *,
    data_kubun: str = "1",
    ketto_num: str = KETTO_NUM,
    overrides: dict | None = None,
    **field_values,
) -> dict:
    """Return one official-domain UM dictionary parsed from official bytes."""

    raw = bytearray(build_record(data_kubun=data_kubun, ketto_num=ketto_num))
    for name, value in OFFICIAL_CODE_BYTES.items():
        position, size = _POSITIONS[name]
        assert len(value) == size, name
        raw[position - 1 : position - 1 + size] = value
    parsed = UMParser().parse(bytes(raw))
    assert parsed is not None
    parsed.update(field_values)
    parsed.update(overrides or {})
    return parsed


def um_erase(ketto_num: str = KETTO_NUM) -> dict:
    """Return the caller-built official delete command for one key."""

    return {
        "RecordSpec": "UM",
        "DataKubun": "0",
        "MakeDate": "20260819",
        "KettoNum": ketto_num,
    }


def _table(use_standard: bool) -> tuple[str, str]:
    table_name = "UMA" if use_standard else "NL_UM"
    schema = JRAVAN_SCHEMAS[table_name] if use_standard else SCHEMAS[table_name]
    return table_name, schema


@pytest.mark.parametrize(
    "change",
    (
        pytest.param({"KettoNum": "20199A0001"}, id="non-digit-key"),
        pytest.param({"KettoNum": "201990001"}, id="short-key"),
        pytest.param({"BirthDate": "20190230"}, id="impossible-birth-date"),
        pytest.param({"BirthDate": "2019031"}, id="short-birth-date"),
        pytest.param({"RegDate": "notadate"}, id="non-digit-registration-date"),
        pytest.param({"DelDate": "20261332"}, id="impossible-erase-date"),
        pytest.param({"DelKubun": "2"}, id="non-official-erase-flag"),
        pytest.param({"ZaikyuFlag": "Z"}, id="non-official-stabling-flag"),
        pytest.param({"SexCD": "X"}, id="non-digit-sex-code"),
        pytest.param({"HinsyuCD": ""}, id="missing-breed-code"),
        pytest.param({"KeiroCD": "1"}, id="short-colour-code"),
        pytest.param({"UmaKigoCD": "1"}, id="short-symbol-code"),
        pytest.param({"TozaiCD": "AB"}, id="wide-affiliation-code"),
        pytest.param({"ChokyosiCode": "9901"}, id="short-trainer-code"),
        pytest.param({"BreederCode": "999"}, id="short-breeder-code"),
        pytest.param({"BanusiCode": "1234567"}, id="wide-owner-code"),
        pytest.param({"Ketto3InfoHansyokuNum1": "12345"}, id="short-pedigree-number"),
        pytest.param({"Ketto3InfoHansyokuNum14": None}, id="missing-pedigree-number"),
        pytest.param({"RuikeiHonsyoHeiti": "12345"}, id="short-prize-total"),
        pytest.param({"SogoChaku": "12"}, id="short-finish-counts"),
        pytest.param({"KyakusituKeiko": "001002003"}, id="short-running-style"),
        pytest.param({"TorokuRaceSu": "abc"}, id="non-digit-race-count"),
        pytest.param({"Bamei": None}, id="missing-name"),
        pytest.param({"BameiEng": None}, id="missing-blankable-text"),
        pytest.param({"DataKubun": "5"}, id="non-official-status"),
        pytest.param({"DataKubun": ""}, id="missing-status"),
    ),
)
def test_um_caller_values_are_rejected_before_coercion(change: dict) -> None:
    record = um_record()
    record.update(change)
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(record)


@pytest.mark.parametrize("data_kubun", ("1", "2", "3", "4", "9"))
def test_um_accepts_every_official_live_status(data_kubun: str) -> None:
    assert validate_import_record_header(um_record(data_kubun=data_kubun)) == ("UM", data_kubun)


def test_um_accepts_official_blank_and_zero_values() -> None:
    record = um_record(
        ZaikyuFlag="",
        Reserved="",
        BameiEng="",
        Syotai="",
        SanchiName="",
        DelDate="00000000",
        Ketto3InfoBamei14="",
    )
    assert validate_import_record_header(record) == ("UM", "1")
    assert validate_um_record(dict(record), "NL_UM") is True


def test_um_status_zero_validates_only_header_and_exact_key() -> None:
    class ExplodingBody:
        def __str__(self) -> str:
            raise RuntimeError("opaque UM body was inspected")

    erase = {**um_erase(), "BirthDate": ExplodingBody()}
    assert validate_import_record_header(erase) == ("UM", "0")
    assert validate_um_record(dict(erase), "NL_UM") is True
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header({**erase, "KettoNum": "123"})


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
def test_um_official_blank_spans_remain_empty_provider_values(
    tmp_path: Path,
    use_standard: bool,
) -> None:
    """The official 初期値 for these spans is spaces, which is not NULL."""

    table_name, schema = _table(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"blank-{table_name}.db")})
    with database:
        database.execute(schema)
        database.commit()
        stats = DataImporter(database, use_jravan_schema=use_standard).import_records(
            iter([um_record(ZaikyuFlag="", Reserved="", BameiEng="", SanchiName="")])
        )
        assert stats["records_imported"] == 1
        assert database.fetch_one(
            f"SELECT ZaikyuFlag, Reserved, BameiEng, SanchiName FROM {table_name}"
        ) == {"ZaikyuFlag": "", "Reserved": "", "BameiEng": "", "SanchiName": ""}


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_um_batch_erase_is_physical_and_provider_ordered(
    tmp_path: Path,
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
                    um_record(Bamei="登録馬名"),
                    um_record(ketto_num=OTHER_KETTO_NUM, Bamei="別馬"),
                    um_record(data_kubun="2", Bamei="改名馬"),
                    um_erase(),
                ]
            ),
            auto_commit=auto_commit,
        )
        assert database.fetch_all(f"SELECT KettoNum, Bamei FROM {table_name}") == [
            {"KettoNum": OTHER_KETTO_NUM, "Bamei": "別馬"}
        ]
        if not auto_commit:
            database.commit()

    assert stats["records_imported"] == 4
    assert stats["records_failed"] == 0


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
def test_um_retirement_status_is_a_live_update_not_an_erase(
    tmp_path: Path,
    use_standard: bool,
) -> None:
    """`9:抹消` retires the horse; only `0` deletes the row."""

    table_name, schema = _table(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"retire-{table_name}.db")})
    with database:
        database.execute(schema)
        database.commit()
        importer = DataImporter(database, use_jravan_schema=use_standard)
        importer.import_records(iter([um_record()]))
        importer.import_records(
            iter([um_record(data_kubun="9", DelKubun="1", DelDate="20260810")])
        )
        assert database.fetch_all(f"SELECT DataKubun, DelKubun, DelDate FROM {table_name}") == [
            {"DataKubun": "9", "DelKubun": "1", "DelDate": "20260810"}
        ]


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
def test_um_single_record_erase_is_physical(
    tmp_path: Path,
    auto_commit: bool,
    use_standard: bool,
) -> None:
    table_name, schema = _table(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"single-{table_name}-{auto_commit}.db")})
    with database:
        database.execute(schema)
        database.commit()
        importer = DataImporter(database, use_jravan_schema=use_standard)
        assert importer.import_single_record(um_record(), auto_commit=auto_commit)
        assert importer.import_single_record(
            um_record(data_kubun="2", Bamei="改名馬"),
            auto_commit=auto_commit,
        )
        assert importer.import_single_record(um_erase(), auto_commit=auto_commit)
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}
        if not auto_commit:
            database.commit()

    assert importer.get_statistics()["records_imported"] == 3


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
def test_um_same_key_update_replaces_body_and_caller_owned_rollback_holds(
    tmp_path: Path,
    use_standard: bool,
) -> None:
    table_name, schema = _table(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"update-{table_name}.db")})
    with database:
        database.execute(schema)
        database.commit()
        importer = DataImporter(database, use_jravan_schema=use_standard)
        importer.import_records(iter([um_record(Bamei="旧馬名")]))
        importer.import_records(iter([um_record(data_kubun="2", Bamei="新馬名")]))
        assert database.fetch_all(f"SELECT DataKubun, Bamei FROM {table_name}") == [
            {"DataKubun": "2", "Bamei": "新馬名"}
        ]

        stats = importer.import_records(
            iter([um_record(ketto_num=OTHER_KETTO_NUM)]),
            auto_commit=False,
        )
        assert stats["records_imported"] == 1
        database.rollback()
        assert database.fetch_all(f"SELECT KettoNum FROM {table_name}") == [
            {"KettoNum": KETTO_NUM}
        ]


def _drop_not_null(schema: str, column: str) -> str:
    """Return the schema with ``column``'s NOT NULL removed, keeping the layout."""

    pattern = re.compile(rf"^(\s+{column}\s+\S+) NOT NULL", re.MULTILINE)
    patched, count = pattern.subn(r"\1", schema)
    assert count == 1, (column, count)
    return patched


def _defective_schema(defect: str, use_standard: bool = False) -> str:
    _, schema = _table(use_standard)
    primary_key = "PRIMARY KEY (KettoNum)"
    if defect == "nullable-key":
        return _drop_not_null(schema, "KettoNum")
    if defect == "nullable-body":
        return _drop_not_null(schema, "Bamei")
    if defect == "wrong-body-type":
        patched, count = re.subn(
            r"BameiEng( +)VARCHAR\(60\)" if use_standard else r"ZaikyuFlag( +)TEXT",
            r"BameiEng\1VARCHAR(40)" if use_standard else r"ZaikyuFlag\1INTEGER",
            schema,
        )
        assert count == 1, count
        return patched
    if defect == "extra-unique":
        return schema.replace(primary_key, f"UNIQUE (BreederCode), {primary_key}")
    if defect == "extra-check":
        return schema.replace(primary_key, f"CHECK (LENGTH(KettoNum) = 8), {primary_key}")
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
    if defect == "extra-required-column":
        return schema.replace(primary_key, f"ExternalRequired TEXT NOT NULL, {primary_key}")
    raise AssertionError(defect)


DEFECTS = (
    "nullable-key",
    "nullable-body",
    "wrong-body-type",
    "extra-unique",
    "extra-check",
    "extra-foreign-key",
    "extra-generated",
    "extra-required-column",
)


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("defect", DEFECTS)
def test_um_schema_verifier_rejects_each_unsafe_contract(
    tmp_path: Path,
    defect: str,
    use_standard: bool,
) -> None:
    table_name, canonical = _table(use_standard)
    unsafe = _defective_schema(defect, use_standard)
    assert unsafe != canonical, defect
    database = SQLiteDatabase({"path": str(tmp_path / f"verify-{table_name}-{defect}.db")})
    with database:
        database.execute(unsafe)
        database.commit()
        before = database.fetch_all(f'PRAGMA table_xinfo("{table_name}")')
        with pytest.raises(SchemaMigrationError):
            verify_um_storage_schema(database, table_name)
        assert database.fetch_all(f'PRAGMA table_xinfo("{table_name}")') == before
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("defect", DEFECTS)
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_um_importer_paths_reject_each_unsafe_contract_before_dml(
    tmp_path: Path,
    importer_class,
    defect: str,
    use_standard: bool,
) -> None:
    """Both batch entry points must reach the verifier for every unsafe schema."""

    table_name, _ = _table(use_standard)
    database = SQLiteDatabase({"path": str(tmp_path / f"path-{table_name}-{defect}.db")})
    with database:
        database.execute(_defective_schema(defect, use_standard))
        database.commit()
        before = database.fetch_all(f'PRAGMA table_xinfo("{table_name}")')
        importer = importer_class(database, use_jravan_schema=use_standard)
        with pytest.raises(SchemaMigrationError):
            importer.import_records(iter([deepcopy(um_record())]))
        with pytest.raises(SchemaMigrationError):
            importer.import_records(iter([um_erase()]))
        assert database.fetch_all(f'PRAGMA table_xinfo("{table_name}")') == before
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}
        assert importer.get_statistics()["records_imported"] == 0


@pytest.mark.parametrize("defect", DEFECTS)
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
def test_um_single_record_path_rejects_each_unsafe_contract_before_dml(
    tmp_path: Path,
    auto_commit: bool,
    defect: str,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"single-{defect}-{auto_commit}.db")})
    with database:
        database.execute(_defective_schema(defect))
        database.commit()
        before = database.fetch_all('PRAGMA table_xinfo("NL_UM")')
        importer = DataImporter(database)
        with pytest.raises(SchemaMigrationError):
            importer.import_single_record(um_record(), auto_commit=auto_commit)
        with pytest.raises(SchemaMigrationError):
            importer.import_single_record(um_erase(), auto_commit=auto_commit)
        assert database.fetch_all('PRAGMA table_xinfo("NL_UM")') == before
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_UM") == {"count": 0}


def test_um_dual_rejects_either_unsafe_target_before_mutation(tmp_path: Path) -> None:
    for unsafe_target in ("primary", "secondary"):
        primary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-primary.db")})
        secondary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-secondary.db")})
        with primary, secondary:
            unsafe = _defective_schema("extra-unique")
            primary.execute(unsafe if unsafe_target == "primary" else SCHEMAS["NL_UM"])
            secondary.execute(unsafe if unsafe_target == "secondary" else SCHEMAS["NL_UM"])
            primary.commit()
            secondary.commit()
            importer = DataImporter(DualDatabase(primary, secondary))
            with pytest.raises(SchemaMigrationError):
                importer.import_records(iter([um_record()]))
            assert importer.get_statistics()["records_imported"] == 0
            assert primary.fetch_one("SELECT COUNT(*) AS count FROM NL_UM") == {"count": 0}
            assert secondary.fetch_one("SELECT COUNT(*) AS count FROM NL_UM") == {"count": 0}


def test_um_is_accumulated_only_and_never_routed_to_realtime(tmp_path: Path) -> None:
    class CacheProbe:
        def __init__(self) -> None:
            self.calls = 0

        def write_rt_record(self, *_args) -> None:
            self.calls += 1

    assert "RT_UM" not in SCHEMAS
    assert "UM" not in RealtimeUpdater.RECORD_TYPE_TABLE
    cache = CacheProbe()
    database = SQLiteDatabase({"path": str(tmp_path / "realtime-um.db")})
    with database:
        updater = RealtimeUpdater(database, cache_manager=cache)
        assert updater.process_record(build_record()) is None
        assert cache.calls == 0
        assert not database.table_exists("RT_UM")
        assert not database.table_exists("NL_UM")


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from scripts.setup_pg_test_db import postgresql_test_config
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_um_{uuid4().hex[:12]}"
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
def test_um_postgresql_provider_order_exact_erase_and_operation_statistics(
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
                um_record(Bamei="登録馬名"),
                um_record(ketto_num=OTHER_KETTO_NUM, BameiEng=""),
                um_record(data_kubun="2", Bamei="改名馬"),
                um_erase(),
            ]
        ),
        auto_commit=auto_commit,
    )
    # PostgreSQL folds unquoted identifiers to lower case; alias for one shape.
    assert postgresql_db.fetch_all(
        f'SELECT KettoNum AS "KettoNum", BameiEng AS "BameiEng" FROM {table_name}'
    ) == [{"KettoNum": OTHER_KETTO_NUM, "BameiEng": ""}]
    if not auto_commit:
        postgresql_db.commit()
    assert stats["records_imported"] == 4
    assert stats["records_failed"] == 0
    assert stats["batches_processed"] == 2


@pytest.mark.parametrize("use_standard", (False, True), ids=("native", "standard"))
def test_um_postgresql_rejects_deferrable_primary_key(postgresql_db, use_standard: bool) -> None:
    table_name, schema = _table(use_standard)
    postgresql_db.execute(
        schema.replace(
            "PRIMARY KEY (KettoNum)",
            "PRIMARY KEY (KettoNum) DEFERRABLE INITIALLY DEFERRED",
        )
    )
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        verify_um_storage_schema(postgresql_db, table_name)


@pytest.mark.parametrize("unsafe_on_postgresql", (False, True), ids=("sqlite", "postgresql"))
def test_um_mixed_dual_rejects_unsafe_target_before_either_mutates(
    tmp_path: Path,
    postgresql_db,
    unsafe_on_postgresql: bool,
) -> None:
    sqlite = SQLiteDatabase({"path": str(tmp_path / "mixed-dual.db")})
    safe = SCHEMAS["NL_UM"]
    unsafe = _defective_schema("extra-unique")
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
            importer.import_records(iter([um_record()]))
        assert importer.get_statistics()["records_imported"] == 0
        assert dual.secondary_in_sync is True
        assert sqlite.fetch_one("SELECT COUNT(*) AS count FROM NL_UM") == {"count": 0}
        assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM NL_UM") == {"count": 0}


@pytest.mark.parametrize("defect", ("nullable-body", "extra-unique"))
def test_um_schema_manager_refuses_to_migrate_an_unsafe_existing_table(
    tmp_path: Path,
    defect: str,
) -> None:
    """Table creation/migration must not touch an unsafe existing NL_UM."""

    from src.database.schema import SchemaManager

    database = SQLiteDatabase({"path": str(tmp_path / f"manager-{defect}.db")})
    with database:
        database.execute(_defective_schema(defect))
        database.commit()
        before = database.fetch_all('PRAGMA table_xinfo("NL_UM")')
        manager = SchemaManager(database)
        assert manager.create_table("NL_UM") is False
        assert manager.create_all_tables()["NL_UM"] is False
        assert database.fetch_all('PRAGMA table_xinfo("NL_UM")') == before
