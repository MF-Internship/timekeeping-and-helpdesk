---

description: "Dependency-ordered implementation tasks for Task Management Core"
---

# Tasks: Task Management Core

**Input**: Design documents from `/specs/007-task-management-core/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/task-api.yaml`, `quickstart.md`

**Tests**: Required by the feature Definition of Done and Constitution Principle
XI. Test tasks precede the behavior they prove, and PostgreSQL is mandatory for
constraints, rollback, and concurrency.

**Organization**: Shared aggregate/port infrastructure is foundational; delivery
then follows the five user stories in specification priority order. Every task
has one verifiable outcome and concrete paths.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Genuinely independent task touching different files and requiring no
  incomplete task.
- **[Story]**: User story traceability label for story phases only.
- Run each phase gate before starting the next phase.

## Phase 1: Setup

**Purpose**: Register the new module in the existing project and establish empty
inward-architecture packages without changing business behavior.

- [X] T001 Create the `tasks` Django app package and empty `domain/`, `application/`, `ports/`, `adapters/api/`, `adapters/persistence/`, and `migrations/` packages in `backend/tasks/`
- [X] T002 Register `tasks` in `backend/config/settings.py` and add `backend/tasks` to the hardcoded mypy/function-length checks in `.github/workflows/quality.yml`
- [X] T003 Extend production module-boundary and maintainability coverage to include `backend/tasks` in `backend/tests/architecture/test_module_boundaries.py` and `backend/tests/architecture/test_maintainability.py`

**Gate 1**: The new empty module imports, Django starts, architecture tests include
it, and no runtime dependency or endpoint has been added.

---

## Phase 2: Foundational Aggregate and Ports

**Purpose**: Build the shared Task vocabulary, persistence schema, ports, and
composition required by every user story.

**⚠️ BLOCKING**: No story implementation starts until this phase passes.

### Tests first

- [X] T004 [P] Add pure domain tests for closed `TaskStatus`/`CompletionMethod`, all canonical transition outcomes, same-state classification, terminal rejection, block-reason normalization, and read-time list projection in `backend/tests/unit/tasks/test_transitions.py` and `backend/tests/unit/tasks/test_projections.py`
- [X] T005 [P] Add model contract tests for Task snapshot shape, nonblank title/reason/note rules, TaskAssignee uniqueness/no-status shape, TaskUpdate completion shape, and required indexes in `backend/tests/unit/tasks/test_model_contract.py`
- [X] T006 [P] Add Task authorization adapter and canonical matrix tests proving MANAGER is ASSIGN-only, HELPDESK is SELF-only, read/update implications remain closed at exactly five pairs, override is exact, inactive/password-change gates hold, and Task code never interprets roles in `backend/tests/unit/tasks/test_authorization_adapter.py` and `backend/tests/unit/identity/test_authorization.py`
- [X] T007 [P] Add PostgreSQL constraint and migration-catalog tests for Task, TaskAssignee, and TaskUpdate in `backend/tests/integration/postgres/tasks/test_task_constraints.py` and `backend/tests/integration/postgres/tasks/test_task_migration.py`

### Foundational implementation

- [X] T008 Implement canonical enums, immutable snapshots, transition decision types, and completion snapshot construction in `backend/tasks/domain/tasks.py` and `backend/tasks/domain/transitions.py`
- [X] T009 Implement server-business-date grouping and derived `overdue_days` with one captured Asia/Ho_Chi_Minh date in `backend/tasks/domain/projections.py`
- [X] T010 Define typed create/read/update/override authorization modes and the Task authorization protocol in `backend/tasks/ports/authorization.py`
- [X] T011 [P] Define typed assignee-eligibility and expected-Location reference protocols, including ascending-ID locked eligibility loading and locked SELF-actor reauthorization inside the caller unit of work, in `backend/tasks/ports/assignees.py` and `backend/tasks/ports/locations.py`
- [X] T012 [P] Define Task repository, clock, and unit-of-work protocols plus command/query DTOs in `backend/tasks/ports/repositories.py`, `backend/tasks/ports/clock.py`, `backend/tasks/ports/unit_of_work.py`, and `backend/tasks/application/dto.py`
- [X] T013 Implement `Task`, `TaskAssignee`, and core `TaskUpdate` models with R-84 snapshot checks, `UNIQUE(task,user)`, `PROTECT` FKs, and list/scope/history indexes in `backend/tasks/models.py`
- [X] T014 Generate and review the expand-only single-leaf migration with explicit constraints, indexes, and database defaults in `backend/tasks/migrations/0001_initial.py`
- [X] T015 Implement ORM repository operations, scoped query predicates, `select_for_update` loading, insert-only TaskUpdate writes, full-set assignee deltas, Django clock, and atomic unit of work in `backend/tasks/adapters/persistence/repositories.py`, `backend/tasks/adapters/clock.py`, and `backend/tasks/adapters/persistence/unit_of_work.py`
- [X] T016 Remove MANAGER's direct `TASK_CREATE_SELF` grant while retaining `TASK_COMPLETE_FIELD`, then implement composition-root adapters that translate exact create and implied read/update grants, lock/revalidate assignee Users, and reauthorize a locked SELF actor without Task cross-module imports in `backend/identity/domain/authorization.py` and `backend/config/task_adapters.py`
- [X] T017 Add only the governed `INACTIVE_ASSIGNEE`, `BLOCK_REASON_REQUIRED`, and `TASK_ALREADY_COMPLETED` codes/messages to `backend/core/error_codes.py` and `backend/core/errors.py`
- [X] T018 Define Task dependencies/container and wire the cached container without API routes in `backend/tasks/application/dependencies.py`, `backend/tasks/application/container.py`, and `backend/config/composition.py`

**Gate 2**: T004–T007 pass; `migration_check.py check`,
`makemigrations --check --dry-run`, Task architecture checks, Ruff, and mypy pass.

---

