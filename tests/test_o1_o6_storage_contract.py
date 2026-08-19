"""O1-O6（オッズ1〜6）公式ストレージ契約テスト。

一次資料は公式仕様書 JV-Data Ver.4.9.0.1 の「７．オッズ1（単複枠）」〜
「１２．オッズ6（3連単）」節。この段では次を固定する。

- オッズ・人気順の公式提供値（数値／`0` の並び=無投票／`-` の並び=発売前取消／
  `*` の並び=発売後取消／空白=登録なし）を native・リアルタイム・標準名の
  すべてで無損失に保持する。
- レースキーと組番は NULL を許さない（1レースの置換が別レースを消さない）。
- 危険な既存 schema は DML の前に fail closed で拒否する。
"""

import os
from pathlib import Path

import pytest

from src.database.dual_handler import DualDatabase
from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import (
    DataImporter,
    validate_odds_record,
    verify_odds_storage_schema,
)
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.odds_domain import SNAPSHOT_ROWS_KEY, TOTAL_COMBINATION
from src.realtime.updater import RealtimeUpdater
from tests.test_o1_o6_official_contract import (
    ALL_RECORD_TYPES,
    IMPORTERS,
    LAYOUTS,
    NATIVE_TABLES,
    STANDARD_TABLES,
    _create,
    _o1_raw,
    _o1_rows,
)

RECORD_TYPES = ("O1", *ALL_RECORD_TYPES)

# 公式のオッズ・人気順は数値以外の提供値も持つ。桁数はレコードごとに異なる。
NATIVE_MARKER_FIELDS = {
    "O1": (("TanOdds", 4), ("TanNinki", 2), ("FukuOddsLow", 4), ("FukuOddsHigh", 4),
           ("FukuNinki", 2), ("WakurenOdds", 5), ("WakurenNinki", 2)),
    "O2": (("Odds", 6), ("Ninki", 3)),
    "O3": (("OddsLow", 5), ("OddsHigh", 5), ("Ninki", 3)),
    "O4": (("Odds", 6), ("Ninki", 3)),
    "O5": (("Odds", 6), ("Ninki", 3)),
    "O6": (("Odds", 7), ("Ninki", 4)),
}


def _native_table(record_type: str) -> str:
    return NATIVE_TABLES[record_type]


def _rows(record_type: str, **kwargs) -> list[dict]:
    if record_type == "O1":
        return [dict(row) for row in _o1_rows(**kwargs)]
    return [dict(row) for row in LAYOUTS[record_type].rows(**kwargs)]


def _marker_rows(record_type: str, marker: str) -> list[dict]:
    """One official snapshot whose odds and popularity are cancellation markers."""

    if record_type == "O1":
        return [
            dict(row)
            for row in _o1_rows(
                horses=2,
                brackets=2,
                tan_odds=marker.encode("ascii") * 4,
                tan_favourite=marker.encode("ascii") * 2,
                fuku_low=marker.encode("ascii") * 4,
                fuku_high=marker.encode("ascii") * 4,
                fuku_favourite=marker.encode("ascii") * 2,
                wakuren_odds=marker.encode("ascii") * 5,
                wakuren_favourite=marker.encode("ascii") * 2,
            )
        ]
    layout = LAYOUTS[record_type]
    return [
        dict(row)
        for row in layout.rows(
            filled=2,
            odds={name: marker.encode("ascii") * width for name, width in layout.odds_fields},
            favourite=marker.encode("ascii") * layout.favourite_width,
        )
    ]


