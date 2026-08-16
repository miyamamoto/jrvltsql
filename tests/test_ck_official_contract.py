#!/usr/bin/env python
"""CK current-layout parsing and normalized native-storage contract."""

from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from uuid import uuid4

import pytest

from src.database.base import DatabaseError
from src.database.migration import SchemaMigrationError, migrate_table_if_needed
from src.database.schema import SCHEMAS, SchemaManager
from src.database.schema_types import (
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.ck_parser import CKParser


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
    schema_name = f"jlt_ck_{uuid4().hex[:12]}"
    database.connect()
    try:
        database.execute(f"CREATE SCHEMA {schema_name}")
        database.execute(f"SET search_path TO {schema_name}")
        database.commit()
        yield database, schema_name
    finally:
        if not database.is_connected():
            database.connect()
        try:
            database.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
            database.commit()
        finally:
            database.disconnect()


PARENT_KEY = ("Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "KettoNum")
CHILD_TABLES = (
    "NL_CK_CHAKU",
    "NL_CK_RUIKEI",
)
UMA_GROUPS = (
    ("ChakuSogo", 100, 1),
    ("ChakuChuo", 118, 1),
    ("ChakuKaisuBa", 136, 7),
    ("ChakuKaisuJyotai", 262, 12),
    ("ChakuKaisuSibaKyori", 478, 9),
    ("ChakuKaisuDirtKyori", 640, 9),
    ("ChakuKaisuJyoSiba", 802, 10),
    ("ChakuKaisuJyoDirt", 982, 10),
    ("ChakuKaisuJyoSyogai", 1162, 10),
)


@dataclass
class _Sequence:
    value: int = 1

    def take(self, width: int) -> str:
        value = str(self.value % (10**width)).zfill(width)
        self.value += 1
        return value


def _pad(value: str, width: int) -> bytes:
    encoded = value.encode("cp932")
    assert len(encoded) <= width
    return encoded.ljust(width, b" ")


def _put(record: bytearray, start: int, width: int, value: str | bytes) -> str:
    encoded = value if isinstance(value, bytes) else _pad(value, width)
    assert len(encoded) == width
    assert record[start : start + width] == b" " * width
    record[start : start + width] = encoded
    return encoded.decode("cp932").strip()


def _parent_key() -> dict[str, str]:
    return {
        "Year": "2026",
        "MonthDay": "0817",
        "JyoCD": "05",
        "Kaiji": "01",
        "Nichiji": "02",
        "RaceNum": "03",
        "KettoNum": "2026000001",
    }


def _put_hon_ruikei(
    record: bytearray,
    start: int,
    actor_type: str,
    number: int,
    sequence: _Sequence,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    summary = {
        **_parent_key(),
        "EntityKubun": actor_type,
        "PeriodNum": str(number),
        "HonSyokinTotal": "",
        "FukaSyokin": "",
    }
    count_rows = []
    cursor = start
    scalar_fields = (
        ("SetYear", 4),
        ("HonSyokinHeichi", 10),
        ("HonSyokinSyogai", 10),
        ("FukaSyokinHeichi", 10),
        ("FukaSyokinSyogai", 10),
    )
    for name, width in scalar_fields:
        value = "2026" if name == "SetYear" else sequence.take(width)
        summary[name] = _put(record, cursor, width, value)
        cursor += width

    groups = (
        ("ChakuKaisuSiba", 1, 5),
        ("ChakuKaisuDirt", 1, 5),
        ("ChakuKaisuSyogai", 1, 4),
        ("ChakuKaisuSibaKyori", 9, 4),
        ("ChakuKaisuDirtKyori", 9, 4),
        ("ChakuKaisuJyoSiba", 10, 4),
        ("ChakuKaisuJyoDirt", 10, 4),
        ("ChakuKaisuJyoSyogai", 10, 3),
    )
    for group, count, width in groups:
        for index in range(1, count + 1):
            row = {
                **_parent_key(),
                "EntityKubun": actor_type,
                "PeriodNum": str(number),
                "MetricKubun": group,
                "BucketNum": str(index),
            }
            for rank in range(1, 7):
                value = sequence.take(width)
                row[f"Count{rank}"] = _put(record, cursor, width, value)
                cursor += width
            count_rows.append(row)
    assert cursor == start + 1220
    assert len(count_rows) == 51
    return summary, count_rows


def _put_sei_ruikei(
    record: bytearray,
    start: int,
    actor_type: str,
    number: int,
    sequence: _Sequence,
) -> tuple[dict[str, str], dict[str, str]]:
    summary = {
        **_parent_key(),
        "EntityKubun": actor_type,
        "PeriodNum": str(number),
        "HonSyokinHeichi": "",
        "HonSyokinSyogai": "",
        "FukaSyokinHeichi": "",
        "FukaSyokinSyogai": "",
    }
    cursor = start
    for name, width in (
        ("SetYear", 4),
        ("HonSyokinTotal", 10),
        ("FukaSyokin", 10),
    ):
        value = "2026" if name == "SetYear" else sequence.take(width)
        summary[name] = _put(record, cursor, width, value)
        cursor += width
    row = {
        **_parent_key(),
        "EntityKubun": actor_type,
        "PeriodNum": str(number),
        "MetricKubun": "ChakuKaisu",
        "BucketNum": "1",
    }
    for rank in range(1, 7):
        value = sequence.take(6)
        row[f"Count{rank}"] = _put(record, cursor, 6, value)
        cursor += 6
    assert cursor == start + 60
    return summary, row


def build_record(
    *,
    data_kubun: str = "1",
    horse_name: str = "完全展開馬",
    sequence_start: int = 1,
):
    record = bytearray(b" " * 6870)
    expected_parent = {
        "RecordSpec": _put(record, 0, 2, "CK"),
        "DataKubun": _put(record, 2, 1, data_kubun),
        "MakeDate": date(2026, 8, 17),
        "Year": 2026,
        "MonthDay": 817,
        "JyoCD": _put(record, 19, 2, "05"),
        "Kaiji": 1,
        "Nichiji": 2,
        "RaceNum": 3,
        "KettoNum": _put(record, 27, 10, "2026000001"),
        "Bamei": _put(record, 37, 36, horse_name),
    }
    _put(record, 3, 8, "20260817")
    _put(record, 11, 4, "2026")
    _put(record, 15, 4, "0817")
    _put(record, 21, 2, "01")
    _put(record, 23, 2, "02")
    _put(record, 25, 2, "03")
    for name, start in (
        ("HeichiHonsyokinTotal", 73),
        ("SyogaiHonsyokinTotal", 82),
        ("HeichiFukasyokinTotal", 91),
        ("SyogaiFukasyokinTotal", 100),
        ("HeichiSyutokuTotal", 109),
        ("SyogaiSyutokuTotal", 118),
    ):
        expected_parent[name] = _put(record, start, 9, str(start).zfill(9))

    sequence = _Sequence(sequence_start)
    expected_chaku_rows = []
    uma_start = 27
    for group, relative_start, count in UMA_GROUPS:
        for number in range(1, count + 1):
            row = {
                **_parent_key(),
                "EntityKubun": "UMA",
                "PeriodNum": "0",
                "MetricKubun": group,
                "BucketNum": str(number),
            }
            cursor = uma_start + relative_start + 18 * (number - 1)
            for rank in range(1, 7):
                value = sequence.take(3)
                row[f"Count{rank}"] = _put(record, cursor, 3, value)
                cursor += 3
            expected_chaku_rows.append(row)

    kyakusitu = {
        **_parent_key(),
        "EntityKubun": "UMA",
        "PeriodNum": "0",
        "MetricKubun": "Kyakusitu",
        "BucketNum": "1",
    }
    for rank in range(1, 5):
        value = sequence.take(3)
        kyakusitu[f"Count{rank}"] = _put(record, 1369 + 3 * (rank - 1), 3, value)
    kyakusitu["Count5"] = ""
    kyakusitu["Count6"] = ""
    expected_chaku_rows.append(kyakusitu)
    expected_parent["RegisteredRaceCount"] = _put(record, 1381, 3, sequence.take(3))

    expected_parent["KisyuCode"] = _put(record, 1384, 5, "01234")
    expected_parent["KisyuName"] = _put(record, 1389, 34, "騎手 完全")
    professional = [
        _put_hon_ruikei(record, 1423 + 1220 * (number - 1), "KISYU", number, sequence)
        for number in range(1, 3)
    ]
    expected_parent["ChokyosiCode"] = _put(record, 3863, 5, "05678")
    expected_parent["ChokyosiName"] = _put(record, 3868, 34, "調教師 完全")
    professional.extend(
        _put_hon_ruikei(record, 3902 + 1220 * (number - 1), "CHOKYOSI", number, sequence)
        for number in range(1, 3)
    )

    expected_parent["BanusiCode"] = _put(record, 6342, 6, "123456")
    expected_parent["BanusiName"] = _put(record, 6348, 64, "株式会社馬主")
    expected_parent["BanusiName_Co"] = _put(record, 6412, 64, "馬主法人格なし")
    owners = [
        _put_sei_ruikei(record, 6476 + 60 * (number - 1), "BANUSI", number, sequence)
        for number in range(1, 3)
    ]
    expected_parent["BreederCode"] = _put(record, 6596, 8, "12345678")
    expected_parent["BreederName"] = _put(record, 6604, 72, "株式会社生産者")
    expected_parent["BreederName_Co"] = _put(record, 6676, 72, "生産者法人格なし")
    owners.extend(
        _put_sei_ruikei(record, 6748 + 60 * (number - 1), "BREEDER", number, sequence)
        for number in range(1, 3)
    )
    record[6868:6870] = b"\r\n"
    expected_chaku_rows.extend(row for _, rows in professional for row in rows)
    expected_chaku_rows.extend(row for _, row in owners)
    expected_ruikei_rows = [
        *(summary for summary, _ in professional),
        *(summary for summary, _ in owners),
    ]
    return bytes(record), expected_parent, expected_chaku_rows, expected_ruikei_rows


def _rejects(record: bytes) -> bool:
    try:
        return CKParser().parse(record) is None
    except (UnicodeDecodeError, ValueError):
        return True


def test_ck_parser_expands_all_1698_child_leaves_without_opaque_substitution() -> None:
    record, parent, chaku_rows, ruikei_rows = build_record()
    parsed = CKParser().parse(record)

    assert parsed is not None
    assert {name: parsed[name] for name in parent} == parent
    assert parsed["_ck_chaku_rows"] == chaku_rows
    assert parsed["_ck_ruikei_rows"] == ruikei_rows
    assert len(chaku_rows) == 278
    assert len(ruikei_rows) == 8
    # 277 complete six-count blocks plus four running-style counts make
    # 1,666 count leaves. Eight summaries hold another 32 leaves. The remaining
    # 31 official leaves are in
    # the parent or are the strictly validated CRLF delimiter.
    assert 277 * 6 + 4 + 32 == 1698
    assert 1698 + 31 == 1729


@pytest.mark.parametrize("data_kubun", ["", "3", "9"])
def test_ck_rejects_undefined_data_kubun(data_kubun: str) -> None:
    assert _rejects(build_record(data_kubun=data_kubun)[0])


def test_ck_rejects_previous_6864_byte_layout() -> None:
    assert _rejects(build_record()[0][:6862] + b"\r\n")


def test_ck_rejects_non_numeric_official_count_leaf() -> None:
    record = bytearray(build_record()[0])
    record[127:130] = b"0X1"
    assert CKParser().parse(bytes(record)) is None


def test_ck_normalized_native_schemas_fit_postgresql_and_have_exact_keys() -> None:
    assert set(CHILD_TABLES) <= set(SCHEMAS)
    assert get_table_primary_key_columns("NL_CK") == list(PARENT_KEY)
    assert get_table_primary_key_columns("NL_CK_CHAKU") == [
        *PARENT_KEY,
        "EntityKubun",
        "PeriodNum",
        "MetricKubun",
        "BucketNum",
    ]
    assert get_table_primary_key_columns("NL_CK_RUIKEI") == [
        *PARENT_KEY,
        "EntityKubun",
        "PeriodNum",
    ]
    assert len(get_table_column_types("NL_CK_CHAKU")) == 17
    assert len(get_table_column_types("NL_CK_RUIKEI")) == 16
    assert max(len(get_table_column_types(name)) for name in ("NL_CK", *CHILD_TABLES)) < 1600


def _create_ck_tables(database: SQLiteDatabase) -> None:
    database.create_table("NL_CK", SCHEMAS["NL_CK"])
    for table_name in CHILD_TABLES:
        database.create_table(table_name, SCHEMAS[table_name])


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ck_importers_store_update_delete_in_provider_order_and_reconnect(
    tmp_path, importer_class
) -> None:
    path = tmp_path / f"{importer_class.__name__}.db"
    initial = CKParser().parse(build_record()[0])
    updated_record = build_record(
        data_kubun="2",
        horse_name="更新完全馬",
        sequence_start=4000,
    )
    updated = CKParser().parse(updated_record[0])
    deletion = CKParser().parse(build_record(data_kubun="0")[0])
    database = SQLiteDatabase({"path": str(path)})
    with database:
        _create_ck_tables(database)
        stats = importer_class(database).import_records(iter([initial, deletion, updated]))
    assert stats["records_imported"] == 3
    assert stats["records_failed"] == 0

    with SQLiteDatabase({"path": str(path)}) as reopened:
        parent = reopened.fetch_one("SELECT Bamei, CKStorageVersion FROM NL_CK")
        counts = reopened.fetch_one("SELECT COUNT(*) AS count FROM NL_CK_CHAKU")
        summaries = reopened.fetch_one("SELECT COUNT(*) AS count FROM NL_CK_RUIKEI")
        count_sentinel = reopened.fetch_one(
            "SELECT Count1 FROM NL_CK_CHAKU WHERE EntityKubun = ? "
            "AND PeriodNum = ? AND MetricKubun = ? AND BucketNum = ?",
            ("UMA", 0, "ChakuSogo", 1),
        )
        summary_sentinel = reopened.fetch_one(
            "SELECT HonSyokinHeichi FROM NL_CK_RUIKEI " "WHERE EntityKubun = ? AND PeriodNum = ?",
            ("KISYU", 1),
        )
        assert parent == {"Bamei": "更新完全馬", "CKStorageVersion": 1}
        assert counts["count"] == 278
        assert summaries["count"] == 8
        assert count_sentinel == {"Count1": int(updated_record[2][0]["Count1"])}
        assert summary_sentinel == {"HonSyokinHeichi": int(updated_record[3][0]["HonSyokinHeichi"])}
        deleted = importer_class(reopened).import_records(iter([deletion]))
        assert deleted["records_imported"] == 1
        for table_name in ("NL_CK", *CHILD_TABLES):
            assert reopened.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"] == 0


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ck_import_refuses_missing_child_before_parent_mutation(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "missing-child.db")})
    with database:
        database.create_table("NL_CK", SCHEMAS["NL_CK"])
        with pytest.raises(SchemaMigrationError, match="NL_CK_CHAKU"):
            importer_class(database).import_records(iter([CKParser().parse(build_record()[0])]))
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_CK")["count"] == 0


def test_ck_parent_migration_marks_legacy_rows_incomplete_until_reimport(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-marker.db")})
    legacy_schema = SCHEMAS["NL_CK"].replace("            CKStorageVersion INTEGER,\n", "")
    with database:
        database.create_table("NL_CK", legacy_schema)
        database.execute(
            "INSERT INTO NL_CK "
            "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, KettoNum, Bamei) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (2025, 101, "05", 1, 1, 1, "2025000001", "legacy"),
        )
        database.commit()
        assert migrate_table_if_needed(database, "NL_CK", SCHEMAS["NL_CK"])
        assert database.fetch_one("SELECT Bamei, CKStorageVersion FROM NL_CK") == {
            "Bamei": "legacy",
            "CKStorageVersion": None,
        }


def test_ck_single_record_api_uses_the_same_coupled_contract(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "single.db")})
    parsed = CKParser().parse(build_record()[0])
    deletion = CKParser().parse(build_record(data_kubun="0")[0])
    with database:
        _create_ck_tables(database)
        importer = DataImporter(database)
        assert importer.import_single_record(parsed)
        assert database.fetch_one("SELECT CKStorageVersion FROM NL_CK") == {"CKStorageVersion": 1}
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_CK_CHAKU")["count"] == 278
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_CK_RUIKEI")["count"] == 8
        assert importer.import_single_record(deletion)
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_CK")["count"] == 0


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ck_standard_schema_mode_is_explicitly_unsupported(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "standard.db")})
    with database:
        with pytest.raises(SchemaMigrationError, match="CHOKYO_DETAIL"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter([CKParser().parse(build_record()[0])])
            )
        assert not database.table_exists("CHOKYO_DETAIL")


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ck_delete_rejects_forged_child_payload_before_mutation(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "delete-payload.db")})
    initial = CKParser().parse(build_record()[0])
    deletion = CKParser().parse(build_record(data_kubun="0")[0])
    deletion["_ck_chaku_rows"] = deepcopy(initial["_ck_chaku_rows"])
    with database:
        _create_ck_tables(database)
        importer_class(database).import_records(iter([initial]))
        with pytest.raises(SchemaMigrationError, match="must not carry"):
            importer_class(database).import_records(iter([deletion]))
        assert database.fetch_one("SELECT CKStorageVersion FROM NL_CK") == {"CKStorageVersion": 1}


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
@pytest.mark.parametrize("defect", ["reordered", "missing", "parent-key"])
def test_ck_metadata_defects_fail_before_replacing_a_complete_row(
    tmp_path, importer_class, defect
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"metadata-{defect}.db")})
    initial = CKParser().parse(build_record()[0])
    broken = deepcopy(CKParser().parse(build_record(data_kubun="2", sequence_start=5000)[0]))
    if defect == "reordered":
        broken["_ck_chaku_rows"][0], broken["_ck_chaku_rows"][1] = (
            broken["_ck_chaku_rows"][1],
            broken["_ck_chaku_rows"][0],
        )
    elif defect == "missing":
        broken["_ck_ruikei_rows"].pop()
    else:
        broken["_ck_chaku_rows"][0]["Year"] = "2025"
    with database:
        _create_ck_tables(database)
        importer_class(database).import_records(iter([initial]))
        before = database.fetch_one(
            "SELECT Count1 FROM NL_CK_CHAKU WHERE EntityKubun = 'UMA' "
            "AND MetricKubun = 'ChakuSogo'"
        )
        with pytest.raises(SchemaMigrationError):
            importer_class(database).import_records(iter([broken]))
        after = database.fetch_one(
            "SELECT Count1 FROM NL_CK_CHAKU WHERE EntityKubun = 'UMA' "
            "AND MetricKubun = 'ChakuSogo'"
        )
        assert after == before
        assert database.fetch_one("SELECT CKStorageVersion FROM NL_CK") == {"CKStorageVersion": 1}