## Phase 3: User Story 1 — Create and Assign Work (Priority: P1) 🎯 MVP

**Goal**: Manager creates a Task for one or more active HELPDESK users; Helpdesk
creates an arising Task for themselves; optional expected Location and immutable
assigned date are retained.

**Independent Test**: Create one Manager Task with two active assignees and an
expected Location, then one Helpdesk Task without Location; verify creator,
assignees, original date, TODO status, DTO ownership, and atomic failure paths.

### Tests first

- [X] T019 [P] [US1] Add create-service unit tests for Manager ASSIGN normalization/required assignees, Helpdesk SELF sole-assignee authority, optional Location, past/today/future dates, mixed missing/wrong-role/inactive ID aggregation, and rollback on repository failure in `backend/tests/unit/tasks/test_create_service.py`
- [X] T020 [P] [US1] Add create API contract tests for `tasks_create`, role-shaped request ownership, canonical envelopes, and 201 response schema in `backend/tests/contract/tasks/test_task_create_contract.py`
- [X] T021 [P] [US1] Add API integration tests proving RBAC-before-DTO, Manager ASSIGN-only multi-create success, Manager missing-assignee failure, Helpdesk SELF-only success/`assignee_ids` rejection, Leader/anonymous deny, duplicate-ID normalization, all mixed ineligible IDs in one 422, and no partial rows in `backend/tests/integration/api/tasks/test_task_create_api.py`
- [X] T022 [P] [US1] Add real-PostgreSQL atomic-create tests for mixed valid/missing/wrong-role/inactive IDs, duplicate relation protection, full rollback, ASSIGN-versus-deactivation/role-change, and SELF-create-versus-actor-deactivation/role-change in both lock orders with canonical 401/403 outcomes in `backend/tests/integration/postgres/tasks/test_task_create_atomicity.py`

### Implementation

- [X] T023 [US1] Implement `TaskCommandService.create` with exact authorized create mode, SELF actor lock/reauthorization, stable ASSIGN deduplication and ascending-ID User locks/revalidation, R-141/R-142 errors, and one Task/assignee transaction in `backend/tasks/application/commands.py`
- [X] T024 [US1] Implement mode-specific create serializers that reject server-owned fields and serialize minimal Task identity projections `{id, full_name}` plus assignee/Location data without username/account status in `backend/tasks/adapters/api/serializers.py`
- [X] T025 [US1] Implement Task action permission gating and `POST /tasks/` view/URL with RBAC before serializer validation in `backend/tasks/adapters/api/permissions.py`, `backend/tasks/adapters/api/views.py`, and `backend/tasks/adapters/api/urls.py`
- [X] T026 [US1] Compose Task URL fragments beneath the single `/api/v1/` prefix in `backend/config/urls.py`
- [X] T027 [US1] Regenerate and verify the additive create operation in `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts` using the existing generation scripts
- [X] T028 [P] [US1] Add frontend unit tests for Manager assignment fields, Helpdesk self-create fields, duplicate-submit suppression, retained form input, and active-user/Location picker reuse in `frontend/tests/unit/tasks/task-create.test.tsx`
- [X] T029 [US1] Implement generated-client create wrapper and Task create form/state integration in `frontend/src/features/tasks/api/task-api.ts`, `frontend/src/features/tasks/model/task-state.ts`, `frontend/src/features/tasks/model/use-task-management.ts`, and `frontend/src/features/tasks/ui/TaskForm.tsx`

**Gate 3 / MVP**: T019–T022 and T028 pass, generated contract checks are clean,
and quickstart scenarios 1–3 create paths pass without implementing lifecycle UI.

---

## Phase 4: User Story 2 — Track Lifecycle and Blockers (Priority: P1)

**Goal**: Authorized participants apply the canonical nonterminal matrix, record
BLOCKED reasons, resume the same Task, and Manager completes through audited
zero-photo/no-GPS override. COMPLETED is terminal.

**Independent Test**: Exercise every matrix cell, same-state retries, reason
validation, override, terminal mutations, and competing requests; verify ordered
TaskUpdates, matching snapshot, one audit, and absence of forbidden side effects.

### Tests first

- [X] T030 [P] [US2] Add status/override service tests for every allowed/rejected/no-op matrix cell, note/block-reason resolution, resume clearing, ordinary COMPLETED rejection, completion snapshot, and completed freeze in `backend/tests/unit/tasks/test_lifecycle_service.py`
- [X] T031 [P] [US2] Add status and override contract tests for operation IDs, ordinary status enum exclusion, 200 no-op/transition, 422 BLOCK_REASON_REQUIRED, ordinary terminal `400 VALIDATION_FAILED`, and 409 TASK_ALREADY_COMPLETED only on override in `backend/tests/contract/tasks/test_task_lifecycle_contract.py`
- [X] T032 [P] [US2] Add API integration tests for action-before-DTO and DTO-before-object-scope ordering (including malformed Leader 403 and malformed out-of-scope Helpdesk 400), self/ANY success, invalid edges, whitespace reasons, no-op evidence absence, exact override permission, and terminal freeze in `backend/tests/integration/api/tasks/test_task_lifecycle_api.py`
- [X] T033 [P] [US2] Add real-PostgreSQL two-connection tests for valid chained transitions, later same-state no-op, later invalid edge, status-versus-override, metadata/Location/assignee PATCH-versus-override, and duplicate override prevention with zero losing-request deltas in `backend/tests/integration/postgres/tasks/test_task_status_concurrency.py`
- [X] T034 [P] [US2] Add PostgreSQL rollback tests that fail after TaskUpdate insertion and after override AuditLog append, accept a valid URL-bearing completion note without placing it in audit payload, and assert Task/update/audit/outbox atomicity in `backend/tests/integration/postgres/tasks/test_task_lifecycle_atomicity.py`

### Implementation

