"""Fail-closed gates for current JV-Data fixed-length records."""

import json
from pathlib import Path

import pytest

from src.parser.base import validate_fixed_record
from src.parser.factory import ParserFactory

OFFICIAL_LAYOUT_ROOT = Path(__file__).parent / "fixtures" / "official_layout"
CURRENT_LAYOUT = json.loads(
    (OFFICIAL_LAYOUT_ROOT / "jvdata_sdk500_manifest.json").read_text(encoding="utf-8")
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
    record[2:3] = b"1"
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
