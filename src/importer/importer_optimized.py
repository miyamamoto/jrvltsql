"""Optimized data importer for JLTSQL.

This module provides optimized import strategies for different database backends.
Key optimizations:
- Single transaction for entire import
- Uses database-specific bulk insert APIs
- Adaptive batch sizing based on performance
"""

from itertools import chain
from typing import Dict, Iterator, List, Optional, Union

from src.database.base import BaseDatabase, DatabaseError
from src.database.migration import SchemaMigrationError
from src.importer.importer import (
    _ORDERED_MASTER_STORAGE_TABLES,
    _PREPARED_CH_SEISEKI_ROWS_KEY,
    _PREPARED_CK_ROWS_KEY,
    _PREPARED_KS_SEISEKI_ROWS_KEY,
    _PROVIDER_OPERATION_COUNT_STORAGE_TABLES,
    _RC_STORAGE_TABLES,
    _STANDARD_ODDS_CONFIG_BY_OWNER,
    _STANDARD_VOTE_CONFIG_BY_OWNER,
    _STRICT_NONADDITIVE_STANDARD_TABLES,
    _TK_CHILD_STORAGE_TABLES,
    _WF_NATIVE_STORAGE_TABLES,
    _WF_STANDARD_STORAGE_TABLES,
    _YS_STORAGE_TABLES,
    TransactionRecoveryError,
    _ck_child_tables,
    _delete_mining_race_rows,
    _delete_official_record,
    _expanded_record_fingerprint,
    _is_mining_race_delete,
    _is_mining_snapshot_follower,
    _is_official_record_erase,
    _is_standard_odds_record_erase,
    _is_standard_vote_record_erase,
    _mining_native_snapshot_rows,
    _rollback_call_created_validation_transactions,
    _snapshot_validation_transactions,
    _standard_odds_physical_fingerprint,
    _standard_vote_physical_fingerprint,
    apply_rc_batch,
    apply_ys_batch,
    clean_record_metadata,
    delete_standard_odds_record,
    delete_standard_vote_record,
    insert_ch_coupled_batch,
    insert_ck_coupled_batch,
    insert_ks_coupled_batch,
    insert_standard_odds_batch,
    insert_standard_vote_batch,
    insert_tk_coupled_batch,
    insert_wf_native_batch,
    insert_wf_standard_batch,
    inspect_pending_transaction_or_invalidate,
    preflight_standard_schema_migrations,
    prepare_ch_coupled_rows,
    prepare_ck_coupled_rows,
    prepare_ks_coupled_rows,
    prepare_tk_coupled_record,
    prepare_wf_standard_record,
    replace_mining_native_snapshot,
    resolve_standard_storage_table_name,
    resolve_standard_table_name,
    rollback_failed_import,
    validate_av_record,
    validate_cc_record,
    validate_hc_record,
    validate_hn_record,
    validate_hr_record,
    validate_hs_record,
    validate_import_record_header,
    validate_jc_record,
    validate_jg_record,
    validate_se_record,
    validate_sk_record,
    validate_h1_record,
    validate_um_record,
    validate_tc_record,
    validate_wc_record,
    validate_we_record,
    validate_wf_record,
    verify_av_storage_schema,
    verify_bt_storage_schema,
    verify_cc_storage_schema,
    verify_ch_coupled_table,
    verify_ck_coupled_tables,
    verify_cs_storage_schema,
    verify_hc_storage_schema,
    verify_hn_storage_schema,
    verify_hr_storage_schema,
    verify_hs_storage_schema,
    verify_hy_storage_schema,
    verify_jc_storage_schema,
    verify_jg_storage_schema,
    verify_ks_coupled_table,
    verify_mining_native_schema,
    verify_rc_storage_schema,
    verify_se_storage_schema,
    verify_sk_storage_schema,
    verify_tc_storage_schema,
    verify_tk_coupled_tables,
    verify_h1_storage_schema,
    verify_um_storage_schema,
    verify_wc_storage_schema,
    verify_we_storage_schema,
    verify_wf_storage_schema,
    verify_ys_storage_schema,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OptimizedDataImporter:
    """Optimized importer for JV-Data records.

    Handles batch insertion with database-specific optimizations:
    - PostgreSQL: Uses autocommit mode (already optimized)
    - SQLite: Uses transaction batching

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
        """Initialize optimized data importer."""
        self.database = database
        self.batch_size = batch_size
        self.use_jravan_schema = use_jravan_schema

        self._records_imported = 0
        self._records_failed = 0
        self._batches_processed = 0
        self._jravan_tables_ready = not use_jravan_schema
        self._verified_mining_native_tables: set[str] = set()
        self._verified_hy_tables: set[str] = set()
        self._verified_bt_tables: set[str] = set()
        self._verified_se_tables: set[str] = set()
        self._verified_we_tables: set[str] = set()
        self._verified_av_tables: set[str] = set()
        self._verified_hr_tables: set[str] = set()
        self._verified_hs_tables: set[str] = set()
        self._verified_hc_tables: set[str] = set()
        self._verified_hn_tables: set[str] = set()
        self._verified_sk_tables: set[str] = set()
        self._verified_tc_tables: set[str] = set()
        self._verified_cc_tables: set[str] = set()
        self._verified_jc_tables: set[str] = set()
        self._verified_cs_tables: set[str] = set()
        self._verified_um_tables: set[str] = set()
        self._verified_h1_tables: set[str] = set()
        self._verified_jg_tables: set[str] = set()
        self._verified_wc_tables: set[str] = set()
        self._verified_wf_tables: set[str] = set()
        self._verified_ck_child_tables: dict[str, tuple[str, str]] = {}
        self._verified_rc_tables: set[str] = set()
        self._verified_ys_tables: set[str] = set()
        self._verified_tk_header_tables: dict[str, str] = {}
        self._verified_standard_odds_configs: dict[str, tuple[str, dict]] = {}
        self._verified_standard_vote_configs: dict[str, tuple[str, dict]] = {}

        # Detect database type for optimization
        self.db_type = self._detect_database_type()

        # Map record types to table names (same as original)
        self._table_map = {
            "RA": "NL_RA",
            "SE": "NL_SE",
            "HR": "NL_HR",
            "JG": "NL_JG",
            "H1": "NL_H1",
            "H6": "NL_H6",
            "O1": "NL_O1",
            "O2": "NL_O2",
            "O3": "NL_O3",
            "O4": "NL_O4",
            "O5": "NL_O5",
            "O6": "NL_O6",
            "YS": "NL_YS",
            "UM": "NL_UM",
            "KS": "NL_KS",
            "CH": "NL_CH",
            "BR": "NL_BR",
            "BN": "NL_BN",
            "HN": "NL_HN",
            "SK": "NL_SK",
            "RC": "NL_RC",
            "CC": "NL_CC",
            "TC": "NL_TC",
            "CS": "NL_CS",
            "CK": "NL_CK",
            "WC": "NL_WC",
            "AV": "NL_AV",
            "JC": "NL_JC",
            "HC": "NL_HC",
            "HS": "NL_HS",
            "HY": "NL_HY",
            "WE": "NL_WE",
            "WF": "NL_WF",
            "WH": "NL_WH",
            "TM": "NL_TM",
            "TK": "NL_TK",
            "BT": "NL_BT",
            "DM": "NL_DM",
        }

        logger.info(
            "OptimizedDataImporter initialized",
            batch_size=batch_size,
            db_type=self.db_type,
            use_jravan_schema=use_jravan_schema,
        )

    def _migrate_existing_jravan_tables(self, *, commit: bool) -> None:
        """Add newly supported columns to existing standard-name tables."""
        from src.database.migration import migrate_table_if_needed, verify_table_schema
        from src.database.schema_jravan import JRAVAN_SCHEMAS

        native_table_names = set(self._table_map.values())
        preflight_standard_schema_migrations(self.database, native_table_names)
        for native_name in native_table_names:
            standard_name = resolve_standard_storage_table_name(native_name)
            schema_sql = JRAVAN_SCHEMAS.get(standard_name)
            if schema_sql and self.database.table_exists(standard_name):
                if standard_name not in _STRICT_NONADDITIVE_STANDARD_TABLES:
                    migrate_table_if_needed(
                        self.database,
                        standard_name,
                        schema_sql,
                        commit=commit,
                    )
                # Ordered masters receive a complete field/key check only in
                # their dedicated writers. Preflight checks existing types and
                # capacities; a mismatched key makes additive migration a no-op.
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
            from src.importer.importer import ImporterError

            raise ImporterError("JRA-VAN schema import requires a connected database")
        transaction_snapshot = _snapshot_validation_transactions(self.database)
        try:
            self._migrate_existing_jravan_tables(commit=auto_commit)
        except Exception:
            _rollback_call_created_validation_transactions(
                transaction_snapshot,
                context="failed standard-schema preparation",
            )
            raise
        _rollback_call_created_validation_transactions(
            transaction_snapshot,
            context="completed standard-schema preparation",
        )
        if auto_commit:
            self._jravan_tables_ready = True

    def _detect_database_type(self) -> str:
        """Detect database type from handler class."""
        class_name = self.database.__class__.__name__
        if "PostgreSQL" in class_name:
            return "postgresql"
        elif "SQLite" in class_name:
            return "sqlite"
        else:
            return "unknown"

    def _get_table_name(self, record_type: str) -> Optional[str]:
        """Get table name for record type."""
        table_name = self._table_map.get(record_type)
        if not table_name:
            return None

        if self.use_jravan_schema:
            return resolve_standard_table_name(self.database, table_name)

        return table_name

    @staticmethod
    def _clean_record(record: dict) -> dict:
        return clean_record_metadata(record)

    @classmethod
    def _record_for_table(cls, record: dict, table_name: str) -> dict:
        """Return the parser representation required by the target schema."""
        if table_name in {"BATAIJYU", "MINING", "TAISENGATA_MINING"}:
            wide_record = record.get("_wide_record")
            if isinstance(wide_record, dict):
                return cls._clean_record(wide_record)
        from src.importer.importer import translate_standard_field_names

        return translate_standard_field_names(cls._clean_record(record), table_name)

    @staticmethod
    def _convert_record(record: dict, table_name: str) -> dict:
        from src.importer.importer import convert_record_types

        return convert_record_types(record, table_name)

    @staticmethod
    def _has_complete_primary_key(table_name: str, record: dict) -> bool:
        from src.database.schema_types import get_table_primary_key_columns
        from src.database.table_mappings import JRAVAN_TO_JLTSQL

        primary_keys = get_table_primary_key_columns(table_name)
        if not primary_keys:
            primary_keys = get_table_primary_key_columns(
                JRAVAN_TO_JLTSQL.get(table_name, table_name)
            )
        return not primary_keys or all(record.get(key) not in (None, "") for key in primary_keys)

    def import_records(
        self,
        records: Iterator[dict],
        auto_commit: bool = True,
    ) -> Dict[str, int]:
        """Import records with database-specific optimizations.

        For PostgreSQL: Already optimized with autocommit
        For SQLite: Uses transaction batching

        Args:
            records: Iterator of parsed record dictionaries
            auto_commit: Whether to auto-commit

        Returns:
            Dictionary with import statistics
        """
        previous_statistics = (
            self._records_imported,
            self._records_failed,
            self._batches_processed,
        )
        previous_transaction_generation = self.database.get_transaction_generation()

        self._records_imported = 0
        self._records_failed = 0
        self._batches_processed = 0

        records = iter(records)
        exhausted = object()
        try:
            first_record = next(records, exhausted)
            if first_record is not exhausted:
                first_record_type, _ = validate_import_record_header(first_record)
                first_table_name = self._get_table_name(first_record_type)
                if first_table_name is not None:
                    validate_se_record(first_record, first_table_name)
                    validate_we_record(first_record, first_table_name)
                    validate_av_record(first_record, first_table_name)
                    validate_hr_record(first_record, first_table_name)
                    validate_hs_record(first_record, first_table_name)
                    validate_hc_record(first_record, first_table_name)
                    validate_hn_record(first_record, first_table_name)
                    validate_sk_record(first_record, first_table_name)
                    validate_jc_record(first_record, first_table_name)
                records = chain((first_record,), records)
        except Exception:
            if not auto_commit:
                try:
                    pending_transaction = inspect_pending_transaction_or_invalidate(
                        self.database,
                        context="first-header failure in optimized caller-owned import",
                    )
                except TransactionRecoveryError:
                    if (
                        self.database.is_connected()
                        and previous_transaction_generation is not None
                    ):
                        (
                            self._records_imported,
                            self._records_failed,
                            self._batches_processed,
                        ) = previous_statistics
                    else:
                        self._records_imported = 0
                        self._records_failed = 0
                        self._batches_processed = 0
                    raise
                if pending_transaction:
                    rollback_failed_import(
                        self.database,
                        context="first-header failure in optimized caller-owned import",
                    )
                self._records_imported = 0
                self._records_failed = 0
                self._batches_processed = 0
            raise

        if not auto_commit:
            self.database.begin_transaction()
        try:
            self._ensure_jravan_tables_ready(auto_commit=auto_commit)
        except Exception:
            if not auto_commit:
                rollback_failed_import(
                    self.database,
                    context="optimized standard-schema preflight in caller-owned import",
                )
            raise

        # Group records by type for batch insertion
        batch_buffers: Dict[str, List[dict]] = {}
        standard_odds_fingerprints: dict[str, tuple] = {}
        standard_vote_fingerprints: dict[str, tuple] = {}
        verified_ch_result_tables: Dict[str, str] = {}
        verified_ks_result_tables: Dict[str, str] = {}
        last_expanded_record_fingerprint = None

        try:
            for record in records:
                record_type, _ = validate_import_record_header(record)
                # Get record type and table name
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
                if table_name not in self._verified_se_tables:
                    if verify_se_storage_schema(self.database, table_name):
                        self._verified_se_tables.add(table_name)
                validate_se_record(record, table_name)
                if table_name not in self._verified_we_tables:
                    if verify_we_storage_schema(self.database, table_name):
                        self._verified_we_tables.add(table_name)
                validate_we_record(record, table_name)
                if table_name not in self._verified_av_tables:
                    if verify_av_storage_schema(self.database, table_name):
                        self._verified_av_tables.add(table_name)
                validate_av_record(record, table_name)
                if table_name not in self._verified_hr_tables:
                    if verify_hr_storage_schema(self.database, table_name):
                        self._verified_hr_tables.add(table_name)
                validate_hr_record(record, table_name)
                if table_name not in self._verified_hs_tables:
                    if verify_hs_storage_schema(self.database, table_name):
                        self._verified_hs_tables.add(table_name)
                validate_hs_record(record, table_name)
                if table_name not in self._verified_hc_tables:
                    if verify_hc_storage_schema(self.database, table_name):
                        self._verified_hc_tables.add(table_name)
                validate_hc_record(record, table_name)
                if table_name not in self._verified_hn_tables:
                    if verify_hn_storage_schema(self.database, table_name):
                        self._verified_hn_tables.add(table_name)
                validate_hn_record(record, table_name)
                if table_name not in self._verified_sk_tables:
                    if verify_sk_storage_schema(self.database, table_name):
                        self._verified_sk_tables.add(table_name)
                validate_sk_record(record, table_name)
                if table_name not in self._verified_tc_tables:
                    if verify_tc_storage_schema(self.database, table_name):
                        self._verified_tc_tables.add(table_name)
                validate_tc_record(record, table_name)
                if table_name not in self._verified_cc_tables:
                    if verify_cc_storage_schema(self.database, table_name):
                        self._verified_cc_tables.add(table_name)
                validate_cc_record(record, table_name)
                if table_name not in self._verified_jc_tables:
                    if verify_jc_storage_schema(self.database, table_name):
                        self._verified_jc_tables.add(table_name)
                validate_jc_record(record, table_name)
                if table_name not in self._verified_cs_tables:
                    if verify_cs_storage_schema(self.database, table_name):
                        self._verified_cs_tables.add(table_name)
                if table_name not in self._verified_um_tables:
                    if verify_um_storage_schema(self.database, table_name):
                        self._verified_um_tables.add(table_name)
                validate_um_record(record, table_name)
                if table_name not in self._verified_h1_tables:
                    if verify_h1_storage_schema(self.database, table_name):
                        self._verified_h1_tables.add(table_name)
                validate_h1_record(record, table_name)
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

                if table_name not in self._verified_mining_native_tables:
                    if verify_mining_native_schema(self.database, record, table_name):
                        self._verified_mining_native_tables.add(table_name)

                if _is_standard_vote_record_erase(record, table_name):
                    pending = batch_buffers.setdefault(table_name, [])
                    if pending:
                        self._flush_batch_optimized(
                            table_name,
                            pending,
                            commit_batch=auto_commit,
                        )
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
                        self._flush_batch_optimized(
                            table_name,
                            pending,
                            commit_batch=auto_commit,
                        )
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
                        self._flush_batch_optimized(
                            table_name,
                            pending,
                            commit_batch=auto_commit,
                        )
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
                        self._flush_batch_optimized(
                            table_name,
                            pending,
                            commit_batch=auto_commit,
                        )
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
                        self._flush_batch_optimized(
                            table_name,
                            pending,
                            commit_batch=auto_commit,
                        )
                        batch_buffers[table_name] = []
                    if auto_commit:
                        self.database.begin_transaction()
                    try:
                        rows = replace_mining_native_snapshot(
                            self.database, record, table_name
                        )
                        if auto_commit:
                            self.database.commit()
                    except TransactionRecoveryError:
                        raise
                    except Exception:
                        self.database.rollback()
                        raise
                    self._records_imported += rows
                    self._batches_processed += 1
                    continue

                if (
                    table_name in _TK_CHILD_STORAGE_TABLES
                    or table_name in _WF_STANDARD_STORAGE_TABLES
                ):
                    # Coupled parent/child writers prepare the raw record at
                    # flush time so header conversion cannot drop child payload.
                    if table_name not in batch_buffers:
                        batch_buffers[table_name] = []
                    batch_buffers[table_name].append(record)
                    if len(batch_buffers[table_name]) >= self.batch_size:
                        self._flush_batch_optimized(
                            table_name,
                            batch_buffers[table_name],
                            commit_batch=auto_commit,
                        )
                        batch_buffers[table_name] = []
                    continue

                if table_name in _STANDARD_VOTE_CONFIG_BY_OWNER:
                    fingerprint = _standard_vote_physical_fingerprint(
                        record,
                        table_name,
                    )
                    pending = batch_buffers.setdefault(table_name, [])
                    previous = standard_vote_fingerprints.get(table_name)
                    if pending and previous != fingerprint:
                        self._flush_batch_optimized(
                            table_name,
                            pending,
                            commit_batch=auto_commit,
                        )
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
                        self._flush_batch_optimized(
                            table_name,
                            pending,
                            commit_batch=auto_commit,
                        )
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

                clean_record = self._record_for_table(record, table_name)
                converted_record = self._convert_record(clean_record, table_name)
                if (
                    table_name not in _ORDERED_MASTER_STORAGE_TABLES
                    and not self._has_complete_primary_key(table_name, converted_record)
                ):
                    logger.warning(
                        "Record has incomplete primary key after conversion",
                        table=table_name,
                    )
                    self._records_failed += 1
                    continue
                if (
                    table_name in ("NL_CH", "CHOKYO")
                    and table_name not in verified_ch_result_tables
                ):
                    try:
                        result_table = verify_ch_coupled_table(self.database, table_name)
                    except DatabaseError as error:
                        if not auto_commit:
                            raise
                        logger.warning(
                            "CH result schema verification failed, retrying coupled import",
                            table=table_name,
                            error=str(error),
                        )
                        self.database.rollback()
                        result_table = verify_ch_coupled_table(self.database, table_name)
                    if result_table is None:
                        raise SchemaMigrationError(
                            f"CH import could not resolve normalized table for {table_name}"
                        )
                    verified_ch_result_tables[table_name] = result_table
                if table_name in ("NL_KS", "KISYU") and table_name not in verified_ks_result_tables:
                    try:
                        result_table = verify_ks_coupled_table(self.database, table_name)
                    except DatabaseError as error:
                        if not auto_commit:
                            raise
                        logger.warning(
                            "KS result schema verification failed, retrying coupled import",
                            table=table_name,
                            error=str(error),
                        )
                        self.database.rollback()
                        result_table = verify_ks_coupled_table(self.database, table_name)
                    if result_table is None:
                        raise SchemaMigrationError(
                            f"KS import could not resolve normalized table for {table_name}"
                        )
                    verified_ks_result_tables[table_name] = result_table
                if (
                    _ck_child_tables(table_name) is not None
                    and table_name not in self._verified_ck_child_tables
                ):
                    child_tables = verify_ck_coupled_tables(self.database, table_name)
                    if child_tables is None:
                        raise SchemaMigrationError(
                            f"CK import could not resolve normalized children for {table_name}"
                        )
                    self._verified_ck_child_tables[table_name] = child_tables
                coupled = prepare_ch_coupled_rows(
                    self.database,
                    record,
                    table_name,
                    verified_result_table=verified_ch_result_tables.get(table_name),
                )
                if coupled is not None:
                    converted_record[_PREPARED_CH_SEISEKI_ROWS_KEY] = coupled
                ks_coupled = prepare_ks_coupled_rows(
                    self.database,
                    record,
                    table_name,
                    verified_result_table=verified_ks_result_tables.get(table_name),
                )
                if ks_coupled is not None:
                    converted_record[_PREPARED_KS_SEISEKI_ROWS_KEY] = ks_coupled
                ck_coupled = prepare_ck_coupled_rows(
                    self.database,
                    record,
                    table_name,
                    converted_record,
                    verified_child_tables=self._verified_ck_child_tables.get(table_name),
                )
                if ck_coupled is not None:
                    converted_record[_PREPARED_CK_ROWS_KEY] = ck_coupled
                batch_buffers[table_name].append(converted_record)

                # Check if any batch is full
                if len(batch_buffers[table_name]) >= self.batch_size:
                    self._flush_batch_optimized(
                        table_name,
                        batch_buffers[table_name],
                        commit_batch=auto_commit,
                    )
                    batch_buffers[table_name] = []

            # Flush remaining batches
            for table_name, batch in batch_buffers.items():
                if batch:
                    self._flush_batch_optimized(table_name, batch, commit_batch=auto_commit)

            # Log summary
            stats = self.get_statistics()
            logger.info("Import completed", **stats)

            return stats

        except TransactionRecoveryError:
            raise
        except SchemaMigrationError:
            if not auto_commit:
                rollback_failed_import(
                    self.database,
                    context="validation/schema failure in optimized caller-owned import",
                )
                self._records_imported = 0
                self._records_failed = 0
                self._batches_processed = 0
            raise
        except Exception as e:
            if not auto_commit:
                rollback_failed_import(
                    self.database,
                    context="unexpected failure in optimized caller-owned import",
                )
                self._records_imported = 0
                self._records_failed = 0
                self._batches_processed = 0
            logger.error("Import failed", error=str(e))

            from src.importer.importer import ImporterError

            raise ImporterError(f"Failed to import records: {e}")

    def _flush_batch_optimized(
        self,
        table_name: str,
        batch: List[dict],
        commit_batch: bool,
    ):
        """Flush a batch with database-specific optimizations."""
        if not batch:
            return

        if table_name in _RC_STORAGE_TABLES:
            # RC validation/write failures propagate directly and never enter
            # the generic per-row fallback below.
            rows = apply_rc_batch(
                self.database,
                table_name,
                batch,
                commit_batch=commit_batch,
                optimized=True,
            )
            self._records_imported += rows
            if rows:
                self._batches_processed += 1
            return

        if table_name in _YS_STORAGE_TABLES:
            # YS validation/write failures propagate directly and never enter
            # the generic per-row fallback below.
            rows = apply_ys_batch(
                self.database,
                table_name,
                batch,
                commit_batch=commit_batch,
                optimized=True,
            )
            self._records_imported += rows
            if rows:
                self._batches_processed += 1
            return

        if table_name in _STANDARD_VOTE_CONFIG_BY_OWNER:
            rows = insert_standard_vote_batch(
                self.database,
                table_name,
                batch,
                commit_batch=commit_batch,
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
                commit_batch=commit_batch,
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
                commit_batch=commit_batch,
                optimized=True,
            )
            self._records_imported += succeeded
            self._records_failed += failed
            if succeeded:
                self._batches_processed += 1
            return

        if table_name in _WF_STANDARD_STORAGE_TABLES:
            # WF standard failures propagate directly and never enter the
            # generic per-row fallback below.
            prepared_wf = [prepare_wf_standard_record(record) for record in batch]
            succeeded, failed = insert_wf_standard_batch(
                self.database,
                prepared_wf,
                commit_batch=commit_batch,
                optimized=True,
            )
            self._records_imported += succeeded
            self._records_failed += failed
            if succeeded:
                self._batches_processed += 1
            return

        prepared_ch = []
        for record in batch:
            coupled = record.get(_PREPARED_CH_SEISEKI_ROWS_KEY)
            if coupled is None:
                continue
            result_table, result_rows = coupled
            main_row = {
                key: value for key, value in record.items() if key != _PREPARED_CH_SEISEKI_ROWS_KEY
            }
            prepared_ch.append((main_row, result_table, result_rows))
        if prepared_ch:
            if len(prepared_ch) != len(batch):
                raise SchemaMigrationError("CH batch lost its coupled result rows")
            succeeded, failed = insert_ch_coupled_batch(
                self.database,
                table_name,
                prepared_ch,
                commit_batch=commit_batch,
                optimized=True,
            )
            self._records_imported += succeeded
            self._records_failed += failed
            if succeeded:
                self._batches_processed += 1
            return

        prepared_ck = []
        for record in batch:
            coupled = record.get(_PREPARED_CK_ROWS_KEY)
            if coupled is None:
                continue
            chaku_table, chaku_rows, ruikei_table, ruikei_rows = coupled
            main_row = {key: value for key, value in record.items() if key != _PREPARED_CK_ROWS_KEY}
            prepared_ck.append((main_row, chaku_table, chaku_rows, ruikei_table, ruikei_rows))
        if prepared_ck:
            if len(prepared_ck) != len(batch):
                raise SchemaMigrationError("CK batch lost its coupled child rows")
            succeeded, failed = insert_ck_coupled_batch(
                self.database,
                table_name,
                prepared_ck,
                commit_batch=commit_batch,
                optimized=True,
            )
            self._records_imported += succeeded
            self._records_failed += failed
            if succeeded:
                self._batches_processed += 1
            return

        prepared_ks = []
        for record in batch:
            coupled = record.get(_PREPARED_KS_SEISEKI_ROWS_KEY)
            if coupled is None:
                continue
            result_table, result_rows = coupled
            main_row = {
                key: value for key, value in record.items() if key != _PREPARED_KS_SEISEKI_ROWS_KEY
            }
            prepared_ks.append((main_row, result_table, result_rows))
        if prepared_ks:
            if len(prepared_ks) != len(batch):
                raise SchemaMigrationError("KS batch lost its coupled result rows")
            succeeded, failed = insert_ks_coupled_batch(
                self.database,
                table_name,
                prepared_ks,
                commit_batch=commit_batch,
                optimized=True,
            )
            self._records_imported += succeeded
            self._records_failed += failed
            if succeeded:
                self._batches_processed += 1
            return

        if table_name in _WF_NATIVE_STORAGE_TABLES:
            rows = insert_wf_native_batch(
                self.database,
                table_name,
                batch,
                commit_batch=commit_batch,
                optimized=True,
            )
            self._records_imported += rows
            if rows:
                self._batches_processed += 1
            return

        try:
            # Use optimized insert if available
            if hasattr(self.database, "insert_many_optimized"):
                # Optimized path
                affected_rows = self.database.insert_many_optimized(table_name, batch)
            else:
                # Standard insert_many
                affected_rows = self.database.insert_many(table_name, batch)

            # PostgreSQL collapses same-key replacement operations before one upsert.
            # Statistics count accepted provider operations, not final rows.
            rows = (
                len(batch)
                if table_name in _PROVIDER_OPERATION_COUNT_STORAGE_TABLES
                else affected_rows
            )

            self._records_imported += rows
            self._batches_processed += 1

            # Only commit if not in a larger transaction
            if commit_batch:
                self.database.commit()

            logger.debug(
                "Batch inserted",
                table=table_name,
                records=rows,
                batch_num=self._batches_processed,
            )

        except DatabaseError as e:
            if not commit_batch:
                # The backend may already have rolled back the caller-owned
                # transaction. Retrying rows here would create a partial import
                # and make the reported statistics diverge from persisted data.
                raise

            # Try inserting one by one on batch failure
            logger.warning(
                "Batch insert failed, trying individual inserts",
                table=table_name,
                error=str(e),
            )

            for record in batch:
                try:
                    self.database.insert(table_name, record)
                    self._records_imported += 1

                    if commit_batch:
                        self.database.commit()

                except DatabaseError as e:
                    self._records_failed += 1
                    logger.error(
                        "Failed to insert record",
                        table=table_name,
                        error=str(e),
                    )

    def get_statistics(self) -> Dict[str, Union[int, float]]:
        """Get import statistics."""
        return {
            "records_imported": self._records_imported,
            "records_failed": self._records_failed,
            "batches_processed": self._batches_processed,
            "success_rate": (
                self._records_imported * 100 / (self._records_imported + self._records_failed)
                if (self._records_imported + self._records_failed) > 0
                else 0
            ),
        }