- [X] T035 [US2] Implement locked `change_status` and `complete_override` application flows with latest-state re-evaluation, R-136 no-op, R-137 override, R-138 serialization, and R-139 terminal rejection in `backend/tasks/application/commands.py`
- [X] T036 [US2] Add insert-only lifecycle persistence and six-field snapshot update mapping to `backend/tasks/adapters/persistence/repositories.py`
- [X] T037 [US2] Add `task.completion.overridden` to the audit-owned action vocabulary, update the exact enum-cardinality test, and append an ID/status/method/actor/time payload without free-text completion note inside the override transaction in `backend/audit/domain/records.py`, `backend/tests/unit/audit/test_records.py`, and `backend/tasks/application/commands.py`
- [X] T038 [US2] Implement status/override serializers, response history serialization, views, and URLs in `backend/tasks/adapters/api/serializers.py`, `backend/tasks/adapters/api/views.py`, and `backend/tasks/adapters/api/urls.py`
- [X] T039 [US2] Regenerate and verify additive status/override operations and error schemas in `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`
- [X] T040 [P] [US2] Add frontend tests for allowed action rendering, BLOCKED reason form, no-op handling, override confirmation/note, 409 refetch, and completed read-only controls in `frontend/tests/unit/tasks/task-lifecycle.test.tsx`
- [X] T041 [US2] Implement status and Manager override API wrappers/state/forms with no automatic mutation retry and conflict refetch in `frontend/src/features/tasks/api/task-api.ts`, `frontend/src/features/tasks/model/use-task-management.ts`, `frontend/src/features/tasks/ui/TaskStatusForm.tsx`, and `frontend/src/features/tasks/ui/ManagerOverrideForm.tsx`

**Gate 4**: All matrix, atomicity, and PostgreSQL race tests pass; Ruff/mypy and
OpenAPI/client drift checks pass; exactly one override update/audit can commit.

---

## Phase 5: User Story 3 — Focus on Overdue and Current Work (Priority: P1)

**Goal**: Authorized users read each Task in exactly one of Overdue, Today,
Upcoming, or Completed with server-derived overdue days and immutable schedule.

**Independent Test**: Read representative past/current/future/completed Tasks
across an Asia/Ho_Chi_Minh date boundary; verify group exclusivity/order,
derived days, original date, and no write.

### Tests first

- [X] T042 [P] [US3] Add query-service tests for one captured business date, four-group exclusivity, completed precedence, creator/assignee de-duplication, inactive-history visibility, and no persisted overdue field in `backend/tests/unit/tasks/test_query_service.py`
- [X] T043 [P] [US3] Add list contract/API tests for `tasks_list`, `business_date`, group fields/order, nullable overdue semantics, private/no-store responses, malformed query rejection, and no-write behavior in `backend/tests/contract/tasks/test_task_list_contract.py` and `backend/tests/integration/api/tasks/test_task_list_api.py`
- [X] T044 [P] [US3] Add PostgreSQL query-count/index-plan and local-midnight read tests at representative MVP volume without wall-clock assertions in `backend/tests/integration/postgres/tasks/test_task_list_projection.py`

### Implementation

- [X] T045 [US3] Implement scoped list loading with batched creator/assignee/Location snapshots and one-request business date in `backend/tasks/application/queries.py` and `backend/tasks/adapters/persistence/repositories.py`
- [X] T046 [US3] Implement grouped list serialization and `GET /tasks/` endpoint with derived `group`/`overdue_days` and private/no-store response in `backend/tasks/adapters/api/serializers.py` and `backend/tasks/adapters/api/views.py`
- [X] T047 [US3] Regenerate and verify the additive grouped-list contract in `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`
- [X] T048 [P] [US3] Add frontend tests for four-section order, overdue labels/original dates, future exclusion, completed precedence, empty/loading/refetch-failure states, and server-owned grouping in `frontend/tests/unit/tasks/task-list.test.tsx`
- [X] T049 [US3] Implement the capability-guarded `/tasks` page, grouped list/card UI, list loading state, and employee navigation activation in `frontend/src/app/(employee)/tasks/page.tsx`, `frontend/src/features/tasks/ui/TaskManagementPanel.tsx`, `frontend/src/features/tasks/ui/TaskGroup.tsx`, `frontend/src/features/tasks/ui/TaskCard.tsx`, `frontend/src/features/identity/model/IdentityRouteBoundary.tsx`, and `frontend/src/shared/ui/shell/employee-navigation.ts`

**Gate 5**: List unit/API/PostgreSQL/frontend tests pass; no Task row changes
across date rollover; list query shape meets the deterministic query/index proxy
and contract gates remain clean. SC-010 wall-clock acceptance is closed in T072.

---

## Phase 6: User Story 4 — Preserve Inactive Assignment History (Priority: P2)

**Goal**: New inactive assignees are rejected atomically, while retained inactive
relationships stay visible and do not block unrelated edits.

**Independent Test**: Attempt mixed active/inactive create and replacement,
deactivate an existing assignee, edit metadata, remove/re-add the user, and race
two full-set replacements.

### Tests first

- [X] T050 [P] [US4] Add update-service tests for full desired assignee sets, additions-only eligibility, retained inactive users, empty-set rejection, immutable assigned date, nullable expected Location, and completed rejection in `backend/tests/unit/tasks/test_update_service.py`
- [X] T051 [P] [US4] Add PATCH contract/API tests for Manager-only assignee management, Helpdesk assignee-field rejection, all mixed missing/wrong-role/inactive IDs in one 422, metadata success with retained inactive user, server-owned assigned date/status fields, and atomic failures in `backend/tests/contract/tasks/test_task_update_contract.py` and `backend/tests/integration/api/tasks/test_task_update_api.py`
- [X] T052 [P] [US4] Add real-PostgreSQL tests for retained inactive links, remove/re-add rejection, empty-set protection, competing full-set replacements, update-versus-deactivation/role-change serialization, and rollback of assignment deltas in `backend/tests/integration/postgres/tasks/test_task_assignment_concurrency.py`

### Implementation

