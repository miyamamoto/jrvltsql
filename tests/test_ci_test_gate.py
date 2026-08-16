"""Regression contract for the fail-closed GitHub test gate."""

from copy import deepcopy
from pathlib import Path

import pytest
import tomllib
import yaml

from scripts.validate_test_gate import main, validate_test_gate

STRICT_PYPROJECT = {
    "tool": {
        "pytest": {
            "ini_options": {
                "testpaths": ["tests"],
                "python_files": ["test_*.py"],
                "python_classes": ["Test*"],
                "python_functions": ["test_*"],
                "addopts": [
                    "--strict-markers",
                    "--strict-config",
                    "--cov=src",
                    "--cov-report=term-missing",
                    "--cov-report=html",
                    "--basetemp=.pytest-tmp",
                ],
                "filterwarnings": ["error"],
            }
        }
    }
}


def _step(workflow, job, name):
    return next(step for step in workflow["jobs"][job]["steps"] if step["name"] == name)


def _set_run(job, name, run):
    return lambda workflow: _step(workflow, job, name).__setitem__("run", run)


def _set_key(job, name, key, value):
    return lambda workflow: _step(workflow, job, name).__setitem__(key, value)


PYTEST_COMMAND = 'pytest tests --ignore=tests/integration --ignore=tests/e2e -m "not slow"'
FLAKE8_COMMAND = (
    "flake8 src tests scripts tools --isolated --count --select=E9,F63,F7,F82 "
    "--show-source --statistics"
)

# One row per masking channel: (mutation of the good workflow, expected refusal code)
SINGLE_COMMAND_MASKING_CASES = {
    "pytest-newline-true": (
        _set_run("test", "Run tests", PYTEST_COMMAND + "\ntrue"),
        "pytest-step-not-single-command",
    ),
    "pytest-newline-exit-0": (
        _set_run("test", "Run tests", PYTEST_COMMAND + "\nexit 0"),
        "pytest-step-not-single-command",
    ),
    "pytest-set-plus-e-prefix": (
        _set_run("test", "Run tests", "set +e\n" + PYTEST_COMMAND),
        "pytest-step-not-single-command",
    ),
    "pytest-semicolon-true": (
        _set_run("test", "Run tests", PYTEST_COMMAND + "; true"),
        "pytest-shell-status-masking",
    ),
    "pytest-wrapped-in-bash-c": (
        _set_run("test", "Run tests", f"bash -c '{PYTEST_COMMAND}'"),
        "pytest-command-not-pytest",
    ),
    "pytest-alternate-ini": (
        _set_run("test", "Run tests", PYTEST_COMMAND + " -c /dev/null"),
        "pytest-unapproved-option",
    ),
    "pytest-e2e-not-excluded": (
        _set_run(
            "test",
            "Run tests",
            'pytest tests --ignore=tests/integration -m "not slow"',
        ),
        "pytest-e2e-not-excluded",
    ),
    "pytest-step-env-addopts": (
        _set_key("test", "Run tests", "env", {"PYTEST_ADDOPTS": "-W ignore"}),
        "pytest-environment-override",
    ),
    "pytest-job-env-pythonwarnings": (
        lambda workflow: workflow["jobs"]["test"].__setitem__(
            "env", {"PYTHONWARNINGS": "ignore"}
        ),
        "pytest-environment-override",
    ),
    "pytest-custom-shell": (
        _set_key("test", "Run tests", "shell", 'sh -c "true" {0}'),
        "pytest-step-custom-shell-or-directory",
    ),
    "pytest-working-directory": (
        _set_key("test", "Run tests", "working-directory", "tools"),
        "pytest-step-custom-shell-or-directory",
    ),
    "workflow-default-shell": (
        lambda workflow: workflow.__setitem__(
            "defaults", {"run": {"shell": 'sh -c "true" {0}'}}
        ),
        "workflow-custom-run-defaults",
    ),
    "test-job-default-shell": (
        lambda workflow: workflow["jobs"]["test"].__setitem__(
            "defaults", {"run": {"shell": 'sh -c "true" {0}'}}
        ),
        "test-job-custom-run-defaults",
    ),
    "lint-job-default-shell": (
        lambda workflow: workflow["jobs"]["lint"].__setitem__(
            "defaults", {"run": {"shell": 'sh -c "true" {0}'}}
        ),
        "lint-job-custom-run-defaults",
    ),
    "self-check-echo": (
        _set_run("test", "Validate test gate", "echo scripts/validate_test_gate.py"),
        "ci-check-step-missing-or-advisory",
    ),
    "self-check-alternate-workflow": (
        _set_run(
            "test",
            "Validate test gate",
            "python scripts/validate_test_gate.py --workflow other.yml",
        ),
        "ci-check-step-missing-or-advisory",
    ),
    "self-check-newline-true": (
        _set_run("test", "Validate test gate", "python scripts/validate_test_gate.py\ntrue"),
        "ci-check-step-missing-or-advisory",
    ),
    "self-check-custom-shell": (
        _set_key("test", "Validate test gate", "shell", 'sh -c "true" {0}'),
        "ci-check-step-missing-or-advisory",
    ),
    "flake8-echo": (
        _set_run("lint", "Fatal lint", "echo " + FLAKE8_COMMAND),
        "fatal-flake8-step-missing",
    ),
    "flake8-newline-true": (
        _set_run("lint", "Fatal lint", FLAKE8_COMMAND + "\ntrue"),
        "fatal-flake8-not-single-command",
    ),
    "flake8-or-true": (
        _set_run("lint", "Fatal lint", FLAKE8_COMMAND + " || true"),
        "fatal-flake8-shell-status-masking",
    ),
    "flake8-custom-shell": (
        _set_key("lint", "Fatal lint", "shell", 'sh -c "true" {0}'),
        "fatal-flake8-custom-shell-or-directory",
    ),
    "flake8-unapproved-exclude": (
        _set_run(
            "lint",
            "Fatal lint",
            FLAKE8_COMMAND + " --exclude=src,tests,scripts,tools",
        ),
        "fatal-flake8-unapproved-option",
    ),
    "flake8-config-not-isolated": (
        _set_run("lint", "Fatal lint", FLAKE8_COMMAND.replace(" --isolated", "")),
        "fatal-flake8-config-not-isolated",
    ),
}


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    SINGLE_COMMAND_MASKING_CASES.values(),
    ids=SINGLE_COMMAND_MASKING_CASES.keys(),
)
def test_validator_rejects_single_command_masking(mutate, expected_code):
    workflow = _good_workflow()
    mutate(workflow)

    assert expected_code in validate_test_gate(workflow, STRICT_PYPROJECT)


