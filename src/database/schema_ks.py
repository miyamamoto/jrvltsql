"""Normalized native and standard schemas for the official KS master record."""

FIRST_RIDE_SUBFIELDS = (
    ("Hatukijyoid", "TEXT", "VARCHAR(16)"),
    ("SyussoTosu", "INTEGER", "SMALLINT"),
    ("KettoNum", "TEXT", "VARCHAR(10)"),
    ("Bamei", "TEXT", "VARCHAR(36)"),
    ("KakuteiJyuni", "INTEGER", "SMALLINT"),
    ("IJyoCD", "TEXT", "VARCHAR(1)"),
)
FIRST_WIN_SUBFIELDS = (
    ("Hatusyoriid", "TEXT", "VARCHAR(16)"),
    ("SyussoTosu", "INTEGER", "SMALLINT"),
    ("KettoNum", "TEXT", "VARCHAR(10)"),
    ("Bamei", "TEXT", "VARCHAR(36)"),
)
RECENT_SUBFIELDS = (
    ("SaikinJyusyoid", "TEXT", "VARCHAR(16)"),
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
        ("KisyuCode", "VARCHAR(5)" if standard else text),
        ("DelKubun", "VARCHAR(1)" if standard else text),
        ("IssueDate", "VARCHAR(8)" if standard else text),
        ("DelDate", "VARCHAR(8)" if standard else text),
        ("BirthDate", "VARCHAR(8)" if standard else text),
        ("KisyuName", "VARCHAR(34)" if standard else text),
        ("reserved", "VARCHAR(34)" if standard else text),
        ("KisyuNameKana", "VARCHAR(30)" if standard else text),
        ("KisyuRyakusyo", "VARCHAR(8)" if standard else text),
        ("KisyuNameEng", "VARCHAR(80)" if standard else text),
        ("SexCD", "VARCHAR(1)" if standard else text),
        ("SikakuCD", "VARCHAR(1)" if standard else text),
        ("MinaraiCD", "VARCHAR(1)" if standard else text),
        ("TozaiCD", "VARCHAR(1)" if standard else text),
        ("Syotai", "VARCHAR(20)" if standard else text),
        ("ChokyosiCode", "VARCHAR(5)" if standard else text),
        ("ChokyosiRyakusyo", "VARCHAR(8)" if standard else text),
    ]
    for block in range(1, 3):
        for suffix, native_type, standard_type in FIRST_RIDE_SUBFIELDS:
            columns.append(
                (f"HatuKiJyo{block}{suffix}", standard_type if standard else native_type)
            )
    for block in range(1, 3):
        for suffix, native_type, standard_type in FIRST_WIN_SUBFIELDS:
            columns.append(
                (f"HatuSyori{block}{suffix}", standard_type if standard else native_type)
            )
    for block in range(1, 4):
        for suffix, native_type, standard_type in RECENT_SUBFIELDS:
            columns.append(
                (f"SaikinJyusyo{block}{suffix}", standard_type if standard else native_type)
            )
    return columns


def _result_columns(*, standard: bool) -> list[tuple[str, str]]:
    columns = [
        ("MakeDate", "VARCHAR(8)" if standard else "TEXT"),
        ("KisyuCode", "VARCHAR(5)" if standard else "TEXT"),
        ("Num", "SMALLINT" if standard else "INTEGER"),
        ("SetYear", "SMALLINT" if standard else "INTEGER"),
        ("HonSyokinHeichi", "BIGINT"),
        ("HonSyokinSyogai", "BIGINT"),
        ("FukaSyokinHeichi", "BIGINT"),
        ("FukaSyokinSyogai", "BIGINT"),
    ]
    columns.extend((name, "INTEGER") for name in RESULT_FIELD_NAMES[5:])
    return columns


NL_KS_SCHEMA = _create_table("NL_KS", _header_columns(standard=False), ("KisyuCode",))
NL_KS_SEISEKI_SCHEMA = _create_table(
    "NL_KS_SEISEKI", _result_columns(standard=False), ("KisyuCode", "Num")
)
KISYU_SCHEMA = _create_table("KISYU", _header_columns(standard=True), ("KisyuCode",))
KISYU_SEISEKI_SCHEMA = _create_table(
    "KISYU_SEISEKI", _result_columns(standard=True), ("KisyuCode", "Num")
)
