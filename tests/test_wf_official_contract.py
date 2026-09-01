"""WF parser and storage contract for the official 7,215-byte layout."""

import json
import os
import re
from pathlib import Path
from uuid import uuid4

import pytest

from src.database.base import DatabaseError
from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS, SchemaManager
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_metadata import TABLE_METADATA
from src.database.schema_types import (
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.database.table_mappings import (
    JLTSQL_TO_JRAVAN,
    JRAVAN_TO_JLTSQL,
    STANDARD_EXPANDED_RECORD_OWNER,
)
from src.importer.importer import (
    DataImporter,
    ImporterError,
    verify_wf_storage_schema,
)
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.wf_parser import WFParser
from src.realtime.updater import RealtimeUpdater


def _pad(value: str, width: int) -> bytes:
    encoded = value.encode("cp932")
    assert len(encoded) <= width
    return encoded.ljust(width, b" ")


def _replace_ddl_fragment(schema: str, expected: str, replacement: str) -> str:
    """Replace one whitespace-aligned DDL fragment and prove it was present."""
    pattern = r"\s+".join(re.escape(token) for token in expected.split())
    replaced, count = re.subn(pattern, replacement, schema, count=1)
    assert count == 1, expected
    assert replaced != schema
    return replaced


def build_record(
    *,
    data_kubun: str = "3",
    make_date: str = "20260817",
    year: str = "2026",
    month_day: str = "0816",
    populate_payload: bool | None = None,
    field_overrides: dict[str, str] | None = None,
) -> bytes:
    """Build one complete current WF record with distinct boundary slots."""
    if populate_payload is None:
        populate_payload = data_kubun != "1"
    values = {
        "DataKubun": data_kubun,
        "MakeDate": make_date,
        "Year": year,
        "MonthDay": month_day,
        "Yobi1": "00",
        "Yobi2": "000000",
        "HatubaiHyosu": "123456" if populate_payload else "",
        "HenkanFlag": "0",
        "FuseirituFlag": "0",
        "TekichuNasiFlag": "0",
        "CarryOverStart": "1000",
        "CarryOverBalance": "2000" if populate_payload else "",
    }
    remaining_votes = (100, 80, 60, 40, 24)
    for index in range(1, 6):
        # Four distinct values per composite so a JyoCD/Kaiji/Nichiji/RaceNum
        # position swap cannot survive the readback assertions.
        values[f"RaceInfo{index}"] = f"{index:02d}{index + 1:02d}{index + 3:02d}{index + 7:02d}"
        values[f"YukoHyosu{index}"] = str(remaining_votes[index - 1]) if populate_payload else ""
    if field_overrides:
        values.update(field_overrides)

    record = bytearray(b" " * WFParser.RECORD_LENGTH)
    record[0:2] = b"WF"
    record[2:3] = _pad(values["DataKubun"], 1)
    record[3:11] = _pad(values["MakeDate"], 8)
    record[11:15] = _pad(values["Year"], 4)
    record[15:19] = _pad(values["MonthDay"], 4)
    record[19:21] = _pad(values["Yobi1"], 2)
    for index in range(1, 6):
        start = 21 + (index - 1) * 8
        record[start : start + 8] = _pad(values[f"RaceInfo{index}"], 8)
    record[61:67] = _pad(values["Yobi2"], 6)
    record[67:78] = _pad(values["HatubaiHyosu"], 11)
    for index in range(1, 6):
        start = 78 + (index - 1) * 11
        record[start : start + 11] = _pad(values[f"YukoHyosu{index}"], 11)
    record[133:134] = _pad(values["HenkanFlag"], 1)
    record[134:135] = _pad(values["FuseirituFlag"], 1)
    record[135:136] = _pad(values["TekichuNasiFlag"], 1)
    record[136:151] = _pad(values["CarryOverStart"], 15)
    record[151:166] = _pad(values["CarryOverBalance"], 15)
    if populate_payload:
        for index, kumi, pay, votes in (
            (1, "0102030405", "123456", "7"),
            (122, "0203040506", "234567", "8"),
            (243, "0304050607", "345678", "9"),
        ):
            start = 166 + (index - 1) * WFParser.PAYOUT_LENGTH
            record[start : start + 10] = _pad(kumi, 10)
            record[start + 10 : start + 19] = _pad(pay, 9)
            record[start + 19 : start + 29] = _pad(votes, 10)
    record[7213:7215] = b"\r\n"
    return bytes(record)


def parsed_record(**kwargs) -> dict:
    parsed = WFParser().parse(build_record(**kwargs))
    assert parsed is not None
    return parsed


def realtime_ra_record(*, month_day: str = "0816") -> dict:
    """Build the minimum complete official key for one realtime RA row."""
    return {
        "RecordSpec": "RA",
        "DataKubun": "1",
        "Year": "2026",
        "MonthDay": month_day,
        "JyoCD": "05",
        "Kaiji": "01",
        "Nichiji": "01",
        "RaceNum": "01",
    }


def cancellation_record() -> bytes:
    record = bytearray(build_record(data_kubun="9", populate_payload=False))
    record[166:176] = b"0000000000"
    record[176:185] = b"000000100"
    record[185:195] = b"0000000000"
    return bytes(record)


def no_hit_record(*, data_kubun: str = "3") -> bytes:
    """Build the official final no-hit representation with zero pay/votes."""
    record = bytearray(
        build_record(
            data_kubun=data_kubun,
            field_overrides={"TekichuNasiFlag": "1"},
        )
    )
    for index in (1, 122, 243):
        start = 166 + (index - 1) * WFParser.PAYOUT_LENGTH
        record[start + 10 : start + 19] = b"000000000"
        record[start + 19 : start + 29] = b"0000000000"
    return bytes(record)


def _payout_slot_override(
    index: int, kumi: str, pay: str, votes: str, *, data_kubun: str = "3"
) -> bytes:
    """Overwrite one physically bounded payout slot."""
    record = bytearray(build_record(data_kubun=data_kubun, populate_payload=False))
    start = 166 + (index - 1) * WFParser.PAYOUT_LENGTH
    record[start : start + 10] = _pad(kumi, 10)
    record[start + 10 : start + 19] = _pad(pay, 9)
    record[start + 19 : start + 29] = _pad(votes, 10)
    return bytes(record)


def test_wf_layout_is_bound_to_the_pinned_sdk_manifest() -> None:
    manifest = json.loads(
        Path("tests/fixtures/official_layout/jvdata_sdk500_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    info = manifest["structures"]["JV_WF_INFO"]
    repeats = {
        field["name"]: (field["start"], field["width"], field["stride"], field["count"])
        for field in info["fields"]
        if field["kind"] == "repeat"
    }
    assert info["width"] == WFParser.RECORD_LENGTH == 7215
    assert info["expanded_leaf_count"] == 771
    assert repeats == {
        "WFRaceInfo": (22, 8, 8, 5),
        "WFYukoHyoInfo": (79, 11, 11, 5),
        "WFPayInfo": (167, 29, 29, 243),
    }
    assert info["fields"][-1] == {
        "name": "crlf",
        "kind": "scalar",
        "start": 7214,
        "width": 2,
        "decoder": "text",
    }

    parsed = parsed_record()
    payouts = json.loads(parsed["PayoutsJson"])
    assert [parsed[f"RaceInfo{index}"] for index in range(1, 6)] == [
        "01020408",
        "02030509",
        "03040610",
        "04050711",
        "05060812",
    ]
    assert [parsed[f"YukoHyosu{index}"] for index in range(1, 6)] == [
        "100",
        "80",
        "60",
        "40",
        "24",
    ]
    assert [payouts[index - 1] for index in (1, 122, 243)] == [
        {"Kumi": "0102030405", "PayJyushosiki": "123456", "TekichuHyosu": "7"},
        {"Kumi": "0203040506", "PayJyushosiki": "234567", "TekichuHyosu": "8"},
        {"Kumi": "0304050607", "PayJyushosiki": "345678", "TekichuHyosu": "9"},
    ]


def test_wf_venue_domain_is_bound_to_official_code_table_2001() -> None:
    contract = json.loads(
        Path("tests/fixtures/official_layout/wf_jyo_codes_4901.json").read_text(encoding="utf-8")
    )
    assert contract["source_artifact"] == "JV-Data4901.xlsx"
    assert contract["source_sha256"] == (
        "23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234"
    )
    assert contract["source_sheet"] == "コード表"
    assert contract["source_rows"] == "10-126"
    assert contract["code_table"] == "2001.競馬場コード"
    listed_codes = contract["listed_non_initial_non_unused_codes"]
    assert len(listed_codes) == len(set(listed_codes)) == 108
    assert WFParser.OFFICIAL_JYO_CODES == frozenset(listed_codes)
    assert set(contract["excluded_codes"]) == {
        "00",
        "C4",
        "F4",
        "F6",
        "G4",
        "G6",
        "G8",
    }
    assert WFParser.OFFICIAL_JYO_CODES.isdisjoint(contract["excluded_codes"])


def test_wf_parser_reads_every_manifest_scalar_and_repeat_at_the_pinned_offset() -> None:
    """Fill each SDK field at its manifest offset and read it back by native name."""
    manifest = json.loads(
        Path("tests/fixtures/official_layout/jvdata_sdk500_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    structures = manifest["structures"]
    fields = {field["name"]: field for field in structures["JV_WF_INFO"]["fields"]}
    record = bytearray(b" " * manifest["root_records"]["WF"]["length"])

    def put(start: int, width: int, value: str) -> None:
        encoded = value.encode("ascii")
        assert len(encoded) == width, (start, width, value)
        record[start - 1 : start - 1 + width] = encoded

    head = fields["head"]
    for sub in structures["RECORD_ID"]["fields"]:
        if sub["name"] == "RecordSpec":
            put(head["start"] + sub["start"] - 1, sub["width"], "WF")
        elif sub["name"] == "DataKubun":
            put(head["start"] + sub["start"] - 1, sub["width"], "3")
        elif sub["name"] == "MakeDate":
            put(head["start"] + sub["start"] - 1, sub["width"], "20260817")
    kaisai = fields["KaisaiDate"]
    put(kaisai["start"], kaisai["width"], "20260816")
    scalar_values = {
        "reserved1": ("Yobi1", "00"),
        "reserved2": ("Yobi2", "000000"),
        "Hatsubai_Hyo": ("HatubaiHyosu", "12345678901"),
        "HenkanFlag": ("HenkanFlag", "1"),
        "FuseiritsuFlag": ("FuseirituFlag", "0"),
        "TekichunashiFlag": ("TekichuNasiFlag", "0"),
        "COShoki": ("CarryOverStart", "100000000000001"),
        "COZanDaka": ("CarryOverBalance", "100000000000002"),
    }
    for sdk_name, (_, value) in scalar_values.items():
        put(fields[sdk_name]["start"], fields[sdk_name]["width"], value)
    race = fields["WFRaceInfo"]
    composites = ["01020408", "02030509", "03040610", "04050711", "05060812"]
    for slot, composite in enumerate(composites):
        put(race["start"] + slot * race["stride"], race["width"], composite)
    yuko = fields["WFYukoHyoInfo"]
    yuko_values = [f"{20000000000 + slot:011d}" for slot in range(1, 6)]
    for slot, value in enumerate(yuko_values):
        put(yuko["start"] + slot * yuko["stride"], yuko["width"], value)
    pay = fields["WFPayInfo"]
    pay_struct = {sub["name"]: sub for sub in structures["WF_PAY_INFO"]["fields"]}
    payout_values = {
        1: ("0102030405", "000001110", "0000000007"),
        122: ("0203040506", "000002220", "0000000008"),
        243: ("0304050607", "000003330", "0000000009"),
    }
    for slot, (kumi, amount, votes) in payout_values.items():
        base = pay["start"] + (slot - 1) * pay["stride"]
        put(base + pay_struct["Kumiban"]["start"] - 1, 10, kumi)
        put(base + pay_struct["Pay"]["start"] - 1, 9, amount)
        put(base + pay_struct["Tekichu_Hyo"]["start"] - 1, 10, votes)
    put(fields["crlf"]["start"], fields["crlf"]["width"], "\r\n")

    parsed = WFParser().parse(bytes(record))
    assert parsed is not None
    assert (parsed["RecordSpec"], parsed["DataKubun"], parsed["MakeDate"]) == (
        "WF",
        "3",
        "20260817",
    )
    assert (parsed["Year"], parsed["MonthDay"]) == ("2026", "0816")
    for native_name, value in scalar_values.values():
        assert parsed[native_name] == value, native_name
    assert [parsed[f"RaceInfo{slot}"] for slot in range(1, 6)] == composites
    assert [parsed[f"YukoHyosu{slot}"] for slot in range(1, 6)] == yuko_values
    payouts = json.loads(parsed["PayoutsJson"])
    for slot, (kumi, amount, votes) in payout_values.items():
        assert payouts[slot - 1] == {
            "Kumi": kumi,
            "PayJyushosiki": amount,
            "TekichuHyosu": votes,
        }
    assert sum(1 for slot in payouts if slot["Kumi"]) == 3


@pytest.mark.parametrize(
    "record",
    (
        pytest.param(build_record(data_kubun=""), id="blank-status"),
        pytest.param(build_record(data_kubun="8"), id="unknown-status"),
        pytest.param(build_record(make_date="20260230"), id="impossible-make-date"),
        pytest.param(build_record(year="20A6"), id="nondigit-year"),
        pytest.param(build_record(month_day="0230"), id="impossible-event-date"),
        pytest.param(
            build_record(field_overrides={"RaceInfo3": "05A30103"}),
            id="nondigit-race-info",
        ),
        pytest.param(
            build_record(field_overrides={"RaceInfo3": "ZZ030103"}),
            id="unknown-venue-code",
        ),
        pytest.param(
            build_record(field_overrides={"RaceInfo3": "n6030103"}),
            id="lowercase-venue-code",
        ),
        pytest.param(
            build_record(field_overrides={"HatubaiHyosu": "12X3"}),
            id="nondigit-sales-votes",
        ),
        pytest.param(
            build_record(field_overrides={"HenkanFlag": "8"}),
            id="unknown-refund-flag",
        ),
        pytest.param(
            build_record(field_overrides={"CarryOverStart": "9Q8"}),
            id="nondigit-carryover",
        ),
        pytest.param(
            _payout_slot_override(1, "010203040", "123456", "7"),
            id="nine-digit-kumi",
        ),
        pytest.param(
            _payout_slot_override(122, "0102030405", "", "7"),
            id="partial-payout-tuple",
        ),
        pytest.param(
            build_record(data_kubun="2", field_overrides={"HenkanFlag": ""}),
            id="status2-blank-flag",
        ),
        pytest.param(
            build_record(
                data_kubun="1",
                make_date="20111201",
                year="2011",
                month_day="1201",
                populate_payload=False,
                field_overrides={"CarryOverStart": "100"},
            ),
            id="pre420-status1-noninitial-carryover",
        ),
        pytest.param(
            build_record(
                data_kubun="1",
                make_date="20120221",
                year="2012",
                month_day="0221",
                populate_payload=False,
                field_overrides={"CarryOverStart": ""},
            ),
            id="ver420-inclusive-boundary-missing-carryover",
        ),
        pytest.param(
            build_record(
                data_kubun="2",
                make_date="20260817",
                year="2011",
                month_day="1201",
                populate_payload=False,
                field_overrides={"CarryOverStart": ""},
            ),
            id="current-format-old-event-missing-carryover",
        ),
        pytest.param(
            _payout_slot_override(
                1,
                "0102030405",
                "000000123",
                "0000000004",
                data_kubun="9",
            ),
            id="status9-noncancellation-payout",
        ),
        pytest.param(
            build_record(data_kubun="1", populate_payload=True),
            id="status1-noninitial-payload",
        ),
        pytest.param(
            build_record(data_kubun="3", populate_payload=False),
            id="status3-missing-required-payload",
        ),
        pytest.param(
            build_record(field_overrides={"TekichuNasiFlag": "1"}),
            id="no-hit-with-positive-pay-and-votes",
        ),
        *(
            pytest.param(
                build_record(
                    data_kubun=status,
                    field_overrides={"CarryOverStart": ""},
                ),
                id=f"current-status{status}-missing-initial-carryover",
            )
            for status in ("1", "2", "9")
        ),
    ),
)
def test_wf_rejects_unsupported_status_and_semantically_corrupt_fields(
    record: bytes,
) -> None:
    assert WFParser().parse(record) is None


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        pytest.param("Yobi1", "01", id="noninitial-reserved1"),
        pytest.param("Yobi2", "000001", id="noninitial-reserved2"),
        pytest.param("Yobi1", "  ", id="blank-reserved1"),
        pytest.param("Yobi2", "      ", id="blank-reserved2"),
    ),
)
def test_wf_keeps_reserved_spans_without_interpreting_them(field_name: str, value: str) -> None:
    """The official layout defines no item for these spans, so any content is kept."""

    parsed = WFParser().parse(build_record(field_overrides={field_name: value}))
    assert parsed is not None
    assert parsed[field_name] == value.strip()


@pytest.mark.parametrize("value", (None, "missing"))
def test_wf_reserved_spans_cannot_be_absent(value: object) -> None:
    """A reserved span has opaque content, but its bytes must still be present."""

    record = parsed_record()
    if value == "missing":
        record.pop("Yobi1")
    else:
        record["Yobi1"] = value
    database = SQLiteDatabase({"path": ":memory:"})
    with database:
        database.create_table("NL_WF", SCHEMAS["NL_WF"])
        with pytest.raises(SchemaMigrationError):
            DataImporter(database).import_records(iter([record]))
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_WF") == {"count": 0}


@pytest.mark.parametrize("value1,value2", (("XX", "OPAQUE"), ("", "")))
@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_wf_reserved_spans_survive_accumulated_storage(
    tmp_path,
    importer_class,
    standard: bool,
    value1: str,
    value2: str,
) -> None:
    """Validated WF reserved bytes retain their exact normalized text value."""

    record = parsed_record(field_overrides={"Yobi1": value1, "Yobi2": value2})
    database = SQLiteDatabase({"path": str(tmp_path / "reserved-wf.db")})
    with database:
        if standard:
            database.create_table("JYUSYOSIKI_HEAD", JRAVAN_SCHEMAS["JYUSYOSIKI_HEAD"])
            database.create_table("JYUSYOSIKI", JRAVAN_SCHEMAS["JYUSYOSIKI"])
            table_name = "JYUSYOSIKI_HEAD"
            columns = ("reserved1", "reserved2")
        else:
            database.create_table("NL_WF", SCHEMAS["NL_WF"])
            table_name = "NL_WF"
            columns = ("Yobi1", "Yobi2")
        stats = importer_class(database, use_jravan_schema=standard).import_records(iter([record]))
        assert stats["records_imported"] == 1
        assert stats["records_failed"] == 0
        assert database.fetch_one(f"SELECT {', '.join(columns)} FROM {table_name}") == dict(
            zip(columns, (value1, value2), strict=True)
        )


@pytest.mark.parametrize("value1,value2", (("XX", "OPAQUE"), ("", "")))
def test_wf_reserved_spans_survive_realtime_storage(
    tmp_path,
    value1: str,
    value2: str,
) -> None:
    record = parsed_record(field_overrides={"Yobi1": value1, "Yobi2": value2})
    database = SQLiteDatabase({"path": str(tmp_path / "reserved-wf-realtime.db")})
    with database:
        database.create_table("RT_WF", SCHEMAS["RT_WF"])
        result = RealtimeUpdater(database).process_parsed_records_batch([record])
        assert result["success"] is True
        assert result["inserted"] == 1
        assert result["errors"] == 0
        assert database.fetch_one("SELECT Yobi1, Yobi2 FROM RT_WF") == {
            "Yobi1": value1,
            "Yobi2": value2,
        }


def test_wf_accepts_all_official_accumulated_statuses_and_opaque_delete() -> None:
    for status in ("0", "1", "2", "3", "7", "9"):
        overrides = None
        if status == "0":
            overrides = {
                "RaceInfo1": "XXXXXXXX",
                "HatubaiHyosu": "NOT-NUMERIC",
                "HenkanFlag": "X",
                "CarryOverStart": "OPAQUE",
                "Yobi1": "XX",
                "Yobi2": "OPAQUE",
            }
        parsed = WFParser().parse(
            build_record(
                data_kubun=status,
                populate_payload=False if status == "9" else None,
                field_overrides=overrides,
            )
        )
        assert parsed is not None
        assert parsed["DataKubun"] == status
    for status in ("2", "9"):
        optional_blank = WFParser().parse(build_record(data_kubun=status, populate_payload=False))
        assert optional_blank is not None

    for status in ("1", "2", "9"):
        pre_420 = WFParser().parse(
            build_record(
                data_kubun=status,
                make_date="20111201",
                year="2011",
                month_day="1201",
                populate_payload=False,
                field_overrides={"CarryOverStart": ""},
            )
        )
        assert pre_420 is not None

    boundary_before = WFParser().parse(
        build_record(
            data_kubun="1",
            make_date="20120220",
            year="2012",
            month_day="0220",
            populate_payload=False,
            field_overrides={"CarryOverStart": ""},
        )
    )
    assert boundary_before is not None
    overseas = WFParser().parse(build_record(field_overrides={"RaceInfo3": "N6030103"}))
    assert overseas is not None

    no_hit = WFParser().parse(no_hit_record())
    assert no_hit is not None
    no_hit_payouts = json.loads(no_hit["PayoutsJson"])
    assert no_hit["TekichuNasiFlag"] == "1"
    assert all(
        (slot["PayJyushosiki"], slot["TekichuHyosu"]) == ("000000000", "0000000000")
        for slot in no_hit_payouts
        if slot["Kumi"]
    )

    cancelled = WFParser().parse(cancellation_record())
    assert cancelled is not None
    assert WFParser.CANCELLATION_PAYOUT == ("0000000000", "000000100", "0000000000")
    assert json.loads(cancelled["PayoutsJson"])[0] == dict(
        zip(WFParser.PAYOUT_KEYS, WFParser.CANCELLATION_PAYOUT, strict=True)
    )


def test_wf_native_canonical_and_metadata_schemas_encode_the_official_key() -> None:
    assert get_table_primary_key_columns("NL_WF") == ["Year", "MonthDay"]
    assert get_table_primary_key_columns("RT_WF") == ["Year", "MonthDay"]
    assert STANDARD_EXPANDED_RECORD_OWNER["NL_WF"] == "JYUSYOSIKI_HEAD"
    assert JRAVAN_TO_JLTSQL["JYUSYOSIKI_HEAD"] == "NL_WF"
    assert JRAVAN_TO_JLTSQL["JYUSYOSIKI"] == "NL_WF"
    assert JLTSQL_TO_JRAVAN["NL_WF"] == "JYUSYOSIKI_HEAD"
    assert "WIN5" not in JRAVAN_SCHEMAS

    head_fields = get_table_column_types("JYUSYOSIKI_HEAD")
    child_fields = get_table_column_types("JYUSYOSIKI")
    assert set(head_fields) == {
        "RecordSpec",
        "DataKubun",
        "MakeDate",
        "Year",
        "MonthDay",
        "reserved1",
        *(
            f"{name}{index}"
            for index in range(1, 6)
            for name in ("JyoCD", "Kaiji", "Nichiji", "RaceNum")
        ),
        "reserved2",
        "HatubaiHyosu",
        *(f"YukoHyosu{index}" for index in range(1, 6)),
        "HenkanFlag",
        "FuseirituFlag",
        "TekichunashiFlag",
        "CarryoverSyoki",
        "CarryoverZandaka",
    }
    assert get_table_primary_key_columns("JYUSYOSIKI_HEAD") == ["Year", "MonthDay"]
    assert set(child_fields) == {
        "Year",
        "MonthDay",
        "Num",
        "Kumi",
        "PayJyushosiki",
        "TekichuHyo",
    }
    assert get_table_primary_key_columns("JYUSYOSIKI") == ["Year", "MonthDay", "Num"]

    for table_name in ("NL_WF", "RT_WF"):
        metadata = TABLE_METADATA[table_name]
        assert [(column["name"], column["type"]) for column in metadata["columns"]] == list(
            get_table_column_types(table_name).items()
        )
        assert metadata["primary_key"] == ["Year", "MonthDay"]


def test_wf_same_length_specification_changes_are_ledgered_without_fake_layout() -> None:
    history = json.loads(
        Path("tests/fixtures/official_layout/jvdata_layout_history.json").read_text(
            encoding="utf-8"
        )
    )
    assert not any(item["record_type"] == "WF" for item in history["physical_length_changes"])
    assert [
        item for item in history["same_length_semantic_changes"] if item["record_type"] == "WF"
    ] == [
        {
            "record_type": "WF",
            "announced_date": "2011-09-28",
            "official_spec_version": "4.1.1",
            "length_unchanged": True,
            "layout_unchanged": True,
            "change_kind": "name_initial_value_and_no_hit_clarification",
            "provenance_required": False,
            "reason": (
                "The specification corrected the carryover balance field name, "
                "documented both carryover initial values, and documented the "
                "no-hit payout representation without changing the 7,215-byte layout."
            ),
            "source": "JV-Data4901.xlsx:変更履歴:107-109",
        },
        {
            "record_type": "WF",
            "announced_date": "2012-02-21",
            "official_spec_version": "4.2.0",
            "length_unchanged": True,
            "layout_unchanged": True,
            "change_kind": "status_availability_change",
            "provenance_required": False,
            "reason": (
                "Initial carryover availability for statuses 1, 2, and 9 changed "
                "to required without changing byte positions or record length."
            ),
            "source": "JV-Data4901.xlsx:変更履歴:103-105",
        },
    ]


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_wf_caller_rows_are_revalidated_before_native_mutation(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "caller.db")})
    with database:
        database.create_table("NL_WF", SCHEMAS["NL_WF"])
        importer = importer_class(database)
        assert importer.import_records(iter([parsed_record()]))["records_imported"] == 1
        before = database.fetch_all("SELECT * FROM NL_WF")

        invalid = parsed_record()
        invalid.update(
            {
                "Year": "20A6",
                "MonthDay": "0230",
                "HatubaiHyosu": "12X3",
                "CarryOverStart": "9Q8",
            }
        )
        with pytest.raises(SchemaMigrationError):
            importer.import_records(iter([invalid]))
        assert database.fetch_all("SELECT * FROM NL_WF") == before


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_wf_wrong_native_key_is_rejected_before_row_mutation(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "wrong-key.db")})
    wrong_schema = SCHEMAS["NL_WF"].replace("PRIMARY KEY (Year, MonthDay)", "PRIMARY KEY (Year)")
    with database:
        database.execute(wrong_schema)
        database.execute(
            "INSERT INTO NL_WF (RecordSpec, DataKubun, Year, MonthDay) " "VALUES (?, ?, ?, ?)",
            ("WF", "1", 2025, 101),
        )
        database.commit()
        before_schema = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='NL_WF'"
        )
        before_rows = database.fetch_all("SELECT * FROM NL_WF")

        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database).import_records(iter([parsed_record()]))

        assert (
            database.fetch_one("SELECT sql FROM sqlite_master WHERE type='table' AND name='NL_WF'")
            == before_schema
        )
        assert database.fetch_all("SELECT * FROM NL_WF") == before_rows


