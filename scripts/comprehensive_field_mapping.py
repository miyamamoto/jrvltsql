#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Comprehensive field name mapping: Japanese -> English/Romanized."""

# Comprehensive field name mapping for JRA-VAN standard compliance
COMPREHENSIVE_FIELD_MAPPING = {
    # Common fields
    "レコード種別ID": "RecordSpec",
    "データ区分": "DataKubun",
    "データ作成年月日": "MakeDate",
    "レコード区切": "RecordDelimiter",
    "予備": "reserved",

    # Race identification
    "開催年": "Year",
    "開催月日": "MonthDay",
    "競馬場コード": "JyoCD",
    "開催回[第N回]": "Kaiji",
    "開催回第N回": "Kaiji",
    "開催日目[N日目]": "Nichiji",
    "開催日目N日目": "Nichiji",
    "レース番号": "RaceNum",
    "曜日コード": "YoubiCD",
    "特別競走番号": "TokuNum",

    # Race names
    "競走名本題": "Hondai",
    "競走名副題": "Fukudai",
    "競走名カッコ内": "Kakko",
    "競走名本題欧字": "HondaiEng",
    "競走名副題欧字": "FukudaiEng",
    "競走名カッコ内欧字": "KakkoEng",
    "競走名略称10文字": "Ryakusyo10",
    "競走名略称6文字": "Ryakusyo6",
    "競走名略称3文字": "Ryakusyo3",
    "競走名区分": "Kubun",

    # Horse
    "血統登録番号": "KettoNum",
    "馬名": "Bamei",
    "馬名半角ｶﾅ": "BameiKana",
    "馬名欧字": "BameiEng",
    "馬記号コード": "UmaKigoCD",
    "性別コード": "SexCD",
    "品種コード": "HinsyuCD",
    "毛色コード": "KeiroCD",
    "馬齢": "Barei",
    "馬体重": "BaTaijyu",
    "増減符号": "ZogenFugo",
    "増減差": "ZogenSa",
    "枠番": "Wakuban",
    "馬番": "Umaban",

    # Jockey
    "騎手コード": "KisyuCode",
    "騎手名略称": "KisyuRyakusyo",
    "騎手名": "KisyuName",
    "騎手名半角ｶﾅ": "KisyuNameKana",
    "騎手名欧字": "KisyuNameEng",
    "見習区分": "MinaraiCD",
    "騎手見習コード": "MinaraiCD",
    "変更前騎手コード": "KisyuCodeBefore",
    "変更前騎手名略称": "KisyuRyakusyoBefore",
    "変更前騎手見習コード": "MinaraiCDBefore",

    # Trainer
    "東西所属コード": "TozaiCD",
    "調教師コード": "ChokyosiCode",
    "調教師名略称": "ChokyosiRyakusyo",
    "調教師名": "ChokyosiName",
    "調教師名半角ｶﾅ": "ChokyosiNameKana",
    "調教師名欧字": "ChokyosiNameEng",
    "トレセン区分": "TresenKubun",
    "調教タイプ": "ChokyoType",

    # Owner
    "馬主コード": "BanusiCode",
    "馬主名": "BanusiName",
    "馬主名(法人格無)": "BanusiName_Co",
    "馬主名(法人格有)": "BanusiName",
    "馬主名半角ｶﾅ": "BanusiNameKana",
    "馬主名欧字": "BanusiNameEng",
    "服色標示": "Fukusyoku",

    # Breeder/Producer
    "生産者コード": "BreederCode",
    "生産者名(法人格無)": "BreederName_Co",
    "生産者名(法人格有)": "BreederName",
    "生産者名半角ｶﾅ": "BreederNameKana",
    "生産者名欧字": "BreederNameEng",
    "生産者住所自治省名": "BreederAddress",
    "産地名": "SanchiName",

    # Race details
    "距離": "Kyori",
    "変更前距離": "KyoriBefore",
    "トラックコード": "TrackCD",
    "変更前トラックコード": "TrackCDBefore",
    "コース区分": "CourseKubunCD",
    "変更前コース区分": "CourseKubunCDBefore",
    "負担重量": "Futan",
    "変更前負担重量": "FutanBefore",
    "斤量": "Futan",
    "ブリンカー使用区分": "Blinker",

    # Results
    "入線順位": "NyusenJyuni",
    "確定着順": "KakuteiJyuni",
    "同着区分": "DochakuKubun",
    "同着頭数": "DochakuTosu",
    "走破タイム": "Time",
    "タイム": "Time",
    "着差コード": "ChakusaCD",
    "＋着差コード": "ChakusaCD2",
    "＋＋着差コード": "ChakusaCD3",
    "人気": "Ninki",
    "単勝人気順": "Ninki",
    "オッズ": "Odds",
    "単勝オッズ": "Odds",

    # Prize money
    "本賞金": "Honsyokin",
    "変更前本賞金": "HonsyokinBefore",
    "付加賞金": "Fukasyokin",
    "変更前付加賞金": "FukasyokinBefore",
    "獲得本賞金": "Honsyokin",
    "獲得付加賞金": "Fukasyokin",

    # Lap times
    "前3ハロン": "HaronTimeS3",
    "前4ハロン": "HaronTimeS4",
    "後3ハロン": "HaronTimeL3",
    "後4ハロン": "HaronTimeL4",
    "後3ハロンタイム": "HaronTimeL3",
    "後4ハロンタイム": "HaronTimeL4",
    "ラップタイム": "LapTime",
    "障害マイルタイム": "SyogaiMileTime",

    # Time/Date
    "発走時刻": "HassoTime",
    "変更前発走時刻": "HassoTimeBefore",
    "発表月日時分": "HappyoTime",
    "ハンデ発表日": "HandeDate",
    "データ作成時分": "MakeTime",
    "調教年月日": "ChokyoDate",
    "調教時刻": "ChokyoTime",
    "生年月日": "BirthDate",

    # Counts
    "登録頭数": "TorokuTosu",
    "出走頭数": "SyussoTosu",
    "入線頭数": "NyusenTosu",
    "重賞回次[第N回]": "Nkai",
    "登録レース数": "RegisteredRaceCount",

    # Weather/Track
    "天候コード": "TenkoCD",
    "芝馬場状態コード": "SibaBabaCD",
    "ダート馬場状態コード": "DirtBabaCD",

    # Grade/Classification
    "グレードコード": "GradeCD",
    "変更前グレードコード": "GradeCDBefore",
    "競走種別コード": "SyubetuCD",
    "競走記号コード": "KigoCD",
    "重量種別コード": "JyuryoCD",
    "競走条件名称": "JyokenName",

    # Flags
    "不成立フラグ　単勝": "FuseirituFlag1",
    "不成立フラグ　複勝": "FuseirituFlag2",
    "不成立フラグ　枠連": "FuseirituFlag3",
    "不成立フラグ　馬連": "FuseirituFlag4",
    "不成立フラグ　ワイド": "FuseirituFlag5",
    "不成立フラグ　馬単": "FuseirituFlag7",
    "不成立フラグ　3連複": "FuseirituFlag8",
    "不成立フラグ　3連単": "FuseirituFlag9",

    "特払フラグ　単勝": "TokubaraiFlag1",
    "特払フラグ　複勝": "TokubaraiFlag2",
    "特払フラグ　枠連": "TokubaraiFlag3",
    "特払フラグ　馬連": "TokubaraiFlag4",
    "特払フラグ　ワイド": "TokubaraiFlag5",
    "特払フラグ　馬単": "TokubaraiFlag7",
    "特払フラグ　3連複": "TokubaraiFlag8",
    "特払フラグ　3連単": "TokubaraiFlag9",

    "返還フラグ　単勝": "HenkanFlag1",
    "返還フラグ　複勝": "HenkanFlag2",
    "返還フラグ　枠連": "HenkanFlag3",
    "返還フラグ　馬連": "HenkanFlag4",
    "返還フラグ　ワイド": "HenkanFlag5",
    "返還フラグ　馬単": "HenkanFlag7",
    "返還フラグ　3連複": "HenkanFlag8",
    "返還フラグ　3連単": "HenkanFlag9",

    "発売フラグ　単勝": "HatsubaiFlag1",
    "発売フラグ　複勝": "HatsubaiFlag2",
    "発売フラグ　枠連": "HatsubaiFlag3",
    "発売フラグ　馬連": "HatsubaiFlag4",
    "発売フラグ　ワイド": "HatsubaiFlag5",
    "発売フラグ　馬単": "HatsubaiFlag6",
    "発売フラグ　3連複": "HatsubaiFlag7",
    "発売フラグ　3連単": "HatsubaiFlag8",

    "返還馬番情報(馬番01～28)": "HenkanUmabanInfo",
    "返還枠番情報(枠番1～8)": "HenkanWakubanInfo",
    "返還同枠情報(枠番1～8)": "HenkanDowakuInfo",
    "キャリーオーバー金額": "CarryOver",

    # Totals/Summaries
    "単勝票数合計": "TansyoHyosuTotal",
    "複勝票数合計": "FukusyoHyosuTotal",
    "枠連票数合計": "WakurenHyosuTotal",
    "馬連票数合計": "UmarenHyosuTotal",
    "ワイド票数合計": "WideHyosuTotal",
    "馬単票数合計": "UmatanHyosuTotal",
    "3連複票数合計": "SanrenfukuHyosuTotal",
    "3連単票数合計": "SanrentanHyosuTotal",

    "単勝返還票数合計": "TansyoHenkanTotal",
    "複勝返還票数合計": "FukusyoHenkanTotal",
    "枠連返還票数合計": "WakurenHenkanTotal",
    "馬連返還票数合計": "UmarenHenkanTotal",
    "ワイド返還票数合計": "WideHenkanTotal",
    "馬単返還票数合計": "UmatanHenkanTotal",
    "3連複返還票数合計": "SanrenfukuHenkanTotal",
    "3連単返還票数合計": "SanrentanHenkanTotal",

    # Corner positions
    "1コーナーでの順位": "Jyuni1c",
    "2コーナーでの順位": "Jyuni2c",
    "3コーナーでの順位": "Jyuni3c",
    "4コーナーでの順位": "Jyuni4c",

    # Performance statistics (様々な条件での着回数)
    "総合着回数": "TotalChakuCount",
    "中央合計着回数": "ChuoChakuCount",
    "芝直・着回数": "SibaChoChaku",
    "芝右・着回数": "SibaMigiChaku",
    "芝左・着回数": "SibaHidariChaku",
    "ダ直・着回数": "DirtChoChaku",
    "ダ右・着回数": "DirtMigiChaku",
    "ダ左・着回数": "DirtHidariChaku",
    "障害・着回数": "SyogaiChaku",

    # Track condition
    "芝良・着回数": "SibaRyoChaku",
    "芝稍・着回数": "SibaYayaChaku",
    "芝重・着回数": "SibaOmoChaku",
    "芝不・着回数": "SibaFuChaku",
    "ダ良・着回数": "DirtRyoChaku",
    "ダ稍・着回数": "DirtYayaChaku",
    "ダ重・着回数": "DirtOmoChaku",
    "ダ不・着回数": "DirtFuChaku",
    "障良・着回数": "SyogaiRyoChaku",
    "障稍・着回数": "SyogaiYayaChaku",
    "障重・着回数": "SyogaiOmoChaku",
    "障不・着回数": "SyogaiFuChaku",

    # Distance categories
    "芝16下・着回数": "Siba16Chaku",
    "芝22下・着回数": "Siba22Chaku",
    "芝22超・着回数": "Siba22OverChaku",
    "ダ16下・着回数": "Dirt16Chaku",
    "ダ22下・着回数": "Dirt22Chaku",
    "ダ22超・着回数": "Dirt22OverChaku",

    # Lap time summaries
    "2ハロンタイム合計(400M～0M)": "HaronTime2Total",
    "3ハロンタイム合計(600M～0M)": "HaronTime3Total",
    "4ハロンタイム合計(800M～0M)": "HaronTime4Total",
    "5ハロンタイム合計(1000M～0M)": "HaronTime5Total",
    "6ハロンタイム合計(1200M～0M)": "HaronTime6Total",
    "7ハロンタイム合計(1400M～0M)": "HaronTime7Total",
    "8ロンタイム合計(1600M～0M)": "HaronTime8Total",
    "9ハロンタイム合計(1800M～0M)": "HaronTime9Total",
    "10ハロンタイム合計(2000M～0M)": "HaronTime10Total",

    # Odds/Betting blocks
    "<単勝オッズ>": "TansyoOddsBlock",
    "<複勝オッズ>": "FukusyoOddsBlock",
    "<枠連オッズ>": "WakurenOddsBlock",
    "<馬連オッズ>": "UmarenOddsBlock",
    "<ワイドオッズ>": "WideOddsBlock",
    "<馬単オッズ>": "UmatanOddsBlock",
    "<3連複オッズ>": "SanrenfukuOddsBlock",
    "<3連単オッズ>": "SanrentanOddsBlock",

    "<単勝票数>": "TansyoHyosuBlock",
    "<複勝票数>": "FukusyoHyosuBlock",
    "<枠連票数>": "WakurenHyosuBlock",
    "<馬連票数>": "UmarenHyosuBlock",
    "<ワイド票数>": "WideHyosuBlock",
    "<馬単票数>": "UmatanHyosuBlock",
    "<3連複票数>": "SanrenfukuHyosuBlock",
    "<3連単票数>": "SanrentanHyosuBlock",

    # Special keys and classifications
    "複勝着払キー": "FukusyoChakubaraiKey",
    "除外状態区分": "JyogaiJotaiKubun",
    "出馬投票受付順番": "SyutsubaTohyoJunban",
    "出走区分": "SyussoKubun",
    "産駒持込区分": "SankoMochikomiKubun",
    "輸入年": "YunyuYear",
    "3代血統 繁殖登録番号": "SandaiKettoNum",
    "馬名の意味由来": "BameiMeaning",

    # Information blocks
    "<登録馬毎情報>": "TorokuUmaInfo",
    "<重賞案内>": "JyusyoAnnai",
    "<馬体重情報>": "BataijyuInfo",
    "<マイニング予想>": "MiningYoso",
    "<レコード保持馬情報>": "RecordHolderInfo",

    # Course related
    "コース": "Course",
    "コース改修年月日": "CourseKaishuDate",
    "コース説明": "CourseDescription",
    "馬場周り": "BabaMawari",

    # Sales/Trading info
    "父馬_繁殖登録番号": "SireHansyokuNum",
    "母馬_繁殖登録番号": "DamHansyokuNum",
    "生年": "BirthYear",
    "主催者・市場コード": "SponsorMarketCode",
    "主催者名称": "SponsorName",
    "市場の名称": "MarketName",
    "市場の開催期間(開始日)": "MarketStartDate",
    "市場の開催期間(終了日)": "MarketEndDate",
    "取引時の競走馬の年齢": "TradingAge",
    "取引価格": "TradingPrice",

    # Weather/Track state
    "変更識別": "HenkoID",
    "天候状態": "TenkoState",
    "馬場状態・芝": "SibaBabaState",
    "馬場状態・ダート": "DirtBabaState",

    # Multi-race betting (重勝式)
    "<重勝式対象レース情報>": "JyusyoshikiTargetInfo",
    "重勝式発売票数": "JyusyoshikiHatsubaiHyosu",
    "<有効票数情報>": "YukoHyosuInfo",
    "的中無フラグ": "TekichuNashiFlag",
    "キャリーオーバー金額初期": "CarryOverInitial",
    "キャリーオーバー金額残高": "CarryOverBalance",
    "<重勝式払戻情報>": "JyusyoshikiHaraiInfo",

    # Prize money totals
    "平地本賞金累計": "HeichiHonsyokinTotal",
    "障害本賞金累計": "SyogaiHonsyokinTotal",
    "平地付加賞金累計": "HeichiFukasyokinTotal",
    "障害付加賞金累計": "SyogaiFukasyokinTotal",
    "平地収得賞金累計": "HeichiSyutokuTotal",
    "障害収得賞金累計": "SyogaiSyutokuTotal",

    # Distance-based performance (turf)
    "芝1200以下・着回数": "Siba1200IkaChaku",
    "芝1201-1400・着回数": "Siba1201_1400Chaku",
    "芝1401-1600・着回数": "Siba1401_1600Chaku",
    "芝1601-1800・着回数": "Siba1601_1800Chaku",
    "芝1801-2000・着回数": "Siba1801_2000Chaku",
    "芝2001-2200・着回数": "Siba2001_2200Chaku",
    "芝2201-2400・着回数": "Siba2201_2400Chaku",
    "芝2401-2800・着回数": "Siba2401_2800Chaku",
    "芝2801以上・着回数": "Siba2801OverChaku",

    # Distance-based performance (dirt)
    "ダ1200以下・着回数": "Dirt1200IkaChaku",
    "ダ1201-1400・着回数": "Dirt1201_1400Chaku",
    "ダ1401-1600・着回数": "Dirt1401_1600Chaku",
    "ダ1601-1800・着回数": "Dirt1601_1800Chaku",
    "ダ1801-2000・着回数": "Dirt1801_2000Chaku",
    "ダ2001-2200・着回数": "Dirt2001_2200Chaku",
    "ダ2201-2400・着回数": "Dirt2201_2400Chaku",
    "ダ2401-2800・着回数": "Dirt2401_2800Chaku",
    "ダ2801以上・着回数": "Dirt2801OverChaku",

    # Racecourse-based performance (turf)
    "札幌芝・着回数": "SapporoSibaChaku",
    "函館芝・着回数": "HakodateSibaChaku",
    "福島芝・着回数": "FukushimaSibaChaku",
    "新潟芝・着回数": "NiigataSibaChaku",
    "東京芝・着回数": "TokyoSibaChaku",
    "中山芝・着回数": "NakayamaSibaChaku",
    "中京芝・着回数": "ChukyoSibaChaku",
    "京都芝・着回数": "KyotoSibaChaku",
    "阪神芝・着回数": "HanshinSibaChaku",
    "小倉芝・着回数": "KokuraSibaChaku",

    # Racecourse-based performance (dirt)
    "札幌ダ・着回数": "SapporoDirtChaku",
    "函館ダ・着回数": "HakodateDirtChaku",
    "福島ダ・着回数": "FukushimaDirtChaku",
    "新潟ダ・着回数": "NiigataDirtChaku",
    "東京ダ・着回数": "TokyoDirtChaku",
    "中山ダ・着回数": "NakayamaDirtChaku",
    "中京ダ・着回数": "ChukyoDirtChaku",
    "京都ダ・着回数": "KyotoDirtChaku",
    "阪神ダ・着回数": "HanshinDirtChaku",
    "小倉ダ・着回数": "KokuraDirtChaku",

    # Racecourse-based performance (obstacle)
    "札幌障・着回数": "SapporoSyogaiChaku",
    "函館障・着回数": "HakodateSyogaiChaku",
    "福島障・着回数": "FukushimaSyogaiChaku",
    "新潟障・着回数": "NiigataSyogaiChaku",
    "東京障・着回数": "TokyoSyogaiChaku",
    "中山障・着回数": "NakayamaSyogaiChaku",
    "中京障・着回数": "ChukyoSyogaiChaku",
    "京都障・着回数": "KyotoSyogaiChaku",
    "阪神障・着回数": "HanshinSyogaiChaku",
    "小倉障・着回数": "KokuraSyogaiChaku",

    # Results/Stats blocks
    "<騎手本年･累計成績情報>": "KisyuResultsInfo",
    "<調教師本年･累計成績情報>": "ChokyosiResultsInfo",
    "<本年･累計成績情報>": "ResultsInfo",

    # Others
    "異常区分コード": "IJyoCD",
    "事由区分": "JiyuKubun",
    "レコード更新区分": "RecordUpKubun",
    "脚質傾向": "KyakusituKeiko",
    "マイニング区分": "MiningKubun",
    "今回レース脚質判定": "KonkaiKyakusitu",
    "タイム差": "TimeSa",
    "変更後": "After",
    "変更前": "Before",
    "変更": "Change",
    "確定": "Kakutei",
    "新規": "Shinki",
    "削除": "Delete",
    "抹消": "Massho",
    "予定頭数": "YoteiTosu",
    "アルファベット区分": "AlphabetKubun",
    "3歳条件 繰上げ出走頭数": "Kuriage3sai",
    "返還フラグ": "HenkanFlag",
    "不成立フラグ": "FuseirituFlag",
}