- [X] T053 [US4] Implement Task-locked metadata/expected-Location update and Manager full-set assignee replacement with ascending-ID locks/revalidation for additions only, aggregate R-141 errors, and immutable assigned date in `backend/tasks/application/commands.py`
- [X] T054 [US4] Implement SELF versus ANY update serializers plus `PATCH /tasks/{task_id}/` endpoint without status/date/completion fields in `backend/tasks/adapters/api/serializers.py`, `backend/tasks/adapters/api/views.py`, and `backend/tasks/adapters/api/urls.py`
- [X] T055 [US4] Regenerate and verify PATCH ownership, inactive-assignee error details, and server-owned field contract in `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`
- [X] T056 [P] [US4] Add frontend tests for active-only picker filtering, historical assignee display through minimal `{id, full_name}` Task data (inferring picker absence without exposing account status), Manager assignment editing, Helpdesk absence of assignment controls, and error ID presentation in `frontend/tests/unit/tasks/task-assignment.test.tsx`
- [X] T057 [US4] Implement Manager Task edit/assignee controls using existing user/Location APIs and retained inactive display in `frontend/src/features/tasks/api/task-api.ts`, `frontend/src/features/tasks/model/use-task-management.ts`, `frontend/src/features/tasks/ui/TaskForm.tsx`, and `frontend/src/features/tasks/ui/TaskCard.tsx`

**Gate 6**: Update/assignment unit, API, and PostgreSQL concurrency tests pass;
inactive history remains stable and every forbidden/new inactive assignment is
side-effect free.

---

## Phase 7: User Story 5 — Enforce Role and Object Scope (Priority: P2)

**Goal**: Helpdesk reads/updates only creator-or-assignee Tasks, Manager operates
at any scope without bypassing invariants, and Leader is read-only.

**Independent Test**: Exercise detail and every mutation as creator, assignee,
unrelated Helpdesk, Manager, Leader, and anonymous caller, including malformed
bodies and identifiers to prove ordering and IDOR protection.

### Tests first

- [X] T058 [P] [US5] Add authorization/object-scope service tests for creator OR assignee SELF, implied ALL/ANY grants, exact override scope, and invariant enforcement after broad scope in `backend/tests/unit/tasks/test_scope_policy.py`
- [X] T059 [P] [US5] Add detail/API precedence tests for anonymous, Leader read-only, unrelated Helpdesk scope-safe 404, malformed/nonexistent IDs, malformed Leader body returning 403 before DTO, action-authorized malformed out-of-scope Helpdesk body returning 400 before scope 404, Manager ANY transitions, and zero denied side effects in `backend/tests/integration/api/tasks/test_task_scope_api.py`
- [X] T060 [P] [US5] Add contract tests for `tasks_retrieve`, string path identifier authorization precedence, Task history shape, minimal `{id, full_name}` identity projections without username/is_active, and effective capability access in `backend/tests/contract/tasks/test_task_detail_contract.py`

### Implementation

- [X] T061 [US5] Centralize creator-or-assignee scope predicates for detail/update/status and ALL/ANY bypass without bypassing domain invariants in `backend/tasks/application/queries.py`, `backend/tasks/application/commands.py`, and `backend/tasks/adapters/persistence/repositories.py`
- [X] T062 [US5] Implement scoped `GET /tasks/{task_id}/`, string-ID parsing after permission, and scope-safe not-found mapping in `backend/tasks/adapters/api/views.py` and `backend/tasks/adapters/api/urls.py`
- [X] T063 [US5] Regenerate and verify detail/history/authorization contract additions in `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`
- [X] T064 [P] [US5] Add frontend tests proving Tasks route capability mapping and role-shaped mutation controls are presentation-only in `frontend/tests/unit/tasks/task-authorization.test.tsx` and `frontend/tests/unit/identity/capabilities.test.tsx`
- [X] T065 [US5] Integrate detail loading and role-shaped read-only/action presentation without client-side authorization assumptions in `frontend/src/features/tasks/api/task-api.ts`, `frontend/src/features/tasks/model/use-task-management.ts`, and `frontend/src/features/tasks/ui/TaskManagementPanel.tsx`

**Gate 7**: Authorization-order, IDOR, scope, Leader deny, and effective
capability tests pass; direct API calls remain authoritative and contract checks
are clean.

---

## Phase 8: Core Baseline Verification

**Purpose**: Prove the core Task aggregate, migration compatibility, static
quality, and original lifecycle/list behavior before evidence expansion.

- [X] T066 [P] Add an end-to-end Tasks journey covering Manager multi-create/override, Helpdesk self-create/status, Leader read-only, inactive history, and grouped rollover in `frontend/tests/e2e/tasks.spec.ts`
- [X] T068 Run fresh and previous-leaf migration verification plus `scripts/migration_check.py check` and record any compatibility fix in `backend/tasks/migrations/0001_initial.py`
- [X] T069 Run Task unit, API, contract, and real-PostgreSQL suites; fix only behavior within Feature 007 until all pass in `backend/tests/{unit/tasks,integration/api/tasks,integration/postgres/tasks,contract/tasks}/`
- [X] T070 Run Ruff, mypy, maintainability, module-boundary, Django system check, and migration-drift checks; fix scoped findings in `backend/tasks/`, `backend/config/`, and affected test gates
- [X] T071 Run deterministic OpenAPI generation, OpenAPI validation/compatibility, frontend API drift, TypeScript, ESLint, Vitest, and Tasks Playwright checks; fix scoped findings in `contracts/openapi.yaml`, `frontend/src/shared/api/schema.ts`, and `frontend/src/features/tasks/`
- [X] T072 Implement and run a no-new-dependency controlled Task-list capacity harness at representative ~50-user history, capture 100 authorized PostgreSQL-backed reads, and record/assert p95 below two seconds in `scripts/task_list_capacity_check.py` and `specs/007-task-management-core/evidence/task-list-performance.md`