@pytest.mark.parametrize("table_name", ("NL_WF", "RT_WF"))
@pytest.mark.parametrize(
    ("expected", "malformed"),
    (
        pytest.param("Year INTEGER", "Year TEXT", id="numeric-key-as-text"),
        pytest.param(
            "HatubaiHyosu BIGINT",
            "HatubaiHyosu SMALLINT",
            id="undersized-vote-count",
        ),
        pytest.param(
            "PayoutsJson TEXT",
            "PayoutsJson VARCHAR(1)",
            id="bounded-json-text",
        ),
    ),
)
def test_wf_native_and_realtime_type_drift_is_rejected_before_mutation(
    tmp_path, table_name, expected, malformed
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "wrong-native-type.db")})
    with database:
        database.execute(SCHEMAS[table_name].replace(expected, malformed))
        before = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        with pytest.raises(SchemaMigrationError, match="column type"):
            verify_wf_storage_schema(database, table_name)
        assert (
            database.fetch_one(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            == before
        )
        assert _count(database, table_name) == 0


@pytest.mark.parametrize(
    ("table_name", "expected", "malformed"),
    (
        pytest.param("JYUSYOSIKI_HEAD", "MakeDate DATE", "MakeDate BLOB", id="head-date"),
        pytest.param("JYUSYOSIKI_HEAD", "Year SMALLINT", "Year TEXT", id="head-key"),
        pytest.param("JYUSYOSIKI", "Num SMALLINT", "Num BLOB", id="child-ordinal"),
    ),
)
def test_wf_standard_type_drift_is_rejected_before_mutation(
    tmp_path, table_name, expected, malformed
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "wrong-standard-type.db")})
    head_schema = JRAVAN_SCHEMAS["JYUSYOSIKI_HEAD"]
    child_schema = JRAVAN_SCHEMAS["JYUSYOSIKI"]
    if table_name == "JYUSYOSIKI_HEAD":
        head_schema = _replace_ddl_fragment(head_schema, expected, malformed)
    else:
        child_schema = _replace_ddl_fragment(child_schema, expected, malformed)
    with database:
        database.execute(head_schema)
        database.execute(child_schema)
        before = database.fetch_all(
            "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        with pytest.raises(SchemaMigrationError, match="column type"):
            verify_wf_storage_schema(database, "JYUSYOSIKI_HEAD")
        assert (
            database.fetch_all(
                "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            == before
        )
        assert _count(database, "JYUSYOSIKI_HEAD") == 0
        assert _count(database, "JYUSYOSIKI") == 0


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
def test_wf_extra_unique_constraint_is_rejected_before_silent_replacement(
    tmp_path, importer_class, standard
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "extra-unique.db")})
    with database:
        if standard:
            database.execute(
                JRAVAN_SCHEMAS["JYUSYOSIKI_HEAD"].replace(
                    "PRIMARY KEY (Year, MonthDay)",
                    "PRIMARY KEY (Year, MonthDay), UNIQUE (Year)",
                )
            )
            database.execute(JRAVAN_SCHEMAS["JYUSYOSIKI"])
        else:
            database.execute(
                SCHEMAS["NL_WF"].replace(
                    "PRIMARY KEY (Year, MonthDay)",
                    "PRIMARY KEY (Year, MonthDay), UNIQUE (Year)",
                )
            )
        target = "JYUSYOSIKI_HEAD" if standard else "NL_WF"
        before = database.fetch_all(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type IN ('table', 'index') ORDER BY type, name"
        )
        with pytest.raises(SchemaMigrationError, match="UNIQUE"):
            importer_class(database, use_jravan_schema=standard).import_records(
                iter([parsed_record(), parsed_record(month_day="0817")])
            )
        assert (
            database.fetch_all(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type IN ('table', 'index') ORDER BY type, name"
            )
            == before
        )
        assert _count(database, target) == 0
        if standard:
            assert _count(database, "JYUSYOSIKI") == 0