def map_field_name(japanese_name: str) -> str:
    """Map Japanese field name to English/Romanized name.

    Args:
        japanese_name: Japanese field name

    Returns:
        English/Romanized field name if mapping exists, otherwise Japanese name
    """
    # Direct mapping
    if japanese_name in COMPREHENSIVE_FIELD_MAPPING:
        return COMPREHENSIVE_FIELD_MAPPING[japanese_name]

    # Handle numbered fields (e.g., "本賞金1着" -> "Honsyokin1")
    if "本賞金" in japanese_name and "着" in japanese_name:
        num = japanese_name.replace("本賞金", "").replace("着", "")
        return f"Honsyokin{num}"

    if "付加賞金" in japanese_name and "着" in japanese_name:
        num = japanese_name.replace("付加賞金", "").replace("着", "")
        return f"Fukasyokin{num}"

    if "ラップタイム" in japanese_name:
        num = japanese_name.replace("ラップタイム", "")
        return f"LapTime{num}" if num else "LapTime"

    if "競走条件コード" in japanese_name:
        if "2歳条件" in japanese_name:
            return "JyokenCD1"
        elif "3歳条件" in japanese_name:
            return "JyokenCD2"
        elif "4歳条件" in japanese_name:
            return "JyokenCD3"
        elif "5歳以上条件" in japanese_name:
            return "JyokenCD4"
        elif "最若年条件" in japanese_name:
            return "JyokenCD5"

    # Default: return as is (will be marked for manual review)
    return japanese_name
