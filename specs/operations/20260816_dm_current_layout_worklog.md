# DM current-layout compatibility worklog

## Objective and minimum scope

- Bring jrvltsql's `DM` parser and both accumulated/realtime persistence paths
  into exact agreement with the official JV-Data physical contract.
- Re-audit both the older and current official specification generations before
  choosing compatibility behavior. Do not infer a legacy format from the
  repository's current 48-byte truncation.
- Preserve every official horse entry without weakening record-length,
  record-type, delimiter, primary-key, transaction, or migration checks.
- Keep this iteration limited to `DM`; the remaining official-layout gaps and
  the later documentation/privacy/package/release work stay in separate PRs.

## Repository and version identity

- Repository: `miyamamoto/jrvltsql`
- Dedicated worktree:
  `/home/keiba/scratch/20260816_jrvltsql_dm_layout`
- Branch: `agent/dm-current-layout-20260816`
- Base and initial HEAD:
  `7d360f34f6590100ab816af99474344b69295450`
- Initial `origin/master`:
  `7d360f34f6590100ab816af99474344b69295450`
- Latest published tag at start: `v1.6.10`
- Production/release status: this branch is an unreleased candidate. The final
  jrvltsql release remains downstream of all official-layout iterations and a
  fresh live-provider acquisition-to-database validation on final merged code.

## Dependency order

1. PR #179 (`CH`) was merged first as
   `7d360f34f6590100ab816af99474344b69295450`.
2. This `DM` iteration starts from that merge SHA and must merge before the next
   official-layout iteration starts.
3. Documentation/privacy/package cleanup, jrvltsql release, jrvltsql-nar work,
   and jvlink-mcp-server work remain later dependent iterations.

## Initial observed state

- The tracked compatibility audit records official `DM` length 303 and marks
  the implementation partial because its public length is 48 and it reads only
  one of 18 horse entries.
- `src/parser/dm_parser.py` currently declares `RECORD_LENGTH = 48`, accepts
  short input, and treats bytes 47-48 as the delimiter.
- Existing native tables already use one row per horse and include `Umaban` in
  the primary key. Standard-name schema and importer behavior still require
  independent inspection before an implementation decision.
- Official source material available for this iteration includes JV-Data
  4.8.0.2, JV-Data 4.9.0.1, and SDK 5.0.0 structure definitions. Exact offsets,
  generation differences, blank-entry behavior, and delimiter placement have
  not yet been fixed in this worklog.

## Official and community re-audit

- JV-Data 4.8.0.2 and 4.9.0.1 have the same DM contract. Both specify one
  303-byte physical record: bytes 1-11 header, bytes 12-27 race identity,
  bytes 28-31 `MakeHM`, 18 repeated 15-byte horse entries beginning at byte 32,
  and CR/LF at bytes 302-303. Each horse entry is `Umaban` 2,
  `DMTime` 5, `DMGosaP` 4, and `DMGosaM` 4 bytes.
- SDK 5.0.0 independently agrees in its C++, C#, and Python structures. The C#
  implementation allocates a 303-byte buffer and iterates
  `32 + (15 * i)` for all 18 `DMInfo` entries; the Python implementation uses
  the same one-based offsets and reads the delimiter from byte 302.
- No old/current DM physical-layout split appears between the two audited
  official generations. The 48-byte repository shape is exactly the 31-byte
  header plus one 15-byte entry plus CR/LF, so it is a truncated reconstruction,
  not a documented legacy JV-Data record. It must be rejected rather than
  treated as backwards compatibility.
- The official change history records naming/format-number changes around
  versions 4.0/4.1.1, but no 48-to-303 layout transition. The older 4.8.0.2
  workbook already carries the same 303-byte/18-entry definition as 4.9.0.1.
- The official developer community confirms that accumulated DM/TM are obtained
  through `MING`, realtime DM through `0B13`, and that accumulated and realtime
  prediction content is the same:
  <https://developer.jra-van.jp/t/topic/284> and
  <https://developer.jra-van.jp/t/topic/286>.
- Community correction history is operationally relevant. JRA-VAN support
  states that `DataKubun=3` and `DataKubun=7` should not change the prediction,
  but documented erroneous source rows were later corrected. Therefore storage
  must upsert a complete race revision rather than preserve only the first horse:
  <https://developer.jra-van.jp/t/topic/95>.
- A 2026 community clarification states that DataLab DM is the official
  predicted finishing time, while the consumer app may show a derived score.
  This implementation must preserve the five-byte JV-Data time and must not
  attempt the unpublished score conversion:
  <https://developer.jra-van.jp/t/topic/856>.

## Storage-path findings and decision

- Native `NL_DM` and `RT_DM` are already keyed per horse. They should receive
  one logical row for every populated entry in the 303-byte record.
- The repository's JRA-VAN standard schema already defines the official wide
  table `MINING` with 18 numbered entry groups, but reverse mapping currently
  points `NL_DM` to the non-schema alias `DATA_MASTER`. Canonical standard mode
  must target one wide `MINING` row per race.
- `MINING` currently lacks a primary key. Safe correction/upsert requires the
  six-field race identity key. Existing keyless tables cannot be made safe by
  silent append behavior and must be rejected for operator rebuild.
- Expanded-parser metadata can follow the established WH design: emit native
  horse rows carrying one shared `_wide_record`; ordinary and optimized
  importers deduplicate that physical record only when targeting `MINING`.
- Official `DataKubun=0` deletes the whole physical race record. A blank horse
  array therefore must retain only race identity and delete all matching
  `NL_DM`/`RT_DM` rows (or the one `MINING` row); it must not fail open because
  `Umaban` is absent.

## Validation and review policy

- Codex-only implementation and review; do not use Claude Code.
- If a validator, migration gate, or fail-closed check changes, add the minimum
  paired failing/passing regression first and run it against the old code to
  record the actual red result.
- Validate the final immutable full SHA with focused and full suites, both
  supported Python generations, disposable PostgreSQL coverage where storage
  behavior is affected, critical lint/compile/static checks, and one aggregated
  exact-SHA Codex review.
- Do not merge on a failed executable check, unresolved actionable finding,
  unresolved review thread, base/head drift, or dirty worktree.

## Next safe commands

1. Extract the `DM` definition from official 4.8.0.2, 4.9.0.1, and SDK 5.0.0
   sources and compare the complete byte layout.
2. Inspect native and standard schemas, both importers, realtime updater, and
   existing fixtures to decide whether one 303-byte physical record should be
   expanded into up to 18 logical rows on all paths.
3. Recheck official/community notices for any documented DM layout transition.
4. Add the smallest official-contract tests, run them on this base SHA, and
   stop unless the intended regression is demonstrably red.

## STOP conditions

- Official generations disagree in a way that cannot be distinguished safely
  from the record itself.
- Standard-name storage requires a destructive or ambiguous migration not
  bounded to the DM tables.
- A test failure reveals coupling outside the stated DM scope.
- Credentials or a remote state change would be required before the local
  contract can be established.
