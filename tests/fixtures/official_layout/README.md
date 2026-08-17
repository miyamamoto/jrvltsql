# Official layout oracle fixtures

These JSON files contain derived layout facts and change-history references for
JV-Data. They do not contain provider records or a copy of the SDK source.

- `jvdata_sdk500_manifest.json` was generated from the Python structure file
  included with JRA-VAN Data Lab. SDK 5.0.0. Its `source.sha256` identifies the
  exact local source artifact used by the maintainer.
- `jvdata_layout_history.json` records physical-length and same-length semantic
  changes cited by the official 4.8.0.2 and 4.9.0.1 specification workbooks.
- `jvdata_status_domain.json` records all 38 current DataKubun domains, the
  three explicit accumulated/realtime differences, and date-bounded historical
  values cited by the official 4.9.0.1 format and change-history sheets. Its
  `current_accumulated` object is the base parser/import validation context; it
  does not claim that all 38 formats are available from an accumulated-data
  provider call.

The manifest is intentionally independent of jrvltsql parser and schema code.
When the official source changes, regenerate it from a separately obtained SDK
file and review the resulting diff before updating parser or storage contracts:

```console
python scripts/official_jvdata_oracle.py generate \
  --source /path/to/JVData_Struct.py \
  --output tests/fixtures/official_layout/jvdata_sdk500_manifest.json \
  --jvdata-version 4.9.0.1
python scripts/official_jvdata_oracle.py validate \
  --manifest tests/fixtures/official_layout/jvdata_sdk500_manifest.json
```

The reconstructed binary fixtures elsewhere under `tests/fixtures` serve only
as parser value regressions. They are not official-layout evidence.
