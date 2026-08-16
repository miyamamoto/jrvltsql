# JRVLTSQL test suite

The repository separates deterministic local tests from authenticated JV-Link
tests. A green local suite is necessary but does not prove that a release can
acquire and store current provider data.

## Setup

Python 3.12 or later is required.

```bash
uv sync --python 3.12 --all-extras
```

Without `uv`, install the project extras directly:

```bash
python -m pip install -e ".[dev,postgres]"
```

## Local tests

Run the full local suite outside the authenticated Windows-only directories:

```bash
python -m pytest tests/ -q \
  --ignore=tests/integration/ \
  --ignore=tests/e2e/ \
  --basetemp=.pytest-tmp-local
```

Useful focused selections:

```bash
python -m pytest tests/test_current_record_validation.py -q --no-cov
python -m pytest tests/test_integration.py -q --no-cov
python -m pytest tests/test_retired_data_specs.py tests/test_realtime.py -q --no-cov
```

`test_current_record_validation.py` checks every current record ID at the
physical envelope: exact supported length, record ID, strict CP932, and CRLF.
Record-specific tests separately check offsets, repeated arrays, schema,
upsert/delete behavior, and SQLite/PostgreSQL storage.

The GitHub Actions selection is defined in `.github/workflows/test.yml`. Do not
copy a fixed test count into documentation; the suite changes with each
official-contract repair.

## Authenticated tests

`tests/integration/test_jvlink_real.py` performs a real fetch, parse, SQLite
import, and readback. It is skipped unless explicitly enabled on an authorized
JV-Link host:

```cmd
set JLTSQL_RUN_REAL_INTEGRATION=1
py -3.12-32 -m pytest tests\integration\test_jvlink_real.py -v -s --no-cov
```

The currently release-validated runtime path is 32-bit Python with 32-bit
JV-Link. The x64 path must not be reported as supported until an actual x64 SDK
installation completes the same acquisition and storage workflow.

Standalone Windows E2E scripts are documented in `tests/e2e/README.md`.
Release evidence must use the exact release candidate full SHA, acquire at
least one new provider record, store it through the candidate code, read it
back, and close the JV-Link session cleanly. A mock, reconstructed fixture,
cached replay, or an older SHA is not a substitute.

## Test-writing rules

- For a new or changed validator/gate, first prove that the pre-fix code fails
  a negative case, then retain the paired positive case.
- Fixed-width provider records are byte-oriented CP932 records. Do not build a
  positive fixture with a short body, space padding in place of CRLF, or a
  database-row reconstruction presented as provider raw data.
- Use a dedicated `--basetemp` for concurrent runs.
- Keep credentials, runtime identities, raw payloads, and provider filenames
  out of test output and tracked evidence.

## References

- [JV-Data specification 4.9.0.1](https://jra-van.jp/dlb/sdv/sdk/JV-Data4901.pdf)
- [pytest documentation](https://docs.pytest.org/)
- [Project README](../README.md)
