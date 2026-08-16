"""Independent contracts for the compact official JV-Data layout oracle."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.official_jvdata_oracle import (
    OracleExtractionError,
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
            "YMD": {
                "width": 8,
                "expanded_leaf_count": 3,
                "fields": [
                    {
                        "name": "Year",
                        "kind": "scalar",
                        "start": 1,
                        "width": 4,
                        "decoder": "text",
                    },
                    {
                        "name": "Month",
                        "kind": "scalar",
                        "start": 5,
                        "width": 2,
                        "decoder": "text",
                    },
                    {
                        "name": "Day",
                        "kind": "scalar",
                        "start": 7,
                        "width": 2,
                        "decoder": "text",
                    },
                ],
            },
            "RECORD_ID": {
                "width": 11,
                "expanded_leaf_count": 5,
                "fields": [
                    {
                        "name": "RecordSpec",
                        "kind": "scalar",
                        "start": 1,
                        "width": 2,
                        "decoder": "text",
                    },
                    {
                        "name": "DataKubun",
                        "kind": "scalar",
                        "start": 3,
                        "width": 1,
                        "decoder": "text",
                    },
                    {
                        "name": "MakeDate",
                        "kind": "nested",
                        "start": 4,
                        "width": 8,
                        "struct": "YMD",
                    },
                ],
            },
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
                "width": 15,
                "expanded_leaf_count": 7,
                "fields": [
                    {
                        "name": "head",
                        "kind": "nested",
                        "start": 1,
                        "width": 11,
                        "struct": "RECORD_ID",
                    },
                    {
                        "name": "values",
                        "kind": "repeat",
                        "start": 12,
                        "width": 2,
                        "stride": 2,
                        "count": 2,
                        "element_kind": "scalar",
                        "decoder": "text",
                    },
                ],
            },
        },
        "root_records": {"ZZ": {"struct": "JV_ZZ_ROOT", "length": 15}},
        "summary": {
            "structure_count": 4,
            "repeat_template_count": 1,
            "root_record_count": 1,
            "expanded_leaf_count": 7,
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


def _point_root_at_non_root_child(manifest):
    manifest["root_records"]["ZZ"] = {"struct": "Child", "length": 2}
    manifest["summary"]["expanded_leaf_count"] = 1


def _point_root_at_prefixed_scalar_head(manifest):
    fake_root = deepcopy(manifest["structures"]["Child"])
    fake_root["fields"][0]["name"] = "head"
    manifest["structures"]["JV_ZZ_CHILD"] = fake_root
    manifest["root_records"]["ZZ"] = {"struct": "JV_ZZ_CHILD", "length": 2}
    manifest["summary"]["structure_count"] = 5
    manifest["summary"]["expanded_leaf_count"] = 1


def _remove_child_decoder(manifest):
    manifest["structures"]["Child"]["fields"][0].pop("decoder")


def _remove_repeat_decoder(manifest):
    manifest["structures"]["JV_ZZ_ROOT"]["fields"][1].pop("decoder")


def _make_repeat_nested_without_target(manifest):
    field = manifest["structures"]["JV_ZZ_ROOT"]["fields"][1]
    field.pop("decoder")
    field["element_kind"] = "nested"
    manifest["structures"]["JV_ZZ_ROOT"]["expanded_leaf_count"] = 5
    manifest["summary"]["expanded_leaf_count"] = 5


def _corrupt_record_header_semantics(manifest):
    manifest["structures"]["RECORD_ID"]["fields"][1]["name"] = "WrongKubun"


def _empty_oracle(manifest):
    manifest["structures"] = {}
    manifest["root_records"] = {}
    manifest["summary"] = {
        "structure_count": 0,
        "repeat_template_count": 0,
        "root_record_count": 0,
        "expanded_leaf_count": 0,
    }


@pytest.mark.parametrize(
    ("mutate", "expected_error"),
    [
        (
            _set(("structures", "JV_ZZ_ROOT", "fields", 1, "start"), 15),
            "JV_ZZ_ROOT:gap:12-14",
        ),
        (
            _set(("structures", "JV_ZZ_ROOT", "fields", 1, "start"), 11),
            "JV_ZZ_ROOT:overlap:11",
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
            "JV_ZZ_ROOT.head:nested-width-mismatch:1!=11",
        ),
        (
            _set(("summary", "expanded_leaf_count"), 2),
            "summary:expanded-leaf-count:2!=7",
        ),
        (
            _set(("source", "sha256"), "not-a-sha256"),
            "source:invalid-sha256",
        ),
        (
            _set(("source", "sha256"), int("1" * 64)),
            "source:invalid-sha256",
        ),
        (
            _set(("manifest_schema_version",), True),
            "manifest:unsupported-schema-version",
        ),
        (
            _set(("source", "artifact"), ""),
            "source:artifact-missing",
        ),
        (
            _set(("source", "artifact"), 123),
            "source:artifact-missing",
        ),
        (
            _set(("source", "jvdata_version"), ""),
            "source:jvdata-version-missing",
        ),
        (
            _set(("source", "jvdata_version"), 4901),
            "source:jvdata-version-missing",
        ),
        (
            _set(("structures", "Child", "expanded_leaf_count"), True),
            "Child:expanded-leaf-count:True!=1",
        ),
        (
            _set(("structures", "Child", "fields", 0, "name"), None),
            "Child:invalid-or-duplicate-field:None",
        ),
        (
            _set(("structures", "JV_ZZ_ROOT", "fields", 0, "struct"), None),
            "JV_ZZ_ROOT.head:struct-missing",
        ),
        (
            _remove_child_decoder,
            "Child.value:invalid-decoder",
        ),
        (
            _remove_repeat_decoder,
            "JV_ZZ_ROOT.values:invalid-decoder",
        ),
        (
            _make_repeat_nested_without_target,
            "JV_ZZ_ROOT.values:struct-missing",
        ),
        (
            _set(("structures", "JV_ZZ_ROOT", "fields", 0, "name"), "not_head"),
            "root:ZZ:head-missing:JV_ZZ_ROOT",
        ),
        (
            _point_root_at_non_root_child,
            "root:ZZ:structure-name-mismatch:Child",
        ),
        (
            _point_root_at_prefixed_scalar_head,
            "root:ZZ:invalid-head-contract:JV_ZZ_CHILD",
        ),
        (
            _corrupt_record_header_semantics,
            "record-header:invalid-record-id",
        ),
        (
            _empty_oracle,
            "structures:empty",
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
class YMD:
    Year: str
    Month: str
    Day: str
    @classmethod
    def SetDataB(cls, b):
        return cls(
            MidB2S(b, 1, 4),
            MidB2S(b, 5, 2),
            MidB2S(b, 7, 2),
        )

@dataclass
class RECORD_ID:
    RecordSpec: str
    DataKubun: str
    MakeDate: YMD
    @classmethod
    def SetDataB(cls, b):
        return cls(
            MidB2S(b, 1, 2),
            MidB2S(b, 3, 1),
            YMD.SetDataB(MidB2B(b, 4, 8)),
        )

@dataclass
class Child:
    value: str
    @classmethod
    def SetDataB(cls, b):
        return cls(MidB2S(b, 1, 2))

@dataclass
class JV_ZZ_ROOT:
    head: RECORD_ID
    values: list[str]
    @classmethod
    def SetDataB(cls, b):
        return cls(
            RECORD_ID.SetDataB(MidB2B(b, 1, 11)),
            [MidB2S(b, 12 + 2 * i, 2) for i in range(2)],
        )
"""

    manifest = extract_manifest_from_source(
        source,
        artifact="synthetic oracle unit fixture",
        jvdata_version="test",
    )

    assert validate_manifest(manifest) == []
    assert manifest["root_records"] == {"ZZ": {"struct": "JV_ZZ_ROOT", "length": 15}}
    assert manifest["summary"] == _valid_manifest()["summary"]
    assert manifest["structures"]["JV_ZZ_ROOT"]["fields"][1] == {
        "name": "values",
        "kind": "repeat",
        "start": 12,
        "width": 2,
        "stride": 2,
        "count": 2,
        "element_kind": "scalar",
        "decoder": "text",
    }