@pytest.mark.parametrize("record_type", RECORD_TYPES)
@pytest.mark.parametrize("marker", ("-", "*"))
@pytest.mark.parametrize("importer_class", IMPORTERS)
def test_native_storage_keeps_the_official_cancellation_markers(
    tmp_path: Path,
    record_type: str,
    marker: str,
    importer_class: type,
) -> None:
    """発売前後の取消記号は native ストレージでも1文字も失わない。"""

    table_name = _native_table(record_type)
    rows = _marker_rows(record_type, marker)
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"{table_name}-{marker}-{importer_class.__name__}.db")}
    )
    with database:
        _create(database, (table_name,))
        stats = importer_class(database, batch_size=10).import_records(iter(rows))
        assert stats["records_failed"] == 0
        for field_name, width in NATIVE_MARKER_FIELDS[record_type]:
            stored = {
                row[field_name]
                for row in database.fetch_all(f"SELECT {field_name} FROM {table_name}")
                if row[field_name] not in (None, "")
            }
            assert stored == {marker * width}, field_name


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_standard_storage_keeps_the_official_cancellation_markers(
    tmp_path: Path,
    record_type: str,
) -> None:
    """標準名の子表でも取消記号を数値へ丸めない。"""

    tables = STANDARD_TABLES[record_type]
    rows = _marker_rows(record_type, "*")
    database = SQLiteDatabase({"path": str(tmp_path / f"standard-{record_type}.db")})
    with database:
        _create(database, tables)
        stats = DataImporter(database, batch_size=10, use_jravan_schema=True).import_records(
            iter(rows)
        )
        assert stats["records_failed"] == 0
        child_table = tables[-1]
        for field_name, width in NATIVE_MARKER_FIELDS[record_type]:
            stored = {
                row[field_name]
                for row in database.fetch_all(f"SELECT {field_name} FROM {child_table}")
            }
            assert stored == {"*" * width}, field_name


@pytest.mark.parametrize("record_type", RECORD_TYPES)
def test_realtime_storage_keeps_the_official_cancellation_markers(
    tmp_path: Path,
    record_type: str,
) -> None:
    """速報経路（RT_*）も取消記号を保持する。"""

    table_name = f"RT_{record_type}"
    if record_type == "O1":
        raw = _o1_raw(
            horses=2,
            brackets=2,
            tan_odds=b"----",
            tan_favourite=b"--",
            fuku_low=b"----",
            fuku_high=b"----",
            fuku_favourite=b"--",
            wakuren_odds=b"-----",
            wakuren_favourite=b"--",
        )
    else:
        layout = LAYOUTS[record_type]
        raw = layout.raw(
            filled=2,
            odds={name: b"-" * width for name, width in layout.odds_fields},
            favourite=b"-" * layout.favourite_width,
        )
    database = SQLiteDatabase({"path": str(tmp_path / f"realtime-{record_type}.db")})
    with database:
        _create(database, (table_name,))
        results = RealtimeUpdater(database).process_record(raw)
        assert results and all(result["success"] for result in results)
        for field_name, width in NATIVE_MARKER_FIELDS[record_type]:
            stored = {
                row[field_name]
                for row in database.fetch_all(f"SELECT {field_name} FROM {table_name}")
                if row[field_name] not in (None, "")
            }
            assert stored == {"-" * width}, field_name


@pytest.mark.parametrize("record_type", RECORD_TYPES)
def test_official_key_columns_reject_null(record_type: str) -> None:
    """公式レースキーと組番は NULL を許さない（別レースを消さないため）。"""

    schema_sql = SCHEMAS[_native_table(record_type)]
    required = ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi"]
    if record_type == "O1":
        required.append("Umaban")
    for column in required:
        assert f"{column} " in schema_sql
        line = next(
            text.strip()
            for text in schema_sql.splitlines()
            if text.strip().startswith(f"{column} ")
        )
        assert "NOT NULL" in line, line