def test_wf_nonunique_indexes_remain_compatible(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "nonunique-index.db")})
    with database:
        database.execute(SCHEMAS["NL_WF"])
        database.execute("CREATE INDEX nl_wf_year_lookup ON NL_WF (Year)")
        _standard_tables(database)
        database.execute("CREATE INDEX jyusyosiki_year_lookup ON JYUSYOSIKI_HEAD (Year)")
        verify_wf_storage_schema(database, "NL_WF")
        verify_wf_storage_schema(database, "JYUSYOSIKI_HEAD")
        native = DataImporter(database).import_records(
            iter([parsed_record(), parsed_record(month_day="0817")])
        )
        standard = DataImporter(database, use_jravan_schema=True).import_records(
            iter([parsed_record(), parsed_record(month_day="0817")])
        )
        assert native["records_imported"] == 2
        assert standard["records_imported"] == 2
        assert _count(database, "NL_WF") == 2
        assert _count(database, "JYUSYOSIKI_HEAD") == 2
        assert _count(database, "JYUSYOSIKI") == 486


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_wf_standard_storage_is_one_parent_and_243_ordered_children(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "standard.db")})
    with database:
        database.create_table("JYUSYOSIKI_HEAD", JRAVAN_SCHEMAS["JYUSYOSIKI_HEAD"])
        database.create_table("JYUSYOSIKI", JRAVAN_SCHEMAS["JYUSYOSIKI"])
        stats = importer_class(database, use_jravan_schema=True).import_records(
            iter([parsed_record()])
        )
        assert stats["records_imported"] == 1
        assert stats["records_failed"] == 0
        assert database.fetch_one("SELECT COUNT(*) AS count FROM JYUSYOSIKI_HEAD") == {"count": 1}
        assert database.fetch_one("SELECT COUNT(*) AS count FROM JYUSYOSIKI") == {"count": 243}
        assert database.fetch_all(
            "SELECT Num, Kumi, PayJyushosiki, TekichuHyo FROM JYUSYOSIKI "
            "WHERE Num IN (1, 122, 243) ORDER BY Num"
        ) == [
            {"Num": 1, "Kumi": "0102030405", "PayJyushosiki": "123456", "TekichuHyo": "7"},
            {"Num": 122, "Kumi": "0203040506", "PayJyushosiki": "234567", "TekichuHyo": "8"},
            {"Num": 243, "Kumi": "0304050607", "PayJyushosiki": "345678", "TekichuHyo": "9"},
        ]

        cancelled = WFParser().parse(cancellation_record())
        assert cancelled is not None
        ordered = importer_class(database, use_jravan_schema=True).import_records(
            iter(
                [
                    parsed_record(data_kubun="1"),
                    parsed_record(data_kubun="2"),
                    cancelled,
                ]
            )
        )
        assert ordered["records_imported"] == 3
        assert database.fetch_one("SELECT DataKubun FROM JYUSYOSIKI_HEAD") == {"DataKubun": "9"}
        assert database.fetch_one(
            "SELECT Kumi, PayJyushosiki, TekichuHyo FROM JYUSYOSIKI WHERE Num=1"
        ) == {
            "Kumi": "0000000000",
            "PayJyushosiki": "000000100",
            "TekichuHyo": "0000000000",
        }
        opaque_delete = parsed_record(data_kubun="0")
        opaque_delete["CarryoverSyoki"] = "body-is-not-defined-for-delete"
        deleted = importer_class(database, use_jravan_schema=True).import_records(
            iter([opaque_delete])
        )
        assert deleted["records_imported"] == 1
        assert database.fetch_one("SELECT COUNT(*) AS count FROM JYUSYOSIKI_HEAD") == {"count": 0}
        assert database.fetch_one("SELECT COUNT(*) AS count FROM JYUSYOSIKI") == {"count": 0}

        restored = importer_class(database, use_jravan_schema=True).import_records(
            iter([parsed_record(data_kubun="0"), parsed_record(data_kubun="3")])
        )
        assert restored["records_imported"] == 2
        assert database.fetch_one("SELECT DataKubun FROM JYUSYOSIKI_HEAD") == {"DataKubun": "3"}
        assert database.fetch_one("SELECT COUNT(*) AS count FROM JYUSYOSIKI") == {"count": 243}


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_wf_standard_missing_child_is_rejected_before_parent_mutation(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "missing-child.db")})
    with database:
        database.create_table("JYUSYOSIKI_HEAD", JRAVAN_SCHEMAS["JYUSYOSIKI_HEAD"])
        with pytest.raises(SchemaMigrationError, match="JYUSYOSIKI"):
            importer_class(database, use_jravan_schema=True).import_records(iter([parsed_record()]))
        assert database.fetch_one("SELECT COUNT(*) AS count FROM JYUSYOSIKI_HEAD") == {"count": 0}


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_wf_standard_missing_foreign_key_is_rejected_before_mutation(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "missing-fk.db")})
    child_without_fk = """
        CREATE TABLE JYUSYOSIKI (
            Year SMALLINT,
            MonthDay SMALLINT,
            Num SMALLINT,
            Kumi VARCHAR(10),
            PayJyushosiki VARCHAR(9),
            TekichuHyo VARCHAR(10),
            PRIMARY KEY (Year, MonthDay, Num)
        )
    """
    with database:
        database.create_table("JYUSYOSIKI_HEAD", JRAVAN_SCHEMAS["JYUSYOSIKI_HEAD"])
        database.create_table("JYUSYOSIKI", child_without_fk)
        with pytest.raises(SchemaMigrationError, match="foreign key"):
            importer_class(database, use_jravan_schema=True).import_records(iter([parsed_record()]))
        assert database.fetch_one("SELECT COUNT(*) AS count FROM JYUSYOSIKI_HEAD") == {"count": 0}
        assert database.fetch_one("SELECT COUNT(*) AS count FROM JYUSYOSIKI") == {"count": 0}


