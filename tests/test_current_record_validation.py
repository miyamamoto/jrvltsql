"""Fail-closed gates for current JV-Data fixed-length records."""

import json
from pathlib import Path

import pytest

from src.parser import status_domain
from src.parser.base import validate_fixed_record
from src.parser.factory import ParserFactory
from src.parser.status_domain import (
    CURRENT_ACCUMULATED_DATA_KUBUN,
    CURRENT_REALTIME_DATA_KUBUN,
    DataKubunContext,
    validate_data_kubun,
)

OFFICIAL_LAYOUT_ROOT = Path(__file__).parent / "fixtures" / "official_layout"
CURRENT_LAYOUT = json.loads(
    (OFFICIAL_LAYOUT_ROOT / "jvdata_sdk500_manifest.json").read_text(encoding="utf-8")
)
STATUS_DOMAIN = json.loads(
    (OFFICIAL_LAYOUT_ROOT / "jvdata_status_domain.json").read_text(encoding="utf-8")
)
LAYOUT_HISTORY = json.loads(
    (OFFICIAL_LAYOUT_ROOT / "jvdata_layout_history.json").read_text(encoding="utf-8")
)
CURRENT_LENGTHS = {
    record_type: (contract["length"],)
    for record_type, contract in CURRENT_LAYOUT["root_records"].items()
}
PREVIOUS_OFFICIAL_LENGTHS = tuple(
    (change["record_type"], change["before_length"])
    for change in LAYOUT_HISTORY["physical_length_changes"]
)

# These parsers also require populated domain-specific arrays or master fields.
# Their valid payloads are covered by dedicated official-contract tests; this
# module limits their positive case to the shared physical-record envelope.
# JG, WC, and WF additionally require their official fixed-width keys, race
# composites, and current status/code domains, so a generic space-filled
# envelope is not valid.
DOMAIN_PAYLOAD_REQUIRED = {"CK", "DM", "JG", "KS", "TK", "TM", "WC", "WF", "WH"}


def test_declared_current_lengths_match_every_factory_parser():
    """The independent official-length matrix cannot drift from dispatch."""

    factory = ParserFactory()
    assert set(CURRENT_LENGTHS) == set(factory.supported_types())

    for record_type, expected_lengths in CURRENT_LENGTHS.items():
        parser = factory.get_parser(record_type)
        parser_lengths = (parser.RECORD_LENGTH,)
        assert parser_lengths == expected_lengths, record_type


def _record(record_type: str, length: int) -> bytes:
    record = bytearray(b" " * length)
    record[0:2] = record_type.encode("ascii")
    # H1/H6 do not define status 1. Their generic framing control uses the
    # official update-interim state 2; domain payload tests live elsewhere.
    record[2:3] = b"2" if record_type in {"H1", "H6"} else b"1"
    record[3:11] = b"20260816"
    if length >= 27:
        record[11:15] = b"2026"
        record[15:19] = b"0816"
        record[19:21] = b"05"
        record[21:23] = b"01"
        record[23:25] = b"01"
        record[25:27] = b"01"
    if record_type == "WH":
        record[27:35] = b"08161234"
    record[-2:] = b"\r\n"
    return bytes(record)


def _is_rejected(parser, record: bytes) -> bool:
    try:
        return parser.parse(record) is None
    except (UnicodeDecodeError, ValueError):
        return True


def _record_with_header(
    record_type: str,
    *,
    data_kubun: str,
    make_date: str = "20260816",
) -> bytes:
    length = CURRENT_LENGTHS[record_type][0]
    record = bytearray(_record(record_type, length))
    record[2:3] = data_kubun.encode("ascii")
    record[3:11] = make_date.encode("ascii")
    return bytes(record)


def test_official_status_oracle_covers_all_38_records_and_154_current_pairs():
    """The reviewed workbook oracle is complete, not a selected sentinel list."""

    current = STATUS_DOMAIN["current_accumulated"]
    assert set(current) == set(CURRENT_LENGTHS)
    assert sum(len(contract["values"]) for contract in current.values()) == 154
    assert set(STATUS_DOMAIN["realtime_overrides"]) == {"DM", "TM", "WF"}
    assert set(STATUS_DOMAIN["historical_exceptions"]) == {
        "AV",
        "JC",
        "RC",
        "WE",
        "WH",
    }
    assert STATUS_DOMAIN["unresolved_history"]["DM"]["reintroduced_at"] is None
    assert STATUS_DOMAIN["unresolved_history"]["RA"]["before_allowed"] is None

    expected_accumulated = {
        record_type: frozenset(contract["values"]) for record_type, contract in current.items()
    }
    expected_realtime = dict(expected_accumulated)
    expected_realtime.update(
        {
            record_type: frozenset(contract["values"])
            for record_type, contract in STATUS_DOMAIN["realtime_overrides"].items()
        }
    )
    assert CURRENT_ACCUMULATED_DATA_KUBUN == expected_accumulated
    assert CURRENT_REALTIME_DATA_KUBUN == expected_realtime


