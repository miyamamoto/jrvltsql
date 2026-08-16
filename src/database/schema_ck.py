"""Normalized native schemas for the official current CK record."""

PARENT_KEY_COLUMNS = (
    ("Year", "INTEGER NOT NULL"),
    ("MonthDay", "INTEGER NOT NULL"),
    ("JyoCD", "TEXT NOT NULL"),
    ("Kaiji", "INTEGER NOT NULL"),
    ("Nichiji", "INTEGER NOT NULL"),
    ("RaceNum", "INTEGER NOT NULL"),
    ("KettoNum", "TEXT NOT NULL"),
)
PARENT_KEY = tuple(name for name, _ in PARENT_KEY_COLUMNS)


def _create_table(
    table_name: str,
    columns: list[tuple[str, str]],
    primary_key: tuple[str, ...],
    constraints: tuple[str, ...],
) -> str:
    items = [f"            {name} {column_type}" for name, column_type in columns]
    items.extend(f"            {constraint}" for constraint in constraints)
    items.append(f"            PRIMARY KEY ({', '.join(primary_key)})")
    return f"CREATE TABLE IF NOT EXISTS {table_name} (\n" + ",\n".join(items) + "\n        )"


def _metric_clause(metric: str, count: int) -> str:
    return f"(MetricKubun = '{metric}' AND BucketNum BETWEEN 1 AND {count})"


_HORSE_METRICS = (
    ("ChakuSogo", 1),
    ("ChakuChuo", 1),
    ("ChakuKaisuBa", 7),
    ("ChakuKaisuJyotai", 12),
    ("ChakuKaisuSibaKyori", 9),
    ("ChakuKaisuDirtKyori", 9),
    ("ChakuKaisuJyoSiba", 10),
    ("ChakuKaisuJyoDirt", 10),
    ("ChakuKaisuJyoSyogai", 10),
    ("Kyakusitu", 1),
)
_PROFESSIONAL_METRICS = (
    ("ChakuKaisuSiba", 1),
    ("ChakuKaisuDirt", 1),
    ("ChakuKaisuSyogai", 1),
    ("ChakuKaisuSibaKyori", 9),
    ("ChakuKaisuDirtKyori", 9),
    ("ChakuKaisuJyoSiba", 10),
    ("ChakuKaisuJyoDirt", 10),
    ("ChakuKaisuJyoSyogai", 10),
)
_HORSE_DOMAIN = " OR ".join(_metric_clause(*item) for item in _HORSE_METRICS)
_PROFESSIONAL_DOMAIN = " OR ".join(_metric_clause(*item) for item in _PROFESSIONAL_METRICS)
_CHAKU_DOMAIN_CHECK = (
    "CHECK ((EntityKubun = 'UMA' AND PeriodNum = 0 AND ("
    + _HORSE_DOMAIN
    + ")) OR (EntityKubun IN ('KISYU', 'CHOKYOSI') AND PeriodNum IN (1, 2) AND ("
    + _PROFESSIONAL_DOMAIN
    + ")) OR (EntityKubun IN ('BANUSI', 'BREEDER') AND PeriodNum IN (1, 2) "
    "AND MetricKubun = 'ChakuKaisu' AND BucketNum = 1))"
)


NL_CK_CHAKU_SCHEMA = _create_table(
    "NL_CK_CHAKU",
    [
        *PARENT_KEY_COLUMNS,
        ("EntityKubun", "TEXT NOT NULL"),
        ("PeriodNum", "INTEGER NOT NULL"),
        ("MetricKubun", "TEXT NOT NULL"),
        ("BucketNum", "INTEGER NOT NULL"),
        *((f"Count{rank}", "INTEGER NOT NULL") for rank in range(1, 5)),
        ("Count5", "INTEGER"),
        ("Count6", "INTEGER"),
    ],
    (*PARENT_KEY, "EntityKubun", "PeriodNum", "MetricKubun", "BucketNum"),
    (
        "CONSTRAINT ck_chaku_parent_fk FOREIGN KEY "
        f"({', '.join(PARENT_KEY)}) REFERENCES NL_CK ({', '.join(PARENT_KEY)}) "
        "ON DELETE CASCADE",
        f"CONSTRAINT ck_chaku_domain {_CHAKU_DOMAIN_CHECK}",
        "CONSTRAINT ck_chaku_count_shape CHECK "
        "((EntityKubun = 'UMA' AND MetricKubun = 'Kyakusitu' "
        "AND Count5 IS NULL AND Count6 IS NULL) OR "
        "(NOT (EntityKubun = 'UMA' AND MetricKubun = 'Kyakusitu') "
        "AND Count5 IS NOT NULL AND Count6 IS NOT NULL))",
    ),
)

NL_CK_RUIKEI_SCHEMA = _create_table(
    "NL_CK_RUIKEI",
    [
        *PARENT_KEY_COLUMNS,
        ("EntityKubun", "TEXT NOT NULL"),
        ("PeriodNum", "INTEGER NOT NULL"),
        ("SetYear", "INTEGER NOT NULL"),
        ("HonSyokinHeichi", "BIGINT"),
        ("HonSyokinSyogai", "BIGINT"),
        ("FukaSyokinHeichi", "BIGINT"),
        ("FukaSyokinSyogai", "BIGINT"),
        ("HonSyokinTotal", "BIGINT"),
        ("FukaSyokin", "BIGINT"),
    ],
    (*PARENT_KEY, "EntityKubun", "PeriodNum"),
    (
        "CONSTRAINT ck_ruikei_parent_fk FOREIGN KEY "
        f"({', '.join(PARENT_KEY)}) REFERENCES NL_CK ({', '.join(PARENT_KEY)}) "
        "ON DELETE CASCADE",
        "CONSTRAINT ck_ruikei_shape CHECK ((EntityKubun IN ('KISYU', 'CHOKYOSI') "
        "AND PeriodNum IN (1, 2) AND HonSyokinHeichi IS NOT NULL "
        "AND HonSyokinSyogai IS NOT NULL AND FukaSyokinHeichi IS NOT NULL "
        "AND FukaSyokinSyogai IS NOT NULL AND HonSyokinTotal IS NULL "
        "AND FukaSyokin IS NULL) OR (EntityKubun IN ('BANUSI', 'BREEDER') "
        "AND PeriodNum IN (1, 2) AND HonSyokinHeichi IS NULL "
        "AND HonSyokinSyogai IS NULL AND FukaSyokinHeichi IS NULL "
        "AND FukaSyokinSyogai IS NULL AND HonSyokinTotal IS NOT NULL "
        "AND FukaSyokin IS NOT NULL))",
    ),
)
