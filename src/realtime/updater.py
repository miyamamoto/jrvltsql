"""Real-time data updater for JLTSQL.

This module handles real-time data updates to the database.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from src.database.base import BaseDatabase
from src.database.migration import SchemaMigrationError
from src.database.schema_types import get_table_primary_key_columns
from src.importer.importer import (
    CANCELLATION_STATE_RECORD_TYPES,
    clean_record_metadata,
    insert_wf_native_batch,
    resolve_record_data_kubun,
    resolve_record_type,
    validate_wf_record,
    verify_wf_storage_schema,
)
from src.jvlink.constants import (
    DATA_KUBUN_DELETE,
    DATA_KUBUN_ERASE,
    DATA_KUBUN_NEW,
    DATA_KUBUN_REFRESH,
    DATA_KUBUN_REREGISTER,
    DATA_KUBUN_UPDATE,
)
from src.parser.factory import ParserFactory
from src.utils.logger import get_logger

logger = get_logger(__name__)


def summarize_update_result(result) -> tuple[List[Dict], int]:
    """Return successful operations and the number of rejected operations."""
    items = result if isinstance(result, list) else [result]
    if not items:
        return [], 1
    successful = [
        item
        for item in items
        if isinstance(item, dict) and item.get("success") is True
    ]
    return successful, len(items) - len(successful)


class RealtimeUpdater:
    """Real-time data updater.

    Processes real-time data records and updates the database
    based on headDataKubun (new/update/delete).

    Examples:
        >>> from src.database.sqlite_handler import SQLiteDatabase
        >>> from src.realtime.updater import RealtimeUpdater
        >>>
        >>> db = SQLiteDatabase({"path": "./keiba.db"})
        >>> with db:
        ...     updater = RealtimeUpdater(db)
        ...     result = updater.process_record(buff)
    """

    # Table mapping from record type to RT_ tables (Real-Time data)
    # Real-time updates use RT_ prefix, historical data uses NL_ prefix
    #
    # JVRTOpen provides two categories of data:
    # - 速報系データ (0B1x): 馬体重、レース、開催変更、マイニング
    # - 時系列データ (0B2x-0B3x): 継続更新オッズ・票数
    RECORD_TYPE_TABLE = {
        # === 速報系データ (Speed Report - 0B1x) ===
        # 0B11: 速報馬体重
        "WH": "RT_WH",  # 馬体重

        # 0B12/0B15: レース情報・払戻
        "RA": "RT_RA",  # レース詳細
        "SE": "RT_SE",  # 馬毎レース情報
        "HR": "RT_HR",  # 払戻

        # 0B13: データマイニング予想
        "DM": "RT_DM",  # データマイニング（タイム型）

        # 0B14/0B16: 速報開催情報
        "WE": "RT_WE",  # 天候・馬場状態
        "AV": "RT_AV",  # 出走取消・競走除外
        "JC": "RT_JC",  # 騎手変更
        "TC": "RT_TC",  # 発走時刻変更
        "CC": "RT_CC",  # コース変更

        # 0B17: 対戦型データマイニング予想
        "TM": "RT_TM",  # データマイニング（対戦型）

        # 0B51: 速報重勝式 (WIN5)
        "WF": "RT_WF",

        # === オッズ/票数データ ===
        # 0B20: 票数情報
        "H1": "RT_H1",  # 票数（単勝・複勝等）
        "H6": "RT_H6",  # 票数（３連単）

        # 0B30-0B36: 速報オッズ、0B41/0B42: 公式1年保持の時系列オッズ
        "O1": "RT_O1",  # オッズ（単勝・複勝・枠連）
        "O2": "RT_O2",  # オッズ（馬連）
        "O3": "RT_O3",  # オッズ（ワイド）
        "O4": "RT_O4",  # オッズ（馬単）
        "O5": "RT_O5",  # オッズ（３連複）
        "O6": "RT_O6",  # オッズ（３連単）

        # === 変更情報データ ===
        "RC": "RT_RC",
    }

    DATE_SNAPSHOT_TABLES = (
        "RT_WE",
        "RT_AV",
        "RT_JC",
        "RT_TC",
        "RT_CC",
    )

    def replace_date_snapshot(self, date_key: str) -> None:
        """Clear the previous 0B14 snapshot for one race date.

        JRA-VAN 0B14 is a complete current snapshot. Withdrawn changes are
        omitted from later responses, so upserts alone leave stale rows.
        Call this only after JVRTOpen succeeds and inside the same transaction
        as the replacement inserts.
        """
        if len(date_key) != 8 or not date_key.isdigit():
            raise ValueError(f"Invalid 0B14 date key: {date_key!r}")
        year = int(date_key[:4])
        month_day = int(date_key[4:])
        for table_name in self.DATE_SNAPSHOT_TABLES:
            self.database.execute(
                f"DELETE FROM {table_name} WHERE Year = ? AND MonthDay = ?",
                (year, month_day),
            )

    SOKUHO_TIMESERIES_SPECS = {
        "0B30",
        "0B31",
        "0B32",
        "0B33",
        "0B34",
        "0B35",
        "0B36",
    }

    # 公式1年保持の時系列オッズ専用テーブルマッピング (TS_O1/TS_O2)。
    # O3-O6は既存DBとの互換用に残すが、新規の速報保存には使わない。
    # HassoTimeをPRIMARY KEYに含めて複数時点のデータを保持
    TIMESERIES_RECORD_TYPE_TABLE = {
        "O1": "TS_O1",  # 単複枠オッズ時系列
        "O2": "TS_O2",  # 馬連オッズ時系列
        "O3": "TS_O3",  # ワイドオッズ時系列
        "O4": "TS_O4",  # 馬単オッズ時系列
        "O5": "TS_O5",  # 三連複オッズ時系列
        "O6": "TS_O6",  # 三連単オッズ時系列
    }

    # 開催週速報オッズ専用テーブルマッピング (TS_SOKUHO_O1-O6)
    # 0B30-0B36は公式長期時系列と保持期間も意味も異なるため分離する。
    SOKUHO_TIMESERIES_RECORD_TYPE_TABLE = {
        "O1": "TS_SOKUHO_O1",
        "O2": "TS_SOKUHO_O2",
        "O3": "TS_SOKUHO_O3",
        "O4": "TS_SOKUHO_O4",
        "O5": "TS_SOKUHO_O5",
        "O6": "TS_SOKUHO_O6",
    }

    # Note: The following record types are NOT provided in real-time:
    # - TK (特別登録馬) - Accumulated data only
    # - UM, KS, CH, BR, BN, HN, SK (Master data) - Updated via DIFN
    # - CK, HC, HS, HY (Code/Status data) - Updated via SNPN
    # - YS, BT, CS (Change data) - Updated via YSCH, SLOP, etc.
    # - JG, WC - Not in the supported realtime stream

    def __init__(self, database: BaseDatabase, cache_manager=None):
        """Initialize real-time updater.

        Args:
            database: Database handler instance
            cache_manager: Optional CacheManager for writing RT records to local cache
        """
        self.database = database
        self.parser_factory = ParserFactory()
        self.cache_manager = cache_manager
        self._verified_mining_native_tables: set[str] = set()
        self._verified_wf_tables: set[str] = set()

        logger.info("RealtimeUpdater initialized")

    # Realtime tables whose caller-built rows are revalidated against the
    # official contract before any coercion or mutation.
    STRICT_RECORD_TABLES = frozenset({"RT_WF"})

    def _canonicalize_strict_record_aliases(
        self, record: Dict
    ) -> tuple[Optional[str], Optional[str]]:
        """Canonicalize aliases needed to route a strict realtime record.

        Returns ``(record_type, error)``. Conflicts and missing WF status stay
        explicit validation failures; they are never defaulted to a live row.
        """
        try:
            record_type = resolve_record_type(record)
        except SchemaMigrationError as error:
            return None, str(error)
        if record_type != "WF":
            return record_type, None

        record["RecordSpec"] = record_type
        has_status = any(
            record.get(name) not in (None, "")
            for name in ("DataKubun", "headDataKubun")
        )
        if not has_status:
            return record_type, "WF DataKubun is required"
        try:
            record["DataKubun"] = resolve_record_data_kubun(record)
        except ValueError as error:
            return record_type, str(error)
        return record_type, None

    def _reject_strict_record(self, table_name: str, record: Dict) -> Optional[str]:
        """Return a rejection reason for a strict-contract table, else None.

        The physical WF parser already enforces the official layout, but the
        parsed and batch entry points accept dictionaries. Schema verification
        (exact ordered key) and record validation both happen before
        ``convert_record_types`` could strip characters, and every failure is
        reported without touching a row.
        """
        if table_name not in self.STRICT_RECORD_TABLES:
            return None
        try:
            if table_name not in self._verified_wf_tables:
                if verify_wf_storage_schema(self.database, table_name):
                    self._verified_wf_tables.add(table_name)
            validate_wf_record(record, table_name)
        except SchemaMigrationError as error:
            logger.error(f"Rejected realtime {table_name} record: {error}")
            return str(error)
        return None

    def process_record(
        self,
        buff: bytes,
        timeseries: bool = False,
        source_spec: Optional[str] = None,
    ) -> Optional[Union[Dict, List[Dict]]]:
        """Process real-time data record.

        Args:
            buff: Raw JV-Data record buffer (bytes)
            timeseries: If True, save odds data to official TS_O* or
                       sokuho TS_SOKUHO_O* tables instead of RT_O* tables.
                       This preserves odds history with HassoTime as part of
                       the primary key.

        Returns:
            Dictionary or list of dictionaries with processing result, or None if failed

        Raises:
            Exception: If processing fails
        """
        try:
            # Parse record
            parsed_data = self.parser_factory.parse(buff)
            if not parsed_data:
                logger.warning("Failed to parse record")
                return None

            # Write to RT cache if enabled
            if self.cache_manager and buff:
                from datetime import date
                today = date.today().strftime("%Y%m%d")
                # Use RecordSpec to determine spec_code bucket
                spec = (parsed_data[0].get("RecordSpec") if isinstance(parsed_data, list) else parsed_data.get("RecordSpec")) if parsed_data else None
                if spec:
                    self.cache_manager.write_rt_record(spec, today, buff)

            return self.process_parsed_record(
                parsed_data,
                timeseries=timeseries,
                source_spec=source_spec,
            )

        except Exception as e:
            logger.error(f"Error processing record: {e}", exc_info=True)
            raise

    def process_parsed_record(
        self,
        parsed_data,
        timeseries: bool = False,
        source_spec: Optional[str] = None,
    ) -> Optional[Union[Dict, List[Dict]]]:
        """Process already parsed JV-Data.

        Batch time-series fetchers may expand one raw JV-Link record into many
        odds rows. Re-processing the raw buffer would duplicate work and insert
        the same expanded record repeatedly, so callers can save the parsed rows
        directly through this method. Returns a list when parsed_data is a list.
        """
        if isinstance(parsed_data, list):
            if parsed_data:
                from src.importer.importer import _mining_native_snapshot_rows

                record_type = parsed_data[0].get("RecordSpec")
                table_name = {"DM": "RT_DM", "TM": "RT_TM"}.get(record_type)
                if table_name is not None:
                    snapshot_rows = _mining_native_snapshot_rows(
                        parsed_data[0], table_name
                    )
                    if snapshot_rows is not None:
                        return self._replace_mining_native_snapshot(
                            parsed_data[0], snapshot_rows, table_name
                        )
            results = []
            for item in parsed_data:
                if timeseries and source_spec:
                    item.setdefault("SourceSpec", source_spec)
                result = self._process_single_record(item, timeseries=timeseries)
                # Keep rejected subrecords as None so fail-closed callers can
                # count every parser expansion, not only successful inserts.
                results.append(result)
            return results

        if timeseries and source_spec:
            parsed_data.setdefault("SourceSpec", source_spec)
        return self._process_single_record(parsed_data, timeseries=timeseries)

    def _replace_mining_native_snapshot(
        self,
        record: Dict,
        snapshot_rows: list[Dict],
        table_name: str,
    ) -> List[Dict]:
        """Replace one complete realtime mining snapshot in the caller transaction."""
        from src.importer.importer import replace_mining_native_snapshot

        record_type = record.get("RecordSpec")
        transaction_active = getattr(self.database, "is_transaction_active", None)
        owns_transaction = not bool(transaction_active()) if callable(transaction_active) else False
        owned_transaction_started = False

        try:
            from src.importer.importer import verify_mining_native_schema

            if owns_transaction:
                self.database.begin_transaction()
                owned_transaction_started = True
            if table_name not in self._verified_mining_native_tables:
                if verify_mining_native_schema(self.database, record, table_name):
                    self._verified_mining_native_tables.add(table_name)
            inserted = replace_mining_native_snapshot(self.database, record, table_name)
            if inserted != len(snapshot_rows):
                raise RuntimeError(
                    f"{table_name} snapshot inserted {inserted} of {len(snapshot_rows)} rows"
                )
            if owns_transaction:
                self.database.commit()
                owned_transaction_started = False
            return [
                {
                    "operation": "insert",
                    "table": table_name,
                    "record_type": record_type,
                    "success": True,
                }
                for _ in snapshot_rows
            ]
        except Exception as exc:
            recovery_error = None
            if owned_transaction_started:
                try:
                    self.database.rollback()
                except Exception as rollback_error:
                    recovery_error = rollback_error
                    try:
                        self.database.invalidate_connection()
                    except Exception as invalidation_error:
                        recovery_error = RuntimeError(
                            f"rollback failed: {rollback_error}; "
                            f"connection invalidation failed: {invalidation_error}"
                        )
            logger.error(f"Failed to replace {table_name} snapshot: {exc}", exc_info=True)
            error = str(exc)
            if recovery_error is not None:
                error = f"{error}; transactional recovery failed: {recovery_error}"
            return [
                {
                    "operation": "insert",
                    "table": table_name,
                    "record_type": record_type,
                    "success": False,
                    "error": error,
                }
                for _ in snapshot_rows
            ]

    def process_parsed_records_batch(self, records: list[Dict], timeseries: bool = False) -> Dict:
        """Insert already parsed records in batches grouped by target table."""
        grouped: dict[str, list[Dict]] = {}
        errors = 0
        batch_collected_at = self._current_collected_at() if timeseries else None
        validated_records: list[Dict] = []
        ordered_mutation_required = False

        for record in records:
            record_type, alias_error = self._canonicalize_strict_record_aliases(record)
            if alias_error is not None:
                logger.warning(f"Skipping record with conflicting header aliases: {alias_error}")
                errors += 1
                continue
            try:
                data_kubun = resolve_record_data_kubun(record)
            except ValueError as exc:
                logger.warning(f"Skipping record with conflicting DataKubun aliases: {exc}")
                errors += 1
                continue
            strict_table = self.RECORD_TYPE_TABLE.get(record_type)
            if (
                strict_table in self.STRICT_RECORD_TABLES
                and self._reject_strict_record(strict_table, record) is not None
            ):
                errors += 1
                continue
            if data_kubun == DATA_KUBUN_ERASE or (
                data_kubun == DATA_KUBUN_DELETE
                and record_type not in CANCELLATION_STATE_RECORD_TYPES
            ):
                ordered_mutation_required = True
            validated_records.append(record)

        if ordered_mutation_required:
            if timeseries and batch_collected_at:
                for record in validated_records:
                    record.setdefault("CollectedAt", batch_collected_at)
            results = [
                self._process_single_record(record, timeseries=timeseries)
                for record in validated_records
            ]
            successful, rejected = summarize_update_result(results)
            tables = sorted(
                {
                    item["table"]
                    for item in successful
                    if item.get("table")
                }
            )
            return {
                "operation": "batch_insert",
                "success": errors + rejected == 0,
                "inserted": len(successful),
                "errors": errors + rejected,
                "tables": tables,
            }

        for record in validated_records:
            if timeseries and batch_collected_at:
                record.setdefault("CollectedAt", batch_collected_at)
            record_type = record.get("RecordSpec")
            table_name = self._resolve_timeseries_table(record) if timeseries else None
            if table_name is None:
                table_name = self.RECORD_TYPE_TABLE.get(record_type)
            if not table_name:
                logger.warning(f"Unknown record type: {record_type}")
                errors += 1
                continue

            clean_data = self._prepare_data_for_db(table_name, record)
            if not self._has_complete_primary_key(table_name, clean_data):
                logger.warning(
                    f"Skipping record with incomplete primary key for {table_name}"
                )
                errors += 1
                continue
            grouped.setdefault(table_name, []).append(clean_data)

        inserted = 0
        for table_name, rows in grouped.items():
            if table_name in self.STRICT_RECORD_TABLES:
                try:
                    inserted += insert_wf_native_batch(
                        self.database,
                        table_name,
                        rows,
                        commit_batch=False,
                        optimized=False,
                    )
                except Exception as exc:
                    logger.error(
                        f"Atomic realtime insert failed for {table_name}: {exc}"
                    )
                    errors += len(rows)
                continue
            inserted_rows, failed_rows = self._insert_rows_resilient(table_name, rows)
            inserted += inserted_rows
            errors += failed_rows

        return {
            "operation": "batch_insert",
            "success": errors == 0,
            "inserted": inserted,
            "errors": errors,
            "tables": sorted(grouped),
        }

    def _resolve_timeseries_table(self, record: Dict) -> Optional[str]:
        """Resolve official vs速報 odds time-series table from source spec."""
        record_type = record.get("RecordSpec")
        if record_type not in self.TIMESERIES_RECORD_TYPE_TABLE:
            return None

        source_spec = str(
            record.get("SourceSpec") or record.get("_SourceSpec") or ""
        ).upper()
        if source_spec in self.SOKUHO_TIMESERIES_SPECS:
            return self.SOKUHO_TIMESERIES_RECORD_TYPE_TABLE.get(record_type)

        # O3-O6 are only available as current-week速報 odds in JRA-VAN RT specs.
        # If older callers omitted SourceSpec, keep these out of official TS_O*.
        if not source_spec and record_type in {"O3", "O4", "O5", "O6"}:
            return self.SOKUHO_TIMESERIES_RECORD_TYPE_TABLE.get(record_type)

        return self.TIMESERIES_RECORD_TYPE_TABLE.get(record_type)

    def _clean_data_for_table(self, table_name: str, data: Dict) -> Dict:
        """Drop parser metadata and coerce values for the target schema."""
        return self._prepare_data_for_db(table_name, data)

    def _insert_rows_resilient(
        self,
        table_name: str,
        rows: list[Dict],
        reconnected: bool = False,
    ) -> tuple[int, int]:
        """Insert rows, splitting batches on timeout/driver failures.

        PostgreSQL can time out on very large odds time-series upserts.
        Dropping a whole 5,000-row odds batch silently corrupts later strategy
        evaluation, so recursively split failed batches and only count
        irreducible single-row failures as errors.
        """
        if not rows:
            return 0, 0

        try:
            self.database.insert_many(table_name, rows)
            return len(rows), 0
        except Exception as exc:
            if not reconnected and self._reconnect_database_after_insert_error(exc):
                return self._insert_rows_resilient(
                    table_name,
                    rows,
                    reconnected=True,
                )

            if len(rows) == 1:
                logger.error(f"Failed to insert row into {table_name}: {exc}")
                return 0, 1

            midpoint = len(rows) // 2
            logger.warning(
                f"Batch insert failed for {table_name}; retrying split batches "
                f"({len(rows)} -> {midpoint}+{len(rows) - midpoint}): {exc}"
            )
            left_inserted, left_failed = self._insert_rows_resilient(table_name, rows[:midpoint])
            right_inserted, right_failed = self._insert_rows_resilient(table_name, rows[midpoint:])
            return left_inserted + right_inserted, left_failed + right_failed

    def _reconnect_database_after_insert_error(self, exc: Exception) -> bool:
        """Reconnect once after driver/network failures before retrying rows."""
        message = str(exc).lower()
        connection_error_markers = (
            "not connected",
            "timed out",
            "timeout",
            "connection",
            "socket",
            "closed",
        )
        if not any(marker in message for marker in connection_error_markers):
            return False

        reconnect = getattr(self.database, "_reconnect", None)
        if reconnect is None:
            reconnect = getattr(self.database, "connect", None)
        if reconnect is None:
            return False

        try:
            logger.warning(f"Database insert failed with connection error; reconnecting: {exc}")
            reconnect()
            return True
        except Exception as reconnect_exc:
            logger.error(f"Database reconnect failed after insert error: {reconnect_exc}")
            return False

    def _process_single_record(self, parsed_data: Dict, timeseries: bool = False) -> Optional[Dict]:
        """Process a single parsed record dict."""
        try:
            record_type, alias_error = self._canonicalize_strict_record_aliases(parsed_data)
            if alias_error is not None:
                return {
                    "operation": "validate",
                    "table": "RT_WF" if record_type == "WF" else None,
                    "record_type": record_type,
                    "success": False,
                    "error": alias_error,
                }
            if not record_type:
                logger.warning("Missing RecordSpec in parsed data")
                return None

            # Get table name. In time-series mode, route official 0B41/0B42
            # and current-week 0B30-0B36速報 odds to separate physical tables.
            table_name = self._resolve_timeseries_table(parsed_data) if timeseries else None
            if table_name is None:
                table_name = self.RECORD_TYPE_TABLE.get(record_type)

            if not table_name:
                logger.warning(f"Unknown record type: {record_type}")
                return None

            from src.importer.importer import verify_mining_native_schema

            if table_name not in self._verified_mining_native_tables:
                if verify_mining_native_schema(self.database, parsed_data, table_name):
                    self._verified_mining_native_tables.add(table_name)

            # DataKubun is record-specific domain state. The legacy flattened
            # name headDataKubun is the same header field, not a second command.
            # For cancellation-capable records, 9 must remain queryable and
            # only the official 0 value requests physical erase.
            record_data_kubun = resolve_record_data_kubun(parsed_data)

            rejection = self._reject_strict_record(table_name, parsed_data)
            if rejection is not None:
                return {
                    "operation": "validate",
                    "table": table_name,
                    "record_type": record_type,
                    "success": False,
                    "error": rejection,
                }
            if (
                record_type in CANCELLATION_STATE_RECORD_TYPES
                and record_data_kubun not in {
                    DATA_KUBUN_ERASE,
                    DATA_KUBUN_NEW,
                    DATA_KUBUN_UPDATE,
                    DATA_KUBUN_REREGISTER,
                    DATA_KUBUN_REFRESH,
                }
            ):
                head_data_kubun = DATA_KUBUN_NEW
            else:
                head_data_kubun = record_data_kubun

            # Process the resolved record-specific DataKubun.
            # Note: Per-record debug logging removed to reduce verbosity
            if head_data_kubun == DATA_KUBUN_NEW:
                return self._handle_new_record(table_name, parsed_data)
            elif head_data_kubun == DATA_KUBUN_UPDATE:
                return self._handle_update_record(table_name, parsed_data)
            elif head_data_kubun == DATA_KUBUN_DELETE:
                return self._handle_delete_record(table_name, parsed_data)
            elif head_data_kubun in (DATA_KUBUN_REFRESH, DATA_KUBUN_REREGISTER):
                # REFRESH(4) and REREGISTER(3): replace existing record (INSERT OR REPLACE)
                return self._handle_new_record(table_name, parsed_data)
            elif head_data_kubun == DATA_KUBUN_ERASE:
                # ERASE(0) is treated same as DELETE
                return self._handle_delete_record(table_name, parsed_data)
            else:
                logger.warning(f"Unknown DataKubun: {head_data_kubun}")
                return None

        except ValueError as e:
            logger.error(f"Rejected realtime record: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing single record: {e}", exc_info=True)
            raise

    def _prepare_data_for_db(self, table_name: str, data: Dict) -> Dict:
        """Strip metadata and coerce JV-Data sentinel values.

        Mirrors importer.py's _convert_record so that parser metadata is
        dropped and "*", "****", "0103*****" etc. become NULL instead of
        failing PostgreSQL's INTEGER/BIGINT/REAL validation. Required because
        RealtimeUpdater bypasses DataImporter.
        """
        from src.importer.importer import convert_record_types

        clean_data = clean_record_metadata(data)
        if table_name.startswith("TS_"):
            clean_data.setdefault("CollectedAt", self._current_collected_at())
        if table_name in {"TS_O1", "TS_SOKUHO_O1"}:
            if clean_data.get("Umaban") and not clean_data.get("Kumi"):
                clean_data["Kumi"] = "00"
            if clean_data.get("Kumi") and not clean_data.get("Umaban"):
                clean_data["Umaban"] = "0"
        return convert_record_types(clean_data, table_name)

    @staticmethod
    def _has_complete_primary_key(table_name: str, data: Dict) -> bool:
        primary_keys = get_table_primary_key_columns(table_name)
        if not primary_keys:
            return True
        return all(data.get(key) not in (None, "") for key in primary_keys)

    @staticmethod
    def _current_collected_at() -> str:
        """Return collector-side capture timestamp in UTC ISO-8601."""
        return datetime.now(timezone.utc).isoformat()

    def _handle_new_record(self, table_name: str, data: Dict) -> Dict:
        """Handle new record insertion.

        Args:
            table_name: Table name
            data: Parsed record data

        Returns:
            Result dictionary with operation details
        """
        try:
            clean_data = self._prepare_data_for_db(table_name, data)
            if not self._has_complete_primary_key(table_name, clean_data):
                return {
                    "operation": "insert",
                    "table": table_name,
                    "record_type": data.get("RecordSpec"),
                    "success": False,
                    "error": "Incomplete primary key",
                }

            # INSERT OR REPLACE handles duplicates (UPSERT semantics)
            self.database.insert(table_name, clean_data)

            # Note: Per-record debug logging removed to reduce verbosity during real-time processing

            return {
                "operation": "insert",
                "table": table_name,
                "record_type": data.get("RecordSpec"),
                "success": True,
            }

        except Exception as e:
            logger.error(f"Failed to insert record: {e}")
            return {
                "operation": "insert",
                "table": table_name,
                "success": False,
                "error": str(e),
            }

    def _handle_update_record(self, table_name: str, data: Dict) -> Dict:
        """Handle record update.

        Args:
            table_name: Table name
            data: Parsed record data

        Returns:
            Result dictionary with operation details
        """
        try:
            clean_data = self._prepare_data_for_db(table_name, data)
            if not self._has_complete_primary_key(table_name, clean_data):
                return {
                    "operation": "update",
                    "table": table_name,
                    "record_type": data.get("RecordSpec"),
                    "success": False,
                    "error": "Incomplete primary key",
                }

            # INSERT OR REPLACE handles the update (replaces existing row on PK match)
            self.database.insert(table_name, clean_data)

            # Note: Per-record debug logging removed to reduce verbosity during real-time processing

            return {
                "operation": "update",
                "table": table_name,
                "record_type": data.get("RecordSpec"),
                "success": True,
            }

        except Exception as e:
            logger.error(f"Failed to update record: {e}")
            return {
                "operation": "update",
                "table": table_name,
                "success": False,
                "error": str(e),
            }

    def _get_primary_keys(self, table_name: str) -> list:
        """Get primary key columns for a table.

        Args:
            table_name: Table name (e.g., "RT_RA", "RT_SE")

        Returns:
            List of primary key column names

        Note:
            Primary key definitions are based on schema.py table definitions.
            Tables without explicit primary keys return empty list.
        """
        lookup_name = table_name

        PRIMARY_KEY_MAP = {
            # Race data - standard race identifier
            "RT_RA": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"],
            "RT_SE": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban"],
            "RT_HR": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"],

            # Odds data - race identifier + Umaban or Kumi
            "RT_O1": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban", "Kumi"],
            "RT_O2": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi"],
            "RT_O3": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi"],
            "RT_O4": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi"],
            "RT_O5": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi"],
            "RT_O6": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi"],

            # Vote data
            "RT_H1": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "BetType", "Kumi"],
            "RT_H6": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "SanrentanKumi"],

            # Change data - 騎手変更情報
            "RT_RC": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban"],

            # 時系列オッズ (HassoTimeを含むPRIMARY KEY)
            "TS_O1": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban", "Kumi", "HassoTime"],
            "TS_O2": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
            "TS_O3": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
            "TS_O4": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
            "TS_O5": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
            "TS_O6": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
            "TS_SOKUHO_O1": [
                "Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji",
                "RaceNum", "Umaban", "Kumi", "HassoTime", "SourceSpec",
                "CollectedAt",
            ],
            "TS_SOKUHO_O2": [
                "Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji",
                "RaceNum", "Kumi", "HassoTime", "SourceSpec", "CollectedAt",
            ],
            "TS_SOKUHO_O3": [
                "Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji",
                "RaceNum", "Kumi", "HassoTime", "SourceSpec", "CollectedAt",
            ],
            "TS_SOKUHO_O4": [
                "Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji",
                "RaceNum", "Kumi", "HassoTime", "SourceSpec", "CollectedAt",
            ],
            "TS_SOKUHO_O5": [
                "Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji",
                "RaceNum", "Kumi", "HassoTime", "SourceSpec", "CollectedAt",
            ],
            "TS_SOKUHO_O6": [
                "Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji",
                "RaceNum", "Kumi", "HassoTime", "SourceSpec", "CollectedAt",
            ],

            # Weather and horse-weight tables
            "RT_WE": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "HenkoID"],
            "RT_WH": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban"],

            # Other realtime tables
            "RT_DM": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban"],
            "RT_TM": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban"],
            "RT_AV": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban"],
            "RT_JC": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban"],
            "RT_TC": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"],
            "RT_CC": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"],
            "RT_WF": ["Year", "MonthDay"],
        }

        return PRIMARY_KEY_MAP.get(lookup_name, [])

    @staticmethod
    def _expanded_record_delete_keys(table_name: str, data: Dict) -> list:
        """Return record-level delete keys for expanded array tables."""
        data_kubun = resolve_record_data_kubun(data)
        record_type = data.get("RecordSpec")
        if data_kubun != DATA_KUBUN_ERASE and not (
            data_kubun == DATA_KUBUN_DELETE
            and record_type not in CANCELLATION_STATE_RECORD_TYPES
        ):
            return []

        base_keys = ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"]
        expanded_tables = {
            "RT_H1", "RT_H6",
            "RT_O1", "RT_O2", "RT_O3", "RT_O4", "RT_O5", "RT_O6",
            "RT_WH", "RT_DM", "RT_TM",
        }
        ts_tables = {
            "TS_O1", "TS_O2", "TS_O3", "TS_O4", "TS_O5", "TS_O6",
            "TS_SOKUHO_O1", "TS_SOKUHO_O2", "TS_SOKUHO_O3",
            "TS_SOKUHO_O4", "TS_SOKUHO_O5", "TS_SOKUHO_O6",
        }

        if table_name in expanded_tables:
            keys = base_keys
        elif table_name in ts_tables:
            keys = [*base_keys, "HassoTime"]
            if table_name.startswith("TS_SOKUHO_") and data.get("SourceSpec"):
                keys.append("SourceSpec")
        else:
            return []

        if all(data.get(key) not in (None, "") for key in keys):
            return keys
        return []

    def _handle_delete_record(self, table_name: str, data: Dict) -> Dict:
        """Handle record deletion.

        Args:
            table_name: Table name
            data: Parsed record data

        Returns:
            Result dictionary with operation details

        Note:
            Performs physical deletion based on primary key.
            For tables without primary keys, deletion is not supported.
        """
        try:
            clean_data = self._prepare_data_for_db(table_name, data)
            # Get primary key columns for this table
            primary_keys = self._get_primary_keys(table_name)

            if not primary_keys:
                logger.warning(
                    f"No primary key defined for {table_name}, deletion not supported"
                )
                return {
                    "operation": "delete",
                    "table": table_name,
                    "record_type": data.get("RecordSpec"),
                    "success": False,
                    "error": "No primary key defined for table",
                }

            record_level_keys = self._expanded_record_delete_keys(table_name, clean_data)
            if record_level_keys:
                where_conditions = [f"{key} = ?" for key in record_level_keys]
                where_values = [clean_data[key] for key in record_level_keys]
                sql = f"DELETE FROM {table_name} WHERE {' AND '.join(where_conditions)}"
                self.database.execute(sql, tuple(where_values))
                return {
                    "operation": "delete",
                    "table": table_name,
                    "record_type": data.get("RecordSpec"),
                    "success": True,
                }

            missing_keys = [
                key for key in primary_keys
                if key not in clean_data
                or clean_data.get(key) is None
                or clean_data.get(key) == ""
            ]
            if missing_keys:
                logger.warning(
                    f"Missing primary key columns for {table_name}: {missing_keys}"
                )
                return {
                    "operation": "delete",
                    "table": table_name,
                    "record_type": data.get("RecordSpec"),
                    "success": False,
                    "error": f"Missing primary key values: {', '.join(missing_keys)}",
                }

            # Build WHERE clause from primary key fields
            where_conditions = []
            where_values = []

            for key in primary_keys:
                where_conditions.append(f"{key} = ?")
                where_values.append(clean_data[key])

            # Execute DELETE statement
            sql = f"DELETE FROM {table_name} WHERE {' AND '.join(where_conditions)}"
            self.database.execute(sql, tuple(where_values))

            # Note: Per-record debug logging removed to reduce verbosity during real-time processing

            return {
                "operation": "delete",
                "table": table_name,
                "record_type": data.get("RecordSpec"),
                "success": True,
            }

        except Exception as e:
            logger.error(f"Failed to delete record: {e}")
            return {
                "operation": "delete",
                "table": table_name,
                "success": False,
                "error": str(e),
            }
