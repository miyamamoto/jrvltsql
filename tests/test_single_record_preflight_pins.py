"""Pin the strict-storage preflight on the single-record import path.

Every official-contract family verifies its native storage schema before any DML,
and the per-family modules prove the verifier rejects each unsafe schema. What was
not pinned is that ``DataImporter.import_single_record`` still performs that
preflight: deleting the guard block inside that method left
``tests/test_<family>_official_contract.py`` fully green for 14 of the 16 families
that have one. This module is that pin, using one defect that is unsafe for every
family - an extra UNIQUE constraint, which silently turns an official replacement
into an erase of a different key.
"""

from collections.abc import Callable

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter
from src.parser.rc_parser import RCParser
from tests.test_av_official_contract import parsed_av
from tests.test_cc_official_contract import parsed_cc
from tests.test_cs_official_contract import parsed_record as parsed_cs
from tests.test_hc_official_contract import parsed_record as parsed_hc
from tests.test_hn_official_contract import hn_record
from tests.test_hr_official_contract import parsed_hr
from tests.test_hs_official_contract import parsed_hs
from tests.test_jc_official_contract import parsed_jc
from tests.test_jg_official_contract import parsed_record as parsed_jg
from tests.test_rc_official_contract import build_rc_record
from tests.test_se_official_contract import _parsed_se
from tests.test_sk_official_contract import sk_record
from tests.test_tc_official_contract import parsed_tc
from tests.test_wc_official_contract import parsed_record as parsed_wc
from tests.test_we_official_contract import parsed_we
from tests.test_wf_official_contract import parsed_record as parsed_wf


def _parsed_rc() -> dict:
    record = RCParser().parse(build_rc_record()[0])
    assert record is not None
    return record


FAMILIES: tuple[tuple[str, Callable[[], dict]], ...] = (
    ("NL_AV", parsed_av),
    ("NL_CC", parsed_cc),
    ("NL_CS", parsed_cs),
    ("NL_HC", parsed_hc),
    ("NL_HN", hn_record),
    ("NL_HR", parsed_hr),
    ("NL_HS", parsed_hs),
    ("NL_JC", parsed_jc),
    ("NL_JG", parsed_jg),
    ("NL_RC", _parsed_rc),
    ("NL_SE", _parsed_se),
    ("NL_SK", sk_record),
    ("NL_TC", parsed_tc),
    ("NL_WC", parsed_wc),
    ("NL_WE", parsed_we),
    ("NL_WF", parsed_wf),
)


def _drifted_schema(table_name: str) -> str:
    """Return the official schema carrying one unapproved UNIQUE constraint."""

    schema = SCHEMAS[table_name]
    marker = "PRIMARY KEY ("
    assert marker in schema, table_name
    return schema.replace(marker, "UNIQUE (RecordSpec), " + marker, 1)


@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-owned"))
@pytest.mark.parametrize(
    ("table_name", "build_record"),
    FAMILIES,
    ids=[table_name for table_name, _ in FAMILIES],
)
def test_single_record_path_rejects_a_drifted_native_schema_before_dml(
    tmp_path,
    table_name: str,
    build_record: Callable[[], dict],
    auto_commit: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}-{auto_commit}.db")})
    with database:
        database.execute(_drifted_schema(table_name))
        database.commit()
        before_indexes = database.fetch_all(f'PRAGMA index_list("{table_name}")')
        importer = DataImporter(database)
        with pytest.raises(SchemaMigrationError, match="UNIQUE"):
            importer.import_single_record(build_record(), auto_commit=auto_commit)
        assert database.fetch_all(f'PRAGMA index_list("{table_name}")') == before_indexes
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}
        assert importer.get_statistics()["records_imported"] == 0