def test_physical_header_accepts_every_official_current_status():
    """Every workbook-listed positive remains accepted by the shared envelope."""

    for record_type, contract in STATUS_DOMAIN["current_accumulated"].items():
        for data_kubun in contract["values"]:
            validate_fixed_record(
                _record_with_header(record_type, data_kubun=data_kubun),
                record_type,
                CURRENT_LENGTHS[record_type],
            )


def test_physical_header_rejects_blank_and_unknown_status_for_all_38_records():
    """A structurally valid buffer is not valid when byte 3 has no official state."""

    for record_type in CURRENT_LENGTHS:
        for data_kubun in (" ", "Z"):
            with pytest.raises(ValueError, match="DataKubun"):
                validate_fixed_record(
                    _record_with_header(record_type, data_kubun=data_kubun),
                    record_type,
                    CURRENT_LENGTHS[record_type],
                )


def test_direct_factory_parsers_reject_unknown_status_through_the_shared_gate():
    """Domain-specific payload rejection must not be mistaken for status coverage."""

    factory = ParserFactory()
    for record_type in CURRENT_LENGTHS:
        record = _record_with_header(record_type, data_kubun="Z")
        assert _is_rejected(factory.get_parser(record_type), record), record_type


def test_all_factory_parsers_reach_the_central_status_gate(monkeypatch):
    """A parser's separate body checks cannot provide a false-green signal."""

    observed: list[str] = []
    original = status_domain.validate_data_kubun

    def observe(record_type, data_kubun, **kwargs):
        observed.append(record_type)
        return original(record_type, data_kubun, **kwargs)

    monkeypatch.setattr(status_domain, "validate_data_kubun", observe)
    factory = ParserFactory()
    for record_type, lengths in CURRENT_LENGTHS.items():
        try:
            factory.get_parser(record_type).parse(_record(record_type, lengths[0]))
        except (UnicodeDecodeError, ValueError):
            pass

    assert observed == list(CURRENT_LENGTHS)


def test_realtime_overrides_reject_only_accumulated_status_seven():
    """DM/TM/WF have one explicit channel difference and paired RT controls."""

    realtime_controls = {"DM": "1", "TM": "3", "WF": "9"}
    for record_type, realtime_value in realtime_controls.items():
        assert validate_data_kubun(record_type, "7") == "7"
        with pytest.raises(ValueError, match="DataKubun"):
            validate_data_kubun(
                record_type,
                "7",
                context=DataKubunContext.REALTIME,
            )
        assert (
            validate_data_kubun(
                record_type,
                realtime_value,
                context=DataKubunContext.REALTIME,
            )
            == realtime_value
        )


@pytest.mark.parametrize(
    ("record_type", "legacy_value", "valid_before"),
    [
        (record_type, contract["value"], contract["valid_before_make_date"])
        for record_type, contract in STATUS_DOMAIN["historical_exceptions"].items()
    ],
)
def test_historical_status_requires_make_date_before_its_official_boundary(
    record_type,
    legacy_value,
    valid_before,
):
    """Old and current generations share a length, so MakeDate is provenance."""

    before = str(int(valid_before) - 1)
    validate_fixed_record(
        _record_with_header(
            record_type,
            data_kubun=legacy_value,
            make_date=before,
        ),
        record_type,
        CURRENT_LENGTHS[record_type],
    )
    with pytest.raises(ValueError, match="DataKubun"):
        validate_fixed_record(
            _record_with_header(
                record_type,
                data_kubun=legacy_value,
                make_date=valid_before,
            ),
            record_type,
            CURRENT_LENGTHS[record_type],
        )


@pytest.mark.parametrize(
    ("record_type", "legacy_value"),
    [
        (record_type, contract["value"])
        for record_type, contract in STATUS_DOMAIN["historical_exceptions"].items()
    ],
)
def test_historical_only_status_rejects_missing_or_invalid_provenance(
    record_type,
    legacy_value,
):
    """Unknown provenance means current-only, never a permissive history union."""

    for make_date in (None, "", "not-a-date"):
        with pytest.raises(ValueError, match="DataKubun"):
            validate_data_kubun(
                record_type,
                legacy_value,
                make_date=make_date,
            )


