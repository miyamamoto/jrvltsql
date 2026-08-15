# SK current-layout compatibility worklog

## Iteration identity

- Started: 2026-08-15 JST
- Objective: reconcile the `SK` foal master parser and storage contract with
  the official pre-2023 and current JV-Data definitions, including all 14
  three-generation pedigree registration numbers.
- Minimum scope: `SK` parser, directly coupled native/standard schemas and
  importer mappings, exact current-layout acceptance, old-layout rejection,
  gap-free byte-offset tests, migration guidance, and compatibility audit.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260815_jrvltsql_sk_layout`
- Branch: `agent/sk-current-layout-20260815`
- Base / initial HEAD / `origin/master` full SHA:
  `6dc55078dba33a7f4582d67e816276c25be2700e`
- Previous iteration: PR #172 merged at the base SHA; its final candidate was
  `72a7c33d24efeb95ce0ceb2524264b3e3e1d5512`.
- Implementer: Codex. Review will use Codex reviewers; Claude Code is not used
  because the user explicitly requested continued Codex review.
- Applied workflow: `kps-jra-nar-release-readiness`, limited to JRA parser
  data-integrity audit, batched focused tests, exact-SHA review, and PR gates.

## Initial decision boundary

- Compare official 4.8.0.2, 4.9.0.1, and current SDK 5.0.0 definitions before
  changing code. Record the complete field sequence, physical lengths, and the
  2023 width changes rather than inferring them from the current parser.
- Determine whether historical compatibility is provider-normalized current
  shape or a true dual physical-layout contract. Do not silently parse 178-byte
  and 208-byte records through one set of offsets.
- Add the smallest exact-layout regression contract before production changes
  and run it against the base to prove the partial parser and fail-open layout
  gate are observable failures.
- Stop before merge if any current field/array item is dropped, old records are
  ambiguously accepted, schemas cannot store every official value, either
  importer loses data, tests fail, review findings remain, or PR threads are
  unresolved.

## Official and community evidence

- Official 4.8.0.2 workbook SHA-256:
  `6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7`.
  Its SK definition is 178 bytes: `BreederCode=39/6`, `SanchiName=45/20`,
  fourteen 8-byte pedigree numbers from position 65, and CRLF at 177/2.
- Official 4.9.0.1 workbook SHA-256:
  `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`.
  The change history expands `BreederCode` from 6 to 8 bytes and all fourteen
  three-generation breeding registration numbers from 8 to 10 bytes. The
  resulting current record is 208 bytes: `BreederCode=39/8`,
  `SanchiName=47/20`, pedigree slots at `67 + 10*i` for `i=0..13`, and CRLF at
  207/2.
- SDK 5.0.0 archive SHA-256 is
  `21f4d54706ff050e383f21f3571f59ffe8de38ed46a01be3e5b7756ee957f9d7`;
  its Python `JVData_Struct.py` SHA-256 is
  `8994f985fce846f1b4fcbc3ddf2a5c6394c586a458478346891222b3b61e4ee3`.
  `JV_SK_SANKU.SetDataB` retains the same 208-byte layout and 14-item loop.
- Official developer-community staff topics 215 and 221 say the N-suffixed
  current setup converts historical data to current widths and advise against
  mixing old/current stores. This iteration therefore follows the existing
  current-only product policy: accept exactly 208-byte physical SK records and
  reject the complete 178-byte legacy layout.

## Base audit and red proof

- The base parser declares 78 bytes, parses only the current basic prefix plus
  `FNum`, treats bytes 77-78 as a delimiter, warns but continues on short data,
  and accepts arbitrary longer data. Thirteen pedigree values are dropped, and
  a complete official 178-byte legacy record is misread as if current.
- Native `NL_SK` only stores `FNum`. Standard `SANKU` omits `KettoNum`,
  `MMMNum`, and its primary key. The reverse table mapping points SK imports to
  legacy `HANSYOKU_UMA`, for which no standard schema exists, so standard-name
  SK import cannot succeed.
- Added the current gap-free sentinel and legacy/storage counterexamples before
  production changes. Four selected tests failed against the base, exit 1:
  parser length was 78 instead of 208; `MMMNum` was absent; the complete
  official legacy 178-byte record returned a corrupt dictionary instead of
  `None`; and the official `SANKU` mapping was absent.

## Implemented candidate

- `SKParser` now accepts only an exact 208-byte current physical record with
  CRLF at bytes 207-208 and parses all fourteen 10-byte pedigree registration
  numbers. Exact short, long, bad-delimiter, and complete official 178-byte
  legacy records fail closed.
- Native `NL_SK` now stores all fourteen numbers. Standard `SANKU` now includes
  `KettoNum`, the previously missing final pedigree number, and a primary key.
  The official `SANKU` mapping is present while the historical alias remains a
  compatible input mapping.
- Both regular and optimized importers have SQLite round-trip coverage in
  native and standard naming modes. A pre-existing keyless standard table is
  rejected rather than being silently treated as migration-compatible.
- The reconstructed historical 78-byte test fixture is padded into a clearly
  documented synthetic current-shape core-field record. It is not used as
  evidence for an official raw layout.

## Validation performed before candidate commit

- Dedicated contract: `43 passed`.
- Focused parser/schema/migration/importer/mapping set: `818 passed, 1 skipped`.
- First full suite: `1953 passed, 47 skipped`, with the two known order-sensitive
  CLI version/status failures; both passed in isolation. A clean second full
  run then completed at `1955 passed, 47 skipped, 5 subtests passed`.
- Built both wheel and sdist with `uv build` into an external scratch directory.
  The wheel had 95 entries and the sdist 176 entries; both contained zero
  `specs/` entries. Generated build directories in this worktree were moved to
  trash after inspection.

## Migration and operating note

- Existing native `NL_SK` tables can receive the new nullable columns through
  additive migration, but old rows contain only `FNum`; restoring the other
  thirteen values requires reimporting current-shape source records.
- Existing standard `SANKU` tables without `KettoNum` and its primary key must
  be rebuilt before import. Treating that incompatible table as usable would
  make distinct foals collide or become unaddressable.

## Current state and next safe commands

1. Run formatting, critical lint, and diff checks over the completed batch.
2. Commit once, record the full candidate SHA, and rerun the affected workflow
   tests against that exact SHA.
3. Gather the required Codex reviews in one batch, resolve all actionable
   findings together, then push and complete PR gates.

## Queued follow-up outside this iteration

- After this SK iteration is merged, start a separate latest-master worktree
  and PR for the user's public-documentation cleanup request.
- Remove references to the specified internal collector identifier and to the
  private runtime implementation, delete `docs/crawler_audit_01_mining_spec.md`,
  `docs/crawler_audit_02_ra_extended_layout.md`,
  `docs/crawler_audit_03_we_realtime_spec.md`, and
  `docs/crawler_audit_04_se_layout.md`, then audit all tracked references so no
  broken links or equivalent disclosures remain.
- Keep the tracked `specs/` directory as the repository's audit and handoff
  record. It is intentionally absent from both wheel and sdist distributions;
  verify this again from the final release artifacts.
- After that cleanup is merged, re-audit all public documentation, examples,
  links, packaging, and release metadata. Reconcile every known
  release-blocking implementation finding from the canonical compatibility
  audit; documentation cleanup must not substitute for fixing parser/storage
  behavior. Only after those fixes are merged and latest-master full-SHA tests,
  reviews, and the public-information audit are green, prepare and publish the
  next repository release using the existing versioning convention.
