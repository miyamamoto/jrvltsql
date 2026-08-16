#!/usr/bin/env python3
"""Fail closed when CI can report green without running the test contract.

Every required step (self-check, pytest, fatal flake8) must be exactly one
executed shell command whose tokens are on an allowlist. Anything that could
mask the command's exit status - extra lines, shell operators, wrappers, custom
shells, environment overrides, advisory or conditional flags - is rejected.
"""

from __future__ import annotations

import argparse
import re
import shlex
import sys
import tomllib
from pathlib import Path
from typing import Any

import yaml

SELF_CHECK_COMMAND = ("python", "scripts/validate_test_gate.py")
FATAL_FLAKE8_SELECT = "--select=E9,F63,F7,F82"
FATAL_FLAKE8_ROOTS = ("src", "tests", "scripts", "tools")
FATAL_FLAKE8_ALLOWED_TOKENS = frozenset(
    {
        "flake8",
        *FATAL_FLAKE8_ROOTS,
        "--isolated",
        "--count",
        FATAL_FLAKE8_SELECT,
        "--show-source",
        "--statistics",
    }
)
REQUIRED_PYTEST_IGNORES = ("tests/integration", "tests/e2e")
REQUIRED_PYTEST_COLLECTION = {
    "testpaths": ["tests"],
    "python_files": ["test_*.py"],
    "python_classes": ["Test*"],
    "python_functions": ["test_*"],
}
REQUIRED_PYTEST_ADDOPTS = [
    "--strict-markers",
    "--strict-config",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--basetemp=.pytest-tmp",
]
SHELL_OPERATOR_PATTERN = re.compile(r"[|&;<>`$(){}]")
PYTEST_ENVIRONMENT_OVERRIDES = frozenset({"PYTEST_ADDOPTS", "PYTHONWARNINGS"})
# Options that may accompany the pytest contract without changing what runs.
PYTEST_ALLOWED_OPTION_PREFIXES = ("--cov-report=", "--durations=", "-r")
PYTEST_ALLOWED_OPTIONS = frozenset({"-v", "-q", "--cov=src"})


def _job(workflow: dict[str, Any], job_name: str) -> dict[str, Any]:
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return {}
    job = jobs.get(job_name)
    return job if isinstance(job, dict) else {}


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    steps = job.get("steps")
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, dict)]


def _is_conditional_or_advisory(node: dict[str, Any]) -> bool:
    return "if" in node or node.get("continue-on-error") not in (None, False)


def _has_custom_shell_or_directory(step: dict[str, Any]) -> bool:
    return "shell" in step or "working-directory" in step


def _has_custom_run_defaults(node: dict[str, Any]) -> bool:
    defaults = node.get("defaults")
    if not isinstance(defaults, dict):
        return False
    run = defaults.get("run")
    return isinstance(run, dict) and bool({"shell", "working-directory"} & set(run))


