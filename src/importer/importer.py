"""Data importer for JLTSQL.

This module imports parsed JV-Data records into database.
"""

import json
import re
from typing import Any, Dict, Iterator, List, Optional

from src.database.base import BaseDatabase, DatabaseError
from src.database.migration import SchemaMigrationError
from src.database.schema_types import (
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def rollback_failed_import(database: BaseDatabase, *, context: str) -> None:
    """Rollback a failed strict import, invalidating an unrecoverable session."""
    try:
        database.rollback()
    except Exception as rollback_error:
        try:
            database.invalidate_connection()
        except Exception as invalidation_error:
            raise RuntimeError(
                f"{context}: rollback failed ({rollback_error}); connection "
                f"invalidation failed ({invalidation_error})"
            ) from invalidation_error
        logger.error(
            "Invalidated database after strict import rollback failure",
            context=context,
            error=str(rollback_error),
        )


def resolve_standard_storage_table_name(native_table_name: str) -> str:
    """Resolve the canonical standard storage owner without database checks."""
    from src.database.table_mappings import (
        JLTSQL_TO_JRAVAN,
        STANDARD_EXPANDED_RECORD_OWNER,
    )

    return STANDARD_EXPANDED_RECORD_OWNER.get(
        native_table_name,
        JLTSQL_TO_JRAVAN.get(native_table_name, native_table_name),
    )


def resolve_standard_table_name(database: BaseDatabase, native_table_name: str) -> str:
    """Resolve a canonical standard table and reject unsupported legacy-only storage."""
    standard_name = resolve_standard_storage_table_name(native_table_name)
    if native_table_name == "NL_CK":
        raise SchemaMigrationError(
            "CK standard-schema storage is not implemented; use native NL_CK until the "
            "canonical CHOKYO_DETAIL parent/child contract is available"
        )
    if (
        native_table_name == "NL_BT"
        and database.is_connected()
        and database.table_exists("BLOOD")
        and not database.table_exists(standard_name)
    ):
        raise SchemaMigrationError(
            "Legacy standard table BLOOD exists but canonical KEITO does not. "
            "Automatic BT import is refused; rebuild the standard table as KEITO "
            "and reimport current 6,889-byte source records."
        )
    if (
        native_table_name == "NL_JG"
        and database.is_connected()
        and database.table_exists("WEIGHT_CHANGE")
        and not database.table_exists(standard_name)
    ):
        raise SchemaMigrationError(
            "Legacy standard table WEIGHT_CHANGE exists but canonical JOGAIBA does not. "
            "Automatic JG import is refused; rebuild the standard table as JOGAIBA "
            "and reimport current 80-byte source records."
        )
    if (
        native_table_name == "NL_WF"
        and database.is_connected()
        and database.table_exists(_WF_LEGACY_STANDARD_TABLE)
        and not database.table_exists(standard_name)
    ):
        raise SchemaMigrationError(
            "Legacy standard table WIN5 exists but canonical JYUSYOSIKI_HEAD does not. "
            "Automatic WF import is refused; rebuild the standard tables as "
            "JYUSYOSIKI_HEAD plus JYUSYOSIKI and reimport current 7,215-byte "
            "source records."
        )
    if (
        native_table_name == "NL_SK"
        and database.is_connected()
        and database.table_exists("HANSYOKU_UMA")
        and not database.table_exists(standard_name)
    ):
        raise SchemaMigrationError(
            "Legacy standard table HANSYOKU_UMA exists but canonical SANKU does not. "
            "Automatic SK import is refused; rebuild the standard table as SANKU and "
            "reimport current-shape source records."
        )
    if (
        native_table_name == "NL_BR"
        and database.is_connected()
        and database.table_exists("BREEDER")
        and not database.table_exists(standard_name)
    ):
        raise SchemaMigrationError(
            "Legacy standard table BREEDER exists but canonical SEISAN does not. "
            "Automatic BR import is refused; rebuild the standard table as SEISAN and "
            "reimport current-shape source records."
        )
    if (
        native_table_name == "NL_HY"
        and database.is_connected()
        and database.table_exists("MEANING")
        and not database.table_exists(standard_name)
    ):
        raise SchemaMigrationError(
            "Legacy standard table MEANING exists but canonical BAMEIORIGIN does not. "
            "Automatic HY import is refused; rebuild the standard table as "
            "BAMEIORIGIN and reimport current-shape source records."
        )
    if (
        native_table_name == "NL_DM"
        and database.is_connected()
        and database.table_exists("DATA_MASTER")
        and not database.table_exists(standard_name)
    ):
        raise SchemaMigrationError(
            "Legacy standard table DATA_MASTER exists but canonical MINING does not. "
            "Automatic DM import is refused; rebuild the standard table as MINING and "
            "reimport official 303-byte source records."
        )
    if (
        native_table_name == "NL_TM"
        and database.is_connected()
        and database.table_exists("TIME_MASTER")
        and not database.table_exists(standard_name)
    ):
        raise SchemaMigrationError(
            "Legacy standard table TIME_MASTER exists but canonical "
            "TAISENGATA_MINING does not. Automatic TM import is refused; rebuild "
            "the standard table as TAISENGATA_MINING and reimport official "
            "141-byte source records."
        )
    return standard_name


_STANDARD_FIELD_ALIASES = {
    "HANSYOKU": {
        "MochiKubun": "HansyokuMochiKubun",
        "FHansyokuNum": "HansyokuFNum",
        "MHansyokuNum": "HansyokuMNum",
    },
    "TENKO_BABA": {
        "TenkoState": "AtoTenkoCD",
        "SibaBabaState": "AtoSibaBabaCD",
        "DirtBabaState": "AtoDirtBabaCD",
        "TenkoState2": "MaeTenkoCD",
        "SibaBabaState2": "MaeSibaBabaCD",
        "DirtBabaState2": "MaeDirtBabaCD",
    },
    "CHOKYO": {
        **{
            f"SaikinJyusyo{block}_{suffix}": (
                f"SaikinJyusyo{block}SaikinJyusyoid"
                if suffix == "id"
                else f"SaikinJyusyo{block}{suffix}"
            )
            for block in range(1, 4)
            for suffix in (
                "id",
                "Hondai",
                "Ryakusyo10",
                "Ryakusyo6",
                "Ryakusyo3",
                "GradeCD",
                "SyussoTosu",
                "KettoNum",
                "Bamei",
            )
        }
    },
    "TOKU": {
        "RenbanNum": "Num",
    },
    "JOGAIBA": {
        "Num": "ShutsubaTohyoJun",
        "SyussoKubun": "ShussoKubun",
        "JyogaiStateKubun": "JogaiJotaiKubun",
    },
    "WOOD": {
        "BabaMawari": "BabaAround",
        "HaronTime10Total": "HaronTime10",
        "LapTime_2000M_1800M": "LapTime10",
        "HaronTime9Total": "HaronTime9",
        "LapTime_1800M_1600M": "LapTime9",
        "HaronTime8Total": "HaronTime8",
        "LapTime_1600M_1400M": "LapTime8",
        "HaronTime7Total": "HaronTime7",
        "LapTime_1400M_1200M": "LapTime7",
        "HaronTime6Total": "HaronTime6",
        "LapTime_1200M_1000M": "LapTime6",
        "HaronTime5Total": "HaronTime5",
        "LapTime_1000M_800M": "LapTime5",
        "HaronTime4Total": "HaronTime4",
        "LapTime_800M_600M": "LapTime4",
        "HaronTime3Total": "HaronTime3",
        "LapTime_600M_400M": "LapTime3",
        "HaronTime2Total": "HaronTime2",
        "LapTime_400M_200M": "LapTime2",
        "LapTime_200M_0M": "LapTime1",
    },
    "JYUSYOSIKI_HEAD": {
        "Yobi1": "reserved1",
        "Yobi2": "reserved2",
        "TekichuNasiFlag": "TekichunashiFlag",
        "CarryOverStart": "CarryoverSyoki",
        "CarryOverBalance": "CarryoverZandaka",
    },
    "TOKU_RACE": {
        "RaceRyakusyo10": "Ryakusyo10",
        "RaceRyakusyo6": "Ryakusyo6",
        "RaceRyakusyo3": "Ryakusyo3",
        "RaceMeiKubun": "Kubun",
        "JyusyoKaiji": "Nkai",
        "JyokenCD2": "JyokenCD1",
        "JyokenCD3": "JyokenCD2",
        "JyokenCD4": "JyokenCD3",
        "JyokenCD5": "JyokenCD4",
        "JyokenCDYoung": "JyokenCD5",
        "CourseKubun": "CourseKubunCD",
        "HandeHappyoDate": "HandiDate",
    },
}


def translate_standard_field_names(record: dict, table_name: str) -> dict:
    """Translate legacy native parser names for a standard-name table."""
    aliases = _STANDARD_FIELD_ALIASES.get(table_name)
    if not aliases:
        return record
    translated = dict(record)
    for source, target in aliases.items():
        if source in translated and target not in translated:
            translated[target] = translated.pop(source)
    return translated


_RC_STORAGE_TABLES = frozenset({"NL_RC", "RECORD"})
_RC_KEY_COLUMNS = (
    "RecInfoKubun",
    "Year",
    "MonthDay",
    "JyoCD",
    "Kaiji",
    "Nichiji",
    "RaceNum",
    "TokuNum",
    "SyubetuCD",
    "Kyori",
    "TrackCD",
)

_YS_STORAGE_TABLES = frozenset({"NL_YS", "SCHEDULE"})
_YS_KEY_COLUMNS = ("Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji")
_TK_CHILD_STORAGE_TABLES = frozenset({"NL_TK", "TOKU"})
_TK_KEY_COLUMNS = ("Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum")
_TK_ROWS_KEY = "_tk_registered_horse_rows"
_HY_STORAGE_TABLES = frozenset({"NL_HY", "BAMEIORIGIN"})
_BT_STORAGE_TABLES = frozenset({"NL_BT", "KEITO"})
_JG_STORAGE_TABLES = frozenset({"NL_JG", "JOGAIBA"})
_JG_KEY_COLUMNS = (
    "Year",
    "MonthDay",
    "JyoCD",
    "Kaiji",
    "Nichiji",
    "RaceNum",
    "KettoNum",
    "Num",
)
_WC_STORAGE_TABLES = frozenset({"NL_WC", "WOOD"})
_WC_KEY_COLUMNS = ("TresenKubun", "ChokyoDate", "ChokyoTime", "KettoNum")
_WF_NATIVE_STORAGE_TABLES = frozenset({"NL_WF", "RT_WF"})
_WF_STANDARD_HEAD_TABLE = "JYUSYOSIKI_HEAD"
_WF_STANDARD_CHILD_TABLE = "JYUSYOSIKI"
_WF_STANDARD_STORAGE_TABLES = frozenset({_WF_STANDARD_HEAD_TABLE})
_WF_STORAGE_TABLES = _WF_NATIVE_STORAGE_TABLES | _WF_STANDARD_STORAGE_TABLES
_WF_KEY_COLUMNS = ("Year", "MonthDay")
_WF_LEGACY_STANDARD_TABLE = "WIN5"
_WF_RACE_SPLIT = (("JyoCD", 0, 2), ("Kaiji", 2, 4), ("Nichiji", 4, 6), ("RaceNum", 6, 8))
# JYUSYOSIKI (the WF child) is never a resolved standard owner name; preflight
# verifies it strictly through verify_wf_coupled_tables instead.
_STRICT_NONADDITIVE_STANDARD_TABLES = frozenset(
    {"KEITO", "JOGAIBA", "WOOD", _WF_STANDARD_HEAD_TABLE}
)
_LEGACY_STANDARD_PREFLIGHT_NATIVE_TABLES = (
    "NL_BT",
    "NL_JG",
    "NL_SK",
    "NL_BR",
    "NL_HY",
    "NL_DM",
    "NL_TM",
    "NL_WF",
)
_ORDERED_MASTER_STORAGE_TABLES = _RC_STORAGE_TABLES | _YS_STORAGE_TABLES | _TK_CHILD_STORAGE_TABLES


def verify_bt_storage_schema(database: BaseDatabase, table_name: str) -> bool:
    """Fail closed unless BT storage preserves every current field and key."""
    if table_name not in _BT_STORAGE_TABLES:
        return False

    from src.database.migration import verify_table_schema
    from src.database.schema import SCHEMAS
    from src.database.schema_jravan import JRAVAN_SCHEMAS

    schema_sql = SCHEMAS.get(table_name) or JRAVAN_SCHEMAS.get(table_name)
    if schema_sql is None:
        raise SchemaMigrationError(f"BT storage schema is undefined: {table_name}")
    verify_table_schema(database, table_name, schema_sql)
    return True


def verify_jg_storage_schema(database: BaseDatabase, table_name: str) -> bool:
    """Fail closed unless JG storage preserves every field and the eight-part key."""
    if table_name not in _JG_STORAGE_TABLES:
        return False

    from src.database.migration import verify_table_schema
    from src.database.schema import SCHEMAS
    from src.database.schema_jravan import JRAVAN_SCHEMAS

    schema_sql = SCHEMAS.get(table_name) or JRAVAN_SCHEMAS.get(table_name)
    if schema_sql is None:
        raise SchemaMigrationError(f"JG storage schema is undefined: {table_name}")
    verify_table_schema(database, table_name, schema_sql)
    return True


def validate_jg_record(record: dict, table_name: str) -> bool:
    """Revalidate a JG row's status and official key immediately before storage.

    The parser already enforces the current contract, but importer entry points
    also accept caller-built dictionaries. A row outside ``DataKubun`` 0/1 or
    without the complete eight-part key must stop the import before any row of
    that record can be upserted, deleted, or silently skipped.
    """
    if table_name not in _JG_STORAGE_TABLES:
        return False
    if _record_type_from_record(record) != "JG":
        raise SchemaMigrationError(f"{table_name} received a non-JG record")

    from src.parser.jg_parser import JGParser

    if record.get("DataKubun") in (None, "") and record.get("headDataKubun") in (
        None,
        "",
    ):
        raise SchemaMigrationError("JG DataKubun is required")
    try:
        data_kubun = resolve_record_data_kubun(record)
    except ValueError as error:
        raise SchemaMigrationError(str(error)) from error
    if data_kubun not in JGParser.DATA_KUBUN_VALUES:
        raise SchemaMigrationError(f"JG record has unsupported DataKubun: {data_kubun!r}")
    aliases = _STANDARD_FIELD_ALIASES.get(table_name, {})
    conflicts = [
        (native_name, standard_name)
        for native_name, standard_name in aliases.items()
        if native_name in record
        and standard_name in record
        and record[native_name] != record[standard_name]
    ]
    if conflicts:
        raise SchemaMigrationError(f"conflicting JG alias values: {conflicts}")

    def value_for(native_name: str):
        if native_name in record:
            return record[native_name]
        return record.get(aliases.get(native_name, native_name))

    missing = [column for column in _JG_KEY_COLUMNS if value_for(column) in (None, "")]
    if missing:
        raise SchemaMigrationError(f"JG record has incomplete official key: {missing}")

    digit_widths = {
        "MakeDate": 8,
        "Year": 4,
        "MonthDay": 4,
        "Kaiji": 2,
        "Nichiji": 2,
        "RaceNum": 2,
        "KettoNum": 10,
        "Num": 3,
    }
    for field_name, width in digit_widths.items():
        value = value_for(field_name)
        if (
            not isinstance(value, str)
            or len(value) != width
            or not value.isascii()
            or not value.isdigit()
        ):
            raise SchemaMigrationError(
                f"JG record {field_name} must be exactly {width} ASCII digits"
            )
    jyo_cd = value_for("JyoCD")
    if (
        not isinstance(jyo_cd, str)
        or len(jyo_cd) != 2
        or not jyo_cd.isascii()
        or not jyo_cd.isalnum()
    ):
        raise SchemaMigrationError("JG record JyoCD must be a 2-character code")

    syusso = value_for("SyussoKubun")
    if syusso not in JGParser.SYUSSO_KUBUN_VALUES and not (
        data_kubun == "0" and syusso in (None, "")
    ):
        raise SchemaMigrationError(
            f"JG record SyussoKubun has unsupported code: {syusso!r}"
        )
    jyogai = value_for("JyogaiStateKubun")
    if jyogai not in JGParser.JYOGAI_STATE_KUBUN_VALUES and not (
        data_kubun == "0" and jyogai in (None, "")
    ):
        raise SchemaMigrationError(
            f"JG record JyogaiStateKubun has unsupported code: {jyogai!r}"
        )
    return True


def verify_wc_storage_schema(database: BaseDatabase, table_name: str) -> bool:
    """Fail closed unless WC storage preserves every field and official key."""
    if table_name not in _WC_STORAGE_TABLES:
        return False

    from src.database.migration import verify_table_schema
    from src.database.schema import SCHEMAS
    from src.database.schema_jravan import JRAVAN_SCHEMAS

    schema_sql = SCHEMAS.get(table_name) or JRAVAN_SCHEMAS.get(table_name)
    if schema_sql is None:
        raise SchemaMigrationError(f"WC storage schema is undefined: {table_name}")
    verify_table_schema(database, table_name, schema_sql)
    return True


def validate_wc_record(record: dict, table_name: str) -> bool:
    """Revalidate a caller-built WC row before any insert, update, or delete."""
    if table_name not in _WC_STORAGE_TABLES:
        return False
    if _record_type_from_record(record) != "WC":
        raise SchemaMigrationError(f"{table_name} received a non-WC record")

    from src.parser.wc_parser import WCParser

    if record.get("DataKubun") in (None, "") and record.get("headDataKubun") in (
        None,
        "",
    ):
        raise SchemaMigrationError("WC DataKubun is required")
    try:
        data_kubun = resolve_record_data_kubun(record)
    except ValueError as error:
        raise SchemaMigrationError(str(error)) from error
    if data_kubun not in WCParser.DATA_KUBUN_VALUES:
        raise SchemaMigrationError(f"WC record has unsupported DataKubun: {data_kubun!r}")

    aliases = _STANDARD_FIELD_ALIASES.get(table_name, {})
    conflicts = [
        (native_name, standard_name)
        for native_name, standard_name in aliases.items()
        if native_name in record
        and standard_name in record
        and record[native_name] != record[standard_name]
    ]
    if conflicts:
        raise SchemaMigrationError(f"conflicting WC alias values: {conflicts}")

    def value_for(native_name: str):
        if native_name in record:
            return record[native_name]
        return record.get(aliases.get(native_name, native_name))

    def require_digits(name: str, width: int) -> None:
        value = value_for(name)
        if (
            not isinstance(value, str)
            or len(value) != width
            or not value.isascii()
            or not value.isdigit()
        ):
            raise SchemaMigrationError(
                f"WC record {name} must be exactly {width} ASCII digits"
            )

    for field_name, width in WCParser.KEY_FIXED_FIELDS:
        require_digits(field_name, width)
    try:
        WCParser._require_yyyymmdd("MakeDate", value_for("MakeDate"))
        WCParser._require_yyyymmdd("ChokyoDate", value_for("ChokyoDate"))
        WCParser._require_hhmm("ChokyoTime", value_for("ChokyoTime"))
    except ValueError as error:
        raise SchemaMigrationError(str(error)) from error
    if value_for("TresenKubun") not in WCParser.TRESEN_KUBUN_VALUES:
        raise SchemaMigrationError("WC record TresenKubun must be 0 or 1")

    # DataKubun=0 is a keyed command; the provider does not define a blank-body
    # requirement. Status 1 owns the payload and therefore validates all codes
    # and every fixed-width timing value.
    if data_kubun == "1":
        if value_for("Course") not in WCParser.COURSE_VALUES:
            raise SchemaMigrationError("WC record Course must be in 0..4")
        if value_for("BabaMawari") not in WCParser.BABA_MAWARI_VALUES:
            raise SchemaMigrationError("WC record BabaMawari must be 0 or 1")
        try:
            WCParser._require_cp932_width("reserved", value_for("reserved"), 1)
        except ValueError as error:
            raise SchemaMigrationError(str(error)) from error
        for field_name, width in WCParser.TIME_FIXED_FIELDS:
            require_digits(field_name, width)
    return True


def _verify_wf_sqlite_foreign_key(database: BaseDatabase) -> None:
    """Require the actual JYUSYOSIKI -> JYUSYOSIKI_HEAD cascade in SQLite."""
    enforcement = database.fetch_one("PRAGMA foreign_keys")
    if not enforcement or int(next(iter(enforcement.values()), 0)) != 1:
        raise SchemaMigrationError("WF child foreign key enforcement is disabled for SQLite")
    rows = database.fetch_all(f'PRAGMA foreign_key_list("{_WF_STANDARD_CHILD_TABLE}")')
    ordered = sorted(rows, key=lambda item: (int(item["id"]), int(item["seq"])))
    expected = [column.lower() for column in _WF_KEY_COLUMNS]
    if not ordered or len({int(item["id"]) for item in ordered}) != 1:
        raise SchemaMigrationError(
            f"WF child {_WF_STANDARD_CHILD_TABLE} must declare exactly one composite "
            f"foreign key to {_WF_STANDARD_HEAD_TABLE}"
        )
    local = [str(item["from"]).lower() for item in ordered]
    remote_values = [item["to"] for item in ordered]
    if all(value is None for value in remote_values):
        # An implicit reference targets the parent primary key, which
        # verify_table_schema already proved to be (Year, MonthDay).
        remote = expected
    else:
        remote = [str(value).lower() for value in remote_values]
    if (
        local != expected
        or remote != expected
        or any(str(item["table"]).lower() != _WF_STANDARD_HEAD_TABLE.lower() for item in ordered)
        or any(str(item["on_delete"]).upper() != "CASCADE" for item in ordered)
        or any(str(item["on_update"]).upper() != "NO ACTION" for item in ordered)
        or any(str(item["match"]).upper() != "NONE" for item in ordered)
    ):
        raise SchemaMigrationError(
            f"WF child foreign key mismatch for {_WF_STANDARD_CHILD_TABLE}: expected "
            f"({', '.join(_WF_KEY_COLUMNS)}) -> {_WF_STANDARD_HEAD_TABLE} "
            "MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE"
        )


def _verify_wf_postgresql_foreign_key(database: BaseDatabase) -> None:
    """Require the actual JYUSYOSIKI -> JYUSYOSIKI_HEAD cascade in PostgreSQL."""
    trigger_mode = database.fetch_one(
        "SELECT current_setting('session_replication_role') AS trigger_mode"
    )
    if not trigger_mode or str(trigger_mode.get("trigger_mode")) != "origin":
        raise SchemaMigrationError(
            "WF child foreign key enforcement requires PostgreSQL origin trigger mode"
        )
    child = _WF_STANDARD_CHILD_TABLE.lower()
    parent = _WF_STANDARD_HEAD_TABLE.lower()
    rows = database.fetch_all(
        "SELECT oid AS constraint_oid, confdeltype AS delete_type, "
        "confupdtype AS update_type, confmatchtype AS match_type, "
        "condeferrable AS deferrable, condeferred AS initially_deferred, "
        "convalidated AS validated, confrelid = to_regclass(?) AS parent_matches "
        "FROM pg_constraint WHERE conrelid = to_regclass(?) AND contype = 'f'",
        (parent, child),
    )
    if len(rows) != 1:
        raise SchemaMigrationError(
            f"WF child {_WF_STANDARD_CHILD_TABLE} must declare exactly one composite "
            f"foreign key to {_WF_STANDARD_HEAD_TABLE}"
        )
    row = rows[0]
    if (
        str(row.get("delete_type")) != "c"
        or str(row.get("update_type")) != "a"
        or str(row.get("match_type")) != "s"
        or not bool(row.get("validated"))
        or not bool(row.get("parent_matches"))
        or bool(row.get("deferrable"))
        or bool(row.get("initially_deferred"))
    ):
        raise SchemaMigrationError(
            f"WF child foreign key mismatch for {_WF_STANDARD_CHILD_TABLE}: expected a "
            f"validated immediate MATCH SIMPLE reference to {_WF_STANDARD_HEAD_TABLE} "
            "ON DELETE CASCADE ON UPDATE NO ACTION"
        )
    key_rows = database.fetch_all(
        "SELECT local_column.attname AS local_name, remote_column.attname AS remote_name "
        "FROM pg_constraint constraint_row "
        "JOIN LATERAL generate_subscripts(constraint_row.conkey, 1) "
        "AS key_position(position) ON TRUE "
        "JOIN pg_attribute local_column ON local_column.attrelid = constraint_row.conrelid "
        "AND local_column.attnum = constraint_row.conkey[key_position.position] "
        "JOIN pg_attribute remote_column ON remote_column.attrelid = constraint_row.confrelid "
        "AND remote_column.attnum = constraint_row.confkey[key_position.position] "
        "WHERE constraint_row.oid = ? ORDER BY key_position.position",
        (int(row["constraint_oid"]),),
    )
    expected = [column.lower() for column in _WF_KEY_COLUMNS]
    if (
        [str(key_row["local_name"]).lower() for key_row in key_rows] != expected
        or [str(key_row["remote_name"]).lower() for key_row in key_rows] != expected
    ):
        raise SchemaMigrationError(
            f"WF child foreign key columns mismatch for {_WF_STANDARD_CHILD_TABLE}: "
            f"expected ordered ({', '.join(_WF_KEY_COLUMNS)})"
        )
    trigger_rows = database.fetch_all(
        "SELECT tgenabled AS enabled, tgrelid = to_regclass(?) AS on_child, "
        "tgrelid = to_regclass(?) AS on_parent "
        "FROM pg_trigger WHERE tgconstraint = ? AND tgisinternal ORDER BY oid",
        (child, parent, int(row["constraint_oid"])),
    )
    if (
        len(trigger_rows) != 4
        or any(str(trigger["enabled"]) != "O" for trigger in trigger_rows)
        or sum(bool(trigger["on_child"]) for trigger in trigger_rows) != 2
        or sum(bool(trigger["on_parent"]) for trigger in trigger_rows) != 2
    ):
        raise SchemaMigrationError(
            f"WF child foreign key triggers are not active for {_WF_STANDARD_CHILD_TABLE}"
        )


def _normalize_wf_column_type(declared_type: str) -> str:
    """Return the exact logical type used by the frozen WF storage contract."""
    normalized = re.sub(r"\s+", " ", declared_type.strip().lower())
    match = re.fullmatch(
        r"(?:varchar|character varying)\s*\(\s*(\d+)\s*\)", normalized
    )
    if match:
        return f"varchar({int(match.group(1))})"
    match = re.fullmatch(r"(?:char|character)\s*\(\s*(\d+)\s*\)", normalized)
    if match:
        return f"char({int(match.group(1))})"
    aliases = {
        "text": "text",
        "smallint": "smallint",
        "int2": "smallint",
        "integer": "integer",
        "int": "integer",
        "int4": "integer",
        "bigint": "bigint",
        "int8": "bigint",
        "date": "date",
    }
    return aliases.get(normalized, f"unsupported:{normalized or '<empty>'}")


def _verify_wf_column_types(
    database: BaseDatabase, table_name: str, schema_sql: str
) -> None:
    """Require every existing WF column to retain its declared logical type."""
    from src.database.migration import (
        _definition_type,
        _extract_column_definitions,
        _get_existing_column_types,
    )

    definitions = _extract_column_definitions(schema_sql)
    if definitions is None:
        raise SchemaMigrationError(f"Could not parse WF schema for {table_name}")
    actual_types = _get_existing_column_types(database, table_name)
    mismatches = []
    for column, definition in definitions.items():
        expected = _normalize_wf_column_type(_definition_type(definition))
        actual_raw = actual_types.get(column.lower(), "")
        actual = _normalize_wf_column_type(actual_raw)
        if actual != expected:
            mismatches.append(
                f"{column} existing={actual_raw or '<unknown>'} expected={expected}"
            )
    if mismatches:
        raise SchemaMigrationError(
            f"WF column type mismatch for {table_name}: {', '.join(mismatches)}"
        )


def _verify_wf_unique_and_primary_constraints(
    database: BaseDatabase, table_name: str
) -> None:
    """Reject replacement-changing UNIQUEs and unusable PostgreSQL PKs."""
    db_type = database.get_db_type()
    if db_type == "sqlite":
        indexes = database.fetch_all(f'PRAGMA index_list("{table_name}")')
        unexpected = [
            str(row.get("name") or "<unnamed>")
            for row in indexes
            if int(row.get("unique") or 0) == 1
            and str(row.get("origin") or "").lower() != "pk"
        ]
        if unexpected:
            raise SchemaMigrationError(
                f"WF storage {table_name} has unsupported additional UNIQUE "
                f"constraints/indexes: {unexpected}"
            )
        return
    if db_type != "postgresql":
        raise SchemaMigrationError(
            f"WF constraints cannot be verified for database type {db_type!r}"
        )

    indexes = database.fetch_all(
        "SELECT index_class.relname AS index_name, index_row.indisprimary AS is_primary, "
        "index_row.indisunique AS is_unique, index_row.indisexclusion AS is_exclusion, "
        "index_row.indisvalid AS is_valid, index_row.indisready AS is_ready, "
        "index_row.indimmediate AS is_immediate, "
        "constraint_row.condeferrable AS is_deferrable, "
        "constraint_row.condeferred AS is_deferred, "
        "constraint_row.convalidated AS is_validated "
        "FROM pg_index index_row "
        "JOIN pg_class index_class ON index_class.oid = index_row.indexrelid "
        "LEFT JOIN pg_constraint constraint_row "
        "ON constraint_row.conindid = index_row.indexrelid "
        "AND constraint_row.conrelid = index_row.indrelid "
        "AND constraint_row.contype = 'p' "
        "WHERE index_row.indrelid = to_regclass(?) ORDER BY index_class.relname",
        (table_name.lower(),),
    )
    unexpected = [
        str(row.get("index_name") or "<unnamed>")
        for row in indexes
        if not bool(row.get("is_primary"))
        and (bool(row.get("is_unique")) or bool(row.get("is_exclusion")))
    ]
    if unexpected:
        raise SchemaMigrationError(
            f"WF storage {table_name} has unsupported additional UNIQUE/exclusion "
            f"indexes: {unexpected}"
        )
    primary = [row for row in indexes if bool(row.get("is_primary"))]
    if len(primary) != 1:
        raise SchemaMigrationError(
            f"WF primary key catalog mismatch for {table_name}: expected one primary key"
        )
    key = primary[0]
    if (
        not bool(key.get("is_unique"))
        or not bool(key.get("is_valid"))
        or not bool(key.get("is_ready"))
        or not bool(key.get("is_immediate"))
        or bool(key.get("is_deferrable"))
        or bool(key.get("is_deferred"))
        or not bool(key.get("is_validated"))
    ):
        raise SchemaMigrationError(
            f"WF primary key for {table_name} must be valid, ready, immediate, "
            "non-deferrable, and usable by ON CONFLICT"
        )


def _verify_wf_table_contract(
    database: BaseDatabase, table_name: str, schema_sql: str
) -> None:
    """Verify one concrete WF table without applying any migration."""
    from src.database.migration import verify_table_schema

    verify_table_schema(database, table_name, schema_sql)
    _verify_wf_column_types(database, table_name, schema_sql)
    _verify_wf_unique_and_primary_constraints(database, table_name)


def verify_wf_coupled_tables(database: BaseDatabase) -> None:
    """Fail closed unless JYUSYOSIKI_HEAD and JYUSYOSIKI form the official pair.

    Both tables must exist with every column and their ordered primary keys,
    and the child must carry the composite ``(Year, MonthDay)`` foreign key with
    ``ON DELETE CASCADE``. The catalog is inspected directly (PRAGMA /
    pg_constraint), never inferred from constraint names.
    """
    from src.database.migration import _migration_targets
    from src.database.schema_jravan import JRAVAN_SCHEMAS

    for target in _migration_targets(database):
        for required_table in (_WF_STANDARD_HEAD_TABLE, _WF_STANDARD_CHILD_TABLE):
            if not target.table_exists_strict(required_table):
                raise SchemaMigrationError(
                    f"WF import requires table {required_table} before mutation"
                )
        for required_table in (_WF_STANDARD_HEAD_TABLE, _WF_STANDARD_CHILD_TABLE):
            _verify_wf_table_contract(
                target, required_table, JRAVAN_SCHEMAS[required_table]
            )
        db_type = target.get_db_type()
        if db_type == "sqlite":
            _verify_wf_sqlite_foreign_key(target)
        elif db_type == "postgresql":
            _verify_wf_postgresql_foreign_key(target)
        else:
            raise SchemaMigrationError(
                f"WF child foreign key cannot be verified for database type {db_type!r}"
            )


def verify_wf_storage_schema(database: BaseDatabase, table_name: str) -> bool:
    """Fail closed unless WF storage preserves the official key and payload."""
    if table_name in _WF_NATIVE_STORAGE_TABLES:
        from src.database.migration import _migration_targets
        from src.database.schema import SCHEMAS

        for target in _migration_targets(database):
            _verify_wf_table_contract(target, table_name, SCHEMAS[table_name])
        return True
    if table_name in _WF_STANDARD_STORAGE_TABLES:
        verify_wf_coupled_tables(database)
        return True
    return False


def _wf_payout_tuples(payouts_json: Any) -> list[tuple[Any, Any, Any]]:
    """Decode PayoutsJson into exactly 243 (Kumi, Pay, Votes) tuples."""
    from src.parser.wf_parser import WFParser

    if not isinstance(payouts_json, str):
        raise ValueError("WF PayoutsJson must be JSON text describing 243 payout slots")
    try:
        decoded = json.loads(payouts_json)
    except ValueError as error:
        raise ValueError("WF PayoutsJson is not valid JSON") from error
    if not isinstance(decoded, list) or len(decoded) != WFParser.PAYOUT_COUNT:
        raise ValueError(
            f"WF PayoutsJson must contain exactly {WFParser.PAYOUT_COUNT} payout slots"
        )
    expected_keys = set(WFParser.PAYOUT_KEYS)
    tuples = []
    for index, slot in enumerate(decoded, start=1):
        if not isinstance(slot, dict) or set(slot) != expected_keys:
            raise ValueError(
                f"WF payout slot {index} must be a Kumi/PayJyushosiki/TekichuHyosu dictionary"
            )
        tuples.append(tuple(slot[key] for key in WFParser.PAYOUT_KEYS))
    return tuples


def _wf_split_conflicts(record: dict) -> list[str]:
    """Report caller split race fields that contradict the composite values."""
    from src.parser.wf_parser import WFParser

    conflicts = []
    for index in range(1, WFParser.RACE_COUNT + 1):
        composite = record.get(f"RaceInfo{index}")
        if not isinstance(composite, str) or len(composite) != 8:
            continue
        for name, start, end in _WF_RACE_SPLIT:
            provided = record.get(f"{name}{index}")
            if provided in (None, ""):
                continue
            expected = composite[start:end]
            actual = str(provided).strip()
            if name == "JyoCD":
                matches = actual == expected
            else:
                matches = actual.isdigit() and expected.isdigit() and int(actual) == int(expected)
            if not matches:
                conflicts.append(f"{name}{index}")
    return conflicts


def validate_wf_record(record: dict, table_name: str) -> bool:
    """Revalidate a caller-built WF row before any coercion or mutation.

    The parser already enforces the official contract, but importer and
    realtime entry points also accept dictionaries. Record-type and status
    aliases must be present and consistent, the key must be a real date, and
    the state-dependent body plus all 243 payout slots must be valid before
    generic numeric coercion could silently strip characters. A status-0 row
    is an exact-key erase whose body stays opaque.
    """
    if table_name not in _WF_STORAGE_TABLES:
        return False
    if _record_type_from_record(record) != "WF":
        raise SchemaMigrationError(f"{table_name} received a non-WF record")

    from src.parser.wf_parser import WFParser

    if record.get("DataKubun") in (None, "") and record.get("headDataKubun") in (
        None,
        "",
    ):
        raise SchemaMigrationError("WF DataKubun is required")
    try:
        data_kubun = resolve_record_data_kubun(record)
    except ValueError as error:
        raise SchemaMigrationError(str(error)) from error
    allowed = (
        WFParser.REALTIME_DATA_KUBUN_VALUES
        if table_name == "RT_WF"
        else WFParser.ACCUMULATED_DATA_KUBUN_VALUES
    )
    if data_kubun not in allowed:
        raise SchemaMigrationError(
            f"WF record has unsupported DataKubun for {table_name}: {data_kubun!r}"
        )

    aliases = _STANDARD_FIELD_ALIASES.get(table_name, {})
    def value_for(native_name: str):
        if native_name in record:
            return record[native_name]
        return record.get(aliases.get(native_name, native_name))

    try:
        make_date = WFParser._require_yyyymmdd("MakeDate", value_for("MakeDate"))
        WFParser._require_event_date(value_for("Year"), value_for("MonthDay"))
        if data_kubun == "0":
            return True
        conflicts = [
            (native_name, standard_name)
            for native_name, standard_name in aliases.items()
            if native_name in record
            and standard_name in record
            and record[native_name] != record[standard_name]
        ]
        if conflicts:
            raise SchemaMigrationError(f"conflicting WF alias values: {conflicts}")
        body_names = (
            "Yobi1",
            *WFParser.RACE_INFO_FIELDS,
            "Yobi2",
            "HatubaiHyosu",
            *WFParser.YUKO_HYOSU_FIELDS,
            *WFParser.FLAG_FIELDS,
            "CarryOverStart",
            "CarryOverBalance",
        )
        # A caller-built row may carry None for a blank optional field; that is
        # the same stored NULL as the parser's "" and is not a coercion hole.
        # Payout slots stay strict text because PayoutsJson is stored verbatim.
        values = {
            name: "" if value_for(name) is None else value_for(name) for name in body_names
        }
        payouts = _wf_payout_tuples(record.get("PayoutsJson"))
        WFParser.validate_body(values, payouts, data_kubun, make_date)
    except ValueError as error:
        raise SchemaMigrationError(str(error)) from error

    if table_name in _WF_STANDARD_STORAGE_TABLES:
        split_conflicts = _wf_split_conflicts(record)
        if split_conflicts:
            raise SchemaMigrationError(
                "WF record split race fields contradict RaceInfo composites: "
                f"{split_conflicts}"
            )
    return True


def prepare_wf_standard_record(record: dict) -> tuple[str, dict, list[dict]]:
    """Build (status, JYUSYOSIKI_HEAD row, exactly 243 JYUSYOSIKI rows).

    The returned status is the validated official DataKubun; the writer
    branches on it rather than re-deriving it from the converted header.
    """
    from src.parser.wf_parser import WFParser

    validate_wf_record(record, _WF_STANDARD_HEAD_TABLE)
    source = translate_standard_field_names(
        clean_record_metadata(record), _WF_STANDARD_HEAD_TABLE
    )
    status = resolve_record_data_kubun(record)
    if status != "0":
        for index in range(1, WFParser.RACE_COUNT + 1):
            composite = str(source.get(f"RaceInfo{index}"))
            for name, start, end in _WF_RACE_SPLIT:
                source[f"{name}{index}"] = composite[start:end]
    header = convert_record_types(source, _WF_STANDARD_HEAD_TABLE)
    if any(header.get(column) in (None, "") for column in _WF_KEY_COLUMNS):
        raise SchemaMigrationError("WF header has an incomplete official key")
    if status == "0":
        return status, header, []

    payouts = _wf_payout_tuples(source.get("PayoutsJson"))
    children = []
    for index, (kumi, pay, votes) in enumerate(payouts, start=1):
        child = convert_record_types(
            {
                "Year": source.get("Year"),
                "MonthDay": source.get("MonthDay"),
                "Num": str(index),
                "Kumi": kumi,
                "PayJyushosiki": pay,
                "TekichuHyo": votes,
            },
            _WF_STANDARD_CHILD_TABLE,
        )
        if any(child.get(column) != header.get(column) for column in _WF_KEY_COLUMNS):
            raise SchemaMigrationError(f"WF payout row {index} has a mismatched parent key")
        if child.get("Num") != index:
            raise SchemaMigrationError(f"WF payout row {index} lost its ordinal")
        children.append(child)
    if len(children) != WFParser.PAYOUT_COUNT:
        raise SchemaMigrationError("WF standard storage requires exactly 243 payout rows")
    return status, header, children


def insert_wf_native_batch(
    database: BaseDatabase,
    table_name: str,
    rows: list[dict],
    *,
    commit_batch: bool,
    optimized: bool,
) -> int:
    """Write one strict native WF batch atomically without row fallback."""
    if table_name not in _WF_NATIVE_STORAGE_TABLES:
        raise SchemaMigrationError(f"Unsupported native WF storage table: {table_name}")
    if not rows:
        return 0

    try:
        if not database.is_transaction_active():
            database.begin_transaction()
        if optimized and hasattr(database, "insert_many_optimized"):
            inserted = database.insert_many_optimized(table_name, rows)
        else:
            inserted = database.insert_many(table_name, rows, use_replace=True)
        if commit_batch:
            database.commit()
        return inserted
    except Exception:
        rollback_failed_import(database, context=f"atomic WF write to {table_name}")
        raise


def insert_wf_standard_batch(
    database: BaseDatabase,
    prepared: list[tuple[str, dict, list[dict]]],
    *,
    commit_batch: bool,
    optimized: bool,
) -> tuple[int, int]:
    """Atomically replace parent plus 243 children per record in provider order.

    Status 0 deletes the children and then the parent for the exact key; every
    other status upserts the parent, deletes the previous children, and inserts
    all 243 ordinals. A failure rolls back the whole batch and propagates; the
    caller must never fall back to a parent-only insert.
    """
    if not prepared:
        return 0, 0
    from src.parser.wf_parser import WFParser

    def begin_if_owned() -> None:
        if commit_batch:
            begin = getattr(database, "begin_transaction", None)
            if begin is not None:
                begin()

    def rollback_or_invalidate() -> None:
        try:
            database.rollback()
        except Exception:
            try:
                database.invalidate_connection()
            except Exception as disconnect_error:
                logger.error(
                    "Failed to invalidate database after WF rollback failure",
                    table=_WF_STANDARD_HEAD_TABLE,
                    error=str(disconnect_error),
                )
            raise

    def upsert_header(header: dict) -> int:
        if optimized and hasattr(database, "insert_many_optimized"):
            return database.insert_many_optimized(_WF_STANDARD_HEAD_TABLE, [header])
        return database.insert_many(_WF_STANDARD_HEAD_TABLE, [header], use_replace=True)

    where = " AND ".join(f"{column} = ?" for column in _WF_KEY_COLUMNS)
    try:
        begin_if_owned()
        for status, header, children in prepared:
            key_values = tuple(header.get(column) for column in _WF_KEY_COLUMNS)
            if any(value in (None, "") for value in key_values):
                raise SchemaMigrationError("WF write has an incomplete parent key")
            if status == "0":
                database.execute(f"DELETE FROM {_WF_STANDARD_CHILD_TABLE} WHERE {where}", key_values)
                database.execute(f"DELETE FROM {_WF_STANDARD_HEAD_TABLE} WHERE {where}", key_values)
                continue
            if len(children) != WFParser.PAYOUT_COUNT:
                raise SchemaMigrationError("WF standard storage requires exactly 243 payout rows")
            if upsert_header(header) != 1:
                raise DatabaseError(f"WF header upsert failed for {_WF_STANDARD_HEAD_TABLE}")
            database.execute(f"DELETE FROM {_WF_STANDARD_CHILD_TABLE} WHERE {where}", key_values)
            inserted = database.insert_many(_WF_STANDARD_CHILD_TABLE, children, use_replace=False)
            if inserted != WFParser.PAYOUT_COUNT:
                raise DatabaseError(
                    f"WF payout child insert count mismatch for {_WF_STANDARD_CHILD_TABLE}: "
                    f"{inserted}"
                )
        if commit_batch:
            database.commit()
        return len(prepared), 0
    except Exception:
        rollback_or_invalidate()
        raise


def preflight_standard_schema_migrations(
    database: BaseDatabase,
    native_table_names: set[str],
) -> None:
    """Reject every known incompatibility before the first additive ALTER."""
    from src.database.migration import verify_table_schema
    from src.database.schema_jravan import JRAVAN_SCHEMAS

    # Alias-only layouts are not reconstructable. Resolve all known pairs before
    # touching an unrelated table so a later record cannot expose a partial
    # startup migration.
    for native_name in _LEGACY_STANDARD_PREFLIGHT_NATIVE_TABLES:
        resolve_standard_table_name(database, native_name)

    for native_name in native_table_names:
        standard_name = resolve_standard_storage_table_name(native_name)
        schema_sql = JRAVAN_SCHEMAS.get(standard_name)
        if not schema_sql or not database.table_exists(standard_name):
            continue
        verify_table_schema(
            database,
            standard_name,
            schema_sql,
            allow_missing_columns=(standard_name not in _STRICT_NONADDITIVE_STANDARD_TABLES),
            allow_primary_key_mismatch=(standard_name in _ORDERED_MASTER_STORAGE_TABLES),
        )

    for child_table in ("CHOKYO_SEISEKI", "KISYU_SEISEKI"):
        child_schema = JRAVAN_SCHEMAS.get(child_table)
        if child_schema and database.table_exists(child_table):
            verify_table_schema(
                database,
                child_table,
                child_schema,
                allow_missing_columns=True,
            )

    # WF standard storage is a strict parent/child pair. A partial pair, an old
    # keyless layout, or a child without the composite cascade foreign key must
    # stop the standard import before any unrelated additive ALTER runs.
    if database.table_exists(_WF_STANDARD_HEAD_TABLE) or database.table_exists(
        _WF_STANDARD_CHILD_TABLE
    ):
        try:
            verify_wf_coupled_tables(database)
        except SchemaMigrationError as error:
            raise SchemaMigrationError(
                "Standard-schema import stopped before any mutation because the "
                f"existing WF storage pair {_WF_STANDARD_HEAD_TABLE}/"
                f"{_WF_STANDARD_CHILD_TABLE} does not satisfy the current contract; "
                "back up and rebuild both tables (parent first) with the current "
                f"schema, then reimport RACE data: {error}"
            ) from error


def verify_hy_storage_schema(database: BaseDatabase, table_name: str) -> bool:
    """Fail closed unless HY storage has the official fields and KettoNum key."""
    if table_name not in _HY_STORAGE_TABLES:
        return False

    from src.database.migration import verify_table_schema
    from src.database.schema import SCHEMAS
    from src.database.schema_jravan import JRAVAN_SCHEMAS

    schema_sql = SCHEMAS.get(table_name) or JRAVAN_SCHEMAS.get(table_name)
    if schema_sql is None:
        raise SchemaMigrationError(f"HY storage schema is undefined: {table_name}")
    verify_table_schema(database, table_name, schema_sql)
    return True


def verify_rc_storage_schema(database: BaseDatabase, table_name: str) -> bool:
    """Fail closed unless RC storage has every field and the official key."""
    if table_name not in _RC_STORAGE_TABLES:
        return False

    from src.database.migration import verify_table_schema
    from src.database.schema import SCHEMAS
    from src.database.schema_jravan import JRAVAN_SCHEMAS

    schema_sql = SCHEMAS.get(table_name) or JRAVAN_SCHEMAS.get(table_name)
    if schema_sql is None:
        raise SchemaMigrationError(f"RC storage schema is undefined: {table_name}")
    verify_table_schema(database, table_name, schema_sql)
    return True


def apply_rc_batch(
    database: BaseDatabase,
    table_name: str,
    rows: list[dict],
    *,
    commit_batch: bool,
    optimized: bool,
) -> int:
    """Atomically apply RC upserts/deletes in provider order."""
    if table_name not in _RC_STORAGE_TABLES:
        raise SchemaMigrationError(f"Unsupported RC storage table: {table_name}")
    if not rows:
        return 0

    for row in rows:
        missing = [column for column in _RC_KEY_COLUMNS if row.get(column) in (None, "")]
        if missing:
            raise SchemaMigrationError(f"RC record has incomplete official key: {missing}")
        # The current format uses 1 for ordinary rows and 0 for deletion.
        # Before Ver.2.1.3, RC also used 2 for a non-delete row; the 2005
        # transition unified 1/2 to 1 without changing the 501-byte layout.
        if row.get("DataKubun") not in {"0", "1", "2"}:
            raise SchemaMigrationError(
                f"RC record has unsupported DataKubun: {row.get('DataKubun')!r}"
            )

    def begin_if_owned() -> None:
        if commit_batch:
            begin = getattr(database, "begin_transaction", None)
            if begin is not None:
                begin()

    def rollback_or_invalidate() -> None:
        try:
            database.rollback()
        except DatabaseError:
            try:
                database.invalidate_connection()
            except Exception as disconnect_error:
                logger.error(
                    "Failed to invalidate database after RC rollback failure",
                    table=table_name,
                    error=str(disconnect_error),
                )
            raise

    def write_upserts(upserts: list[dict]) -> None:
        if not upserts:
            return
        if optimized and hasattr(database, "insert_many_optimized"):
            database.insert_many_optimized(table_name, upserts)
        else:
            database.insert_many(table_name, upserts, use_replace=True)

    try:
        begin_if_owned()
        pending_upserts: list[dict] = []
        for row in rows:
            if row["DataKubun"] != "0":
                pending_upserts.append(row)
                continue
            write_upserts(pending_upserts)
            pending_upserts = []
            where = " AND ".join(f"{column} = ?" for column in _RC_KEY_COLUMNS)
            database.execute(
                f"DELETE FROM {table_name} WHERE {where}",
                tuple(row[column] for column in _RC_KEY_COLUMNS),
            )
        write_upserts(pending_upserts)
        if commit_batch:
            database.commit()
    except DatabaseError:
        rollback_or_invalidate()
        raise
    return len(rows)


def verify_ys_storage_schema(database: BaseDatabase, table_name: str) -> bool:
    """Fail closed unless YS storage has all three guides and its official key."""
    if table_name not in _YS_STORAGE_TABLES:
        return False

    from src.database.migration import verify_table_schema
    from src.database.schema import SCHEMAS
    from src.database.schema_jravan import JRAVAN_SCHEMAS

    schema_sql = SCHEMAS.get(table_name) or JRAVAN_SCHEMAS.get(table_name)
    if schema_sql is None:
        raise SchemaMigrationError(f"YS storage schema is undefined: {table_name}")
    verify_table_schema(database, table_name, schema_sql)
    return True


def apply_ys_batch(
    database: BaseDatabase,
    table_name: str,
    rows: list[dict],
    *,
    commit_batch: bool,
    optimized: bool,
) -> int:
    """Atomically apply YS upserts and exact-key deletes in provider order."""
    if table_name not in _YS_STORAGE_TABLES:
        raise SchemaMigrationError(f"Unsupported YS storage table: {table_name}")
    if not rows:
        return 0

    # Validate the whole logical batch before starting any mutation. A malformed
    # deletion must not commit the valid schedule rows that preceded it.
    for row in rows:
        missing = [column for column in _YS_KEY_COLUMNS if row.get(column) in (None, "")]
        if missing:
            raise SchemaMigrationError(f"YS record has incomplete official key: {missing}")
        if row.get("DataKubun") not in {"0", "1", "2", "3", "9"}:
            raise SchemaMigrationError(
                f"YS record has unsupported DataKubun: {row.get('DataKubun')!r}"
            )

    def begin_if_owned() -> None:
        if commit_batch:
            begin = getattr(database, "begin_transaction", None)
            if begin is not None:
                begin()

    def rollback_or_invalidate() -> None:
        try:
            database.rollback()
        except DatabaseError:
            try:
                database.invalidate_connection()
            except Exception as disconnect_error:
                logger.error(
                    "Failed to invalidate database after YS rollback failure",
                    table=table_name,
                    error=str(disconnect_error),
                )
            raise

    def write_upserts(upserts: list[dict]) -> None:
        if not upserts:
            return
        if optimized and hasattr(database, "insert_many_optimized"):
            database.insert_many_optimized(table_name, upserts)
        else:
            database.insert_many(table_name, upserts, use_replace=True)

    try:
        begin_if_owned()
        pending_upserts: list[dict] = []
        for row in rows:
            if row["DataKubun"] != "0":
                pending_upserts.append(row)
                continue
            write_upserts(pending_upserts)
            pending_upserts = []
            where = " AND ".join(f"{column} = ?" for column in _YS_KEY_COLUMNS)
            database.execute(
                f"DELETE FROM {table_name} WHERE {where}",
                tuple(row[column] for column in _YS_KEY_COLUMNS),
            )
        write_upserts(pending_upserts)
        if commit_batch:
            database.commit()
    except DatabaseError:
        rollback_or_invalidate()
        raise
    return len(rows)


def _tk_header_table_name(child_table_name: str) -> str | None:
    """Return the coupled TK header table for a native or standard child table."""
    return {
        "NL_TK": "NL_TK_RACE",
        "TOKU": "TOKU_RACE",
    }.get(child_table_name)


def verify_tk_coupled_tables(
    database: BaseDatabase,
    child_table_name: str,
) -> str | None:
    """Fail closed unless both normalized TK tables have their required keys."""
    header_table_name = _tk_header_table_name(child_table_name)
    if header_table_name is None:
        return None

    from src.database.migration import verify_table_schema
    from src.database.schema import SCHEMAS
    from src.database.schema_jravan import JRAVAN_SCHEMAS

    header_schema = SCHEMAS.get(header_table_name) or JRAVAN_SCHEMAS.get(header_table_name)
    child_schema = SCHEMAS.get(child_table_name) or JRAVAN_SCHEMAS.get(child_table_name)
    if not header_schema or not database.table_exists_strict(header_table_name):
        raise SchemaMigrationError(
            f"TK import requires header table {header_table_name} before mutation"
        )
    verify_table_schema(database, header_table_name, header_schema)
    if not child_schema or not database.table_exists_strict(child_table_name):
        raise SchemaMigrationError(
            f"TK import requires registered-horse table {child_table_name} before mutation"
        )
    verify_table_schema(database, child_table_name, child_schema)
    return header_table_name


def prepare_tk_coupled_record(
    database: BaseDatabase,
    record: dict,
    child_table_name: str,
    *,
    verified_header_table: str | None = None,
) -> tuple[dict, str, list[dict]] | None:
    """Validate and convert a complete TK physical snapshot before writes."""
    expected_header_table = _tk_header_table_name(child_table_name)
    if expected_header_table is None:
        return None
    header_table = verified_header_table or verify_tk_coupled_tables(
        database, child_table_name
    )
    if header_table != expected_header_table:
        raise SchemaMigrationError(
            f"TK import expected header table {expected_header_table}"
        )
    if _record_type_from_record(record) != "TK":
        raise SchemaMigrationError("TK storage received a non-TK record")

    status = record.get("DataKubun")
    if status not in {"0", "1", "2"}:
        raise SchemaMigrationError(f"TK record has unsupported DataKubun: {status!r}")
    missing_key = [column for column in _TK_KEY_COLUMNS if record.get(column) in (None, "")]
    if missing_key:
        raise SchemaMigrationError(f"TK record has incomplete official key: {missing_key}")

    try:
        expected_count = int(str(record.get("TorokuTosu")))
    except (TypeError, ValueError) as error:
        raise SchemaMigrationError("TK record has a non-numeric registration count") from error
    if not 0 <= expected_count <= 300:
        raise SchemaMigrationError(
            f"TK record registration count is outside 0..300: {expected_count}"
        )

    rows = record.get(_TK_ROWS_KEY)
    if not isinstance(rows, list):
        raise SchemaMigrationError("TK record is missing its registered-horse rows")
    if len(rows) != expected_count:
        raise SchemaMigrationError(
            "TK registered-horse row count does not match TorokuTosu: "
            f"expected={expected_count}, actual={len(rows)}"
        )

    header_fields = set(get_table_column_types(header_table))
    translated_header = translate_standard_field_names(record, header_table)
    missing_header = sorted(field for field in header_fields if field not in translated_header)
    if missing_header:
        raise SchemaMigrationError(f"TK header is missing fields: {missing_header}")
    header_record = {
        field: translated_header[field]
        for field in get_table_column_types(header_table)
    }
    converted_header = convert_record_types(header_record, header_table)
    if not DataImporter._has_complete_primary_key(header_table, converted_header):
        raise SchemaMigrationError("TK header has an incomplete normalized key")

    expected_child_fields = set(get_table_column_types(child_table_name))
    sequence_field = "Num" if child_table_name == "TOKU" else "RenbanNum"
    converted_rows: list[dict] = []
    seen_sequences: set[int] = set()
    for expected_sequence, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise SchemaMigrationError(
                f"TK registered-horse row {expected_sequence} is not a dictionary"
            )
        translated_row = translate_standard_field_names(row, child_table_name)
        if set(translated_row) != expected_child_fields:
            raise SchemaMigrationError(
                f"TK registered-horse row {expected_sequence} does not match "
                f"{child_table_name} fields"
            )
        for parent_field in ("MakeDate", *_TK_KEY_COLUMNS):
            if str(row.get(parent_field)) != str(record.get(parent_field)):
                raise SchemaMigrationError(
                    f"TK registered-horse row {expected_sequence} has an inconsistent "
                    f"parent field: {parent_field}"
                )
        try:
            sequence = int(str(translated_row.get(sequence_field)))
        except (TypeError, ValueError) as error:
            raise SchemaMigrationError(
                f"TK registered-horse row {expected_sequence} has a non-numeric sequence"
            ) from error
        if sequence != expected_sequence or sequence in seen_sequences:
            raise SchemaMigrationError(
                "TK registered-horse sequence must be unique and contiguous from 001"
            )
        seen_sequences.add(sequence)
        converted = convert_record_types(translated_row, child_table_name)
        if not DataImporter._has_complete_primary_key(child_table_name, converted):
            raise SchemaMigrationError(
                f"TK registered-horse row {expected_sequence} has an incomplete key"
            )
        converted_rows.append(converted)

    if status == "0" and (expected_count != 0 or converted_rows):
        raise SchemaMigrationError("TK delete record must not contain registered-horse rows")
    return converted_header, header_table, converted_rows


def insert_tk_coupled_batch(
    database: BaseDatabase,
    child_table_name: str,
    prepared: list[tuple[dict, str, list[dict]]],
    *,
    commit_batch: bool,
    optimized: bool,
) -> tuple[int, int]:
    """Atomically apply complete TK snapshots and deletes in provider order."""
    if not prepared:
        return 0, 0
    header_tables = {header_table for _, header_table, _ in prepared}
    if len(header_tables) != 1:
        raise SchemaMigrationError("TK batch contains inconsistent header tables")

    def begin_if_owned() -> None:
        if commit_batch:
            begin = getattr(database, "begin_transaction", None)
            if begin is not None:
                begin()

    def rollback_or_invalidate() -> None:
        try:
            database.rollback()
        except DatabaseError:
            try:
                database.invalidate_connection()
            except Exception as disconnect_error:
                logger.error(
                    "Failed to invalidate database after TK rollback failure",
                    table=child_table_name,
                    error=str(disconnect_error),
                )
            raise

    def insert_rows(table_name: str, rows: list[dict]) -> int:
        if not rows:
            return 0
        if optimized and hasattr(database, "insert_many_optimized"):
            return database.insert_many_optimized(table_name, rows)
        return database.insert_many(table_name, rows, use_replace=True)

    try:
        begin_if_owned()
        for header, header_table, child_rows in prepared:
            where = " AND ".join(f"{column} = ?" for column in _TK_KEY_COLUMNS)
            key_values = tuple(header[column] for column in _TK_KEY_COLUMNS)
            database.execute(
                f"DELETE FROM {child_table_name} WHERE {where}",
                key_values,
            )
            if header.get("DataKubun") == "0":
                database.execute(
                    f"DELETE FROM {header_table} WHERE {where}",
                    key_values,
                )
                continue
            if insert_rows(header_table, [header]) != 1:
                raise DatabaseError(f"TK header insert failed for {header_table}")
            if insert_rows(child_table_name, child_rows) != len(child_rows):
                raise DatabaseError(
                    f"TK child insert count mismatch for {child_table_name}"
                )
        if commit_batch:
            database.commit()
        return len(prepared), 0
    except DatabaseError:
        rollback_or_invalidate()
        raise


def _expanded_record_fingerprint(record: dict, table_name: str) -> Optional[tuple]:
    """Identify duplicate expanded rows that share one official wide record."""
    if table_name not in {"BATAIJYU", "MINING", "TAISENGATA_MINING"}:
        return None
    wide_record = record.get("_wide_record")
    if not isinstance(wide_record, dict):
        return None
    return tuple(sorted((str(key), repr(value)) for key, value in wide_record.items()))


_MINING_RACE_KEY_COLUMNS = ("Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum")
_DM_RACE_KEY_COLUMNS = _MINING_RACE_KEY_COLUMNS
_DM_SNAPSHOT_ROWS_KEY = "_dm_snapshot_rows"
_DM_SNAPSHOT_INDEX_KEY = "_dm_snapshot_index"
_TM_SNAPSHOT_ROWS_KEY = "_tm_snapshot_rows"
_TM_SNAPSHOT_INDEX_KEY = "_tm_snapshot_index"

_MINING_STORAGE_CONFIG: dict[str, dict[str, Any]] = {
    "DM": {
        "native_tables": {"NL_DM", "RT_DM"},
        "standard_table": "MINING",
        "snapshot_rows_key": _DM_SNAPSHOT_ROWS_KEY,
        "snapshot_index_key": _DM_SNAPSHOT_INDEX_KEY,
    },
    "TM": {
        "native_tables": {"NL_TM", "RT_TM"},
        "standard_table": "TAISENGATA_MINING",
        "snapshot_rows_key": _TM_SNAPSHOT_ROWS_KEY,
        "snapshot_index_key": _TM_SNAPSHOT_INDEX_KEY,
    },
}


def _record_type_from_record(record: dict) -> Any:
    """Resolve every record-type alias accepted by importer entry points."""
    aliases = tuple(
        (name, str(record[name]))
        for name in ("レコード種別ID", "RecordSpec", "headRecordSpec")
        if record.get(name) not in (None, "")
    )
    values = {value for _, value in aliases}
    if len(values) > 1:
        raise SchemaMigrationError(f"record-type aliases conflict: {aliases}")
    return aliases[0][1] if aliases else None


def resolve_record_type(record: dict) -> Any:
    """Resolve and consistency-check importer-supported record-type aliases."""
    return _record_type_from_record(record)


CANCELLATION_STATE_RECORD_TYPES = frozenset(
    {"RA", "SE", "HR", "H1", "H6", "O1", "O2", "O3", "O4", "O5", "O6", "WF"}
)

_OFFICIAL_ERASE_KEY_COLUMNS = {
    "RA": _MINING_RACE_KEY_COLUMNS,
    "SE": (*_MINING_RACE_KEY_COLUMNS, "Umaban"),
    "HR": _MINING_RACE_KEY_COLUMNS,
    # One physical H1/H6/O1-O6 record expands into multiple child rows.
    "H1": _MINING_RACE_KEY_COLUMNS,
    "H6": _MINING_RACE_KEY_COLUMNS,
    "O1": _MINING_RACE_KEY_COLUMNS,
    "O2": _MINING_RACE_KEY_COLUMNS,
    "O3": _MINING_RACE_KEY_COLUMNS,
    "O4": _MINING_RACE_KEY_COLUMNS,
    "O5": _MINING_RACE_KEY_COLUMNS,
    "O6": _MINING_RACE_KEY_COLUMNS,
    "WF": ("Year", "MonthDay"),
    "HY": ("KettoNum",),
    "BT": ("HansyokuNum",),
    "JG": _JG_KEY_COLUMNS,
    "WC": _WC_KEY_COLUMNS,
}

_OFFICIAL_ERASE_STORAGE_TABLES = {
    "RA": {"NL_RA", "RT_RA", "RACE"},
    "SE": {"NL_SE", "RT_SE", "UMA_RACE"},
    "HR": {"NL_HR", "RT_HR", "HARAI"},
    "H1": {"NL_H1", "RT_H1", "HYO_TANPUKU"},
    "H6": {"NL_H6", "RT_H6", "HYO_SANRENTAN"},
    "O1": {"NL_O1", "RT_O1", "ODDS_TANPUKUWAKU_HEAD"},
    "O2": {"NL_O2", "RT_O2", "ODDS_UMAREN_HEAD"},
    "O3": {"NL_O3", "RT_O3", "ODDS_WIDE_HEAD"},
    "O4": {"NL_O4", "RT_O4", "ODDS_UMATAN_HEAD"},
    "O5": {"NL_O5", "RT_O5", "ODDS_SANREN_HEAD"},
    "O6": {"NL_O6", "RT_O6", "ODDS_SANRENTAN_HEAD"},
    # Standard-mode WF erases are applied by the coupled parent/child writer in
    # provider order; WIN5 is a legacy alias and never a physical write target.
    "WF": set(_WF_NATIVE_STORAGE_TABLES),
    "HY": {"NL_HY", "BAMEIORIGIN"},
    "BT": {"NL_BT", "KEITO"},
    "JG": {"NL_JG", "JOGAIBA"},
    "WC": {"NL_WC", "WOOD"},
}

_STANDARD_ODDS_RACE_KEY_COLUMNS = _MINING_RACE_KEY_COLUMNS
_STANDARD_ODDS_CONFIG: dict[str, dict[str, Any]] = {
    "O1": {
        "owner": "ODDS_TANPUKUWAKU_HEAD",
        "children": {
            "ODDS_TANPUKU": (*_STANDARD_ODDS_RACE_KEY_COLUMNS, "Umaban"),
            "ODDS_WAKU": (*_STANDARD_ODDS_RACE_KEY_COLUMNS, "Kumi"),
        },
    },
    "O2": {
        "owner": "ODDS_UMAREN_HEAD",
        "children": {
            "ODDS_UMAREN": (*_STANDARD_ODDS_RACE_KEY_COLUMNS, "Kumi"),
        },
    },
    "O3": {
        "owner": "ODDS_WIDE_HEAD",
        "children": {
            "ODDS_WIDE": (*_STANDARD_ODDS_RACE_KEY_COLUMNS, "Kumi"),
        },
    },
    "O4": {
        "owner": "ODDS_UMATAN_HEAD",
        "children": {
            "ODDS_UMATAN": (*_STANDARD_ODDS_RACE_KEY_COLUMNS, "Kumi"),
        },
    },
    "O5": {
        "owner": "ODDS_SANREN_HEAD",
        "children": {
            "ODDS_SANREN": (*_STANDARD_ODDS_RACE_KEY_COLUMNS, "Kumi"),
        },
    },
    "O6": {
        "owner": "ODDS_SANRENTAN_HEAD",
        "children": {
            "ODDS_SANRENTAN": (*_STANDARD_ODDS_RACE_KEY_COLUMNS, "Kumi"),
        },
    },
}
_STANDARD_ODDS_CONFIG_BY_OWNER = {
    config["owner"]: (record_type, config)
    for record_type, config in _STANDARD_ODDS_CONFIG.items()
}


def resolve_record_data_kubun(record: dict) -> str:
    """Resolve current and legacy names for the same JV-Data header field."""
    current = record.get("DataKubun")
    legacy = record.get("headDataKubun")
    current = None if current in (None, "") else str(current)
    legacy = None if legacy in (None, "") else str(legacy)
    if current is not None and legacy is not None and current != legacy:
        raise ValueError(
            "record has conflicting DataKubun and headDataKubun values: "
            f"{current!r} != {legacy!r}"
        )
    return current or legacy or "1"


def clean_record_metadata(record: dict) -> dict:
    """Drop parser metadata and normalize legacy JV-Data header aliases."""
    metadata_fields = {
        "headRecordSpec",
        "レコード種別ID",
        "_raw_data",
        "_parse_errors",
        "RecordDelimiter",
        "RecordSeparator",
    }
    cleaned = {
        key: value
        for key, value in record.items()
        if key not in metadata_fields and not key.startswith("_")
    }
    record_type = _record_type_from_record(record)
    if record_type is not None:
        cleaned["RecordSpec"] = record_type
    if record.get("DataKubun") not in (None, "") or record.get("headDataKubun") not in (
        None,
        "",
    ):
        cleaned["DataKubun"] = resolve_record_data_kubun(record)
    cleaned.pop("headDataKubun", None)
    return cleaned


def _standard_odds_config(
    record: dict,
    table_name: str,
) -> tuple[str, dict[str, Any]] | None:
    """Resolve a split standard odds owner for one normalized parser row."""
    configured = _STANDARD_ODDS_CONFIG_BY_OWNER.get(table_name)
    if configured is None:
        return None
    record_type, config = configured
    if _record_type_from_record(record) != record_type:
        raise SchemaMigrationError(
            f"{table_name} received a non-{record_type} standard odds row"
        )
    return record_type, config


def _standard_odds_physical_fingerprint(
    record: dict,
    owner_table_name: str,
) -> tuple:
    """Identify all normalized rows emitted from one physical odds record."""
    configured = _standard_odds_config(record, owner_table_name)
    if configured is None:
        raise SchemaMigrationError(
            f"{owner_table_name} is not a standard odds owner table"
        )
    raw = record.get("_raw")
    if isinstance(raw, (bytes, bytearray, memoryview)):
        # Fetchers attach the same raw buffer object to every expanded row.
        # Object identity avoids re-hashing an O6 buffer thousands of times;
        # the pending rows keep it alive until the boundary is flushed.
        return owner_table_name, "raw", id(raw)
    return (
        owner_table_name,
        "header",
        _record_type_from_record(record),
        resolve_record_data_kubun(record),
        record.get("MakeDate"),
        *(record.get(column) for column in _STANDARD_ODDS_RACE_KEY_COLUMNS),
        record.get("HassoTime") or record.get("HappyoTime"),
    )


def verify_standard_odds_tables(
    database: BaseDatabase,
    owner_table_name: str,
) -> tuple[str, dict[str, Any]]:
    """Require every header/child table and add safe uniqueness indexes."""
    configured = _STANDARD_ODDS_CONFIG_BY_OWNER.get(owner_table_name)
    if configured is None:
        raise SchemaMigrationError(
            f"Unknown standard odds owner table: {owner_table_name}"
        )

    from src.database.migration import migrate_table_if_needed, verify_table_schema
    from src.database.schema_jravan import JRAVAN_SCHEMAS

    record_type, config = configured
    table_keys = {
        owner_table_name: _STANDARD_ODDS_RACE_KEY_COLUMNS,
        **config["children"],
    }
    for table_name, key_columns in table_keys.items():
        schema_sql = JRAVAN_SCHEMAS.get(table_name)
        if not schema_sql or not database.table_exists_strict(table_name):
            raise SchemaMigrationError(
                f"{record_type} standard odds import requires table {table_name}"
            )
        migrate_table_if_needed(
            database,
            table_name,
            schema_sql,
            commit=False,
        )
        verify_table_schema(database, table_name, schema_sql)
        index_name = f"jltsql_uq_{table_name.lower()}"
        columns = ", ".join(key_columns)
        try:
            database.execute(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} "
                f"ON {table_name} ({columns})"
            )
        except DatabaseError as error:
            raise SchemaMigrationError(
                f"{table_name} contains duplicate official keys; "
                "deduplicate or rebuild it before standard odds import"
            ) from error
    return record_type, config


