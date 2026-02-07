# Tasks: 地方競馬データ対応（UmaConn連携）

**Input**: Design documents from `/specs/001-local-racing-support/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in specification. Test tasks omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths based on plan.md structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new module structure and foundational entities

- [x] T001 Create nvlink module directory structure at src/nvlink/
- [x] T002 [P] Create DataSource enum in src/utils/data_source.py with JRA, NAR, ALL values
- [x] T003 [P] Create NAR track codes constants in src/nvlink/constants.py

**Checkpoint**: Basic structure ready for wrapper implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core NVLinkWrapper that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create NVLinkWrapper class in src/nvlink/wrapper.py mirroring JVLinkWrapper interface
- [x] T005 Implement nv_init() method in src/nvlink/wrapper.py
- [x] T006 Implement nv_open() method in src/nvlink/wrapper.py
- [x] T007 Implement nv_read() and nv_gets() methods in src/nvlink/wrapper.py
- [x] T008 Implement nv_close() method in src/nvlink/wrapper.py
- [x] T009 Implement nv_rt_open() method in src/nvlink/wrapper.py
- [x] T010 Create NVLinkError exception class in src/nvlink/wrapper.py
- [x] T011 Add UmaConn-specific error messages (Japanese) in src/nvlink/wrapper.py
- [x] T012 Export NVLinkWrapper and constants in src/nvlink/__init__.py

**Checkpoint**: Foundation ready - NVLinkWrapper complete and can communicate with UmaConn COM API

---

## Phase 3: User Story 1 - 地方競馬データの蓄積インポート (Priority: P1) 🎯 MVP

**Goal**: Enable historical data import from UmaConn to database with NAR table suffix

**Independent Test**: Run `jltsql fetch --source nar --spec RACE` and verify data appears in NL_RA_NAR table

### Implementation for User Story 1

- [x] T013 [P] [US1] Create NAR schema definitions in src/database/schema_nar.py (copy from schema.py with _NAR suffix)
- [x] T014 [P] [US1] Add NAR table mappings in src/database/table_mappings.py
- [x] T015 [US1] Modify importer to support DataSource-based table name generation in src/importer/importer.py
- [x] T016 [US1] Update historical fetcher to accept DataSource parameter in src/fetcher/historical.py
- [x] T017 [US1] Add wrapper selection logic based on DataSource in src/fetcher/historical.py
- [x] T018 [US1] Add --source option to fetch command in src/cli/main.py
- [x] T019 [US1] Implement UmaConn unavailable error handling with clear message in src/cli/main.py

**Checkpoint**: User Story 1 complete - `jltsql fetch --source nar` works and stores data in _NAR tables

---

## Phase 4: User Story 2 - 統一されたCLIインターフェース (Priority: P2)

**Goal**: Unified CLI with --source option for all commands, maintaining backward compatibility

**Independent Test**: Run `jltsql status --source all` and verify both JRA and NAR status displayed

### Implementation for User Story 2

- [x] T020 [P] [US2] Add --source option to status command in src/cli/main.py
- [x] T021 [P] [US2] Implement JRA+NAR combined status output for --source all in src/cli/main.py
- [x] T022 [US2] Add --source option to version command showing both data sources in src/cli/main.py
- [x] T023 [US2] Ensure --source defaults to jra for backward compatibility in src/cli/main.py
- [x] T024 [US2] Update CLI help text in Japanese for --source option in src/cli/main.py

**Checkpoint**: User Story 2 complete - all CLI commands support --source option with jra default

---

## Phase 5: User Story 3 - 地方競馬リアルタイムデータ取得 (Priority: P3)

**Goal**: Real-time NAR data monitoring via `jltsql monitor --source nar`

**Independent Test**: Run `jltsql monitor --source nar` on race day and verify real-time odds updates

### Implementation for User Story 3

- [x] T025 [P] [US3] Update realtime fetcher to accept DataSource parameter in src/fetcher/realtime.py
- [x] T026 [US3] Add wrapper selection logic based on DataSource in src/fetcher/realtime.py
- [x] T027 [US3] Add --source option to monitor command in src/cli/main.py
- [x] T028 [US3] Ensure RT_*_NAR tables are created for realtime NAR data in src/database/schema_nar.py
- [x] T029 [US3] Update monitor display to show NAR track names in src/cli/main.py

**Checkpoint**: User Story 3 complete - real-time NAR monitoring works

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates and validation

- [x] T030 [P] Update README.md with NAR support documentation
- [x] T031 [P] Add NAR examples to existing CLI help
- [x] T032 Run quickstart.md validation scenarios manually
- [x] T033 Verify backward compatibility (existing JRA commands work unchanged)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Can run parallel with US1
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Depends on US1 for schema_nar.py RT tables

### Within Each User Story

- Schema/models before services
- Services before CLI commands
- Core implementation before error handling
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003 can run in parallel (different files)
- T013, T014 can run in parallel (different files)
- T020, T021 can run in parallel (different areas of same file but no conflicts)
- T025 can run parallel with US1/US2 tasks (different file)
- T030, T031 can run in parallel (different files)

---

## Parallel Example: User Story 1

```bash
# Launch schema and mapping tasks together:
Task: "Create NAR schema definitions in src/database/schema_nar.py"
Task: "Add NAR table mappings in src/database/table_mappings.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T012)
3. Complete Phase 3: User Story 1 (T013-T019)
4. **STOP and VALIDATE**: Test `jltsql fetch --source nar --spec RACE`
5. Deploy if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy (MVP!)
3. Add User Story 2 → Test independently → Deploy
4. Add User Story 3 → Test independently → Deploy
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
3. After US1 schema_nar.py complete:
   - Developer C: User Story 3
4. Stories complete and integrate independently

---

## Key Files Modified/Created

### New Files (9 files)

| File | Purpose |
|------|---------|
| src/nvlink/__init__.py | Module exports |
| src/nvlink/wrapper.py | NVLinkWrapper class (core) |
| src/nvlink/constants.py | NAR track codes |
| src/utils/data_source.py | DataSource enum |
| src/database/schema_nar.py | NAR table schemas |

### Modified Files (5 files)

| File | Changes |
|------|---------|
| src/cli/main.py | Add --source option to all commands |
| src/database/table_mappings.py | Add NAR table mappings |
| src/fetcher/historical.py | Support DataSource selection |
| src/fetcher/realtime.py | Support DataSource selection |
| src/importer/importer.py | NAR table name generation |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Parsers (38 types) are reused unchanged - no parser tasks needed
- All schemas are identical to JRA, only table names differ
