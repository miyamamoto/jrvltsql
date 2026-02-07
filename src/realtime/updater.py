"""Real-time data updater for JLTSQL.

This module handles real-time data updates to the database.
"""

from typing import Dict, Optional

from src.database.base import BaseDatabase
from src.jvlink.constants import (
    DATA_KUBUN_NEW,
    DATA_KUBUN_UPDATE,
    DATA_KUBUN_DELETE,
    DATA_KUBUN_REFRESH,
    DATA_KUBUN_REREGISTER,
    DATA_KUBUN_ERASE,
)
from src.parser.factory import ParserFactory
from src.utils.data_source import DataSource
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

    # Table mapping from record type to RT_ tables (Real-Time data)
    # Real-time updates use RT_ prefix, historical data uses NL_ prefix
    #
    # JVRTOpen provides two categories of data:
    # - 速報系データ (0B1x): レース確定情報
    # - 時系列データ (0B2x-0B3x): 継続更新オッズ・票数
    RECORD_TYPE_TABLE = {
        # === 速報系データ (Speed Report - 0B1x) ===
        # 0B11: 開催情報
        "WE": "RT_WE",  # 開催情報

        # 0B12: レース情報
        "RA": "RT_RA",  # レース詳細
        "SE": "RT_SE",  # 馬毎レース情報

        # 0B13: データマイニング予想
        "DM": "RT_DM",  # データマイニング（タイム型）

        # 0B14: 出走取消・競走除外
        "AV": "RT_AV",  # 場外発売情報

        # 0B15: 払戻情報
        "HR": "RT_HR",  # 払戻

        # 0B16: 馬体重
        "WH": "RT_WH",  # 馬体重

        # 0B17: 対戦型データマイニング予想
        "TM": "RT_TM",  # データマイニング（対戦型）

        # === 時系列データ (Time Series - 0B2x-0B3x) ===
        # 0B20: 票数情報
        "H1": "RT_H1",  # 票数（単勝・複勝等）
        "H6": "RT_H6",  # 票数（３連単）

        # 0B30-0B36: オッズ情報
        "O1": "RT_O1",  # オッズ（単勝・複勝）
        "O2": "RT_O2",  # オッズ（枠連）
        "O3": "RT_O3",  # オッズ（馬連）
        "O4": "RT_O4",  # オッズ（ワイド）
        "O5": "RT_O5",  # オッズ（馬単）
        "O6": "RT_O6",  # オッズ（３連複・３連単）

        # === その他 (成績データ) ===
        "JC": "RT_JC",  # 騎手成績
        "TC": "RT_TC",  # 調教師成績/調教師変更情報 (0B42)
        "CC": "RT_CC",  # 競走馬成績

        # === 変更情報データ (0B4x) ===
        # 0B41: 騎手変更情報
        "RC": "RT_RC",  # 騎手変更情報 (Row D, E両方)
        # 0B42: 調教師変更情報 - TCで対応済み
    }

    # 時系列オッズ専用テーブルマッピング (TS_O1-O6)
    # HassoTimeをPRIMARY KEYに含めて複数時点のデータを保持
    TIMESERIES_RECORD_TYPE_TABLE = {
        "O1": "TS_O1",  # 単複枠オッズ時系列
        "O2": "TS_O2",  # 馬連オッズ時系列
        "O3": "TS_O3",  # ワイドオッズ時系列
        "O4": "TS_O4",  # 馬単オッズ時系列
        "O5": "TS_O5",  # 三連複オッズ時系列
        "O6": "TS_O6",  # 三連単オッズ時系列
    }

    # Note: The following record types are NOT provided in real-time:
    # - TK (特別登録馬) - Accumulated data only
    # - UM, KS, CH, BR, BN, HN, SK (Master data) - Updated via DIFF/DIFN
    # - CK, HC, HS, HY (Code/Status data) - Updated via SNAP/SNPN
    # - YS, BT, CS (Change data) - Updated via YSCH, SLOP, etc.
    # - WF (WIN5), JG (重賞), WC (天候) - Not in real-time stream

    def __init__(self, database: BaseDatabase, data_source: DataSource = DataSource.JRA):
        """Initialize real-time updater.

        Args:
            database: Database handler instance
            data_source: Data source (DataSource.JRA or DataSource.NAR, default: JRA)
        """
        self.database = database
        self.data_source = data_source
        self.parser_factory = ParserFactory()

        logger.info("RealtimeUpdater initialized", data_source=data_source.value)

    def process_record(self, buff: bytes, timeseries: bool = False) -> Optional[Dict]:
        """Process real-time data record.

        Args:
            buff: Raw JV-Data record buffer (bytes)
            timeseries: If True, save odds data to TS_O* tables (time series)
                       instead of RT_O* tables. This preserves odds history
                       with HassoTime as part of the primary key.

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
            # For timeseries mode, use TS_O* tables for odds data
            if timeseries and record_type in self.TIMESERIES_RECORD_TYPE_TABLE:
                table_name = self.TIMESERIES_RECORD_TYPE_TABLE.get(record_type)
            else:
                table_name = self.RECORD_TYPE_TABLE.get(record_type)

            if not table_name:
                logger.warning(f"Unknown record type: {record_type}")
                return None

            # Add _NAR suffix for NAR data source
            if self.data_source == DataSource.NAR:
                table_name = f"{table_name}_NAR"

            # Get headDataKubun with fallback to DataKubun
            head_data_kubun = (
                parsed_data.get("headDataKubun")
                or parsed_data.get("DataKubun")
                or "1"
            )

            # Process based on headDataKubun
            # Note: Per-record debug logging removed to reduce verbosity
            if head_data_kubun == DATA_KUBUN_NEW:
                return self._handle_new_record(table_name, parsed_data)
            elif head_data_kubun == DATA_KUBUN_UPDATE:
                return self._handle_update_record(table_name, parsed_data)
            elif head_data_kubun == DATA_KUBUN_DELETE:
                return self._handle_delete_record(table_name, parsed_data)
            elif head_data_kubun in (DATA_KUBUN_REFRESH, DATA_KUBUN_REREGISTER):
                # REFRESH(4) and REREGISTER(3) are treated as new records
                # TODO: Implement proper UPSERT logic when PRIMARY KEY is available
                return self._handle_new_record(table_name, parsed_data)
            elif head_data_kubun == DATA_KUBUN_ERASE:
                # ERASE(0) is treated same as DELETE
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
            # Remove metadata fields
            clean_data = {k: v for k, v in data.items() if not k.startswith("_")}

            # Update record
            # TODO: Implement proper UPDATE based on primary key
            # For now, use INSERT (may cause duplicate key error)
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
        PRIMARY_KEY_MAP = {
            # Race data - standard race identifier
            "RT_RA": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"],
            "RT_SE": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban"],
            "RT_HR": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"],

            # Odds data - race identifier + Umaban or Kumi
            "RT_O1": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban"],
            "RT_O2": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi"],
            "RT_O3": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi"],
            "RT_O4": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi"],
            "RT_O5": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi"],
            "RT_O6": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi"],

            # Vote data
            "RT_H1": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"],
            "RT_H6": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi"],

            # Change data - 騎手変更情報 (0B41)
            "RT_RC": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban"],

            # 時系列オッズ (HassoTimeを含むPRIMARY KEY)
            "TS_O1": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban", "HassoTime"],
            "TS_O2": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
            "TS_O3": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
            "TS_O4": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
            "TS_O5": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],
            "TS_O6": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Kumi", "HassoTime"],

            # Weather/Track condition tables
            "RT_WE": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "HenkoID"],
            "RT_WH": ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "HappyoTime", "HenkoID"],

            # Tables without explicit PRIMARY KEY in schema
            # These tables don't have PRIMARY KEY constraints defined
            "RT_DM": [],  # Data mining (time type) - no primary key
            "RT_TM": [],  # Data mining (match type) - no primary key
            "RT_AV": [],  # Sale info - no primary key
            "RT_JC": [],  # Jockey results - no primary key
            "RT_TC": [],  # Trainer results - no primary key
            "RT_CC": [],  # Horse results - no primary key
        }

        return PRIMARY_KEY_MAP.get(table_name, [])

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

            # Build WHERE clause from primary key fields
            where_conditions = []
            where_values = []

            for key in primary_keys:
                if key in data:
                    where_conditions.append(f"{key} = ?")
                    where_values.append(data[key])
                else:
                    logger.warning(
                        f"Primary key column {key} not found in data for {table_name}"
                    )

            # Check if we have all required primary key values
            if not where_conditions:
                return {
                    "operation": "delete",
                    "table": table_name,
                    "record_type": data.get("RecordSpec"),
                    "success": False,
                    "error": "Missing primary key values in data",
                }

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