def _standard_odds_header_source(record_type: str, record: dict) -> dict:
    """Translate normalized parser header names to VB standard-schema names."""
    source = clean_record_metadata(record)
    source["HappyoTime"] = source.get("HassoTime")
    if record_type == "O1":
        source.update(
            {
                "TansyoFlag": source.get("TanFlag"),
                "FukusyoFlag": source.get("FukuFlag"),
                "FukuChakuBaraiKey": source.get("FukuChakubaraiKey"),
                "TotalHyosuTansyo": source.get("TanVote"),
                "TotalHyosuFukusyo": source.get("FukuVote"),
                "TotalHyosuWakuren": source.get("WakurenVote"),
            }
        )
    elif record_type == "O2":
        source["TotalHyosuUmaren"] = source.get("Vote")
    elif record_type == "O3":
        source["TotalHyosuWide"] = source.get("Vote")
    elif record_type == "O4":
        source["TotalHyosuUmatan"] = source.get("Vote")
    elif record_type == "O5":
        source["SanrenFlag"] = source.get("SanrenpukuFlag")
        source["TotalHyosuSanren"] = source.get("Vote")
    elif record_type == "O6":
        source["TotalHyosuSanrentan"] = source.get("Vote")
    return source


def prepare_standard_odds_record(
    record: dict,
    owner_table_name: str,
) -> tuple[dict, str | None, dict | None]:
    """Build one standard header and at most one routed child row."""
    configured = _standard_odds_config(record, owner_table_name)
    if configured is None:
        raise SchemaMigrationError(
            f"{owner_table_name} is not a standard odds owner table"
        )
    record_type, config = configured
    source = _standard_odds_header_source(record_type, record)
    header = convert_record_types(source, owner_table_name)
    missing_header_key = [
        column
        for column in _STANDARD_ODDS_RACE_KEY_COLUMNS
        if header.get(column) in (None, "")
    ]
    if missing_header_key:
        raise SchemaMigrationError(
            f"{record_type} standard odds header has incomplete key: "
            f"{missing_header_key}"
        )

    if resolve_record_data_kubun(record) == "0":
        return header, None, None

    child_source = {
        column: source.get(column)
        for column in ("MakeDate", *_STANDARD_ODDS_RACE_KEY_COLUMNS)
    }
    child_table: str | None = None
    if record_type == "O1":
        umaban = str(source.get("Umaban") or "").strip()
        kumi = str(source.get("Kumi") or "").strip()
        if umaban.strip("0"):
            child_table = "ODDS_TANPUKU"
            child_source.update(
                {
                    "Umaban": source.get("Umaban"),
                    "TanOdds": source.get("TanOdds"),
                    "TanNinki": source.get("TanNinki"),
                    "FukuOddsLow": source.get("FukuOddsLow"),
                    "FukuOddsHigh": source.get("FukuOddsHigh"),
                    "FukuNinki": source.get("FukuNinki"),
                }
            )
        elif kumi and kumi != "00":
            child_table = "ODDS_WAKU"
            child_source.update(
                {
                    "Kumi": source.get("Kumi"),
                    "Odds": source.get("WakurenOdds"),
                    "Ninki": source.get("WakurenNinki"),
                }
            )
    else:
        kumi = str(source.get("Kumi") or "").strip()
        if kumi:
            child_table = next(iter(config["children"]))
            child_source["Kumi"] = source.get("Kumi")
            if record_type == "O3":
                child_source.update(
                    {
                        "OddsLow": source.get("OddsLow"),
                        "OddsHigh": source.get("OddsHigh"),
                        "Ninki": source.get("Ninki"),
                    }
                )
            else:
                child_source.update(
                    {
                        "Odds": source.get("Odds"),
                        "Ninki": source.get("Ninki"),
                    }
                )

    if child_table is None:
        return header, None, None
    child = convert_record_types(child_source, child_table)
    child_keys = config["children"][child_table]
    missing_child_key = [
        column for column in child_keys if child.get(column) in (None, "")
    ]
    if missing_child_key:
        raise SchemaMigrationError(
            f"{record_type} standard odds child has incomplete key: "
            f"{missing_child_key}"
        )
    return header, child_table, child


