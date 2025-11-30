"""Data importer for JLTSQL.

This module imports parsed JV-Data records into database.
"""

from typing import Dict, Iterator, List, Optional

from src.database.base import BaseDatabase, DatabaseError
from src.utils.logger import get_logger

logger = get_logger(__name__)


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

        # Map record types to table names
        # Note: Table names match schema.py table definitions (e.g. NL_RA, not NL_RA_RACE)
        self._table_map = {
            # NL_ tables (蓄積データ)
            "RA": "NL_RA",  # レース詳細
            "SE": "NL_SE",  # 馬毎レース情報
            "HR": "NL_HR",  # 払戻
            "JG": "NL_JG",  # 除外馬
            "H1": "NL_H1",  # 単勝・複勝オッズ
            "H6": "NL_H6",  # 単勝・複勝オッズ（6レースまとめ）
            "O1": "NL_O1",  # 馬連オッズ
            "O2": "NL_O2",  # ワイドオッズ
            "O3": "NL_O3",  # 枠連オッズ
            "O4": "NL_O4",  # 馬単オッズ
            "O5": "NL_O5",  # 三連複オッズ
            "O6": "NL_O6",  # 三連単オッズ
            "YS": "NL_YS",  # スケジュール
            "UM": "NL_UM",  # 馬マスター
            "KS": "NL_KS",  # 騎手マスター
            "CH": "NL_CH",  # 調教師マスター
            "BR": "NL_BR",  # 繁殖馬マスター
            "BN": "NL_BN",  # 生産者マスター
            "HN": "NL_HN",  # 馬主マスター
            "SK": "NL_SK",  # 競走馬見積もり
            "RC": "NL_RC",  # レースコメント
            "CC": "NL_CC",  # コース変更
            "TC": "NL_TC",  # タイムコメント
            "CS": "NL_CS",  # コメントショート
            "CK": "NL_CK",  # 勝利騎手・調教師コメント
            "WC": "NL_WC",  # 天候コメント
            "AV": "NL_AV",  # 場外発売情報
            "JC": "NL_JC",  # 重量変更情報
            "HC": "NL_HC",  # 異常区分情報
            "HS": "NL_HS",  # 配当金情報
            "HY": "NL_HY",  # 払戻情報（地方競馬）
            "WE": "NL_WE",  # 気象情報
            "WF": "NL_WF",  # 風情報
            "WH": "NL_WH",  # 馬場情報
            "TM": "NL_TM",  # タイムマスター
            "TK": "NL_TK",  # 追切マスター
            "BT": "NL_BT",  # 調教Bタイム
            "DM": "NL_DM",  # データマスター
            # RT_ tables (速報データ)
            "RT_RA": "RT_RA",  # レース詳細（速報）
            "RT_SE": "RT_SE",  # 馬毎レース情報（速報）
            "RT_HR": "RT_HR",  # 払戻（速報）
            "RT_O1": "RT_O1",  # 馬連オッズ（速報）
            "RT_O2": "RT_O2",  # ワイドオッズ（速報）
            "RT_O3": "RT_O3",  # 枠連オッズ（速報）
            "RT_O4": "RT_O4",  # 馬単オッズ（速報）
            "RT_O5": "RT_O5",  # 三連複オッズ（速報）
            "RT_O6": "RT_O6",  # 三連単オッズ（速報）
            "RT_H1": "RT_H1",  # 単勝・複勝オッズ（速報）
            "RT_H6": "RT_H6",  # 単勝・複勝オッズ6R（速報）
            "RT_WE": "RT_WE",  # 気象情報（速報）
            "RT_WH": "RT_WH",  # 馬場情報（速報）
            "RT_JC": "RT_JC",  # 重量変更情報（速報）
            "RT_CC": "RT_CC",  # コース変更（速報）
            "RT_TC": "RT_TC",  # タイムコメント（速報）
            "RT_TM": "RT_TM",  # タイムマスター（速報）
            "RT_DM": "RT_DM",  # データマスター（速報）
            "RT_AV": "RT_AV",  # 場外発売情報（速報）
        }

        logger.info(
            "DataImporter initialized",
            batch_size=batch_size,
            use_jravan_schema=use_jravan_schema,
        )

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
            from src.database.table_mappings import JLTSQL_TO_JRAVAN
            return JLTSQL_TO_JRAVAN.get(table_name, table_name)

        return table_name

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
        # Reset statistics
        self._records_imported = 0
        self._records_failed = 0
        self._batches_processed = 0

        # Group records by type for batch insertion
        batch_buffers: Dict[str, List[dict]] = {}

        try:
            for record in records:
                # Get record type and table name
                # Note: Japanese parsers use 'レコード種別ID', JRA-VAN standard uses 'RecordSpec'
                record_type = (
                    record.get("レコード種別ID") or
                    record.get("RecordSpec") or
                    record.get("headRecordSpec")
                )
                if not record_type:
                    logger.warning(
                        "Record missing record type field",
                        record_keys=list(record.keys())[:5] if record else None
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

        try:
            # Insert batch
            rows = self.database.insert_many(table_name, batch)

            self._records_imported += rows
            self._batches_processed += 1

            if auto_commit:
                self.database.commit()

            logger.debug(
                f"Batch inserted",
                table=table_name,
                records=rows,
                batch_num=self._batches_processed,
            )

        except DatabaseError as e:
            # Try inserting one by one on batch failure
            logger.warning(
                f"Batch insert failed, trying individual inserts",
                table=table_name,
                error=str(e),
            )

            for record in batch:
                try:
                    self.database.insert(table_name, record)
                    self._records_imported += 1

                    if auto_commit:
                        self.database.commit()

                except DatabaseError as e:
                    self._records_failed += 1
                    logger.error(
                        "Failed to insert record",
                        table=table_name,
                        error=str(e),
                    )

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
        # Note: Japanese parsers use 'レコード種別ID', JRA-VAN standard uses 'RecordSpec'
        record_type = (
            record.get("レコード種別ID") or
            record.get("RecordSpec") or
            record.get("headRecordSpec")
        )
        if not record_type:
            logger.warning("Record missing record type field")
            return False

        table_name = self._get_table_name(record_type)
        if not table_name:
            logger.warning(f"Unknown record type: {record_type}")
            return False

        try:
            self.database.insert(table_name, record)
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
