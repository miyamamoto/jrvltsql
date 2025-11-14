"""Database schema manager for JLTSQL.

This module provides schema definitions and table creation management.
"""

from typing import Dict, List

from src.database.base import BaseDatabase
from src.utils.logger import get_logger

logger = get_logger(__name__)


# Table schema definitions based on JV-Data specification
SCHEMAS = {
    "NL_RA_RACE": """
        CREATE TABLE IF NOT EXISTS NL_RA_RACE (
            -- レコードヘッダー
            headRecordSpec TEXT,
            headDataKubun TEXT,
            headMakeDate TEXT,

            -- レース識別情報（主キー）
            idYear TEXT NOT NULL,
            idMonthDay TEXT NOT NULL,
            idJyoCD TEXT NOT NULL,
            idKaiji TEXT NOT NULL,
            idNichiji TEXT NOT NULL,
            idRaceNum TEXT NOT NULL,

            -- レース名称
            RaceNameShort TEXT,
            RaceNameShort6 TEXT,
            RaceNameShort3 TEXT,
            RaceName TEXT,
            RaceNameKana TEXT,
            RaceNameEng TEXT,
            RaceNameFukudai TEXT,
            RaceNameKakko TEXT,
            GradeCD TEXT,
            Jyoken5 TEXT,
            Jyoken4 TEXT,
            Jyoken3 TEXT,
            Jyoken2 TEXT,

            -- コース情報
            Kyori TEXT,
            TrackCD TEXT,
            CourseKubunCD TEXT,

            -- 賞金情報
            HondaiSyogaku1 TEXT,
            HondaiSyogaku2 TEXT,
            HondaiSyogaku3 TEXT,
            HondaiSyogaku4 TEXT,
            HondaiSyogaku5 TEXT,
            FukaSyogaku1 TEXT,
            FukaSyogaku2 TEXT,
            FukaSyogaku3 TEXT,

            -- レース状況
            HassoTime TEXT,
            TorokuTosu TEXT,
            SyussoTosu TEXT,
            NyusenTosu TEXT,
            TenkoCD TEXT,
            SibaBabaCD TEXT,
            DirtBabaCD TEXT,

            -- ラップタイム（200m×25区間）
            LapTime01 TEXT, LapTime02 TEXT, LapTime03 TEXT, LapTime04 TEXT, LapTime05 TEXT,
            LapTime06 TEXT, LapTime07 TEXT, LapTime08 TEXT, LapTime09 TEXT, LapTime10 TEXT,
            LapTime11 TEXT, LapTime12 TEXT, LapTime13 TEXT, LapTime14 TEXT, LapTime15 TEXT,
            LapTime16 TEXT, LapTime17 TEXT, LapTime18 TEXT, LapTime19 TEXT, LapTime20 TEXT,
            LapTime21 TEXT, LapTime22 TEXT, LapTime23 TEXT, LapTime24 TEXT, LapTime25 TEXT,

            -- コーナー通過順位
            CornerInfo1 TEXT,
            CornerInfo2 TEXT,
            CornerInfo3 TEXT,
            CornerInfo4 TEXT,

            -- その他
            RecordUpKubun TEXT,

            PRIMARY KEY (idYear, idMonthDay, idJyoCD, idKaiji, idNichiji, idRaceNum)
        )
    """,
    "NL_SE_RACE_UMA": """
        CREATE TABLE IF NOT EXISTS NL_SE_RACE_UMA (
            -- レコードヘッダー
            headRecordSpec TEXT,
            headDataKubun TEXT,
            headMakeDate TEXT,

            -- レース識別情報
            idYear TEXT NOT NULL,
            idMonthDay TEXT NOT NULL,
            idJyoCD TEXT NOT NULL,
            idKaiji TEXT NOT NULL,
            idNichiji TEXT NOT NULL,
            idRaceNum TEXT NOT NULL,

            -- 馬識別情報
            KettoNum TEXT NOT NULL,
            Bamei TEXT,

            -- 馬基本情報
            UmaKigoCD TEXT,
            SexCD TEXT,
            Barei TEXT,
            TozaiCD TEXT,
            ChokyosiCode TEXT,
            ChokyosiRyakusyo TEXT,
            BanusiCode TEXT,
            BanusiName TEXT,
            KeiroCD TEXT,

            -- 出走情報
            Wakuban TEXT,
            Umaban TEXT,
            Futan TEXT,
            BlinkerCD TEXT,

            -- 騎手情報
            KisyuCode TEXT,
            KisyuRyakusyo TEXT,
            MinaraiCD TEXT,

            -- レース成績
            KakuteiJyuni TEXT,
            Time TEXT,
            Tyakusa TEXT,
            CornerJyuni1 TEXT,
            CornerJyuni2 TEXT,
            CornerJyuni3 TEXT,
            CornerJyuni4 TEXT,

            -- オッズ・人気
            Odds TEXT,
            Ninki TEXT,

            -- 馬体情報
            Bataiju TEXT,
            BataijuZoka TEXT,

            -- 賞金
            HondaiSyogaku TEXT,
            FukaSyogaku TEXT,

            -- その他
            Jyuni TEXT,
            IjyoKubun TEXT,
            TimeDiff TEXT,

            PRIMARY KEY (idYear, idMonthDay, idJyoCD, idKaiji, idNichiji, idRaceNum, KettoNum)
        )
    """,
    "NL_HR_PAY": """
        CREATE TABLE IF NOT EXISTS NL_HR_PAY (
            -- レコードヘッダー
            headRecordSpec TEXT,
            headDataKubun TEXT,
            headMakeDate TEXT,

            -- レース識別情報
            idYear TEXT NOT NULL,
            idMonthDay TEXT NOT NULL,
            idJyoCD TEXT NOT NULL,
            idKaiji TEXT NOT NULL,
            idNichiji TEXT NOT NULL,
            idRaceNum TEXT NOT NULL,

            -- 単勝
            TansyoUmaban1 TEXT,
            TansyoHaraimodosi1 TEXT,
            TansyoNinki1 TEXT,

            -- 複勝
            FukusyoUmaban1 TEXT,
            FukusyoHaraimodosi1 TEXT,
            FukusyoNinki1 TEXT,
            FukusyoUmaban2 TEXT,
            FukusyoHaraimodosi2 TEXT,
            FukusyoNinki2 TEXT,
            FukusyoUmaban3 TEXT,
            FukusyoHaraimodosi3 TEXT,
            FukusyoNinki3 TEXT,

            -- 枠連
            WakurenWakuban1_1 TEXT,
            WakurenWakuban1_2 TEXT,
            WakurenHaraimodosi1 TEXT,
            WakurenNinki1 TEXT,

            -- 馬連
            UmarenUmaban1_1 TEXT,
            UmarenUmaban1_2 TEXT,
            UmarenHaraimodosi1 TEXT,
            UmarenNinki1 TEXT,

            -- ワイド
            WideUmaban1_1 TEXT,
            WideUmaban1_2 TEXT,
            WideHaraimodosi1 TEXT,
            WideNinki1 TEXT,

            -- 馬単
            UmatanUmaban1_1 TEXT,
            UmatanUmaban1_2 TEXT,
            UmatanHaraimodosi1 TEXT,
            UmatanNinki1 TEXT,

            -- 3連複
            Sanrenpuku3Umaban1_1 TEXT,
            Sanrenpuku3Umaban1_2 TEXT,
            Sanrenpuku3Umaban1_3 TEXT,
            Sanrenpuku3Haraimodosi1 TEXT,
            Sanrenpuku3Ninki1 TEXT,

            -- 3連単
            Sanrentan3Umaban1_1 TEXT,
            Sanrentan3Umaban1_2 TEXT,
            Sanrentan3Umaban1_3 TEXT,
            Sanrentan3Haraimodosi1 TEXT,
            Sanrentan3Ninki1 TEXT,

            PRIMARY KEY (idYear, idMonthDay, idJyoCD, idKaiji, idNichiji, idRaceNum)
        )
    """,
}


