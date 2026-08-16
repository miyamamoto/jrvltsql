"""Fail-closed gates for current JV-Data fixed-length records."""

import pytest

from src.parser.base import validate_fixed_record
from src.parser.factory import ParserFactory


CURRENT_LENGTHS = {
    "AV": (78,),
    "BN": (477,),
    "BR": (545,),
    "BT": (6889,),
    "CC": (50,),
    "CH": (3862,),
    "CK": (6870,),
    "CS": (6829,),
    "DM": (303,),
    "HR": (719,),
    "H1": (317, 28955),
    "H6": (78, 102890),
    "HC": (60,),
    "HN": (251,),
    "HS": (200,),
    "HY": (123,),
    "JC": (161,),
    "JG": (80,),
    "KS": (4173,),
    "O1": (962,),
    "O2": (2042,),
    "O3": (2654,),
    "O4": (4031,),
    "O5": (12293,),
    "O6": (83285,),
    "RA": (1272,),
    "RC": (501,),
    "SE": (555,),
    "SK": (208,),
    "TC": (45,),
    "TK": (21657,),
    "TM": (141,),
    "UM": (1609,),
    "WC": (105,),
    "WE": (42,),
    "WF": (7215,),
    "WH": (847,),
    "YS": (382,),
}

# These parsers also require populated domain-specific arrays or master fields.
# Their valid payloads are covered by dedicated official-contract tests; this
# module limits their positive case to the shared physical-record envelope.
DOMAIN_PAYLOAD_REQUIRED = {"DM", "KS", "TK", "TM", "WH"}


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
