"""JRA-VAN Standard Database Schema Definitions.

Auto-generated from VB2019-Builder source code.
Compatible with PostgreSQL, SQLite.
"""

from typing import Dict


# JRA-VAN Standard Schema (52 tables)
JRAVAN_SCHEMAS: Dict[str, str] = {
    "BAMEIORIGIN": """
        CREATE TABLE IF NOT EXISTS BAMEIORIGIN (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Bamei                          VARCHAR(36)           -- 文字列(36)
        )
    """,
    "BANUSI": """
        CREATE TABLE IF NOT EXISTS BANUSI (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            BanusiName                     VARCHAR(255)        ,  -- テキスト
            BanusiName_Co                  VARCHAR(64)         ,  -- 文字列(64)
            BanusiNameKana                 VARCHAR(255)        ,  -- テキスト
            BanusiNameEng                  VARCHAR(255)        ,  -- テキスト
            Fukusyoku                      VARCHAR(255)        ,  -- テキスト
            H_SetYear                      VARCHAR(255)        ,  -- テキスト
            H_HonSyokinTotal               VARCHAR(255)        ,  -- テキスト
            H_FukaSyokin                   VARCHAR(255)        ,  -- テキスト
            H_ChakuKaisu1                  VARCHAR(255)        ,  -- テキスト
            H_ChakuKaisu2                  VARCHAR(255)        ,  -- テキスト
            H_ChakuKaisu3                  VARCHAR(255)        ,  -- テキスト
            H_ChakuKaisu4                  VARCHAR(255)        ,  -- テキスト
            H_ChakuKaisu5                  VARCHAR(255)        ,  -- テキスト
            H_ChakuKaisu6                  VARCHAR(255)        ,  -- テキスト
            R_SetYear                      VARCHAR(255)        ,  -- テキスト
            R_HonSyokinTotal               VARCHAR(255)        ,  -- テキスト
            R_FukaSyokin                   VARCHAR(255)        ,  -- テキスト
            R_ChakuKaisu1                  VARCHAR(255)        ,  -- テキスト
            R_ChakuKaisu2                  VARCHAR(255)        ,  -- テキスト
            R_ChakuKaisu3                  VARCHAR(255)        ,  -- テキスト
            R_ChakuKaisu4                  VARCHAR(255)        ,  -- テキスト
            R_ChakuKaisu5                  VARCHAR(255)          -- テキスト
        )
    """,
    "BATAIJYU": """
        CREATE TABLE IF NOT EXISTS BATAIJYU (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            HappyoTime                     TIMESTAMP           ,  -- 発表時刻
            Umaban1                        SMALLINT            ,  -- 馬番
            Bamei1                         VARCHAR(255)        ,  -- テキスト
            BaTaijyu1                      SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo1                     VARCHAR(255)        ,  -- テキスト
            ZogenSa1                       SMALLINT            ,  -- 増減(kg)
            Umaban2                        SMALLINT            ,  -- 馬番
            Bamei2                         VARCHAR(255)        ,  -- テキスト
            BaTaijyu2                      SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo2                     VARCHAR(255)        ,  -- テキスト
            ZogenSa2                       SMALLINT            ,  -- 増減(kg)
            Umaban3                        SMALLINT            ,  -- 馬番
            Bamei3                         VARCHAR(255)        ,  -- テキスト
            BaTaijyu3                      SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo3                     VARCHAR(255)        ,  -- テキスト
            ZogenSa3                       SMALLINT            ,  -- 増減(kg)
            Umaban4                        SMALLINT            ,  -- 馬番
            Bamei4                         VARCHAR(255)        ,  -- テキスト
            BaTaijyu4                      SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo4                     VARCHAR(255)        ,  -- テキスト
            ZogenSa4                       SMALLINT            ,  -- 増減(kg)
            Umaban5                        SMALLINT            ,  -- 馬番
            Bamei5                         VARCHAR(255)        ,  -- テキスト
            BaTaijyu5                      SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo5                     VARCHAR(255)        ,  -- テキスト
            ZogenSa5                       SMALLINT            ,  -- 増減(kg)
            Umaban6                        SMALLINT            ,  -- 馬番
            Bamei6                         VARCHAR(255)        ,  -- テキスト
            BaTaijyu6                      SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo6                     VARCHAR(255)        ,  -- テキスト
            ZogenSa6                       SMALLINT            ,  -- 増減(kg)
            Umaban7                        SMALLINT            ,  -- 馬番
            Bamei7                         VARCHAR(255)        ,  -- テキスト
            BaTaijyu7                      SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo7                     VARCHAR(255)        ,  -- テキスト
            ZogenSa7                       SMALLINT            ,  -- 増減(kg)
            Umaban8                        SMALLINT            ,  -- 馬番
            Bamei8                         VARCHAR(255)        ,  -- テキスト
            BaTaijyu8                      SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo8                     VARCHAR(255)        ,  -- テキスト
            ZogenSa8                       SMALLINT            ,  -- 増減(kg)
            Umaban9                        SMALLINT            ,  -- 馬番
            Bamei9                         VARCHAR(255)        ,  -- テキスト
            BaTaijyu9                      SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo9                     VARCHAR(255)        ,  -- テキスト
            ZogenSa9                       SMALLINT            ,  -- 増減(kg)
            Umaban10                       SMALLINT            ,  -- 馬番
            Bamei10                        VARCHAR(255)        ,  -- テキスト
            BaTaijyu10                     SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo10                    VARCHAR(255)        ,  -- テキスト
            ZogenSa10                      SMALLINT            ,  -- 増減(kg)
            Umaban11                       SMALLINT            ,  -- 馬番
            Bamei11                        VARCHAR(255)        ,  -- テキスト
            BaTaijyu11                     SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo11                    VARCHAR(255)        ,  -- テキスト
            ZogenSa11                      SMALLINT            ,  -- 増減(kg)
            Umaban12                       SMALLINT            ,  -- 馬番
            Bamei12                        VARCHAR(255)        ,  -- テキスト
            BaTaijyu12                     SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo12                    VARCHAR(255)        ,  -- テキスト
            ZogenSa12                      SMALLINT            ,  -- 増減(kg)
            Umaban13                       SMALLINT            ,  -- 馬番
            Bamei13                        VARCHAR(255)        ,  -- テキスト
            BaTaijyu13                     SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo13                    VARCHAR(255)        ,  -- テキスト
            ZogenSa13                      SMALLINT            ,  -- 増減(kg)
            Umaban14                       SMALLINT            ,  -- 馬番
            Bamei14                        VARCHAR(255)        ,  -- テキスト
            BaTaijyu14                     SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo14                    VARCHAR(255)        ,  -- テキスト
            ZogenSa14                      SMALLINT            ,  -- 増減(kg)
            Umaban15                       SMALLINT            ,  -- 馬番
            Bamei15                        VARCHAR(255)        ,  -- テキスト
            BaTaijyu15                     SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo15                    VARCHAR(255)        ,  -- テキスト
            ZogenSa15                      SMALLINT            ,  -- 増減(kg)
            Umaban16                       SMALLINT            ,  -- 馬番
            Bamei16                        VARCHAR(255)        ,  -- テキスト
            BaTaijyu16                     SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo16                    VARCHAR(255)        ,  -- テキスト
            ZogenSa16                      SMALLINT            ,  -- 増減(kg)
            Umaban17                       SMALLINT            ,  -- 馬番
            Bamei17                        VARCHAR(255)        ,  -- テキスト
            BaTaijyu17                     SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo17                    VARCHAR(255)        ,  -- テキスト
            ZogenSa17                      SMALLINT            ,  -- 増減(kg)
            Umaban18                       SMALLINT            ,  -- 馬番
            Bamei18                        VARCHAR(255)        ,  -- テキスト
            BaTaijyu18                     SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo18                    VARCHAR(255)        ,  -- テキスト
            ZogenSa18                      SMALLINT              -- 増減(kg)
        )
    """,
    "CHOKYO": """
        CREATE TABLE IF NOT EXISTS CHOKYO (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            DelKubun                       VARCHAR(255)        ,  -- テキスト
            IssueDate                      DATE                ,  -- 免許交付年月日
            DelDate                        DATE                ,  -- 抹消年月日
            BirthDate                      DATE                ,  -- 生年月日
            ChokyosiName                   VARCHAR(255)        ,  -- テキスト
            ChokyosiNameKana               VARCHAR(255)        ,  -- テキスト
            ChokyosiRyakusyo               VARCHAR(255)        ,  -- テキスト
            ChokyosiNameEng                VARCHAR(255)        ,  -- テキスト
            SexCD                          VARCHAR(255)        ,  -- テキスト
            TozaiCD                        VARCHAR(255)        ,  -- テキスト
            Syotai                         VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo1SaikinJyusyoid    VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo1Hondai            VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo1Ryakusyo10        VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo1Ryakusyo6         VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo1Ryakusyo3         VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo1GradeCD           VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo1SyussoTosu        VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo1KettoNum          VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo1Bamei             VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo2SaikinJyusyoid    VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo2Hondai            VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo2Ryakusyo10        VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo2Ryakusyo6         VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo2Ryakusyo3         VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo2GradeCD           VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo2SyussoTosu        VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo2KettoNum          VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo2Bamei             VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo3SaikinJyusyoid    VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo3Hondai            VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo3Ryakusyo10        VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo3Ryakusyo6         VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo3Ryakusyo3         VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo3GradeCD           VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo3SyussoTosu        VARCHAR(255)        ,  -- テキスト
            SaikinJyusyo3KettoNum          VARCHAR(255)          -- テキスト
        )
    """,
    "CHOKYO_SEISEKI": """
        CREATE TABLE IF NOT EXISTS CHOKYO_SEISEKI (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            ChokyosiCode                   VARCHAR(255)        ,  -- テキスト
            Num                            VARCHAR(255)        ,  -- テキスト
            SetYear                        VARCHAR(255)        ,  -- テキスト
            HonSyokinHeichi                VARCHAR(255)        ,  -- テキスト
            HonSyokinSyogai                VARCHAR(255)        ,  -- テキスト
            FukaSyokinHeichi               VARCHAR(255)        ,  -- テキスト
            FukaSyokinSyogai               VARCHAR(255)        ,  -- テキスト
            HeichiChakukaisu1              VARCHAR(255)        ,  -- テキスト
            HeichiChakukaisu2              VARCHAR(255)        ,  -- テキスト
            HeichiChakukaisu3              VARCHAR(255)        ,  -- テキスト
            HeichiChakukaisu4              VARCHAR(255)        ,  -- テキスト
            HeichiChakukaisu5              VARCHAR(255)        ,  -- テキスト
            HeichiChakukaisu6              VARCHAR(255)        ,  -- テキスト
            SyogaiChakukaisu1              VARCHAR(255)        ,  -- テキスト
            SyogaiChakukaisu2              VARCHAR(255)        ,  -- テキスト
            SyogaiChakukaisu3              VARCHAR(255)        ,  -- テキスト
            SyogaiChakukaisu4              VARCHAR(255)        ,  -- テキスト
            SyogaiChakukaisu5              VARCHAR(255)        ,  -- テキスト
            SyogaiChakukaisu6              VARCHAR(255)        ,  -- テキスト
            Jyo1Chakukaisu1                VARCHAR(255)        ,  -- テキスト
            Jyo1Chakukaisu2                VARCHAR(255)        ,  -- テキスト
            Jyo1Chakukaisu3                VARCHAR(255)        ,  -- テキスト
            Jyo1Chakukaisu4                VARCHAR(255)        ,  -- テキスト
            Jyo1Chakukaisu5                VARCHAR(255)        ,  -- テキスト
            Jyo1Chakukaisu6                VARCHAR(255)        ,  -- テキスト
            Jyo2Chakukaisu1                VARCHAR(255)        ,  -- テキスト
            Jyo2Chakukaisu2                VARCHAR(255)        ,  -- テキスト
            Jyo2Chakukaisu3                VARCHAR(255)        ,  -- テキスト
            Jyo2Chakukaisu4                VARCHAR(255)        ,  -- テキスト
            Jyo2Chakukaisu5                VARCHAR(255)        ,  -- テキスト
            Jyo2Chakukaisu6                VARCHAR(255)        ,  -- テキスト
            Jyo3Chakukaisu1                VARCHAR(255)        ,  -- テキスト
            Jyo3Chakukaisu2                VARCHAR(255)        ,  -- テキスト
            Jyo3Chakukaisu3                VARCHAR(255)        ,  -- テキスト
            Jyo3Chakukaisu4                VARCHAR(255)        ,  -- テキスト
            Jyo3Chakukaisu5                VARCHAR(255)        ,  -- テキスト
            Jyo3Chakukaisu6                VARCHAR(255)        ,  -- テキスト
            Jyo4Chakukaisu1                VARCHAR(255)        ,  -- テキスト
            Jyo4Chakukaisu2                VARCHAR(255)        ,  -- テキスト
            Jyo4Chakukaisu3                VARCHAR(255)        ,  -- テキスト
            Jyo4Chakukaisu4                VARCHAR(255)        ,  -- テキスト
            Jyo4Chakukaisu5                VARCHAR(255)        ,  -- テキスト
            Jyo4Chakukaisu6                VARCHAR(255)        ,  -- テキスト
            Jyo5Chakukaisu1                VARCHAR(255)        ,  -- テキスト
            Jyo5Chakukaisu2                VARCHAR(255)        ,  -- テキスト
            Jyo5Chakukaisu3                VARCHAR(255)        ,  -- テキスト
            Jyo5Chakukaisu4                VARCHAR(255)        ,  -- テキスト
            Jyo5Chakukaisu5                VARCHAR(255)        ,  -- テキスト
            Jyo5Chakukaisu6                VARCHAR(255)        ,  -- テキスト
            Jyo6Chakukaisu1                VARCHAR(255)        ,  -- テキスト
            Jyo6Chakukaisu2                VARCHAR(255)        ,  -- テキスト
            Jyo6Chakukaisu3                VARCHAR(255)        ,  -- テキスト
            Jyo6Chakukaisu4                VARCHAR(255)        ,  -- テキスト
            Jyo6Chakukaisu5                VARCHAR(255)        ,  -- テキスト
            Jyo6Chakukaisu6                VARCHAR(255)        ,  -- テキスト
            Jyo7Chakukaisu1                VARCHAR(255)        ,  -- テキスト
            Jyo7Chakukaisu2                VARCHAR(255)        ,  -- テキスト
            Jyo7Chakukaisu3                VARCHAR(255)        ,  -- テキスト
            Jyo7Chakukaisu4                VARCHAR(255)        ,  -- テキスト
            Jyo7Chakukaisu5                VARCHAR(255)        ,  -- テキスト
            Jyo7Chakukaisu6                VARCHAR(255)        ,  -- テキスト
            Jyo8Chakukaisu1                VARCHAR(255)        ,  -- テキスト
            Jyo8Chakukaisu2                VARCHAR(255)        ,  -- テキスト
            Jyo8Chakukaisu3                VARCHAR(255)        ,  -- テキスト
            Jyo8Chakukaisu4                VARCHAR(255)        ,  -- テキスト
            Jyo8Chakukaisu5                VARCHAR(255)        ,  -- テキスト
            Jyo8Chakukaisu6                VARCHAR(255)        ,  -- テキスト
            Jyo9Chakukaisu1                VARCHAR(255)        ,  -- テキスト
            Jyo9Chakukaisu2                VARCHAR(255)        ,  -- テキスト
            Jyo9Chakukaisu3                VARCHAR(255)        ,  -- テキスト
            Jyo9Chakukaisu4                VARCHAR(255)        ,  -- テキスト
            Jyo9Chakukaisu5                VARCHAR(255)        ,  -- テキスト
            Jyo9Chakukaisu6                VARCHAR(255)        ,  -- テキスト
            Jyo10Chakukaisu1               VARCHAR(255)        ,  -- テキスト
            Jyo10Chakukaisu2               VARCHAR(255)        ,  -- テキスト
            Jyo10Chakukaisu3               VARCHAR(255)        ,  -- テキスト
            Jyo10Chakukaisu4               VARCHAR(255)        ,  -- テキスト
            Jyo10Chakukaisu5               VARCHAR(255)        ,  -- テキスト
            Jyo10Chakukaisu6               VARCHAR(255)        ,  -- テキスト
            Jyo11Chakukaisu1               VARCHAR(255)        ,  -- テキスト
            Jyo11Chakukaisu2               VARCHAR(255)        ,  -- テキスト
            Jyo11Chakukaisu3               VARCHAR(255)        ,  -- テキスト
            Jyo11Chakukaisu4               VARCHAR(255)        ,  -- テキスト
            Jyo11Chakukaisu5               VARCHAR(255)        ,  -- テキスト
            Jyo11Chakukaisu6               VARCHAR(255)        ,  -- テキスト
            Jyo12Chakukaisu1               VARCHAR(255)        ,  -- テキスト
            Jyo12Chakukaisu2               VARCHAR(255)        ,  -- テキスト
            Jyo12Chakukaisu3               VARCHAR(255)        ,  -- テキスト
            Jyo12Chakukaisu4               VARCHAR(255)        ,  -- テキスト
            Jyo12Chakukaisu5               VARCHAR(255)        ,  -- テキスト
            Jyo12Chakukaisu6               VARCHAR(255)        ,  -- テキスト
            Jyo13Chakukaisu1               VARCHAR(255)        ,  -- テキスト
            Jyo13Chakukaisu2               VARCHAR(255)        ,  -- テキスト
            Jyo13Chakukaisu3               VARCHAR(255)        ,  -- テキスト
            Jyo13Chakukaisu4               VARCHAR(255)        ,  -- テキスト
            Jyo13Chakukaisu5               VARCHAR(255)        ,  -- テキスト
            Jyo13Chakukaisu6               VARCHAR(255)        ,  -- テキスト
            Jyo14Chakukaisu1               VARCHAR(255)        ,  -- テキスト
            Jyo14Chakukaisu2               VARCHAR(255)        ,  -- テキスト
            Jyo14Chakukaisu3               VARCHAR(255)        ,  -- テキスト
            Jyo14Chakukaisu4               VARCHAR(255)        ,  -- テキスト
            Jyo14Chakukaisu5               VARCHAR(255)        ,  -- テキスト
            Jyo14Chakukaisu6               VARCHAR(255)        ,  -- テキスト
            Jyo15Chakukaisu1               VARCHAR(255)        ,  -- テキスト
            Jyo15Chakukaisu2               VARCHAR(255)        ,  -- テキスト
            Jyo15Chakukaisu3               VARCHAR(255)        ,  -- テキスト
            Jyo15Chakukaisu4               VARCHAR(255)        ,  -- テキスト
            Jyo15Chakukaisu5               VARCHAR(255)        ,  -- テキスト
            Jyo15Chakukaisu6               VARCHAR(255)        ,  -- テキスト
            Jyo16Chakukaisu1               VARCHAR(255)        ,  -- テキスト
            Jyo16Chakukaisu2               VARCHAR(255)        ,  -- テキスト
            Jyo16Chakukaisu3               VARCHAR(255)        ,  -- テキスト
            Jyo16Chakukaisu4               VARCHAR(255)        ,  -- テキスト
            Jyo16Chakukaisu5               VARCHAR(255)        ,  -- テキスト
            Jyo16Chakukaisu6               VARCHAR(255)        ,  -- テキスト
            Jyo17Chakukaisu1               VARCHAR(255)        ,  -- テキスト
            Jyo17Chakukaisu2               VARCHAR(255)        ,  -- テキスト
            Jyo17Chakukaisu3               VARCHAR(255)        ,  -- テキスト
            Jyo17Chakukaisu4               VARCHAR(255)        ,  -- テキスト
            Jyo17Chakukaisu5               VARCHAR(255)        ,  -- テキスト
            Jyo17Chakukaisu6               VARCHAR(255)        ,  -- テキスト
            Jyo18Chakukaisu1               VARCHAR(255)        ,  -- テキスト
            Jyo18Chakukaisu2               VARCHAR(255)        ,  -- テキスト
            Jyo18Chakukaisu3               VARCHAR(255)        ,  -- テキスト
            Jyo18Chakukaisu4               VARCHAR(255)        ,  -- テキスト
            Jyo18Chakukaisu5               VARCHAR(255)        ,  -- テキスト
            Jyo18Chakukaisu6               VARCHAR(255)        ,  -- テキスト
            Jyo19Chakukaisu1               VARCHAR(255)        ,  -- テキスト
            Jyo19Chakukaisu2               VARCHAR(255)        ,  -- テキスト
            Jyo19Chakukaisu3               VARCHAR(255)        ,  -- テキスト
            Jyo19Chakukaisu4               VARCHAR(255)        ,  -- テキスト
            Jyo19Chakukaisu5               VARCHAR(255)        ,  -- テキスト
            Jyo19Chakukaisu6               VARCHAR(255)        ,  -- テキスト
            Jyo20Chakukaisu1               VARCHAR(255)        ,  -- テキスト
            Jyo20Chakukaisu2               VARCHAR(255)        ,  -- テキスト
            Jyo20Chakukaisu3               VARCHAR(255)        ,  -- テキスト
            Jyo20Chakukaisu4               VARCHAR(255)        ,  -- テキスト
            Jyo20Chakukaisu5               VARCHAR(255)        ,  -- テキスト
            Jyo20Chakukaisu6               VARCHAR(255)        ,  -- テキスト
            Kyori1Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu6              SMALLINT              -- 距離(m)
        )
    """,
    "COURSE": """
        CREATE TABLE IF NOT EXISTS COURSE (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kyori                          SMALLINT            ,  -- 距離(m)
            TrackCD                        VARCHAR(2)          ,  -- 文字列(2)
            KaishuDate                     VARCHAR(8)            -- 文字列(8)
        )
    """,
    "COURSE_CHANGE": """
        CREATE TABLE IF NOT EXISTS COURSE_CHANGE (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            HappyoTime                     TIMESTAMP           ,  -- 発表時刻
            AtoKyori                       VARCHAR(4)          ,  -- 文字列(4)
            AtoTruckCD                     VARCHAR(2)          ,  -- 文字列(2)
            MaeKyori                       VARCHAR(4)          ,  -- 文字列(4)
            MaeTruckCD                     VARCHAR(2)          ,  -- 文字列(2)
            JiyuCD                         VARCHAR(1)            -- 文字列(1)
        )
    """,
    "HANRO": """
        CREATE TABLE IF NOT EXISTS HANRO (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            TresenKubun                    VARCHAR(255)        ,  -- テキスト
            ChokyoDate                     VARCHAR(255)        ,  -- テキスト
            ChokyoTime                     VARCHAR(255)        ,  -- テキスト
            KettoNum                       VARCHAR(255)        ,  -- テキスト
            HaronTime4                     VARCHAR(255)        ,  -- テキスト
            LapTime4                       VARCHAR(255)        ,  -- テキスト
            HaronTime3                     VARCHAR(255)        ,  -- テキスト
            LapTime3                       DECIMAL(4,1)        ,  -- ラップタイム3
            HaronTime2                     VARCHAR(255)        ,  -- テキスト
            LapTime2                       DECIMAL(4,1)        ,  -- ラップタイム2
            LapTime1                       DECIMAL(4,1)          -- ラップタイム1(秒)
        )
    """,
    "HANSYOKU": """
        CREATE TABLE IF NOT EXISTS HANSYOKU (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            reserved                       VARCHAR(255)        ,  -- テキスト
            KettoNum                       VARCHAR(255)        ,  -- テキスト
            DelKubun                       VARCHAR(255)        ,  -- テキスト
            Bamei                          VARCHAR(255)        ,  -- テキスト
            BameiKana                      VARCHAR(255)        ,  -- テキスト
            BameiEng                       VARCHAR(255)        ,  -- テキスト
            BirthYear                      VARCHAR(255)        ,  -- テキスト
            SexCD                          VARCHAR(255)        ,  -- テキスト
            HinsyuCD                       VARCHAR(255)        ,  -- テキスト
            KeiroCD                        VARCHAR(255)        ,  -- テキスト
            HansyokuMochiKubun             VARCHAR(255)        ,  -- テキスト
            ImportYear                     VARCHAR(255)        ,  -- テキスト
            SanchiName                     VARCHAR(255)        ,  -- テキスト
            HansyokuFNum                   VARCHAR(255)          -- テキスト
        )
    """,
    "HARAI": """
        CREATE TABLE IF NOT EXISTS HARAI (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            TorokuTosu                     SMALLINT            ,  -- 登録頭数
            SyussoTosu                     SMALLINT            ,  -- 出走頭数
            FuseirituFlag1                 VARCHAR(255)        ,  -- テキスト
            FuseirituFlag2                 VARCHAR(255)        ,  -- テキスト
            FuseirituFlag3                 VARCHAR(255)        ,  -- テキスト
            FuseirituFlag4                 VARCHAR(255)        ,  -- テキスト
            FuseirituFlag5                 VARCHAR(255)        ,  -- テキスト
            FuseirituFlag6                 VARCHAR(255)        ,  -- テキスト
            FuseirituFlag7                 VARCHAR(255)        ,  -- テキスト
            FuseirituFlag8                 VARCHAR(255)        ,  -- テキスト
            FuseirituFlag9                 VARCHAR(255)        ,  -- テキスト
            TokubaraiFlag1                 VARCHAR(255)        ,  -- テキスト
            TokubaraiFlag2                 VARCHAR(255)        ,  -- テキスト
            TokubaraiFlag3                 VARCHAR(255)        ,  -- テキスト
            TokubaraiFlag4                 VARCHAR(255)        ,  -- テキスト
            TokubaraiFlag5                 VARCHAR(255)        ,  -- テキスト
            TokubaraiFlag6                 VARCHAR(255)        ,  -- テキスト
            TokubaraiFlag7                 VARCHAR(255)        ,  -- テキスト
            TokubaraiFlag8                 VARCHAR(255)        ,  -- テキスト
            TokubaraiFlag9                 VARCHAR(255)        ,  -- テキスト
            HenkanFlag1                    VARCHAR(255)        ,  -- テキスト
            HenkanFlag2                    VARCHAR(255)        ,  -- テキスト
            HenkanFlag3                    VARCHAR(255)        ,  -- テキスト
            HenkanFlag4                    VARCHAR(255)        ,  -- テキスト
            HenkanFlag5                    VARCHAR(255)        ,  -- テキスト
            HenkanFlag6                    VARCHAR(255)        ,  -- テキスト
            HenkanFlag7                    VARCHAR(255)        ,  -- テキスト
            HenkanFlag8                    VARCHAR(255)        ,  -- テキスト
            HenkanFlag9                    VARCHAR(255)        ,  -- テキスト
            HenkanUma1                     VARCHAR(255)        ,  -- テキスト
            HenkanUma2                     VARCHAR(255)        ,  -- テキスト
            HenkanUma3                     VARCHAR(255)        ,  -- テキスト
            HenkanUma4                     VARCHAR(255)        ,  -- テキスト
            HenkanUma5                     VARCHAR(255)        ,  -- テキスト
            HenkanUma6                     VARCHAR(255)        ,  -- テキスト
            HenkanUma7                     VARCHAR(255)        ,  -- テキスト
            HenkanUma8                     VARCHAR(255)        ,  -- テキスト
            HenkanUma9                     VARCHAR(255)        ,  -- テキスト
            HenkanUma10                    VARCHAR(255)        ,  -- テキスト
            HenkanUma11                    VARCHAR(255)        ,  -- テキスト
            HenkanUma12                    VARCHAR(255)        ,  -- テキスト
            HenkanUma13                    VARCHAR(255)        ,  -- テキスト
            HenkanUma14                    VARCHAR(255)        ,  -- テキスト
            HenkanUma15                    VARCHAR(255)        ,  -- テキスト
            HenkanUma16                    VARCHAR(255)        ,  -- テキスト
            HenkanUma17                    VARCHAR(255)        ,  -- テキスト
            HenkanUma18                    VARCHAR(255)        ,  -- テキスト
            HenkanUma19                    VARCHAR(255)        ,  -- テキスト
            HenkanUma20                    VARCHAR(255)        ,  -- テキスト
            HenkanUma21                    VARCHAR(255)        ,  -- テキスト
            HenkanUma22                    VARCHAR(255)        ,  -- テキスト
            HenkanUma23                    VARCHAR(255)        ,  -- テキスト
            HenkanUma24                    VARCHAR(255)        ,  -- テキスト
            HenkanUma25                    VARCHAR(255)        ,  -- テキスト
            HenkanUma26                    VARCHAR(255)        ,  -- テキスト
            HenkanUma27                    VARCHAR(255)        ,  -- テキスト
            HenkanUma28                    VARCHAR(255)        ,  -- テキスト
            HenkanWaku1                    VARCHAR(255)        ,  -- テキスト
            HenkanWaku2                    VARCHAR(255)        ,  -- テキスト
            HenkanWaku3                    VARCHAR(255)        ,  -- テキスト
            HenkanWaku4                    VARCHAR(255)        ,  -- テキスト
            HenkanWaku5                    VARCHAR(255)        ,  -- テキスト
            HenkanWaku6                    VARCHAR(255)        ,  -- テキスト
            HenkanWaku7                    VARCHAR(255)        ,  -- テキスト
            HenkanWaku8                    VARCHAR(255)        ,  -- テキスト
            HenkanDoWaku1                  VARCHAR(255)        ,  -- テキスト
            HenkanDoWaku2                  VARCHAR(255)        ,  -- テキスト
            HenkanDoWaku3                  VARCHAR(255)        ,  -- テキスト
            HenkanDoWaku4                  VARCHAR(255)        ,  -- テキスト
            HenkanDoWaku5                  VARCHAR(255)        ,  -- テキスト
            HenkanDoWaku6                  VARCHAR(255)        ,  -- テキスト
            HenkanDoWaku7                  VARCHAR(255)        ,  -- テキスト
            HenkanDoWaku8                  VARCHAR(255)        ,  -- テキスト
            PayTansyoUmaban1               VARCHAR(255)        ,  -- テキスト
            PayTansyoPay1                  VARCHAR(255)        ,  -- テキスト
            PayTansyoNinki1                VARCHAR(255)        ,  -- テキスト
            PayTansyoUmaban2               VARCHAR(255)        ,  -- テキスト
            PayTansyoPay2                  VARCHAR(255)        ,  -- テキスト
            PayTansyoNinki2                VARCHAR(255)        ,  -- テキスト
            PayTansyoUmaban3               VARCHAR(255)        ,  -- テキスト
            PayTansyoPay3                  VARCHAR(255)        ,  -- テキスト
            PayTansyoNinki3                VARCHAR(255)        ,  -- テキスト
            PayFukusyoUmaban1              VARCHAR(255)        ,  -- テキスト
            PayFukusyoPay1                 VARCHAR(255)        ,  -- テキスト
            PayFukusyoNinki1               VARCHAR(255)        ,  -- テキスト
            PayFukusyoUmaban2              VARCHAR(255)        ,  -- テキスト
            PayFukusyoPay2                 VARCHAR(255)        ,  -- テキスト
            PayFukusyoNinki2               VARCHAR(255)        ,  -- テキスト
            PayFukusyoUmaban3              VARCHAR(255)        ,  -- テキスト
            PayFukusyoPay3                 VARCHAR(255)        ,  -- テキスト
            PayFukusyoNinki3               VARCHAR(255)        ,  -- テキスト
            PayFukusyoUmaban4              VARCHAR(255)        ,  -- テキスト
            PayFukusyoPay4                 VARCHAR(255)        ,  -- テキスト
            PayFukusyoNinki4               VARCHAR(255)        ,  -- テキスト
            PayFukusyoUmaban5              VARCHAR(255)        ,  -- テキスト
            PayFukusyoPay5                 VARCHAR(255)        ,  -- テキスト
            PayFukusyoNinki5               VARCHAR(255)        ,  -- テキスト
            PayWakurenKumi1                VARCHAR(255)        ,  -- テキスト
            PayWakurenPay1                 VARCHAR(255)        ,  -- テキスト
            PayWakurenNinki1               VARCHAR(255)        ,  -- テキスト
            PayWakurenKumi2                VARCHAR(255)        ,  -- テキスト
            PayWakurenPay2                 VARCHAR(255)        ,  -- テキスト
            PayWakurenNinki2               VARCHAR(255)        ,  -- テキスト
            PayWakurenKumi3                VARCHAR(255)        ,  -- テキスト
            PayWakurenPay3                 VARCHAR(255)        ,  -- テキスト
            PayWakurenNinki3               VARCHAR(255)        ,  -- テキスト
            PayUmarenKumi1                 VARCHAR(255)        ,  -- テキスト
            PayUmarenPay1                  VARCHAR(255)        ,  -- テキスト
            PayUmarenNinki1                VARCHAR(255)        ,  -- テキスト
            PayUmarenKumi2                 VARCHAR(255)        ,  -- テキスト
            PayUmarenPay2                  VARCHAR(255)        ,  -- テキスト
            PayUmarenNinki2                VARCHAR(255)        ,  -- テキスト
            PayUmarenKumi3                 VARCHAR(255)        ,  -- テキスト
            PayUmarenPay3                  VARCHAR(255)        ,  -- テキスト
            PayUmarenNinki3                VARCHAR(255)        ,  -- テキスト
            PayWideKumi1                   VARCHAR(255)        ,  -- テキスト
            PayWidePay1                    VARCHAR(255)        ,  -- テキスト
            PayWideNinki1                  VARCHAR(255)        ,  -- テキスト
            PayWideKumi2                   VARCHAR(255)        ,  -- テキスト
            PayWidePay2                    VARCHAR(255)        ,  -- テキスト
            PayWideNinki2                  VARCHAR(255)        ,  -- テキスト
            PayWideKumi3                   VARCHAR(255)        ,  -- テキスト
            PayWidePay3                    VARCHAR(255)        ,  -- テキスト
            PayWideNinki3                  VARCHAR(255)        ,  -- テキスト
            PayWideKumi4                   VARCHAR(255)        ,  -- テキスト
            PayWidePay4                    VARCHAR(255)        ,  -- テキスト
            PayWideNinki4                  VARCHAR(255)        ,  -- テキスト
            PayWideKumi5                   VARCHAR(255)        ,  -- テキスト
            PayWidePay5                    VARCHAR(255)        ,  -- テキスト
            PayWideNinki5                  VARCHAR(255)        ,  -- テキスト
            PayWideKumi6                   VARCHAR(255)        ,  -- テキスト
            PayWidePay6                    VARCHAR(255)        ,  -- テキスト
            PayWideNinki6                  VARCHAR(255)        ,  -- テキスト
            PayWideKumi7                   VARCHAR(255)        ,  -- テキスト
            PayWidePay7                    VARCHAR(255)        ,  -- テキスト
            PayWideNinki7                  VARCHAR(255)        ,  -- テキスト
            PayReserved1Kumi1              VARCHAR(255)        ,  -- テキスト
            PayReserved1Pay1               VARCHAR(255)        ,  -- テキスト
            PayReserved1Ninki1             VARCHAR(255)        ,  -- テキスト
            PayReserved1Kumi2              VARCHAR(255)        ,  -- テキスト
            PayReserved1Pay2               VARCHAR(255)        ,  -- テキスト
            PayReserved1Ninki2             VARCHAR(255)        ,  -- テキスト
            PayReserved1Kumi3              VARCHAR(255)        ,  -- テキスト
            PayReserved1Pay3               VARCHAR(255)        ,  -- テキスト
            PayReserved1Ninki3             VARCHAR(255)        ,  -- テキスト
            PayUmatanKumi1                 VARCHAR(255)        ,  -- テキスト
            PayUmatanPay1                  VARCHAR(255)        ,  -- テキスト
            PayUmatanNinki1                VARCHAR(255)        ,  -- テキスト
            PayUmatanKumi2                 VARCHAR(255)        ,  -- テキスト
            PayUmatanPay2                  VARCHAR(255)        ,  -- テキスト
            PayUmatanNinki2                VARCHAR(255)        ,  -- テキスト
            PayUmatanKumi3                 VARCHAR(255)        ,  -- テキスト
            PayUmatanPay3                  VARCHAR(255)        ,  -- テキスト
            PayUmatanNinki3                VARCHAR(255)        ,  -- テキスト
            PayUmatanKumi4                 VARCHAR(255)        ,  -- テキスト
            PayUmatanPay4                  VARCHAR(255)        ,  -- テキスト
            PayUmatanNinki4                VARCHAR(255)        ,  -- テキスト
            PayUmatanKumi5                 VARCHAR(255)        ,  -- テキスト
            PayUmatanPay5                  VARCHAR(255)        ,  -- テキスト
            PayUmatanNinki5                VARCHAR(255)        ,  -- テキスト
            PayUmatanKumi6                 VARCHAR(255)        ,  -- テキスト
            PayUmatanPay6                  VARCHAR(255)        ,  -- テキスト
            PayUmatanNinki6                VARCHAR(255)        ,  -- テキスト
            PaySanrenpukuKumi1             VARCHAR(255)        ,  -- テキスト
            PaySanrenpukuPay1              VARCHAR(255)        ,  -- テキスト
            PaySanrenpukuNinki1            VARCHAR(255)        ,  -- テキスト
            PaySanrenpukuKumi2             VARCHAR(255)        ,  -- テキスト
            PaySanrenpukuPay2              VARCHAR(255)        ,  -- テキスト
            PaySanrenpukuNinki2            VARCHAR(255)        ,  -- テキスト
            PaySanrenpukuKumi3             VARCHAR(255)        ,  -- テキスト
            PaySanrenpukuPay3              VARCHAR(255)        ,  -- テキスト
            PaySanrenpukuNinki3            VARCHAR(255)        ,  -- テキスト
            PaySanrentanKumi1              VARCHAR(255)        ,  -- テキスト
            PaySanrentanPay1               VARCHAR(255)        ,  -- テキスト
            PaySanrentanNinki1             VARCHAR(255)        ,  -- テキスト
            PaySanrentanKumi2              VARCHAR(255)        ,  -- テキスト
            PaySanrentanPay2               VARCHAR(255)        ,  -- テキスト
            PaySanrentanNinki2             VARCHAR(255)        ,  -- テキスト
            PaySanrentanKumi3              VARCHAR(255)        ,  -- テキスト
            PaySanrentanPay3               VARCHAR(255)        ,  -- テキスト
            PaySanrentanNinki3             VARCHAR(255)        ,  -- テキスト
            PaySanrentanKumi4              VARCHAR(255)        ,  -- テキスト
            PaySanrentanPay4               VARCHAR(255)        ,  -- テキスト
            PaySanrentanNinki4             VARCHAR(255)        ,  -- テキスト
            PaySanrentanKumi5              VARCHAR(255)        ,  -- テキスト
            PaySanrentanPay5               VARCHAR(255)        ,  -- テキスト
            PaySanrentanNinki5             VARCHAR(255)        ,  -- テキスト
            PaySanrentanKumi6              VARCHAR(255)        ,  -- テキスト
            PaySanrentanPay6               VARCHAR(255)        ,  -- テキスト
            PaySanrentanNinki6             VARCHAR(255)          -- テキスト
        )
    """,
    "HASSOU_JIKOKU_CHANGE": """
        CREATE TABLE IF NOT EXISTS HASSOU_JIKOKU_CHANGE (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            HappyoTime                     TIMESTAMP           ,  -- 発表時刻
            AtoJi                          VARCHAR(2)          ,  -- 文字列(2)
            AtoFun                         VARCHAR(2)          ,  -- 文字列(2)
            MaeJi                          VARCHAR(2)          ,  -- 文字列(2)
            MaeFun                         VARCHAR(2)            -- 文字列(2)
        )
    """,
    "HYOSU": """
        CREATE TABLE IF NOT EXISTS HYOSU (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            TorokuTosu                     SMALLINT            ,  -- 登録頭数
            SyussoTosu                     SMALLINT            ,  -- 出走頭数
            HatubaiFlag1                   VARCHAR(1)          ,  -- 文字列(1)
            HatubaiFlag2                   VARCHAR(1)          ,  -- 文字列(1)
            HatubaiFlag3                   VARCHAR(1)          ,  -- 文字列(1)
            HatubaiFlag4                   VARCHAR(1)          ,  -- 文字列(1)
            HatubaiFlag5                   VARCHAR(1)          ,  -- 文字列(1)
            HatubaiFlag6                   VARCHAR(1)          ,  -- 文字列(1)
            HatubaiFlag7                   VARCHAR(1)          ,  -- 文字列(1)
            FukuChakuBaraiKey              VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma1                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma2                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma3                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma4                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma5                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma6                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma7                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma8                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma9                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma10                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma11                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma12                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma13                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma14                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma15                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma16                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma17                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma18                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma19                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma20                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma21                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma22                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma23                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma24                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma25                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma26                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma27                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma28                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanWaku1                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanWaku2                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanWaku3                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanWaku4                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanWaku5                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanWaku6                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanWaku7                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanWaku8                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanDoWaku1                  VARCHAR(1)          ,  -- 文字列(1)
            HenkanDoWaku2                  VARCHAR(1)          ,  -- 文字列(1)
            HenkanDoWaku3                  VARCHAR(1)          ,  -- 文字列(1)
            HenkanDoWaku4                  VARCHAR(1)          ,  -- 文字列(1)
            HenkanDoWaku5                  VARCHAR(1)          ,  -- 文字列(1)
            HenkanDoWaku6                  VARCHAR(1)          ,  -- 文字列(1)
            HenkanDoWaku7                  VARCHAR(1)          ,  -- 文字列(1)
            HenkanDoWaku8                  VARCHAR(1)          ,  -- 文字列(1)
            HyoTotal1                      VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal2                      VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal3                      VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal4                      VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal5                      VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal6                      VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal7                      VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal8                      VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal9                      VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal10                     VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal11                     VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal12                     VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal13                     VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal14                     VARCHAR(11)           -- 文字列(11)
        )
    """,
    "HYOSU2": """
        CREATE TABLE IF NOT EXISTS HYOSU2 (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            TorokuTosu                     SMALLINT            ,  -- 登録頭数
            SyussoTosu                     SMALLINT            ,  -- 出走頭数
            HatubaiFlag1                   VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma1                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma2                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma3                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma4                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma5                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma6                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma7                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma8                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma9                     VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma10                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma11                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma12                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma13                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma14                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma15                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma16                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma17                    VARCHAR(1)          ,  -- 文字列(1)
            HenkanUma18                    VARCHAR(1)          ,  -- 文字列(1)
            HyoTotal1                      VARCHAR(11)         ,  -- 文字列(11)
            HyoTotal2                      VARCHAR(11)           -- 文字列(11)
        )
    """,
    "HYOSU_SANREN": """
        CREATE TABLE IF NOT EXISTS HYOSU_SANREN (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Kumi                           VARCHAR(6)          ,  -- 文字列(6)
            Hyo                            VARCHAR(11)         ,  -- 文字列(11)
            Ninki                          SMALLINT              -- 人気
        )
    """,
    "HYOSU_SANRENTAN": """
        CREATE TABLE IF NOT EXISTS HYOSU_SANRENTAN (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Kumi                           VARCHAR(6)          ,  -- 文字列(6)
            Hyo                            VARCHAR(11)         ,  -- 文字列(11)
            Ninki                          SMALLINT              -- 人気
        )
    """,
    "HYOSU_TANPUKU": """
        CREATE TABLE IF NOT EXISTS HYOSU_TANPUKU (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Umaban                         SMALLINT            ,  -- 馬番
            TanHyo                         VARCHAR(11)         ,  -- 文字列(11)
            TanNinki                       VARCHAR(2)          ,  -- 文字列(2)
            FukuHyo                        VARCHAR(11)         ,  -- 文字列(11)
            FukuNinki                      VARCHAR(2)            -- 文字列(2)
        )
    """,
    "HYOSU_UMARENWIDE": """
        CREATE TABLE IF NOT EXISTS HYOSU_UMARENWIDE (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Kumi                           VARCHAR(4)          ,  -- 文字列(4)
            UmarenHyo                      VARCHAR(11)         ,  -- 文字列(11)
            UmarenNinki                    VARCHAR(3)          ,  -- 文字列(3)
            WideHyo                        VARCHAR(11)         ,  -- 文字列(11)
            WideNinki                      VARCHAR(3)            -- 文字列(3)
        )
    """,
    "HYOSU_UMATAN": """
        CREATE TABLE IF NOT EXISTS HYOSU_UMATAN (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Kumi                           VARCHAR(4)          ,  -- 文字列(4)
            Hyo                            VARCHAR(11)         ,  -- 文字列(11)
            Ninki                          SMALLINT              -- 人気
        )
    """,
    "HYOSU_WAKU": """
        CREATE TABLE IF NOT EXISTS HYOSU_WAKU (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Kumi                           VARCHAR(2)          ,  -- 文字列(2)
            Hyo                            VARCHAR(11)         ,  -- 文字列(11)
            Ninki                          SMALLINT              -- 人気
        )
    """,
    "JYUSYOSIKI": """
        CREATE TABLE IF NOT EXISTS JYUSYOSIKI (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            Kumi                           VARCHAR(10)         ,  -- 文字列(10)
            PayJyushosiki                  VARCHAR(9)          ,  -- 文字列(9)
            TekichuHyo                     VARCHAR(10)           -- 文字列(10)
        )
    """,
    "JYUSYOSIKI_HEAD": """
        CREATE TABLE IF NOT EXISTS JYUSYOSIKI_HEAD (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            reserved1                      VARCHAR(2)          ,  -- 文字列(2)
            JyoCD1                         CHAR(2)             ,  -- 競馬場コード
            Kaiji1                         SMALLINT            ,  -- 開催回
            Nichiji1                       SMALLINT            ,  -- 開催日目
            RaceNum1                       SMALLINT            ,  -- レース番号
            JyoCD2                         CHAR(2)             ,  -- 競馬場コード
            Kaiji2                         SMALLINT            ,  -- 開催回
            Nichiji2                       SMALLINT            ,  -- 開催日目
            RaceNum2                       SMALLINT            ,  -- レース番号
            JyoCD3                         CHAR(2)             ,  -- 競馬場コード
            Kaiji3                         SMALLINT            ,  -- 開催回
            Nichiji3                       SMALLINT            ,  -- 開催日目
            RaceNum3                       SMALLINT            ,  -- レース番号
            JyoCD4                         CHAR(2)             ,  -- 競馬場コード
            Kaiji4                         SMALLINT            ,  -- 開催回
            Nichiji4                       SMALLINT            ,  -- 開催日目
            RaceNum4                       SMALLINT            ,  -- レース番号
            JyoCD5                         CHAR(2)             ,  -- 競馬場コード
            Kaiji5                         SMALLINT            ,  -- 開催回
            Nichiji5                       SMALLINT            ,  -- 開催日目
            RaceNum5                       SMALLINT            ,  -- レース番号
            reserved2                      VARCHAR(6)          ,  -- 文字列(6)
            YukoHyosu1                     VARCHAR(11)         ,  -- 文字列(11)
            YukoHyosu2                     VARCHAR(11)         ,  -- 文字列(11)
            YukoHyosu3                     VARCHAR(11)         ,  -- 文字列(11)
            YukoHyosu4                     VARCHAR(11)         ,  -- 文字列(11)
            YukoHyosu5                     VARCHAR(11)         ,  -- 文字列(11)
            HenkanFlag                     VARCHAR(1)          ,  -- 文字列(1)
            FuseirituFlag                  VARCHAR(1)          ,  -- 文字列(1)
            TekichunashiFlag               VARCHAR(1)          ,  -- 文字列(1)
            CarryoverSyoki                 VARCHAR(15)         ,  -- 文字列(15)
            CarryoverZandaka               VARCHAR(15)           -- 文字列(15)
        )
    """,
    "KEITO": """
        CREATE TABLE IF NOT EXISTS KEITO (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            KeitoId                        VARCHAR(30)         ,  -- 文字列(30)
            KeitoName                      VARCHAR(36)           -- 文字列(36)
        )
    """,
    "KISYU": """
        CREATE TABLE IF NOT EXISTS KISYU (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            DelKubun                       VARCHAR(1)          ,  -- 文字列(1)
            IssueDate                      DATE                ,  -- 免許交付年月日
            DelDate                        DATE                ,  -- 抹消年月日
            BirthDate                      DATE                ,  -- 生年月日
            KisyuName                      VARCHAR(34)         ,  -- 文字列(34)
            reserved                       VARCHAR(34)         ,  -- 文字列(34)
            KisyuNameKana                  VARCHAR(30)         ,  -- 文字列(30)
            KisyuRyakusyo                  VARCHAR(8)          ,  -- 文字列(8)
            KisyuNameEng                   VARCHAR(80)         ,  -- 文字列(80)
            SexCD                          VARCHAR(1)          ,  -- 文字列(1)
            SikakuCD                       VARCHAR(1)          ,  -- 文字列(1)
            MinaraiCD                      VARCHAR(1)          ,  -- 文字列(1)
            TozaiCD                        VARCHAR(1)          ,  -- 文字列(1)
            Syotai                         VARCHAR(20)         ,  -- 文字列(20)
            ChokyosiCode                   VARCHAR(5)          ,  -- 文字列(5)
            ChokyosiRyakusyo               VARCHAR(8)          ,  -- 文字列(8)
            HatuKiJyo1Hatukijyoid          VARCHAR(16)         ,  -- 文字列(16)
            HatuKiJyo1SyussoTosu           VARCHAR(2)          ,  -- 文字列(2)
            HatuKiJyo1KettoNum             VARCHAR(10)         ,  -- 文字列(10)
            HatuKiJyo1Bamei                VARCHAR(36)         ,  -- 文字列(36)
            HatuKiJyo1KakuteiJyuni         VARCHAR(2)          ,  -- 文字列(2)
            HatuKiJyo1IJyoCD               VARCHAR(1)          ,  -- 文字列(1)
            HatuKiJyo2Hatukijyoid          VARCHAR(16)         ,  -- 文字列(16)
            HatuKiJyo2SyussoTosu           VARCHAR(2)          ,  -- 文字列(2)
            HatuKiJyo2KettoNum             VARCHAR(10)         ,  -- 文字列(10)
            HatuKiJyo2Bamei                VARCHAR(36)         ,  -- 文字列(36)
            HatuKiJyo2KakuteiJyuni         VARCHAR(2)          ,  -- 文字列(2)
            HatuKiJyo2IJyoCD               VARCHAR(1)          ,  -- 文字列(1)
            HatuSyori1Hatusyoriid          VARCHAR(16)         ,  -- 文字列(16)
            HatuSyori1SyussoTosu           VARCHAR(2)          ,  -- 文字列(2)
            HatuSyori1KettoNum             VARCHAR(10)         ,  -- 文字列(10)
            HatuSyori1Bamei                VARCHAR(36)         ,  -- 文字列(36)
            HatuSyori2Hatusyoriid          VARCHAR(16)         ,  -- 文字列(16)
            HatuSyori2SyussoTosu           VARCHAR(2)          ,  -- 文字列(2)
            HatuSyori2KettoNum             VARCHAR(10)         ,  -- 文字列(10)
            HatuSyori2Bamei                VARCHAR(36)         ,  -- 文字列(36)
            SaikinJyusyo1SaikinJyusyoid    VARCHAR(16)         ,  -- 文字列(16)
            SaikinJyusyo1Hondai            VARCHAR(60)         ,  -- 文字列(60)
            SaikinJyusyo1Ryakusyo10        VARCHAR(20)         ,  -- 文字列(20)
            SaikinJyusyo1Ryakusyo6         VARCHAR(12)         ,  -- 文字列(12)
            SaikinJyusyo1Ryakusyo3         VARCHAR(6)          ,  -- 文字列(6)
            SaikinJyusyo1GradeCD           VARCHAR(1)          ,  -- 文字列(1)
            SaikinJyusyo1SyussoTosu        VARCHAR(2)          ,  -- 文字列(2)
            SaikinJyusyo1KettoNum          VARCHAR(10)         ,  -- 文字列(10)
            SaikinJyusyo1Bamei             VARCHAR(36)         ,  -- 文字列(36)
            SaikinJyusyo2SaikinJyusyoid    VARCHAR(16)         ,  -- 文字列(16)
            SaikinJyusyo2Hondai            VARCHAR(60)         ,  -- 文字列(60)
            SaikinJyusyo2Ryakusyo10        VARCHAR(20)         ,  -- 文字列(20)
            SaikinJyusyo2Ryakusyo6         VARCHAR(12)         ,  -- 文字列(12)
            SaikinJyusyo2Ryakusyo3         VARCHAR(6)          ,  -- 文字列(6)
            SaikinJyusyo2GradeCD           VARCHAR(1)          ,  -- 文字列(1)
            SaikinJyusyo2SyussoTosu        VARCHAR(2)          ,  -- 文字列(2)
            SaikinJyusyo2KettoNum          VARCHAR(10)         ,  -- 文字列(10)
            SaikinJyusyo2Bamei             VARCHAR(36)         ,  -- 文字列(36)
            SaikinJyusyo3SaikinJyusyoid    VARCHAR(16)         ,  -- 文字列(16)
            SaikinJyusyo3Hondai            VARCHAR(60)         ,  -- 文字列(60)
            SaikinJyusyo3Ryakusyo10        VARCHAR(20)         ,  -- 文字列(20)
            SaikinJyusyo3Ryakusyo6         VARCHAR(12)         ,  -- 文字列(12)
            SaikinJyusyo3Ryakusyo3         VARCHAR(6)          ,  -- 文字列(6)
            SaikinJyusyo3GradeCD           VARCHAR(1)          ,  -- 文字列(1)
            SaikinJyusyo3SyussoTosu        VARCHAR(2)          ,  -- 文字列(2)
            SaikinJyusyo3KettoNum          VARCHAR(10)           -- 文字列(10)
        )
    """,
    "KISYU_CHANGE": """
        CREATE TABLE IF NOT EXISTS KISYU_CHANGE (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            HappyoTime                     TIMESTAMP           ,  -- 発表時刻
            Umaban                         SMALLINT            ,  -- 馬番
            Bamei                          VARCHAR(36)         ,  -- 文字列(36)
            AtoFutan                       VARCHAR(3)          ,  -- 文字列(3)
            AtoKisyuCode                   VARCHAR(5)          ,  -- 文字列(5)
            AtoKisyuName                   VARCHAR(34)         ,  -- 文字列(34)
            AtoMinaraiCD                   VARCHAR(1)          ,  -- 文字列(1)
            MaeFutan                       VARCHAR(3)          ,  -- 文字列(3)
            MaeKisyuCode                   VARCHAR(5)          ,  -- 文字列(5)
            MaeKisyuName                   VARCHAR(34)         ,  -- 文字列(34)
            MaeMinaraiCD                   VARCHAR(1)            -- 文字列(1)
        )
    """,
    "KISYU_SEISEKI": """
        CREATE TABLE IF NOT EXISTS KISYU_SEISEKI (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            KisyuCode                      VARCHAR(5)          ,  -- 文字列(5)
            Num                            VARCHAR(1)          ,  -- 文字列(1)
            SetYear                        VARCHAR(4)          ,  -- 文字列(4)
            HonSyokinHeichi                VARCHAR(10)         ,  -- 文字列(10)
            HonSyokinSyogai                VARCHAR(10)         ,  -- 文字列(10)
            FukaSyokinHeichi               VARCHAR(10)         ,  -- 文字列(10)
            FukaSyokinSyogai               VARCHAR(10)         ,  -- 文字列(10)
            HeichiChakukaisu1              VARCHAR(6)          ,  -- 文字列(6)
            HeichiChakukaisu2              VARCHAR(6)          ,  -- 文字列(6)
            HeichiChakukaisu3              VARCHAR(6)          ,  -- 文字列(6)
            HeichiChakukaisu4              VARCHAR(6)          ,  -- 文字列(6)
            HeichiChakukaisu5              VARCHAR(6)          ,  -- 文字列(6)
            HeichiChakukaisu6              VARCHAR(6)          ,  -- 文字列(6)
            SyogaiChakukaisu1              VARCHAR(6)          ,  -- 文字列(6)
            SyogaiChakukaisu2              VARCHAR(6)          ,  -- 文字列(6)
            SyogaiChakukaisu3              VARCHAR(6)          ,  -- 文字列(6)
            SyogaiChakukaisu4              VARCHAR(6)          ,  -- 文字列(6)
            SyogaiChakukaisu5              VARCHAR(6)          ,  -- 文字列(6)
            SyogaiChakukaisu6              VARCHAR(6)          ,  -- 文字列(6)
            Jyo1Chakukaisu1                VARCHAR(6)          ,  -- 文字列(6)
            Jyo1Chakukaisu2                VARCHAR(6)          ,  -- 文字列(6)
            Jyo1Chakukaisu3                VARCHAR(6)          ,  -- 文字列(6)
            Jyo1Chakukaisu4                VARCHAR(6)          ,  -- 文字列(6)
            Jyo1Chakukaisu5                VARCHAR(6)          ,  -- 文字列(6)
            Jyo1Chakukaisu6                VARCHAR(6)          ,  -- 文字列(6)
            Jyo2Chakukaisu1                VARCHAR(6)          ,  -- 文字列(6)
            Jyo2Chakukaisu2                VARCHAR(6)          ,  -- 文字列(6)
            Jyo2Chakukaisu3                VARCHAR(6)          ,  -- 文字列(6)
            Jyo2Chakukaisu4                VARCHAR(6)          ,  -- 文字列(6)
            Jyo2Chakukaisu5                VARCHAR(6)          ,  -- 文字列(6)
            Jyo2Chakukaisu6                VARCHAR(6)          ,  -- 文字列(6)
            Jyo3Chakukaisu1                VARCHAR(6)          ,  -- 文字列(6)
            Jyo3Chakukaisu2                VARCHAR(6)          ,  -- 文字列(6)
            Jyo3Chakukaisu3                VARCHAR(6)          ,  -- 文字列(6)
            Jyo3Chakukaisu4                VARCHAR(6)          ,  -- 文字列(6)
            Jyo3Chakukaisu5                VARCHAR(6)          ,  -- 文字列(6)
            Jyo3Chakukaisu6                VARCHAR(6)          ,  -- 文字列(6)
            Jyo4Chakukaisu1                VARCHAR(6)          ,  -- 文字列(6)
            Jyo4Chakukaisu2                VARCHAR(6)          ,  -- 文字列(6)
            Jyo4Chakukaisu3                VARCHAR(6)          ,  -- 文字列(6)
            Jyo4Chakukaisu4                VARCHAR(6)          ,  -- 文字列(6)
            Jyo4Chakukaisu5                VARCHAR(6)          ,  -- 文字列(6)
            Jyo4Chakukaisu6                VARCHAR(6)          ,  -- 文字列(6)
            Jyo5Chakukaisu1                VARCHAR(6)          ,  -- 文字列(6)
            Jyo5Chakukaisu2                VARCHAR(6)          ,  -- 文字列(6)
            Jyo5Chakukaisu3                VARCHAR(6)          ,  -- 文字列(6)
            Jyo5Chakukaisu4                VARCHAR(6)          ,  -- 文字列(6)
            Jyo5Chakukaisu5                VARCHAR(6)          ,  -- 文字列(6)
            Jyo5Chakukaisu6                VARCHAR(6)          ,  -- 文字列(6)
            Jyo6Chakukaisu1                VARCHAR(6)          ,  -- 文字列(6)
            Jyo6Chakukaisu2                VARCHAR(6)          ,  -- 文字列(6)
            Jyo6Chakukaisu3                VARCHAR(6)          ,  -- 文字列(6)
            Jyo6Chakukaisu4                VARCHAR(6)          ,  -- 文字列(6)
            Jyo6Chakukaisu5                VARCHAR(6)          ,  -- 文字列(6)
            Jyo6Chakukaisu6                VARCHAR(6)          ,  -- 文字列(6)
            Jyo7Chakukaisu1                VARCHAR(6)          ,  -- 文字列(6)
            Jyo7Chakukaisu2                VARCHAR(6)          ,  -- 文字列(6)
            Jyo7Chakukaisu3                VARCHAR(6)          ,  -- 文字列(6)
            Jyo7Chakukaisu4                VARCHAR(6)          ,  -- 文字列(6)
            Jyo7Chakukaisu5                VARCHAR(6)          ,  -- 文字列(6)
            Jyo7Chakukaisu6                VARCHAR(6)          ,  -- 文字列(6)
            Jyo8Chakukaisu1                VARCHAR(6)          ,  -- 文字列(6)
            Jyo8Chakukaisu2                VARCHAR(6)          ,  -- 文字列(6)
            Jyo8Chakukaisu3                VARCHAR(6)          ,  -- 文字列(6)
            Jyo8Chakukaisu4                VARCHAR(6)          ,  -- 文字列(6)
            Jyo8Chakukaisu5                VARCHAR(6)          ,  -- 文字列(6)
            Jyo8Chakukaisu6                VARCHAR(6)          ,  -- 文字列(6)
            Jyo9Chakukaisu1                VARCHAR(6)          ,  -- 文字列(6)
            Jyo9Chakukaisu2                VARCHAR(6)          ,  -- 文字列(6)
            Jyo9Chakukaisu3                VARCHAR(6)          ,  -- 文字列(6)
            Jyo9Chakukaisu4                VARCHAR(6)          ,  -- 文字列(6)
            Jyo9Chakukaisu5                VARCHAR(6)          ,  -- 文字列(6)
            Jyo9Chakukaisu6                VARCHAR(6)          ,  -- 文字列(6)
            Jyo10Chakukaisu1               VARCHAR(6)          ,  -- 文字列(6)
            Jyo10Chakukaisu2               VARCHAR(6)          ,  -- 文字列(6)
            Jyo10Chakukaisu3               VARCHAR(6)          ,  -- 文字列(6)
            Jyo10Chakukaisu4               VARCHAR(6)          ,  -- 文字列(6)
            Jyo10Chakukaisu5               VARCHAR(6)          ,  -- 文字列(6)
            Jyo10Chakukaisu6               VARCHAR(6)          ,  -- 文字列(6)
            Jyo11Chakukaisu1               VARCHAR(6)          ,  -- 文字列(6)
            Jyo11Chakukaisu2               VARCHAR(6)          ,  -- 文字列(6)
            Jyo11Chakukaisu3               VARCHAR(6)          ,  -- 文字列(6)
            Jyo11Chakukaisu4               VARCHAR(6)          ,  -- 文字列(6)
            Jyo11Chakukaisu5               VARCHAR(6)          ,  -- 文字列(6)
            Jyo11Chakukaisu6               VARCHAR(6)          ,  -- 文字列(6)
            Jyo12Chakukaisu1               VARCHAR(6)          ,  -- 文字列(6)
            Jyo12Chakukaisu2               VARCHAR(6)          ,  -- 文字列(6)
            Jyo12Chakukaisu3               VARCHAR(6)          ,  -- 文字列(6)
            Jyo12Chakukaisu4               VARCHAR(6)          ,  -- 文字列(6)
            Jyo12Chakukaisu5               VARCHAR(6)          ,  -- 文字列(6)
            Jyo12Chakukaisu6               VARCHAR(6)          ,  -- 文字列(6)
            Jyo13Chakukaisu1               VARCHAR(6)          ,  -- 文字列(6)
            Jyo13Chakukaisu2               VARCHAR(6)          ,  -- 文字列(6)
            Jyo13Chakukaisu3               VARCHAR(6)          ,  -- 文字列(6)
            Jyo13Chakukaisu4               VARCHAR(6)          ,  -- 文字列(6)
            Jyo13Chakukaisu5               VARCHAR(6)          ,  -- 文字列(6)
            Jyo13Chakukaisu6               VARCHAR(6)          ,  -- 文字列(6)
            Jyo14Chakukaisu1               VARCHAR(6)          ,  -- 文字列(6)
            Jyo14Chakukaisu2               VARCHAR(6)          ,  -- 文字列(6)
            Jyo14Chakukaisu3               VARCHAR(6)          ,  -- 文字列(6)
            Jyo14Chakukaisu4               VARCHAR(6)          ,  -- 文字列(6)
            Jyo14Chakukaisu5               VARCHAR(6)          ,  -- 文字列(6)
            Jyo14Chakukaisu6               VARCHAR(6)          ,  -- 文字列(6)
            Jyo15Chakukaisu1               VARCHAR(6)          ,  -- 文字列(6)
            Jyo15Chakukaisu2               VARCHAR(6)          ,  -- 文字列(6)
            Jyo15Chakukaisu3               VARCHAR(6)          ,  -- 文字列(6)
            Jyo15Chakukaisu4               VARCHAR(6)          ,  -- 文字列(6)
            Jyo15Chakukaisu5               VARCHAR(6)          ,  -- 文字列(6)
            Jyo15Chakukaisu6               VARCHAR(6)          ,  -- 文字列(6)
            Jyo16Chakukaisu1               VARCHAR(6)          ,  -- 文字列(6)
            Jyo16Chakukaisu2               VARCHAR(6)          ,  -- 文字列(6)
            Jyo16Chakukaisu3               VARCHAR(6)          ,  -- 文字列(6)
            Jyo16Chakukaisu4               VARCHAR(6)          ,  -- 文字列(6)
            Jyo16Chakukaisu5               VARCHAR(6)          ,  -- 文字列(6)
            Jyo16Chakukaisu6               VARCHAR(6)          ,  -- 文字列(6)
            Jyo17Chakukaisu1               VARCHAR(6)          ,  -- 文字列(6)
            Jyo17Chakukaisu2               VARCHAR(6)          ,  -- 文字列(6)
            Jyo17Chakukaisu3               VARCHAR(6)          ,  -- 文字列(6)
            Jyo17Chakukaisu4               VARCHAR(6)          ,  -- 文字列(6)
            Jyo17Chakukaisu5               VARCHAR(6)          ,  -- 文字列(6)
            Jyo17Chakukaisu6               VARCHAR(6)          ,  -- 文字列(6)
            Jyo18Chakukaisu1               VARCHAR(6)          ,  -- 文字列(6)
            Jyo18Chakukaisu2               VARCHAR(6)          ,  -- 文字列(6)
            Jyo18Chakukaisu3               VARCHAR(6)          ,  -- 文字列(6)
            Jyo18Chakukaisu4               VARCHAR(6)          ,  -- 文字列(6)
            Jyo18Chakukaisu5               VARCHAR(6)          ,  -- 文字列(6)
            Jyo18Chakukaisu6               VARCHAR(6)          ,  -- 文字列(6)
            Jyo19Chakukaisu1               VARCHAR(6)          ,  -- 文字列(6)
            Jyo19Chakukaisu2               VARCHAR(6)          ,  -- 文字列(6)
            Jyo19Chakukaisu3               VARCHAR(6)          ,  -- 文字列(6)
            Jyo19Chakukaisu4               VARCHAR(6)          ,  -- 文字列(6)
            Jyo19Chakukaisu5               VARCHAR(6)          ,  -- 文字列(6)
            Jyo19Chakukaisu6               VARCHAR(6)          ,  -- 文字列(6)
            Jyo20Chakukaisu1               VARCHAR(6)          ,  -- 文字列(6)
            Jyo20Chakukaisu2               VARCHAR(6)          ,  -- 文字列(6)
            Jyo20Chakukaisu3               VARCHAR(6)          ,  -- 文字列(6)
            Jyo20Chakukaisu4               VARCHAR(6)          ,  -- 文字列(6)
            Jyo20Chakukaisu5               VARCHAR(6)          ,  -- 文字列(6)
            Jyo20Chakukaisu6               VARCHAR(6)          ,  -- 文字列(6)
            Kyori1Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu6              SMALLINT              -- 距離(m)
        )
    """,
    "MINING": """
        CREATE TABLE IF NOT EXISTS MINING (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            MakeHM                         VARCHAR(4)          ,  -- 文字列(4)
            Umaban1                        SMALLINT            ,  -- 馬番
            DMTime1                        DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP1                       VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM1                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban2                        SMALLINT            ,  -- 馬番
            DMTime2                        DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP2                       VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM2                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban3                        SMALLINT            ,  -- 馬番
            DMTime3                        DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP3                       VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM3                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban4                        SMALLINT            ,  -- 馬番
            DMTime4                        DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP4                       VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM4                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban5                        SMALLINT            ,  -- 馬番
            DMTime5                        DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP5                       VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM5                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban6                        SMALLINT            ,  -- 馬番
            DMTime6                        DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP6                       VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM6                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban7                        SMALLINT            ,  -- 馬番
            DMTime7                        DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP7                       VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM7                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban8                        SMALLINT            ,  -- 馬番
            DMTime8                        DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP8                       VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM8                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban9                        SMALLINT            ,  -- 馬番
            DMTime9                        DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP9                       VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM9                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban10                       SMALLINT            ,  -- 馬番
            DMTime10                       DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP10                      VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM10                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban11                       SMALLINT            ,  -- 馬番
            DMTime11                       DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP11                      VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM11                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban12                       SMALLINT            ,  -- 馬番
            DMTime12                       DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP12                      VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM12                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban13                       SMALLINT            ,  -- 馬番
            DMTime13                       DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP13                      VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM13                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban14                       SMALLINT            ,  -- 馬番
            DMTime14                       DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP14                      VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM14                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban15                       SMALLINT            ,  -- 馬番
            DMTime15                       DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP15                      VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM15                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban16                       SMALLINT            ,  -- 馬番
            DMTime16                       DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP16                      VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM16                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban17                       SMALLINT            ,  -- 馬番
            DMTime17                       DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP17                      VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM17                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban18                       SMALLINT            ,  -- 馬番
            DMTime18                       DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP18                      VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM18                      VARCHAR(4)            -- 文字列(4)
        )
    """,
    "ODDS_SANREN": """
        CREATE TABLE IF NOT EXISTS ODDS_SANREN (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Kumi                           VARCHAR(6)          ,  -- 文字列(6)
            Odds                           DECIMAL(6,1)        ,  -- オッズ
            Ninki                          SMALLINT              -- 人気
        )
    """,
    "ODDS_SANRENTAN": """
        CREATE TABLE IF NOT EXISTS ODDS_SANRENTAN (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Kumi                           VARCHAR(6)          ,  -- 文字列(6)
            Odds                           DECIMAL(6,1)        ,  -- オッズ
            Ninki                          SMALLINT              -- 人気
        )
    """,
    "ODDS_SANRENTAN_HEAD": """
        CREATE TABLE IF NOT EXISTS ODDS_SANRENTAN_HEAD (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            HappyoTime                     TIMESTAMP           ,  -- 発表時刻
            TorokuTosu                     SMALLINT            ,  -- 登録頭数
            SyussoTosu                     SMALLINT            ,  -- 出走頭数
            SanrentanFlag                  VARCHAR(1)          ,  -- 文字列(1)
            TotalHyosuSanrentan            VARCHAR(11)           -- 文字列(11)
        )
    """,
    "ODDS_SANREN_HEAD": """
        CREATE TABLE IF NOT EXISTS ODDS_SANREN_HEAD (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            HappyoTime                     TIMESTAMP           ,  -- 発表時刻
            TorokuTosu                     SMALLINT            ,  -- 登録頭数
            SyussoTosu                     SMALLINT            ,  -- 出走頭数
            SanrenFlag                     VARCHAR(1)          ,  -- 文字列(1)
            TotalHyosuSanren               VARCHAR(11)           -- 文字列(11)
        )
    """,
    "ODDS_TANPUKU": """
        CREATE TABLE IF NOT EXISTS ODDS_TANPUKU (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Umaban                         SMALLINT            ,  -- 馬番
            TanOdds                        VARCHAR(4)          ,  -- 文字列(4)
            TanNinki                       VARCHAR(2)          ,  -- 文字列(2)
            FukuOddsLow                    VARCHAR(4)          ,  -- 文字列(4)
            FukuOddsHigh                   VARCHAR(4)          ,  -- 文字列(4)
            FukuNinki                      VARCHAR(2)            -- 文字列(2)
        )
    """,
    "ODDS_TANPUKUWAKU_HEAD": """
        CREATE TABLE IF NOT EXISTS ODDS_TANPUKUWAKU_HEAD (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            HappyoTime                     TIMESTAMP           ,  -- 発表時刻
            TorokuTosu                     SMALLINT            ,  -- 登録頭数
            SyussoTosu                     SMALLINT            ,  -- 出走頭数
            TansyoFlag                     VARCHAR(1)          ,  -- 文字列(1)
            FukusyoFlag                    VARCHAR(1)          ,  -- 文字列(1)
            WakurenFlag                    VARCHAR(1)          ,  -- 文字列(1)
            FukuChakuBaraiKey              VARCHAR(1)          ,  -- 文字列(1)
            TotalHyosuTansyo               VARCHAR(11)         ,  -- 文字列(11)
            TotalHyosuFukusyo              VARCHAR(11)         ,  -- 文字列(11)
            TotalHyosuWakuren              VARCHAR(11)           -- 文字列(11)
        )
    """,
    "ODDS_UMAREN": """
        CREATE TABLE IF NOT EXISTS ODDS_UMAREN (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Kumi                           VARCHAR(4)          ,  -- 文字列(4)
            Odds                           DECIMAL(6,1)        ,  -- オッズ
            Ninki                          SMALLINT              -- 人気
        )
    """,
    "ODDS_UMAREN_HEAD": """
        CREATE TABLE IF NOT EXISTS ODDS_UMAREN_HEAD (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            HappyoTime                     TIMESTAMP           ,  -- 発表時刻
            TorokuTosu                     SMALLINT            ,  -- 登録頭数
            SyussoTosu                     SMALLINT            ,  -- 出走頭数
            UmarenFlag                     VARCHAR(1)          ,  -- 文字列(1)
            TotalHyosuUmaren               VARCHAR(11)           -- 文字列(11)
        )
    """,
    "ODDS_UMATAN": """
        CREATE TABLE IF NOT EXISTS ODDS_UMATAN (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Kumi                           VARCHAR(4)          ,  -- 文字列(4)
            Odds                           DECIMAL(6,1)        ,  -- オッズ
            Ninki                          SMALLINT              -- 人気
        )
    """,
    "ODDS_UMATAN_HEAD": """
        CREATE TABLE IF NOT EXISTS ODDS_UMATAN_HEAD (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            HappyoTime                     TIMESTAMP           ,  -- 発表時刻
            TorokuTosu                     SMALLINT            ,  -- 登録頭数
            SyussoTosu                     SMALLINT            ,  -- 出走頭数
            UmatanFlag                     VARCHAR(1)          ,  -- 文字列(1)
            TotalHyosuUmatan               VARCHAR(11)           -- 文字列(11)
        )
    """,
    "ODDS_WAKU": """
        CREATE TABLE IF NOT EXISTS ODDS_WAKU (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Kumi                           VARCHAR(2)          ,  -- 文字列(2)
            Odds                           DECIMAL(6,1)        ,  -- オッズ
            Ninki                          SMALLINT              -- 人気
        )
    """,
    "ODDS_WIDE": """
        CREATE TABLE IF NOT EXISTS ODDS_WIDE (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Kumi                           VARCHAR(4)          ,  -- 文字列(4)
            OddsLow                        VARCHAR(5)          ,  -- 文字列(5)
            OddsHigh                       VARCHAR(5)          ,  -- 文字列(5)
            Ninki                          SMALLINT              -- 人気
        )
    """,
    "ODDS_WIDE_HEAD": """
        CREATE TABLE IF NOT EXISTS ODDS_WIDE_HEAD (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            HappyoTime                     TIMESTAMP           ,  -- 発表時刻
            TorokuTosu                     SMALLINT            ,  -- 登録頭数
            SyussoTosu                     SMALLINT            ,  -- 出走頭数
            WideFlag                       VARCHAR(1)          ,  -- 文字列(1)
            TotalHyosuWide                 VARCHAR(11)           -- 文字列(11)
        )
    """,
    "RACE": """
        CREATE TABLE IF NOT EXISTS RACE (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            YoubiCD                        VARCHAR(1)          ,  -- 文字列(1)
            TokuNum                        VARCHAR(4)          ,  -- 文字列(4)
            Hondai                         VARCHAR(60)         ,  -- 文字列(60)
            Fukudai                        VARCHAR(60)         ,  -- 文字列(60)
            Kakko                          VARCHAR(60)         ,  -- 文字列(60)
            HondaiEng                      VARCHAR(120)        ,  -- 文字列(120)
            FukudaiEng                     VARCHAR(120)        ,  -- 文字列(120)
            KakkoEng                       VARCHAR(120)        ,  -- 文字列(120)
            Ryakusyo10                     VARCHAR(20)         ,  -- 文字列(20)
            Ryakusyo6                      VARCHAR(12)         ,  -- 文字列(12)
            Ryakusyo3                      VARCHAR(6)          ,  -- 文字列(6)
            Kubun                          VARCHAR(1)          ,  -- 文字列(1)
            Nkai                           SMALLINT            ,  -- 第N回
            GradeCD                        VARCHAR(1)          ,  -- 文字列(1)
            GradeCDBefore                  VARCHAR(1)          ,  -- 文字列(1)
            SyubetuCD                      VARCHAR(2)          ,  -- 文字列(2)
            KigoCD                         VARCHAR(3)          ,  -- 文字列(3)
            JyuryoCD                       VARCHAR(1)          ,  -- 文字列(1)
            JyokenCD1                      VARCHAR(3)          ,  -- 文字列(3)
            JyokenCD2                      VARCHAR(3)          ,  -- 文字列(3)
            JyokenCD3                      VARCHAR(3)          ,  -- 文字列(3)
            JyokenCD4                      VARCHAR(3)          ,  -- 文字列(3)
            JyokenCD5                      VARCHAR(3)          ,  -- 文字列(3)
            JyokenName                     VARCHAR(60)         ,  -- 文字列(60)
            Kyori                          SMALLINT            ,  -- 距離(m)
            KyoriBefore                    SMALLINT            ,  -- 変更前距離
            TrackCD                        VARCHAR(2)          ,  -- 文字列(2)
            TrackCDBefore                  VARCHAR(2)          ,  -- 文字列(2)
            CourseKubunCD                  VARCHAR(2)          ,  -- 文字列(2)
            CourseKubunCDBefore            VARCHAR(2)          ,  -- 文字列(2)
            Honsyokin1                     INTEGER             ,  -- 1着本賞金
            Honsyokin2                     INTEGER             ,  -- 2着本賞金
            Honsyokin3                     INTEGER             ,  -- 3着本賞金
            Honsyokin4                     INTEGER             ,  -- 4着本賞金
            Honsyokin5                     INTEGER             ,  -- 5着本賞金
            Honsyokin6                     INTEGER             ,  -- 6着本賞金
            Honsyokin7                     INTEGER             ,  -- 7着本賞金
            HonsyokinBefore1               VARCHAR(8)          ,  -- 文字列(8)
            HonsyokinBefore2               VARCHAR(8)          ,  -- 文字列(8)
            HonsyokinBefore3               VARCHAR(8)          ,  -- 文字列(8)
            HonsyokinBefore4               VARCHAR(8)          ,  -- 文字列(8)
            HonsyokinBefore5               VARCHAR(8)          ,  -- 文字列(8)
            Fukasyokin1                    INTEGER             ,  -- 1着付加賞金
            Fukasyokin2                    INTEGER             ,  -- 2着付加賞金
            Fukasyokin3                    INTEGER             ,  -- 3着付加賞金
            Fukasyokin4                    INTEGER             ,  -- 4着付加賞金
            Fukasyokin5                    INTEGER             ,  -- 5着付加賞金
            FukasyokinBefore1              VARCHAR(8)          ,  -- 文字列(8)
            FukasyokinBefore2              VARCHAR(8)          ,  -- 文字列(8)
            FukasyokinBefore3              VARCHAR(8)          ,  -- 文字列(8)
            HassoTime                      TIME                ,  -- 発走時刻(HHMM)
            HassoTimeBefore                VARCHAR(4)          ,  -- 文字列(4)
            TorokuTosu                     SMALLINT            ,  -- 登録頭数
            SyussoTosu                     SMALLINT            ,  -- 出走頭数
            NyusenTosu                     SMALLINT            ,  -- 入選頭数
            TenkoCD                        VARCHAR(1)          ,  -- 文字列(1)
            SibaBabaCD                     VARCHAR(1)          ,  -- 文字列(1)
            DirtBabaCD                     VARCHAR(1)          ,  -- 文字列(1)
            LapTime1                       DECIMAL(4,1)        ,  -- ラップタイム1(秒)
            LapTime2                       DECIMAL(4,1)        ,  -- ラップタイム2
            LapTime3                       DECIMAL(4,1)        ,  -- ラップタイム3
            LapTime4                       VARCHAR(3)          ,  -- 文字列(3)
            LapTime5                       VARCHAR(3)          ,  -- 文字列(3)
            LapTime6                       VARCHAR(3)          ,  -- 文字列(3)
            LapTime7                       VARCHAR(3)          ,  -- 文字列(3)
            LapTime8                       VARCHAR(3)          ,  -- 文字列(3)
            LapTime9                       VARCHAR(3)          ,  -- 文字列(3)
            LapTime10                      DECIMAL(4,1)        ,  -- ラップタイム0(秒)
            LapTime11                      DECIMAL(4,1)        ,  -- ラップタイム1(秒)
            LapTime12                      DECIMAL(4,1)        ,  -- ラップタイム2(秒)
            LapTime13                      DECIMAL(4,1)        ,  -- ラップタイム3(秒)
            LapTime14                      DECIMAL(4,1)        ,  -- ラップタイム4(秒)
            LapTime15                      DECIMAL(4,1)        ,  -- ラップタイム5(秒)
            LapTime16                      DECIMAL(4,1)        ,  -- ラップタイム6(秒)
            LapTime17                      DECIMAL(4,1)        ,  -- ラップタイム7(秒)
            LapTime18                      DECIMAL(4,1)        ,  -- ラップタイム8(秒)
            LapTime19                      DECIMAL(4,1)        ,  -- ラップタイム9(秒)
            LapTime20                      DECIMAL(4,1)        ,  -- ラップタイム2
            LapTime21                      DECIMAL(4,1)        ,  -- ラップタイム2
            LapTime22                      DECIMAL(4,1)        ,  -- ラップタイム2
            LapTime23                      DECIMAL(4,1)        ,  -- ラップタイム2
            LapTime24                      DECIMAL(4,1)        ,  -- ラップタイム2
            LapTime25                      DECIMAL(4,1)        ,  -- ラップタイム2
            SyogaiMileTime                 DECIMAL(5,1)        ,  -- 障害マイルタイム
            HaronTimeS3                    DECIMAL(4,1)        ,  -- 前3F(秒)
            HaronTimeS4                    DECIMAL(4,1)        ,  -- 前4F(秒)
            HaronTimeL3                    DECIMAL(4,1)        ,  -- 後3F(秒)
            HaronTimeL4                    DECIMAL(4,1)        ,  -- 後4F(秒)
            Corner1                        VARCHAR(1)          ,  -- 文字列(1)
            Syukaisu1                      VARCHAR(1)          ,  -- 文字列(1)
            Jyuni1                         VARCHAR(70)         ,  -- 文字列(70)
            Corner2                        VARCHAR(1)          ,  -- 文字列(1)
            Syukaisu2                      VARCHAR(1)          ,  -- 文字列(1)
            Jyuni2                         VARCHAR(70)         ,  -- 文字列(70)
            Corner3                        VARCHAR(1)          ,  -- 文字列(1)
            Syukaisu3                      VARCHAR(1)          ,  -- 文字列(1)
            Jyuni3                         VARCHAR(70)         ,  -- 文字列(70)
            Corner4                        VARCHAR(1)          ,  -- 文字列(1)
            Syukaisu4                      VARCHAR(1)          ,  -- 文字列(1)
            Jyuni4                         VARCHAR(70)         ,  -- 文字列(70)
            RecordUpKubun                  VARCHAR(1)            -- 文字列(1)
        )
    """,
    "RECORD": """
        CREATE TABLE IF NOT EXISTS RECORD (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            RecInfoKubun                   VARCHAR(1)          ,  -- 文字列(1)
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            TokuNum                        VARCHAR(4)          ,  -- 文字列(4)
            Hondai                         VARCHAR(60)         ,  -- 文字列(60)
            GradeCD                        VARCHAR(1)          ,  -- 文字列(1)
            SyubetuCD_TrackCD              VARCHAR(4)          ,  -- 文字列(4)
            Kyori                          SMALLINT            ,  -- 距離(m)
            RecKubun                       VARCHAR(1)          ,  -- 文字列(1)
            RecTime                        VARCHAR(4)          ,  -- 文字列(4)
            TenkoCD                        VARCHAR(1)          ,  -- 文字列(1)
            SibaBabaCD                     VARCHAR(1)          ,  -- 文字列(1)
            DirtBabaCD                     VARCHAR(1)          ,  -- 文字列(1)
            RecUmaKettoNum1                VARCHAR(10)         ,  -- 文字列(10)
            RecUmaBamei1                   VARCHAR(36)         ,  -- 文字列(36)
            RecUmaUmaKigoCD1               VARCHAR(2)          ,  -- 文字列(2)
            RecUmaSexCD1                   VARCHAR(1)          ,  -- 文字列(1)
            RecUmaChokyosiCode1            VARCHAR(5)          ,  -- 文字列(5)
            RecUmaChokyosiName1            VARCHAR(34)         ,  -- 文字列(34)
            RecUmaFutan1                   VARCHAR(3)          ,  -- 文字列(3)
            RecUmaKisyuCode1               VARCHAR(5)          ,  -- 文字列(5)
            RecUmaKisyuName1               VARCHAR(34)         ,  -- 文字列(34)
            RecUmaKettoNum2                VARCHAR(10)         ,  -- 文字列(10)
            RecUmaBamei2                   VARCHAR(36)         ,  -- 文字列(36)
            RecUmaUmaKigoCD2               VARCHAR(2)          ,  -- 文字列(2)
            RecUmaSexCD2                   VARCHAR(1)          ,  -- 文字列(1)
            RecUmaChokyosiCode2            VARCHAR(5)          ,  -- 文字列(5)
            RecUmaChokyosiName2            VARCHAR(34)         ,  -- 文字列(34)
            RecUmaFutan2                   VARCHAR(3)          ,  -- 文字列(3)
            RecUmaKisyuCode2               VARCHAR(5)          ,  -- 文字列(5)
            RecUmaKisyuName2               VARCHAR(34)         ,  -- 文字列(34)
            RecUmaKettoNum3                VARCHAR(10)         ,  -- 文字列(10)
            RecUmaBamei3                   VARCHAR(36)         ,  -- 文字列(36)
            RecUmaUmaKigoCD3               VARCHAR(2)          ,  -- 文字列(2)
            RecUmaSexCD3                   VARCHAR(1)          ,  -- 文字列(1)
            RecUmaChokyosiCode3            VARCHAR(5)          ,  -- 文字列(5)
            RecUmaChokyosiName3            VARCHAR(34)         ,  -- 文字列(34)
            RecUmaFutan3                   VARCHAR(3)          ,  -- 文字列(3)
            RecUmaKisyuCode3               VARCHAR(5)          ,  -- 文字列(5)
            RecUmaKisyuName3               VARCHAR(34)           -- 文字列(34)
        )
    """,
    "SALE": """
        CREATE TABLE IF NOT EXISTS SALE (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            KettoNum                       VARCHAR(10)         ,  -- 文字列(10)
            HansyokuFNum                   VARCHAR(255)        ,  -- テキスト
            HansyokuMNum                   VARCHAR(255)        ,  -- テキスト
            BirthYear                      VARCHAR(255)        ,  -- テキスト
            SaleCode                       VARCHAR(255)        ,  -- テキスト
            SaleHostName                   VARCHAR(40)         ,  -- 文字列(40)
            SaleName                       VARCHAR(80)         ,  -- 文字列(80)
            FromDate                       VARCHAR(255)        ,  -- テキスト
            ToDate                         VARCHAR(255)        ,  -- テキスト
            Barei                          SMALLINT            ,  -- 馬齢
            Price                          VARCHAR(10)           -- 文字列(10)
        )
    """,
    "SANKU": """
        CREATE TABLE IF NOT EXISTS SANKU (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            BirthDate                      DATE                ,  -- 生年月日
            SexCD                          VARCHAR(1)          ,  -- 文字列(1)
            HinsyuCD                       VARCHAR(1)          ,  -- 文字列(1)
            KeiroCD                        VARCHAR(2)          ,  -- 文字列(2)
            SankuMochiKubun                VARCHAR(1)          ,  -- 文字列(1)
            ImportYear                     VARCHAR(4)          ,  -- 文字列(4)
            BreederCode                    VARCHAR(8)          ,  -- 文字列(8)
            SanchiName                     VARCHAR(20)         ,  -- 文字列(20)
            FNum                           VARCHAR(10)         ,  -- 文字列(10)
            MNum                           VARCHAR(10)         ,  -- 文字列(10)
            FFNum                          VARCHAR(10)         ,  -- 文字列(10)
            FMNum                          VARCHAR(10)         ,  -- 文字列(10)
            MFNum                          VARCHAR(10)         ,  -- 文字列(10)
            MMNum                          VARCHAR(10)         ,  -- 文字列(10)
            FFFNum                         VARCHAR(10)         ,  -- 文字列(10)
            FFMNum                         VARCHAR(10)         ,  -- 文字列(10)
            FMFNum                         VARCHAR(10)         ,  -- 文字列(10)
            FMMNum                         VARCHAR(10)         ,  -- 文字列(10)
            MFFNum                         VARCHAR(10)         ,  -- 文字列(10)
            MFMNum                         VARCHAR(10)         ,  -- 文字列(10)
            MMFNum                         VARCHAR(10)           -- 文字列(10)
        )
    """,
    "SCHEDULE": """
        CREATE TABLE IF NOT EXISTS SCHEDULE (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            YoubiCD                        VARCHAR(1)          ,  -- 文字列(1)
            Jyusyo1TokuNum                 VARCHAR(4)          ,  -- 文字列(4)
            Jyusyo1Hondai                  VARCHAR(60)         ,  -- 文字列(60)
            Jyusyo1Ryakusyo10              VARCHAR(20)         ,  -- 文字列(20)
            Jyusyo1Ryakusyo6               VARCHAR(12)         ,  -- 文字列(12)
            Jyusyo1Ryakusyo3               VARCHAR(6)          ,  -- 文字列(6)
            Jyusyo1Nkai                    VARCHAR(3)          ,  -- 文字列(3)
            Jyusyo1GradeCD                 VARCHAR(1)          ,  -- 文字列(1)
            Jyusyo1SyubetuCD               VARCHAR(2)          ,  -- 文字列(2)
            Jyusyo1KigoCD                  VARCHAR(3)          ,  -- 文字列(3)
            Jyusyo1JyuryoCD                VARCHAR(1)          ,  -- 文字列(1)
            Jyusyo1Kyori                   VARCHAR(4)          ,  -- 文字列(4)
            Jyusyo1TrackCD                 VARCHAR(2)          ,  -- 文字列(2)
            Jyusyo2TokuNum                 VARCHAR(4)          ,  -- 文字列(4)
            Jyusyo2Hondai                  VARCHAR(60)         ,  -- 文字列(60)
            Jyusyo2Ryakusyo10              VARCHAR(20)         ,  -- 文字列(20)
            Jyusyo2Ryakusyo6               VARCHAR(12)         ,  -- 文字列(12)
            Jyusyo2Ryakusyo3               VARCHAR(6)          ,  -- 文字列(6)
            Jyusyo2Nkai                    VARCHAR(3)          ,  -- 文字列(3)
            Jyusyo2GradeCD                 VARCHAR(1)          ,  -- 文字列(1)
            Jyusyo2SyubetuCD               VARCHAR(2)          ,  -- 文字列(2)
            Jyusyo2KigoCD                  VARCHAR(3)          ,  -- 文字列(3)
            Jyusyo2JyuryoCD                VARCHAR(1)          ,  -- 文字列(1)
            Jyusyo2Kyori                   VARCHAR(4)          ,  -- 文字列(4)
            Jyusyo2TrackCD                 VARCHAR(2)          ,  -- 文字列(2)
            Jyusyo3TokuNum                 VARCHAR(4)          ,  -- 文字列(4)
            Jyusyo3Hondai                  VARCHAR(60)         ,  -- 文字列(60)
            Jyusyo3Ryakusyo10              VARCHAR(20)         ,  -- 文字列(20)
            Jyusyo3Ryakusyo6               VARCHAR(12)         ,  -- 文字列(12)
            Jyusyo3Ryakusyo3               VARCHAR(6)          ,  -- 文字列(6)
            Jyusyo3Nkai                    VARCHAR(3)          ,  -- 文字列(3)
            Jyusyo3GradeCD                 VARCHAR(1)          ,  -- 文字列(1)
            Jyusyo3SyubetuCD               VARCHAR(2)          ,  -- 文字列(2)
            Jyusyo3KigoCD                  VARCHAR(3)          ,  -- 文字列(3)
            Jyusyo3JyuryoCD                VARCHAR(1)          ,  -- 文字列(1)
            Jyusyo3Kyori                   VARCHAR(4)          ,  -- 文字列(4)
            Jyusyo3TrackCD                 VARCHAR(2)            -- 文字列(2)
        )
    """,
    "SEISAN": """
        CREATE TABLE IF NOT EXISTS SEISAN (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            BreederName_Co                 VARCHAR(72)         ,  -- 文字列(72)
            BreederName                    VARCHAR(72)         ,  -- 文字列(72)
            BreederNameKana                VARCHAR(72)         ,  -- 文字列(72)
            BreederNameEng                 VARCHAR(168)        ,  -- 文字列(168)
            Address                        VARCHAR(20)         ,  -- 文字列(20)
            H_SetYear                      VARCHAR(4)          ,  -- 文字列(4)
            H_HonSyokinTotal               VARCHAR(10)         ,  -- 文字列(10)
            H_FukaSyokin                   VARCHAR(10)         ,  -- 文字列(10)
            H_ChakuKaisu1                  VARCHAR(6)          ,  -- 文字列(6)
            H_ChakuKaisu2                  VARCHAR(6)          ,  -- 文字列(6)
            H_ChakuKaisu3                  VARCHAR(6)          ,  -- 文字列(6)
            H_ChakuKaisu4                  VARCHAR(6)          ,  -- 文字列(6)
            H_ChakuKaisu5                  VARCHAR(6)          ,  -- 文字列(6)
            H_ChakuKaisu6                  VARCHAR(6)          ,  -- 文字列(6)
            R_SetYear                      VARCHAR(4)          ,  -- 文字列(4)
            R_HonSyokinTotal               VARCHAR(10)         ,  -- 文字列(10)
            R_FukaSyokin                   VARCHAR(10)         ,  -- 文字列(10)
            R_ChakuKaisu1                  VARCHAR(6)          ,  -- 文字列(6)
            R_ChakuKaisu2                  VARCHAR(6)          ,  -- 文字列(6)
            R_ChakuKaisu3                  VARCHAR(6)          ,  -- 文字列(6)
            R_ChakuKaisu4                  VARCHAR(6)          ,  -- 文字列(6)
            R_ChakuKaisu5                  VARCHAR(6)            -- 文字列(6)
        )
    """,
    "TAISENGATA_MINING": """
        CREATE TABLE IF NOT EXISTS TAISENGATA_MINING (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            MakeHM                         VARCHAR(4)          ,  -- 文字列(4)
            Umaban1                        SMALLINT            ,  -- 馬番
            TMScore1                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban2                        SMALLINT            ,  -- 馬番
            TMScore2                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban3                        SMALLINT            ,  -- 馬番
            TMScore3                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban4                        SMALLINT            ,  -- 馬番
            TMScore4                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban5                        SMALLINT            ,  -- 馬番
            TMScore5                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban6                        SMALLINT            ,  -- 馬番
            TMScore6                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban7                        SMALLINT            ,  -- 馬番
            TMScore7                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban8                        SMALLINT            ,  -- 馬番
            TMScore8                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban9                        SMALLINT            ,  -- 馬番
            TMScore9                       VARCHAR(4)          ,  -- 文字列(4)
            Umaban10                       SMALLINT            ,  -- 馬番
            TMScore10                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban11                       SMALLINT            ,  -- 馬番
            TMScore11                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban12                       SMALLINT            ,  -- 馬番
            TMScore12                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban13                       SMALLINT            ,  -- 馬番
            TMScore13                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban14                       SMALLINT            ,  -- 馬番
            TMScore14                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban15                       SMALLINT            ,  -- 馬番
            TMScore15                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban16                       SMALLINT            ,  -- 馬番
            TMScore16                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban17                       SMALLINT            ,  -- 馬番
            TMScore17                      VARCHAR(4)          ,  -- 文字列(4)
            Umaban18                       SMALLINT            ,  -- 馬番
            TMScore18                      VARCHAR(4)            -- 文字列(4)
        )
    """,
    "TENKO_BABA": """
        CREATE TABLE IF NOT EXISTS TENKO_BABA (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            HappyoTime                     TIMESTAMP           ,  -- 発表時刻
            HenkoID                        VARCHAR(1)          ,  -- 文字列(1)
            AtoTenkoCD                     VARCHAR(1)          ,  -- 文字列(1)
            AtoSibaBabaCD                  VARCHAR(1)          ,  -- 文字列(1)
            AtoDirtBabaCD                  VARCHAR(1)          ,  -- 文字列(1)
            MaeTenkoCD                     VARCHAR(1)          ,  -- 文字列(1)
            MaeSibaBabaCD                  VARCHAR(1)          ,  -- 文字列(1)
            MaeDirtBabaCD                  VARCHAR(1)            -- 文字列(1)
        )
    """,
    "TOKU": """
        CREATE TABLE IF NOT EXISTS TOKU (
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Num                            VARCHAR(3)          ,  -- 文字列(3)
            KettoNum                       VARCHAR(10)         ,  -- 文字列(10)
            Bamei                          VARCHAR(36)         ,  -- 文字列(36)
            UmaKigoCD                      VARCHAR(2)          ,  -- 文字列(2)
            SexCD                          VARCHAR(1)          ,  -- 文字列(1)
            TozaiCD                        VARCHAR(1)          ,  -- 文字列(1)
            ChokyosiCode                   VARCHAR(5)          ,  -- 文字列(5)
            ChokyosiRyakusyo               VARCHAR(8)          ,  -- 文字列(8)
            Futan                          DECIMAL(4,1)        ,  -- 斤量(kg)
            Koryu                          VARCHAR(1)            -- 文字列(1)
        )
    """,
    "TOKU_RACE": """
        CREATE TABLE IF NOT EXISTS TOKU_RACE (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            YoubiCD                        VARCHAR(1)          ,  -- 文字列(1)
            TokuNum                        VARCHAR(4)          ,  -- 文字列(4)
            Hondai                         VARCHAR(60)         ,  -- 文字列(60)
            Fukudai                        VARCHAR(60)         ,  -- 文字列(60)
            Kakko                          VARCHAR(60)         ,  -- 文字列(60)
            HondaiEng                      VARCHAR(120)        ,  -- 文字列(120)
            FukudaiEng                     VARCHAR(120)        ,  -- 文字列(120)
            KakkoEng                       VARCHAR(120)        ,  -- 文字列(120)
            Ryakusyo10                     VARCHAR(20)         ,  -- 文字列(20)
            Ryakusyo6                      VARCHAR(12)         ,  -- 文字列(12)
            Ryakusyo3                      VARCHAR(6)          ,  -- 文字列(6)
            Kubun                          VARCHAR(1)          ,  -- 文字列(1)
            Nkai                           SMALLINT            ,  -- 第N回
            GradeCD                        VARCHAR(1)          ,  -- 文字列(1)
            SyubetuCD                      VARCHAR(2)          ,  -- 文字列(2)
            KigoCD                         VARCHAR(3)          ,  -- 文字列(3)
            JyuryoCD                       VARCHAR(1)          ,  -- 文字列(1)
            JyokenCD1                      VARCHAR(3)          ,  -- 文字列(3)
            JyokenCD2                      VARCHAR(3)          ,  -- 文字列(3)
            JyokenCD3                      VARCHAR(3)          ,  -- 文字列(3)
            JyokenCD4                      VARCHAR(3)          ,  -- 文字列(3)
            JyokenCD5                      VARCHAR(3)          ,  -- 文字列(3)
            Kyori                          SMALLINT            ,  -- 距離(m)
            TrackCD                        VARCHAR(2)          ,  -- 文字列(2)
            CourseKubunCD                  VARCHAR(2)          ,  -- 文字列(2)
            HandiDate                      VARCHAR(8)          ,  -- 文字列(8)
            TorokuTosu                     SMALLINT              -- 登録頭数
        )
    """,
    "TORIKESI_JYOGAI": """
        CREATE TABLE IF NOT EXISTS TORIKESI_JYOGAI (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            HappyoTime                     TIMESTAMP           ,  -- 発表時刻
            Umaban                         SMALLINT            ,  -- 馬番
            Bamei                          VARCHAR(36)         ,  -- 文字列(36)
            JiyuKubun                      VARCHAR(3)            -- 文字列(3)
        )
    """,
    "UMA": """
        CREATE TABLE IF NOT EXISTS UMA (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            DelKubun                       VARCHAR(1)          ,  -- 文字列(1)
            RegDate                        VARCHAR(8)          ,  -- 文字列(8)
            DelDate                        DATE                ,  -- 抹消年月日
            BirthDate                      DATE                ,  -- 生年月日
            Bamei                          VARCHAR(36)         ,  -- 文字列(36)
            BameiKana                      VARCHAR(36)         ,  -- 文字列(36)
            BameiEng                       VARCHAR(60)         ,  -- 文字列(60)
            ZaikyuFlag                     VARCHAR(1)          ,  -- 文字列(1)
            Reserved                       VARCHAR(19)         ,  -- 文字列(19)
            UmaKigoCD                      VARCHAR(2)          ,  -- 文字列(2)
            SexCD                          VARCHAR(1)          ,  -- 文字列(1)
            HinsyuCD                       VARCHAR(1)          ,  -- 文字列(1)
            KeiroCD                        VARCHAR(2)          ,  -- 文字列(2)
            Ketto3InfoHansyokuNum1         VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei1               VARCHAR(36)         ,  -- 文字列(36)
            Ketto3InfoHansyokuNum2         VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei2               VARCHAR(36)         ,  -- 文字列(36)
            Ketto3InfoHansyokuNum3         VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei3               VARCHAR(36)         ,  -- 文字列(36)
            Ketto3InfoHansyokuNum4         VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei4               VARCHAR(36)         ,  -- 文字列(36)
            Ketto3InfoHansyokuNum5         VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei5               VARCHAR(36)         ,  -- 文字列(36)
            Ketto3InfoHansyokuNum6         VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei6               VARCHAR(36)         ,  -- 文字列(36)
            Ketto3InfoHansyokuNum7         VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei7               VARCHAR(36)         ,  -- 文字列(36)
            Ketto3InfoHansyokuNum8         VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei8               VARCHAR(36)         ,  -- 文字列(36)
            Ketto3InfoHansyokuNum9         VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei9               VARCHAR(36)         ,  -- 文字列(36)
            Ketto3InfoHansyokuNum10        VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei10              VARCHAR(36)         ,  -- 文字列(36)
            Ketto3InfoHansyokuNum11        VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei11              VARCHAR(36)         ,  -- 文字列(36)
            Ketto3InfoHansyokuNum12        VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei12              VARCHAR(36)         ,  -- 文字列(36)
            Ketto3InfoHansyokuNum13        VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei13              VARCHAR(36)         ,  -- 文字列(36)
            Ketto3InfoHansyokuNum14        VARCHAR(10)         ,  -- 文字列(10)
            Ketto3InfoBamei14              VARCHAR(36)         ,  -- 文字列(36)
            TozaiCD                        VARCHAR(1)          ,  -- 文字列(1)
            ChokyosiCode                   VARCHAR(5)          ,  -- 文字列(5)
            ChokyosiRyakusyo               VARCHAR(8)          ,  -- 文字列(8)
            Syotai                         VARCHAR(20)         ,  -- 文字列(20)
            BreederCode                    VARCHAR(8)          ,  -- 文字列(8)
            BreederName                    VARCHAR(72)         ,  -- 文字列(72)
            SanchiName                     VARCHAR(20)         ,  -- 文字列(20)
            BanusiCode                     VARCHAR(6)          ,  -- 文字列(6)
            BanusiName                     VARCHAR(64)         ,  -- 文字列(64)
            RuikeiHonsyoHeiti              VARCHAR(9)          ,  -- 文字列(9)
            RuikeiHonsyoSyogai             VARCHAR(9)          ,  -- 文字列(9)
            RuikeiFukaHeichi               VARCHAR(9)          ,  -- 文字列(9)
            RuikeiFukaSyogai               VARCHAR(9)          ,  -- 文字列(9)
            RuikeiSyutokuHeichi            VARCHAR(9)          ,  -- 文字列(9)
            RuikeiSyutokuSyogai            VARCHAR(9)          ,  -- 文字列(9)
            SogoChakukaisu1                VARCHAR(3)          ,  -- 文字列(3)
            SogoChakukaisu2                VARCHAR(3)          ,  -- 文字列(3)
            SogoChakukaisu3                VARCHAR(3)          ,  -- 文字列(3)
            SogoChakukaisu4                VARCHAR(3)          ,  -- 文字列(3)
            SogoChakukaisu5                VARCHAR(3)          ,  -- 文字列(3)
            SogoChakukaisu6                VARCHAR(3)          ,  -- 文字列(3)
            ChuoChakukaisu1                VARCHAR(3)          ,  -- 文字列(3)
            ChuoChakukaisu2                VARCHAR(3)          ,  -- 文字列(3)
            ChuoChakukaisu3                VARCHAR(3)          ,  -- 文字列(3)
            ChuoChakukaisu4                VARCHAR(3)          ,  -- 文字列(3)
            ChuoChakukaisu5                VARCHAR(3)          ,  -- 文字列(3)
            ChuoChakukaisu6                VARCHAR(3)          ,  -- 文字列(3)
            Ba1Chakukaisu1                 VARCHAR(3)          ,  -- 文字列(3)
            Ba1Chakukaisu2                 VARCHAR(3)          ,  -- 文字列(3)
            Ba1Chakukaisu3                 VARCHAR(3)          ,  -- 文字列(3)
            Ba1Chakukaisu4                 VARCHAR(3)          ,  -- 文字列(3)
            Ba1Chakukaisu5                 VARCHAR(3)          ,  -- 文字列(3)
            Ba1Chakukaisu6                 VARCHAR(3)          ,  -- 文字列(3)
            Ba2Chakukaisu1                 VARCHAR(3)          ,  -- 文字列(3)
            Ba2Chakukaisu2                 VARCHAR(3)          ,  -- 文字列(3)
            Ba2Chakukaisu3                 VARCHAR(3)          ,  -- 文字列(3)
            Ba2Chakukaisu4                 VARCHAR(3)          ,  -- 文字列(3)
            Ba2Chakukaisu5                 VARCHAR(3)          ,  -- 文字列(3)
            Ba2Chakukaisu6                 VARCHAR(3)          ,  -- 文字列(3)
            Ba3Chakukaisu1                 VARCHAR(3)          ,  -- 文字列(3)
            Ba3Chakukaisu2                 VARCHAR(3)          ,  -- 文字列(3)
            Ba3Chakukaisu3                 VARCHAR(3)          ,  -- 文字列(3)
            Ba3Chakukaisu4                 VARCHAR(3)          ,  -- 文字列(3)
            Ba3Chakukaisu5                 VARCHAR(3)          ,  -- 文字列(3)
            Ba3Chakukaisu6                 VARCHAR(3)          ,  -- 文字列(3)
            Ba4Chakukaisu1                 VARCHAR(3)          ,  -- 文字列(3)
            Ba4Chakukaisu2                 VARCHAR(3)          ,  -- 文字列(3)
            Ba4Chakukaisu3                 VARCHAR(3)          ,  -- 文字列(3)
            Ba4Chakukaisu4                 VARCHAR(3)          ,  -- 文字列(3)
            Ba4Chakukaisu5                 VARCHAR(3)          ,  -- 文字列(3)
            Ba4Chakukaisu6                 VARCHAR(3)          ,  -- 文字列(3)
            Ba5Chakukaisu1                 VARCHAR(3)          ,  -- 文字列(3)
            Ba5Chakukaisu2                 VARCHAR(3)          ,  -- 文字列(3)
            Ba5Chakukaisu3                 VARCHAR(3)          ,  -- 文字列(3)
            Ba5Chakukaisu4                 VARCHAR(3)          ,  -- 文字列(3)
            Ba5Chakukaisu5                 VARCHAR(3)          ,  -- 文字列(3)
            Ba5Chakukaisu6                 VARCHAR(3)          ,  -- 文字列(3)
            Ba6Chakukaisu1                 VARCHAR(3)          ,  -- 文字列(3)
            Ba6Chakukaisu2                 VARCHAR(3)          ,  -- 文字列(3)
            Ba6Chakukaisu3                 VARCHAR(3)          ,  -- 文字列(3)
            Ba6Chakukaisu4                 VARCHAR(3)          ,  -- 文字列(3)
            Ba6Chakukaisu5                 VARCHAR(3)          ,  -- 文字列(3)
            Ba6Chakukaisu6                 VARCHAR(3)          ,  -- 文字列(3)
            Ba7Chakukaisu1                 VARCHAR(3)          ,  -- 文字列(3)
            Ba7Chakukaisu2                 VARCHAR(3)          ,  -- 文字列(3)
            Ba7Chakukaisu3                 VARCHAR(3)          ,  -- 文字列(3)
            Ba7Chakukaisu4                 VARCHAR(3)          ,  -- 文字列(3)
            Ba7Chakukaisu5                 VARCHAR(3)          ,  -- 文字列(3)
            Ba7Chakukaisu6                 VARCHAR(3)          ,  -- 文字列(3)
            Jyotai1Chakukaisu1             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai1Chakukaisu2             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai1Chakukaisu3             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai1Chakukaisu4             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai1Chakukaisu5             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai1Chakukaisu6             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai2Chakukaisu1             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai2Chakukaisu2             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai2Chakukaisu3             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai2Chakukaisu4             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai2Chakukaisu5             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai2Chakukaisu6             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai3Chakukaisu1             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai3Chakukaisu2             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai3Chakukaisu3             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai3Chakukaisu4             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai3Chakukaisu5             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai3Chakukaisu6             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai4Chakukaisu1             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai4Chakukaisu2             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai4Chakukaisu3             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai4Chakukaisu4             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai4Chakukaisu5             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai4Chakukaisu6             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai5Chakukaisu1             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai5Chakukaisu2             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai5Chakukaisu3             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai5Chakukaisu4             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai5Chakukaisu5             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai5Chakukaisu6             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai6Chakukaisu1             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai6Chakukaisu2             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai6Chakukaisu3             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai6Chakukaisu4             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai6Chakukaisu5             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai6Chakukaisu6             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai7Chakukaisu1             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai7Chakukaisu2             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai7Chakukaisu3             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai7Chakukaisu4             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai7Chakukaisu5             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai7Chakukaisu6             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai8Chakukaisu1             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai8Chakukaisu2             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai8Chakukaisu3             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai8Chakukaisu4             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai8Chakukaisu5             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai8Chakukaisu6             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai9Chakukaisu1             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai9Chakukaisu2             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai9Chakukaisu3             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai9Chakukaisu4             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai9Chakukaisu5             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai9Chakukaisu6             VARCHAR(3)          ,  -- 文字列(3)
            Jyotai10Chakukaisu1            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai10Chakukaisu2            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai10Chakukaisu3            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai10Chakukaisu4            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai10Chakukaisu5            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai10Chakukaisu6            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai11Chakukaisu1            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai11Chakukaisu2            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai11Chakukaisu3            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai11Chakukaisu4            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai11Chakukaisu5            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai11Chakukaisu6            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai12Chakukaisu1            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai12Chakukaisu2            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai12Chakukaisu3            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai12Chakukaisu4            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai12Chakukaisu5            VARCHAR(3)          ,  -- 文字列(3)
            Jyotai12Chakukaisu6            VARCHAR(3)          ,  -- 文字列(3)
            Kyori1Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori1Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori2Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori3Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori4Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori5Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu1              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu2              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu3              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu4              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu5              SMALLINT            ,  -- 距離(m)
            Kyori6Chakukaisu6              SMALLINT            ,  -- 距離(m)
            Kyakusitu1                     VARCHAR(3)          ,  -- 文字列(3)
            Kyakusitu2                     VARCHAR(3)          ,  -- 文字列(3)
            Kyakusitu3                     VARCHAR(3)          ,  -- 文字列(3)
            Kyakusitu4                     VARCHAR(3)            -- 文字列(3)
        )
    """,
    "UMA_RACE": """
        CREATE TABLE IF NOT EXISTS UMA_RACE (
            RecordSpec                     CHAR(2)             ,  -- レコード種別ID
            DataKubun                      CHAR(1)             ,  -- データ区分
            MakeDate                       DATE                ,  -- YYYYMMDD形式の日付
            Year                           SMALLINT            ,  -- 年(4桁)
            MonthDay                       SMALLINT            ,  -- 月日(MMDD)
            JyoCD                          CHAR(2)             ,  -- 競馬場コード
            Kaiji                          SMALLINT            ,  -- 開催回
            Nichiji                        SMALLINT            ,  -- 開催日目
            RaceNum                        SMALLINT            ,  -- レース番号
            Wakuban                        SMALLINT            ,  -- 枠番
            Umaban                         SMALLINT            ,  -- 馬番
            KettoNum                       VARCHAR(10)         ,  -- 文字列(10)
            Bamei                          VARCHAR(36)         ,  -- 文字列(36)
            UmaKigoCD                      VARCHAR(2)          ,  -- 文字列(2)
            SexCD                          VARCHAR(1)          ,  -- 文字列(1)
            HinsyuCD                       VARCHAR(1)          ,  -- 文字列(1)
            KeiroCD                        VARCHAR(2)          ,  -- 文字列(2)
            Barei                          SMALLINT            ,  -- 馬齢
            TozaiCD                        VARCHAR(1)          ,  -- 文字列(1)
            ChokyosiCode                   VARCHAR(5)          ,  -- 文字列(5)
            ChokyosiRyakusyo               VARCHAR(8)          ,  -- 文字列(8)
            BanusiCode                     VARCHAR(6)          ,  -- 文字列(6)
            BanusiName                     VARCHAR(64)         ,  -- 文字列(64)
            Fukusyoku                      VARCHAR(60)         ,  -- 文字列(60)
            reserved1                      VARCHAR(60)         ,  -- 文字列(60)
            Futan                          DECIMAL(4,1)        ,  -- 斤量(kg)
            FutanBefore                    DECIMAL(4,1)        ,  -- 変更前斤量
            Blinker                        VARCHAR(1)          ,  -- 文字列(1)
            reserved2                      VARCHAR(1)          ,  -- 文字列(1)
            KisyuCode                      VARCHAR(5)          ,  -- 文字列(5)
            KisyuCodeBefore                VARCHAR(5)          ,  -- 文字列(5)
            KisyuRyakusyo                  VARCHAR(8)          ,  -- 文字列(8)
            KisyuRyakusyoBefore            VARCHAR(8)          ,  -- 文字列(8)
            MinaraiCD                      VARCHAR(1)          ,  -- 文字列(1)
            MinaraiCDBefore                VARCHAR(1)          ,  -- 文字列(1)
            BaTaijyu                       SMALLINT            ,  -- 馬体重(kg)
            ZogenFugo                      VARCHAR(1)          ,  -- 文字列(1)
            ZogenSa                        SMALLINT            ,  -- 増減(kg)
            IJyoCD                         VARCHAR(1)          ,  -- 文字列(1)
            NyusenJyuni                    SMALLINT            ,  -- 入線順位
            KakuteiJyuni                   SMALLINT            ,  -- 確定着順
            DochakuKubun                   VARCHAR(1)          ,  -- 文字列(1)
            DochakuTosu                    VARCHAR(1)          ,  -- 文字列(1)
            Time                           DECIMAL(5,1)        ,  -- 走破タイム(秒)
            ChakusaCD                      VARCHAR(3)          ,  -- 文字列(3)
            ChakusaCDP                     VARCHAR(3)          ,  -- 文字列(3)
            ChakusaCDPP                    VARCHAR(3)          ,  -- 文字列(3)
            Jyuni1c                        SMALLINT            ,  -- 1コーナー順位
            Jyuni2c                        SMALLINT            ,  -- 2コーナー順位
            Jyuni3c                        SMALLINT            ,  -- 3コーナー順位
            Jyuni4c                        SMALLINT            ,  -- 4コーナー順位
            Odds                           DECIMAL(6,1)        ,  -- オッズ
            Ninki                          SMALLINT            ,  -- 人気
            Honsyokin                      INTEGER             ,  -- 本賞金(千円)
            Fukasyokin                     INTEGER             ,  -- 付加賞金(千円)
            reserved3                      VARCHAR(3)          ,  -- 文字列(3)
            reserved4                      VARCHAR(3)          ,  -- 文字列(3)
            HaronTimeL4                    DECIMAL(4,1)        ,  -- 後4F(秒)
            HaronTimeL3                    DECIMAL(4,1)        ,  -- 後3F(秒)
            KettoNum1                      VARCHAR(10)         ,  -- 文字列(10)
            Bamei1                         VARCHAR(36)         ,  -- 文字列(36)
            KettoNum2                      VARCHAR(10)         ,  -- 文字列(10)
            Bamei2                         VARCHAR(36)         ,  -- 文字列(36)
            KettoNum3                      VARCHAR(10)         ,  -- 文字列(10)
            Bamei3                         VARCHAR(36)         ,  -- 文字列(36)
            TimeDiff                       VARCHAR(4)          ,  -- 文字列(4)
            RecordUpKubun                  VARCHAR(1)          ,  -- 文字列(1)
            DMKubun                        VARCHAR(1)          ,  -- 文字列(1)
            DMTime                         DECIMAL(6,1)        ,  -- DMタイム
            DMGosaP                        VARCHAR(4)          ,  -- 文字列(4)
            DMGosaM                        VARCHAR(4)          ,  -- 文字列(4)
            DMJyuni                        VARCHAR(2)          ,  -- 文字列(2)
            KyakusituKubun                 VARCHAR(1)            -- 文字列(1)
        )
    """,
}
