# Real JV-Link integration tests

`test_jvlink_real.py` uses the real JV-Link API and verifies connection,
provider acquisition, parsing, SQLite import, and readback. These tests are
never enabled implicitly.

## Requirements

- GUI-capable Windows environment
- Python 3.12 or later
- Installed JV-Link and active JRA-VAN DataLab subscription
- Service key configured through the normal JRA-VAN DataLab/JV-Link settings

The release-validated path is 32-bit Python with 32-bit JV-Link. An x64 run is
release evidence only after an actual x64 SDK installation completes the full
acquisition and storage test; architecture matching alone is not proof.

## Run

From the exact candidate checkout:

```cmd
set JLTSQL_RUN_REAL_INTEGRATION=1
py -3.12-32 -m pytest tests\integration\test_jvlink_real.py -v -s --no-cov --basetemp=.pytest-tmp-real
```

Without `JLTSQL_RUN_REAL_INTEGRATION=1`, every test in this directory is
skipped. The opt-in flag prevents an ordinary local or CI run from making
authenticated provider calls.

## Covered paths

- `test_jvlink_connection`: constructs the production fetcher and initializes
  JV-Link.
- `test_fetch_small_data_sample`: reads and parses a bounded RACE sample.
- `test_full_workflow_with_real_data`: fetches RACE data through
  `BatchProcessor`, stores it in a temporary SQLite database, and requires
  non-empty `NL_RA` and `NL_SE` readback.
- `test_parser_with_real_data_formats`: checks required record headers in a
  bounded real sample.
- error tests cover invalid and future date requests.

The test currently selects a recent date. If that date has no JRA meeting, the
release harness must choose a bounded known meeting date rather than accepting
a no-data result as green.

## Evidence and safety

- Record the exact 40-character candidate SHA and sanitized counts/status.
- Do not print the service key, raw record payload, provider filename, race
  identity, local account/path, or runtime identity.
- Always observe `JVClose`; abort if another collector owns the runtime.
- A cached record, synthetic fixture, or result from another SHA does not prove
  fresh acquisition.
- Use a temporary database and verify inserted rows with SQL before cleanup.