**Core Gate**: The original Task aggregate, lifecycle, scope, list, migration,
contract, and static checks pass before FIELD_EVIDENCE phases begin. Overall
Feature-007 completion is governed by T104/T120 after all later phases.

---

## Phase 9: User Story 6 — Complete Work with Field Evidence (Priority: P1)

**Goal**: Let an authorized creator or assignee stage 1-5 private images, capture
fresh GPS, resolve Location ambiguity, and atomically complete a Task with
idempotent FIELD_EVIDENCE.

**Independent Test**: Upload two valid images for an in-scope Task, finalize with
fresh GPS and one idempotency key, then retry the same request and verify exactly
one completion update, two photos, bound intents, one Task snapshot, and protected
photo reads.

- [X] T075 [P] [US6] Add pure Task GPS quality, Location resolution, upload metadata, and normalized idempotency tests in `backend/tests/unit/tasks/test_evidence_rules.py`
- [X] T076 [P] [US6] Add command-service tests for upload intent scope, FIELD_EVIDENCE validation, Location choice, terminal behavior, and storage preflight in `backend/tests/unit/tasks/test_evidence_service.py`
- [X] T077 [P] [US6] Add model/constraint tests for evidence-shaped TaskUpdate, one-time EvidenceUpload binding, TaskPhoto immutability, and idempotency uniqueness in `backend/tests/unit/tasks/test_evidence_model_contract.py`
- [X] T078 [P] [US6] Add API/contract tests for evidence-upload, complete-field, idempotency, candidate errors, photo access authorization, and private/no-store responses in `backend/tests/contract/tasks/test_task_evidence_contract.py` and `backend/tests/integration/api/tasks/test_task_evidence_api.py`
- [X] T079 [P] [US6] Add real-PostgreSQL competing-finalize, same/different-key retry, upload reuse, rollback, and completed-task zero-delta tests in `backend/tests/integration/postgres/tasks/test_task_evidence_atomicity.py`
- [X] T080 [P] [US6] Add S3/R2 adapter tests for private presigned PUT/GET expiry, canonical staging keys, HEAD verification, and secret/object-key redaction in `backend/tests/unit/tasks/test_evidence_storage.py`
- [X] T081 [US6] Add Task GPS, Location resolution, evidence metadata, and idempotency domain types/rules in `backend/tasks/domain/evidence.py` and `backend/tasks/domain/tasks.py`
- [X] T082 [US6] Add evidence storage, Location geometry/config, and repository protocols plus typed commands in `backend/tasks/ports/evidence.py`, `backend/tasks/ports/locations.py`, `backend/tasks/ports/repositories.py`, and `backend/tasks/application/dto.py`
- [X] T083 [US6] Add `EvidenceUpload`, `TaskPhoto`, `CompletionIdempotency`, TaskUpdate GPS fields, constraints, indexes, and expand migration in `backend/tasks/models.py` and `backend/tasks/migrations/0002_task_evidence.py`
- [X] T084 [US6] Implement evidence persistence, locking, idempotency lookup, immutable photo reads, and detailed projection mapping in `backend/tasks/adapters/persistence/repositories.py`
- [X] T085 [US6] Implement S3/R2 presign and HEAD adapter with fail-closed runtime configuration in `backend/tasks/adapters/evidence_storage.py`, `backend/core/deployment.py`, `backend/config/settings.py`, `.env.example`, and `deploy/environments.yaml`
- [X] T086 [US6] Implement upload-intent, complete-field, and photo-access application use cases with storage preflight before the Task/upload lock transaction in `backend/tasks/application/evidence.py`, `backend/tasks/application/dependencies.py`, and `backend/tasks/application/container.py`
- [X] T087 [US6] Wire identity, Config, Location geometry, and evidence storage ports only at the composition root in `backend/config/task_adapters.py` and `backend/config/composition.py`
- [X] T088 [US6] Implement boundary serializers, permission ordering, evidence routes, candidate/idempotency errors, protected photo access, and evidence detail projections in `backend/tasks/adapters/api/serializers.py`, `backend/tasks/adapters/api/permissions.py`, `backend/tasks/adapters/api/views.py`, and `backend/tasks/adapters/api/urls.py`
- [X] T089 [US6] Add canonical Task evidence error codes/messages and storage dependencies in `backend/core/error_codes.py`, `backend/core/messages.py`, and `backend/pyproject.toml`
- [X] T090 [US6] Regenerate and verify additive evidence operations/schemas in `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`
- [X] T091 [P] [US6] Add frontend tests for image validation/compression, partial upload resume, fresh GPS, ambiguity selection, draft isolation, idempotent finalize, evidence history, and photo access in `frontend/tests/unit/tasks/task-evidence.test.tsx`
- [X] T092 [US6] Implement generated-client evidence wrappers and upload/finalize state without automatic mutation retry in `frontend/src/features/tasks/api/task-api.ts`, `frontend/src/features/tasks/model/task-state.ts`, and `frontend/src/features/tasks/model/use-task-management.ts`
- [X] T093 [US6] Implement Task evidence image preparation, account/Task-scoped seven-day drafts, foreground GPS capture, finalize form, Location choice, evidence history, Maps links, and protected photo viewing in `frontend/src/features/tasks/model/evidence-draft.ts`, `frontend/src/features/tasks/model/use-task-evidence.ts`, `frontend/src/features/tasks/ui/TaskEvidenceForm.tsx`, `frontend/src/features/tasks/ui/TaskEvidenceHistory.tsx`, and `frontend/src/features/tasks/ui/TaskCard.tsx`

---

## Phase 10: User Story 7 — Responsive Role-Aware UI Across Every Page (Priority: P1)

**Goal**: Give all routes one maintainable shadcn-based visual language, clear
page identity, role-shaped navigation, semantic statuses, and overflow-safe
mobile/desktop layouts.