@pytest.mark.parametrize("record_type", RECORD_TYPES)
def test_official_odds_columns_are_lossless(record_type: str) -> None:
    """オッズ・人気順は記号値を保持できる型で宣言する。"""

    for table_name in (_native_table(record_type), f"RT_{record_type}"):
        schema_sql = SCHEMAS[table_name]
        for field_name, _ in NATIVE_MARKER_FIELDS[record_type]:
            line = next(
                text.strip()
                for text in schema_sql.splitlines()
                if text.strip().startswith(f"{field_name} ")
            )
            assert " TEXT" in line, (table_name, line)


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_standard_odds_columns_are_lossless(record_type: str) -> None:
    child_table = STANDARD_TABLES[record_type][-1]
    schema_sql = JRAVAN_SCHEMAS[child_table]
    for field_name, width in NATIVE_MARKER_FIELDS[record_type]:
        line = next(
            text.strip()
            for text in schema_sql.splitlines()
            if text.strip().startswith(f"{field_name} ")
        )
        assert f"VARCHAR({width})" in line, (child_table, line)


def _o_record(record_type: str) -> dict:
    return _rows(record_type)[0]


@pytest.mark.parametrize("record_type", RECORD_TYPES)
def test_validation_accepts_official_rows_and_binds_the_record_type(
    record_type: str,
) -> None:
    record = _o_record(record_type)
    assert validate_odds_record(record) is True
    assert validate_odds_record(record, _native_table(record_type)) is True
    assert validate_odds_record(record, "NL_RA") is False
    other = "O2" if record_type != "O2" else "O3"
    with pytest.raises(SchemaMigrationError):
        validate_odds_record(record, _native_table(other))


@pytest.mark.parametrize("record_type", RECORD_TYPES)
@pytest.mark.parametrize(
    "override",
    (
        {"MonthDay": "0230"},
        {"JyoCD": "5"},
        {"TorokuTosu": "1"},
        {"DataKubun": "7"},
    ),
)
def test_validation_rejects_non_official_values(record_type: str, override: dict) -> None:
    record = {**_o_record(record_type), **override}
    with pytest.raises(SchemaMigrationError):
        validate_odds_record(record, _native_table(record_type))


def _native_columns(record_type: str, table_name: str) -> tuple[str, ...]:
    schema_sql = SCHEMAS[table_name]
    body = schema_sql.split("(", 1)[1].rsplit(")", 1)[0]
    return tuple(
        line.strip().rstrip(",")
        for line in body.splitlines()
        if line.strip() and not line.strip().startswith("PRIMARY KEY")
    )


def _key_columns(record_type: str) -> str:
    columns = ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"]
    if record_type == "O1":
        columns.append("Umaban")
    columns.append("Kumi")
    return ", ".join(columns)


@pytest.mark.parametrize("record_type", RECORD_TYPES)
@pytest.mark.parametrize(
    "mutation",
    ("nullable_key", "lossy_odds", "missing_key_column", "extra_unique", "extra_column"),
)
def test_schema_verifier_rejects_each_unsafe_contract(
    tmp_path: Path,
    record_type: str,
    mutation: str,
) -> None:
    """危険な既存 schema は DML の前に拒否する。"""

    table_name = _native_table(record_type)
    columns = list(_native_columns(record_type, table_name))
    key = _key_columns(record_type)
    if mutation == "nullable_key":
        columns = [
            column.replace(" NOT NULL", "") if column.startswith("Kumi ") else column
            for column in columns
        ]
    elif mutation == "lossy_odds":
        field_name = NATIVE_MARKER_FIELDS[record_type][0][0]
        columns = [
            f"{field_name} REAL" if column.startswith(f"{field_name} ") else column
            for column in columns
        ]
    elif mutation == "missing_key_column":
        key = ", ".join(key.split(", ")[:-1])
    elif mutation == "extra_column":
        columns.append("ExtraColumn TEXT")

    database = SQLiteDatabase({"path": str(tmp_path / f"unsafe-{record_type}-{mutation}.db")})
    with database:
        database.execute(
            f"CREATE TABLE {table_name} ({', '.join(columns)}, PRIMARY KEY ({key}))"
        )
        if mutation == "extra_unique":
            database.execute(
                f"CREATE UNIQUE INDEX idx_extra ON {table_name} (Year, MonthDay, JyoCD)"
            )
        database.commit()
        with pytest.raises(SchemaMigrationError):
            verify_odds_storage_schema(database, table_name)