def _weaken_ck_chaku_schema(defect: str) -> str:
    schema = SCHEMAS["NL_CK_CHAKU"]
    if defect == "not-validated":
        return schema
    if defect == "check-true":
        start = schema.index("CONSTRAINT ck_chaku_domain")
        end = schema.index(",\n            CONSTRAINT ck_chaku_count_shape", start)
        return schema[:start] + "CONSTRAINT ck_chaku_domain CHECK (TRUE)" + schema[end:]
    if defect == "token-tautology":
        start = schema.index("CONSTRAINT ck_chaku_domain")
        end = schema.index(",\n            CONSTRAINT ck_chaku_count_shape", start)
        constraint = schema[start:end].replace("CHECK (", "CHECK (TRUE OR (", 1) + ")"
        return schema[:start] + constraint + schema[end:]
    if defect == "weak-count-shape":
        start = schema.index("CONSTRAINT ck_chaku_count_shape")
        end = schema.index(",\n            PRIMARY KEY", start)
        constraint = (
            "CONSTRAINT ck_chaku_count_shape CHECK "
            "(Count5 IS NULL OR Count6 IS NULL OR MetricKubun = 'Kyakusitu')"
        )
        return schema[:start] + constraint + schema[end:]
    if defect == "restrict-fk":
        return schema.replace("ON DELETE CASCADE", "ON DELETE RESTRICT", 1)
    if defect == "wrong-fk-order":
        return schema.replace(
            "FOREIGN KEY (Year, MonthDay,",
            "FOREIGN KEY (MonthDay, Year,",
            1,
        )
    if defect == "nullable-dimension":
        return schema.replace("EntityKubun TEXT NOT NULL", "EntityKubun TEXT", 1)
    if defect == "wrong-pk":
        return schema.replace(
            ", MetricKubun, BucketNum)",
            ", MetricKubun)",
            1,
        )
    return schema.replace(
        ",\n            CONSTRAINT ck_chaku_parent_fk",
        ",\n            Unexpected INTEGER,\n            CONSTRAINT ck_chaku_parent_fk",
        1,
    )


