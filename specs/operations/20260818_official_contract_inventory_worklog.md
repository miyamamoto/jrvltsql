# Official-contract inventory worklog

## Start state (2026-08-18)

- Objective: map all 38 current JV-Data record types to their official oracle,
  parser, native/standard/realtime storage, red-first tests, merged PRs, and
  tracked worklogs, then identify the exact remaining implementation
  iterations before the `2.0.0.dev0` prerelease.
- Minimal scope: inventory and decision record only. Do not modify production
  parser/storage behavior in this iteration, and do not assume that a file
  named `test_*_official_contract.py` alone proves full contract completion.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_contract_inventory`.
- Branch: `agent/official-contract-inventory-20260818`.
- Base and starting HEAD: `b13aba1e3b5eb397b7147c3087d5e6544168967b`
  (`origin/master`, CC PR #215 squash merge).
- Package version: `2.0.0.dev0`; no prerelease tag/release has been created.
- Working tree was clean at creation.

## Inventory method

1. Use the pinned 38-record status-domain fixture as the record-type universe.
2. For every type, bind the current official workbook/SDK layout evidence to
   executable parser spans and identify current/historical status policy.
3. Inspect native, standard, and realtime schemas/mappings, exact keys,
   physical erase or snapshot semantics, caller validation, migration
   fail-closed behavior, and provider ordering.
4. Distinguish a fully merged contract iteration from partial parser-layout,
   status-only, or storage-only work. Record the supporting PR/merge SHA and
   the strongest relevant test rather than inferring completion from filenames.
5. Produce one concrete remaining-order list. Each remaining logical family
   will be a separate later PR with its own red-first test, backend evidence,
   independent review, GitHub checks, thread-zero gate, and merge.

## Known starting facts

- Dedicated `test_*_official_contract.py` modules exist for 27 record types.
- The 11 types without that exact filename pattern are `H1`, `H6`, `HN`,
  `O1`-`O6`, `SK`, and `UM`; several have prior merged parser/storage PRs or
  differently named tests, so this is a review queue, not yet a finding list.
- Relevant earlier merges include HN #172, SK #175, H1/H6 #190, UM #204, and
  the just-merged CC #215. Their actual end-to-end contract coverage must still
  be verified against the same inventory columns.

## Complete dedicated-contract baseline

The following 27 types have a merged dedicated official-contract iteration.
The merge commit and executable contract module are the evidence boundary;
this inventory does not reinterpret a filename alone as proof.

| Type | PR | Merge full SHA | Strongest contract module | Classification |
|---|---:|---|---|---|
| AV | #210 | `c748da1b0ff9d3c39a1ab455112b9561b6343f39` | `tests/test_av_official_contract.py` | complete baseline |
| BN | #177 | `19954206bc8f282f535e505a44b2f81023bbfd96` | `tests/test_bn_official_contract.py` | complete baseline |
| BR | #178 | `e54991eb02f5fbee8c4e561bf1f54adb9be255ac` | `tests/test_br_official_contract.py` | complete baseline |
| BT | #198 | `a53eed6c24cbb4cbb8ebc0edc845ae67849b76b2` | `tests/test_bt_official_contract.py` | complete baseline |
| CC | #215 | `b13aba1e3b5eb397b7147c3087d5e6544168967b` | `tests/test_cc_official_contract.py` | complete baseline |
| CH | #179 | `7d360f34f6590100ab816af99474344b69295450` | `tests/test_ch_official_contract.py` | complete baseline |
| CK | #196 | `1b66f45629b9ede51fc2f4415e688784b2f55a2c` | `tests/test_ck_official_contract.py` | complete baseline |
| CS | #205 | `0ca68a7c1ab3eb6fe7a40bb60bc2800a5ea16993` | `tests/test_cs_official_contract.py` | complete baseline |
| DM | #180 | `b01a92634056e2bc574c92c257adea89f6b8b271` | `tests/test_dm_official_contract.py` | complete baseline |
| HC | #213 | `282e03a5cba06fdc42d4d651ee7624b27dadad01` | `tests/test_hc_official_contract.py` | complete baseline |
| HR | #211 | `e1fcb810b69c133a3668fe38b8480e31db5e8b27` | `tests/test_hr_official_contract.py` | complete baseline |
| HS | #212 | `ed39ac78aa371e7ce4e18a87d8a25c50a07fe78a` | `tests/test_hs_official_contract.py` | complete baseline |
| HY | #195 | `9f2e2a8c11bae32a76e850c13aa0e112f75ef67a` | `tests/test_hy_official_contract.py` | complete baseline |
| JC | #209 | `a152045c4bf9c6f9c53f483d2f2cfa0baa05dcb7` | `tests/test_jc_official_contract.py` | complete baseline |
| JG | #199 | `b4369f74d2ba236c8b33dbb1e45882ffa7c9aa0f` | `tests/test_jg_official_contract.py` | complete baseline |
| KS | #182 | `79833980f8a7f0cc09c2a308a50a512091e5565b` | `tests/test_ks_official_contract.py` | complete baseline |
| RA | #176 | `05bc415713d8995559debbccc2cb5d520d99b4a9` | `tests/test_ra_official_contract.py` | complete baseline |
| RC | #183 | `609f9c4ee3571857367781f4cc8d7e3630a0e9e0` | `tests/test_rc_official_contract.py` | complete baseline |
| SE | #207 | `2e7aa556ecb5cf6aa1ba190b2f22a2ed67c00a2a` | `tests/test_se_official_contract.py` | complete baseline |
| TC | #214 | `6e9a9f500f2353d7b423e5f1e12b07c30275f8d1` | `tests/test_tc_official_contract.py` | complete baseline |
| TK | #185 | `3fbd5272a3375e3422f47335bc4a98f98c9f6e2b` | `tests/test_tk_official_contract.py` | complete baseline |
| TM | #181 | `888e3cb4d572320512da6da4854c5cc6b66bb37d` | `tests/test_tm_official_contract.py` | complete baseline |
| WC | #200 | `4e052962ca7b3322be7d1025c3151c8d2afcd02a` | `tests/test_wc_official_contract.py` | complete baseline |
| WE | #208 | `074425a220f33e63b053751b96ce1e5e7cdd1f7e` | `tests/test_we_official_contract.py` | complete baseline |
| WF | #201 | `98ec163222aab3eadaa82f048273c8a0be8722e6` | `tests/test_wf_official_contract.py` | complete baseline |
| WH | #167 | `d0b4ad32c0b2ebd01405269375906783e7a99e74` | `tests/test_wh_official_contract.py` | complete baseline |
| YS | #184 | `b62ba13be49c07e034acab1b5a5b483e10eb365a` | `tests/test_ys_official_contract.py` | complete baseline |

This is a release-planning baseline, not a claim that no future defect can be
found. A completed type is reopened only by concrete new official or executable
evidence, rather than by repeatedly replaying the whole review sequence.

## Remaining formats: confirmed gaps

Independent read-only audits on candidate
`c721a293858764cfbf43d364b5a89fbace301e73` confirmed that all 11 queued types
still need bounded closure work.

| Family | Earlier merge | Already closed | Remaining P1 boundary |
|---|---|---|---|
| H1/H6 | #190, `3a2c892649b8e9ec85113a7b0122e7e4d637443b` | official layout and standard owner/child atomic snapshot storage/erase | native and realtime complete-snapshot replacement for statuses 2/4/5/9; exact key/body/value validation; strict native/realtime preflight; coupled Dual evidence; H6 additionally needs an owner/header representation for a valid zero-combination snapshot |
| HN | #172, `6dc55078dba33a7f4582d67e816276c25be2700e` | official 251-byte layout, full native/standard mapping and basic roundtrip | status-0 physical erase/order/stats; exact key/body caller validation; strict native/standard preflight; PostgreSQL/Dual evidence |
| SK | #175, `ff62d65c07b1026e7ea7606b1d6329dbd9768199` | official 208-byte layout, full pedigree mapping and basic roundtrip | status-0 physical erase/order/stats; 10-digit key/body caller validation; strict native/standard preflight; PostgreSQL/Dual evidence |
| UM | #204, `17335604e0f951ae1cc39ebb447c6fb1b7b683be` | official 1609-byte layout, lossless native body, 227-column standard expansion, key and partial UMA constraint checks | status-0 physical erase/order/stats; full body validation; strict native and complete standard schema contract; Dual evidence |
| O1-O6 | #189, `dde898c3394c24c9b781024d959c770ee7add58e` | physical lengths/repeat expansion and standard header/child atomic snapshot storage/erase | retain valid zero-vote combinations and distinguish official sentinels/history; strict key/body and SourceSpec/family validation; native/realtime lossless snapshot/header preservation; strict native/RT/TS preflight |

Concrete reproductions used for the classification:

- H1 native/RT: a full status-4 snapshot followed by a valid empty status-5
  snapshot retained stale child rows and mixed statuses. H6 rejected the valid
  empty replacement and retained the old snapshot. Exactly-sized status-valid
  records with invalid venue/value payload also parsed.
- HN/SK/UM: native/standard `1 -> 2 -> 0` left a status-0 tombstone instead of
  deleting the keyed record in all exercised DataImporter/Optimized paths.
  Header-plus-key caller dictionaries also reported successful imports with the
  required body absent. These accumulated masters intentionally have no RT
  tables; realtime is N/A rather than a missing implementation.
- O1-O6: zero-vote combinations are discarded and native conversion collapses
  distinct hyphen/asterisk sentinels to NULL. The standard split path is
  atomic, but native/RT child-only upsert can retain omitted combinations and
  cannot preserve a header-only O2 record's flags/totals/status. Source-spec
  and record-family combinations are not yet bound fail-closed, and O*
  native/RT/TS schemas lack dedicated preflight.

Existing focused tests remained green (`273 passed, 25 skipped` for the initial
11-type selection and `336 passed, 5 skipped` for the HN/SK/UM audit), showing
that these are missing regression contracts rather than failures already caught
by the suite. The bounded H1/H6 audit was `49 passed, 6 skipped, 71 deselected`;
the O-family positive selection was `21 passed`. PostgreSQL skips in these
read-only audits are not credited as backend closure; each implementation PR
must run its own fresh PostgreSQL and Dual evidence.

A read-only partition check loaded
`tests/fixtures/official_layout/jvdata_status_domain.json` and asserted that the
27 complete-baseline types and 11 remaining types are disjoint and union to the
fixture's exact 38-type universe. Result:
`38-type partition PASS: complete_baseline=27, remaining=11, total=38`.

## Planned closure order

The minimal dependency order is:

1. HN official contract.
2. SK official contract.
3. UM official contract.
4. H1 official snapshot, validation, and strict schema contract.
5. H6 official snapshot, owner/header, validation, and strict schema contract.
6. O1-O6 official truth/parser/provider contract: repeated rows, zero-vote and
   sentinel/history semantics, strict caller validation, and SourceSpec binding.
7. O1-O6 lossless state/storage contract: native NL/RT/TS owner/header model,
   atomic snapshot replacement, raw sentinel preservation, erase/order, strict
   schema preflight, and SQLite/PostgreSQL/Dual proof.

HN, SK, and UM use the same erase/preflight architecture but remain separate
iterations because their official keys, body domains, standard tables, and
migration risks differ. H1 and H6 reuse a snapshot architecture but remain
separate because H6's valid zero-combination state needs a new owner/header
boundary. O1-O6 stay a family because all six share the provider/source and
lossless physical-snapshot rules. Official truth/provider validation is split
from storage migration so that routing, parser semantics, and a multi-table
migration do not form one oversized PR.

After all seven PRs merge, the release iteration will rerun the exact full gate,
build wheel/sdist from the frozen SHA, run isolated installed-wheel smoke, and
publish the `2.0.0.dev0` prerelease. The tracked Devin handoff will then assign
real development-environment install, fresh JV-Link acquisition/storage checks,
and the formal `2.0.0` decision; Codex stops after that handoff.

## Next safe command and STOP conditions

- Next: commit this inventory evidence, run a docs-only independent review on
  that exact full SHA, push a dedicated PR, complete thread-zero/clean gates,
  and merge it. Then fetch the latest `origin/master` and begin the HN official
  contract in a new worktree with its red test first.
- STOP on repository drift, an official-source disagreement, an ambiguous PR
  dependency, or any need to mutate provider/runtime/release state.
- Do not record credentials, connection strings, private provider identifiers,
  or raw secret-bearing logs.
