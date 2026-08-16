"""Data importer for JLTSQL.

This module imports parsed JV-Data records into database.
"""

from typing import Any, Dict, Iterator, List, Optional

from src.database.base import BaseDatabase, DatabaseError
from src.database.migration import SchemaMigrationError
from src.database.schema_types import (
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


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
_ORDERED_MASTER_STORAGE_TABLES = (
    _RC_STORAGE_TABLES | _YS_STORAGE_TABLES | _TK_CHILD_STORAGE_TABLES
)


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
    return record.get("レコード種別ID") or record.get("RecordSpec") or record.get("headRecordSpec")


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
    "WF": {"NL_WF", "RT_WF", "WIN5"},
    "HY": {"NL_HY", "BAMEIORIGIN"},
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

    key_columns = _OFFICIAL_ERASE_KEY_COLUMNS[record_type]
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
    expected_names = set(_ck_named_constraints(expected_schema))
    rows = database.fetch_all(
        "SELECT conname AS name, contype AS type, confdeltype AS delete_type, "
        "pg_get_constraintdef(oid) AS definition "
        "FROM pg_constraint WHERE conrelid = to_regclass(?)",
        (table_name.lower(),),
    )
    by_name = {str(row["name"]).lower(): row for row in rows}
    if not expected_names <= set(by_name):
        raise SchemaMigrationError(
            f"CK child constraints missing for {table_name}: "
            f"{sorted(expected_names - set(by_name))}"
        )
    required_tokens = {
        "ck_chaku_parent_fk": (*_CK_PARENT_KEY, "nl_ck", "cascade"),
        "ck_chaku_domain": (
            "entitykubun",
            "periodnum",
            "metrickubun",
            "bucketnum",
            "uma",
            "kisyu",
            "chokyosi",
            "banusi",
            "breeder",
            *tuple(metric for metric, _ in (*_CK_HORSE_METRICS, *_CK_PROFESSIONAL_METRICS)),
        ),
        "ck_chaku_count_shape": ("count5", "count6", "kyakusitu", "is null"),
        "ck_ruikei_parent_fk": (*_CK_PARENT_KEY, "nl_ck", "cascade"),
        "ck_ruikei_shape": (
            "entitykubun",
            "periodnum",
            "honsyokinheichi",
            "honsyokinsyogai",
            "fukasyokinheichi",
            "fukasyokinsyogai",
            "honsyokintotal",
            "fukasyokin",
            "is not null",
        ),
    }
    for constraint_name in expected_names:
        definition = str(by_name[constraint_name].get("definition") or "").lower()
        if not all(str(token).lower() in definition for token in required_tokens[constraint_name]):
            raise SchemaMigrationError(
                f"CK child constraint body mismatch for {table_name}.{constraint_name}"
            )
        if (
            constraint_name.endswith("parent_fk")
            and str(by_name[constraint_name].get("delete_type")) != "c"
        ):
            raise SchemaMigrationError(f"CK child foreign key is not CASCADE: {table_name}")


def verify_ck_coupled_tables(
    database: BaseDatabase,
    main_table_name: str,
) -> tuple[str, str] | None:
    """Verify the complete CK parent/child contract before any mutation."""
    child_tables = _ck_child_tables(main_table_name)
    if child_tables is None:
        return None

    from src.database.migration import verify_table_schema
    from src.database.schema import SCHEMAS

    for target in _ck_schema_targets(database):
        for table_name in (main_table_name, *child_tables):
            schema_sql = SCHEMAS[table_name]
            if not target.table_exists_strict(table_name):
                raise SchemaMigrationError(f"CK import requires table {table_name} before mutation")
            verify_table_schema(target, table_name, schema_sql)
            if table_name != main_table_name:
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
        self._jravan_tables_ready = not use_jravan_schema
        self._verified_mining_native_tables: set[str] = set()
        self._verified_hy_tables: set[str] = set()
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
            "JG": "NL_JG",  # 除外馬
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
            "WF": "NL_WF",  # 風情報
            "WH": "NL_WH",  # 馬体重情報
            "TM": "NL_TM",  # 対戦型データマイニング予想
            "TK": "NL_TK",  # 追切マスター
            "BT": "NL_BT",  # 調教Bタイム
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

        for table_name in set(self._table_map.values()):
            standard_name = self._get_table_name_for_native(table_name)
            schema_sql = JRAVAN_SCHEMAS.get(standard_name)
            if schema_sql and self.database.table_exists(standard_name):
                migrate_table_if_needed(self.database, standard_name, schema_sql, commit=commit)
                # Ordered masters have deliberately non-automatic key migrations.
                # Verify them only when a matching row is about to be written so
                # an obsolete unused table cannot block unrelated imports.
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
        self._ensure_jravan_tables_ready(auto_commit=auto_commit)

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
            raise
        except Exception as e:
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
        if not auto_commit:
            self.database.begin_transaction()
        self._ensure_jravan_tables_ready(auto_commit=auto_commit)

        # Note: Japanese parsers use 'レコード種別ID', JRA-VAN standard uses 'RecordSpec'
        record_type = _record_type_from_record(record)
        if not record_type:
            logger.warning("Record missing record type field")
            return False

        table_name = self._get_table_name(record_type)
        if not table_name:
            logger.warning(f"Unknown record type: {record_type}")
            return False

        try:
            if table_name not in self._verified_hy_tables:
                if verify_hy_storage_schema(self.database, table_name):
                    self._verified_hy_tables.add(table_name)
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

        except DatabaseError as e:
            self._records_failed += 1
            logger.error("Failed to insert record", error=str(e))
            return False

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
