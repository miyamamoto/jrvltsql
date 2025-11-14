"""Real-time data updater for JLTSQL.

This module handles real-time data updates to the database.
"""

from typing import Dict, Optional

from src.database.base import BaseDatabase
from src.parser.factory import ParserFactory
from src.utils.logger import get_logger

logger = get_logger(__name__)


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

    # headDataKubun constants
    DATA_KUBUN_NEW = "1"  # 新規データ
    DATA_KUBUN_UPDATE = "2"  # 更新データ
    DATA_KUBUN_DELETE = "3"  # 削除データ

    # Table mapping from record type to RT_ tables (Real-Time data)
    # Real-time updates use RT_ prefix, historical data uses NL_ prefix
    #
    # IMPORTANT: Only 19 record types are provided via JVRTOpen (real-time)
    # Based on JV-Data4901.xlsx specification (Sheet 6: データ種別一覧 > 速報系データ)
    RECORD_TYPE_TABLE = {
        # Race data (0B12, 0B15)
        "RA": "RT_RA",  # Format 2: レース詳細
        "SE": "RT_SE",  # Format 3: 馬毎レース情報
        "HR": "RT_HR",  # Format 4: 払戻

        # Odds data (0B30-0B36)
        "O1": "RT_O1",  # Format 7: オッズ（単勝・複勝）
        "O2": "RT_O2",  # Format 8: オッズ（枠連）
        "O3": "RT_O3",  # Format 9: オッズ（馬連）
        "O4": "RT_O4",  # Format 10: オッズ（ワイド）
        "O5": "RT_O5",  # Format 11: オッズ（馬単）
        "O6": "RT_O6",  # Format 12: オッズ（３連複・３連単）

        # Vote data (0B20)
        "H1": "RT_H1",  # Format 5: 票数（単勝・複勝等）
        "H6": "RT_H6",  # Format 6: 票数（３連単）

        # Baba/Kaisai (0B11, 0B14, 0B16)
        "WH": "RT_WH",  # Format 101: 馬場状態
        "WE": "RT_WE",  # Format 102: 開催情報

        # Data mining (0B13, 0B17)
        "DM": "RT_DM",  # Format 28: データマイニング（タイム型）
        "TM": "RT_TM",  # Format 29: データマイニング（対戦型）

        # Performance data (0B14, 0B16)
        "AV": "RT_AV",  # Format 103: 場外発売情報
        "JC": "RT_JC",  # Format 104: 騎手成績
        "TC": "RT_TC",  # Format 105: 調教師成績
        "CC": "RT_CC",  # Format 106: 競走馬成績
    }

    # Note: The following record types are NOT provided in real-time:
    # - TK (特別登録馬) - Accumulated data only
    # - UM, KS, CH, BR, BN, HN, SK, RC (Master data) - Updated via DIFF/DIFN
    # - CK, HC, HS, HY (Code/Status data) - Updated via SNAP/SNPN
    # - YS, BT, CS (Change data) - Updated via YSCH, SLOP, etc.
    # - WF (WIN5), JG (重賞), WC (天候) - Not in real-time stream

    def __init__(self, database: BaseDatabase):
        """Initialize real-time updater.

        Args:
            database: Database handler instance
        """
        self.database = database
        self.parser_factory = ParserFactory()

        logger.info("RealtimeUpdater initialized")

    def process_record(self, buff: str) -> Optional[Dict]:
        """Process real-time data record.

        Args:
            buff: Raw JV-Data record buffer

        Returns:
            Dictionary with processing result, or None if failed

        Raises:
            Exception: If processing fails
        """
        try:
            # Parse record
            parsed_data = self.parser_factory.parse(buff)
            if not parsed_data:
                logger.warning("Failed to parse record")
                return None

            record_type = parsed_data.get("RecordSpec")
            if not record_type:
                logger.warning("Missing RecordSpec in parsed data")
                return None

            # Get table name
            table_name = self.RECORD_TYPE_TABLE.get(record_type)
            if not table_name:
                logger.warning(f"Unknown record type: {record_type}")
                return None

            # Get headDataKubun
            head_data_kubun = parsed_data.get("headDataKubun", "1")

            logger.debug(
                "Processing record",
                record_type=record_type,
                table=table_name,
                kubun=head_data_kubun,
            )

            # Process based on headDataKubun
            if head_data_kubun == self.DATA_KUBUN_NEW:
                return self._handle_new_record(table_name, parsed_data)
            elif head_data_kubun == self.DATA_KUBUN_UPDATE:
                return self._handle_update_record(table_name, parsed_data)
            elif head_data_kubun == self.DATA_KUBUN_DELETE:
                return self._handle_delete_record(table_name, parsed_data)
            else:
                logger.warning(f"Unknown headDataKubun: {head_data_kubun}")
                return None

        except Exception as e:
            logger.error(f"Error processing record: {e}", exc_info=True)
            raise

    def _handle_new_record(self, table_name: str, data: Dict) -> Dict:
        """Handle new record insertion.

        Args:
            table_name: Table name
            data: Parsed record data

        Returns:
            Result dictionary with operation details
        """
        try:
            # Remove metadata fields
            clean_data = {k: v for k, v in data.items() if not k.startswith("_")}

            # Insert into database
            # TODO: Implement UPSERT to handle duplicates
            self.database.insert(table_name, clean_data)

            logger.debug(f"Inserted new record into {table_name}")

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
            # Remove metadata fields
            clean_data = {k: v for k, v in data.items() if not k.startswith("_")}

            # Update record
            # TODO: Implement proper UPDATE based on primary key
            # For now, use INSERT (may cause duplicate key error)
            self.database.insert(table_name, clean_data)

            logger.debug(f"Updated record in {table_name}")

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

    def _handle_delete_record(self, table_name: str, data: Dict) -> Dict:
        """Handle record deletion.

        Args:
            table_name: Table name
            data: Parsed record data

        Returns:
            Result dictionary with operation details

        Note:
            Instead of physical deletion, we set a delete flag if available,
            or perform physical deletion based on primary key.
        """
        try:
            # Build WHERE clause from primary key fields
            # For now, we'll use a simplified approach
            # TODO: Implement proper primary key detection

            # Option 1: Set delete flag (if table has DeleteFlag column)
            # Option 2: Physical deletion

            # For simplicity, we'll do physical deletion based on key fields
            # This is a simplified implementation

            logger.warning(
                f"Delete operation not fully implemented for {table_name}",
                data=data,
            )

            return {
                "operation": "delete",
                "table": table_name,
                "record_type": data.get("RecordSpec"),
                "success": False,
                "error": "Delete operation not fully implemented",
            }

        except Exception as e:
            logger.error(f"Failed to delete record: {e}")
            return {
                "operation": "delete",
                "table": table_name,
                "success": False,
                "error": str(e),
            }
