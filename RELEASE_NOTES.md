# jrvltsql v1.6.8 Release Notes

## Highlights

- Adds canonical numeric JRA SE columns for race time, final 3F, body weight,
  body-weight change, finish position, and horse number while preserving the
  official raw fixed-width fields unchanged.
- Applies the new columns through additive SQLite/PostgreSQL migrations and
  verifies both schema keys and representative official record conversions.

- Treats `JVRead -2` as a read failure rather than no data, preventing partial
  realtime and historical responses from being committed.
- Rejects every realtime stream that exits before the official completion
  code, including positive-length reads with an empty buffer, so an incomplete
  0B14 response cannot replace a valid stored snapshot.
- Migrates dual SQLite/PostgreSQL schemas against each concrete backend, using
  backend-specific table identifiers and verifying both copies before import.
- Preserves best-effort dual-mode availability by excluding an unavailable
  secondary mirror from migration while still validating connected mirrors.

- Treats Wine bridge subscription responses as normal optional-spec skips in
  the non-interactive daily collector path.
- Prevents an unsubscribed 0B14 or 0B51 feed from aborting collection of other
  configured feeds.

## Upgrade Notes

- This is a compatible reliability patch for v1.6.3 data layouts.
- Docker/Wine runtime changes are not part of this repository release.