**Independent Test**: Exercise every route at 360 px and 1280 px for each role;
assert current-page headers, allowed navigation, no horizontal page overflow,
semantic status badges, consistent fields/actions, and accessible focus/labels.

- [X] T094 [P] [US7] Add shared primitive and page-header tests for typography, field descriptions, badge variants, action spacing, focus, and accessible names in `frontend/tests/unit/ui/design-system.test.tsx` and `frontend/tests/unit/shell/page-header.test.tsx`
- [X] T095 [P] [US7] Add role/navigation and 360 px/1280 px overflow coverage for every route, including visible Tasks and Attendance destinations, in `frontend/tests/e2e/responsive-shell.spec.ts`
- [X] T096 [US7] Install/configure shadcn source conventions and Tailwind utilities, then add shared `cn`, Input, Textarea, Select, Field, Typography, StatusBadge, Card, and ActionGroup primitives in `frontend/components.json`, `frontend/postcss.config.mjs`, `frontend/src/shared/lib/cn.ts`, and `frontend/src/shared/ui/`
- [X] T097 [US7] Extend design tokens and global resets for responsive type scale, semantic status colors, field rhythm, overflow wrapping, and accessible focus/touch targets in `frontend/src/shared/ui/theme/tokens.css` and `frontend/src/app/globals.css`
- [X] T098 [US7] Make AppShell derive the current page title and role context, keep role-allowed destinations visible without horizontal scrolling, and constrain desktop columns consistently in `frontend/src/shared/ui/shell/AppShell.tsx`, `frontend/src/shared/ui/shell/AppHeader.tsx`, `frontend/src/shared/ui/shell/PrimaryNavigation.tsx`, and their CSS modules
- [X] T099 [P] [US7] Migrate login, change-password, users, locations, holidays, config, and job-health pages/features to shared PageHeader, Field, Card, Badge, Typography, and ActionGroup primitives in `frontend/src/app/` and `frontend/src/features/{identity,locations,operations}/ui/`
- [X] T100 [P] [US7] Migrate Attendance and guidance surfaces to shared headers, badges, typography, cards, fields, and responsive action groups without changing attendance logic in `frontend/src/features/{attendance,guidance}/ui/`
- [X] T101 [US7] Rework Tasks group/card/form/history/evidence layout so every column uses `minmax(0,1fr)`, long content wraps, forms/actions have consistent rhythm, and phone/desktop widths have no horizontal page overflow in `frontend/src/features/tasks/ui/` and `frontend/src/features/tasks/ui/TaskManagement.module.css`

---

## Phase 11: Convergence and Full Verification

**Purpose**: Close all artifacts/code gaps and prove both new user stories plus
all previously completed Feature-007 behavior.

- [X] T102 [P] Add end-to-end Manager/Helpdesk/Leader journeys for FIELD_EVIDENCE, Manager override, protected photo reads, ambiguity resolution, and responsive role navigation in `frontend/tests/e2e/tasks.spec.ts`
- [X] T103 Run Task unit/API/contract/PostgreSQL suites, migration/architecture/security gates, OpenAPI/client drift, Ruff/mypy, ESLint/TypeScript/Vitest, and Playwright; fix every scoped failure in affected Feature-007 files

---

## Phase 12: Convergence Follow-up

**Purpose**: Resolve the final cross-artifact conflict discovered by convergence.

- [X] T105 Correct the Manager override description in `specs/007-task-management-core/plan.md` so it remains a note-only completion path without photos or GPS, consistent with the specification, API, and implementation

---

## Phase 13: User Story 8 — Correct Task Entry and Evidence Failures

**Goal**: Support arbitrary expected places, reset successful create forms,
soft-delete mistaken Helpdesk self tasks, and make protected high-precision GPS
validation reliable.

**Independent Test**: Create/reset/delete an external-place self task, exercise
all delete denial cases, then finalize and reject high-precision/protected GPS
payloads with the specified persistence, maps, audit, and error outcomes.

- [X] T106 [P] [US8] Add redacted protected-validation and high-precision Task GPS regression tests in `backend/tests/unit/core/test_errors.py` and `backend/tests/contract/tasks/test_task_evidence_contract.py`
- [X] T107 [P] [US8] Add Task expected-place and soft-delete command/API/PostgreSQL tests in `backend/tests/unit/tasks/`, `backend/tests/integration/api/tasks/`, and `backend/tests/integration/postgres/tasks/`
- [X] T108 [US8] Add expand-only Task expected-place/deletion fields and repository filtering in `backend/tasks/models.py`, `backend/tasks/migrations/0003_task_correction.py`, and `backend/tasks/adapters/persistence/repositories.py`
- [X] T109 [US8] Add exact Helpdesk self-delete authorization, locked command, safe audit, endpoint, and canonical errors in `backend/identity/domain/authorization.py`, `backend/tasks/application/`, `backend/tasks/adapters/api/`, and `backend/audit/domain/records.py`
- [X] T110 [US8] Accept and project normalized free-text expected places and 18/15 GPS precision in Task DTOs, serializers, views, repository records, and generated contracts
- [X] T111 [P] [US8] Add frontend regressions for successful create reset, failed-create retention, free expected place, and eligible delete controls in `frontend/tests/unit/tasks/` and `frontend/tests/e2e/tasks.spec.ts`
- [X] T112 [US8] Implement generated-client delete, free expected-place input with Location suggestions, create-form reset, delete UI, and no-known-location evidence copy in `frontend/src/features/tasks/`
- [X] T113 [US8] Regenerate OpenAPI/client artifacts and run Task unit/API/PostgreSQL, migration, security, architecture, frontend unit/build, and Playwright gates

---

## Phase 14: Evidence Governance and Operational Remediation

**Purpose**: Close the remaining audit, cleanup, draft, immutable-history, and
presentation proof gaps introduced by the finalized FIELD_EVIDENCE specification.