def _upsert_rows_by_official_key(
    database: BaseDatabase,
    table_name: str,
    rows: list[dict],
    key_columns: tuple[str, ...],
    *,
    preserve_existing_on_null: bool = False,
) -> int:
    """Upsert partial standard rows against an additive unique index."""
    grouped_rows: dict[tuple[str, ...], list[tuple]] = {}
    for row in rows:
        if preserve_existing_on_null:
            row = {
                column: value
                for column, value in row.items()
                if column in key_columns or value is not None
            }
        columns = tuple(row)
        grouped_rows.setdefault(columns, []).append(
            tuple(row[column] for column in columns)
        )

    total = 0
    for columns, parameter_rows in grouped_rows.items():
        placeholders = ", ".join("?" for _ in columns)
        conflict_columns = ", ".join(key_columns)
        update_columns = [column for column in columns if column not in key_columns]
        if update_columns:
            updates = ", ".join(
                f"{column} = EXCLUDED.{column}" for column in update_columns
            )
            conflict_action = f"DO UPDATE SET {updates}"
        else:
            conflict_action = "DO NOTHING"
        sql = (
            f"INSERT INTO {table_name} ({', '.join(columns)}) "
            f"VALUES ({placeholders}) ON CONFLICT ({conflict_columns}) "
            f"{conflict_action}"
        )
        database.executemany(sql, parameter_rows)
        total += len(parameter_rows)
    return total