def _command_lines(run: Any) -> list[str]:
    """Return the logical command lines of a `run:` block (continuations joined)."""
    joined = re.sub(r"\\\s*\n", " ", str(run))
    return [
        line.strip()
        for line in joined.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _single_command_tokens(run: Any) -> tuple[list[str] | None, str | None]:
    """Return (tokens, defect) where defect is None only for one clean command."""
    lines = _command_lines(run)
    if len(lines) != 1:
        return None, "not-single-command"
    command = lines[0]
    if SHELL_OPERATOR_PATTERN.search(command):
        return None, "shell-status-masking"
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None, "shell-status-masking"
    if not tokens:
        return None, "not-single-command"
    return tokens, None


def _env_overrides(*nodes: dict[str, Any]) -> bool:
    for node in nodes:
        env = node.get("env")
        if isinstance(env, dict) and PYTEST_ENVIRONMENT_OVERRIDES & set(map(str, env)):
            return True
    return False


def _self_check_errors(steps: list[dict[str, Any]]) -> list[str]:
    for step in steps:
        tokens, defect = _single_command_tokens(step.get("run", ""))
        if tokens is None or tokens[:2] != list(SELF_CHECK_COMMAND):
            continue
        if (
            defect is None
            and tuple(tokens) == SELF_CHECK_COMMAND
            and not _is_conditional_or_advisory(step)
            and not _has_custom_shell_or_directory(step)
        ):
            return []
        break
    return ["ci-check-step-missing-or-advisory"]


def _first_line_tokens(run: Any) -> list[str]:
    lines = _command_lines(run)
    if not lines:
        return []
    try:
        return shlex.split(lines[0])
    except ValueError:
        return lines[0].split()


def _pytest_option_errors(tokens: list[str], index: int) -> list[str]:
    errors: set[str] = set()
    ignores: list[str] = []
    marker_expressions: list[str] = []
    while index < len(tokens):
        token = tokens[index]
        if token == "--ignore" and index + 1 < len(tokens):
            ignores.append(tokens[index + 1])
            index += 2
            continue
        if token.startswith("--ignore="):
            ignores.append(token.split("=", 1)[1])
        elif token == "-m" and index + 1 < len(tokens):
            marker_expressions.append(tokens[index + 1])
            index += 2
            continue
        elif token in {"-W", "--disable-warnings", "--disable-pytest-warnings"} or (
            token.startswith("-W") or token.startswith("--pythonwarnings")
        ):
            errors.add("pytest-warning-suppression")
        elif token in {"-p"} and index + 1 < len(tokens):
            errors.add("pytest-unapproved-option")
            if tokens[index + 1] == "no:warnings":
                errors.add("pytest-warning-suppression")
            index += 2
            continue
        elif token in {"-k", "--collect-only", "--co", "--deselect", "--ignore-glob",
                       "--last-failed", "--lf"} or token.startswith(
            ("-k", "--deselect=", "--ignore-glob=")
        ):
            errors.add("pytest-selection-bypass")
        elif token in {"-o", "--override-ini", "-c"} or token.startswith(
            ("-o", "--override-ini=", "-c")
        ):
            errors.add("pytest-unapproved-option")
            if "filterwarnings" in " ".join(tokens[index:index + 2]):
                errors.add("pytest-warning-suppression")
        elif token in PYTEST_ALLOWED_OPTIONS or token.startswith(PYTEST_ALLOWED_OPTION_PREFIXES):
            pass
        else:
            errors.add("pytest-unapproved-option")
        index += 1

    normalized_ignores = {path.rstrip("/") for path in ignores}
    if "tests/integration" not in normalized_ignores:
        errors.add("pytest-live-integration-not-excluded")
    if "tests/e2e" not in normalized_ignores:
        errors.add("pytest-e2e-not-excluded")
    if normalized_ignores - set(REQUIRED_PYTEST_IGNORES):
        errors.add("pytest-unapproved-ignore")
    if marker_expressions != ["not slow"]:
        errors.add("pytest-slow-tests-not-excluded")
    return sorted(errors)


def _pytest_errors(workflow: dict[str, Any], test_job: dict[str, Any]) -> list[str]:
    step = next(
        (step for step in _steps(test_job) if step.get("name") == "Run tests"),
        None,
    )
    if step is None:
        return ["pytest-step-missing"]

    errors: list[str] = []
    if _is_conditional_or_advisory(step):
        errors.append("pytest-step-conditional-or-advisory")
    if _has_custom_shell_or_directory(step):
        errors.append("pytest-step-custom-shell-or-directory")
    if _env_overrides(workflow, test_job, step):
        errors.append("pytest-environment-override")

    run = str(step.get("run", ""))
    if re.search(r"tests/(?:[^\s]+/)?test_[^\s]+\.py", run):
        errors.append("pytest-explicit-test-whitelist")

    tokens, defect = _single_command_tokens(run)
    if defect == "shell-status-masking":
        errors.append("pytest-shell-status-masking")
        return errors
    if defect is not None:
        errors.append(f"pytest-step-{defect}")
        return errors
    if tokens[0] != "pytest":
        errors.append("pytest-command-not-pytest")
        return errors
    if tokens[1:2] in (["tests"], ["tests/"]):
        option_start = 2
    else:
        errors.append("pytest-full-tree-missing")
        option_start = 1
    errors.extend(_pytest_option_errors(tokens, option_start))
    return errors


def _fatal_flake8_errors(lint_job: dict[str, Any]) -> list[str]:
    for step in _steps(lint_job):
        run = str(step.get("run", ""))
        tokens, defect = _single_command_tokens(run)
        candidate_tokens = tokens if tokens is not None else _first_line_tokens(run)
        if not candidate_tokens or candidate_tokens[0] != "flake8":
            continue
        if FATAL_FLAKE8_SELECT not in candidate_tokens:
            continue
        errors: list[str] = []
        if step.get("continue-on-error") not in (None, False):
            errors.append("fatal-flake8-is-advisory")
        if "if" in step:
            errors.append("fatal-flake8-is-conditional")
        if _has_custom_shell_or_directory(step):
            errors.append("fatal-flake8-custom-shell-or-directory")
        if defect is not None:
            errors.append(f"fatal-flake8-{defect}")
        if "--exit-zero" in candidate_tokens:
            errors.append("fatal-flake8-mixed-with-advisory")
        if "--isolated" not in candidate_tokens:
            errors.append("fatal-flake8-config-not-isolated")
        if any(
            token not in FATAL_FLAKE8_ALLOWED_TOKENS and token != "--exit-zero"
            for token in candidate_tokens
        ):
            errors.append("fatal-flake8-unapproved-option")
        if not all(root in candidate_tokens for root in FATAL_FLAKE8_ROOTS):
            errors.append("fatal-flake8-scope-incomplete")
        return errors
    return ["fatal-flake8-step-missing"]


def _pytest_ini_errors(pyproject: dict[str, Any]) -> list[str]:
    ini_options = pyproject.get("tool", {}).get("pytest", {}).get("ini_options", {})
    if not isinstance(ini_options, dict):
        return [
            "pytest-collection-policy-not-strict",
            "pytest-addopts-policy-not-strict",
            "pytest-warning-policy-not-strict",
        ]

    errors: list[str] = []
    if any(
        ini_options.get(key) != expected
        for key, expected in REQUIRED_PYTEST_COLLECTION.items()
    ):
        errors.append("pytest-collection-policy-not-strict")
    if ini_options.get("addopts") != REQUIRED_PYTEST_ADDOPTS:
        errors.append("pytest-addopts-policy-not-strict")
    filters = ini_options.get("filterwarnings", [])
    if isinstance(filters, str):
        filters = [filters]
    if filters != ["error"]:
        errors.append("pytest-warning-policy-not-strict")
    return errors


def validate_test_gate(
    workflow: dict[str, Any],
    pyproject: dict[str, Any],
) -> list[str]:
    """Return stable error codes for every fail-open CI test-gate defect."""

    errors: list[str] = []
    test_job = _job(workflow, "test")
    lint_job = _job(workflow, "lint")
    if _is_conditional_or_advisory(test_job):
        errors.append("test-job-conditional-or-advisory")
    if _is_conditional_or_advisory(lint_job):
        errors.append("lint-job-conditional-or-advisory")
    if _has_custom_run_defaults(workflow):
        errors.append("workflow-custom-run-defaults")
    if _has_custom_run_defaults(test_job):
        errors.append("test-job-custom-run-defaults")
    if _has_custom_run_defaults(lint_job):
        errors.append("lint-job-custom-run-defaults")

    errors.extend(_self_check_errors(_steps(test_job)))
    errors.extend(_pytest_errors(workflow, test_job))
    errors.extend(_pytest_ini_errors(pyproject))
    errors.extend(_fatal_flake8_errors(lint_job))
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