class SchemaManager:
    """Manager for database schema operations.

    Handles table creation and schema management for JV-Data tables.

    Examples:
        >>> from src.database.sqlite_handler import SQLiteDatabase
        >>> db = SQLiteDatabase({"path": "./test.db"})
        >>> manager = SchemaManager(db)
        >>> with db:
        ...     manager.create_all_tables()
    """

    def __init__(self, database: BaseDatabase):
        """Initialize schema manager.

        Args:
            database: Database handler instance
        """
        self.database = database

    def create_table(self, table_name: str) -> bool:
        """Create single table.

        Args:
            table_name: Name of table to create

        Returns:
            True if created successfully, False otherwise

        Examples:
            >>> manager.create_table("NL_RA_RACE")
            True
        """
        if table_name not in SCHEMAS:
            logger.error(f"Unknown table: {table_name}")
            return False

        try:
            schema = SCHEMAS[table_name]
            self.database.create_table(table_name, schema)
            logger.info(f"Created table: {table_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create table {table_name}", error=str(e))
            return False

    def create_all_tables(self) -> Dict[str, bool]:
        """Create all defined tables.

        Returns:
            Dictionary mapping table names to creation status

        Examples:
            >>> results = manager.create_all_tables()
            >>> print(results)
            {'NL_RA_RACE': True, 'NL_SE_RACE_UMA': True, 'NL_HR_PAY': True}
        """
        results = {}

        for table_name in SCHEMAS.keys():
            results[table_name] = self.create_table(table_name)

        success_count = sum(1 for v in results.values() if v)
        logger.info(
            f"Created {success_count}/{len(results)} tables",
            results=results,
        )

        return results

    def get_table_names(self) -> List[str]:
        """Get list of defined table names.

        Returns:
            List of table names
        """
        return list(SCHEMAS.keys())

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists in database.

        Args:
            table_name: Name of table to check

        Returns:
            True if table exists, False otherwise
        """
        return self.database.table_exists(table_name)

    def get_existing_tables(self) -> List[str]:
        """Get list of existing tables.

        Returns:
            List of table names that exist in database
        """
        existing = []
        for table_name in SCHEMAS.keys():
            if self.table_exists(table_name):
                existing.append(table_name)
        return existing

    def get_missing_tables(self) -> List[str]:
        """Get list of missing tables.

        Returns:
            List of table names that don't exist in database
        """
        missing = []
        for table_name in SCHEMAS.keys():
            if not self.table_exists(table_name):
                missing.append(table_name)
        return missing
