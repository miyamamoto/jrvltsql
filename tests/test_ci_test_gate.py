"""Regression contract for the fail-closed GitHub test gate."""

from pathlib import Path

import tomllib
import yaml

from scripts.validate_test_gate import main, validate_test_gate


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
                        "run": "flake8 src tests scripts tools --select=E9,F63,F7,F82",
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
                "--deselect=tests/test_parser.py::test_parse | true"
            ),
            "continue-on-error": "${{ true }}",
            "if": "${{ false }}",
        },
    ]
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

    pyproject = {
        "tool": {
            "pytest": {
                "ini_options": {"filterwarnings": ["error", "ignore"]},
            }
        }
    }

    assert set(validate_test_gate(workflow, pyproject)) == {
        "ci-check-step-missing-or-advisory",
        "test-job-conditional-or-advisory",
        "lint-job-conditional-or-advisory",
        "pytest-explicit-test-whitelist",
        "pytest-full-tree-missing",
        "pytest-live-integration-not-excluded",
        "pytest-slow-tests-not-excluded",
        "pytest-step-conditional-or-advisory",
        "pytest-warning-policy-not-strict",
        "pytest-warning-suppression",
        "pytest-selection-bypass",
        "pytest-unapproved-ignore",
        "pytest-shell-status-masking",
        "fatal-flake8-is-advisory",
        "fatal-flake8-is-conditional",
        "fatal-flake8-mixed-with-advisory",
        "fatal-flake8-scope-incomplete",
    }


def test_validator_accepts_the_paired_fail_closed_control():
    pyproject = {
        "tool": {
            "pytest": {
                "ini_options": {"filterwarnings": ["error"]},
            }
        }
    }

    assert validate_test_gate(_good_workflow(), pyproject) == []


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
