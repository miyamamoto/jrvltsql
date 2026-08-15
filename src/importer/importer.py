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


def resolve_standard_table_name(database: BaseDatabase, native_table_name: str) -> str:
    """Resolve a canonical standard table and reject unsupported legacy-only storage."""
    from src.database.table_mappings import JLTSQL_TO_JRAVAN

    standard_name = JLTSQL_TO_JRAVAN.get(native_table_name, native_table_name)
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


def _expanded_record_fingerprint(record: dict, table_name: str) -> Optional[tuple]:
    """Identify duplicate expanded rows that share one official wide record."""
    if table_name != "BATAIJYU":
        return None
    wide_record = record.get("_wide_record")
    if not isinstance(wide_record, dict):
        return None
    return tuple(sorted((str(key), repr(value)) for key, value in wide_record.items()))


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

    schema_sql = SCHEMAS.get(result_table) or JRAVAN_SCHEMAS.get(result_table)
    if not schema_sql or not database.table_exists_strict(result_table):
        raise SchemaMigrationError(
            f"CH import requires normalized result table {result_table} before mutation"
        )
    verify_table_schema(database, result_table, schema_sql)
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
            "RC": "NL_RC",  # レースコメント
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
            "TM": "NL_TM",  # タイムマスター
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
            "RT_TM": "RT_TM",  # タイムマスター（速報）
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
                verify_table_schema(self.database, standard_name, schema_sql)
        child_schema = JRAVAN_SCHEMAS.get("CHOKYO_SEISEKI")
        if child_schema and self.database.table_exists("CHOKYO_SEISEKI"):
            migrate_table_if_needed(
                self.database,
                "CHOKYO_SEISEKI",
                child_schema,
                commit=commit,
            )
            verify_table_schema(self.database, "CHOKYO_SEISEKI", child_schema)

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
        from src.database.table_mappings import JLTSQL_TO_JRAVAN

        return JLTSQL_TO_JRAVAN.get(table_name, table_name)

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
        # Fields used for routing/metadata that shouldn't be in database tables
        metadata_fields = {
            "headRecordSpec",
            "レコード種別ID",
            "_raw_data",
            "_parse_errors",
            "RecordDelimiter",
            "RecordSeparator",
        }

        return {
            k: v for k, v in record.items() if k not in metadata_fields and not k.startswith("_")
        }

    def _record_for_table(self, record: dict, table_name: str) -> dict:
        """Return the parser representation required by the target schema."""
        if table_name == "BATAIJYU":
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
        last_expanded_record_fingerprint = None

        try:
            for record in records:
                # Get record type and table name
                # Note: Japanese parsers use 'レコード種別ID', JRA-VAN standard uses 'RecordSpec'
                record_type = (
                    record.get("レコード種別ID")
                    or record.get("RecordSpec")
                    or record.get("headRecordSpec")
                )
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

        try:
            # Clean records to remove metadata fields before insertion
            clean_batch = [self._record_for_table(record, table_name) for record in batch]
            # Convert types based on schema definition
            converted_batch = []
            prepared_ch: list[tuple[dict, str, list[dict]]] = []
            for original_record, record in zip(batch, clean_batch, strict=True):
                converted_record = self._convert_record(record, table_name)
                if self._has_complete_primary_key(table_name, converted_record):
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
                else:
                    self._records_failed += 1
                    logger.warning(
                        "Skipping record with incomplete primary key",
                        table=table_name,
                        primary_key=get_table_primary_key_columns(table_name),
                    )

            if not converted_batch:
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
            if _ch_result_table_name(table_name) is not None:
                # Coupled CH writes must never enter the parent-only fallback.
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
        record_type = (
            record.get("レコード種別ID") or record.get("RecordSpec") or record.get("headRecordSpec")
        )
        if not record_type:
            logger.warning("Record missing record type field")
            return False

        table_name = self._get_table_name(record_type)
        if not table_name:
            logger.warning(f"Unknown record type: {record_type}")
            return False

        try:
            clean_record = self._record_for_table(record, table_name)
            converted_record = self._convert_record(clean_record, table_name)
            if not self._has_complete_primary_key(table_name, converted_record):
                self._records_failed += 1
                logger.warning(
                    "Skipping record with incomplete primary key",
                    table=table_name,
                    primary_key=get_table_primary_key_columns(table_name),
                )
                return False
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