@pytest.mark.parametrize("record_type", RECORD_TYPES)
def test_verifier_declines_storage_outside_the_official_family(
    tmp_path: Path,
    record_type: str,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"other-{record_type}.db")})
    with database:
        assert verify_odds_storage_schema(database, "NL_RA") is False


@pytest.mark.parametrize("record_type", RECORD_TYPES)
def test_missing_storage_fails_closed(tmp_path: Path, record_type: str) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"missing-{record_type}.db")})
    with database:
        with pytest.raises(SchemaMigrationError):
            verify_odds_storage_schema(database, _native_table(record_type))


@pytest.mark.parametrize("record_type", RECORD_TYPES)
@pytest.mark.parametrize("importer_class", IMPORTERS)
def test_importer_paths_reject_an_unsafe_contract_before_dml(
    tmp_path: Path,
    record_type: str,
    importer_class: type,
) -> None:
    table_name = _native_table(record_type)
    columns = [
        column.replace(" NOT NULL", "") if column.startswith("Kumi ") else column
        for column in _native_columns(record_type, table_name)
    ]
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"dml-{record_type}-{importer_class.__name__}.db")}
    )
    with database:
        database.execute(
            f"CREATE TABLE {table_name} "
            f"({', '.join(columns)}, PRIMARY KEY ({_key_columns(record_type)}))"
        )
        database.commit()
        importer = importer_class(database, batch_size=10)
        with pytest.raises(SchemaMigrationError):
            importer.import_records(iter(_rows(record_type)))
        assert database.fetch_one(f"SELECT COUNT(*) AS cnt FROM {table_name}")["cnt"] == 0


@pytest.mark.parametrize("record_type", RECORD_TYPES)
def test_single_record_path_rejects_an_unsafe_contract_before_dml(
    tmp_path: Path,
    record_type: str,
) -> None:
    table_name = _native_table(record_type)
    columns = [
        column.replace(" NOT NULL", "") if column.startswith("Kumi ") else column
        for column in _native_columns(record_type, table_name)
    ]
    database = SQLiteDatabase({"path": str(tmp_path / f"single-{record_type}.db")})
    with database:
        database.execute(
            f"CREATE TABLE {table_name} "
            f"({', '.join(columns)}, PRIMARY KEY ({_key_columns(record_type)}))"
        )
        database.commit()
        importer = DataImporter(database, batch_size=1)
        with pytest.raises(SchemaMigrationError):
            importer.import_single_record(_o_record(record_type))
        assert database.fetch_one(f"SELECT COUNT(*) AS cnt FROM {table_name}")["cnt"] == 0


@pytest.mark.parametrize("record_type", RECORD_TYPES)
def test_dual_rejects_an_unsafe_target_before_mutation(
    tmp_path: Path,
    record_type: str,
) -> None:
    table_name = _native_table(record_type)
    safe = SQLiteDatabase({"path": str(tmp_path / f"dual-safe-{record_type}.db")})
    unsafe = SQLiteDatabase({"path": str(tmp_path / f"dual-unsafe-{record_type}.db")})
    columns = [
        column.replace(" NOT NULL", "") if column.startswith("Kumi ") else column
        for column in _native_columns(record_type, table_name)
    ]
    with safe, unsafe:
        safe.execute(SCHEMAS[table_name])
        unsafe.execute(
            f"CREATE TABLE {table_name} "
            f"({', '.join(columns)}, PRIMARY KEY ({_key_columns(record_type)}))"
        )
        safe.commit()
        unsafe.commit()
        for primary, secondary in ((safe, unsafe), (unsafe, safe)):
            importer = DataImporter(DualDatabase(primary, secondary), batch_size=10)
            with pytest.raises(SchemaMigrationError):
                importer.import_records(iter(_rows(record_type)))
            assert safe.fetch_one(f"SELECT COUNT(*) AS cnt FROM {table_name}")["cnt"] == 0
            assert unsafe.fetch_one(f"SELECT COUNT(*) AS cnt FROM {table_name}")["cnt"] == 0


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("PostgreSQL integration is disabled")
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(
        {
            "host": os.environ["POSTGRES_HOST"],
            "port": int(os.environ["POSTGRES_PORT"]),
            "user": os.environ["POSTGRES_USER"],
            "password": os.environ["POSTGRES_PASSWORD"],
            "database": os.environ["POSTGRES_DB"],
        }
    )
    database.connect()
    yield database
    database.disconnect()