def _rollback_coupled_snapshot(database: BaseDatabase) -> None:
    try:
        database.rollback()
    except DatabaseError:
        try:
            database.invalidate_connection()
        except Exception as invalidation_error:
            logger.error(
                "Failed to invalidate database after coupled snapshot rollback failure",
                error=str(invalidation_error),
            )
        raise


def insert_standard_odds_batch(
    database: BaseDatabase,
    owner_table_name: str,
    records: list[dict],
    *,
    commit_batch: bool,
    verification_cache: dict[str, tuple[str, dict[str, Any]]] | None = None,
) -> int:
    """Atomically materialize split standard odds headers and children."""
    if not records:
        return 0
    try:
        if commit_batch:
            database.begin_transaction()
        verified = (
            verification_cache.get(owner_table_name)
            if verification_cache is not None
            else None
        )
        if verified is None:
            verified = verify_standard_odds_tables(database, owner_table_name)
        _, config = verified
        fingerprints = {
            _standard_odds_physical_fingerprint(record, owner_table_name)
            for record in records
        }
        if len(fingerprints) != 1:
            raise SchemaMigrationError(
                "standard odds batch spans multiple physical records"
            )
        header_by_key: dict[tuple, dict] = {}
        child_by_table: dict[str, dict[tuple, dict]] = {
            table_name: {} for table_name in config["children"]
        }
        for record in records:
            header, child_table, child = prepare_standard_odds_record(
                record,
                owner_table_name,
            )
            if header.get("DataKubun") == "0":
                raise SchemaMigrationError(
                    "standard odds erase must be applied at the physical-record boundary"
                )
            header_key = tuple(
                header[column] for column in _STANDARD_ODDS_RACE_KEY_COLUMNS
            )
            existing_header = header_by_key.get(header_key)
            if existing_header is None:
                header_by_key[header_key] = header
            else:
                existing_header.update(
                    {
                        column: value
                        for column, value in header.items()
                        if value is not None
                    }
                )
            if child_table is not None and child is not None:
                child_keys = config["children"][child_table]
                child_key = tuple(child[column] for column in child_keys)
                child_by_table[child_table][child_key] = child

        if len(header_by_key) != 1:
            raise SchemaMigrationError(
                "standard odds physical record spans multiple race keys"
            )
        current_header = next(iter(header_by_key.values()))
        where = " AND ".join(
            f"{column} = ?" for column in _STANDARD_ODDS_RACE_KEY_COLUMNS
        )
        race_key_values = tuple(
            current_header[column] for column in _STANDARD_ODDS_RACE_KEY_COLUMNS
        )
        for child_table in config["children"]:
            database.execute(
                f"DELETE FROM {child_table} WHERE {where}",
                race_key_values,
            )
        _upsert_rows_by_official_key(
            database,
            owner_table_name,
            list(header_by_key.values()),
            _STANDARD_ODDS_RACE_KEY_COLUMNS,
            preserve_existing_on_null=True,
        )
        for child_table, keyed_rows in child_by_table.items():
            _upsert_rows_by_official_key(
                database,
                child_table,
                list(keyed_rows.values()),
                config["children"][child_table],
            )
        if commit_batch:
            database.commit()
            if verification_cache is not None:
                verification_cache[owner_table_name] = verified
        return len(records)
    except (DatabaseError, SchemaMigrationError):
        if verification_cache is not None:
            verification_cache.pop(owner_table_name, None)
        _rollback_coupled_snapshot(database)
        raise


def delete_standard_odds_record(
    database: BaseDatabase,
    record: dict,
    owner_table_name: str,
    *,
    commit_batch: bool,
    verification_cache: dict[str, tuple[str, dict[str, Any]]] | None = None,
) -> int:
    """Atomically erase a complete split standard odds physical record."""
    if resolve_record_data_kubun(record) != "0":
        raise SchemaMigrationError("standard odds physical erase requires DataKubun=0")
    try:
        if commit_batch:
            database.begin_transaction()
        verified = (
            verification_cache.get(owner_table_name)
            if verification_cache is not None
            else None
        )
        if verified is None:
            verified = verify_standard_odds_tables(database, owner_table_name)
        _, config = verified
        header, _, _ = prepare_standard_odds_record(record, owner_table_name)
        where = " AND ".join(
            f"{column} = ?" for column in _STANDARD_ODDS_RACE_KEY_COLUMNS
        )
        values = tuple(
            header[column] for column in _STANDARD_ODDS_RACE_KEY_COLUMNS
        )
        deleted = 0
        for table_name in (*config["children"], owner_table_name):
            deleted += max(database.execute(f"DELETE FROM {table_name} WHERE {where}", values), 0)
        if commit_batch:
            database.commit()
            if verification_cache is not None:
                verification_cache[owner_table_name] = verified
        return deleted
    except (DatabaseError, SchemaMigrationError):
        if verification_cache is not None:
            verification_cache.pop(owner_table_name, None)
        _rollback_coupled_snapshot(database)
        raise


_STANDARD_VOTE_RACE_KEY_COLUMNS = _MINING_RACE_KEY_COLUMNS
_STANDARD_VOTE_CONFIG: dict[str, dict[str, Any]] = {
    "H1": {
        "owner": "HYOSU",
        "children": {
            "HYOSU_TANPUKU": (*_STANDARD_VOTE_RACE_KEY_COLUMNS, "Umaban"),
            "HYOSU_WAKU": (*_STANDARD_VOTE_RACE_KEY_COLUMNS, "Kumi"),
            "HYOSU_UMARENWIDE": (*_STANDARD_VOTE_RACE_KEY_COLUMNS, "Kumi"),
            "HYOSU_UMATAN": (*_STANDARD_VOTE_RACE_KEY_COLUMNS, "Kumi"),
            "HYOSU_SANREN": (*_STANDARD_VOTE_RACE_KEY_COLUMNS, "Kumi"),
        },
    },
    "H6": {
        "owner": "HYOSU2",
        "children": {
            "HYOSU_SANRENTAN": (*_STANDARD_VOTE_RACE_KEY_COLUMNS, "Kumi"),
        },
    },
}
_STANDARD_VOTE_CONFIG_BY_OWNER = {
    config["owner"]: (record_type, config)
    for record_type, config in _STANDARD_VOTE_CONFIG.items()
}
_H1_TOTAL_NAMES = (
    "TanHyoTotal",
    "FukuHyoTotal",
    "WakuHyoTotal",
    "UmarenHyoTotal",
    "WideHyoTotal",
    "UmatanHyoTotal",
    "SanrenfukuHyoTotal",
    "TanHenkanHyoTotal",
    "FukuHenkanHyoTotal",
    "WakuHenkanHyoTotal",
    "UmarenHenkanHyoTotal",
    "WideHenkanHyoTotal",
    "UmatanHenkanHyoTotal",
    "SanrenfukuHenkanHyoTotal",
)


def _standard_vote_config(
    record: dict,
    table_name: str,
) -> tuple[str, dict[str, Any]] | None:
    """Resolve a split standard vote owner for one normalized parser row."""
    configured = _STANDARD_VOTE_CONFIG_BY_OWNER.get(table_name)
    if configured is None:
        return None
    record_type, config = configured
    if _record_type_from_record(record) != record_type:
        raise SchemaMigrationError(
            f"{table_name} received a non-{record_type} standard vote row"
        )
    return record_type, config


def _standard_vote_physical_fingerprint(
    record: dict,
    owner_table_name: str,
) -> tuple:
    """Identify all normalized rows emitted from one physical H1/H6 record."""
    configured = _standard_vote_config(record, owner_table_name)
    if configured is None:
        raise SchemaMigrationError(
            f"{owner_table_name} is not a standard vote owner table"
        )
    raw = record.get("_raw")
    if isinstance(raw, (bytes, bytearray, memoryview)):
        return owner_table_name, "raw", id(raw)
    physical_record_id = record.get("_physical_record_id")
    if physical_record_id not in (None, ""):
        return owner_table_name, "parser", str(physical_record_id)
    if "RecordDelimiter" in record or "RecordSeparator" in record:
        # The compatibility layouts contain one complete physical record per
        # parser row, so adjacent revisions must not be coalesced.
        return owner_table_name, "flat", id(record)
    return (
        owner_table_name,
        "header",
        _record_type_from_record(record),
        resolve_record_data_kubun(record),
        record.get("MakeDate"),
        *(record.get(column) for column in _STANDARD_VOTE_RACE_KEY_COLUMNS),
    )


def verify_standard_vote_tables(
    database: BaseDatabase,
    owner_table_name: str,
) -> tuple[str, dict[str, Any]]:
    """Require all vote header/child tables and fail closed on duplicate keys."""
    configured = _STANDARD_VOTE_CONFIG_BY_OWNER.get(owner_table_name)
    if configured is None:
        raise SchemaMigrationError(
            f"Unknown standard vote owner table: {owner_table_name}"
        )

    from src.database.migration import migrate_table_if_needed, verify_table_schema
    from src.database.schema_jravan import JRAVAN_SCHEMAS

    record_type, config = configured
    table_keys = {
        owner_table_name: _STANDARD_VOTE_RACE_KEY_COLUMNS,
        **config["children"],
    }
    for table_name, key_columns in table_keys.items():
        schema_sql = JRAVAN_SCHEMAS.get(table_name)
        if not schema_sql or not database.table_exists_strict(table_name):
            raise SchemaMigrationError(
                f"{record_type} standard vote import requires table {table_name}"
            )
        migrate_table_if_needed(database, table_name, schema_sql, commit=False)
        verify_table_schema(database, table_name, schema_sql)
        index_name = f"jltsql_uq_{table_name.lower()}"
        columns = ", ".join(key_columns)
        try:
            database.execute(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} "
                f"ON {table_name} ({columns})"
            )
        except DatabaseError as error:
            raise SchemaMigrationError(
                f"{table_name} contains duplicate official keys; "
                "deduplicate or rebuild it before standard vote import"
            ) from error
    return record_type, config


def _expand_standard_vote_flags(
    source: dict,
    field_name: str,
    count: int,
) -> None:
    if field_name not in source:
        return
    packed = str(source.get(field_name) or "")
    for index in range(count):
        source[f"{field_name}{index + 1}"] = (
            packed[index : index + 1] or None
        )


def _standard_vote_header_source(record_type: str, record: dict) -> dict:
    """Translate normalized H1/H6 header fields to standard-schema columns."""
    source = clean_record_metadata(record)
    if record_type == "H1":
        _expand_standard_vote_flags(source, "HenkanUma", 28)
        _expand_standard_vote_flags(source, "HenkanWaku", 8)
        _expand_standard_vote_flags(source, "HenkanDoWaku", 8)
        for index, field_name in enumerate(_H1_TOTAL_NAMES, start=1):
            source[f"HyoTotal{index}"] = source.get(field_name)
    else:
        source["HatubaiFlag1"] = source.get("HatubaiFlag")
        _expand_standard_vote_flags(source, "HenkanUma", 18)
        source["HyoTotal1"] = source.get("SanrentanHyoTotal")
        source["HyoTotal2"] = source.get("SanrentanHenkanHyoTotal")
    return source