def test_wf_realtime_rejects_unknown_and_accumulated_only_statuses(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "realtime.db")})
    with database:
        database.create_table("RT_WF", SCHEMAS["RT_WF"])
        updater = RealtimeUpdater(database)
        # The physical parser already refuses status 8, so the unsupported
        # status arrives only as a caller-built dictionary.
        unsupported = parsed_record()
        unsupported["DataKubun"] = "8"
        result = updater.process_parsed_records_batch([unsupported, parsed_record(data_kubun="7")])
        assert result["success"] is False
        assert result["inserted"] == 0
        assert result["errors"] == 2
        assert database.fetch_one("SELECT COUNT(*) AS count FROM RT_WF") == {"count": 0}


def test_wf_realtime_wrong_key_is_rejected_before_row_mutation(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "realtime-wrong-key.db")})
    wrong_schema = SCHEMAS["RT_WF"].replace("PRIMARY KEY (Year, MonthDay)", "PRIMARY KEY (Year)")
    with database:
        database.execute(wrong_schema)
        database.execute(
            "INSERT INTO RT_WF (RecordSpec, DataKubun, Year, MonthDay) " "VALUES (?, ?, ?, ?)",
            ("WF", "1", 2025, 101),
        )
        database.commit()
        before = database.fetch_all("SELECT * FROM RT_WF")
        result = RealtimeUpdater(database).process_parsed_records_batch(
            [parsed_record(month_day="0816"), parsed_record(month_day="0817")]
        )
        assert result["success"] is False
        assert result["inserted"] == 0
        assert database.fetch_all("SELECT * FROM RT_WF") == before


def test_wf_rejects_the_repository_only_169_byte_reconstruction() -> None:
    assert WFParser().parse(build_record()[:169]) is None


def _standard_tables(database: SQLiteDatabase) -> None:
    database.create_table("JYUSYOSIKI_HEAD", JRAVAN_SCHEMAS["JYUSYOSIKI_HEAD"])
    database.create_table("JYUSYOSIKI", JRAVAN_SCHEMAS["JYUSYOSIKI"])


def _count(database, table_name: str) -> int:
    return database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"]


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
def test_wf_auto_commit_false_rolls_back_an_earlier_flush_on_validation_failure(
    tmp_path, importer_class, standard
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "validation-rollback.db")})
    with database:
        database.execute(SCHEMAS["NL_WF"])
        _standard_tables(database)
        invalid = parsed_record(month_day="0817")
        invalid["PayoutsJson"] = "[]"
        with pytest.raises(SchemaMigrationError):
            importer_class(
                database,
                batch_size=1,
                use_jravan_schema=standard,
            ).import_records(
                iter([parsed_record(), invalid]),
                auto_commit=False,
            )
        assert database._connection is not None
        assert database._connection.in_transaction is False
        assert _count(database, "JYUSYOSIKI_HEAD" if standard else "NL_WF") == 0
        if standard:
            assert _count(database, "JYUSYOSIKI") == 0


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_wf_native_database_failure_never_enters_partial_row_fallback(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "native-db-failure.db")})
    with database:
        database.execute(SCHEMAS["NL_WF"])
        original_insert_many = database.insert_many

        def partially_failing_insert_many(table_name, rows, *args, **kwargs):
            if table_name == "NL_WF":
                original_insert_many(table_name, rows[:1], *args, **kwargs)
                raise DatabaseError("simulated WF batch failure after one row")
            return original_insert_many(table_name, rows, *args, **kwargs)

        database.insert_many = partially_failing_insert_many
        try:
            with pytest.raises(ImporterError):
                importer_class(database).import_records(
                    iter([parsed_record(), parsed_record(month_day="0817")])
                )
        finally:
            database.insert_many = original_insert_many
        assert _count(database, "NL_WF") == 0


def test_wf_realtime_database_failure_rolls_back_without_split_success(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "realtime-db-failure.db")})
    with database:
        database.execute(SCHEMAS["RT_WF"])
        original_insert = database.insert

        calls = {"RT_WF": 0}

        def partially_failing_insert(table_name, row, *args, **kwargs):
            if table_name == "RT_WF":
                calls["RT_WF"] += 1
                if calls["RT_WF"] == 2:
                    raise DatabaseError("simulated realtime WF failure after one row")
            return original_insert(table_name, row, *args, **kwargs)

        database.insert = partially_failing_insert
        try:
            result = RealtimeUpdater(database).process_parsed_records_batch(
                [parsed_record(), parsed_record(month_day="0817")]
            )
        finally:
            database.insert = original_insert
        assert result["success"] is False
        assert result["inserted"] == 0
        assert result["errors"] == 2
        assert _count(database, "RT_WF") == 0


def test_wf_realtime_transaction_result_matches_durable_mixed_and_ordered_rows(
    tmp_path,
) -> None:
    scenarios = (
        (
            "ordered-non-wf-failure",
            [
                realtime_ra_record(),
                {**realtime_ra_record(), "DataKubun": "0"},
            ],
        ),
        ("non-wf-before-wf-failure", [realtime_ra_record(), parsed_record(month_day="0817")]),
        ("wf-before-non-wf-failure", [parsed_record(), realtime_ra_record(month_day="0817")]),
        (
            "ordered-wf-failure",
            [
                parsed_record(),
                parsed_record(month_day="0817"),
                parsed_record(data_kubun="0"),
            ],
        ),
    )
    for case_id, records in scenarios:
        database = SQLiteDatabase({"path": str(tmp_path / f"{case_id}.db")})
        with database:
            database.execute(SCHEMAS["RT_WF"])
            database.execute(SCHEMAS["RT_RA"])
            database.execute(
                "CREATE TRIGGER reject_rt_wf_0817 BEFORE INSERT ON RT_WF "
                "WHEN NEW.MonthDay = 817 BEGIN SELECT RAISE(FAIL, 'reject WF 0817'); END"
            )
            database.execute(
                "CREATE TRIGGER reject_rt_ra_0817 BEFORE INSERT ON RT_RA "
                "WHEN NEW.MonthDay = 817 BEGIN SELECT RAISE(FAIL, 'reject RA 0817'); END"
            )
            database.execute(
                "CREATE TRIGGER reject_rt_ra_delete BEFORE DELETE ON RT_RA "
                "BEGIN SELECT RAISE(FAIL, 'reject RA delete'); END"
            )
            result = RealtimeUpdater(database).process_parsed_records_batch(records)
            assert result["success"] is False, case_id
            assert result["inserted"] == 0, case_id
            assert result["errors"] == len(records), case_id
            assert result["transaction_rolled_back"] is True, case_id
            assert _count(database, "RT_WF") == 0, case_id
            assert _count(database, "RT_RA") == 0, case_id

    database = SQLiteDatabase({"path": str(tmp_path / "non-strict-failure.db")})
    with database:
        database.execute(SCHEMAS["RT_RA"])
        database.execute(
            "CREATE TRIGGER reject_rt_ra_0817 BEFORE INSERT ON RT_RA "
            "WHEN NEW.MonthDay = 817 BEGIN SELECT RAISE(FAIL, 'reject RA 0817'); END"
        )
        result = RealtimeUpdater(database).process_parsed_records_batch(
            [realtime_ra_record(), realtime_ra_record(month_day="0817")]
        )
        assert result["success"] is False
        assert result["inserted"] == 0
        assert result["errors"] == 2
        assert result["transaction_rolled_back"] is True
        assert _count(database, "RT_RA") == 0

    database = SQLiteDatabase({"path": str(tmp_path / "success-boundary.db")})
    with database:
        database.execute(SCHEMAS["RT_WF"])
        database.execute(SCHEMAS["RT_RA"])
        database.execute(
            "CREATE TRIGGER reject_rt_wf_0817 BEFORE INSERT ON RT_WF "
            "WHEN NEW.MonthDay = 817 BEGIN SELECT RAISE(FAIL, 'reject WF 0817'); END"
        )
        updater = RealtimeUpdater(database)
        first = updater.process_parsed_records_batch([realtime_ra_record()])
        assert first["success"] is True
        assert first["inserted"] == 1
        second = updater.process_parsed_records_batch([parsed_record(month_day="0817")])
        assert second["success"] is False
        assert second["inserted"] == 0
        assert second["errors"] == 1
        assert _count(database, "RT_RA") == 1
        assert _count(database, "RT_WF") == 0

        same_key = updater.process_parsed_records_batch(
            [
                parsed_record(data_kubun="1"),
                parsed_record(data_kubun="2"),
                parsed_record(data_kubun="3"),
            ]
        )
        assert same_key["success"] is True
        assert same_key["inserted"] == 3
        assert same_key["errors"] == 0
        assert database.fetch_one("SELECT DataKubun FROM RT_WF") == {"DataKubun": "3"}

        ordered = updater.process_parsed_records_batch(
            [
                parsed_record(data_kubun="1"),
                parsed_record(data_kubun="2"),
                parsed_record(data_kubun="0"),
            ]
        )
        assert ordered == {
            "operation": "batch_insert",
            "success": True,
            "inserted": 3,
            "errors": 0,
            "tables": ["RT_WF"],
        }
        assert _count(database, "RT_WF") == 0


