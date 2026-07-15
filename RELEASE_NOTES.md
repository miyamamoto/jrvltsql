# jrvltsql v1.6.4 Release Notes

## Highlights

- Treats Wine bridge subscription responses as normal optional-spec skips in
  the non-interactive daily collector path.
- Prevents an unsubscribed 0B14 or 0B51 feed from aborting collection of other
  configured feeds.

## Upgrade Notes

- This is a compatible reliability patch for v1.6.3 data layouts.
- Docker/Wine runtime changes are not part of this repository release.
