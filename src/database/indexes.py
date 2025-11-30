"""Database index definitions for JLTSQL.

This module provides optimized index definitions for all tables
to improve query performance for common search patterns in horse racing data analysis.

Index Design Principles:
1. Date range searches (Year/MonthDay, MakeDate)
2. Venue/Race searches (JyoCD, RaceNum)
3. Horse/Jockey/Trainer searches (KettoNum, KisyuCode, ChokyosiCode)
4. Composite indexes for common JOIN patterns
5. Covering indexes for frequently queried columns
"""

from typing import Dict, List

from src.database.base import BaseDatabase
from src.utils.logger import get_logger

logger = get_logger(__name__)


# Index definitions for each table
# Format: table_name -> list of CREATE INDEX statements
INDEXES = {
    # ============================================================================
    # NL_* Tables (Accumulated Data) - 23 working tables
    # ============================================================================

    "NL_RA": [
        # レース詳細 (Race Details) - Most frequently queried table
        "CREATE INDEX IF NOT EXISTS idx_nl_ra_date ON NL_RA(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_ra_venue ON NL_RA(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_ra_race ON NL_RA(RaceNum)",
        "CREATE INDEX IF NOT EXISTS idx_nl_ra_grade ON NL_RA(GradeCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_ra_distance ON NL_RA(Kyori)",
        "CREATE INDEX IF NOT EXISTS idx_nl_ra_track ON NL_RA(TrackCD)",
        # Composite index for common queries
        "CREATE INDEX IF NOT EXISTS idx_nl_ra_venue_date ON NL_RA(JyoCD, Year, MonthDay)",
    ],

    "NL_AV": [
        # 市場取引価格 (Market Transaction Price)
        # 実際のスキーマ: KettoNum, SaleHostName, SaleName, Price
        "CREATE INDEX IF NOT EXISTS idx_nl_av_horse ON NL_AV(KettoNum)",
        "CREATE INDEX IF NOT EXISTS idx_nl_av_sale ON NL_AV(SaleName)",
    ],

    "NL_BN": [
        # 馬主マスタ (Owner Master)
        "CREATE INDEX IF NOT EXISTS idx_nl_bn_name ON NL_BN(BanusiName_Co)",
        "CREATE INDEX IF NOT EXISTS idx_nl_bn_date ON NL_BN(MakeDate)",
    ],

    "NL_BR": [
        # 生産者マスタ (Breeder Master)
        "CREATE INDEX IF NOT EXISTS idx_nl_br_name ON NL_BR(BreederName_Co)",
        "CREATE INDEX IF NOT EXISTS idx_nl_br_location ON NL_BR(Address)",
        "CREATE INDEX IF NOT EXISTS idx_nl_br_date ON NL_BR(MakeDate)",
    ],

    "NL_BT": [
        # 系統情報 (Bloodline)
        "CREATE INDEX IF NOT EXISTS idx_nl_bt_system ON NL_BT(KeitoId)",
        "CREATE INDEX IF NOT EXISTS idx_nl_bt_name ON NL_BT(KeitoName)",
    ],

    "NL_CC": [
        # 競走馬成績 (Horse Performance)
        "CREATE INDEX IF NOT EXISTS idx_nl_cc_date ON NL_CC(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_cc_venue ON NL_CC(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_cc_race ON NL_CC(RaceNum)",
    ],

    "NL_CH": [
        # 繁殖馬マスタ (Broodmare Master)
        "CREATE INDEX IF NOT EXISTS idx_nl_ch_date ON NL_CH(MakeDate)",
    ],

    "NL_CS": [
        # 成績変更・取消情報 (Result Change/Cancellation)
        # 実際のスキーマにはYear, MonthDay, RaceNumが存在しない
        "CREATE INDEX IF NOT EXISTS idx_nl_cs_venue ON NL_CS(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_cs_date ON NL_CS(MakeDate)",
    ],

    "NL_DM": [
        # データマイニング (Data Mining - Time Type)
        "CREATE INDEX IF NOT EXISTS idx_nl_dm_date ON NL_DM(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_dm_venue ON NL_DM(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_dm_race ON NL_DM(RaceNum)",
    ],

    "NL_HS": [
        # 馬成績 (Horse Results)
        "CREATE INDEX IF NOT EXISTS idx_nl_hs_date ON NL_HS(MakeDate)",
    ],

    "NL_HY": [
        # 馬名意味由来 (Horse Name Meaning/Origin)
        # 実際のスキーマにはYear, MonthDay, JyoCDが存在しない
        "CREATE INDEX IF NOT EXISTS idx_nl_hy_date ON NL_HY(MakeDate)",
        "CREATE INDEX IF NOT EXISTS idx_nl_hy_horse ON NL_HY(Bamei)",
    ],

    "NL_JG": [
        # 重賞レース (Graded Stakes Race)
        # 実際のスキーマにはGradeCDが存在しない
        "CREATE INDEX IF NOT EXISTS idx_nl_jg_date ON NL_JG(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_jg_venue ON NL_JG(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_jg_race ON NL_JG(RaceNum)",
    ],

    "NL_KS": [
        # 騎手マスタ (Jockey Master)
        "CREATE INDEX IF NOT EXISTS idx_nl_ks_name ON NL_KS(KisyuName)",
        "CREATE INDEX IF NOT EXISTS idx_nl_ks_date ON NL_KS(MakeDate)",
    ],

    "NL_O1": [
        # オッズ (単勝・複勝) (Odds - Win/Place)
        # 実際のスキーマにはHappyoTimeが存在しない
        "CREATE INDEX IF NOT EXISTS idx_nl_o1_date ON NL_O1(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_o1_venue ON NL_O1(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_o1_race ON NL_O1(RaceNum)",
    ],

    "NL_O2": [
        # オッズ (枠連) (Odds - Bracket Quinella)
        # 実際のスキーマにはHappyoTimeが存在しない
        "CREATE INDEX IF NOT EXISTS idx_nl_o2_date ON NL_O2(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_o2_venue ON NL_O2(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_o2_race ON NL_O2(RaceNum)",
    ],

    "NL_O3": [
        # オッズ (馬連) (Odds - Quinella)
        # 実際のスキーマにはHappyoTimeが存在しない
        "CREATE INDEX IF NOT EXISTS idx_nl_o3_date ON NL_O3(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_o3_venue ON NL_O3(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_o3_race ON NL_O3(RaceNum)",
    ],

    "NL_O4": [
        # オッズ (ワイド) (Odds - Wide)
        # 実際のスキーマにはHappyoTimeが存在しない
        "CREATE INDEX IF NOT EXISTS idx_nl_o4_date ON NL_O4(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_o4_venue ON NL_O4(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_o4_race ON NL_O4(RaceNum)",
    ],

    "NL_RC": [
        # レースコード (Race Code)
        "CREATE INDEX IF NOT EXISTS idx_nl_rc_date ON NL_RC(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_rc_venue ON NL_RC(JyoCD)",
    ],

    "NL_TC": [
        # 調教師成績 (Trainer Performance)
        "CREATE INDEX IF NOT EXISTS idx_nl_tc_date ON NL_TC(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_tc_venue ON NL_TC(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_tc_race ON NL_TC(RaceNum)",
    ],

    "NL_TK": [
        # 特別登録馬 (Special Registration Horse)
        # 実際のスキーマにはMakeDateが存在しない
        "CREATE INDEX IF NOT EXISTS idx_nl_tk_date ON NL_TK(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_tk_venue ON NL_TK(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_tk_race ON NL_TK(RaceNum)",
    ],

    "NL_TM": [
        # データマイニング (対戦型) (Data Mining - Match Type)
        "CREATE INDEX IF NOT EXISTS idx_nl_tm_date ON NL_TM(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_tm_venue ON NL_TM(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_tm_race ON NL_TM(RaceNum)",
    ],

    "NL_WH": [
        # 天候馬場状態変更 (Weather/Track Condition Change)
        # 実際のスキーマにはRaceNumが存在しない
        "CREATE INDEX IF NOT EXISTS idx_nl_wh_date ON NL_WH(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_wh_venue ON NL_WH(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_wh_time ON NL_WH(HappyoTime)",
    ],

    "NL_YS": [
        # 開催スケジュール (Event Schedule)
        "CREATE INDEX IF NOT EXISTS idx_nl_ys_year ON NL_YS(Year)",
        "CREATE INDEX IF NOT EXISTS idx_nl_ys_date ON NL_YS(MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_nl_ys_venue ON NL_YS(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_nl_ys_day ON NL_YS(YoubiCD)",
    ],

    # ============================================================================
    # RT_* Tables (Real-Time Data) - 11 working tables
    # ============================================================================

    "RT_RA": [
        # リアルタイム: レース詳細
        "CREATE INDEX IF NOT EXISTS idx_rt_ra_date ON RT_RA(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_rt_ra_venue ON RT_RA(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_rt_ra_race ON RT_RA(RaceNum)",
        "CREATE INDEX IF NOT EXISTS idx_rt_ra_time ON RT_RA(HappyoTime)",
        # Real-time specific: recent data queries
        "CREATE INDEX IF NOT EXISTS idx_rt_ra_venue_time ON RT_RA(JyoCD, HappyoTime)",
    ],

    "RT_AV": [
        # リアルタイム: 場外発売 (Market Transaction Price)
        # 実際のスキーマ: KettoNum, SaleHostName, SaleName, Price のみ
        "CREATE INDEX IF NOT EXISTS idx_rt_av_horse ON RT_AV(KettoNum)",
        "CREATE INDEX IF NOT EXISTS idx_rt_av_sale ON RT_AV(SaleName)",
    ],

    "RT_CC": [
        # リアルタイム: 競走馬成績
        "CREATE INDEX IF NOT EXISTS idx_rt_cc_date ON RT_CC(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_rt_cc_venue ON RT_CC(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_rt_cc_race ON RT_CC(RaceNum)",
        "CREATE INDEX IF NOT EXISTS idx_rt_cc_time ON RT_CC(HappyoTime)",
    ],

    "RT_DM": [
        # リアルタイム: データマイニング
        # 実際のスキーマにはHappyoTimeが存在しない
        "CREATE INDEX IF NOT EXISTS idx_rt_dm_date ON RT_DM(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_rt_dm_venue ON RT_DM(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_rt_dm_race ON RT_DM(RaceNum)",
    ],

    "RT_O1": [
        # リアルタイム: オッズ (単勝・複勝)
        # 実際のスキーマにはHappyoTimeが存在しない
        "CREATE INDEX IF NOT EXISTS idx_rt_o1_date ON RT_O1(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_rt_o1_venue ON RT_O1(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_rt_o1_race ON RT_O1(RaceNum)",
        "CREATE INDEX IF NOT EXISTS idx_rt_o1_makedate ON RT_O1(MakeDate)",
    ],

    "RT_O2": [
        # リアルタイム: オッズ (枠連)
        # 実際のスキーマにはHappyoTimeが存在しない
        "CREATE INDEX IF NOT EXISTS idx_rt_o2_date ON RT_O2(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_rt_o2_venue ON RT_O2(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_rt_o2_race ON RT_O2(RaceNum)",
        "CREATE INDEX IF NOT EXISTS idx_rt_o2_makedate ON RT_O2(MakeDate)",
    ],

    "RT_O3": [
        # リアルタイム: オッズ (馬連)
        # 実際のスキーマにはHappyoTimeが存在しない
        "CREATE INDEX IF NOT EXISTS idx_rt_o3_date ON RT_O3(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_rt_o3_venue ON RT_O3(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_rt_o3_race ON RT_O3(RaceNum)",
        "CREATE INDEX IF NOT EXISTS idx_rt_o3_makedate ON RT_O3(MakeDate)",
    ],

    "RT_O4": [
        # リアルタイム: オッズ (ワイド)
        # 実際のスキーマにはHappyoTimeが存在しない
        "CREATE INDEX IF NOT EXISTS idx_rt_o4_date ON RT_O4(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_rt_o4_venue ON RT_O4(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_rt_o4_race ON RT_O4(RaceNum)",
        "CREATE INDEX IF NOT EXISTS idx_rt_o4_makedate ON RT_O4(MakeDate)",
    ],

    "RT_TC": [
        # リアルタイム: 調教師成績
        "CREATE INDEX IF NOT EXISTS idx_rt_tc_date ON RT_TC(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_rt_tc_venue ON RT_TC(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_rt_tc_race ON RT_TC(RaceNum)",
        "CREATE INDEX IF NOT EXISTS idx_rt_tc_time ON RT_TC(HappyoTime)",
    ],

    "RT_TM": [
        # リアルタイム: データマイニング (対戦型)
        # 実際のスキーマにはHappyoTimeが存在しない
        "CREATE INDEX IF NOT EXISTS idx_rt_tm_date ON RT_TM(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_rt_tm_venue ON RT_TM(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_rt_tm_race ON RT_TM(RaceNum)",
    ],

    "RT_WH": [
        # リアルタイム: 馬体重
        "CREATE INDEX IF NOT EXISTS idx_rt_wh_date ON RT_WH(Year, MonthDay)",
        "CREATE INDEX IF NOT EXISTS idx_rt_wh_venue ON RT_WH(JyoCD)",
        "CREATE INDEX IF NOT EXISTS idx_rt_wh_race ON RT_WH(RaceNum)",
        "CREATE INDEX IF NOT EXISTS idx_rt_wh_time ON RT_WH(HappyoTime)",
    ],
}