@pytest.mark.parametrize(
    ("start_expression", "width_expression", "error"),
    (
        ("12 + i * i", "1", "non-affine repeat offset"),
        ("12 + 2 * i", "2 + i", "repeat width depends on loop variable"),
    ),
)
def test_extractor_rejects_non_affine_repeat_layouts(
    start_expression,
    width_expression,
    error,
):
    source = f"""
from dataclasses import dataclass

@dataclass
class RECORD_ID:
    value: bytes
    @classmethod
    def SetDataB(cls, b):
        return cls(MidB2B(b, 1, 11))

@dataclass
class JV_ZZ_ROOT:
    head: RECORD_ID
    values: list[str]
    @classmethod
    def SetDataB(cls, b):
        return cls(
            RECORD_ID.SetDataB(MidB2B(b, 1, 11)),
            [MidB2S(b, {start_expression}, {width_expression}) for i in range(3)],
        )
"""

    with pytest.raises(OracleExtractionError, match=error):
        extract_manifest_from_source(
            source,
            artifact="synthetic oracle unit fixture",
            jvdata_version="test",
        )


def test_extractor_rejects_constructor_keyword_arguments():
    source = """
from dataclasses import dataclass

@dataclass
class RECORD_ID:
    value: bytes
    @classmethod
    def SetDataB(cls, b):
        return cls(MidB2B(b, 1, 11))

@dataclass
class JV_ZZ_ROOT:
    head: RECORD_ID
    @classmethod
    def SetDataB(cls, b):
        return cls(
            RECORD_ID.SetDataB(MidB2B(b, 1, 11)),
            extra=MidB2S(b, 12, 1),
        )
"""

    with pytest.raises(
        OracleExtractionError,
        match="keyword arguments are outside the reviewed grammar",
    ):
        extract_manifest_from_source(
            source,
            artifact="synthetic oracle unit fixture",
            jvdata_version="test",
        )


def test_extractor_rejects_slice_keyword_arguments():
    source = """
from dataclasses import dataclass

@dataclass
class Scalar:
    value: str
    @classmethod
    def SetDataB(cls, b):
        return cls(MidB2S(b, 1, 1, unexpected=True))
"""

    with pytest.raises(
        OracleExtractionError,
        match="keyword arguments are outside the reviewed grammar",
    ):
        extract_manifest_from_source(
            source,
            artifact="synthetic oracle unit fixture",
            jvdata_version="test",
        )


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


def _assert_history_cardinality(history):
    assert len(history["sources"]) == 2
    assert len(history["physical_length_changes"]) == 10
    assert len(history["same_length_semantic_changes"]) == 1


def test_official_layout_history_is_provenanced_and_continuous_to_current():
    history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    current = load_manifest(MANIFEST_PATH)

    assert history["ledger_schema_version"] == 1
    _assert_history_cardinality(history)
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


@pytest.mark.parametrize(
    ("collection", "expected_count"),
    (
        ("sources", 2),
        ("physical_length_changes", 10),
        ("same_length_semantic_changes", 1),
    ),
)
def test_history_contract_rejects_duplicate_entries(collection, expected_count):
    history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    history[collection].append(deepcopy(history[collection][0]))

    assert len(history[collection]) == expected_count + 1
    with pytest.raises(AssertionError):
        _assert_history_cardinality(history)