def _valid_vote_combination(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and text != "TOTAL" and bool(text.strip("0"))


def prepare_standard_vote_record(
    record: dict,
    owner_table_name: str,
) -> tuple[dict, list[tuple[str, dict]]]:
    """Build one standard vote header and its routed partial child rows."""
    configured = _standard_vote_config(record, owner_table_name)
    if configured is None:
        raise SchemaMigrationError(
            f"{owner_table_name} is not a standard vote owner table"
        )
    record_type, config = configured
    source = _standard_vote_header_source(record_type, record)
    header = convert_record_types(source, owner_table_name)
    missing_header_key = [
        column
        for column in _STANDARD_VOTE_RACE_KEY_COLUMNS
        if header.get(column) in (None, "")
    ]
    if missing_header_key:
        raise SchemaMigrationError(
            f"{record_type} standard vote header has incomplete key: "
            f"{missing_header_key}"
        )
    if resolve_record_data_kubun(record) == "0":
        return header, []

    base = {
        column: source.get(column)
        for column in ("MakeDate", *_STANDARD_VOTE_RACE_KEY_COLUMNS)
    }
    child_sources: list[tuple[str, dict]] = []

    def append_child(table_name: str, key_name: str, key_value: Any, **values: Any) -> None:
        if not _valid_vote_combination(key_value):
            return
        child_sources.append(
            (table_name, {**base, key_name: key_value, **values})
        )

    if record_type == "H1":
        bet_type = source.get("BetType")
        if bet_type == "Tansyo":
            append_child(
                "HYOSU_TANPUKU",
                "Umaban",
                source.get("Kumi"),
                TanHyo=source.get("Hyo"),
                TanNinki=source.get("Ninki"),
            )
        elif bet_type == "Fukusyo":
            append_child(
                "HYOSU_TANPUKU",
                "Umaban",
                source.get("Kumi"),
                FukuHyo=source.get("Hyo"),
                FukuNinki=source.get("Ninki"),
            )
        elif bet_type == "Wakuren":
            append_child(
                "HYOSU_WAKU", "Kumi", source.get("Kumi"),
                Hyo=source.get("Hyo"), Ninki=source.get("Ninki")
            )
        elif bet_type == "Umaren":
            append_child(
                "HYOSU_UMARENWIDE", "Kumi", source.get("Kumi"),
                UmarenHyo=source.get("Hyo"), UmarenNinki=source.get("Ninki")
            )
        elif bet_type == "Wide":
            append_child(
                "HYOSU_UMARENWIDE", "Kumi", source.get("Kumi"),
                WideHyo=source.get("Hyo"), WideNinki=source.get("Ninki")
            )
        elif bet_type == "Umatan":
            append_child(
                "HYOSU_UMATAN", "Kumi", source.get("Kumi"),
                Hyo=source.get("Hyo"), Ninki=source.get("Ninki")
            )
        elif bet_type == "Sanrenpuku":
            append_child(
                "HYOSU_SANREN", "Kumi", source.get("Kumi"),
                Hyo=source.get("Hyo"), Ninki=source.get("Ninki")
            )
        elif bet_type not in (None, "", "Total"):
            raise SchemaMigrationError(
                f"H1 standard vote row has unsupported BetType: {bet_type!r}"
            )

        if bet_type in (None, ""):
            append_child(
                "HYOSU_TANPUKU", "Umaban", source.get("TanUma"),
                TanHyo=source.get("TanHyo"), TanNinki=source.get("TanNinki")
            )
            append_child(
                "HYOSU_TANPUKU", "Umaban", source.get("FukuUma"),
                FukuHyo=source.get("FukuHyo"), FukuNinki=source.get("FukuNinki")
            )
            append_child(
                "HYOSU_WAKU", "Kumi", source.get("WakuKumi"),
                Hyo=source.get("WakuHyo"), Ninki=source.get("WakuNinki")
            )
            append_child(
                "HYOSU_UMARENWIDE", "Kumi", source.get("UmarenKumi"),
                UmarenHyo=source.get("UmarenHyo"),
                UmarenNinki=source.get("UmarenNinki")
            )
            append_child(
                "HYOSU_UMARENWIDE", "Kumi", source.get("WideKumi"),
                WideHyo=source.get("WideHyo"), WideNinki=source.get("WideNinki")
            )
            append_child(
                "HYOSU_UMATAN", "Kumi", source.get("UmatanKumi"),
                Hyo=source.get("UmatanHyo"), Ninki=source.get("UmatanNinki")
            )
            append_child(
                "HYOSU_SANREN", "Kumi", source.get("SanrenfukuKumi"),
                Hyo=source.get("SanrenfukuHyo"),
                Ninki=source.get("SanrenfukuNinki")
            )
    else:
        append_child(
            "HYOSU_SANRENTAN", "Kumi", source.get("SanrentanKumi"),
            Hyo=source.get("SanrentanHyo"), Ninki=source.get("SanrentanNinki")
        )

    children: list[tuple[str, dict]] = []
    for child_table, child_source in child_sources:
        child = convert_record_types(child_source, child_table)
        child_keys = config["children"][child_table]
        missing_child_key = [
            column for column in child_keys if child.get(column) in (None, "")
        ]
        if missing_child_key:
            raise SchemaMigrationError(
                f"{record_type} standard vote child has incomplete key: "
                f"{missing_child_key}"
            )
        children.append((child_table, child))
    return header, children


def insert_standard_vote_batch(
    database: BaseDatabase,
    owner_table_name: str,
    records: list[dict],
    *,
    commit_batch: bool,
    verification_cache: dict[str, tuple[str, dict[str, Any]]] | None = None,
) -> int:
    """Atomically replace one complete H1/H6 standard-schema snapshot."""
    if not records:
        return 0
    try:
        if commit_batch:
            database.begin_transaction()
        verified = (
            verification_cache.get(owner_table_name)
            if verification_cache is not None
            else None
        )
        if verified is None:
            verified = verify_standard_vote_tables(database, owner_table_name)
        _, config = verified
        fingerprints = {
            _standard_vote_physical_fingerprint(record, owner_table_name)
            for record in records
        }
        if len(fingerprints) != 1:
            raise SchemaMigrationError(
                "standard vote batch spans multiple physical records"
            )

        header_by_key: dict[tuple, dict] = {}
        child_by_table: dict[str, dict[tuple, dict]] = {
            table_name: {} for table_name in config["children"]
        }
        for record in records:
            header, children = prepare_standard_vote_record(record, owner_table_name)
            if header.get("DataKubun") == "0":
                raise SchemaMigrationError(
                    "standard vote erase must be applied at the physical-record boundary"
                )
            header_key = tuple(
                header[column] for column in _STANDARD_VOTE_RACE_KEY_COLUMNS
            )
            existing_header = header_by_key.get(header_key)
            if existing_header is None:
                header_by_key[header_key] = header
            else:
                existing_header.update(
                    {column: value for column, value in header.items() if value is not None}
                )
            for child_table, child in children:
                child_keys = config["children"][child_table]
                child_key = tuple(child[column] for column in child_keys)
                existing_child = child_by_table[child_table].get(child_key)
                if existing_child is None:
                    child_by_table[child_table][child_key] = child
                else:
                    existing_child.update(
                        {column: value for column, value in child.items() if value is not None}
                    )

        if len(header_by_key) != 1:
            raise SchemaMigrationError(
                "standard vote physical record spans multiple race keys"
            )
        current_header = next(iter(header_by_key.values()))
        where = " AND ".join(
            f"{column} = ?" for column in _STANDARD_VOTE_RACE_KEY_COLUMNS
        )
        race_key_values = tuple(
            current_header[column] for column in _STANDARD_VOTE_RACE_KEY_COLUMNS
        )
        for child_table in config["children"]:
            database.execute(
                f"DELETE FROM {child_table} WHERE {where}", race_key_values
            )
        _upsert_rows_by_official_key(
            database,
            owner_table_name,
            list(header_by_key.values()),
            _STANDARD_VOTE_RACE_KEY_COLUMNS,
        )
        for child_table, keyed_rows in child_by_table.items():
            _upsert_rows_by_official_key(
                database,
                child_table,
                list(keyed_rows.values()),
                config["children"][child_table],
            )
        if commit_batch:
            database.commit()
            if verification_cache is not None:
                verification_cache[owner_table_name] = verified
        return len(records)
    except (DatabaseError, SchemaMigrationError):
        if verification_cache is not None:
            verification_cache.pop(owner_table_name, None)
        _rollback_coupled_snapshot(database)
        raise


def delete_standard_vote_record(
    database: BaseDatabase,
    record: dict,
    owner_table_name: str,
    *,
    commit_batch: bool,
    verification_cache: dict[str, tuple[str, dict[str, Any]]] | None = None,
) -> int:
    """Atomically erase a complete split H1/H6 standard physical record."""
    if resolve_record_data_kubun(record) != "0":
        raise SchemaMigrationError("standard vote physical erase requires DataKubun=0")
    try:
        if commit_batch:
            database.begin_transaction()
        verified = (
            verification_cache.get(owner_table_name)
            if verification_cache is not None
            else None
        )
        if verified is None:
            verified = verify_standard_vote_tables(database, owner_table_name)
        _, config = verified
        header, _ = prepare_standard_vote_record(record, owner_table_name)
        where = " AND ".join(
            f"{column} = ?" for column in _STANDARD_VOTE_RACE_KEY_COLUMNS
        )
        values = tuple(
            header[column] for column in _STANDARD_VOTE_RACE_KEY_COLUMNS
        )
        deleted = 0
        for table_name in (*config["children"], owner_table_name):
            deleted += max(
                database.execute(f"DELETE FROM {table_name} WHERE {where}", values),
                0,
            )
        if commit_batch:
            database.commit()
            if verification_cache is not None:
                verification_cache[owner_table_name] = verified
        return deleted
    except (DatabaseError, SchemaMigrationError):
        if verification_cache is not None:
            verification_cache.pop(owner_table_name, None)
        _rollback_coupled_snapshot(database)
        raise


def _is_standard_vote_record_erase(record: dict, table_name: str) -> bool:
    configured = _standard_vote_config(record, table_name)
    return configured is not None and resolve_record_data_kubun(record) == "0"


def _is_standard_odds_record_erase(record: dict, table_name: str) -> bool:
    configured = _standard_odds_config(record, table_name)
    return configured is not None and resolve_record_data_kubun(record) == "0"


def _is_official_record_erase(record: dict, table_name: str) -> bool:
    """Return whether an official physical record requests keyed erasure."""
    record_type = _record_type_from_record(record)
    return (
        record_type in _OFFICIAL_ERASE_KEY_COLUMNS
        and table_name in _OFFICIAL_ERASE_STORAGE_TABLES[record_type]
        and resolve_record_data_kubun(record) == "0"
    )


def _delete_official_record(database: BaseDatabase, record: dict, table_name: str) -> int:
    """Apply DataKubun=0 at the physical-record boundary after key validation."""
    record_type = _record_type_from_record(record)
    if not _is_official_record_erase(record, table_name):
        raise ValueError(f"{table_name} is not erase storage for record {record_type!r}")

    # Key columns are declared with native parser names; a standard-name table
    # such as JOGAIBA stores them under its own official column names.
    aliases = _STANDARD_FIELD_ALIASES.get(table_name, {})
    key_columns = tuple(
        aliases.get(column, column) for column in _OFFICIAL_ERASE_KEY_COLUMNS[record_type]
    )
    record = translate_standard_field_names(record, table_name)
    converted = convert_record_types(record, table_name)
    # Some legacy standard schemas omit type metadata for an otherwise valid
    # race key. Preserve the raw key only for those columns.
    key_values = {
        column: converted.get(column, record.get(column))
        for column in key_columns
    }
    missing = [column for column, value in key_values.items() if value in (None, "")]
    if missing:
        raise ValueError(f"{record_type} record erase has incomplete key: {missing}")

    where = " AND ".join(f"{column} = ?" for column in key_columns)
    values = tuple(key_values[column] for column in key_columns)
    return database.execute(f"DELETE FROM {table_name} WHERE {where}", values)


def _mining_storage_config(record: dict, table_name: str) -> tuple[str, dict[str, Any]] | None:
    """Return the DM/TM storage contract that owns this parsed record and table."""
    record_type = _record_type_from_record(record)
    config = _MINING_STORAGE_CONFIG.get(record_type)
    if config is None:
        return None
    if table_name not in {*config["native_tables"], config["standard_table"]}:
        return None
    return record_type, config


def _is_mining_race_delete(record: dict, table_name: str) -> bool:
    """Return whether a DM/TM record deletes one complete physical race record."""
    configured = _mining_storage_config(record, table_name)
    return configured is not None and record.get("DataKubun") == "0"


def _delete_mining_race_rows(database: BaseDatabase, record: dict, table_name: str) -> int:
    """Delete every native horse row, or one standard wide row, for a race."""
    configured = _mining_storage_config(record, table_name)
    if configured is None:
        raise ValueError(f"{table_name} is not storage for record {record.get('RecordSpec')!r}")
    record_type, _ = configured
    converted = convert_record_types(record, table_name)
    missing = [
        column
        for column in _MINING_RACE_KEY_COLUMNS
        if converted.get(column) in (None, "")
    ]
    if missing:
        raise ValueError(f"{record_type} race delete has incomplete key: {missing}")
    where = " AND ".join(f"{column} = ?" for column in _MINING_RACE_KEY_COLUMNS)
    values = tuple(converted[column] for column in _MINING_RACE_KEY_COLUMNS)
    return database.execute(f"DELETE FROM {table_name} WHERE {where}", values)


def _mining_native_snapshot_rows(record: dict, table_name: str) -> list[dict] | None:
    """Return all native rows from one official DM/TM snapshot, when available."""
    configured = _mining_storage_config(record, table_name)
    if configured is None or record.get("DataKubun") == "0":
        return None
    _, config = configured
    if table_name not in config["native_tables"]:
        return None
    rows = record.get(config["snapshot_rows_key"])
    if not isinstance(rows, list) or not rows:
        return None
    return rows


def _is_mining_snapshot_follower(record: dict, table_name: str) -> bool:
    """Skip expanded rows already represented by the leading physical snapshot."""
    configured = _mining_storage_config(record, table_name)
    if configured is None:
        return False
    _, config = configured
    rows = record.get(config["snapshot_rows_key"])
    return (
        isinstance(rows, list)
        and bool(rows)
        and record.get(config["snapshot_index_key"]) != 0
    )


def verify_mining_native_schema(
    database: BaseDatabase,
    record: dict,
    table_name: str,
) -> bool:
    """Fail closed on a legacy native TM score type before any mutation."""
    if _record_type_from_record(record) != "TM" or table_name not in {"NL_TM", "RT_TM"}:
        return False

    from src.database.migration import verify_table_schema
    from src.database.schema import SCHEMAS

    verify_table_schema(database, table_name, SCHEMAS[table_name])
    return True


def replace_mining_native_snapshot(
    database: BaseDatabase,
    record: dict,
    table_name: str,
) -> int:
    """Replace one complete native DM/TM snapshot without leaving stale horses.

    Transaction ownership remains with the caller. Every replacement row is
    validated before deletion so malformed metadata cannot erase stored data.
    """
    configured = _mining_storage_config(record, table_name)
    if configured is None:
        raise ValueError(f"{table_name} is not storage for record {record.get('RecordSpec')!r}")
    record_type, _ = configured
    snapshot_rows = _mining_native_snapshot_rows(record, table_name)
    if snapshot_rows is None:
        raise ValueError(f"{table_name} {record_type} snapshot metadata is missing")

    converted_rows = [convert_record_types(row, table_name) for row in snapshot_rows]
    primary_keys = get_table_primary_key_columns(table_name)
    if not primary_keys:
        raise SchemaMigrationError(f"{table_name} {record_type} snapshot requires a primary key")

    expected_race_key = None
    seen_primary_keys = set()
    for converted in converted_rows:
        missing = [column for column in primary_keys if converted.get(column) in (None, "")]
        if missing:
            raise ValueError(f"{record_type} snapshot row has incomplete key: {missing}")
        race_key = tuple(converted[column] for column in _MINING_RACE_KEY_COLUMNS)
        if expected_race_key is None:
            expected_race_key = race_key
        elif race_key != expected_race_key:
            raise ValueError(f"{record_type} snapshot rows span more than one race")
        primary_key = tuple(converted[column] for column in primary_keys)
        if primary_key in seen_primary_keys:
            raise ValueError(
                f"{record_type} snapshot contains duplicate primary key: {primary_key}"
            )
        seen_primary_keys.add(primary_key)

    converted_record = convert_record_types(record, table_name)
    record_race_key = tuple(
        converted_record.get(column) for column in _MINING_RACE_KEY_COLUMNS
    )
    if record_race_key != expected_race_key:
        raise ValueError(f"{record_type} snapshot metadata does not match its expanded row")

    _delete_mining_race_rows(database, record, table_name)
    inserted = database.insert_many(table_name, converted_rows, use_replace=True)
    if inserted != len(converted_rows):
        raise DatabaseError(
            f"{table_name} {record_type} snapshot inserted "
            f"{inserted} of {len(converted_rows)} rows"
        )
    return inserted


def _is_dm_race_delete(record: dict, table_name: str) -> bool:
    """Return whether a DM record instructs deletion of one complete race."""
    return _record_type_from_record(record) == "DM" and _is_mining_race_delete(record, table_name)


def _delete_dm_race_rows(database: BaseDatabase, record: dict, table_name: str) -> int:
    """Delete every native horse row, or the standard wide row, for one DM race."""
    return _delete_mining_race_rows(database, record, table_name)


def _dm_native_snapshot_rows(record: dict, table_name: str) -> list[dict] | None:
    """Return all rows from one official native DM snapshot, when available."""
    if _record_type_from_record(record) != "DM":
        return None
    return _mining_native_snapshot_rows(record, table_name)


def _is_dm_snapshot_follower(record: dict, table_name: str) -> bool:
    """Skip non-leading rows already represented by one physical DM snapshot."""
    return _record_type_from_record(record) == "DM" and _is_mining_snapshot_follower(
        record, table_name
    )


def replace_dm_native_snapshot(
    database: BaseDatabase,
    record: dict,
    table_name: str,
) -> int:
    """Replace one complete native DM race snapshot without leaving stale horses.

    Transaction ownership remains with the caller. All rows are validated before
    the race delete so malformed parser metadata cannot erase an existing snapshot.
    """
    return replace_mining_native_snapshot(database, record, table_name)


_CH_SEISEKI_ROWS_KEY = "_ch_seiseki_rows"
_PREPARED_CH_SEISEKI_ROWS_KEY = "_prepared_ch_seiseki_rows"


def _ch_result_table_name(main_table_name: str) -> str | None:
    return {
        "NL_CH": "NL_CH_SEISEKI",
        "CHOKYO": "CHOKYO_SEISEKI",
    }.get(main_table_name)


def verify_ch_coupled_table(
    database: BaseDatabase,
    main_table_name: str,
) -> str | None:
    """Verify the normalized CH result table once before preparing a batch."""
    result_table = _ch_result_table_name(main_table_name)
    if result_table is None:
        return None

    from src.database.migration import verify_table_schema
    from src.database.schema import SCHEMAS
    from src.database.schema_jravan import JRAVAN_SCHEMAS

    main_schema_sql = SCHEMAS.get(main_table_name) or JRAVAN_SCHEMAS.get(main_table_name)
    if not main_schema_sql or not database.table_exists_strict(main_table_name):
        raise SchemaMigrationError(
            f"CH import requires header table {main_table_name} before mutation"
        )
    verify_table_schema(database, main_table_name, main_schema_sql)

    result_schema_sql = SCHEMAS.get(result_table) or JRAVAN_SCHEMAS.get(result_table)
    if not result_schema_sql or not database.table_exists_strict(result_table):
        raise SchemaMigrationError(
            f"CH import requires normalized result table {result_table} before mutation"
        )
    verify_table_schema(database, result_table, result_schema_sql)
    return result_table


def prepare_ch_coupled_rows(
    database: BaseDatabase,
    record: dict,
    main_table_name: str,
    *,
    verified_result_table: str | None = None,
) -> tuple[str, list[dict]] | None:
    """Validate and convert the three normalized CH result rows before writes."""
    expected_result_table = _ch_result_table_name(main_table_name)
    if expected_result_table is None:
        return None
    result_table = verified_result_table or verify_ch_coupled_table(database, main_table_name)
    if result_table != expected_result_table:
        raise SchemaMigrationError(
            f"CH import expected normalized result table {expected_result_table}"
        )

    rows = record.get(_CH_SEISEKI_ROWS_KEY)
    if not isinstance(rows, list) or len(rows) != 3:
        raise SchemaMigrationError("CH import requires exactly three normalized result rows")

    expected_fields = set(get_table_column_types(result_table))
    expected_make_date = record.get("MakeDate")
    expected_code = record.get("ChokyosiCode")
    converted_rows = []
    for expected_number, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or set(row) != expected_fields:
            raise SchemaMigrationError(
                f"CH result row {expected_number} does not match {result_table} fields"
            )
        if (
            row.get("MakeDate") != expected_make_date
            or row.get("ChokyosiCode") != expected_code
            or str(row.get("Num")) != str(expected_number)
        ):
            raise SchemaMigrationError(
                f"CH result row {expected_number} has inconsistent parent key or sequence"
            )
        converted = convert_record_types(row, result_table)
        if not DataImporter._has_complete_primary_key(result_table, converted):
            raise SchemaMigrationError(
                f"CH result row {expected_number} has an incomplete normalized key"
            )
        converted_rows.append(converted)
    return result_table, converted_rows


def insert_ch_coupled_batch(
    database: BaseDatabase,
    main_table_name: str,
    prepared: list[tuple[dict, str, list[dict]]],
    *,
    commit_batch: bool,
    optimized: bool,
) -> tuple[int, int]:
    """Atomically write CH header/result groups and return physical-record stats."""
    if not prepared:
        return 0, 0

    result_tables = {result_table for _, result_table, _ in prepared}
    if len(result_tables) != 1:
        raise SchemaMigrationError("CH batch contains inconsistent normalized result tables")
    result_table = next(iter(result_tables))

    def begin_if_owned() -> None:
        if commit_batch:
            begin = getattr(database, "begin_transaction", None)
            if begin is not None:
                begin()

    def insert_many(table_name: str, rows: list[dict]) -> int:
        if optimized and hasattr(database, "insert_many_optimized"):
            return database.insert_many_optimized(table_name, rows)
        return database.insert_many(table_name, rows)

    def rollback_or_invalidate() -> None:
        """Rollback a coupled write or close a session that cannot roll back."""
        try:
            database.rollback()
        except DatabaseError:
            # A connection with an unconfirmed rollback must never remain
            # available for a later context-manager commit.
            try:
                database.invalidate_connection()
            except Exception as disconnect_error:
                logger.error(
                    "Failed to invalidate database after CH rollback failure",
                    table=main_table_name,
                    error=str(disconnect_error),
                )
            raise

    main_rows = [main for main, _, _ in prepared]
    result_rows = [row for _, _, rows in prepared for row in rows]
    try:
        begin_if_owned()
        insert_many(main_table_name, main_rows)
        insert_many(result_table, result_rows)
        if commit_batch:
            database.commit()
        return len(prepared), 0
    except DatabaseError:
        if not commit_batch:
            # The caller owns the commit boundary, but a coupled CH write must
            # never leave a header-only mutation available for that commit.
            rollback_or_invalidate()
            raise
        rollback_or_invalidate()

    succeeded = 0
    failed = 0
    for main_row, child_table, child_rows in prepared:
        try:
            begin_if_owned()
            database.insert(main_table_name, main_row)
            insert_many(child_table, child_rows)
            database.commit()
            succeeded += 1
        except DatabaseError as error:
            failed += 1
            rollback_or_invalidate()
            logger.error(
                "Failed to insert coupled CH record",
                table=main_table_name,
                error=str(error),
            )
    return succeeded, failed


_KS_SEISEKI_ROWS_KEY = "_ks_seiseki_rows"
_PREPARED_KS_SEISEKI_ROWS_KEY = "_prepared_ks_seiseki_rows"


def _ks_result_table_name(main_table_name: str) -> str | None:
    return {
        "NL_KS": "NL_KS_SEISEKI",
        "KISYU": "KISYU_SEISEKI",
    }.get(main_table_name)


def verify_ks_coupled_table(
    database: BaseDatabase,
    main_table_name: str,
) -> str | None:
    """Verify both keyed KS tables before any parent or child mutation."""
    result_table = _ks_result_table_name(main_table_name)
    if result_table is None:
        return None

    from src.database.migration import verify_table_schema
    from src.database.schema import SCHEMAS
    from src.database.schema_jravan import JRAVAN_SCHEMAS

    main_schema_sql = SCHEMAS.get(main_table_name) or JRAVAN_SCHEMAS.get(main_table_name)
    if not main_schema_sql or not database.table_exists_strict(main_table_name):
        raise SchemaMigrationError(
            f"KS import requires header table {main_table_name} before mutation"
        )
    verify_table_schema(database, main_table_name, main_schema_sql)

    result_schema_sql = SCHEMAS.get(result_table) or JRAVAN_SCHEMAS.get(result_table)
    if not result_schema_sql or not database.table_exists_strict(result_table):
        raise SchemaMigrationError(
            f"KS import requires normalized result table {result_table} before mutation"
        )
    verify_table_schema(database, result_table, result_schema_sql)
    return result_table


def prepare_ks_coupled_rows(
    database: BaseDatabase,
    record: dict,
    main_table_name: str,
    *,
    verified_result_table: str | None = None,
) -> tuple[str, list[dict]] | None:
    """Validate and convert all three normalized KS result rows before writes."""
    expected_result_table = _ks_result_table_name(main_table_name)
    if expected_result_table is None:
        return None
    result_table = verified_result_table or verify_ks_coupled_table(database, main_table_name)
    if result_table != expected_result_table:
        raise SchemaMigrationError(
            f"KS import expected normalized result table {expected_result_table}"
        )

    # A delete consumes only the official parent key. Child payload is ignored,
    # but both schemas were verified above so the coupled delete cannot degrade
    # into a parent-only mutation.
    if record.get("DataKubun") == "0":
        return result_table, []

    rows = record.get(_KS_SEISEKI_ROWS_KEY)
    if not isinstance(rows, list) or len(rows) != 3:
        raise SchemaMigrationError("KS import requires exactly three normalized result rows")

    expected_fields = set(get_table_column_types(result_table))
    expected_make_date = record.get("MakeDate")
    expected_code = record.get("KisyuCode")
    converted_rows = []
    for expected_number, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or set(row) != expected_fields:
            raise SchemaMigrationError(
                f"KS result row {expected_number} does not match {result_table} fields"
            )
        if (
            row.get("MakeDate") != expected_make_date
            or row.get("KisyuCode") != expected_code
            or str(row.get("Num")) != str(expected_number)
        ):
            raise SchemaMigrationError(
                f"KS result row {expected_number} has inconsistent parent key or sequence"
            )
        converted = convert_record_types(row, result_table)
        if not DataImporter._has_complete_primary_key(result_table, converted):
            raise SchemaMigrationError(
                f"KS result row {expected_number} has an incomplete normalized key"
            )
        converted_rows.append(converted)
    return result_table, converted_rows


def insert_ks_coupled_batch(
    database: BaseDatabase,
    main_table_name: str,
    prepared: list[tuple[dict, str, list[dict]]],
    *,
    commit_batch: bool,
    optimized: bool,
) -> tuple[int, int]:
    """Atomically apply ordered KS upserts/deletes and their result rows."""
    if not prepared:
        return 0, 0
    result_tables = {result_table for _, result_table, _ in prepared}
    if len(result_tables) != 1:
        raise SchemaMigrationError("KS batch contains inconsistent normalized result tables")

    def begin_if_owned() -> None:
        if commit_batch:
            begin = getattr(database, "begin_transaction", None)
            if begin is not None:
                begin()

    def insert_many(table_name: str, rows: list[dict]) -> int:
        if optimized and hasattr(database, "insert_many_optimized"):
            return database.insert_many_optimized(table_name, rows)
        return database.insert_many(table_name, rows)

    def rollback_or_invalidate() -> None:
        try:
            database.rollback()
        except DatabaseError:
            try:
                database.invalidate_connection()
            except Exception as disconnect_error:
                logger.error(
                    "Failed to invalidate database after KS rollback failure",
                    table=main_table_name,
                    error=str(disconnect_error),
                )
            raise

    def write_one(main_row: dict, result_table: str, result_rows: list[dict]) -> None:
        jockey_code = main_row.get("KisyuCode")
        if main_row.get("DataKubun") == "0":
            database.execute(f"DELETE FROM {result_table} WHERE KisyuCode = ?", (jockey_code,))
            database.execute(f"DELETE FROM {main_table_name} WHERE KisyuCode = ?", (jockey_code,))
            return
        insert_many(main_table_name, [main_row])
        insert_many(result_table, result_rows)

    try:
        begin_if_owned()
        for main_row, result_table, result_rows in prepared:
            write_one(main_row, result_table, result_rows)
        if commit_batch:
            database.commit()
        return len(prepared), 0
    except DatabaseError:
        rollback_or_invalidate()
        if not commit_batch:
            raise

    succeeded = 0
    failed = 0
    for main_row, result_table, result_rows in prepared:
        try:
            begin_if_owned()
            write_one(main_row, result_table, result_rows)
            database.commit()
            succeeded += 1
        except DatabaseError as error:
            failed += 1
            rollback_or_invalidate()
            logger.error(
                "Failed to insert coupled KS record",
                table=main_table_name,
                error=str(error),
            )
    return succeeded, failed


_CK_CHAKU_ROWS_KEY = "_ck_chaku_rows"
_CK_RUIKEI_ROWS_KEY = "_ck_ruikei_rows"
_PREPARED_CK_ROWS_KEY = "_prepared_ck_rows"
_CK_PARENT_KEY = ("Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "KettoNum")
_CK_HORSE_METRICS = (
    ("ChakuSogo", 1),
    ("ChakuChuo", 1),
    ("ChakuKaisuBa", 7),
    ("ChakuKaisuJyotai", 12),
    ("ChakuKaisuSibaKyori", 9),
    ("ChakuKaisuDirtKyori", 9),
    ("ChakuKaisuJyoSiba", 10),
    ("ChakuKaisuJyoDirt", 10),
    ("ChakuKaisuJyoSyogai", 10),
    ("Kyakusitu", 1),
)
_CK_PROFESSIONAL_METRICS = (
    ("ChakuKaisuSiba", 1),
    ("ChakuKaisuDirt", 1),
    ("ChakuKaisuSyogai", 1),
    ("ChakuKaisuSibaKyori", 9),
    ("ChakuKaisuDirtKyori", 9),
    ("ChakuKaisuJyoSiba", 10),
    ("ChakuKaisuJyoDirt", 10),
    ("ChakuKaisuJyoSyogai", 10),
)
_CK_EXPECTED_CHAKU_DIMENSIONS = (
    *(
        ("UMA", 0, metric, bucket)
        for metric, count in _CK_HORSE_METRICS
        for bucket in range(1, count + 1)
    ),
    *(
        (entity, period, metric, bucket)
        for entity in ("KISYU", "CHOKYOSI")
        for period in (1, 2)
        for metric, count in _CK_PROFESSIONAL_METRICS
        for bucket in range(1, count + 1)
    ),
    *((entity, period, "ChakuKaisu", 1) for entity in ("BANUSI", "BREEDER") for period in (1, 2)),
)
_CK_EXPECTED_RUIKEI_DIMENSIONS = tuple(
    (entity, period) for entity in ("KISYU", "CHOKYOSI", "BANUSI", "BREEDER") for period in (1, 2)
)


def _ck_child_tables(main_table_name: str) -> tuple[str, str] | None:
    if main_table_name == "NL_CK":
        return "NL_CK_CHAKU", "NL_CK_RUIKEI"
    return None


def _ck_schema_targets(database: BaseDatabase) -> tuple[BaseDatabase, ...]:
    getter = getattr(database, "get_migration_targets", None)
    if getter is None:
        return (database,)
    targets = tuple(getter())
    return targets or (database,)


def _ck_actual_column_contract(
    database: BaseDatabase,
    table_name: str,
) -> dict[str, tuple[str, bool]]:
    if database.get_db_type() == "postgresql":
        rows = database.fetch_all(
            "SELECT a.attname AS name, format_type(a.atttypid, a.atttypmod) AS type, "
            "a.attnotnull AS not_null FROM pg_attribute a "
            "WHERE a.attrelid = to_regclass(?) AND a.attnum > 0 AND NOT a.attisdropped",
            (table_name.lower(),),
        )
    else:
        rows = database.fetch_all(f'PRAGMA table_info("{table_name}")')

    def normalized_type(value: Any) -> str:
        normalized = str(value or "").lower().strip()
        return {
            "int": "integer",
            "int4": "integer",
            "integer": "integer",
            "int8": "bigint",
            "bigint": "bigint",
            "text": "text",
        }.get(normalized, normalized)

    result = {}
    for row in rows:
        not_null_value = row.get("not_null", row.get("notnull", 0))
        result[str(row["name"]).lower()] = (
            normalized_type(row.get("type")),
            bool(not_null_value),
        )
    return result


def _ck_expected_column_contract(schema_sql: str) -> dict[str, tuple[str, bool]]:
    from src.database.migration import _extract_column_definitions

    definitions = _extract_column_definitions(schema_sql)
    if definitions is None:
        raise SchemaMigrationError("CK expected child columns are unreadable")
    result = {}
    for name, definition in definitions.items():
        tokens = definition.split()
        result[name.lower()] = (tokens[1].lower(), "NOT NULL" in definition.upper())
    return result


def _ck_named_constraints(create_sql: str) -> dict[str, str]:
    import re

    from src.database.migration import _schema_body, _split_schema_items

    body = _schema_body(create_sql)
    if body is None:
        raise SchemaMigrationError("CK schema SQL has no table body")
    constraints = {}
    for item in _split_schema_items(body):
        match = re.match(r"CONSTRAINT\s+(\w+)\s+(.+)", item, re.IGNORECASE | re.DOTALL)
        if match:
            normalized = re.sub(r"[\s\"`]", "", match.group(2)).lower()
            constraints[match.group(1).lower()] = normalized
    return constraints


def _verify_ck_sqlite_constraints(
    database: BaseDatabase,
    table_name: str,
    expected_schema: str,
) -> None:
    enforcement = database.fetch_one("PRAGMA foreign_keys")
    if not enforcement or int(next(iter(enforcement.values()), 0)) != 1:
        raise SchemaMigrationError("CK child foreign-key enforcement is disabled for SQLite")

    row = database.fetch_one(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    if not row or not row.get("sql"):
        raise SchemaMigrationError(f"CK child table definition is unreadable: {table_name}")
    expected = _ck_named_constraints(expected_schema)
    actual = _ck_named_constraints(str(row["sql"]))
    if actual != expected:
        raise SchemaMigrationError(
            f"CK child constraints mismatch for {table_name}: "
            f"actual={sorted(actual)}, expected={sorted(expected)}"
        )

    foreign_keys = database.fetch_all(f'PRAGMA foreign_key_list("{table_name}")')
    ordered = sorted(foreign_keys, key=lambda item: int(item["seq"]))
    local = [str(item["from"]) for item in ordered]
    remote = [str(item["to"]) for item in ordered]
    if (
        len(ordered) != len(_CK_PARENT_KEY)
        or len({item["id"] for item in ordered}) != 1
        or [name.lower() for name in local] != [name.lower() for name in _CK_PARENT_KEY]
        or [name.lower() for name in remote] != [name.lower() for name in _CK_PARENT_KEY]
        or any(str(item["table"]).lower() != "nl_ck" for item in ordered)
        or any(str(item["on_delete"]).upper() != "CASCADE" for item in ordered)
    ):
        raise SchemaMigrationError(f"CK child foreign key mismatch for {table_name}")


def _verify_ck_postgresql_constraints(
    database: BaseDatabase,
    table_name: str,
    expected_schema: str,
) -> None:
    trigger_mode = database.fetch_one(
        "SELECT current_setting('session_replication_role') AS trigger_mode"
    )
    if not trigger_mode or str(trigger_mode.get("trigger_mode")) != "origin":
        raise SchemaMigrationError(
            "CK child foreign-key enforcement requires PostgreSQL origin trigger mode"
        )

    expected_names = set(_ck_named_constraints(expected_schema))
    rows = database.fetch_all(
        "SELECT oid AS constraint_oid, conname AS name, contype AS type, "
        "confdeltype AS delete_type, "
        "confupdtype AS update_type, confmatchtype AS match_type, "
        "condeferrable AS deferrable, condeferred AS initially_deferred, "
        "convalidated AS validated, "
        "confrelid = to_regclass('nl_ck') AS parent_matches, "
        "pg_get_expr(conbin, conrelid) AS expression "
        "FROM pg_constraint WHERE conrelid = to_regclass(?)",
        (table_name.lower(),),
    )
    by_name = {str(row["name"]).lower(): row for row in rows}
    if not expected_names <= set(by_name):
        raise SchemaMigrationError(
            f"CK child constraints missing for {table_name}: "
            f"{sorted(expected_names - set(by_name))}"
        )
    unexpected = {
        name
        for name, row in by_name.items()
        if str(row.get("type")) in {"c", "f", "u", "x"} and name not in expected_names
    }
    if unexpected:
        raise SchemaMigrationError(
            f"CK child has unexpected constraints for {table_name}: {sorted(unexpected)}"
        )

    for constraint_name in expected_names:
        row = by_name[constraint_name]
        if not bool(row.get("validated")):
            raise SchemaMigrationError(
                f"CK child constraint is not validated for {table_name}.{constraint_name}"
            )
        if constraint_name.endswith("parent_fk"):
            if (
                str(row.get("type")) != "f"
                or str(row.get("delete_type")) != "c"
                or str(row.get("update_type")) != "a"
                or str(row.get("match_type")) != "s"
                or bool(row.get("deferrable"))
                or bool(row.get("initially_deferred"))
                or not bool(row.get("parent_matches"))
            ):
                raise SchemaMigrationError(
                    f"CK child foreign key metadata mismatch for {table_name}"
                )
            key_rows = database.fetch_all(
                "SELECT local_column.attname AS local_name, "
                "remote_column.attname AS remote_name "
                "FROM pg_constraint constraint_row "
                "JOIN LATERAL generate_subscripts(constraint_row.conkey, 1) "
                "AS key_position(position) ON TRUE "
                "JOIN pg_attribute local_column "
                "ON local_column.attrelid = constraint_row.conrelid "
                "AND local_column.attnum = constraint_row.conkey[key_position.position] "
                "JOIN pg_attribute remote_column "
                "ON remote_column.attrelid = constraint_row.confrelid "
                "AND remote_column.attnum = constraint_row.confkey[key_position.position] "
                "WHERE constraint_row.conrelid = to_regclass(?) "
                "AND constraint_row.conname = ? ORDER BY key_position.position",
                (table_name.lower(), constraint_name),
            )
            local_names = [str(key_row["local_name"]).lower() for key_row in key_rows]
            remote_names = [str(key_row["remote_name"]).lower() for key_row in key_rows]
            if local_names != [name.lower() for name in _CK_PARENT_KEY] or remote_names != [
                name.lower() for name in _CK_PARENT_KEY
            ]:
                raise SchemaMigrationError(
                    f"CK child foreign key columns mismatch for {table_name}"
                )
            trigger_rows = database.fetch_all(
                "SELECT tgenabled AS enabled, tgrelid = to_regclass(?) AS on_child, "
                "tgrelid = to_regclass('nl_ck') AS on_parent "
                "FROM pg_trigger WHERE tgconstraint = ? AND tgisinternal ORDER BY oid",
                (table_name.lower(), int(row["constraint_oid"])),
            )
            if (
                len(trigger_rows) != 4
                or any(str(trigger["enabled"]) != "O" for trigger in trigger_rows)
                or sum(bool(trigger["on_child"]) for trigger in trigger_rows) != 2
                or sum(bool(trigger["on_parent"]) for trigger in trigger_rows) != 2
            ):
                raise SchemaMigrationError(
                    f"CK child foreign-key triggers are not active for {table_name}"
                )
            continue

        if str(row.get("type")) != "c" or not row.get("expression"):
            raise SchemaMigrationError(
                f"CK child CHECK metadata mismatch for {table_name}.{constraint_name}"
            )
        _verify_ck_postgresql_check_truth_table(
            database,
            table_name,
            constraint_name,
            str(row["expression"]),
        )


def _ck_postgresql_check_cases(
    constraint_name: str,
) -> tuple[tuple[tuple[str, str], ...], list[tuple[tuple[Any, ...], bool]]]:
    if constraint_name == "ck_chaku_domain":
        columns = (
            ("EntityKubun", "TEXT"),
            ("PeriodNum", "INTEGER"),
            ("MetricKubun", "TEXT"),
            ("BucketNum", "INTEGER"),
        )
        horse_maximum = dict(_CK_HORSE_METRICS)
        professional_maximum = dict(_CK_PROFESSIONAL_METRICS)
        metrics = tuple(
            dict.fromkeys((*horse_maximum, *professional_maximum, "ChakuKaisu", "INVALID"))
        )
        buckets = (0, 1, 2, 7, 8, 9, 10, 11, 12, 13)
        cases = []
        for entity in (
            "UMA",
            "KISYU",
            "CHOKYOSI",
            "BANUSI",
            "BREEDER",
            "INVALID",
            "chokyosi",
        ):
            for period in (0, 1, 2, 3):
                for metric in metrics:
                    for bucket in buckets:
                        accepted = (
                            entity == "UMA"
                            and period == 0
                            and metric in horse_maximum
                            and 1 <= bucket <= horse_maximum[metric]
                        ) or (
                            entity in {"KISYU", "CHOKYOSI"}
                            and period in {1, 2}
                            and metric in professional_maximum
                            and 1 <= bucket <= professional_maximum[metric]
                        ) or (
                            entity in {"BANUSI", "BREEDER"}
                            and period in {1, 2}
                            and metric == "ChakuKaisu"
                            and bucket == 1
                        )
                        cases.append(((entity, period, metric, bucket), accepted))
        return columns, cases

    if constraint_name == "ck_chaku_count_shape":
        columns = (
            ("EntityKubun", "TEXT"),
            ("MetricKubun", "TEXT"),
            ("Count5", "INTEGER"),
            ("Count6", "INTEGER"),
        )
        cases = []
        for entity in ("UMA", "OTHER"):
            for metric in ("Kyakusitu", "OTHER"):
                for count5 in (None, 1):
                    for count6 in (None, 1):
                        running_style = entity == "UMA" and metric == "Kyakusitu"
                        accepted = (
                            running_style and count5 is None and count6 is None
                        ) or (not running_style and count5 is not None and count6 is not None)
                        cases.append(((entity, metric, count5, count6), accepted))
        return columns, cases

    if constraint_name == "ck_ruikei_shape":
        columns = (
            ("EntityKubun", "TEXT"),
            ("PeriodNum", "INTEGER"),
            ("HonSyokinHeichi", "BIGINT"),
            ("HonSyokinSyogai", "BIGINT"),
            ("FukaSyokinHeichi", "BIGINT"),
            ("FukaSyokinSyogai", "BIGINT"),
            ("HonSyokinTotal", "BIGINT"),
            ("FukaSyokin", "BIGINT"),
        )
        from itertools import product

        cases = []
        for entity in (
            "KISYU",
            "CHOKYOSI",
            "BANUSI",
            "BREEDER",
            "INVALID",
            "chokyosi",
        ):
            for period in (0, 1, 2):
                for values in product((None, 1), repeat=6):
                    professional_shape = all(value is not None for value in values[:4]) and all(
                        value is None for value in values[4:]
                    )
                    owner_shape = all(value is None for value in values[:4]) and all(
                        value is not None for value in values[4:]
                    )
                    accepted = period in {1, 2} and (
                        (entity in {"KISYU", "CHOKYOSI"} and professional_shape)
                        or (entity in {"BANUSI", "BREEDER"} and owner_shape)
                    )
                    cases.append(((entity, period, *values), accepted))
        return columns, cases

    raise SchemaMigrationError(f"Unknown CK PostgreSQL CHECK constraint: {constraint_name}")


def _ck_postgresql_expected_check_signature(
    constraint_name: str,
) -> tuple[dict[str, int], dict[str, int]]:
    from collections import Counter

    atoms: Counter[str] = Counter()
    operators: Counter[str] = Counter()

    def equality(column: str, value: Any) -> None:
        atoms[f"eq:{column.lower()}:{value}"] += 1

    def any_of(column: str, values: tuple[Any, ...]) -> None:
        normalized = ",".join(str(value) for value in values)
        atoms[f"any:{column.lower()}:{normalized}"] += 1

    def metric_family(metrics: tuple[tuple[str, int], ...]) -> None:
        for metric, maximum in metrics:
            equality("MetricKubun", metric)
            atoms["ge:bucketnum:1"] += 1
            atoms[f"le:bucketnum:{maximum}"] += 1
            operators["and"] += 2
        operators["or"] += len(metrics) - 1

    if constraint_name == "ck_chaku_domain":
        equality("EntityKubun", "UMA")
        equality("PeriodNum", 0)
        metric_family(_CK_HORSE_METRICS)
        operators["and"] += 2

        any_of("EntityKubun", ("KISYU", "CHOKYOSI"))
        any_of("PeriodNum", (1, 2))
        metric_family(_CK_PROFESSIONAL_METRICS)
        operators["and"] += 2

        any_of("EntityKubun", ("BANUSI", "BREEDER"))
        any_of("PeriodNum", (1, 2))
        equality("MetricKubun", "ChakuKaisu")
        equality("BucketNum", 1)
        operators["and"] += 3
        operators["or"] += 2
        return dict(atoms), dict(operators)

    if constraint_name == "ck_chaku_count_shape":
        equality("EntityKubun", "UMA")
        equality("MetricKubun", "Kyakusitu")
        atoms["null:count5"] += 1
        atoms["null:count6"] += 1
        equality("EntityKubun", "UMA")
        equality("MetricKubun", "Kyakusitu")
        atoms["notnull:count5"] += 1
        atoms["notnull:count6"] += 1
        operators.update({"and": 6, "or": 1, "not": 1})
        return dict(atoms), dict(operators)

    if constraint_name == "ck_ruikei_shape":
        for entities, required, forbidden in (
            (
                ("KISYU", "CHOKYOSI"),
                (
                    "HonSyokinHeichi",
                    "HonSyokinSyogai",
                    "FukaSyokinHeichi",
                    "FukaSyokinSyogai",
                ),
                ("HonSyokinTotal", "FukaSyokin"),
            ),
            (
                ("BANUSI", "BREEDER"),
                ("HonSyokinTotal", "FukaSyokin"),
                (
                    "HonSyokinHeichi",
                    "HonSyokinSyogai",
                    "FukaSyokinHeichi",
                    "FukaSyokinSyogai",
                ),
            ),
        ):
            any_of("EntityKubun", entities)
            any_of("PeriodNum", (1, 2))
            for column in required:
                atoms[f"notnull:{column.lower()}"] += 1
            for column in forbidden:
                atoms[f"null:{column.lower()}"] += 1
            operators["and"] += 7
        operators["or"] += 1
        return dict(atoms), dict(operators)

    raise SchemaMigrationError(f"Unknown CK PostgreSQL CHECK constraint: {constraint_name}")


def _ck_postgresql_check_signature(
    expression: str,
) -> tuple[dict[str, int], dict[str, int]]:
    import re
    from collections import Counter

    atoms: Counter[str] = Counter()
    working = expression

    def replace_any(match: Any) -> str:
        column = match.group(1).lower()
        raw_values = match.group(2)
        values = []
        for raw_value in raw_values.split(","):
            item = raw_value.strip()
            string_match = re.fullmatch(
                r"'([^']*)'(?:\s*::\s*text)?",
                item,
                flags=re.IGNORECASE,
            )
            number_match = re.fullmatch(r"-?\d+", item)
            if string_match:
                values.append(string_match.group(1))
            elif number_match:
                values.append(number_match.group(0))
            else:
                raise SchemaMigrationError(
                    "CK PostgreSQL CHECK array contains a non-literal value"
                )
        atoms[f"any:{column}:{','.join(values)}"] += 1
        return " atom "

    working = re.sub(
        r"\b([a-z_][a-z0-9_]*)\s*=\s*any\s*\(\s*array\[(.*?)\]\s*\)",
        replace_any,
        working,
        flags=re.DOTALL | re.IGNORECASE,
    )

    def replace_null(match: Any) -> str:
        column = match.group(1).lower()
        qualifier = "notnull" if match.group(2) else "null"
        atoms[f"{qualifier}:{column}"] += 1
        return " atom "

    working = re.sub(
        r"\b([a-z_][a-z0-9_]*)\s+is\s+(not\s+)?null\b",
        replace_null,
        working,
        flags=re.IGNORECASE,
    )

    def replace_text_equality(match: Any) -> str:
        atoms[f"eq:{match.group(1).lower()}:{match.group(2)}"] += 1
        return " atom "

    working = re.sub(
        r"\b([a-z_][a-z0-9_]*)\s*=\s*'([^']*)'(?:\s*::\s*text)?",
        replace_text_equality,
        working,
        flags=re.IGNORECASE,
    )

    def replace_numeric(match: Any) -> str:
        operator = {"=": "eq", ">=": "ge", "<=": "le"}[match.group(2)]
        atoms[f"{operator}:{match.group(1).lower()}:{match.group(3)}"] += 1
        return " atom "

    working = re.sub(
        r"\b([a-z_][a-z0-9_]*)\s*(>=|<=|=)\s*(-?\d+)\b",
        replace_numeric,
        working,
        flags=re.IGNORECASE,
    )
    remaining_words = re.findall(
        r"[a-z_][a-z0-9_]*|>=|<=|=|-?\d+|'[^']*'|::",
        working.lower(),
    )
    operators: Counter[str] = Counter(
        word for word in remaining_words if word in {"and", "or", "not"}
    )
    unrecognized = [
        word for word in remaining_words if word not in {"atom", "and", "or", "not"}
    ]
    if unrecognized:
        raise SchemaMigrationError(
            f"CK PostgreSQL CHECK contains unrecognized structure: {unrecognized[:5]}"
        )
    return dict(atoms), dict(operators)


def _verify_ck_postgresql_check_truth_table(
    database: BaseDatabase,
    table_name: str,
    constraint_name: str,
    expression: str,
) -> None:
    actual_signature = _ck_postgresql_check_signature(expression)
    expected_signature = _ck_postgresql_expected_check_signature(constraint_name)
    if actual_signature != expected_signature:
        raise SchemaMigrationError(
            f"CK child CHECK structure mismatch for {table_name}.{constraint_name}"
        )

    columns, cases = _ck_postgresql_check_cases(constraint_name)
    value_rows = []
    parameters: list[Any] = []
    for case_number, (values, _) in enumerate(cases):
        casts = ["CAST(? AS INTEGER)"]
        parameters.append(case_number)
        for value, (_, sql_type) in zip(values, columns, strict=True):
            casts.append(f"CAST(? AS {sql_type})")
            parameters.append(value)
        value_rows.append(f"({', '.join(casts)})")
    aliases = ", ".join(("case_number", *(name.lower() for name, _ in columns)))
    rows = database.fetch_all(
        "SELECT case_number, COALESCE(("
        + expression
        + "), FALSE) AS accepted FROM (VALUES "
        + ", ".join(value_rows)
        + f") AS ck_probe({aliases}) ORDER BY case_number",
        tuple(parameters),
    )
    actual = {int(row["case_number"]): bool(row["accepted"]) for row in rows}
    expected = {case_number: accepted for case_number, (_, accepted) in enumerate(cases)}
    if actual != expected:
        mismatches = [
            case_number
            for case_number, accepted in expected.items()
            if actual.get(case_number) != accepted
        ]
        raise SchemaMigrationError(
            f"CK child CHECK behavior mismatch for {table_name}.{constraint_name}: "
            f"cases={mismatches[:5]}"
        )


def _verify_ck_child_on_target(
    target: BaseDatabase,
    main_table_name: str,
    table_name: str,
) -> None:
    from src.database.migration import verify_table_schema
    from src.database.schema import SCHEMAS

    for required_table in (main_table_name, table_name):
        if not target.table_exists_strict(required_table):
            raise SchemaMigrationError(
                f"CK import requires table {required_table} before mutation"
            )
        verify_table_schema(target, required_table, SCHEMAS[required_table])

    schema_sql = SCHEMAS[table_name]
    actual = _ck_actual_column_contract(target, table_name)
    expected = _ck_expected_column_contract(schema_sql)
    if actual != expected:
        raise SchemaMigrationError(
            f"CK child columns/types/nullability must match exactly for {table_name}"
        )
    if target.get_db_type() == "sqlite":
        _verify_ck_sqlite_constraints(target, table_name, schema_sql)
    elif target.get_db_type() == "postgresql":
        _verify_ck_postgresql_constraints(target, table_name, schema_sql)


def verify_ck_child_table(
    database: BaseDatabase,
    table_name: str,
) -> None:
    """Verify one CK child without requiring its not-yet-created sibling."""
    if table_name not in {"NL_CK_CHAKU", "NL_CK_RUIKEI"}:
        raise SchemaMigrationError(f"Unknown CK child table: {table_name}")
    for target in _ck_schema_targets(database):
        _verify_ck_child_on_target(target, "NL_CK", table_name)


def verify_ck_coupled_tables(
    database: BaseDatabase,
    main_table_name: str,
) -> tuple[str, str] | None:
    """Verify the complete CK parent/child contract before any mutation."""
    child_tables = _ck_child_tables(main_table_name)
    if child_tables is None:
        return None

    for target in _ck_schema_targets(database):
        for table_name in child_tables:
            _verify_ck_child_on_target(target, main_table_name, table_name)
    return child_tables


def prepare_ck_coupled_rows(
    database: BaseDatabase,
    record: dict,
    main_table_name: str,
    main_row: dict,
    *,
    verified_child_tables: tuple[str, str] | None = None,
) -> tuple[str, list[dict], str, list[dict]] | None:
    """Validate all CK dimensions, keys, and values before a write begins."""
    expected_tables = _ck_child_tables(main_table_name)
    if expected_tables is None:
        return None
    child_tables = verified_child_tables or verify_ck_coupled_tables(database, main_table_name)
    if child_tables != expected_tables:
        raise SchemaMigrationError("CK normalized child-table resolution is inconsistent")
    chaku_table, ruikei_table = child_tables

    if "CKStorageVersion" in record:
        raise SchemaMigrationError("CKStorageVersion is importer-owned metadata")
    data_kubun = resolve_record_data_kubun(record)
    chaku_rows = record.get(_CK_CHAKU_ROWS_KEY)
    ruikei_rows = record.get(_CK_RUIKEI_ROWS_KEY)
    if data_kubun == "0":
        if chaku_rows != [] or ruikei_rows != []:
            raise SchemaMigrationError("CK delete record must not carry normalized child rows")
        return chaku_table, [], ruikei_table, []
    if data_kubun not in {"1", "2"}:
        raise SchemaMigrationError(f"CK import does not support DataKubun={data_kubun!r}")
    if not isinstance(chaku_rows, list) or not isinstance(ruikei_rows, list):
        raise SchemaMigrationError("CK import requires both normalized child row lists")

    expected_chaku_fields = set(get_table_column_types(chaku_table))
    expected_ruikei_fields = set(get_table_column_types(ruikei_table))
    converted_chaku = []
    converted_ruikei = []
    dimensions = []
    for number, row in enumerate(chaku_rows, start=1):
        if not isinstance(row, dict) or set(row) != expected_chaku_fields:
            raise SchemaMigrationError(f"CK count row {number} does not match {chaku_table}")
        converted = convert_record_types(row, chaku_table)
        if any(converted.get(key) != main_row.get(key) for key in _CK_PARENT_KEY):
            raise SchemaMigrationError(f"CK count row {number} has a mismatched parent key")
        dimension = (
            converted.get("EntityKubun"),
            converted.get("PeriodNum"),
            converted.get("MetricKubun"),
            converted.get("BucketNum"),
        )
        dimensions.append(dimension)
        last_rank = 4 if dimension[0] == "UMA" and dimension[2] == "Kyakusitu" else 6
        if any(converted.get(f"Count{rank}") is None for rank in range(1, last_rank + 1)):
            raise SchemaMigrationError(f"CK count row {number} has a missing official value")
        if last_rank == 4 and any(converted.get(f"Count{rank}") is not None for rank in (5, 6)):
            raise SchemaMigrationError("CK running-style row must contain exactly four values")
        converted_chaku.append(converted)
    if tuple(dimensions) != _CK_EXPECTED_CHAKU_DIMENSIONS:
        raise SchemaMigrationError("CK count dimensions are missing, duplicated, or out of order")

    summary_dimensions = []
    for number, row in enumerate(ruikei_rows, start=1):
        if not isinstance(row, dict) or set(row) != expected_ruikei_fields:
            raise SchemaMigrationError(f"CK summary row {number} does not match {ruikei_table}")
        converted = convert_record_types(row, ruikei_table)
        if any(converted.get(key) != main_row.get(key) for key in _CK_PARENT_KEY):
            raise SchemaMigrationError(f"CK summary row {number} has a mismatched parent key")
        summary_dimensions.append((converted.get("EntityKubun"), converted.get("PeriodNum")))
        required = (
            (
                "SetYear",
                "HonSyokinHeichi",
                "HonSyokinSyogai",
                "FukaSyokinHeichi",
                "FukaSyokinSyogai",
            )
            if converted.get("EntityKubun") in {"KISYU", "CHOKYOSI"}
            else ("SetYear", "HonSyokinTotal", "FukaSyokin")
        )
        if any(converted.get(name) is None for name in required):
            raise SchemaMigrationError(f"CK summary row {number} has a missing official value")
        converted_ruikei.append(converted)
    if tuple(summary_dimensions) != _CK_EXPECTED_RUIKEI_DIMENSIONS:
        raise SchemaMigrationError("CK summary dimensions are missing, duplicated, or out of order")

    main_row["CKStorageVersion"] = 1
    return chaku_table, converted_chaku, ruikei_table, converted_ruikei


def insert_ck_coupled_batch(
    database: BaseDatabase,
    main_table_name: str,
    prepared: list[tuple[dict, str, list[dict], str, list[dict]]],
    *,
    commit_batch: bool,
    optimized: bool,
) -> tuple[int, int]:
    """Apply complete CK records in provider order under one transaction."""
    if not prepared:
        return 0, 0

    def begin_if_owned() -> None:
        if commit_batch:
            database.begin_transaction()

    def insert_many(table_name: str, rows: list[dict]) -> int:
        if optimized and hasattr(database, "insert_many_optimized"):
            return database.insert_many_optimized(table_name, rows)
        return database.insert_many(table_name, rows)

    def rollback_or_invalidate() -> None:
        try:
            database.rollback()
        except DatabaseError:
            try:
                database.invalidate_connection()
            except Exception as disconnect_error:
                logger.error(
                    "Failed to invalidate database after CK rollback failure",
                    table=main_table_name,
                    error=str(disconnect_error),
                )
            raise

    def write_one(
        main_row: dict,
        chaku_table: str,
        chaku_rows: list[dict],
        ruikei_table: str,
        ruikei_rows: list[dict],
    ) -> None:
        where = " AND ".join(f"{column} = ?" for column in _CK_PARENT_KEY)
        values = tuple(main_row.get(column) for column in _CK_PARENT_KEY)
        if any(value in (None, "") for value in values):
            raise SchemaMigrationError("CK write has an incomplete parent key")
        if main_row.get("DataKubun") == "0":
            database.execute(f"DELETE FROM {chaku_table} WHERE {where}", values)
            database.execute(f"DELETE FROM {ruikei_table} WHERE {where}", values)
            database.execute(f"DELETE FROM {main_table_name} WHERE {where}", values)
            return

        incomplete = dict(main_row)
        incomplete["CKStorageVersion"] = None
        insert_many(main_table_name, [incomplete])
        database.execute(f"DELETE FROM {chaku_table} WHERE {where}", values)
        database.execute(f"DELETE FROM {ruikei_table} WHERE {where}", values)
        insert_many(chaku_table, chaku_rows)
        insert_many(ruikei_table, ruikei_rows)
        database.execute(
            f"UPDATE {main_table_name} SET CKStorageVersion = ? WHERE {where}",
            (1, *values),
        )

    def write_all(items: list[tuple[dict, str, list[dict], str, list[dict]]]) -> None:
        for item in items:
            write_one(*item)

    try:
        begin_if_owned()
        write_all(prepared)
        if commit_batch:
            database.commit()
        return len(prepared), 0
    except DatabaseError:
        rollback_or_invalidate()
        if not commit_batch:
            raise

    succeeded = 0
    failed = 0
    for item in prepared:
        try:
            begin_if_owned()
            write_one(*item)
            database.commit()
            succeeded += 1
        except DatabaseError as error:
            failed += 1
            rollback_or_invalidate()
            logger.error(
                "Failed to insert coupled CK record",
                table=main_table_name,
                error=str(error),
            )
    return succeeded, failed


# ============================================================================
# REAL型フィールドの変換ルール定義
# JV-Dataでは一部の数値フィールドが10倍された状態で格納されている
# ============================================================================

# 10で割るべきフィールド名のプレフィックス（高速ルックアップ用）
# オッズ系、タイム系、重量系
DIVIDE_BY_10_PREFIXES = frozenset(
    [
        "TanOdds",
        "FukuOdds",
        "WakurenOdds",
        "OddsLow",
        "OddsHigh",
        "TimeDiff",
        "HaronTime",
        "Haron",
        "LapTime",
        "Futan",
        "BaTaijyu",
        "ZogenSa",
        "DMTime",
        "DMGosa",
    ]
)

# 完全一致で10で割るべきフィールド名
DIVIDE_BY_10_EXACT = frozenset(["Odds", "SyogaiMileTime", "Time"])

# Explicit-unit fields are already canonicalized by the parser contract.
CANONICAL_SE_FIELDS = frozenset(
    [
        "FutanKg",
        "FutanBeforeKg",
        "BaTaijyuKg",
        "ZogenSaKg",
        "RaceTimeSeconds",
        "OddsMultiplier",
        "HonsyokinYen",
        "FukasyokinYen",
        "HaronTimeL4Seconds",
        "HaronTimeL3Seconds",
        "TimeDiffSeconds",
        "DMTimeSeconds",
        "DMGosaPSeconds",
        "DMGosaMSeconds",
    ]
)

# RA corner-order fields use three leading spaces as a provider-defined marker
# for horses that did not pass the corner. Only right-side record padding may
# be removed from these fields.
LEADING_SPACE_SIGNIFICANT_FIELDS = frozenset(
    [
        "Jyuni1",
        "Jyuni2",
        "Jyuni3",
        "Jyuni4",
        "TsukaJyuni",
        "TsukaJyuni2",
        "TsukaJyuni3",
        "TsukaJyuni4",
    ]
)

# キャッシュ（フィールド名 → 10で割るべきか）
_divide_cache: dict = {}


def _should_divide_by_10(field_name: str) -> bool:
    """フィールドが10で割る必要があるかチェック（キャッシュ付き）"""
    if field_name in CANONICAL_SE_FIELDS:
        return False
    # キャッシュから取得
    result = _divide_cache.get(field_name)
    if result is not None:
        return result

    # 完全一致チェック
    if field_name in DIVIDE_BY_10_EXACT:
        _divide_cache[field_name] = True
        return True

    # プレフィックスチェック
    for prefix in DIVIDE_BY_10_PREFIXES:
        if field_name.startswith(prefix):
            _divide_cache[field_name] = True
            return True

    _divide_cache[field_name] = False
    return False


def _should_not_divide(field_name: str) -> bool:
    """フィールドがそのまま使うべきかチェック（使用されていないが互換性のため残す）"""
    return False


def convert_record_types(record: dict, table_name: str) -> dict:
    """Convert record field types based on table schema.

    Module-level helper used by DataImporter and RealtimeUpdater so that all
    write paths (NL_*, RT_*, TS_O*) apply identical numeric/text coercion.
    Handles JV-Data sentinel values like "***", "----", "0103*****" by
    mapping them to None for INTEGER/BIGINT/REAL columns. Fields not present
    in the target schema are dropped so parser metadata never reaches INSERT.
    """
    column_types = get_table_column_types(table_name)
    if not column_types:
        return record

    converted = {}

    for field_name, value in record.items():
        if field_name not in column_types:
            continue

        col_type = column_types[field_name]

        if value is None or (isinstance(value, str) and not value.strip()):
            converted[field_name] = None
            continue

        try:
            if col_type in ("INTEGER", "BIGINT"):
                str_value = str(value).strip()
                if str_value:
                    if (
                        str_value.startswith("***")
                        or "****" in str_value
                        or all(c in "-*" for c in str_value)
                        or "--" in str_value
                        or "*" in str_value
                    ):
                        converted[field_name] = None
                    else:
                        numeric_part = "".join(c for c in str_value if c.isdigit() or c == "-")
                        if numeric_part and numeric_part != "-":
                            converted[field_name] = int(numeric_part)
                        else:
                            converted[field_name] = None
                else:
                    converted[field_name] = None

            elif col_type == "REAL":
                str_value = str(value).strip()
                if str_value:
                    if (
                        str_value.startswith("***")
                        or "****" in str_value
                        or all(c in "-*" for c in str_value)
                        or "--" in str_value
                        or "*" in str_value
                    ):
                        converted[field_name] = None
                    else:
                        numeric_part = "".join(c for c in str_value if c.isdigit() or c in ".-")
                        if numeric_part and numeric_part not in ("-", ".", "-."):
                            float_value = float(numeric_part)
                            if _should_divide_by_10(field_name):
                                converted[field_name] = float_value / 10.0
                            else:
                                converted[field_name] = float_value
                        else:
                            converted[field_name] = None
                else:
                    converted[field_name] = None

            else:
                if isinstance(value, str):
                    if field_name in LEADING_SPACE_SIGNIFICANT_FIELDS:
                        normalized = value.rstrip(" ")
                    else:
                        normalized = value.strip()
                    converted[field_name] = normalized if normalized else None
                else:
                    converted[field_name] = str(value) if value is not None else None

        except (ValueError, TypeError):
            converted[field_name] = None

    return converted


class ImporterError(Exception):
    """Data importer error."""

    pass


class DataImporter:
    """Importer for JV-Data records.

    Handles batch insertion of parsed records into database with
    error handling and statistics tracking.

    Duplicate Handling:
        By default, uses INSERT OR REPLACE to handle duplicate records.
        This allows safe re-running of imports without creating duplicate data.

        IMPORTANT: For INSERT OR REPLACE to work effectively, tables should
        have PRIMARY KEY constraints defined on unique identifier columns
        (e.g., Year + MonthDay + JyoCD + RaceNum for race records).

        Without PRIMARY KEY constraints, all records are inserted which may
        result in duplicate data. See schema.py for table definitions.

    Attributes:
        database: Database handler instance
        batch_size: Number of records to insert per batch
        use_jravan_schema: Whether to use JRA-VAN standard table names
    """

    def __init__(
        self,
        database: BaseDatabase,
        batch_size: int = 1000,
        use_jravan_schema: bool = False,
    ):
        """Initialize data importer.

        Args:
            database: Database handler instance
            batch_size: Records per batch (default: 1000)
            use_jravan_schema: Use JRA-VAN standard table names (RACE, UMA_RACE, etc.)
                               instead of jltsql names (NL_RA, NL_SE, etc.)
        """
        self.database = database
        self.batch_size = batch_size
        self.use_jravan_schema = use_jravan_schema

        self._records_imported = 0
        self._records_failed = 0
        self._batches_processed = 0
        self._single_record_stats_checkpoint: Optional[
            tuple[int, int, int, int]
        ] = None
        self._jravan_tables_ready = not use_jravan_schema
        self._verified_mining_native_tables: set[str] = set()
        self._verified_hy_tables: set[str] = set()
        self._verified_bt_tables: set[str] = set()
        self._verified_jg_tables: set[str] = set()
        self._verified_wc_tables: set[str] = set()
        self._verified_wf_tables: set[str] = set()
        self._verified_ck_child_tables: dict[str, tuple[str, str]] = {}
        self._verified_rc_tables: set[str] = set()
        self._verified_ys_tables: set[str] = set()
        self._verified_tk_header_tables: dict[str, str] = {}
        self._verified_standard_odds_configs: dict[
            str,
            tuple[str, dict[str, Any]],
        ] = {}
        self._verified_standard_vote_configs: dict[
            str,
            tuple[str, dict[str, Any]],
        ] = {}

        # Map record types to table names
        # Note: Table names match schema.py table definitions (e.g. NL_RA, not NL_RA_RACE)
        self._table_map = {
            # NL_ tables (蓄積データ)
            "RA": "NL_RA",  # レース詳細
            "SE": "NL_SE",  # 馬毎レース情報
            "HR": "NL_HR",  # 払戻
            "JG": "NL_JG",  # 競走馬除外情報
            "H1": "NL_H1",  # 票数1（全賭式）
            "H6": "NL_H6",  # 票数6（三連単）
            "O1": "NL_O1",  # 単勝・複勝・枠連オッズ
            "O2": "NL_O2",  # 馬連オッズ
            "O3": "NL_O3",  # ワイドオッズ
            "O4": "NL_O4",  # 馬単オッズ
            "O5": "NL_O5",  # 三連複オッズ
            "O6": "NL_O6",  # 三連単オッズ
            "YS": "NL_YS",  # スケジュール
            "UM": "NL_UM",  # 馬マスター
            "KS": "NL_KS",  # 騎手マスター
            "CH": "NL_CH",  # 調教師マスター
            "BR": "NL_BR",  # 繁殖馬マスター
            "BN": "NL_BN",  # 生産者マスター
            "HN": "NL_HN",  # 繁殖馬マスター
            "SK": "NL_SK",  # 産駒マスター
            "RC": "NL_RC",  # レコードマスタ
            "CC": "NL_CC",  # コース変更
            "TC": "NL_TC",  # タイムコメント
            "CS": "NL_CS",  # コメントショート
            "CK": "NL_CK",  # 勝利騎手・調教師コメント
            "WC": "NL_WC",  # ウッドチップ調教
            "AV": "NL_AV",  # 出走取消・競走除外
            "JC": "NL_JC",  # 重量変更情報
            "HC": "NL_HC",  # 坂路調教
            "HS": "NL_HS",  # 競走馬市場取引価格
            "HY": "NL_HY",  # 馬名の意味由来
            "WE": "NL_WE",  # 気象情報
            "WF": "NL_WF",  # 重勝式（WIN5）
            "WH": "NL_WH",  # 馬体重情報
            "TM": "NL_TM",  # 対戦型データマイニング予想
            "TK": "NL_TK",  # 追切マスター
            "BT": "NL_BT",  # 系統情報
            "DM": "NL_DM",  # データマスター
            # RT_ tables (速報データ)
            "RT_RA": "RT_RA",  # レース詳細（速報）
            "RT_SE": "RT_SE",  # 馬毎レース情報（速報）
            "RT_HR": "RT_HR",  # 払戻（速報）
            "RT_O1": "RT_O1",  # 単勝・複勝・枠連オッズ（速報）
            "RT_O2": "RT_O2",  # 馬連オッズ（速報）
            "RT_O3": "RT_O3",  # ワイドオッズ（速報）
            "RT_O4": "RT_O4",  # 馬単オッズ（速報）
            "RT_O5": "RT_O5",  # 三連複オッズ（速報）
            "RT_O6": "RT_O6",  # 三連単オッズ（速報）
            "RT_H1": "RT_H1",  # 票数1（全賭式・速報）
            "RT_H6": "RT_H6",  # 票数6（三連単・速報）
            "RT_WE": "RT_WE",  # 気象情報（速報）
            "RT_WH": "RT_WH",  # 馬体重情報（速報）
            "RT_JC": "RT_JC",  # 重量変更情報（速報）
            "RT_CC": "RT_CC",  # コース変更（速報）
            "RT_TC": "RT_TC",  # タイムコメント（速報）
            "RT_TM": "RT_TM",  # 対戦型データマイニング予想（速報）
            "RT_DM": "RT_DM",  # データマスター（速報）
            "RT_AV": "RT_AV",  # 出走取消・競走除外（速報）
            "RT_RC": "RT_RC",  # 騎手変更情報（速報）
        }

        logger.info(
            "DataImporter initialized",
            batch_size=batch_size,
            use_jravan_schema=use_jravan_schema,
        )

    def _migrate_existing_jravan_tables(self, *, commit: bool) -> None:
        """Add newly supported columns to existing standard-name tables."""
        from src.database.migration import migrate_table_if_needed, verify_table_schema
        from src.database.schema_jravan import JRAVAN_SCHEMAS

        native_table_names = set(self._table_map.values())
        preflight_standard_schema_migrations(self.database, native_table_names)
        for table_name in native_table_names:
            standard_name = self._get_table_name_for_native(table_name)
            schema_sql = JRAVAN_SCHEMAS.get(standard_name)
            if schema_sql and self.database.table_exists(standard_name):
                if standard_name not in _STRICT_NONADDITIVE_STANDARD_TABLES:
                    migrate_table_if_needed(
                        self.database,
                        standard_name,
                        schema_sql,
                        commit=commit,
                    )
                # Ordered masters receive a complete field/key check only when
                # a matching row is written. Their existing types and capacities
                # were checked by preflight; a mismatched key makes the additive
                # migrator a no-op and remains the dedicated writer's concern.
                if standard_name not in _ORDERED_MASTER_STORAGE_TABLES:
                    verify_table_schema(self.database, standard_name, schema_sql)
        for child_table in ("CHOKYO_SEISEKI", "KISYU_SEISEKI"):
            child_schema = JRAVAN_SCHEMAS.get(child_table)
            if child_schema and self.database.table_exists(child_table):
                migrate_table_if_needed(
                    self.database,
                    child_table,
                    child_schema,
                    commit=commit,
                )
                verify_table_schema(self.database, child_table, child_schema)

    def _ensure_jravan_tables_ready(self, *, auto_commit: bool) -> None:
        """Migrate standard-name tables only after the DB is connected."""
        if self._jravan_tables_ready:
            return
        if not self.database.is_connected():
            raise ImporterError("JRA-VAN schema import requires a connected database")
        self._migrate_existing_jravan_tables(commit=auto_commit)
        if auto_commit:
            self._jravan_tables_ready = True

    @staticmethod
    def _get_table_name_for_native(table_name: str) -> str:
        return resolve_standard_storage_table_name(table_name)

    def _get_table_name(self, record_type: str) -> Optional[str]:
        """Get table name for record type.

        Args:
            record_type: Record type code (e.g., "RA", "SE")

        Returns:
            Table name or None if not mapped
        """
        # Get base table name from mapping
        table_name = self._table_map.get(record_type)
        if not table_name:
            return None

        # Convert to JRA-VAN standard name if requested
        if self.use_jravan_schema:
            return resolve_standard_table_name(self.database, table_name)

        return table_name

    def _clean_record(self, record: dict) -> dict:
        """Remove metadata fields that shouldn't be inserted into tables.

        Args:
            record: Original record dictionary

        Returns:
            Cleaned record without metadata fields
        """
        return clean_record_metadata(record)

    def _record_for_table(self, record: dict, table_name: str) -> dict:
        """Return the parser representation required by the target schema."""
        if table_name in {"BATAIJYU", "MINING", "TAISENGATA_MINING"}:
            wide_record = record.get("_wide_record")
            if isinstance(wide_record, dict):
                return self._clean_record(wide_record)
        return translate_standard_field_names(self._clean_record(record), table_name)

    def _convert_record(self, record: dict, table_name: str) -> dict:
        """Convert record field types based on table schema.

        Delegates to the module-level convert_record_types() so that
        DataImporter and RealtimeUpdater share identical coercion rules.
        """
        return convert_record_types(record, table_name)

    @staticmethod
    def _has_complete_primary_key(table_name: str, record: dict) -> bool:
        """Return True when a converted row has all schema primary-key values."""
        from src.database.table_mappings import JRAVAN_TO_JLTSQL

        primary_keys = get_table_primary_key_columns(table_name)
        if not primary_keys:
            primary_keys = get_table_primary_key_columns(
                JRAVAN_TO_JLTSQL.get(table_name, table_name)
            )
        if not primary_keys:
            return True
        return all(record.get(key) not in (None, "") for key in primary_keys)

    def import_records(
        self,
        records: Iterator[dict],
        auto_commit: bool = True,
    ) -> Dict[str, int]:
        """Import records into database.

        Args:
            records: Iterator of parsed record dictionaries
            auto_commit: Whether to auto-commit after each batch

        Returns:
            Dictionary with import statistics

        Raises:
            ImporterError: If import fails

        Examples:
            >>> from src.database.sqlite_handler import SQLiteDatabase
            >>> db = SQLiteDatabase({"path": "./test.db"})
            >>> importer = DataImporter(db)
            >>> with db:
            ...     stats = importer.import_records(records)
            ...     print(f"Imported {stats['records_imported']} records")
        """
        if not auto_commit:
            self.database.begin_transaction()
        try:
            self._ensure_jravan_tables_ready(auto_commit=auto_commit)
        except Exception:
            if not auto_commit:
                rollback_failed_import(
                    self.database,
                    context="standard-schema preflight in caller-owned import",
                )
            raise

        # Reset statistics
        self._records_imported = 0
        self._records_failed = 0
        self._batches_processed = 0

        # Group records by type for batch insertion
        batch_buffers: Dict[str, List[dict]] = {}
        standard_odds_fingerprints: dict[str, tuple] = {}
        standard_vote_fingerprints: dict[str, tuple] = {}
        last_expanded_record_fingerprint = None

        try:
            for record in records:
                # Get record type and table name
                # Note: Japanese parsers use 'レコード種別ID', JRA-VAN standard uses 'RecordSpec'
                record_type = _record_type_from_record(record)
                if not record_type:
                    logger.warning(
                        "Record missing record type field",
                        record_keys=list(record.keys())[:5] if record else None,
                    )
                    self._records_failed += 1
                    continue

                table_name = self._get_table_name(record_type)
                if not table_name:
                    logger.warning(
                        f"Unknown record type: {record_type}",
                        record_type=record_type,
                    )
                    self._records_failed += 1
                    continue

                if table_name not in self._verified_hy_tables:
                    if verify_hy_storage_schema(self.database, table_name):
                        self._verified_hy_tables.add(table_name)
                if table_name not in self._verified_bt_tables:
                    if verify_bt_storage_schema(self.database, table_name):
                        self._verified_bt_tables.add(table_name)
                if table_name not in self._verified_jg_tables:
                    if verify_jg_storage_schema(self.database, table_name):
                        self._verified_jg_tables.add(table_name)
                validate_jg_record(record, table_name)
                if table_name not in self._verified_wc_tables:
                    if verify_wc_storage_schema(self.database, table_name):
                        self._verified_wc_tables.add(table_name)
                validate_wc_record(record, table_name)
                if table_name not in self._verified_wf_tables:
                    if verify_wf_storage_schema(self.database, table_name):
                        self._verified_wf_tables.add(table_name)
                validate_wf_record(record, table_name)

                if table_name not in self._verified_mining_native_tables:
                    if verify_mining_native_schema(self.database, record, table_name):
                        self._verified_mining_native_tables.add(table_name)

                if _is_standard_vote_record_erase(record, table_name):
                    pending = batch_buffers.setdefault(table_name, [])
                    if pending:
                        self._flush_batch(table_name, pending, auto_commit)
                        batch_buffers[table_name] = []
                    delete_standard_vote_record(
                        self.database,
                        record,
                        table_name,
                        commit_batch=auto_commit,
                        verification_cache=self._verified_standard_vote_configs,
                    )
                    standard_vote_fingerprints.pop(table_name, None)
                    self._records_imported += 1
                    self._batches_processed += 1
                    last_expanded_record_fingerprint = None
                    continue

                if _is_standard_odds_record_erase(record, table_name):
                    pending = batch_buffers.setdefault(table_name, [])
                    if pending:
                        self._flush_batch(table_name, pending, auto_commit)
                        batch_buffers[table_name] = []
                    delete_standard_odds_record(
                        self.database,
                        record,
                        table_name,
                        commit_batch=auto_commit,
                        verification_cache=self._verified_standard_odds_configs,
                    )
                    standard_odds_fingerprints.pop(table_name, None)
                    self._records_imported += 1
                    self._batches_processed += 1
                    last_expanded_record_fingerprint = None
                    continue

                if _is_official_record_erase(record, table_name):
                    pending = batch_buffers.setdefault(table_name, [])
                    if pending:
                        self._flush_batch(table_name, pending, auto_commit)
                        batch_buffers[table_name] = []
                    _delete_official_record(self.database, record, table_name)
                    self._records_imported += 1
                    self._batches_processed += 1
                    if auto_commit:
                        self.database.commit()
                    last_expanded_record_fingerprint = None
                    continue

                if _is_mining_race_delete(record, table_name):
                    pending = batch_buffers.setdefault(table_name, [])
                    if pending:
                        self._flush_batch(table_name, pending, auto_commit)
                        batch_buffers[table_name] = []
                    _delete_mining_race_rows(self.database, record, table_name)
                    self._records_imported += 1
                    self._batches_processed += 1
                    if auto_commit:
                        self.database.commit()
                    last_expanded_record_fingerprint = None
                    continue

                if _is_mining_snapshot_follower(record, table_name):
                    continue

                mining_snapshot_rows = _mining_native_snapshot_rows(record, table_name)
                if mining_snapshot_rows is not None:
                    pending = batch_buffers.setdefault(table_name, [])
                    if pending:
                        self._flush_batch(table_name, pending, auto_commit)
                        batch_buffers[table_name] = []
                    if auto_commit:
                        self.database.begin_transaction()
                    try:
                        rows = replace_mining_native_snapshot(
                            self.database, record, table_name
                        )
                        if auto_commit:
                            self.database.commit()
                    except Exception:
                        self.database.rollback()
                        raise
                    self._records_imported += rows
                    self._batches_processed += 1
                    continue

                if table_name in _STANDARD_VOTE_CONFIG_BY_OWNER:
                    fingerprint = _standard_vote_physical_fingerprint(
                        record,
                        table_name,
                    )
                    pending = batch_buffers.setdefault(table_name, [])
                    previous = standard_vote_fingerprints.get(table_name)
                    if pending and previous != fingerprint:
                        self._flush_batch(table_name, pending, auto_commit)
                        pending = []
                        batch_buffers[table_name] = pending
                    pending.append(record)
                    standard_vote_fingerprints[table_name] = fingerprint
                    continue

                if table_name in _STANDARD_ODDS_CONFIG_BY_OWNER:
                    fingerprint = _standard_odds_physical_fingerprint(
                        record,
                        table_name,
                    )
                    pending = batch_buffers.setdefault(table_name, [])
                    previous = standard_odds_fingerprints.get(table_name)
                    if pending and previous != fingerprint:
                        self._flush_batch(table_name, pending, auto_commit)
                        pending = []
                        batch_buffers[table_name] = pending
                    pending.append(record)
                    standard_odds_fingerprints[table_name] = fingerprint
                    continue

                fingerprint = _expanded_record_fingerprint(record, table_name)
                if fingerprint is not None:
                    if fingerprint == last_expanded_record_fingerprint:
                        continue
                    last_expanded_record_fingerprint = fingerprint

                # Add to batch buffer
                if table_name not in batch_buffers:
                    batch_buffers[table_name] = []

                batch_buffers[table_name].append(record)

                # Check if any batch is full
                if len(batch_buffers[table_name]) >= self.batch_size:
                    self._flush_batch(
                        table_name,
                        batch_buffers[table_name],
                        auto_commit,
                    )
                    batch_buffers[table_name] = []

            # Flush remaining batches
            for table_name, batch in batch_buffers.items():
                if batch:
                    self._flush_batch(table_name, batch, auto_commit)

            # Log summary
            stats = self.get_statistics()
            logger.info("Import completed", **stats)

            return stats

        except SchemaMigrationError:
            if not auto_commit:
                rollback_failed_import(
                    self.database,
                    context="validation/schema failure in caller-owned import",
                )
            raise
        except Exception as e:
            if not auto_commit:
                rollback_failed_import(
                    self.database,
                    context="unexpected failure in caller-owned import",
                )
            logger.error("Import failed", error=str(e))
            raise ImporterError(f"Failed to import records: {e}")

    def _flush_batch(
        self,
        table_name: str,
        batch: List[dict],
        auto_commit: bool,
    ):
        """Flush a batch of records to database.

        Args:
            table_name: Target table name
            batch: List of record dictionaries
            auto_commit: Whether to commit after insertion
        """
        if not batch:
            return

        if table_name not in self._verified_rc_tables:
            if verify_rc_storage_schema(self.database, table_name):
                self._verified_rc_tables.add(table_name)
        if table_name not in self._verified_ys_tables:
            if verify_ys_storage_schema(self.database, table_name):
                self._verified_ys_tables.add(table_name)

        if table_name in _STANDARD_VOTE_CONFIG_BY_OWNER:
            rows = insert_standard_vote_batch(
                self.database,
                table_name,
                batch,
                commit_batch=auto_commit,
                verification_cache=self._verified_standard_vote_configs,
            )
            self._records_imported += rows
            if rows:
                self._batches_processed += 1
            return

        if table_name in _STANDARD_ODDS_CONFIG_BY_OWNER:
            rows = insert_standard_odds_batch(
                self.database,
                table_name,
                batch,
                commit_batch=auto_commit,
                verification_cache=self._verified_standard_odds_configs,
            )
            self._records_imported += rows
            if rows:
                self._batches_processed += 1
            return

        if table_name in _TK_CHILD_STORAGE_TABLES:
            header_table = self._verified_tk_header_tables.get(table_name)
            if header_table is None:
                verified = verify_tk_coupled_tables(self.database, table_name)
                if verified is None:
                    raise SchemaMigrationError(
                        f"TK import could not resolve header table for {table_name}"
                    )
                header_table = verified
                self._verified_tk_header_tables[table_name] = header_table
            prepared_tk = [
                prepare_tk_coupled_record(
                    self.database,
                    record,
                    table_name,
                    verified_header_table=header_table,
                )
                for record in batch
            ]
            if any(item is None for item in prepared_tk):
                raise SchemaMigrationError("TK batch lost its coupled snapshot metadata")
            succeeded, failed = insert_tk_coupled_batch(
                self.database,
                table_name,
                [item for item in prepared_tk if item is not None],
                commit_batch=auto_commit,
                optimized=False,
            )
            self._records_imported += succeeded
            self._records_failed += failed
            if succeeded:
                self._batches_processed += 1
            return

        if table_name in _WF_STANDARD_STORAGE_TABLES:
            # One provider record is one parent row plus exactly 243 payout
            # rows; the coupled writer applies them in provider order and never
            # enters the generic parent-only fallback below.
            prepared_wf = [prepare_wf_standard_record(record) for record in batch]
            succeeded, failed = insert_wf_standard_batch(
                self.database,
                prepared_wf,
                commit_batch=auto_commit,
                optimized=False,
            )
            self._records_imported += succeeded
            self._records_failed += failed
            if succeeded:
                self._batches_processed += 1
            return

        verified_ch_result_table = None
        if _ch_result_table_name(table_name) is not None:
            try:
                verified_ch_result_table = verify_ch_coupled_table(self.database, table_name)
            except DatabaseError as error:
                if not auto_commit:
                    raise
                logger.warning(
                    "CH result schema verification failed, retrying coupled batch",
                    table=table_name,
                    error=str(error),
                )
                self.database.rollback()
                # Only retry catalog verification. No header or child mutation
                # has happened yet, and a second failure aborts the import.
                verified_ch_result_table = verify_ch_coupled_table(self.database, table_name)

        verified_ck_child_tables = self._verified_ck_child_tables.get(table_name)
        if _ck_child_tables(table_name) is not None and verified_ck_child_tables is None:
            verified = verify_ck_coupled_tables(self.database, table_name)
            if verified is None:
                raise SchemaMigrationError(
                    f"CK import could not resolve normalized children for {table_name}"
                )
            verified_ck_child_tables = verified
            self._verified_ck_child_tables[table_name] = verified

        verified_ks_result_table = None
        if _ks_result_table_name(table_name) is not None:
            try:
                verified_ks_result_table = verify_ks_coupled_table(self.database, table_name)
            except DatabaseError as error:
                if not auto_commit:
                    raise
                logger.warning(
                    "KS result schema verification failed, retrying coupled batch",
                    table=table_name,
                    error=str(error),
                )
                self.database.rollback()
                verified_ks_result_table = verify_ks_coupled_table(self.database, table_name)

        try:
            # Clean records to remove metadata fields before insertion
            clean_batch = [self._record_for_table(record, table_name) for record in batch]
            # Convert types based on schema definition
            converted_batch = []
            prepared_ch: list[tuple[dict, str, list[dict]]] = []
            prepared_ks: list[tuple[dict, str, list[dict]]] = []
            prepared_ck: list[tuple[dict, str, list[dict], str, list[dict]]] = []
            for original_record, record in zip(batch, clean_batch, strict=True):
                converted_record = self._convert_record(record, table_name)
                if (
                    table_name in _ORDERED_MASTER_STORAGE_TABLES
                    or self._has_complete_primary_key(table_name, converted_record)
                ):
                    converted_batch.append(converted_record)
                    coupled = prepare_ch_coupled_rows(
                        self.database,
                        original_record,
                        table_name,
                        verified_result_table=verified_ch_result_table,
                    )
                    if coupled is not None:
                        result_table, result_rows = coupled
                        prepared_ch.append((converted_record, result_table, result_rows))
                    ks_coupled = prepare_ks_coupled_rows(
                        self.database,
                        original_record,
                        table_name,
                        verified_result_table=verified_ks_result_table,
                    )
                    if ks_coupled is not None:
                        result_table, result_rows = ks_coupled
                        prepared_ks.append((converted_record, result_table, result_rows))
                    ck_coupled = prepare_ck_coupled_rows(
                        self.database,
                        original_record,
                        table_name,
                        converted_record,
                        verified_child_tables=verified_ck_child_tables,
                    )
                    if ck_coupled is not None:
                        chaku_table, chaku_rows, ruikei_table, ruikei_rows = ck_coupled
                        prepared_ck.append(
                            (
                                converted_record,
                                chaku_table,
                                chaku_rows,
                                ruikei_table,
                                ruikei_rows,
                            )
                        )
                else:
                    self._records_failed += 1
                    logger.warning(
                        "Skipping record with incomplete primary key",
                        table=table_name,
                        primary_key=get_table_primary_key_columns(table_name),
                    )

            if not converted_batch:
                return

            if table_name in _WF_NATIVE_STORAGE_TABLES:
                rows = insert_wf_native_batch(
                    self.database,
                    table_name,
                    converted_batch,
                    commit_batch=auto_commit,
                    optimized=False,
                )
                self._records_imported += rows
                if rows:
                    self._batches_processed += 1
                return

            if table_name in _RC_STORAGE_TABLES:
                rows = apply_rc_batch(
                    self.database,
                    table_name,
                    converted_batch,
                    commit_batch=auto_commit,
                    optimized=False,
                )
                self._records_imported += rows
                if rows:
                    self._batches_processed += 1
                return

            if table_name in _YS_STORAGE_TABLES:
                rows = apply_ys_batch(
                    self.database,
                    table_name,
                    converted_batch,
                    commit_batch=auto_commit,
                    optimized=False,
                )
                self._records_imported += rows
                if rows:
                    self._batches_processed += 1
                return

            if prepared_ck:
                if len(prepared_ck) != len(converted_batch):
                    raise SchemaMigrationError("CK batch lost its coupled child rows")
                succeeded, failed = insert_ck_coupled_batch(
                    self.database,
                    table_name,
                    prepared_ck,
                    commit_batch=auto_commit,
                    optimized=False,
                )
                self._records_imported += succeeded
                self._records_failed += failed
                if succeeded:
                    self._batches_processed += 1
                return

            if prepared_ks:
                if len(prepared_ks) != len(converted_batch):
                    raise SchemaMigrationError("KS batch lost its coupled result rows")
                succeeded, failed = insert_ks_coupled_batch(
                    self.database,
                    table_name,
                    prepared_ks,
                    commit_batch=auto_commit,
                    optimized=False,
                )
                self._records_imported += succeeded
                self._records_failed += failed
                if succeeded:
                    self._batches_processed += 1
                return

            if prepared_ch:
                if len(prepared_ch) != len(converted_batch):
                    raise SchemaMigrationError("CH batch lost its coupled result rows")
                succeeded, failed = insert_ch_coupled_batch(
                    self.database,
                    table_name,
                    prepared_ch,
                    commit_batch=auto_commit,
                    optimized=False,
                )
                self._records_imported += succeeded
                self._records_failed += failed
                if succeeded:
                    self._batches_processed += 1
                return

            # Insert batch using INSERT OR REPLACE
            rows = self.database.insert_many(table_name, converted_batch, use_replace=True)

            self._records_imported += rows
            self._batches_processed += 1

            if auto_commit:
                self.database.commit()

            logger.debug(
                "Batch inserted",
                table=table_name,
                records=rows,
                batch_num=self._batches_processed,
            )

        except DatabaseError as e:
            if not auto_commit:
                # The database handler has already rolled back the enclosing
                # transaction. Individual retries here would create a partial
                # import and invalidate BatchProcessor's atomicity guarantee.
                raise
            if (
                _ch_result_table_name(table_name) is not None
                or _ks_result_table_name(table_name) is not None
                or table_name in _ORDERED_MASTER_STORAGE_TABLES
                or table_name in _WF_NATIVE_STORAGE_TABLES
                or table_name in _WF_STANDARD_STORAGE_TABLES
            ):
                # Coupled master writes must never enter the parent-only fallback.
                raise

            # Rollback failed batch transaction
            logger.warning(
                "Batch insert failed, trying individual inserts",
                table=table_name,
                error=str(e),
            )

            # PostgreSQLDatabase performs driver-specific rollback when
            # insert_many() fails. Avoid a second rollback here.
            try:
                db_type = self.database.get_db_type()
            except AttributeError:
                # Fallback for databases without get_db_type() method
                db_type = "unknown"

            if db_type != "postgresql":
                try:
                    self.database.rollback()
                except Exception as rollback_error:
                    logger.debug(
                        "Rollback failed during batch fallback",
                        table=table_name,
                        error=str(rollback_error),
                    )

            # Try inserting one by one on batch failure
            success_count = 0
            fail_count = 0

            for record in batch:
                try:
                    clean_record = self._record_for_table(record, table_name)
                    converted_record = self._convert_record(clean_record, table_name)
                    if not self._has_complete_primary_key(table_name, converted_record):
                        fail_count += 1
                        logger.warning(
                            "Skipping record with incomplete primary key",
                            table=table_name,
                            primary_key=get_table_primary_key_columns(table_name),
                        )
                        continue
                    self.database.insert(table_name, converted_record, use_replace=True)
                    success_count += 1

                except DatabaseError as record_error:
                    fail_count += 1
                    logger.error(
                        "Failed to insert record",
                        table=table_name,
                        error=str(record_error),
                    )

            self._records_imported += success_count
            self._records_failed += fail_count

            # Only commit if we had successful individual inserts
            if auto_commit and success_count > 0:
                self.database.commit()

    def _begin_single_record_transaction(self, *, auto_commit: bool) -> None:
        """Start or join one single-record transaction and checkpoint counters."""
        if auto_commit:
            if not self.database.is_transaction_active():
                self._single_record_stats_checkpoint = None
            return
        if not self.database.is_transaction_active():
            self.database.begin_transaction()
        generation = self.database.get_transaction_generation()
        if generation is None:
            raise DatabaseError(
                "Database did not expose an active transaction generation"
            )
        checkpoint_generation = (
            self._single_record_stats_checkpoint[0]
            if self._single_record_stats_checkpoint is not None
            else None
        )
        if checkpoint_generation != generation:
            # The transaction may have been opened outside this importer. Its
            # generation distinguishes that new caller transaction from a
            # previously committed sequence whose checkpoint is still cached.
            self._single_record_stats_checkpoint = (
                generation,
                self._records_imported,
                self._records_failed,
                self._batches_processed,
            )

    def _rollback_single_record_transaction(self, *, context: str) -> None:
        """Rollback a failed single-record sequence and restore its counters."""
        rollback_failed_import(self.database, context=context)
        if self._single_record_stats_checkpoint is not None:
            (
                _,
                self._records_imported,
                self._records_failed,
                self._batches_processed,
            ) = self._single_record_stats_checkpoint
            self._single_record_stats_checkpoint = None

    def import_single_record(
        self,
        record: dict,
        auto_commit: bool = True,
    ) -> bool:
        """Import single record.

        Args:
            record: Parsed record dictionary
            auto_commit: Whether to commit after insertion

        Returns:
            True if successful, False otherwise
        """
        self._begin_single_record_transaction(auto_commit=auto_commit)
        try:
            self._ensure_jravan_tables_ready(auto_commit=auto_commit)
        except Exception:
            if not auto_commit:
                self._rollback_single_record_transaction(
                    context="standard-schema preflight in single-record import",
                )
            raise

        # Note: Japanese parsers use 'レコード種別ID', JRA-VAN standard uses 'RecordSpec'
        record_type = _record_type_from_record(record)
        if not record_type:
            logger.warning("Record missing record type field")
            if not auto_commit:
                self._rollback_single_record_transaction(
                    context="missing record type in single-record import",
                )
            return False

        table_name = self._get_table_name(record_type)
        if not table_name:
            logger.warning(f"Unknown record type: {record_type}")
            if not auto_commit:
                self._rollback_single_record_transaction(
                    context="unknown record type in single-record import",
                )
            return False

        try:
            if table_name not in self._verified_hy_tables:
                if verify_hy_storage_schema(self.database, table_name):
                    self._verified_hy_tables.add(table_name)
            if table_name not in self._verified_bt_tables:
                if verify_bt_storage_schema(self.database, table_name):
                    self._verified_bt_tables.add(table_name)
            if table_name not in self._verified_jg_tables:
                if verify_jg_storage_schema(self.database, table_name):
                    self._verified_jg_tables.add(table_name)
            validate_jg_record(record, table_name)
            if table_name not in self._verified_wc_tables:
                if verify_wc_storage_schema(self.database, table_name):
                    self._verified_wc_tables.add(table_name)
            validate_wc_record(record, table_name)
            if table_name not in self._verified_wf_tables:
                if verify_wf_storage_schema(self.database, table_name):
                    self._verified_wf_tables.add(table_name)
            validate_wf_record(record, table_name)
            if table_name not in self._verified_rc_tables:
                if verify_rc_storage_schema(self.database, table_name):
                    self._verified_rc_tables.add(table_name)
            if table_name not in self._verified_ys_tables:
                if verify_ys_storage_schema(self.database, table_name):
                    self._verified_ys_tables.add(table_name)
            if table_name in _TK_CHILD_STORAGE_TABLES:
                header_table = self._verified_tk_header_tables.get(table_name)
                if header_table is None:
                    verified = verify_tk_coupled_tables(self.database, table_name)
                    if verified is None:
                        raise SchemaMigrationError(
                            f"TK import could not resolve header table for {table_name}"
                        )
                    header_table = verified
                    self._verified_tk_header_tables[table_name] = header_table
                prepared = prepare_tk_coupled_record(
                    self.database,
                    record,
                    table_name,
                    verified_header_table=header_table,
                )
                if prepared is None:
                    raise SchemaMigrationError("TK single record lost its snapshot metadata")
                succeeded, failed = insert_tk_coupled_batch(
                    self.database,
                    table_name,
                    [prepared],
                    commit_batch=auto_commit,
                    optimized=False,
                )
                self._records_imported += succeeded
                self._records_failed += failed
                if succeeded:
                    self._batches_processed += 1
                return succeeded == 1
            if table_name in _WF_STANDARD_STORAGE_TABLES:
                succeeded, failed = insert_wf_standard_batch(
                    self.database,
                    [prepare_wf_standard_record(record)],
                    commit_batch=auto_commit,
                    optimized=False,
                )
                self._records_imported += succeeded
                self._records_failed += failed
                if succeeded:
                    self._batches_processed += 1
                return succeeded == 1
            if table_name not in self._verified_mining_native_tables:
                if verify_mining_native_schema(self.database, record, table_name):
                    self._verified_mining_native_tables.add(table_name)
            if _is_standard_vote_record_erase(record, table_name):
                delete_standard_vote_record(
                    self.database,
                    record,
                    table_name,
                    commit_batch=auto_commit,
                    verification_cache=self._verified_standard_vote_configs,
                )
                self._records_imported += 1
                self._batches_processed += 1
                return True
            if _is_standard_odds_record_erase(record, table_name):
                delete_standard_odds_record(
                    self.database,
                    record,
                    table_name,
                    commit_batch=auto_commit,
                    verification_cache=self._verified_standard_odds_configs,
                )
                self._records_imported += 1
                self._batches_processed += 1
                return True
            if _is_official_record_erase(record, table_name):
                _delete_official_record(self.database, record, table_name)
                self._records_imported += 1
                self._batches_processed += 1
                if auto_commit:
                    self.database.commit()
                return True
            if _is_mining_race_delete(record, table_name):
                _delete_mining_race_rows(self.database, record, table_name)
                self._records_imported += 1
                self._batches_processed += 1
                if auto_commit:
                    self.database.commit()
                return True
            if _mining_native_snapshot_rows(record, table_name) is not None:
                if auto_commit:
                    self.database.begin_transaction()
                try:
                    rows = replace_mining_native_snapshot(self.database, record, table_name)
                    if auto_commit:
                        self.database.commit()
                except Exception:
                    self.database.rollback()
                    raise
                self._records_imported += rows
                self._batches_processed += 1
                return True
            if table_name in _STANDARD_VOTE_CONFIG_BY_OWNER:
                rows = insert_standard_vote_batch(
                    self.database,
                    table_name,
                    [record],
                    commit_batch=auto_commit,
                    verification_cache=self._verified_standard_vote_configs,
                )
                self._records_imported += rows
                if rows:
                    self._batches_processed += 1
                return rows == 1
            if table_name in _STANDARD_ODDS_CONFIG_BY_OWNER:
                rows = insert_standard_odds_batch(
                    self.database,
                    table_name,
                    [record],
                    commit_batch=auto_commit,
                    verification_cache=self._verified_standard_odds_configs,
                )
                self._records_imported += rows
                if rows:
                    self._batches_processed += 1
                return rows == 1
            clean_record = self._record_for_table(record, table_name)
            converted_record = self._convert_record(clean_record, table_name)
            if (
                table_name not in _ORDERED_MASTER_STORAGE_TABLES
                and not self._has_complete_primary_key(table_name, converted_record)
            ):
                self._records_failed += 1
                logger.warning(
                    "Skipping record with incomplete primary key",
                    table=table_name,
                    primary_key=get_table_primary_key_columns(table_name),
                )
                if not auto_commit:
                    self._rollback_single_record_transaction(
                        context="incomplete key in single-record import",
                    )
                return False
            if table_name in _RC_STORAGE_TABLES:
                rows = apply_rc_batch(
                    self.database,
                    table_name,
                    [converted_record],
                    commit_batch=auto_commit,
                    optimized=False,
                )
                self._records_imported += rows
                if rows:
                    self._batches_processed += 1
                return rows == 1
            if table_name in _YS_STORAGE_TABLES:
                rows = apply_ys_batch(
                    self.database,
                    table_name,
                    [converted_record],
                    commit_batch=auto_commit,
                    optimized=False,
                )
                self._records_imported += rows
                if rows:
                    self._batches_processed += 1
                return rows == 1
            verified_ck = self._verified_ck_child_tables.get(table_name)
            if _ck_child_tables(table_name) is not None and verified_ck is None:
                verified_ck = verify_ck_coupled_tables(self.database, table_name)
                if verified_ck is None:
                    raise SchemaMigrationError(
                        f"CK import could not resolve normalized children for {table_name}"
                    )
                self._verified_ck_child_tables[table_name] = verified_ck
            ck_coupled = prepare_ck_coupled_rows(
                self.database,
                record,
                table_name,
                converted_record,
                verified_child_tables=verified_ck,
            )
            if ck_coupled is not None:
                chaku_table, chaku_rows, ruikei_table, ruikei_rows = ck_coupled
                succeeded, failed = insert_ck_coupled_batch(
                    self.database,
                    table_name,
                    [(converted_record, chaku_table, chaku_rows, ruikei_table, ruikei_rows)],
                    commit_batch=auto_commit,
                    optimized=False,
                )
                self._records_imported += succeeded
                self._records_failed += failed
                if succeeded:
                    self._batches_processed += 1
                return succeeded == 1
            coupled = prepare_ch_coupled_rows(self.database, record, table_name)
            if coupled is not None:
                result_table, result_rows = coupled
                succeeded, failed = insert_ch_coupled_batch(
                    self.database,
                    table_name,
                    [(converted_record, result_table, result_rows)],
                    commit_batch=auto_commit,
                    optimized=False,
                )
                self._records_imported += succeeded
                self._records_failed += failed
                return succeeded == 1
            ks_coupled = prepare_ks_coupled_rows(self.database, record, table_name)
            if ks_coupled is not None:
                result_table, result_rows = ks_coupled
                succeeded, failed = insert_ks_coupled_batch(
                    self.database,
                    table_name,
                    [(converted_record, result_table, result_rows)],
                    commit_batch=auto_commit,
                    optimized=False,
                )
                self._records_imported += succeeded
                self._records_failed += failed
                return succeeded == 1
            self.database.insert(table_name, converted_record, use_replace=True)
            self._records_imported += 1

            if auto_commit:
                self.database.commit()

            return True

        except SchemaMigrationError:
            if not auto_commit:
                self._rollback_single_record_transaction(
                    context="validation/schema failure in single-record import",
                )
            raise
        except DatabaseError as e:
            if not auto_commit:
                self._rollback_single_record_transaction(
                    context="database failure in single-record import",
                )
            self._records_failed += 1
            logger.error("Failed to insert record", error=str(e))
            return False
        except Exception:
            if not auto_commit:
                self._rollback_single_record_transaction(
                    context="unexpected failure in single-record import",
                )
            raise

    def get_statistics(self) -> Dict[str, int]:
        """Get import statistics.

        Returns:
            Dictionary with import statistics
        """
        return {
            "records_imported": self._records_imported,
            "records_failed": self._records_failed,
            "batches_processed": self._batches_processed,
        }

    def reset_statistics(self):
        """Reset import statistics."""
        self._records_imported = 0
        self._records_failed = 0
        self._batches_processed = 0
        self._single_record_stats_checkpoint = None

    def add_table_mapping(self, record_type: str, table_name: str):
        """Add custom table mapping.

        Args:
            record_type: Record type code (e.g., "RA")
            table_name: Target table name
        """
        self._table_map[record_type] = table_name
        logger.info(f"Added table mapping: {record_type} -> {table_name}")

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<DataImporter "
            f"imported={self._records_imported} "
            f"failed={self._records_failed} "
            f"batches={self._batches_processed}>"
        )
