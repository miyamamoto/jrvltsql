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


class OracleExtractionError(ValueError):
    """Raised when an SDK structure expression is outside the reviewed grammar."""


def _integer(expression: ast.expr, environment: dict[str, int] | None = None) -> int:
    environment = environment or {}
    if isinstance(expression, ast.Constant) and isinstance(expression.value, int):
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


def _slice_call(
    expression: ast.expr,
    *,
    loop_variable: str | None = None,
) -> dict[str, Any]:
    environment_zero = {loop_variable: 0} if loop_variable else {}
    environment_one = {loop_variable: 1} if loop_variable else {}

    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id in {"MidB2S", "MidB2B"}
        and len(expression.args) == 3
    ):
        start_expression = expression.args[1]
        result = {
            "kind": "scalar",
            "start": _integer(start_expression, environment_zero),
            "width": _integer(expression.args[2], environment_zero),
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
        if not (
            isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Name)
            and inner.func.id == "MidB2B"
            and len(inner.args) == 3
        ):
            raise OracleExtractionError(
                f"nested structure without MidB2B: {ast.unparse(expression)}"
            )
        start_expression = inner.args[1]
        result = {
            "kind": "nested",
            "start": _integer(start_expression, environment_zero),
            "width": _integer(inner.args[2], environment_zero),
            "struct": expression.func.value.id,
        }
    else:
        raise OracleExtractionError(f"unsupported field expression: {ast.unparse(expression)}")

    if loop_variable:
        result["stride"] = _integer(start_expression, environment_one) - _integer(
            start_expression, environment_zero
        )
    return result


def _field(expression: ast.expr, name: str) -> dict[str, Any]:
    if not isinstance(expression, ast.ListComp):
        return {"name": name, **_slice_call(expression)}

    if len(expression.generators) != 1:
        raise OracleExtractionError(f"repeat must have one generator: {name}")
    generator = expression.generators[0]
    if generator.ifs or generator.is_async or not isinstance(generator.target, ast.Name):
        raise OracleExtractionError(f"unsupported repeat generator: {name}")
    iterator = generator.iter
    if not (
        isinstance(iterator, ast.Call)
        and isinstance(iterator.func, ast.Name)
        and iterator.func.id == "range"
        and len(iterator.args) == 1
    ):
        raise OracleExtractionError(f"repeat must use range(count): {name}")

    element = _slice_call(expression.elt, loop_variable=generator.target.id)
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


def _set_data_return(class_node: ast.ClassDef) -> ast.Call:
    method = next(
        (
            node
            for node in class_node.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == "SetDataB"
        ),
        None,
    )
    if method is None:
        raise OracleExtractionError(f"{class_node.name}: SetDataB is missing")
    returns = [node for node in ast.walk(method) if isinstance(node, ast.Return)]
    if len(returns) != 1:
        raise OracleExtractionError(f"{class_node.name}: expected one return")
    value = returns[0].value
    if not (
        isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "cls"
    ):
        raise OracleExtractionError(f"{class_node.name}: return must construct cls")
    return value


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
        constructor = _set_data_return(class_node)
        if len(annotations) != len(constructor.args):
            raise OracleExtractionError(
                f"{class_node.name}: {len(annotations)} fields != {len(constructor.args)} values"
            )
        fields = [
            _field(expression, annotation.target.id)
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
    if manifest.get("manifest_schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append("manifest:unsupported-schema-version")

    source = manifest.get("source")
    if not isinstance(source, dict) or not SHA256_PATTERN.fullmatch(str(source.get("sha256", ""))):
        errors.append("source:invalid-sha256")
    if not isinstance(source, dict) or not str(source.get("artifact", "")).strip():
        errors.append("source:artifact-missing")
    if not isinstance(source, dict) or not str(source.get("jvdata_version", "")).strip():
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
            field_name = str(field.get("name", ""))
            prefix = f"{structure_name}.{field_name}"
            if not field_name or field_name in names:
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
                target = field.get("struct") if element_kind == "nested" else None
            else:
                end = start + field_width - 1
                target = field.get("struct") if kind == "nested" else None

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
                errors.extend(f"{structure_name}:gap:{byte}" for byte in range(cursor, start))
            elif start < cursor:
                errors.append(f"{structure_name}:overlap:{start}")
            cursor = max(cursor, end + 1)
        if cursor <= width:
            errors.extend(f"{structure_name}:gap:{byte}" for byte in range(cursor, width + 1))
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
        if not isinstance(record_type, str) or not re.fullmatch(r"[A-Z0-9]{2}", record_type):
            errors.append(f"{prefix}:invalid-record-type")
        if not isinstance(contract, dict):
            errors.append(f"{prefix}:invalid-contract")
            continue
        structure_name = contract.get("struct")
        if structure_name not in structures:
            errors.append(f"{prefix}:unknown-struct:{structure_name}")
            continue
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