- [X] T067 [P] Replace the obsolete deferred-evidence guard with regression checks proving only the governed evidence-upload, complete-field, protected-photo, and Task GPS routes/models are exposed; keep the no-unapproved-Task-OutboxEvent assertion and verify no object key, presigned/photo/Maps URL, image data, or precise coordinates enter audit/outbox/telemetry in `backend/tests/architecture/test_task_feature_boundary.py`
- [X] T114 [P] [US6] Define or confirm the CHOT-governed closed audit action for FIELD_EVIDENCE before code changes, then add privacy-safe audit vocabulary/payload tests and command-service tests proving Task ID/status/method/actor/server-time only, with no note, GPS, candidate, photo, object key, or URL data in `docs/CHOT_YEU_CAU.md`, `backend/audit/domain/records.py`, `backend/tests/unit/audit/test_records.py`, and `backend/tests/unit/tasks/test_evidence_service.py`
- [X] T115 [US6] Append FIELD_EVIDENCE AuditLog through the audit port in the same transaction as TaskUpdate, TaskPhoto rows, upload bindings, idempotency record, and Task snapshot; add real-PostgreSQL rollback/race tests proving all-or-none commit in `backend/tasks/application/evidence.py`, `backend/tasks/application/dependencies.py`, `backend/config/composition.py`, and `backend/tests/integration/postgres/tasks/test_task_evidence_atomicity.py`
- [X] T116 [P] [US6] Add an idempotent expired-upload cleanup use case and management command that removes seven-day unbound staging objects/intents, rechecks binding before deletion, never deletes a bound TaskPhoto object, and tolerates per-object storage failure; cover expired/unexpired/bound/finalize-race/retry behavior in `backend/tasks/application/evidence_cleanup.py`, `backend/tasks/adapters/evidence_storage.py`, `backend/tasks/management/commands/cleanup_task_evidence_uploads.py`, and `backend/tests/integration/postgres/tasks/test_evidence_cleanup.py`
- [X] T117 [P] [US6] Extend local-draft implementation and tests for compressed-photos-plus-note-only storage, account+Task isolation, absence of GPS/auth or upload token/object key/presigned URL, verified-finalize/discard/logout/account-switch/seven-day/account-disable purge, and truthful unavailable/quota/eviction states in `frontend/src/features/tasks/model/evidence-draft.ts`, `frontend/src/features/tasks/model/use-task-evidence.ts`, and `frontend/tests/unit/tasks/task-evidence-draft.test.ts`
- [X] T118 [P] [US6] Add PostgreSQL/read-model regression tests proving persisted `location_candidates` remain unchanged after Location radius/active/catalog changes and that GOOD multiple-candidate completion cannot commit without a recomputed valid selection in `backend/tests/integration/postgres/tasks/test_task_evidence_candidates.py`
- [X] T119 [P] [US6] Add contract/backend/frontend presentation tests proving `resolved_address` is selected Location name+address or null, `maps_url` uses exact stored Task capture coordinates with safe external-link attributes, and no reverse-geocoding call, map SDK/embed, Location coordinates, or EXIF GPS is used in `backend/tests/contract/tasks/test_task_evidence_contract.py`, `backend/tests/unit/tasks/test_evidence_projection.py`, and `frontend/tests/unit/tasks/task-evidence-history.test.tsx`
- [X] T120 Update `specs/007-task-management-core/quickstart.md` with the finalized audit/cleanup/draft/candidate/presentation DoD, regenerate OpenAPI/client artifacts if T114–T119 change contracts, run evidence unit/API/contract/PostgreSQL/storage/security/frontend suites plus migration and architecture gates, execute the quickstart, rerun `$speckit-analyze` and `$speckit-converge`, and leave no task checked unless its required evidence passes
- [ ] T073 Create and execute the SC-011 moderated-review protocol with at least 10 representative users, recording only aggregate role/count/time/pass data and requiring at least 9 successful four-group interpretations in `specs/007-task-management-core/evidence/task-list-usability.md`
- [ ] T074 Execute every automated and manual scenario in the finalized `specs/007-task-management-core/quickstart.md`, verify all DoD items and absence of forbidden side effects, then mark only genuinely completed task checkboxes in `specs/007-task-management-core/tasks.md`
- [ ] T104 After T067, T073–T074, and T114–T120 are complete, rerun `$speckit-analyze` and `$speckit-converge`, complete any newly appended tasks, verify every Feature-007 gate is green, and mark T104 complete only when no critical finding or unchecked implementation task remains

---

## Dependencies & Execution Order

### Phase dependencies

```text
Phase 1 Setup
  -> Phase 2 Foundational (blocks every story)
     -> US1 Create/Assign
        -> US2 Lifecycle
        -> US3 Lists
        -> US4 Inactive History / Assignment Update
        -> US5 Authorization / Detail Scope
           -> Phase 8 Core Verification
              -> US6 Field Evidence
                 -> US7 Responsive UI
                    -> Phase 11 Evidence/UI Verification
                       -> Phase 12 Plan Conflict Follow-up
                          -> US8 Correction/Evidence Failures
                             -> Phase 14 Evidence Governance Remediation
                                -> T120 Artifact and Automated Verification
                                   -> T073/T074 Outcome and Manual Verification
                                      -> T104 Final Convergence
```

US2 and US3 can begin after Foundational plus the Task aggregate from US1 is
available. US4 depends on create plus update persistence and terminal semantics.
US5 closes core endpoint scope. US6 adds governed evidence persistence and APIs;
US7 consumes its UI; US8 adds correction behavior; Phase 14 closes the audit,
cleanup, draft, candidate-history, and presentation proof gaps. Final convergence
depends on all of them, regardless of historical phase numbering.

### Within each story

1. Write the listed tests and confirm they fail for the missing behavior.
2. Implement domain/application behavior before adapters.
3. Implement persistence before API views.
4. Regenerate canonical OpenAPI/client artifacts after backend annotations.
5. Implement frontend against generated types.
6. Pass the phase gate before starting the next story.

## Genuine Parallel Opportunities

