# jrvltsql v1.6.1 Release Notes

## Summary

- Fixed the non-interactive JRA daily sync path so training data is refreshed every day.
- Added `SLOP` and `WOOD` to the default `JRA_DAILY_UPDATE_SPECS` used by `daily_sync.bat`.
- Kept this public release scoped to the core Windows/JRA collector. Docker/Wine runtime work is not included.

## Impact

Before this release, `SLOP` / `NL_HC` and `WOOD` / `NL_WC` were fetched during initial setup but were not included in the non-interactive daily incremental path. Scheduled daily updates could therefore leave training-derived fields stale after setup.

After upgrading, the default scheduled daily sync fetches:

```text
RACE,DIFN,SLOP,WOOD,0B12,0B15
```

Existing users who override `JRA_DAILY_UPDATE_SPECS` should add `SLOP,WOOD` to their environment if they want the same behavior.

## Validation

- GitHub Actions on PR #127: `lint` passed, `test` passed, `performance-test` skipped by workflow policy.
- Local focused tests: `uv run pytest tests/test_daily_update.py tests/test_quickstart_cli.py -q` passed with 41 tests.
- JRA readiness scan: target `jra`, 54 pass, 2 warnings for unrelated KPS working-tree/cache state.

## Migration Notes

- No database schema migration is required.
- No service key or JV-Link registration change is required.
- Rollback: return to `v1.6.0` or remove `SLOP,WOOD` from `JRA_DAILY_UPDATE_SPECS`.
