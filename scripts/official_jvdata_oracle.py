#!/usr/bin/env python3
"""Generate and validate a compact oracle from the official SDK structure file.

The generated manifest contains layout facts only: structure/field names,
one-based byte starts, widths, nested structure references, and repeat counts.
It never copies provider records or the SDK source itself into the repository.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from functools import cache
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA_VERSION = 1
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
OFFICIAL_YMD_FIELDS = [
    {"name": "Year", "kind": "scalar", "start": 1, "width": 4, "decoder": "text"},
    {"name": "Month", "kind": "scalar", "start": 5, "width": 2, "decoder": "text"},
    {"name": "Day", "kind": "scalar", "start": 7, "width": 2, "decoder": "text"},
]
OFFICIAL_RECORD_ID_FIELDS = [
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
]


class OracleExtractionError(ValueError):
    """Raised when an SDK structure expression is outside the reviewed grammar."""


def _integer(expression: ast.expr, environment: dict[str, int] | None = None) -> int:
    environment = environment or {}
    if (
        isinstance(expression, ast.Constant)
        and isinstance(expression.value, int)
        and not isinstance(expression.value, bool)
    ):
        return expression.value
    if isinstance(expression, ast.Name) and expression.id in environment:
        return environment[expression.id]
    if isinstance(expression, ast.UnaryOp) and isinstance(expression.op, ast.USub):
        return -_integer(expression.operand, environment)
    if isinstance(expression, ast.BinOp):
        left = _integer(expression.left, environment)
        right = _integer(expression.right, environment)
        if isinstance(expression.op, ast.Add):
            return left + right
        if isinstance(expression.op, ast.Sub):
            return left - right
        if isinstance(expression.op, ast.Mult):
            return left * right
    raise OracleExtractionError(f"unsupported integer expression: {ast.unparse(expression)}")


def _affine_integer(expression: ast.expr, variable: str) -> tuple[int, int]:
    """Return the constant and coefficient for a reviewed affine expression."""

    if (
        isinstance(expression, ast.Constant)
        and isinstance(expression.value, int)
        and not isinstance(expression.value, bool)
    ):
        return expression.value, 0
    if isinstance(expression, ast.Name) and expression.id == variable:
        return 0, 1
    if isinstance(expression, ast.UnaryOp) and isinstance(expression.op, ast.USub):
        constant, coefficient = _affine_integer(expression.operand, variable)
        return -constant, -coefficient
    if isinstance(expression, ast.BinOp):
        left_constant, left_coefficient = _affine_integer(expression.left, variable)
        right_constant, right_coefficient = _affine_integer(expression.right, variable)
        if isinstance(expression.op, ast.Add):
            return (
                left_constant + right_constant,
                left_coefficient + right_coefficient,
            )
        if isinstance(expression.op, ast.Sub):
            return (
                left_constant - right_constant,
                left_coefficient - right_coefficient,
            )
        if isinstance(expression.op, ast.Mult):
            if left_coefficient and right_coefficient:
                raise OracleExtractionError(f"non-affine expression: {ast.unparse(expression)}")
            return (
                left_constant * right_constant,
                left_constant * right_coefficient + left_coefficient * right_constant,
            )
    raise OracleExtractionError(f"non-affine expression: {ast.unparse(expression)}")


def _slice_call(
    expression: ast.expr,
    *,
    source_parameter: str,
    loop_variable: str | None = None,
) -> dict[str, Any]:
    environment_zero = {loop_variable: 0} if loop_variable else {}
    if isinstance(expression, ast.Call) and expression.keywords:
        raise OracleExtractionError("field call keyword arguments are outside the reviewed grammar")

    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id in {"MidB2S", "MidB2B"}
        and len(expression.args) == 3
    ):
        source_expression = expression.args[0]
        if not (
            isinstance(source_expression, ast.Name) and source_expression.id == source_parameter
        ):
            raise OracleExtractionError(
                "slice source must be the reviewed byte parameter " f"{source_parameter}"
            )
        start_expression = expression.args[1]
        width_expression = expression.args[2]
        result = {
            "kind": "scalar",
            "start": _integer(start_expression, environment_zero),
            "width": _integer(width_expression, environment_zero),
            "decoder": "text" if expression.func.id == "MidB2S" else "bytes",
        }
    elif (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Attribute)
        and expression.func.attr == "SetDataB"
        and isinstance(expression.func.value, ast.Name)
        and len(expression.args) == 1
    ):
        inner = expression.args[0]
        if isinstance(inner, ast.Call) and inner.keywords:
            raise OracleExtractionError(
                "slice call keyword arguments are outside the reviewed grammar"
            )
        if not (
            isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Name)
            and inner.func.id == "MidB2B"
            and len(inner.args) == 3
        ):
            raise OracleExtractionError(
                f"nested structure without MidB2B: {ast.unparse(expression)}"
            )
        source_expression = inner.args[0]
        if not (
            isinstance(source_expression, ast.Name) and source_expression.id == source_parameter
        ):
            raise OracleExtractionError(
                "slice source must be the reviewed byte parameter " f"{source_parameter}"
            )
        start_expression = inner.args[1]
        width_expression = inner.args[2]
        result = {
            "kind": "nested",
            "start": _integer(start_expression, environment_zero),
            "width": _integer(width_expression, environment_zero),
            "struct": expression.func.value.id,
        }
    else:
        raise OracleExtractionError(f"unsupported field expression: {ast.unparse(expression)}")

    if loop_variable:
        try:
            start, stride = _affine_integer(start_expression, loop_variable)
        except OracleExtractionError as exc:
            raise OracleExtractionError(
                f"non-affine repeat offset: {ast.unparse(start_expression)}"
            ) from exc
        try:
            width, width_coefficient = _affine_integer(
                width_expression,
                loop_variable,
            )
        except OracleExtractionError as exc:
            raise OracleExtractionError(
                f"non-affine repeat width: {ast.unparse(width_expression)}"
            ) from exc
        if width_coefficient:
            raise OracleExtractionError(
                "repeat width depends on loop variable: " f"{ast.unparse(width_expression)}"
            )
        result["start"] = start
        result["width"] = width
        result["stride"] = stride
    return result


def _field(expression: ast.expr, name: str, *, source_parameter: str) -> dict[str, Any]:
    if not isinstance(expression, ast.ListComp):
        return {
            "name": name,
            **_slice_call(expression, source_parameter=source_parameter),
        }

    if len(expression.generators) != 1:
        raise OracleExtractionError(f"repeat must have one generator: {name}")
    generator = expression.generators[0]
    if generator.ifs or generator.is_async or not isinstance(generator.target, ast.Name):
        raise OracleExtractionError(f"unsupported repeat generator: {name}")
    iterator = generator.iter
    if isinstance(iterator, ast.Call) and iterator.keywords:
        raise OracleExtractionError(
            f"{name}: range keyword arguments are outside the reviewed grammar"
        )
    if not (
        isinstance(iterator, ast.Call)
        and isinstance(iterator.func, ast.Name)
        and iterator.func.id == "range"
        and len(iterator.args) == 1
    ):
        raise OracleExtractionError(f"repeat must use range(count): {name}")

    element = _slice_call(
        expression.elt,
        source_parameter=source_parameter,
        loop_variable=generator.target.id,
    )
    result: dict[str, Any] = {
        "name": name,
        "kind": "repeat",
        "start": element["start"],
        "width": element["width"],
        "stride": element.pop("stride"),
        "count": _integer(iterator.args[0]),
        "element_kind": element.pop("kind"),
    }
    result.update({key: value for key, value in element.items() if key not in {"start", "width"}})
    return result


def _set_data_return(class_node: ast.ClassDef) -> tuple[ast.Call, str]:
    methods = [
        node
        for node in class_node.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == "SetDataB"
    ]
    if len(methods) != 1:
        raise OracleExtractionError(f"{class_node.name}: expected exactly one SetDataB")
    method = methods[0]
    if not isinstance(method, ast.FunctionDef):
        raise OracleExtractionError(f"{class_node.name}: SetDataB must be synchronous")
    if not (
        len(method.decorator_list) == 1
        and isinstance(method.decorator_list[0], ast.Name)
        and method.decorator_list[0].id == "classmethod"
    ):
        raise OracleExtractionError(f"{class_node.name}: SetDataB must be a classmethod")

    arguments = method.args
    if not (
        not arguments.posonlyargs
        and [argument.arg for argument in arguments.args] == ["cls", "b"]
        and arguments.vararg is None
        and not arguments.kwonlyargs
        and not arguments.kw_defaults
        and arguments.kwarg is None
        and not arguments.defaults
    ):
        raise OracleExtractionError(
            f"{class_node.name}: SetDataB signature must be exactly (cls, b)"
        )
    if len(method.body) != 1 or not isinstance(method.body[0], ast.Return):
        raise OracleExtractionError(f"{class_node.name}: SetDataB must contain one direct return")
    value = method.body[0].value
    if not (
        isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "cls"
    ):
        raise OracleExtractionError(f"{class_node.name}: return must construct cls")
    return value, arguments.args[1].arg


def _field_end(field: dict[str, Any]) -> int:
    if field["kind"] == "repeat":
        return field["start"] + field["stride"] * (field["count"] - 1) + field["width"] - 1
    return field["start"] + field["width"] - 1


def _expanded_counts(structures: dict[str, dict[str, Any]]) -> dict[str, int]:
    visiting: set[str] = set()

    @cache
    def count(structure_name: str) -> int:
        if structure_name in visiting:
            raise OracleExtractionError(f"cyclic structure: {structure_name}")
        if structure_name not in structures:
            raise OracleExtractionError(f"unknown structure: {structure_name}")
        visiting.add(structure_name)
        total = 0
        for field in structures[structure_name]["fields"]:
            if field["kind"] == "scalar":
                total += 1
            elif field["kind"] == "nested":
                total += count(field["struct"])
            elif field["element_kind"] == "scalar":
                total += field["count"]
            else:
                total += field["count"] * count(field["struct"])
        visiting.remove(structure_name)
        return total

    return {name: count(name) for name in structures}


def extract_manifest_from_source(
    source: str,
    *,
    artifact: str,
    jvdata_version: str,
    source_sha256: str | None = None,
) -> dict[str, Any]:
    """Extract the reviewed AST grammar into a compact manifest."""

    tree = ast.parse(source)
    structures: dict[str, dict[str, Any]] = {}
    root_records: dict[str, dict[str, Any]] = {}

    for class_node in (node for node in tree.body if isinstance(node, ast.ClassDef)):
        annotations = [
            node
            for node in class_node.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        ]
        if not annotations:
            continue
        constructor, source_parameter = _set_data_return(class_node)
        if constructor.keywords:
            raise OracleExtractionError(
                f"{class_node.name}: keyword arguments are outside the reviewed grammar"
            )
        if len(annotations) != len(constructor.args):
            raise OracleExtractionError(
                f"{class_node.name}: {len(annotations)} fields != {len(constructor.args)} values"
            )
        fields = [
            _field(
                expression,
                annotation.target.id,
                source_parameter=source_parameter,
            )
            for annotation, expression in zip(annotations, constructor.args, strict=True)
        ]
        structures[class_node.name] = {
            "width": max(_field_end(field) for field in fields),
            "fields": fields,
        }

    expanded_counts = _expanded_counts(structures)
    for name, count in expanded_counts.items():
        structures[name]["expanded_leaf_count"] = count

    for name, structure in structures.items():
        fields = structure["fields"]
        if name.startswith("JV_") and fields and fields[0]["name"] == "head":
            parts = name.split("_")
            if len(parts) < 3 or len(parts[1]) != 2:
                raise OracleExtractionError(f"invalid root structure name: {name}")
            record_type = parts[1]
            if record_type in root_records:
                raise OracleExtractionError(f"duplicate root record: {record_type}")
            root_records[record_type] = {"struct": name, "length": structure["width"]}

    digest = source_sha256 or hashlib.sha256(source.encode("utf-8")).hexdigest()
    manifest = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "source": {
            "artifact": artifact,
            "jvdata_version": jvdata_version,
            "sha256": digest,
        },
        "structures": structures,
        "root_records": dict(sorted(root_records.items())),
        "summary": {
            "structure_count": len(structures),
            "repeat_template_count": sum(
                field["kind"] == "repeat"
                for structure in structures.values()
                for field in structure["fields"]
            ),
            "root_record_count": len(root_records),
            "expanded_leaf_count": sum(
                expanded_counts[contract["struct"]] for contract in root_records.values()
            ),
        },
    }
    errors = validate_manifest(manifest)
    if errors:
        raise OracleExtractionError("; ".join(errors))
    return manifest


def _positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _plain_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_manifest(manifest: Any) -> list[str]:
    """Return stable errors for an incomplete or internally inconsistent oracle."""

    try:
        return _validate_manifest(manifest)
    except Exception as exc:  # A crashed inspection is not a passing inspection.
        return [f"manifest:unreadable:{type(exc).__name__}"]


def _validate_manifest(manifest: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest:not-an-object"]
    manifest_schema_version = manifest.get("manifest_schema_version")
    if (
        not _plain_integer(manifest_schema_version)
        or manifest_schema_version != MANIFEST_SCHEMA_VERSION
    ):
        errors.append("manifest:unsupported-schema-version")

    source = manifest.get("source")
    if (
        not isinstance(source, dict)
        or not isinstance(source.get("sha256"), str)
        or not SHA256_PATTERN.fullmatch(source["sha256"])
    ):
        errors.append("source:invalid-sha256")
    if (
        not isinstance(source, dict)
        or not isinstance(source.get("artifact"), str)
        or not source["artifact"].strip()
    ):
        errors.append("source:artifact-missing")
    if (
        not isinstance(source, dict)
        or not isinstance(source.get("jvdata_version"), str)
        or not source["jvdata_version"].strip()
    ):
        errors.append("source:jvdata-version-missing")

    structures = manifest.get("structures")
    root_records = manifest.get("root_records")
    summary = manifest.get("summary")
    if not isinstance(structures, dict):
        return errors + ["structures:not-an-object"]
    if not isinstance(root_records, dict):
        return errors + ["root-records:not-an-object"]
    if not isinstance(summary, dict):
        return errors + ["summary:not-an-object"]
    if not structures:
        errors.append("structures:empty")
    if not root_records:
        errors.append("root-records:empty")
    ymd = structures.get("YMD")
    if (
        not isinstance(ymd, dict)
        or ymd.get("width") != 8
        or ymd.get("fields") != OFFICIAL_YMD_FIELDS
    ):
        errors.append("record-header:invalid-ymd")
    record_id = structures.get("RECORD_ID")
    if (
        not isinstance(record_id, dict)
        or record_id.get("width") != 11
        or record_id.get("fields") != OFFICIAL_RECORD_ID_FIELDS
    ):
        errors.append("record-header:invalid-record-id")

    calculated_repeat_count = 0
    for structure_name, structure in structures.items():
        if not isinstance(structure, dict):
            errors.append(f"{structure_name}:not-an-object")
            continue
        width = structure.get("width")
        fields = structure.get("fields")
        if not _positive_integer(width):
            errors.append(f"{structure_name}:invalid-width")
            continue
        if not isinstance(fields, list) or not fields:
            errors.append(f"{structure_name}:fields-missing")
            continue

        intervals: list[tuple[int, int]] = []
        names: set[str] = set()
        for field in fields:
            if not isinstance(field, dict):
                errors.append(f"{structure_name}:invalid-field")
                continue
            raw_field_name = field.get("name")
            field_name = str(raw_field_name)
            prefix = f"{structure_name}.{field_name}"
            if (
                not isinstance(raw_field_name, str)
                or not raw_field_name.strip()
                or field_name in names
            ):
                errors.append(f"{structure_name}:invalid-or-duplicate-field:{field_name}")
            names.add(field_name)
            kind = field.get("kind")
            start = field.get("start")
            field_width = field.get("width")
            if kind not in {"scalar", "nested", "repeat"}:
                errors.append(f"{prefix}:invalid-kind")
                continue
            if not _positive_integer(start) or not _positive_integer(field_width):
                errors.append(f"{prefix}:invalid-span")
                continue

            if kind == "repeat":
                calculated_repeat_count += 1
                count = field.get("count")
                stride = field.get("stride")
                element_kind = field.get("element_kind")
                if not _positive_integer(count):
                    errors.append(f"{prefix}:invalid-repeat-count")
                    continue
                if not _positive_integer(stride):
                    errors.append(f"{prefix}:invalid-repeat-stride")
                    continue
                if stride != field_width:
                    errors.append(f"{prefix}:repeat-stride-width-mismatch:{stride}!={field_width}")
                if element_kind not in {"scalar", "nested"}:
                    errors.append(f"{prefix}:invalid-element-kind")
                    continue
                end = start + stride * (count - 1) + field_width - 1
                if element_kind == "scalar":
                    target = None
                    if field.get("decoder") not in {"text", "bytes"}:
                        errors.append(f"{prefix}:invalid-decoder")
                else:
                    target = field.get("struct")
            else:
                end = start + field_width - 1
                if kind == "scalar":
                    target = None
                    if field.get("decoder") not in {"text", "bytes"}:
                        errors.append(f"{prefix}:invalid-decoder")
                else:
                    target = field.get("struct")

            if kind == "nested" or (kind == "repeat" and field.get("element_kind") == "nested"):
                if not isinstance(target, str) or not target.strip():
                    errors.append(f"{prefix}:struct-missing")
                    target = None
            if target is not None:
                if target not in structures:
                    errors.append(f"{prefix}:unknown-struct:{target}")
                else:
                    target_width = structures[target].get("width")
                    if field_width != target_width:
                        errors.append(
                            f"{prefix}:nested-width-mismatch:{field_width}!={target_width}"
                        )
            intervals.append((start, end))

        cursor = 1
        for start, end in sorted(intervals):
            if start > cursor:
                errors.append(f"{structure_name}:gap:{cursor}-{start - 1}")
            elif start < cursor:
                errors.append(f"{structure_name}:overlap:{start}")
            cursor = max(cursor, end + 1)
        if cursor <= width:
            errors.append(f"{structure_name}:gap:{cursor}-{width}")
        elif cursor - 1 > width:
            errors.append(f"{structure_name}:extent-exceeds-width:{cursor - 1}>{width}")

    calculated_leaf_counts: dict[str, int] = {}
    visiting: set[str] = set()

    def leaf_count(structure_name: str) -> int:
        if structure_name in calculated_leaf_counts:
            return calculated_leaf_counts[structure_name]
        if structure_name in visiting or structure_name not in structures:
            return 0
        visiting.add(structure_name)
        total = 0
        for field in structures[structure_name].get("fields", []):
            if not isinstance(field, dict):
                continue
            if field.get("kind") == "scalar":
                total += 1
            elif field.get("kind") == "nested":
                target = str(field.get("struct", ""))
                if target in visiting:
                    errors.append(
                        f"{structure_name}.{field.get('name', '')}:" f"cyclic-struct:{target}"
                    )
                else:
                    total += leaf_count(target)
            elif field.get("kind") == "repeat" and _positive_integer(field.get("count")):
                if field.get("element_kind") == "scalar":
                    element_count = 1
                else:
                    target = str(field.get("struct", ""))
                    if target in visiting:
                        errors.append(
                            f"{structure_name}.{field.get('name', '')}:" f"cyclic-struct:{target}"
                        )
                        element_count = 0
                    else:
                        element_count = leaf_count(target)
                total += field["count"] * element_count
        visiting.remove(structure_name)
        calculated_leaf_counts[structure_name] = total
        declared = structures[structure_name].get("expanded_leaf_count")
        if not _plain_integer(declared) or declared != total:
            errors.append(f"{structure_name}:expanded-leaf-count:{declared}!={total}")
        return total

    for structure_name in structures:
        leaf_count(structure_name)

    root_leaf_count = 0
    for record_type, contract in root_records.items():
        prefix = f"root:{record_type}"
        valid_record_type = isinstance(record_type, str) and bool(
            re.fullmatch(r"[A-Z0-9]{2}", record_type)
        )
        if not valid_record_type:
            errors.append(f"{prefix}:invalid-record-type")
        if not isinstance(contract, dict):
            errors.append(f"{prefix}:invalid-contract")
            continue
        structure_name = contract.get("struct")
        if structure_name not in structures:
            errors.append(f"{prefix}:unknown-struct:{structure_name}")
            continue
        if valid_record_type and not structure_name.startswith(f"JV_{record_type}_"):
            errors.append(f"{prefix}:structure-name-mismatch:{structure_name}")
        root_fields = structures[structure_name].get("fields")
        if (
            not isinstance(root_fields, list)
            or not root_fields
            or not isinstance(root_fields[0], dict)
            or root_fields[0].get("name") != "head"
        ):
            errors.append(f"{prefix}:head-missing:{structure_name}")
        else:
            head = root_fields[0]
            if (
                head.get("kind") != "nested"
                or head.get("start") != 1
                or head.get("width") != 11
                or head.get("struct") != "RECORD_ID"
            ):
                errors.append(f"{prefix}:invalid-head-contract:{structure_name}")
        length = contract.get("length")
        structure_width = structures[structure_name].get("width")
        if not _plain_integer(length) or length != structure_width:
            errors.append(f"{prefix}:length-mismatch:{length}!={structure_width}")
        root_leaf_count += calculated_leaf_counts.get(structure_name, 0)

    expected_summary = {
        "structure_count": len(structures),
        "repeat_template_count": calculated_repeat_count,
        "root_record_count": len(root_records),
        "expanded_leaf_count": root_leaf_count,
    }
    summary_codes = {
        "structure_count": "structure-count",
        "repeat_template_count": "repeat-template-count",
        "root_record_count": "root-record-count",
        "expanded_leaf_count": "expanded-leaf-count",
    }
    for key, expected in expected_summary.items():
        actual = summary.get(key)
        if not _plain_integer(actual) or actual != expected:
            errors.append(f"summary:{summary_codes[key]}:{actual}!={expected}")
    return sorted(set(errors))


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON oracle manifest."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("manifest root must be an object")
    return value


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate")
    generate.add_argument("--source", type=Path, required=True)
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument(
        "--artifact",
        default="JRA-VAN Data Lab SDK 5.0.0 Python JV-Data structures",
    )
    generate.add_argument("--jvdata-version", default="4.9.0.1")
    validate = subparsers.add_parser("validate")
    validate.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "generate":
            source_bytes = args.source.read_bytes()
            source = source_bytes.decode("utf-8-sig")
            manifest = extract_manifest_from_source(
                source,
                artifact=args.artifact,
                jvdata_version=args.jvdata_version,
                source_sha256=hashlib.sha256(source_bytes).hexdigest(),
            )
            _write_manifest(args.output, manifest)
            print(
                "OFFICIAL ORACLE GENERATED: "
                f"{manifest['summary']['root_record_count']} records, "
                f"{manifest['summary']['structure_count']} structures, "
                f"{manifest['summary']['expanded_leaf_count']} leaves"
            )
            return 0

        manifest = load_manifest(args.manifest)
        errors = validate_manifest(manifest)
        if errors:
            for error in errors:
                print(f"OFFICIAL ORACLE FAIL: {error}")
            return 1
        print("OFFICIAL ORACLE PASS")
        return 0
    except Exception as exc:
        print(f"OFFICIAL ORACLE ERROR: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