def _ck_chaku_schema_without_count6_or_shape_check() -> str:
    schema = SCHEMAS["NL_CK_CHAKU"].replace("            Count6 INTEGER,\n", "")
    start = schema.index(",\n            CONSTRAINT ck_chaku_count_shape")
    end = schema.index(",\n            PRIMARY KEY", start)
    return schema[:start] + schema[end:]


def test_ck_child_schema_is_never_additively_repaired(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "no-additive-child.db")})
    with database:
        database.create_table("NL_CK", SCHEMAS["NL_CK"])
        database.create_table(
            "NL_CK_CHAKU",
            _ck_chaku_schema_without_count6_or_shape_check(),
        )
        assert SchemaManager(database).create_table("NL_CK_CHAKU") is False
        columns = {row["name"] for row in database.fetch_all('PRAGMA table_info("NL_CK_CHAKU")')}
        assert "Count6" not in columns


def test_ck_single_child_creation_rejects_tautological_check(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "single-child-check.db")})
    with database:
        database.create_table("NL_CK", SCHEMAS["NL_CK"])
        database.create_table("NL_CK_CHAKU", _weaken_ck_chaku_schema("check-true"))
        assert SchemaManager(database).create_table("NL_CK_CHAKU") is False


def test_ck_create_all_tables_reports_malformed_child_contract(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "create-all-malformed.db")})
    with database:
        database.create_table("NL_CK", SCHEMAS["NL_CK"])
        database.create_table("NL_CK_CHAKU", _weaken_ck_chaku_schema("check-true"))
        database.create_table("NL_CK_RUIKEI", SCHEMAS["NL_CK_RUIKEI"])
        results = SchemaManager(database).create_all_tables()
        assert results["NL_CK_CHAKU"] is False
        assert results["NL_CK_RUIKEI"] is False


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
@pytest.mark.parametrize(
    "defect",
    ["check-true", "restrict-fk", "nullable-dimension", "wrong-pk", "extra-column"],
)
def test_ck_malformed_child_schema_fails_closed_and_preserves_legacy_parent(
    tmp_path, importer_class, defect
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"schema-{defect}.db")})
    with database:
        database.create_table("NL_CK", SCHEMAS["NL_CK"])
        database.create_table("NL_CK_CHAKU", _weaken_ck_chaku_schema(defect))
        database.create_table("NL_CK_RUIKEI", SCHEMAS["NL_CK_RUIKEI"])
        database.execute(
            "INSERT INTO NL_CK "
            "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, KettoNum, Bamei) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (2025, 101, "05", 1, 1, 1, "2025000001", "preserve"),
        )
        database.commit()
        with pytest.raises(SchemaMigrationError):
            importer_class(database).import_records(iter([CKParser().parse(build_record()[0])]))
        assert database.fetch_all("SELECT Bamei, CKStorageVersion FROM NL_CK") == [
            {"Bamei": "preserve", "CKStorageVersion": None}
        ]