@pytest.mark.parametrize("record_type", RECORD_TYPES)
def test_postgresql_keeps_the_official_cancellation_markers(
    postgresql_db,
    record_type: str,
) -> None:
    table_name = _native_table(record_type)
    postgresql_db.execute(f"DROP TABLE IF EXISTS {table_name}")
    postgresql_db.execute(SCHEMAS[table_name])
    postgresql_db.commit()
    try:
        stats = DataImporter(postgresql_db, batch_size=10).import_records(
            iter(_marker_rows(record_type, "*"))
        )
        assert stats["records_failed"] == 0
        for field_name, width in NATIVE_MARKER_FIELDS[record_type]:
            stored = {
                row[field_name.lower()]
                for row in postgresql_db.fetch_all(f"SELECT {field_name} FROM {table_name}")
                if row[field_name.lower()] not in (None, "")
            }
            assert stored == {"*" * width}, field_name
    finally:
        postgresql_db.execute(f"DROP TABLE IF EXISTS {table_name}")
        postgresql_db.commit()


@pytest.mark.parametrize("record_type", RECORD_TYPES)
def test_postgresql_rejects_a_deferrable_primary_key(postgresql_db, record_type: str) -> None:
    table_name = _native_table(record_type)
    columns = _native_columns(record_type, table_name)
    postgresql_db.execute(f"DROP TABLE IF EXISTS {table_name}")
    postgresql_db.execute(
        f"CREATE TABLE {table_name} ({', '.join(columns)}, "
        f"PRIMARY KEY ({_key_columns(record_type)}) DEFERRABLE INITIALLY DEFERRED)"
    )
    postgresql_db.commit()
    try:
        with pytest.raises(SchemaMigrationError):
            verify_odds_storage_schema(postgresql_db, table_name)
    finally:
        postgresql_db.execute(f"DROP TABLE IF EXISTS {table_name}")
        postgresql_db.commit()


