# jrvltsql v1.6.2 Release Notes

## Highlights

- Preserved `DataKubun=9` as a cancellation state only for RA/SE/WF while
  restoring physical deletion semantics for odds, vote, and other records.
- Rejects an entire 0B14 snapshot before replacement when any source record
  fails to parse.
- Keeps background realtime polling alive after transient JV-Link or database
  failures.
- Resets historical and realtime fetch statistics for each spec/key response.
- Prepares realtime schemas once per background-updater lifetime instead of
  repeating full schema work for every spec and polling cycle.

## Upgrade Notes

- This is a compatible reliability patch for v1.6.1 data layouts.
- Docker/Wine runtime changes are not part of this repository release.