@pytest.mark.parametrize(
    ("case_id", "expected_success", "expected_inserted"),
    (
        ("empty-non-wf", True, 0),
        ("rejected-non-wf", False, 0),
        ("valid-non-wf", True, 1),
        ("strict-wf", True, 1),
    ),
)
def test_wf_realtime_does_not_commit_implicit_caller_transaction(
    tmp_path, case_id, expected_success, expected_inserted
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"implicit-{case_id}.db")})
    with database:
        database.execute("CREATE TABLE CALLER_MARKER (id INTEGER PRIMARY KEY)")
        database.execute(SCHEMAS["RT_WF"])
        database.execute(SCHEMAS["RT_RA"])
        database.commit()
        database.execute("INSERT INTO CALLER_MARKER (id) VALUES (1)")
        assert database.is_transaction_active() is False
        assert database.has_pending_transaction() is True

        records = {
            "empty-non-wf": [],
            "rejected-non-wf": [{"RecordSpec": "ZZ", "DataKubun": "1"}],
            "valid-non-wf": [realtime_ra_record()],
            "strict-wf": [parsed_record()],
        }[case_id]
        result = RealtimeUpdater(database).process_parsed_records_batch(records)
        assert result["success"] is expected_success
        assert result["inserted"] == expected_inserted
        assert database.has_pending_transaction() is True

        database.rollback()
        assert database.has_pending_transaction() is False
        assert _count(database, "CALLER_MARKER") == 0
        assert _count(database, "RT_WF") == 0
        assert _count(database, "RT_RA") == 0


def test_wf_realtime_extra_unique_constraint_is_rejected_before_mutation(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "realtime-extra-unique.db")})
    malformed = SCHEMAS["RT_WF"].replace(
        "PRIMARY KEY (Year, MonthDay)",
        "PRIMARY KEY (Year, MonthDay), UNIQUE (Year)",
    )
    with database:
        database.execute(malformed)
        result = RealtimeUpdater(database).process_parsed_records_batch(
            [parsed_record(), parsed_record(month_day="0817")]
        )
        assert result["success"] is False
        assert result["inserted"] == 0
        assert result["errors"] == 2
        assert _count(database, "RT_WF") == 0


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(
        {
            "host": os.getenv("POSTGRES_HOST") or os.getenv("PGHOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT") or os.getenv("PGPORT", "5432")),
            "database": os.getenv("POSTGRES_DB") or os.getenv("PGDATABASE", "jltsql_test"),
            "user": os.getenv("POSTGRES_USER") or os.getenv("PGUSER", "jltsql"),
            "password": os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD", ""),
            "connect_timeout": 5,
        }
    )
    schema_name = f"jlt_wf_{uuid4().hex[:12]}"
    database.connect()
    try:
        database.execute(f"CREATE SCHEMA {schema_name}")
        database.execute(f"SET search_path TO {schema_name}")
        database.commit()
        yield database
    finally:
        try:
            database.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
            database.commit()
        finally:
            database.disconnect()


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize("auto_commit", (True, False))
def test_wf_native_provider_order_retains_status_nine_and_erases_status_zero(
    tmp_path, importer_class, auto_commit
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "native-order.db")})
    with database:
        database.create_table("NL_WF", SCHEMAS["NL_WF"])
        cancelled = WFParser().parse(cancellation_record())
        assert cancelled is not None

        importer = importer_class(database)
        ordered = importer.import_records(
            iter(
                [
                    parsed_record(data_kubun="1"),
                    parsed_record(data_kubun="2"),
                    cancelled,
                ]
            ),
            auto_commit=auto_commit,
        )
        if not auto_commit:
            database.commit()
        assert ordered["records_imported"] == 3
        assert ordered["records_failed"] == 0
        row = database.fetch_one("SELECT * FROM NL_WF")
        assert row["DataKubun"] == "9"
        assert (row["Year"], row["MonthDay"]) == (2026, 816)
        assert json.loads(row["PayoutsJson"])[0] == {
            "Kumi": "0000000000",
            "PayJyushosiki": "000000100",
            "TekichuHyosu": "0000000000",
        }

        erased = importer_class(database).import_records(
            iter([parsed_record(data_kubun="0")]), auto_commit=auto_commit
        )
        if not auto_commit:
            database.commit()
        assert erased["records_imported"] == 1
        assert _count(database, "NL_WF") == 0

        restored = importer_class(database).import_records(
            iter(
                [
                    parsed_record(data_kubun="0"),
                    parsed_record(data_kubun="3"),
                    parsed_record(data_kubun="7"),
                ]
            ),
            auto_commit=auto_commit,
        )
        if not auto_commit:
            database.commit()
        assert restored["records_imported"] == 3
        row = database.fetch_one("SELECT * FROM NL_WF")
        assert row["DataKubun"] == "7"
        assert [row[f"RaceInfo{index}"] for index in range(1, 6)] == [
            "01020408",
            "02030509",
            "03040610",
            "04050711",
            "05060812",
        ]
        assert [row[f"YukoHyosu{index}"] for index in range(1, 6)] == [
            100,
            80,
            60,
            40,
            24,
        ]
        assert (row["HatubaiHyosu"], row["CarryOverStart"], row["CarryOverBalance"]) == (
            123456,
            1000,
            2000,
        )
        payouts = json.loads(row["PayoutsJson"])
        assert len(payouts) == 243
        assert [payouts[index - 1] for index in (1, 122, 243)] == [
            {"Kumi": "0102030405", "PayJyushosiki": "123456", "TekichuHyosu": "7"},
            {"Kumi": "0203040506", "PayJyushosiki": "234567", "TekichuHyosu": "8"},
            {"Kumi": "0304050607", "PayJyushosiki": "345678", "TekichuHyosu": "9"},
        ]
        assert payouts[1] == {"Kumi": "", "PayJyushosiki": "", "TekichuHyosu": ""}


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize("failure_type", (DatabaseError, RuntimeError))
def test_wf_standard_replacement_is_atomic_when_auto_commit_is_off(
    tmp_path, importer_class, failure_type
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "standard-atomic.db")})
    with database:
        _standard_tables(database)
        importer = importer_class(database, use_jravan_schema=True)
        stats = importer.import_records(iter([parsed_record()]), auto_commit=False)
        database.commit()
        assert stats["records_imported"] == 1
        assert _count(database, "JYUSYOSIKI_HEAD") == 1
        assert _count(database, "JYUSYOSIKI") == 243

        before_head = database.fetch_all("SELECT * FROM JYUSYOSIKI_HEAD")
        before_children = database.fetch_all("SELECT * FROM JYUSYOSIKI ORDER BY Num")

        original_insert_many = database.insert_many
        child_inserts = {"count": 0}

        def failing_insert_many(table_name, rows, *args, **kwargs):
            if table_name == "JYUSYOSIKI":
                child_inserts["count"] += 1
                if child_inserts["count"] == 2:
                    raise failure_type("simulated child insert failure")
            return original_insert_many(table_name, rows, *args, **kwargs)

        database.insert_many = failing_insert_many
        try:
            with pytest.raises(ImporterError):
                importer_class(database, use_jravan_schema=True).import_records(
                    iter([parsed_record(data_kubun="1"), parsed_record(data_kubun="2")]),
                    auto_commit=False,
                )
        finally:
            database.insert_many = original_insert_many

        assert database.fetch_all("SELECT * FROM JYUSYOSIKI_HEAD") == before_head
        assert database.fetch_all("SELECT * FROM JYUSYOSIKI ORDER BY Num") == before_children


