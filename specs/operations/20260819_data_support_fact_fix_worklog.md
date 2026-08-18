# data_support fact fix (quickstart standard/full, 0B51 key) — 2026-08-19

Base: `origin/master` = `008b97c0e559474eda8888db91f3356f016f3b7b`
(PR #218, the fact-preserving restructure). This iteration changes facts, so it
is a separate PR by design.

## Scope

Two of the 要確認事項 recorded in
`specs/operations/20260818_data_support_readability_worklog.md` were adjudicated
against the official specifications and are corrected here. The other items in
that list are unchanged.

## Sources used

Official documents (primary, version 4.8 and later):

- `JV-Data4901.pdf` (JV-Data 仕様書 4.9.0.1)
- `JV-Data4802.pdf` (JV-Data 仕様書 4.8.0.2)
- `JV-Link4901.pdf` (JV-Link 仕様書 4.9.0.1)

Implementation (secondary): `scripts/quickstart.py`, `src/jvlink/constants.py`,
`scripts/daily_update.py`.

## Item 1 — quickstart `standard` / `full` (doc was wrong)

`scripts/quickstart.py` defines `STANDARD_SPECS` and `FULL_SPECS` as identical
lists: `TOKU, RACE, DIFN, BLDN, MING, SLOP, WOOD, YSCH, HOSN, HOYU, COMM`
(all with the same option values). `MING` and `COMM` are in both. The two modes
therefore request the same データ種別; the in-code note 「フルモード: 標準 +
オッズ」 holds only because `O1`–`O6` are record types inside `RACE`, so `full`
adds no データ種別.

The page claimed `MING` and `COMM` are 「full quickstart に含めています」, i.e.
that they are full-only. Corrected to 「standard / full quickstart に含めて
います」 and one sentence added next to the JVOpen table stating that the two
mode lists are identical and why `full` adds nothing.

Maintainer decision (2026-08-19): accept that `standard` and `full` are
equivalent; do not change the implementation to create a distinction. This PR
is documentation only.

## Item 2 — `0B51` request key (doc was misleading)

JV-Link 4.9.0.1 defines `JVRTOpen` key formats for three units only:
race (`YYYYMMDDJJKKHHRR` / `YYYYMMDDJJRR`), day (`YYYYMMDD`), and
change-information (the values returned by the watch event). JV-Data 4.9.0.1
lists `0B51` as 速報重勝式(WIN5) with 提供単位 「重勝式開催毎」, but no separate
key syntax is defined for that unit anywhere in the inspected official material.
The implementation issues the 8-digit date form (`src/jvlink/constants.py`,
`scripts/daily_update.py`).

The page's 「`YYYYMMDD` または WIN5 開催キー」 reads as if a second, distinct key
syntax existed. Corrected to `YYYYMMDD`. The 提供単位 itself is unchanged
elsewhere on the page.

## Items kept unchanged

- 2023-08 field widths (繁殖登録番号 8→10, 生産者コード 6→8, 生産者名(法人格無)
  70→72, and the producer/breeding master equivalents): confirmed by the
  2023-08-08 change history in the official JV-Data 仕様書. The page is correct;
  no edit.
- UM replacement-key verification missing on native `NL_UM`: an implementation
  gap, not a documentation error. Handled in its own red-first iteration; the
  documentation is not weakened here to match the current behaviour.

## Gates

- `mkdocs build --strict` — pass (anchor validation enabled, 0 warnings)
- `scripts/validate_test_gate.py` — `TEST GATE PASS`
- `tests/test_public_setup_contract.py tests/test_quickstart_cli.py` — 60 passed
- `uv lock --check` — pass
- `git diff --check` — clean