@pytest.mark.parametrize("record_type", RECORD_TYPES)
def test_schema_manager_refuses_to_migrate_an_unsafe_existing_table(
    tmp_path: Path,
    record_type: str,
) -> None:
    """危険な既存表は作成・migration の入口で拒否する。"""

    from src.database.schema import SchemaManager

    table_name = _native_table(record_type)
    columns = [
        column.replace(" NOT NULL", "") if column.startswith("Kumi ") else column
        for column in _native_columns(record_type, table_name)
    ]
    database = SQLiteDatabase({"path": str(tmp_path / f"manager-{record_type}.db")})
    with database:
        database.execute(
            f"CREATE TABLE {table_name} "
            f"({', '.join(columns)}, PRIMARY KEY ({_key_columns(record_type)}))"
        )
        database.commit()
        before = database.fetch_all(f'PRAGMA table_xinfo("{table_name}")')
        manager = SchemaManager(database)
        assert manager.create_table(table_name) is False
        assert manager.create_all_tables()[table_name] is False
        assert database.fetch_all(f'PRAGMA table_xinfo("{table_name}")') == before


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_migration_preflight_covers_the_standard_family(
    tmp_path: Path,
    record_type: str,
) -> None:
    """A drifted standard child stops unrelated additive migration."""

    from src.database.schema import (
        STRICT_ODDS_STORAGE_TABLES,
        _preflight_existing_strict_storage,
    )

    owner_table, child_table = STANDARD_TABLES[record_type]
    assert owner_table in STRICT_ODDS_STORAGE_TABLES
    assert _native_table(record_type) in STRICT_ODDS_STORAGE_TABLES

    database = SQLiteDatabase({"path": str(tmp_path / f"preflight-{record_type}.db")})
    with database:
        database.execute(JRAVAN_SCHEMAS[owner_table])
        database.execute(JRAVAN_SCHEMAS[child_table].replace(" NOT NULL", ""))
        database.commit()
        before = database.fetch_all(f'PRAGMA table_xinfo("{child_table}")')
        with pytest.raises(SchemaMigrationError):
            _preflight_existing_strict_storage(database)
        assert database.fetch_all(f'PRAGMA table_xinfo("{child_table}")') == before


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_standard_family_rejects_an_unsafe_child_before_dml(
    tmp_path: Path,
    record_type: str,
) -> None:
    """所有表の検証は子表まで及ぶ（1物理レコードが両方に跨るため）。"""

    owner_table, child_table = STANDARD_TABLES[record_type]
    unsafe_child = JRAVAN_SCHEMAS[child_table].replace(" NOT NULL", "")
    assert unsafe_child != JRAVAN_SCHEMAS[child_table]
    database = SQLiteDatabase({"path": str(tmp_path / f"standard-unsafe-{record_type}.db")})
    with database:
        database.execute(JRAVAN_SCHEMAS[owner_table])
        database.execute(unsafe_child)
        database.commit()
        with pytest.raises(SchemaMigrationError):
            verify_odds_storage_schema(database, owner_table)
        importer = DataImporter(database, batch_size=10, use_jravan_schema=True)
        with pytest.raises(SchemaMigrationError):
            importer.import_records(iter(_rows(record_type)))
        assert database.fetch_one(f"SELECT COUNT(*) AS cnt FROM {child_table}")["cnt"] == 0


@pytest.mark.parametrize("record_type", RECORD_TYPES)
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
def test_markers_survive_both_transaction_modes(
    tmp_path: Path,
    record_type: str,
    auto_commit: bool,
) -> None:
    table_name = _native_table(record_type)
    database = SQLiteDatabase({"path": str(tmp_path / f"tx-{record_type}-{auto_commit}.db")})
    with database:
        _create(database, (table_name,))
        importer = DataImporter(database, batch_size=10)
        for row in _marker_rows(record_type, "-"):
            assert importer.import_single_record(row, auto_commit=auto_commit)
        if not auto_commit:
            database.commit()
        field_name, width = NATIVE_MARKER_FIELDS[record_type][0]
        stored = {
            row[field_name]
            for row in database.fetch_all(f"SELECT {field_name} FROM {table_name}")
            if row[field_name] not in (None, "")
        }
        assert stored == {"-" * width}

def _stored_combinations(database: SQLiteDatabase, table_name: str) -> list[str]:
    return [
        row["Kumi"]
        for row in database.fetch_all(f"SELECT Kumi FROM {table_name} ORDER BY Kumi")
    ]