def test_wf_single_record_import_covers_native_and_standard_storage(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "single.db")})
    with database:
        database.create_table("NL_WF", SCHEMAS["NL_WF"])
        _standard_tables(database)

        native = DataImporter(database)
        assert native.import_single_record(parsed_record()) is True
        assert _count(database, "NL_WF") == 1
        invalid = parsed_record()
        invalid["CarryOverStart"] = "9Q8"
        with pytest.raises(SchemaMigrationError):
            native.import_single_record(invalid)
        assert database.fetch_one("SELECT CarryOverStart FROM NL_WF") == {"CarryOverStart": 1000}
        assert native.import_single_record(parsed_record(data_kubun="0")) is True
        assert _count(database, "NL_WF") == 0

        standard = DataImporter(database, use_jravan_schema=True)
        distinct_flags = WFParser().parse(no_hit_record(data_kubun="7"))
        assert distinct_flags is not None
        distinct_flags["HenkanFlag"] = "1"
        distinct_flags["headRecordSpec"] = distinct_flags.pop("RecordSpec")
        distinct_flags["headDataKubun"] = distinct_flags.pop("DataKubun")
        assert standard.import_single_record(distinct_flags) is True
        assert _count(database, "JYUSYOSIKI_HEAD") == 1
        assert _count(database, "JYUSYOSIKI") == 243
        head = database.fetch_one("SELECT * FROM JYUSYOSIKI_HEAD")
        assert {
            column: head[column]
            for column in (
                "RecordSpec",
                "DataKubun",
                "MakeDate",
                "Year",
                "MonthDay",
                "reserved1",
                "reserved2",
                "HatubaiHyosu",
                "HenkanFlag",
                "FuseirituFlag",
                "TekichunashiFlag",
                "CarryoverSyoki",
                "CarryoverZandaka",
            )
        } == {
            "RecordSpec": "WF",
            "DataKubun": "7",
            "MakeDate": 20260817,
            "Year": 2026,
            "MonthDay": 816,
            "reserved1": "00",
            "reserved2": "000000",
            "HatubaiHyosu": "123456",
            "HenkanFlag": "1",
            "FuseirituFlag": "0",
            "TekichunashiFlag": "1",
            "CarryoverSyoki": "1000",
            "CarryoverZandaka": "2000",
        }
        assert [
            (
                head[f"JyoCD{index}"],
                head[f"Kaiji{index}"],
                head[f"Nichiji{index}"],
                head[f"RaceNum{index}"],
            )
            for index in range(1, 6)
        ] == [
            ("01", 2, 4, 8),
            ("02", 3, 5, 9),
            ("03", 4, 6, 10),
            ("04", 5, 7, 11),
            ("05", 6, 8, 12),
        ]
        assert [head[f"YukoHyosu{index}"] for index in range(1, 6)] == [
            "100",
            "80",
            "60",
            "40",
            "24",
        ]
        assert database.fetch_all(
            "SELECT Num, Kumi, PayJyushosiki, TekichuHyo FROM JYUSYOSIKI "
            "WHERE Num IN (1, 2, 122, 243) ORDER BY Num"
        ) == [
            {
                "Num": 1,
                "Kumi": "0102030405",
                "PayJyushosiki": "000000000",
                "TekichuHyo": "0000000000",
            },
            {"Num": 2, "Kumi": None, "PayJyushosiki": None, "TekichuHyo": None},
            {
                "Num": 122,
                "Kumi": "0203040506",
                "PayJyushosiki": "000000000",
                "TekichuHyo": "0000000000",
            },
            {
                "Num": 243,
                "Kumi": "0304050607",
                "PayJyushosiki": "000000000",
                "TekichuHyo": "0000000000",
            },
        ]
        native_flags = DataImporter(database)
        assert native_flags.import_single_record(distinct_flags) is True
        assert database.fetch_one(
            "SELECT DataKubun, HenkanFlag, FuseirituFlag, TekichuNasiFlag FROM NL_WF"
        ) == {
            "DataKubun": "7",
            "HenkanFlag": "1",
            "FuseirituFlag": "0",
            "TekichuNasiFlag": "1",
        }
        assert native_flags.import_single_record(parsed_record(data_kubun="0")) is True
        assert _count(database, "NL_WF") == 0
        with pytest.raises(SchemaMigrationError):
            standard.import_single_record(invalid)
        assert _count(database, "JYUSYOSIKI") == 243
        cancelled = WFParser().parse(cancellation_record())
        assert cancelled is not None
        assert standard.import_single_record(cancelled) is True
        assert database.fetch_one("SELECT DataKubun FROM JYUSYOSIKI_HEAD") == {"DataKubun": "9"}
        assert standard.import_single_record(parsed_record(data_kubun="0")) is True
        assert _count(database, "JYUSYOSIKI_HEAD") == 0
        assert _count(database, "JYUSYOSIKI") == 0


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
def test_wf_single_record_owned_transaction_rolls_back_on_validation_failure(
    tmp_path, standard
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "single-owned-transaction.db")})
    with database:
        database.create_table("NL_WF", SCHEMAS["NL_WF"])
        _standard_tables(database)
        importer = DataImporter(database, use_jravan_schema=standard)
        target = "JYUSYOSIKI_HEAD" if standard else "NL_WF"

        assert importer.import_single_record(parsed_record()) is True
        baseline_stats = importer.get_statistics()
        assert baseline_stats["records_imported"] == 1
        assert baseline_stats["records_failed"] == 0

        assert (
            importer.import_single_record(parsed_record(month_day="0817"), auto_commit=False)
            is True
        )
        invalid = parsed_record(month_day="0818")
        invalid["PayoutsJson"] = "[]"
        with pytest.raises(SchemaMigrationError):
            importer.import_single_record(invalid, auto_commit=False)

        assert database.is_transaction_active() is False
        assert _count(database, target) == 1
        assert importer.get_statistics() == baseline_stats
        if standard:
            assert _count(database, "JYUSYOSIKI") == 243

        assert (
            importer.import_single_record(parsed_record(month_day="0817"), auto_commit=False)
            is True
        )
        database.commit()
        assert _count(database, target) == 2
        expected_stats = dict(baseline_stats)
        expected_stats["records_imported"] += 1
        if standard:
            expected_stats["batches_processed"] += 1
        assert importer.get_statistics() == expected_stats
        if standard:
            assert _count(database, "JYUSYOSIKI") == 486

        # A caller may commit one importer sequence and start the next
        # transaction before the importer observes the inactive boundary. A
        # failure in that new transaction must not restore the already
        # committed sequence's older statistics checkpoint.
        database.begin_transaction()
        invalid = parsed_record(month_day="0819")
        invalid["DataKubun"] = "8"
        with pytest.raises(SchemaMigrationError):
            importer.import_single_record(invalid, auto_commit=False)
        assert database.is_transaction_active() is False
        assert _count(database, target) == 2
        assert importer.get_statistics() == expected_stats
        if standard:
            assert _count(database, "JYUSYOSIKI") == 486

        assert (
            importer.import_single_record(parsed_record(month_day="0819"), auto_commit=False)
            is True
        )
        database.commit()
        assert _count(database, target) == 3
        expected_stats["records_imported"] += 1
        if standard:
            expected_stats["batches_processed"] += 1
            assert _count(database, "JYUSYOSIKI") == 729
        assert importer.get_statistics() == expected_stats


