#!/usr/bin/env python3
"""Fail closed when CI can report green without running the test contract."""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

import yaml


def _steps(workflow: dict[str, Any], job_name: str) -> list[dict[str, Any]]:
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return []
    job = jobs.get(job_name)
    if not isinstance(job, dict):
        return []
    steps = job.get("steps")
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, dict)]


def validate_test_gate(
    workflow: dict[str, Any],
    pyproject: dict[str, Any],
) -> list[str]:
    """Return stable error codes for every fail-open CI test-gate defect."""

    errors: list[str] = []
    test_steps = _steps(workflow, "test")

    self_check = next(
        (
            step
            for step in test_steps
            if "scripts/validate_test_gate.py" in str(step.get("run", ""))
        ),
        None,
    )
    if self_check is None or self_check.get("continue-on-error") is True:
        errors.append("ci-check-step-missing-or-advisory")

    pytest_step = next(
        (step for step in test_steps if step.get("name") == "Run tests"),
        None,
    )
    if pytest_step is None:
        errors.append("pytest-step-missing")
    else:
        command = re.sub(r"\\\s*\n", " ", str(pytest_step.get("run", "")))
        if re.search(r"tests/(?:[^\s]+/)?test_[^\s]+\.py", command):
            errors.append("pytest-explicit-test-whitelist")
        if not re.search(r"\bpytest\s+tests/?(?:\s|$)", command):
            errors.append("pytest-full-tree-missing")
        if "--ignore=tests/integration" not in command:
            errors.append("pytest-live-integration-not-excluded")
        if not re.search(r"-m\s+(['\"]?)not slow\1", command):
            errors.append("pytest-slow-tests-not-excluded")

    ini_options = (
        pyproject.get("tool", {})
        .get("pytest", {})
        .get("ini_options", {})
    )
    filters = ini_options.get("filterwarnings", []) if isinstance(ini_options, dict) else []
    if isinstance(filters, str):
        filters = [filters]
    warnings_are_errors = any(
        item == "error" or item.startswith("error::pytest.PytestReturnNotNoneWarning")
        for item in filters
        if isinstance(item, str)
    )
    if not warnings_are_errors:
        errors.append("pytest-return-warning-not-error")

    lint_steps = _steps(workflow, "lint")
    fatal_lint = next(
        (
            step
            for step in lint_steps
            if "flake8" in str(step.get("run", ""))
            and "--select=E9,F63,F7,F82" in str(step.get("run", ""))
        ),
        None,
    )
    if fatal_lint is None:
        errors.append("fatal-flake8-step-missing")
    else:
        if fatal_lint.get("continue-on-error") is True:
            errors.append("fatal-flake8-is-advisory")
        if "--exit-zero" in str(fatal_lint.get("run", "")):
            errors.append("fatal-flake8-mixed-with-advisory")

    return errors


def _load(workflow_path: Path, pyproject_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    with pyproject_path.open("rb") as stream:
        pyproject = tomllib.load(stream)
    if not isinstance(workflow, dict) or not isinstance(pyproject, dict):
        raise ValueError("configuration root must be a mapping")
    return workflow, pyproject


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", type=Path, default=Path(".github/workflows/test.yml"))
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    args = parser.parse_args(argv)

    try:
        workflow, pyproject = _load(args.workflow, args.pyproject)
    except Exception as exc:
        print(f"TEST GATE ERROR: unreadable configuration ({type(exc).__name__})")
        return 2

    errors = validate_test_gate(workflow, pyproject)
    if errors:
        for error in errors:
            print(f"TEST GATE FAIL: {error}")
        return 1

    print("TEST GATE PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
