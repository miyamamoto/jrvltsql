"""Independent contracts for the compact official JV-Data layout oracle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.official_jvdata_oracle import (
    extract_manifest_from_source,
    load_manifest,
    validate_manifest,
)
from src.parser.factory import ALL_RECORD_TYPES, ParserFactory

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "official_layout"
MANIFEST_PATH = FIXTURE_ROOT / "jvdata_sdk500_manifest.json"
HISTORY_PATH = FIXTURE_ROOT / "jvdata_layout_history.json"
OFFICIAL_SOURCE_SHA256 = "8994f985fce846f1b4fcbc3ddf2a5c6394c586a458478346891222b3b61e4ee3"


def _valid_manifest() -> dict:
    return {
        "manifest_schema_version": 1,
        "source": {
            "artifact": "synthetic oracle unit fixture",
            "jvdata_version": "test",
            "sha256": "a" * 64,
        },
        "structures": {
            "Child": {
                "width": 2,
                "expanded_leaf_count": 1,
                "fields": [
                    {
                        "name": "value",
                        "kind": "scalar",
                        "start": 1,
                        "width": 2,
                        "decoder": "text",
                    }
                ],
            },
            "JV_ZZ_ROOT": {
                "width": 6,
                "expanded_leaf_count": 3,
                "fields": [
                    {
                        "name": "head",
                        "kind": "nested",
                        "start": 1,
                        "width": 2,
                        "struct": "Child",
                    },
                    {
                        "name": "values",
                        "kind": "repeat",
                        "start": 3,
                        "width": 2,
                        "stride": 2,
                        "count": 2,
                        "element_kind": "scalar",
                        "decoder": "text",
                    },
                ],
            },
        },
        "root_records": {"ZZ": {"struct": "JV_ZZ_ROOT", "length": 6}},
        "summary": {
            "structure_count": 2,
            "repeat_template_count": 1,
            "root_record_count": 1,
            "expanded_leaf_count": 3,
        },
    }


def _set(path, value):
    def mutate(manifest):
        node = manifest
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value

    return mutate


def _make_child_self_referential(manifest):
    manifest["structures"]["Child"]["fields"][0] = {
        "name": "value",
        "kind": "nested",
        "start": 1,
        "width": 2,
        "struct": "Child",
    }


@pytest.mark.parametrize(
    ("mutate", "expected_error"),
    [
        (_set(("structures", "JV_ZZ_ROOT", "fields", 1, "start"), 4), "JV_ZZ_ROOT:gap:3"),
        (
            _set(("structures", "JV_ZZ_ROOT", "fields", 1, "start"), 2),
            "JV_ZZ_ROOT:overlap:2",
        ),
        (
            _set(("structures", "JV_ZZ_ROOT", "fields", 1, "count"), 0),
            "JV_ZZ_ROOT.values:invalid-repeat-count",
        ),
        (
            _set(("structures", "JV_ZZ_ROOT", "fields", 0, "struct"), "Missing"),
            "JV_ZZ_ROOT.head:unknown-struct:Missing",
        ),
        (
            _set(("structures", "JV_ZZ_ROOT", "fields", 0, "width"), 1),
            "JV_ZZ_ROOT.head:nested-width-mismatch:1!=2",
        ),
        (
            _set(("summary", "expanded_leaf_count"), 2),
            "summary:expanded-leaf-count:2!=3",
        ),
        (
            _set(("source", "sha256"), "not-a-sha256"),
            "source:invalid-sha256",
        ),
        (
            _set(("source", "artifact"), ""),
            "source:artifact-missing",
        ),
        (
            _set(("source", "jvdata_version"), ""),
            "source:jvdata-version-missing",
        ),
        (
            _set(("structures", "Child", "expanded_leaf_count"), True),
            "Child:expanded-leaf-count:True!=1",
        ),
        (
            _make_child_self_referential,
            "Child.value:cyclic-struct:Child",
        ),
    ],
)
def test_oracle_validator_rejects_every_fail_open_shape(mutate, expected_error):
    manifest = _valid_manifest()
    mutate(manifest)

    assert expected_error in validate_manifest(manifest)


def test_oracle_validator_accepts_paired_complete_control():
    assert validate_manifest(_valid_manifest()) == []


def test_extractor_understands_scalar_nested_and_repeat_templates():
    source = """
from dataclasses import dataclass

@dataclass
class Child:
    value: str
    @classmethod
    def SetDataB(cls, b):
        return cls(MidB2S(b, 1, 2))

@dataclass
class JV_ZZ_ROOT:
    head: Child
    values: list[str]
    @classmethod
    def SetDataB(cls, b):
        return cls(
            Child.SetDataB(MidB2B(b, 1, 2)),
            [MidB2S(b, 3 + 2 * i, 2) for i in range(2)],
        )