def _expected_combinations(record_type: str, filled: int) -> list[str]:
    return sorted(row["Kumi"] for row in _rows(record_type, filled=filled))


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_native_snapshot_replacement_removes_withdrawn_combinations(
    tmp_path: Path,
    importer_class,
    record_type: str,
) -> None:
    """1レコードは1レース1時点の完全snapshotなので、古い組合せを残さない。"""

    table_name = _native_table(record_type)
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"replace-{record_type}-{importer_class.__name__}.db")}
    )
    with database:
        _create(database, (table_name,))
        importer = importer_class(database, batch_size=10)
        assert importer.import_records(iter(_rows(record_type, filled=3)))[
            "records_failed"
        ] == 0
        assert _stored_combinations(database, table_name) == _expected_combinations(
            record_type, 3
        )

        assert importer.import_records(iter(_rows(record_type, filled=2)))[
            "records_failed"
        ] == 0
        assert _stored_combinations(database, table_name) == _expected_combinations(
            record_type, 2
        )


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_native_totals_only_snapshot_replaces_every_combination(
    tmp_path: Path,
    record_type: str,
) -> None:
    """発売なし・レース中止の合計のみsnapshotは、古い組合せを残してはならない。"""

    table_name = _native_table(record_type)
    database = SQLiteDatabase({"path": str(tmp_path / f"totals-{record_type}.db")})
    with database:
        _create(database, (table_name,))
        importer = DataImporter(database, batch_size=10)
        assert importer.import_records(iter(_rows(record_type, filled=3)))[
            "records_failed"
        ] == 0
        assert importer.import_records(iter(_rows(record_type, filled=0, sale_flag=b"1")))[
            "records_failed"
        ] == 0
        assert _stored_combinations(database, table_name) == [TOTAL_COMBINATION]


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_realtime_snapshot_replacement_removes_withdrawn_combinations(
    tmp_path: Path,
    record_type: str,
) -> None:
    """速報も同じ完全snapshot置換に従う。"""

    table_name = f"RT_{record_type}"
    database = SQLiteDatabase({"path": str(tmp_path / f"rt-replace-{record_type}.db")})
    with database:
        _create(database, (table_name,))
        updater = RealtimeUpdater(database)
        assert updater.process_parsed_records_batch(_rows(record_type, filled=3))[
            "success"
        ] is True
        assert _stored_combinations(database, table_name) == _expected_combinations(
            record_type, 3
        )

        assert updater.process_parsed_records_batch(_rows(record_type, filled=2))[
            "success"
        ] is True
        assert _stored_combinations(database, table_name) == _expected_combinations(
            record_type, 2
        )

        assert updater.process_parsed_records_batch(_rows(record_type, filled=0, sale_flag=b"1"))[
            "success"
        ] is True
        assert _stored_combinations(database, table_name) == [TOTAL_COMBINATION]


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_single_record_snapshot_replacement_removes_withdrawn_combinations(
    tmp_path: Path,
    record_type: str,
) -> None:
    """単発経路も1物理レコード単位で完全置換する。"""

    table_name = _native_table(record_type)
    database = SQLiteDatabase({"path": str(tmp_path / f"single-replace-{record_type}.db")})
    with database:
        _create(database, (table_name,))
        importer = DataImporter(database)
        for row in _rows(record_type, filled=3):
            assert importer.import_single_record(row)
        assert _stored_combinations(database, table_name) == _expected_combinations(
            record_type, 3
        )
        for row in _rows(record_type, filled=2):
            assert importer.import_single_record(row)
        assert _stored_combinations(database, table_name) == _expected_combinations(
            record_type, 2
        )