def test_ck_database_constraints_reject_orphan_invalid_dimension_and_null_count(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "constraints.db")})
    parsed = CKParser().parse(build_record()[0])
    with database:
        _create_ck_tables(database)
        DataImporter(database).import_records(iter([parsed]))
        stored = database.fetch_one("SELECT * FROM NL_CK_CHAKU LIMIT 1")
        invalid_rows = []
        orphan = dict(stored)
        orphan["KettoNum"] = "9999999999"
        invalid_rows.append(orphan)
        invalid_dimension = dict(stored)
        invalid_dimension["MetricKubun"] = "InventedMetric"
        invalid_rows.append(invalid_dimension)
        missing_count = dict(stored)
        missing_count["Count5"] = None
        invalid_rows.append(missing_count)
        for row in invalid_rows:
            with pytest.raises(DatabaseError):
                database.insert("NL_CK_CHAKU", row)
            database.rollback()
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_CK_CHAKU")["count"] == 278


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ck_postgresql_complete_roundtrip_reconnect_update_delete(
    postgresql_db, importer_class
) -> None:
    database, schema_name = postgresql_db
    database.execute(SCHEMAS["NL_CK"])
    database.execute(SCHEMAS["NL_CK_CHAKU"])
    database.execute(SCHEMAS["NL_CK_RUIKEI"])
    database.commit()
    initial = CKParser().parse(build_record()[0])
    updated_record = build_record(
        data_kubun="2",
        horse_name="PG更新完全馬",
        sequence_start=7000,
    )
    updated = CKParser().parse(updated_record[0])
    deletion = CKParser().parse(build_record(data_kubun="0")[0])
    stats = importer_class(database).import_records(iter([initial, deletion, updated]))
    assert stats["records_imported"] == 3
    assert stats["records_failed"] == 0

    database.disconnect()
    database.connect()
    database.execute(f"SET search_path TO {schema_name}")
    database.commit()
    assert database.fetch_one(
        'SELECT Bamei AS "Bamei", CKStorageVersion AS "CKStorageVersion" FROM NL_CK'
    ) == {"Bamei": "PG更新完全馬", "CKStorageVersion": 1}
    assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_CK_CHAKU")["count"] == 278
    assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_CK_RUIKEI")["count"] == 8
    assert database.fetch_one(
        'SELECT Count1 AS "Count1" FROM NL_CK_CHAKU '
        "WHERE EntityKubun = ? AND PeriodNum = ? AND MetricKubun = ? AND BucketNum = ?",
        ("UMA", 0, "ChakuSogo", 1),
    ) == {"Count1": int(updated_record[2][0]["Count1"])}
    stored = database.fetch_one("SELECT * FROM NL_CK_CHAKU LIMIT 1")
    invalid_dimension = dict(stored)
    invalid_dimension["metrickubun"] = "InventedMetric"
    with pytest.raises(DatabaseError):
        database.insert("NL_CK_CHAKU", invalid_dimension)
    database.rollback()
    orphan = dict(stored)
    orphan["kettonum"] = "9999999999"
    with pytest.raises(DatabaseError):
        database.insert("NL_CK_CHAKU", orphan)
    database.rollback()
    deleted = importer_class(database).import_records(iter([deletion]))
    assert deleted["records_imported"] == 1
    for table_name in ("NL_CK", *CHILD_TABLES):
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"] == 0


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
@pytest.mark.parametrize(
    "defect",
    [
        "check-true",
        "token-tautology",
        "weak-count-shape",
        "not-validated",
        "restrict-fk",
        "wrong-fk-order",
    ],
)
def test_ck_postgresql_malformed_constraints_fail_before_parent_mutation(
    postgresql_db, importer_class, defect
) -> None:
    database, _ = postgresql_db
    database.execute(SCHEMAS["NL_CK"])
    database.execute(_weaken_ck_chaku_schema(defect))
    if defect == "not-validated":
        schema = SCHEMAS["NL_CK_CHAKU"]
        start = schema.index("CONSTRAINT ck_chaku_domain")
        end = schema.index(",\n            CONSTRAINT ck_chaku_count_shape", start)
        domain_constraint = schema[start:end]
        database.execute("ALTER TABLE NL_CK_CHAKU DROP CONSTRAINT ck_chaku_domain")
        database.execute(f"ALTER TABLE NL_CK_CHAKU ADD {domain_constraint} NOT VALID")
    database.execute(SCHEMAS["NL_CK_RUIKEI"])
    database.execute(
        "INSERT INTO NL_CK "
        "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, KettoNum, Bamei) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (2025, 101, "05", 1, 1, 1, "2025000001", "preserve"),
    )
    database.commit()
    with pytest.raises(SchemaMigrationError):
        importer_class(database).import_records(iter([CKParser().parse(build_record()[0])]))
    assert database.fetch_one(
        'SELECT Bamei AS "Bamei", CKStorageVersion AS "CKStorageVersion" FROM NL_CK'
    ) == {"Bamei": "preserve", "CKStorageVersion": None}