"""

    manifest = extract_manifest_from_source(
        source,
        artifact="synthetic oracle unit fixture",
        jvdata_version="test",
    )

    assert validate_manifest(manifest) == []
    assert manifest["root_records"] == {"ZZ": {"struct": "JV_ZZ_ROOT", "length": 6}}
    assert manifest["summary"] == _valid_manifest()["summary"]
    assert manifest["structures"]["JV_ZZ_ROOT"]["fields"][1] == {
        "name": "values",
        "kind": "repeat",
        "start": 3,
        "width": 2,
        "stride": 2,
        "count": 2,
        "element_kind": "scalar",
        "decoder": "text",
    }


def test_tracked_official_manifest_is_complete_and_matches_dispatch():
    manifest = load_manifest(MANIFEST_PATH)

    assert validate_manifest(manifest) == []
    assert manifest["source"]["sha256"] == OFFICIAL_SOURCE_SHA256
    assert manifest["source"]["jvdata_version"] == "4.9.0.1"
    assert manifest["summary"] == {
        "structure_count": 94,
        "repeat_template_count": 93,
        "root_record_count": 38,
        "expanded_leaf_count": 46985,
    }
    assert set(manifest["root_records"]) == set(ALL_RECORD_TYPES)

    factory = ParserFactory()
    for record_type, contract in manifest["root_records"].items():
        assert factory.get_parser(record_type).RECORD_LENGTH == contract["length"]


def test_official_hy_and_ck_sentinels_cannot_follow_current_implementation_drift():
    manifest = load_manifest(MANIFEST_PATH)
    structures = manifest["structures"]

    hy_fields = {
        field["name"]: (field["start"], field["width"])
        for field in structures["JV_HY_BAMEIORIGIN"]["fields"]
    }
    assert hy_fields["KettoNum"] == (12, 10)
    assert hy_fields["Bamei"] == (22, 36)
    assert hy_fields["Origin"] == (58, 64)

    ck = manifest["root_records"]["CK"]
    assert ck == {"struct": "JV_CK_CHAKU", "length": 6870}
    assert structures["JV_CK_CHAKU"]["expanded_leaf_count"] == 1729
    ck_uma_repeats = {
        field["name"]: field["count"]
        for field in structures["JV_CK_UMA"]["fields"]
        if field["kind"] == "repeat"
    }
    assert ck_uma_repeats == {
        "ChakuKaisuBa": 7,
        "ChakuKaisuJyotai": 12,
        "ChakuKaisuSibaKyori": 9,
        "ChakuKaisuDirtKyori": 9,
        "ChakuKaisuJyoSiba": 10,
        "ChakuKaisuJyoDirt": 10,
        "ChakuKaisuJyoSyogai": 10,
        "Kyakusitu": 4,
    }


def test_official_layout_history_is_provenanced_and_continuous_to_current():
    history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    current = load_manifest(MANIFEST_PATH)

    assert history["ledger_schema_version"] == 1
    assert {(source["jvdata_version"], source["sha256"]) for source in history["sources"]} == {
        (
            "4.8.0.2",
            "6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7",
        ),
        (
            "4.9.0.1",
            "23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234",
        ),
    }

    expected_changes = {
        ("SE", 547, 555),
        ("BR", 467, 537),
        ("BN", 413, 477),
        ("UM", 1577, 1609),
        ("BR", 537, 545),
        ("HN", 245, 251),
        ("SK", 178, 208),
        ("CK", 6864, 6870),
        ("HS", 196, 200),
        ("BT", 6887, 6889),
    }
    changes = history["physical_length_changes"]
    assert {
        (change["record_type"], change["before_length"], change["after_length"])
        for change in changes
    } == expected_changes

    by_record = {}
    for change in sorted(changes, key=lambda item: item["effective_date"]):
        record_type = change["record_type"]
        previous = by_record.get(record_type)
        if previous is not None:
            assert change["before_length"] == previous
        by_record[record_type] = change["after_length"]
    for record_type, latest_length in by_record.items():
        assert current["root_records"][record_type]["length"] == latest_length

    assert history["record_type_changes"] == [
        {
            "effective_date": "2003-04-22",
            "before_record_type": "PR",
            "after_record_type": "BR",
            "official_spec_version": "1.0.1-beta",
        }
    ]

    semantic_change = history["same_length_semantic_changes"][0]
    assert semantic_change["record_type"] == "UM"
    assert semantic_change["length_unchanged"] is True
    assert semantic_change["provenance_required"] is True
    um_fields = {
        field["name"]: (field["start"], field["width"])
        for field in current["structures"]["JV_UM_UMA"]["fields"]
    }
    assert um_fields["BameiEng"] == (119, 60)
    assert um_fields["ZaikyuFlag"] == (179, 1)
    assert um_fields["Reserved"] == (180, 19)