class IndexManager:
    """Index management for database tables.

    Creates and manages indexes for optimized query performance.

    Examples:
        >>> from src.database.sqlite_handler import SQLiteDatabase
        >>> from src.database.indexes import IndexManager
        >>>
        >>> db = SQLiteDatabase({"path": "./keiba.db"})
        >>> with db:
        ...     index_mgr = IndexManager(db)
        ...     results = index_mgr.create_all_indexes()
        ...     print(f"Created {sum(results.values())} indexes")
    """

    def __init__(self, database: BaseDatabase):
        """Initialize index manager.

        Args:
            database: Database handler instance
        """
        self.database = database
        logger.info("IndexManager initialized")

    def create_indexes(self, table_name: str) -> bool:
        """Create all indexes for a specific table.

        Args:
            table_name: Name of the table

        Returns:
            True if all indexes created successfully, False otherwise
        """
        if table_name not in INDEXES:
            logger.warning(f"No index definitions for table: {table_name}")
            return False

        try:
            index_statements = INDEXES[table_name]
            for statement in index_statements:
                self.database.execute(statement)

            logger.info(f"Created {len(index_statements)} indexes for {table_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create indexes for {table_name}: {e}")
            return False

    def create_all_indexes(self) -> Dict[str, int]:
        """Create all indexes for all tables.

        Returns:
            Dictionary mapping table names to number of indexes created
        """
        results = {}

        for table_name in INDEXES.keys():
            try:
                index_statements = INDEXES[table_name]
                success_count = 0

                for statement in index_statements:
                    try:
                        self.database.execute(statement)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Failed to create index: {e}")

                results[table_name] = success_count

                if success_count == len(index_statements):
                    logger.info(f"Created {success_count} indexes for {table_name}")
                else:
                    logger.warning(
                        f"Created {success_count}/{len(index_statements)} indexes for {table_name}"
                    )

            except Exception as e:
                logger.error(f"Failed to create indexes for {table_name}: {e}")
                results[table_name] = 0

        total_indexes = sum(results.values())
        logger.info(f"Created {total_indexes} total indexes across {len(results)} tables")

        return results

    def drop_indexes(self, table_name: str) -> bool:
        """Drop all indexes for a specific table.

        Args:
            table_name: Name of the table

        Returns:
            True if all indexes dropped successfully, False otherwise

        Note:
            This will NOT drop the PRIMARY KEY constraint, only additional indexes.
        """
        if table_name not in INDEXES:
            logger.warning(f"No index definitions for table: {table_name}")
            return False

        try:
            index_statements = INDEXES[table_name]

            for statement in index_statements:
                # Extract index name from CREATE INDEX statement
                # Format: "CREATE INDEX IF NOT EXISTS idx_name ON table_name(...)"
                parts = statement.split()

                # Find INDEX keyword position
                try:
                    idx_pos = parts.index("INDEX")
                except ValueError:
                    continue

                # Check if IF NOT EXISTS follows INDEX
                if idx_pos + 3 < len(parts) and parts[idx_pos + 1] == "IF":
                    # Format: CREATE INDEX IF NOT EXISTS idx_name
                    index_name = parts[idx_pos + 4]
                elif idx_pos + 1 < len(parts):
                    # Format: CREATE INDEX idx_name
                    index_name = parts[idx_pos + 1]
                else:
                    continue

                # Drop index
                drop_sql = f"DROP INDEX IF EXISTS {index_name}"
                self.database.execute(drop_sql)

            logger.info(f"Dropped {len(index_statements)} indexes from {table_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to drop indexes from {table_name}: {e}")
            return False

    def get_index_count(self, table_name: str) -> int:
        """Get the number of index definitions for a table.

        Args:
            table_name: Name of the table

        Returns:
            Number of indexes defined for the table
        """
        return len(INDEXES.get(table_name, []))

    def get_all_index_count(self) -> int:
        """Get the total number of index definitions across all tables.

        Returns:
            Total number of indexes defined
        """
        return sum(len(indexes) for indexes in INDEXES.values())

    def list_tables_with_indexes(self) -> List[str]:
        """Get list of table names that have index definitions.

        Returns:
            List of table names
        """
        return list(INDEXES.keys())