@pytest.mark.parametrize(
    ("key", "value", "expected_code"),
    [
        ("addopts", ["--strict-markers", "-k", "never"], "pytest-addopts-policy-not-strict"),
        ("python_functions", ["test_gate_only"], "pytest-collection-policy-not-strict"),
    ],
)
def test_validator_rejects_pyproject_collection_bypass(key, value, expected_code):
    pyproject = deepcopy(STRICT_PYPROJECT)
    pyproject["tool"]["pytest"]["ini_options"][key] = value

    assert expected_code in validate_test_gate(_good_workflow(), pyproject)


def _good_workflow():
    return {
        "jobs": {
            "test": {
                "steps": [
                    {"name": "Validate test gate", "run": "python scripts/validate_test_gate.py"},
                    {
                        "name": "Run tests",
                        "run": (
                            'pytest tests --ignore=tests/integration '
                            '--ignore=tests/e2e -m "not slow"'
                        ),
                    },
                ]
            },
            "lint": {
                "steps": [
                    {
                        "name": "Fatal lint",
                        "run": FLAKE8_COMMAND,
                    },
                    {
                        "name": "Advisory style",
                        "run": "flake8 src tests --exit-zero",
                        "continue-on-error": True,
                    },
                ]
            },
        }
    }


def test_validator_rejects_every_fail_open_branch():
    workflow = _good_workflow()
    workflow["jobs"]["test"].update(
        {"continue-on-error": True, "if": "${{ false }}"}
    )
    workflow["jobs"]["test"]["steps"] = [
        {
            "name": "Validate test gate",
            "run": "python scripts/validate_test_gate.py",
            "if": "${{ false }}",
        },
        {
            "name": "Run tests",
            "run": (
                "pytest tests/test_parsers.py -W ignore -p no:warnings "
                "-k smoke --collect-only --ignore=tests/other "
                "--deselect=tests/test_parser.py::test_parse"
            ),
            "continue-on-error": "${{ true }}",
            "if": "${{ false }}",
        },
    ]
    workflow["env"] = {"PYTEST_ADDOPTS": "-p no:warnings"}
    workflow["jobs"]["lint"].update(
        {"continue-on-error": "${{ true }}", "if": False}
    )
    workflow["jobs"]["lint"]["steps"] = [
        {
            "name": "Lint",
            "run": "flake8 src tests --select=E9,F63,F7,F82 --exit-zero",
            "continue-on-error": True,
            "if": False,
        }
    ]

    pyproject = deepcopy(STRICT_PYPROJECT)
    pyproject["tool"]["pytest"]["ini_options"]["filterwarnings"] = ["error", "ignore"]

    assert set(validate_test_gate(workflow, pyproject)) == {
        "ci-check-step-missing-or-advisory",
        "test-job-conditional-or-advisory",
        "lint-job-conditional-or-advisory",
        "pytest-explicit-test-whitelist",
        "pytest-full-tree-missing",
        "pytest-live-integration-not-excluded",
        "pytest-e2e-not-excluded",
        "pytest-slow-tests-not-excluded",
        "pytest-step-conditional-or-advisory",
        "pytest-environment-override",
        "pytest-warning-policy-not-strict",
        "pytest-warning-suppression",
        "pytest-selection-bypass",
        "pytest-unapproved-ignore",
        "pytest-unapproved-option",
        "fatal-flake8-is-advisory",
        "fatal-flake8-is-conditional",
        "fatal-flake8-config-not-isolated",
        "fatal-flake8-mixed-with-advisory",
        "fatal-flake8-scope-incomplete",
    }


def test_validator_accepts_the_paired_fail_closed_control():
    assert validate_test_gate(_good_workflow(), STRICT_PYPROJECT) == []


def test_unreadable_configuration_returns_machine_failure(tmp_path, capsys):
    missing_workflow = tmp_path / "missing.yml"
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.pytest.ini_options]\n", encoding="utf-8")

    assert main(["--workflow", str(missing_workflow), "--pyproject", str(pyproject)]) == 2
    assert "TEST GATE ERROR" in capsys.readouterr().out


def test_repository_ci_configuration_is_fail_closed():
    workflow = yaml.safe_load(Path(".github/workflows/test.yml").read_text(encoding="utf-8"))
    with Path("pyproject.toml").open("rb") as stream:
        pyproject = tomllib.load(stream)

    assert validate_test_gate(workflow, pyproject) == []
