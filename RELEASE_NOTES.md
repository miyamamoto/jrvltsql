# jrvltsql v1.6.3 Release Notes

## Highlights

- Treats `JVLinkBridgeError` subscription and busy responses the same as the
  native JV-Link exceptions.
- Prevents an optional unsubscribed realtime spec under Wine from rolling back
  valid rows collected by other specs in the same polling cycle.
- Rejects 0B14 snapshot replacement after recoverable JVRead transport errors.
- Reports the realtime monitor as stopped when Wine bridge initialization fails.

## Upgrade Notes

- This is a compatible reliability patch for v1.6.2 data layouts.
- Docker/Wine runtime changes are not part of this repository release.