@pytest.mark.parametrize("record_type", RECORD_TYPES)
def test_blank_official_values_stay_blank_instead_of_null(
    tmp_path: Path,
    record_type: str,
) -> None:
    """空白は公式の「登録なし」なので、未提供（NULL）へ落としてはならない。"""

    table_name = _native_table(record_type)
    rows = _marker_rows(record_type, " ")
    database = SQLiteDatabase({"path": str(tmp_path / f"blank-{record_type}.db")})
    with database:
        _create(database, (table_name,))
        assert DataImporter(database, batch_size=10).import_records(iter(rows))[
            "records_failed"
        ] == 0
        for field_name, _ in NATIVE_MARKER_FIELDS[record_type]:
            stored = {
                row[field_name]
                for row in database.fetch_all(f"SELECT {field_name} FROM {table_name}")
            }
            # O1 は単勝・複勝・枠連の配列が独立なので、その行に無い項目は NULL
            # （未提供）のままでよい。提供された空白は空白として残る。
            assert "" in stored, field_name
            assert stored <= {None, "", *(" " * width for width in range(1, 8))}, field_name


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_single_record_follower_row_alone_still_stores_the_whole_snapshot(
    tmp_path: Path,
    record_type: str,
) -> None:
    """追従行だけを渡されても、黙って書かずに成功と返してはならない。"""

    table_name = _native_table(record_type)
    database = SQLiteDatabase({"path": str(tmp_path / f"follower-{record_type}.db")})
    with database:
        _create(database, (table_name,))
        rows = _rows(record_type, filled=3)
        assert DataImporter(database).import_single_record(rows[-1])
        assert _stored_combinations(database, table_name) == _expected_combinations(
            record_type, 3
        )


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_postgresql_snapshot_replacement_removes_withdrawn_combinations(
    postgresql_db,
    record_type: str,
) -> None:
    """PostgreSQL でも1レース1時点の完全snapshot置換になる。"""

    table_name = _native_table(record_type)
    postgresql_db.execute(f"DROP TABLE IF EXISTS {table_name}")
    postgresql_db.execute(SCHEMAS[table_name])
    postgresql_db.commit()
    try:
        importer = DataImporter(postgresql_db, batch_size=10)
        assert importer.import_records(iter(_rows(record_type, filled=3)))[
            "records_failed"
        ] == 0
        assert importer.import_records(iter(_rows(record_type, filled=2)))[
            "records_failed"
        ] == 0
        stored = [
            row["kumi"]
            for row in postgresql_db.fetch_all(
                f'SELECT Kumi AS kumi FROM {table_name} ORDER BY Kumi'
            )
        ]
        assert stored == _expected_combinations(record_type, 2)

        assert importer.import_records(
            iter(_rows(record_type, filled=0, sale_flag=b"1"))
        )["records_failed"] == 0
        assert [
            row["kumi"]
            for row in postgresql_db.fetch_all(f'SELECT Kumi AS kumi FROM {table_name}')
        ] == [TOTAL_COMBINATION]
    finally:
        postgresql_db.execute(f"DROP TABLE IF EXISTS {table_name}")
        postgresql_db.commit()


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_realtime_rejects_a_non_official_snapshot_before_mutation(
    tmp_path: Path,
    record_type: str,
) -> None:
    """速報経路も公式ドメイン検証を通さない dict を置換 DML へ通さない。"""

    table_name = f"RT_{record_type}"
    database = SQLiteDatabase({"path": str(tmp_path / f"rt-domain-{record_type}.db")})
    with database:
        _create(database, (table_name,))
        updater = RealtimeUpdater(database)
        assert updater.process_parsed_records_batch(_rows(record_type, filled=3))[
            "errors"
        ] == 0
        stored = _stored_combinations(database, table_name)

        broken = [dict(row) for row in _rows(record_type, filled=3)]
        field_name = NATIVE_MARKER_FIELDS[record_type][0][0]
        for row in broken:
            row[field_name] = "9"
            row[SNAPSHOT_ROWS_KEY] = broken
        with pytest.raises((SchemaMigrationError, ValueError)):
            updater.process_parsed_records_batch(broken)
        assert _stored_combinations(database, table_name) == stored


@pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
def test_timeseries_odds_stay_in_the_official_timeseries_table(
    tmp_path: Path,
    record_type: str,
) -> None:
    """時系列取込は公式の TS_O* が対象で、native 置換へ迂回してはならない。"""

    # SourceSpec を伴わない O3-O6 は公式に当週速報のみなので TS_SOKUHO_O* が対象。
    timeseries_tables = (f"TS_{record_type}", f"TS_SOKUHO_{record_type}")
    native_table = f"RT_{record_type}"
    database = SQLiteDatabase({"path": str(tmp_path / f"ts-{record_type}.db")})
    with database:
        _create(database, (*timeseries_tables, native_table))
        updater = RealtimeUpdater(database)
        updater.process_parsed_record(_rows(record_type, filled=3), timeseries=True)
        assert (
            database.fetch_one(f"SELECT COUNT(*) AS total FROM {native_table}")["total"]
            == 0
        )
