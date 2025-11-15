#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate JRA-VAN standard compliant parsers for all record types."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Field name mapping: Japanese -> English/Romanized (JRA-VAN standard)
FIELD_NAME_MAPPING = {
    # Header fields (common)
    "レコード種別ID": "RecordSpec",
    "データ区分": "DataKubun",
    "データ作成年月日": "MakeDate",

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

    # Horse identification
    "血統登録番号": "KettoNum",
    "馬名": "Bamei",
    "馬記号コード": "UmaKigoCD",
    "性別コード": "SexCD",
    "品種コード": "HinsyuCD",
    "毛色コード": "KeiroCD",
    "馬齢": "Barei",
    "東西所属コード": "TozaiCD",
    "調教師コード": "ChokyosiCode",
    "調教師名略称": "ChokyosiRyakusyo",
    "馬主コード": "BanusiCode",
    "馬主名": "BanusiName",
    "服色標示": "Fukusyoku",

    # Jockey
    "騎手コード": "KisyuCode",
    "騎手名略称": "KisyuRyakusyo",
    "見習区分": "MinaraiCD",

    # Race details
    "距離": "Kyori",
    "トラックコード": "TrackCD",
    "コース区分": "CourseKubunCD",
    "斤量": "Futan",
    "馬体重": "BaTaijyu",
    "増減符号": "ZogenFugo",
    "増減差": "ZogenSa",

    # Results
    "入線順位": "NyusenJyuni",
    "確定着順": "KakuteiJyuni",
    "同着区分": "DochakuKubun",
    "タイム": "Time",
    "着差コード": "ChakusaCD",
    "人気": "Ninki",
    "オッズ": "Odds",
    "本賞金": "Honsyokin",
    "付加賞金": "Fukasyokin",

    # Lap times
    "前3ハロン": "HaronTimeS3",
    "前4ハロン": "HaronTimeS4",
    "後3ハロン": "HaronTimeL3",
    "後4ハロン": "HaronTimeL4",

    # Other
    "発走時刻": "HassoTime",
    "登録頭数": "TorokuTosu",
    "出走頭数": "SyussoTosu",
    "入線頭数": "NyusenTosu",
    "天候コード": "TenkoCD",
    "芝馬場状態コード": "SibaBabaCD",
    "ダート馬場状態コード": "DirtBabaCD",
    "レコード区切": "RecordDelimiter",
}

# Type conversion mapping based on field name
TYPE_CONVERSION_MAPPING = {
    "MakeDate": "DATE",
    "Year": "SMALLINT",
    "MonthDay": "MONTH_DAY",
    "Kaiji": "SMALLINT",
    "Nichiji": "SMALLINT",
    "RaceNum": "SMALLINT",
    "Nkai": "SMALLINT",
    "Kyori": "SMALLINT",
    "KyoriBefore": "SMALLINT",
    "HassoTime": "TIME",
    "TorokuTosu": "SMALLINT",
    "SyussoTosu": "SMALLINT",
    "NyusenTosu": "SMALLINT",
    "NyusenJyuni": "SMALLINT",
    "KakuteiJyuni": "SMALLINT",
    "Ninki": "SMALLINT",
    "Barei": "SMALLINT",
    "BaTaijyu": "SMALLINT",
    "ZogenSa": "SMALLINT",
    "Wakuban": "SMALLINT",
    "Umaban": "SMALLINT",
    "Jyuni1c": "SMALLINT",
    "Jyuni2c": "SMALLINT",
    "Jyuni3c": "SMALLINT",
    "Jyuni4c": "SMALLINT",
    "Futan": "WEIGHT",
    "FutanBefore": "WEIGHT",
    "Time": "RACE_TIME",
    "Odds": "ODDS",
    "Honsyokin": "PRIZE_MONEY",
    "Honsyokin1": "PRIZE_MONEY",
    "Honsyokin2": "PRIZE_MONEY",
    "Honsyokin3": "PRIZE_MONEY",
    "Honsyokin4": "PRIZE_MONEY",
    "Honsyokin5": "PRIZE_MONEY",
    "Honsyokin6": "PRIZE_MONEY",
    "Honsyokin7": "PRIZE_MONEY",
    "Fukasyokin": "PRIZE_MONEY",
    "Fukasyokin1": "PRIZE_MONEY",
    "Fukasyokin2": "PRIZE_MONEY",
    "Fukasyokin3": "PRIZE_MONEY",
    "Fukasyokin4": "PRIZE_MONEY",
    "Fukasyokin5": "PRIZE_MONEY",
    "HaronTimeS3": "LAP_TIME",
    "HaronTimeS4": "LAP_TIME",
    "HaronTimeL3": "LAP_TIME",
    "HaronTimeL4": "LAP_TIME",
    "SyogaiMileTime": "RACE_TIME",
    "DMTime": "RACE_TIME",
}

# Add LapTime1-25
for i in range(1, 26):
    TYPE_CONVERSION_MAPPING[f"LapTime{i}"] = "LAP_TIME"


def map_field_name(japanese_name: str) -> str:
    """Map Japanese field name to English/Romanized name."""
    # Direct mapping
    if japanese_name in FIELD_NAME_MAPPING:
        return FIELD_NAME_MAPPING[japanese_name]

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

    # Default: use Japanese name with underscores
    return japanese_name.replace(" ", "_").replace("[", "").replace("]", "")


def get_convert_type(eng_name: str) -> Optional[str]:
    """Get convert_type for a field based on English name."""
    return TYPE_CONVERSION_MAPPING.get(eng_name)


def generate_parser(record_type: str, fields: List[Dict], output_dir: Path) -> None:
    """Generate a JRA-VAN standard compliant parser."""
    parser_name = f"{record_type}ParserJRAVAN"
    output_file = output_dir / f"{record_type.lower()}_parser_jravan.py"

    # Generate field definitions
    field_defs = []
    for field in fields:
        japanese_name = field["name"]
        eng_name = map_field_name(japanese_name)
        position = field["position"] - 1  # Convert to 0-indexed
        length = field["length"]
        convert_type = get_convert_type(eng_name)

        if convert_type:
            field_def = f'            FieldDef("{eng_name}", {position}, {length}, convert_type="{convert_type}", description="{japanese_name}"),'
        else:
            field_def = f'            FieldDef("{eng_name}", {position}, {length}, description="{japanese_name}"),'

        field_defs.append(field_def)

    # Generate parser class
    parser_code = f'''"""Parser for {record_type} record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class {parser_name}(BaseParser):
    """Parser for {record_type} record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "{record_type}"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions with JRA-VAN standard names and types.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
{chr(10).join(field_defs)}
        ]
'''

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(parser_code)

    print(f"Generated: {output_file.name}")


def main():
    """Generate all parsers from jv_data_formats.json."""
    project_root = Path(__file__).parent.parent
    formats_file = project_root / "jv_data_formats.json"
    output_dir = project_root / "src" / "parser"

    # Load JV-Data formats
    with open(formats_file, 'r', encoding='utf-8') as f:
        formats = json.load(f)

    print(f"Generating JRA-VAN standard parsers from {formats_file}...")
    print(f"Output directory: {output_dir}")
    print()

    generated_count = 0
    for record_type, record_info in formats.items():
        fields = record_info.get("fields", [])
        if not fields:
            print(f"Skipping {record_type}: No fields defined")
            continue

        generate_parser(record_type, fields, output_dir)
        generated_count += 1

    print()
    print(f"✓ Generated {generated_count} parsers")
    print(f"✓ All parsers saved to: {output_dir}")


if __name__ == '__main__':
    main()
