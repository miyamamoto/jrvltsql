# jrvltsql v1.6.1 Release Notes

## Highlights

- Added daily collection for MING, date-keyed weather updates, and WIN5.
- Corrected RA/SE extended layouts and rejected malformed records fail-closed.
- Updated WF/WIN5 to the official 7,215-byte layout, preserving five active-vote
  counts and all 243 payout entries.
- Made each single-backend realtime polling cycle transactional. Production
  collectors should write directly to PostgreSQL; legacy dual mode remains a
  best-effort migration mirror and is not a distributed transaction.
- Distinguished date-keyed 0B14 from event-keyed 0B16 requests.
- Replaced each successful 0B14 date snapshot so withdrawn weather, scratch,
  jockey, post-time, and course changes do not remain as stale rows.

## Upgrade Notes

- Startup schema migration adds the new `NL_WF` / `RT_WF` columns. Existing
  legacy WF scalar columns may remain as unused extra columns.
- Docker/Wine runtime changes are not part of this repository release.