def test_um_status_nine_is_rejected_before_its_documented_generation():
    """UM status 9 was added on 2003-04-22, not part of every old UM record."""

    validate_fixed_record(
        _record_with_header("UM", data_kubun="9", make_date="20030422"),
        "UM",
        CURRENT_LENGTHS["UM"],
    )
    with pytest.raises(ValueError, match="DataKubun"):
        validate_fixed_record(
            _record_with_header("UM", data_kubun="9", make_date="20030421"),
            "UM",
            CURRENT_LENGTHS["UM"],
        )


@pytest.mark.parametrize("record_type", CURRENT_LENGTHS)
def test_current_record_shape_accepts_only_declared_physical_lengths(record_type):
    """Short, long, and between-layout buffers must not be parsed as valid."""

    parser = ParserFactory().get_parser(record_type)
    accepted_lengths = CURRENT_LENGTHS[record_type]

    for length in accepted_lengths:
        record = _record(record_type, length)
        validate_fixed_record(record, record_type, accepted_lengths)
        if record_type not in DOMAIN_PAYLOAD_REQUIRED:
            assert parser.parse(record) is not None

    rejected_lengths = {
        candidate
        for length in accepted_lengths
        for candidate in (length - 1, length + 1)
        if candidate not in accepted_lengths
    }
    for length in rejected_lengths:
        assert _is_rejected(parser, _record(record_type, length)), (
            record_type,
            length,
        )


@pytest.mark.parametrize("record_type", CURRENT_LENGTHS)
def test_current_record_shape_rejects_wrong_type_delimiter_and_encoding(record_type):
    """A correctly sized but corrupt record is unknown, never a green parse."""

    parser = ParserFactory().get_parser(record_type)
    for length in CURRENT_LENGTHS[record_type]:
        valid = _record(record_type, length)
        wrong_type = b"ZZ" + valid[2:]
        wrong_delimiter = valid[:-2] + b"XX"
        invalid_cp932 = bytearray(valid)
        invalid_cp932[10] = 0x81

        assert _is_rejected(parser, wrong_type), (record_type, length, "type")
        assert _is_rejected(parser, wrong_delimiter), (
            record_type,
            length,
            "delimiter",
        )
        assert _is_rejected(parser, bytes(invalid_cp932)), (
            record_type,
            length,
            "encoding",
        )


@pytest.mark.parametrize(
    ("record_type", "repository_only_length"),
    (("H1", 317), ("H6", 78)),
)
def test_provider_parser_rejects_repository_only_flattened_vote_records(
    record_type,
    repository_only_length,
):
    """Synthetic repository layouts are not provider JV-Data records."""

    parser = ParserFactory().get_parser(record_type)
    assert _is_rejected(parser, _record(record_type, repository_only_length))


@pytest.mark.parametrize(
    ("record_type", "previous_official_length"),
    PREVIOUS_OFFICIAL_LENGTHS,
)
def test_provider_parser_rejects_every_ledgered_previous_physical_length(
    record_type,
    previous_official_length,
):
    """Current N-layout dispatch must not accept a previous physical length."""

    parser = ParserFactory().get_parser(record_type)
    assert _is_rejected(parser, _record(record_type, previous_official_length))


@pytest.mark.parametrize(
    ("record_type", "length"),
    (
        ("AV", 78),
        ("BT", 6889),
        ("H1", 28955),
        ("H6", 102890),
        ("HN", 251),
        ("HR", 719),
        ("HS", 200),
        ("HY", 123),
        ("JG", 80),
        ("O1", 962),
        ("O2", 2042),
        ("O3", 2654),
        ("O4", 4031),
        ("O5", 12293),
        ("O6", 83285),
        ("SE", 555),
        ("SK", 208),
        ("UM", 1609),
        ("WF", 7215),
    ),
)
def test_current_record_shape_rejects_cp932_pair_crossing_field_boundary(
    record_type,
    length,
):
    """A multibyte code point may not span two fixed-width fields."""

    parser = ParserFactory().get_parser(record_type)
    record = bytearray(_record(record_type, length))
    # MakeDate ends at byte 11 and the next physical field begins there.
    # Together these bytes are valid CP932, but neither field slice is valid.
    record[10:12] = b"\x82\xa0"

    assert bytes(record).decode("cp932", errors="strict")
    assert _is_rejected(parser, bytes(record))
