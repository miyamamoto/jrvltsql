"""Normalized native and standard schemas for the official CH master record."""

RECENT_SUBFIELDS = (
    ("id", "TEXT", "VARCHAR(16)"),
    ("Hondai", "TEXT", "VARCHAR(60)"),
    ("Ryakusyo10", "TEXT", "VARCHAR(20)"),
    ("Ryakusyo6", "TEXT", "VARCHAR(12)"),
    ("Ryakusyo3", "TEXT", "VARCHAR(6)"),
    ("GradeCD", "TEXT", "VARCHAR(1)"),
    ("SyussoTosu", "INTEGER", "SMALLINT"),
    ("KettoNum", "TEXT", "VARCHAR(10)"),
    ("Bamei", "TEXT", "VARCHAR(36)"),
)

RESULT_FIELD_NAMES = (
    "SetYear",
    "HonSyokinHeichi",
    "HonSyokinSyogai",
    "FukaSyokinHeichi",
    "FukaSyokinSyogai",
    *(f"HeichiChakukaisu{rank}" for rank in range(1, 7)),
    *(f"SyogaiChakukaisu{rank}" for rank in range(1, 7)),
    *(f"Jyo{course}Chakukaisu{rank}" for course in range(1, 21) for rank in range(1, 7)),
    *(f"Kyori{distance}Chakukaisu{rank}" for distance in range(1, 7) for rank in range(1, 7)),
)


def _create_table(
    table_name: str, columns: list[tuple[str, str]], primary_key: tuple[str, ...]
) -> str:
    items = [f"            {name} {column_type}" for name, column_type in columns]
    items.append(f"            PRIMARY KEY ({', '.join(primary_key)})")
    return f"CREATE TABLE IF NOT EXISTS {table_name} (\n" + ",\n".join(items) + "\n        )"


def _header_columns(*, standard: bool) -> list[tuple[str, str]]:
    text = "TEXT"
    columns = [
        ("RecordSpec", "CHAR(2)" if standard else text),
        ("DataKubun", "CHAR(1)" if standard else text),
        ("MakeDate", "VARCHAR(8)" if standard else text),
        ("ChokyosiCode", "VARCHAR(5)" if standard else text),
        ("DelKubun", "VARCHAR(1)" if standard else text),
        ("IssueDate", "VARCHAR(8)" if standard else text),
        ("DelDate", "VARCHAR(8)" if standard else text),
        ("BirthDate", "VARCHAR(8)" if standard else text),
        ("ChokyosiName", "VARCHAR(34)" if standard else text),
        ("ChokyosiNameKana", "VARCHAR(30)" if standard else text),
        ("ChokyosiRyakusyo", "VARCHAR(8)" if standard else text),
        ("ChokyosiNameEng", "VARCHAR(80)" if standard else text),
        ("SexCD", "VARCHAR(1)" if standard else text),
        ("TozaiCD", "VARCHAR(1)" if standard else text),
        ("Syotai", "VARCHAR(20)" if standard else text),
    ]
    for block in range(1, 4):
        for suffix, native_type, standard_type in RECENT_SUBFIELDS:
            if standard:
                field_name = (
                    f"SaikinJyusyo{block}SaikinJyusyoid"
                    if suffix == "id"
                    else f"SaikinJyusyo{block}{suffix}"
                )
                columns.append((field_name, standard_type))
            else:
                columns.append((f"SaikinJyusyo{block}_{suffix}", native_type))
    return columns


def _result_columns(*, standard: bool) -> list[tuple[str, str]]:
    columns = [
        ("MakeDate", "VARCHAR(8)" if standard else "TEXT"),
        ("ChokyosiCode", "VARCHAR(5)" if standard else "TEXT"),
        ("Num", "SMALLINT" if standard else "INTEGER"),
        ("SetYear", "SMALLINT" if standard else "INTEGER"),
        ("HonSyokinHeichi", "BIGINT"),
        ("HonSyokinSyogai", "BIGINT"),
        ("FukaSyokinHeichi", "BIGINT"),
        ("FukaSyokinSyogai", "BIGINT"),
    ]
    columns.extend((name, "INTEGER") for name in RESULT_FIELD_NAMES[5:])
    return columns


NL_CH_SCHEMA = _create_table("NL_CH", _header_columns(standard=False), ("ChokyosiCode",))
NL_CH_SEISEKI_SCHEMA = _create_table(
    "NL_CH_SEISEKI",
    _result_columns(standard=False),
    ("ChokyosiCode", "Num"),
)
CHOKYO_SCHEMA = _create_table("CHOKYO", _header_columns(standard=True), ("ChokyosiCode",))
CHOKYO_SEISEKI_SCHEMA = _create_table(
    "CHOKYO_SEISEKI",
    _result_columns(standard=True),
    ("ChokyosiCode", "Num"),
)