- T004, T005, T006, and T007 are independent test files after Setup.
- T011 and T012 define unrelated foundational port groups after T008–T010.
- In each story, `[P]` test tasks can be authored concurrently because they use
  different files and assert the same pre-implementation contract.
- Frontend test tasks marked `[P]` can be authored after the relevant generated
  schema exists while backend implementation is otherwise complete.
- T066 and T067 are independent final regression surfaces after all stories.
- T114, T116, T117, T118, and T119 can begin in parallel after US6 because they
  affect distinct audit, cleanup, draft, candidate, and presentation surfaces;
  T115 depends on T114 and T120 depends on T067 plus T114–T119.

Tasks sharing `commands.py`, serializers/views, generated schema, or Task UI
state are intentionally sequential and are not marked `[P]`.

## Parallel Examples

### Foundational

```text
T004 domain transition/projection tests
T005 model contract tests
T006 authorization adapter tests
T007 PostgreSQL constraint/migration tests
```

### User Story 2

```text
T030 lifecycle service tests
T031 lifecycle contract tests
T032 lifecycle API tests
T033 status concurrency tests
T034 lifecycle atomicity tests
```

### User Story 4

```text
T050 update service tests
T051 PATCH contract/API tests
T052 assignment PostgreSQL concurrency tests
```

## Implementation Strategy

### MVP first

1. Complete Setup and Foundational gates.
2. Complete US1 and Gate 3.
3. Demonstrate Manager multi-assignment and Helpdesk self-create independently.
4. Continue because the user's requested terminal condition is full Feature 007,
   not an MVP stop.

### Incremental delivery

1. US1 establishes Task creation and ownership.
2. US2 adds canonical history, concurrency, and Manager override.
3. US3 exposes the four authoritative read groups.
4. US4 adds safe Manager edits and inactive-history behavior.
5. US5 closes every endpoint with consistent object scope/read-only semantics.
6. US6 implements FIELD_EVIDENCE upload/finalize/photo access and Task GPS rules.
7. US7 standardizes responsive presentation; US8 adds correction and protected
   validation behavior.
8. Phase 14 closes completion audit, expired-upload cleanup, draft purge,
   immutable candidate history, and exact evidence presentation.
9. T120 proves automated migration/contract/implementation gates; T073/T074 then
   prove outcome/manual scenarios, and T104 performs the final convergence gate.

## Requirement Coverage Index

| Requirement cluster | Primary task IDs |
|---|---|
| FR-001–FR-012 create, multi-assignee, inactive eligibility/history | T019–T029, T050–T057 |
| FR-013–FR-020 lifecycle, no-op, history, concurrency | T004, T008, T030–T041 |
| FR-021–FR-024 grouping, overdue, immutable date | T009, T042–T049 |
| FR-025–FR-029 authorization/object scope/Leader | T006, T010, T016, T058–T065 |
| FR-030 expected Location separation | T011, T019, T023–T024, T050–T054 |
| FR-031 FIELD_EVIDENCE and distinct Manager override | T030–T041, T067, T075–T093, T102, T114–T120 |
| FR-032–FR-034 override, terminal, atomic audit, matrix tests | T030–T041, T066, T102–T105 |
| FR-035–FR-037A photo bounds/format, staging, verification, fresh GPS | T075–T093, T102, T106, T110, T120 |
| FR-038 FIELD_EVIDENCE atomic completion and audit | T077, T079, T083–T088, T114–T115, T120 |
| FR-039–FR-041 idempotency, Task GPS quality, Location choice | T075–T093, T102, T118, T120 |
| FR-041A immutable Location candidate snapshot | T075, T077, T083–T084, T118, T120 |
| FR-042–FR-043A private evidence reads, presentation, no EXIF GPS | T078, T080, T084–T093, T102, T119–T120 |
| FR-043B–FR-043C account+Task local draft and purge | T091, T093, T117, T120 |
| FR-043D expired unbound upload cleanup | T116, T120 |
| FR-044–FR-047 responsive role-aware shared UI | T094–T103 |
| FR-048–FR-053 expected-place, reset, soft delete, precise/redacted GPS | T106–T113 |
| FR-054 exact captured-coordinate Maps presentation | T093, T112, T119–T120 |
| SC-001–SC-009 behavior outcomes | Story tests T019–T065 |
| SC-010 list performance at MVP scale | T044, T072 |
| SC-011 usability comprehension | T048, T066, T073 |
| SC-012–SC-020 FIELD_EVIDENCE, upload/GPS validation, UI and atomicity | T075–T103, T106, T114–T120 |
| SC-021 local-draft isolation/purge/failure behavior | T091, T093, T117, T120 |
| SC-022 Manager override method/note/audit | T030–T041, T102, T105 |
| SC-023 Location-only address and captured-coordinate Maps link | T093, T112, T119–T120 |

## Notes

- Feature 007 intentionally includes private S3/R2 evidence storage, Task
  photo/GPS models, upload/finalize/photo-access endpoints, recoverable Task
  deletion, completion-scoped idempotency, and expired-upload cleanup. It adds no
  broker, generic idempotency facility, reopen endpoint, hard delete, or
  unapproved Task OutboxEvent.
- Canonical generated artifacts are changed only by generation commands.
- A genuine requirement conflict stops only the affected task and returns to the
  governance chain; implementation must not resolve it silently.

## Phase 15: Convergence

- [X] T121 Split and canonically name the implemented FIELD_EVIDENCE form/history components as `frontend/src/features/tasks/ui/TaskEvidenceForm.tsx` and `frontend/src/features/tasks/ui/TaskEvidenceHistory.tsx`, preserving the tested draft, upload, GPS, candidate, protected-photo, Location-address, and Maps-link behavior per plan: frontend structure and T093 (partial)
- [X] T122 Restore the full repository Ruff and mypy gates by resolving all currently reported violations without weakening checks, then rerun both gates per Constitution XII and Development Workflow gate 4 (contradicts)