def _corrupt_caller_records(*, standard: bool) -> list[tuple[str, dict]]:
    cases = []

    record = parsed_record()
    record["headRecordSpec"] = "RA"
    cases.append(("conflicting-record-type-alias", record))

    record = parsed_record()
    record["headDataKubun"] = "2"
    cases.append(("conflicting-status-alias", record))

    record = parsed_record()
    record.pop("DataKubun")
    cases.append(("missing-status", record))

    if standard:
        # Native and standard names for the same header field must agree when
        # a caller supplies both for the standard-name owner table.
        record = parsed_record()
        record["DataKubun"] = "7"
        record["headDataKubun"] = "7"
        record["TekichunashiFlag"] = "1"
        cases.append(("conflicting-standard-flag-alias", record))
        record = parsed_record()
        record["Kaiji3"] = "9"
        cases.append(("conflicting-split-race-field", record))

    record = parsed_record()
    record["PayoutsJson"] = "{not json"
    cases.append(("malformed-payout-json", record))

    record = parsed_record()
    record["PayoutsJson"] = json.dumps(json.loads(record["PayoutsJson"])[:242])
    cases.append(("payout-count-242", record))

    record = parsed_record()
    payouts = json.loads(record["PayoutsJson"])
    payouts[121]["PayJyushosiki"] = ""
    record["PayoutsJson"] = json.dumps(payouts)
    cases.append(("partial-payout-tuple", record))

    record = parsed_record()
    payouts = json.loads(record["PayoutsJson"])
    payouts[242]["Extra"] = "1"
    record["PayoutsJson"] = json.dumps(payouts)
    cases.append(("payout-extra-key", record))

    record = parsed_record()
    payouts = json.loads(record["PayoutsJson"])
    payouts[0]["Kumi"] = "01020304X5"
    record["PayoutsJson"] = json.dumps(payouts)
    cases.append(("payout-nondigit-kumi", record))

    record = parsed_record()
    payouts = json.loads(record["PayoutsJson"])
    payouts[0]["Kumi"] = "01020304050"
    record["PayoutsJson"] = json.dumps(payouts)
    cases.append(("payout-overwidth-kumi", record))

    record = parsed_record(data_kubun="3")
    record["TekichuNasiFlag"] = "1"
    cases.append(("no-hit-with-positive-pay-and-votes", record))

    record = parsed_record()
    record["RaceInfo2"] = "0501010"
    cases.append(("short-race-composite", record))
    return cases


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
def test_wf_caller_alias_and_payout_json_corruption_is_rejected_before_mutation(
    tmp_path, importer_class, standard
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "corrupt.db")})
    with database:
        database.create_table("NL_WF", SCHEMAS["NL_WF"])
        _standard_tables(database)
        importer = importer_class(database, use_jravan_schema=standard)
        assert importer.import_records(iter([parsed_record()]))["records_imported"] == 1
        tables = ("JYUSYOSIKI_HEAD", "JYUSYOSIKI") if standard else ("NL_WF",)
        before = {table: database.fetch_all(f"SELECT * FROM {table}") for table in tables}

        for case_id, record in _corrupt_caller_records(standard=standard):
            with pytest.raises(SchemaMigrationError):
                importer_class(database, use_jravan_schema=standard).import_records(iter([record]))
            for table in tables:
                assert database.fetch_all(f"SELECT * FROM {table}") == before[table], case_id


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize(
    "child_schema",
    (
        pytest.param(
            """
            CREATE TABLE JYUSYOSIKI (
                Year SMALLINT,
                MonthDay SMALLINT,
                Num SMALLINT,
                Kumi VARCHAR(10),
                PayJyushosiki VARCHAR(9),
                TekichuHyo VARCHAR(10),
                PRIMARY KEY (Year, MonthDay, Num),
                FOREIGN KEY (Year, MonthDay) REFERENCES JYUSYOSIKI_HEAD (Year, MonthDay)
            )
            """,
            id="no-cascade",
        ),
        pytest.param(
            """
            CREATE TABLE JYUSYOSIKI (
                Year SMALLINT,
                MonthDay SMALLINT,
                Num SMALLINT,
                Kumi VARCHAR(10),
                PayJyushosiki VARCHAR(9),
                TekichuHyo VARCHAR(10),
                PRIMARY KEY (Year, MonthDay, Num),
                FOREIGN KEY (Year, MonthDay) REFERENCES JYUSYOSIKI_HEAD (Year, MonthDay)
                    ON UPDATE CASCADE ON DELETE CASCADE
            )
            """,
            id="update-cascade",
        ),
        pytest.param(
            """
            CREATE TABLE JYUSYOSIKI (
                Year SMALLINT,
                MonthDay SMALLINT,
                Num SMALLINT,
                Kumi VARCHAR(10),
                PayJyushosiki VARCHAR(9),
                TekichuHyo VARCHAR(10),
                PRIMARY KEY (Year, MonthDay, Num),
                FOREIGN KEY (MonthDay, Year) REFERENCES JYUSYOSIKI_HEAD (MonthDay, Year)
                    ON DELETE CASCADE
            )
            """,
            id="swapped-key-order",
        ),
        pytest.param(
            """
            CREATE TABLE JYUSYOSIKI (
                Year SMALLINT,
                MonthDay SMALLINT,
                Num SMALLINT,
                Kumi VARCHAR(10),
                PayJyushosiki VARCHAR(9),
                TekichuHyo VARCHAR(10),
                PRIMARY KEY (Year, MonthDay, Num),
                FOREIGN KEY (Year, MonthDay) REFERENCES NL_WF (Year, MonthDay)
                    ON DELETE CASCADE
            )
            """,
            id="wrong-parent-table",
        ),
        pytest.param(
            """
            CREATE TABLE JYUSYOSIKI (
                Year SMALLINT,
                MonthDay SMALLINT,
                Num SMALLINT,
                Kumi VARCHAR(10),
                PayJyushosiki VARCHAR(9),
                TekichuHyo VARCHAR(10),
                PRIMARY KEY (Year, MonthDay),
                FOREIGN KEY (Year, MonthDay) REFERENCES JYUSYOSIKI_HEAD (Year, MonthDay)
                    ON DELETE CASCADE
            )
            """,
            id="child-key-without-num",
        ),
    ),
)
def test_wf_standard_malformed_child_contract_is_rejected_before_mutation(
    tmp_path, importer_class, child_schema
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "malformed-child.db")})
    with database:
        database.create_table("NL_WF", SCHEMAS["NL_WF"])
        database.create_table("JYUSYOSIKI_HEAD", JRAVAN_SCHEMAS["JYUSYOSIKI_HEAD"])
        database.create_table("JYUSYOSIKI", child_schema)
        before = database.fetch_all(
            "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        with pytest.raises(SchemaMigrationError):
            importer_class(database, use_jravan_schema=True).import_records(iter([parsed_record()]))
        assert (
            database.fetch_all(
                "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            == before
        )
        assert _count(database, "JYUSYOSIKI_HEAD") == 0
        assert _count(database, "JYUSYOSIKI") == 0


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_wf_legacy_only_win5_standard_storage_is_refused(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-win5.db")})
    with database:
        database.execute("CREATE TABLE WIN5 (Year INTEGER, MonthDay INTEGER, PayoutsJson TEXT)")
        database.commit()
        with pytest.raises(SchemaMigrationError, match="WIN5"):
            importer_class(database, use_jravan_schema=True).import_records(iter([parsed_record()]))
        assert database.table_exists("JYUSYOSIKI_HEAD") is False
        assert database.table_exists("JYUSYOSIKI") is False
        assert _count(database, "WIN5") == 0


def test_wf_realtime_raw_and_parsed_paths_upsert_retain_and_erase(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "realtime-paths.db")})
    with database:
        database.create_table("RT_WF", SCHEMAS["RT_WF"])
        updater = RealtimeUpdater(database)

        raw_new = updater.process_record(build_record(data_kubun="1"))
        assert raw_new["success"] is True
        parsed_update = updater.process_parsed_record(parsed_record(data_kubun="2"))
        assert parsed_update["success"] is True

        alias_only = parsed_record(data_kubun="2")
        alias_only["headRecordSpec"] = alias_only.pop("RecordSpec")
        alias_only["headDataKubun"] = alias_only.pop("DataKubun")
        alias_result = updater.process_parsed_record(alias_only)
        assert alias_result["success"] is True
        assert database.fetch_one(
            "SELECT RecordSpec, DataKubun FROM RT_WF WHERE Year = 2026 AND MonthDay = 816"
        ) == {"RecordSpec": "WF", "DataKubun": "2"}

        raw_final = updater.process_record(build_record(data_kubun="3"))
        assert raw_final["success"] is True
        assert _count(database, "RT_WF") == 1
        row = database.fetch_one("SELECT * FROM RT_WF")
        assert row["DataKubun"] == "3"
        payouts = json.loads(row["PayoutsJson"])
        assert [payouts[index - 1] for index in (1, 122, 243)] == [
            {"Kumi": "0102030405", "PayJyushosiki": "123456", "TekichuHyosu": "7"},
            {"Kumi": "0203040506", "PayJyushosiki": "234567", "TekichuHyosu": "8"},
            {"Kumi": "0304050607", "PayJyushosiki": "345678", "TekichuHyosu": "9"},
        ]

        cancelled = updater.process_record(cancellation_record())
        assert cancelled["success"] is True
        row = database.fetch_one("SELECT DataKubun, PayoutsJson FROM RT_WF")
        assert row["DataKubun"] == "9"
        assert json.loads(row["PayoutsJson"])[0] == {
            "Kumi": "0000000000",
            "PayJyushosiki": "000000100",
            "TekichuHyosu": "0000000000",
        }

        assert updater.process_record(build_record(data_kubun="8")) is None
        assert updater.process_record(build_record(month_day="0230")) is None
        accumulated_only = updater.process_record(build_record(data_kubun="7"))
        assert accumulated_only["success"] is False
        parsed_accumulated_only = updater.process_parsed_record(parsed_record(data_kubun="7"))
        assert parsed_accumulated_only["success"] is False
        corrupt = parsed_record()
        corrupt["PayoutsJson"] = "[]"
        assert updater.process_parsed_record(corrupt)["success"] is False
        alias_conflict = parsed_record()
        alias_conflict["headDataKubun"] = "1"
        conflict_result = updater.process_parsed_record(alias_conflict)
        assert conflict_result["success"] is False
        assert conflict_result["operation"] == "validate"
        batch = updater.process_parsed_records_batch([corrupt, parsed_record(month_day="0817")])
        assert batch["success"] is False
        assert batch["errors"] == 2
        assert batch["inserted"] == 0
        assert database.fetch_one("SELECT DataKubun FROM RT_WF WHERE MonthDay = 816") == {
            "DataKubun": "9"
        }
        assert _count(database, "RT_WF") == 1

        erased = updater.process_record(build_record(data_kubun="0"))
        assert erased["success"] is True
        assert database.fetch_all("SELECT MonthDay FROM RT_WF") == []


def test_wf_postgresql_native_standard_and_realtime_contract(postgresql_db) -> None:
    for table_name in ("NL_WF", "RT_WF"):
        postgresql_db.execute(SCHEMAS[table_name])
    postgresql_db.execute(JRAVAN_SCHEMAS["JYUSYOSIKI_HEAD"])
    postgresql_db.execute(JRAVAN_SCHEMAS["JYUSYOSIKI"])
    postgresql_db.commit()
    for table_name in ("NL_WF", "RT_WF"):
        assert SchemaManager(postgresql_db).apply_metadata_to_table(table_name) is True
    postgresql_db.commit()

    cancelled = WFParser().parse(cancellation_record())
    assert cancelled is not None
    for importer_class in (DataImporter, OptimizedDataImporter):
        for standard in (False, True):
            head = "JYUSYOSIKI_HEAD" if standard else "NL_WF"
            importer = importer_class(postgresql_db, use_jravan_schema=standard)
            stats = importer.import_records(iter([parsed_record()]))
            assert stats["records_imported"] == 1
            assert _count(postgresql_db, head) == 1
            if standard:
                assert _count(postgresql_db, "JYUSYOSIKI") == 243
                assert postgresql_db.fetch_all(
                    "SELECT Num AS num, Kumi AS kumi, PayJyushosiki AS pay, "
                    "TekichuHyo AS votes FROM JYUSYOSIKI WHERE Num IN (1, 122, 243) "
                    "ORDER BY Num"
                ) == [
                    {"num": 1, "kumi": "0102030405", "pay": "123456", "votes": "7"},
                    {"num": 122, "kumi": "0203040506", "pay": "234567", "votes": "8"},
                    {"num": 243, "kumi": "0304050607", "pay": "345678", "votes": "9"},
                ]
            ordered = importer_class(postgresql_db, use_jravan_schema=standard).import_records(
                iter([parsed_record(data_kubun="1"), parsed_record(data_kubun="2"), cancelled])
            )
            assert ordered["records_failed"] == 0
            if standard:
                assert ordered["records_imported"] == 3
            else:
                # The generic PostgreSQL upsert collapses same-key rows of one
                # VALUES batch to the last provider row, so only the final
                # state is a stable contract for native storage.
                assert ordered["records_imported"] >= 1
            assert postgresql_db.fetch_one(f"SELECT DataKubun AS status FROM {head}") == {
                "status": "9"
            }
            if standard:
                assert postgresql_db.fetch_one(
                    "SELECT Kumi AS kumi, PayJyushosiki AS pay, TekichuHyo AS votes "
                    "FROM JYUSYOSIKI WHERE Num = 1"
                ) == {"kumi": "0000000000", "pay": "000000100", "votes": "0000000000"}
            erased = importer_class(postgresql_db, use_jravan_schema=standard).import_records(
                iter([parsed_record(data_kubun="0")])
            )
            assert erased["records_imported"] == 1
            assert _count(postgresql_db, head) == 0
            if standard:
                assert _count(postgresql_db, "JYUSYOSIKI") == 0

    updater = RealtimeUpdater(postgresql_db)
    batch = updater.process_parsed_records_batch(
        [parsed_record(data_kubun="1"), parsed_record(data_kubun="7")]
    )
    assert batch["success"] is False
    assert batch["inserted"] == 0
    assert batch["errors"] == 2
    assert updater.process_record(cancellation_record())["success"] is True
    assert postgresql_db.fetch_one("SELECT DataKubun AS status FROM RT_WF") == {"status": "9"}
    assert updater.process_record(build_record(data_kubun="0"))["success"] is True
    assert _count(postgresql_db, "RT_WF") == 0
    postgresql_db.commit()

    constraint_query = (
        "SELECT contype AS type, pg_get_constraintdef(oid) AS definition "
        "FROM pg_constraint WHERE conrelid = to_regclass(?) ORDER BY contype, conname"
    )
    postgresql_db.execute("DROP TABLE JYUSYOSIKI")
    postgresql_db.execute(
        "CREATE TABLE JYUSYOSIKI (Year SMALLINT, MonthDay SMALLINT, Num SMALLINT, "
        "Kumi VARCHAR(10), PayJyushosiki VARCHAR(9), TekichuHyo VARCHAR(10), "
        "PRIMARY KEY (Year, MonthDay, Num), FOREIGN KEY (Year, MonthDay) "
        "REFERENCES JYUSYOSIKI_HEAD (Year, MonthDay))"
    )
    postgresql_db.commit()
    before = postgresql_db.fetch_all(constraint_query, ("jyusyosiki",))
    for importer_class in (DataImporter, OptimizedDataImporter):
        with pytest.raises(SchemaMigrationError, match="foreign key"):
            importer_class(postgresql_db, use_jravan_schema=True).import_records(
                iter([parsed_record()])
            )
        postgresql_db.rollback()
        assert postgresql_db.fetch_all(constraint_query, ("jyusyosiki",)) == before
        assert _count(postgresql_db, "JYUSYOSIKI_HEAD") == 0

    for table_name in ("NL_WF", "RT_WF"):
        postgresql_db.execute(f"DROP TABLE {table_name}")
        postgresql_db.execute(
            SCHEMAS[table_name].replace("PRIMARY KEY (Year, MonthDay)", "PRIMARY KEY (Year)")
        )
        postgresql_db.commit()
    before_key = postgresql_db.fetch_all(constraint_query, ("nl_wf",))
    for importer_class in (DataImporter, OptimizedDataImporter):
        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(postgresql_db).import_records(iter([parsed_record()]))
        postgresql_db.rollback()
        assert postgresql_db.fetch_all(constraint_query, ("nl_wf",)) == before_key
        assert _count(postgresql_db, "NL_WF") == 0
    result = RealtimeUpdater(postgresql_db).process_parsed_records_batch([parsed_record()])
    assert result["success"] is False
    assert result["inserted"] == 0
    postgresql_db.rollback()
    assert _count(postgresql_db, "RT_WF") == 0


@pytest.mark.parametrize(
    ("case_id", "expected_success", "expected_inserted"),
    (
        ("empty-non-wf", True, 0),
        ("rejected-non-wf", False, 0),
        ("valid-non-wf", True, 1),
        ("strict-wf", True, 1),
    ),
)
def test_wf_postgresql_realtime_does_not_commit_implicit_caller_transaction(
    postgresql_db, case_id, expected_success, expected_inserted
) -> None:
    postgresql_db.execute("CREATE TABLE CALLER_MARKER (id INTEGER PRIMARY KEY)")
    postgresql_db.execute(SCHEMAS["RT_WF"])
    postgresql_db.execute(SCHEMAS["RT_RA"])
    postgresql_db.commit()
    postgresql_db.execute("INSERT INTO CALLER_MARKER (id) VALUES (1)")
    assert postgresql_db.is_transaction_active() is False
    assert postgresql_db.has_pending_transaction() is True

    records = {
        "empty-non-wf": [],
        "rejected-non-wf": [{"RecordSpec": "ZZ", "DataKubun": "1"}],
        "valid-non-wf": [realtime_ra_record()],
        "strict-wf": [parsed_record()],
    }[case_id]
    result = RealtimeUpdater(postgresql_db).process_parsed_records_batch(records)
    assert result["success"] is expected_success
    assert result["inserted"] == expected_inserted
    assert postgresql_db.has_pending_transaction() is True

    postgresql_db.rollback()
    assert postgresql_db.has_pending_transaction() is False
    assert _count(postgresql_db, "CALLER_MARKER") == 0
    assert _count(postgresql_db, "RT_WF") == 0
    assert _count(postgresql_db, "RT_RA") == 0
    postgresql_db.commit()


@pytest.mark.parametrize(
    ("expected", "malformed", "message"),
    (
        pytest.param(
            "HatubaiHyosu BIGINT",
            "HatubaiHyosu SMALLINT",
            "column type",
            id="undersized-numeric",
        ),
        pytest.param(
            "PayoutsJson TEXT",
            "PayoutsJson VARCHAR(1)",
            "column type",
            id="bounded-json-text",
        ),
        pytest.param(
            "PRIMARY KEY (Year, MonthDay)",
            "PRIMARY KEY (Year, MonthDay) DEFERRABLE INITIALLY DEFERRED",
            "primary key",
            id="deferrable-primary-key",
        ),
        pytest.param(
            "PRIMARY KEY (Year, MonthDay)",
            "PRIMARY KEY (Year, MonthDay), UNIQUE (Year)",
            "UNIQUE",
            id="extra-unique",
        ),
    ),
)
def test_wf_postgresql_native_schema_drift_is_rejected(
    postgresql_db, expected, malformed, message
) -> None:
    postgresql_db.execute(SCHEMAS["NL_WF"].replace(expected, malformed))
    postgresql_db.commit()
    before = postgresql_db.fetch_all(
        "SELECT contype AS type, condeferrable AS deferrable, "
        "condeferred AS deferred, pg_get_constraintdef(oid) AS definition "
        "FROM pg_constraint WHERE conrelid = to_regclass(?) ORDER BY contype, conname",
        ("nl_wf",),
    )
    with pytest.raises(SchemaMigrationError, match=message):
        verify_wf_storage_schema(postgresql_db, "NL_WF")
    postgresql_db.rollback()
    assert (
        postgresql_db.fetch_all(
            "SELECT contype AS type, condeferrable AS deferrable, "
            "condeferred AS deferred, pg_get_constraintdef(oid) AS definition "
            "FROM pg_constraint WHERE conrelid = to_regclass(?) ORDER BY contype, conname",
            ("nl_wf",),
        )
        == before
    )
    assert _count(postgresql_db, "NL_WF") == 0


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
def test_wf_postgresql_auto_commit_false_validation_failure_rolls_back(
    postgresql_db, importer_class, standard
) -> None:
    postgresql_db.execute(SCHEMAS["NL_WF"])
    postgresql_db.execute(JRAVAN_SCHEMAS["JYUSYOSIKI_HEAD"])
    postgresql_db.execute(JRAVAN_SCHEMAS["JYUSYOSIKI"])
    postgresql_db.commit()
    invalid = parsed_record(month_day="0817")
    invalid["PayoutsJson"] = "[]"
    with pytest.raises(SchemaMigrationError):
        importer_class(
            postgresql_db,
            batch_size=1,
            use_jravan_schema=standard,
        ).import_records(
            iter([parsed_record(), invalid]),
            auto_commit=False,
        )
    assert _count(postgresql_db, "JYUSYOSIKI_HEAD" if standard else "NL_WF") == 0
    if standard:
        assert _count(postgresql_db, "JYUSYOSIKI") == 0
    postgresql_db.commit()

    if importer_class is not DataImporter:
        return
    single = DataImporter(postgresql_db, use_jravan_schema=standard)
    target = "JYUSYOSIKI_HEAD" if standard else "NL_WF"
    assert single.import_single_record(parsed_record()) is True
    baseline_stats = single.get_statistics()
    assert baseline_stats["records_imported"] == 1
    assert baseline_stats["records_failed"] == 0
    assert single.import_single_record(parsed_record(month_day="0817"), auto_commit=False) is True
    invalid = parsed_record(month_day="0818")
    invalid["PayoutsJson"] = "[]"
    with pytest.raises(SchemaMigrationError):
        single.import_single_record(invalid, auto_commit=False)
    assert postgresql_db.is_transaction_active() is False
    assert _count(postgresql_db, target) == 1
    assert single.get_statistics() == baseline_stats
    if standard:
        assert _count(postgresql_db, "JYUSYOSIKI") == 243

    assert single.import_single_record(parsed_record(month_day="0817"), auto_commit=False) is True
    postgresql_db.commit()
    assert _count(postgresql_db, target) == 2
    expected_stats = dict(baseline_stats)
    expected_stats["records_imported"] += 1
    if standard:
        expected_stats["batches_processed"] += 1
    assert single.get_statistics() == expected_stats
    if standard:
        assert _count(postgresql_db, "JYUSYOSIKI") == 486

    postgresql_db.begin_transaction()
    invalid = parsed_record(month_day="0819")
    invalid["DataKubun"] = "8"
    with pytest.raises(SchemaMigrationError):
        single.import_single_record(invalid, auto_commit=False)
    assert postgresql_db.is_transaction_active() is False
    assert _count(postgresql_db, target) == 2
    assert single.get_statistics() == expected_stats
    if standard:
        assert _count(postgresql_db, "JYUSYOSIKI") == 486

    assert single.import_single_record(parsed_record(month_day="0819"), auto_commit=False) is True
    postgresql_db.commit()
    assert _count(postgresql_db, target) == 3
    expected_stats["records_imported"] += 1
    if standard:
        expected_stats["batches_processed"] += 1
        assert _count(postgresql_db, "JYUSYOSIKI") == 729
    assert single.get_statistics() == expected_stats


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_wf_postgresql_native_database_failure_is_atomic(postgresql_db, importer_class) -> None:
    postgresql_db.execute(SCHEMAS["NL_WF"])
    postgresql_db.execute(
        "CREATE FUNCTION reject_second_wf() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN IF NEW.monthday = 817 THEN RAISE EXCEPTION 'simulated WF failure'; "
        "END IF; RETURN NEW; END $$"
    )
    postgresql_db.execute(
        "CREATE TRIGGER reject_second_wf BEFORE INSERT OR UPDATE ON NL_WF "
        "FOR EACH ROW EXECUTE FUNCTION reject_second_wf()"
    )
    postgresql_db.commit()
    with pytest.raises(ImporterError):
        importer_class(postgresql_db).import_records(
            iter([parsed_record(), parsed_record(month_day="0817")])
        )
    assert _count(postgresql_db, "NL_WF") == 0
    postgresql_db.commit()


def test_wf_postgresql_realtime_database_failure_reports_no_success(
    postgresql_db,
) -> None:
    postgresql_db.execute(SCHEMAS["RT_WF"])
    postgresql_db.execute(SCHEMAS["RT_RA"])
    postgresql_db.execute(
        "CREATE FUNCTION reject_second_rt_wf() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN IF NEW.monthday = 817 THEN RAISE EXCEPTION 'simulated RT_WF failure'; "
        "END IF; RETURN NEW; END $$"
    )
    postgresql_db.execute(
        "CREATE TRIGGER reject_second_rt_wf BEFORE INSERT OR UPDATE ON RT_WF "
        "FOR EACH ROW EXECUTE FUNCTION reject_second_rt_wf()"
    )
    postgresql_db.execute(
        "CREATE FUNCTION reject_second_rt_ra() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN IF NEW.monthday = 817 THEN RAISE EXCEPTION 'simulated RT_RA failure'; "
        "END IF; RETURN NEW; END $$"
    )
    postgresql_db.execute(
        "CREATE TRIGGER reject_second_rt_ra BEFORE INSERT OR UPDATE ON RT_RA "
        "FOR EACH ROW EXECUTE FUNCTION reject_second_rt_ra()"
    )
    postgresql_db.commit()
    updater = RealtimeUpdater(postgresql_db)

    same_key = updater.process_parsed_records_batch(
        [
            parsed_record(data_kubun="1"),
            parsed_record(data_kubun="2"),
            parsed_record(data_kubun="3"),
        ]
    )
    assert same_key["success"] is True
    assert same_key["inserted"] == 3
    assert same_key["errors"] == 0
    assert postgresql_db.fetch_one("SELECT DataKubun AS status FROM RT_WF") == {"status": "3"}
    assert updater.process_parsed_record(parsed_record(data_kubun="0"))["success"] is True
    postgresql_db.commit()

    postgresql_db.begin_transaction()
    caller_owned = updater.process_parsed_records_batch(
        [
            parsed_record(data_kubun="1", month_day="0818"),
            parsed_record(data_kubun="2", month_day="0818"),
            parsed_record(data_kubun="3", month_day="0818"),
        ]
    )
    assert caller_owned["success"] is True
    assert caller_owned["inserted"] == 3
    assert postgresql_db.is_transaction_active() is True
    assert postgresql_db.fetch_one(
        "SELECT DataKubun AS status FROM RT_WF WHERE MonthDay = 818"
    ) == {"status": "3"}
    postgresql_db.rollback()
    assert _count(postgresql_db, "RT_WF") == 0

    ra_update = realtime_ra_record()
    ra_update["DataKubun"] = "2"
    mixed_same_key = updater.process_parsed_records_batch(
        [parsed_record(data_kubun="1"), realtime_ra_record(), ra_update]
    )
    assert mixed_same_key["success"] is True
    assert mixed_same_key["inserted"] == 3
    assert postgresql_db.fetch_one("SELECT DataKubun AS status FROM RT_WF") == {"status": "1"}
    assert postgresql_db.fetch_one("SELECT DataKubun AS status FROM RT_RA") == {"status": "2"}
    postgresql_db.execute("DELETE FROM RT_RA")
    assert updater.process_parsed_record(parsed_record(data_kubun="0"))["success"] is True
    postgresql_db.commit()

    result = updater.process_parsed_records_batch(
        [parsed_record(), parsed_record(month_day="0817")]
    )
    assert result["success"] is False
    assert result["inserted"] == 0
    assert result["errors"] == 2
    assert _count(postgresql_db, "RT_WF") == 0

    postgresql_db.execute(
        "CREATE FUNCTION reject_rt_ra_delete() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN RAISE EXCEPTION 'simulated RT_RA delete failure'; END $$"
    )
    postgresql_db.execute(
        "CREATE TRIGGER reject_rt_ra_delete BEFORE DELETE ON RT_RA "
        "FOR EACH ROW EXECUTE FUNCTION reject_rt_ra_delete()"
    )
    postgresql_db.commit()

    for records in (
        [realtime_ra_record(), parsed_record(month_day="0817")],
        [parsed_record(), realtime_ra_record(month_day="0817")],
        [
            realtime_ra_record(),
            {**realtime_ra_record(), "DataKubun": "0"},
        ],
        [
            parsed_record(),
            parsed_record(month_day="0817"),
            parsed_record(data_kubun="0"),
        ],
    ):
        result = updater.process_parsed_records_batch(records)
        assert result["success"] is False
        assert result["inserted"] == 0
        assert result["errors"] == len(records)
        assert result["transaction_rolled_back"] is True
        assert _count(postgresql_db, "RT_WF") == 0
        assert _count(postgresql_db, "RT_RA") == 0

    non_strict = updater.process_parsed_records_batch(
        [realtime_ra_record(), realtime_ra_record(month_day="0817")]
    )
    assert non_strict["success"] is False
    assert non_strict["inserted"] == 0
    assert non_strict["errors"] == 2
    assert non_strict["transaction_rolled_back"] is True
    assert _count(postgresql_db, "RT_RA") == 0
    # psycopg starts a caller-owned transaction for the verification SELECT;
    # close it before the next independent updater-owned call.
    postgresql_db.commit()

    first = updater.process_parsed_records_batch([realtime_ra_record()])
    assert first["success"] is True
    assert first["inserted"] == 1
    second = updater.process_parsed_records_batch([parsed_record(month_day="0817")])
    assert second["success"] is False
    assert second["inserted"] == 0
    assert second["errors"] == 1
    assert _count(postgresql_db, "RT_RA") == 1
    assert _count(postgresql_db, "RT_WF") == 0
    postgresql_db.commit()
