# Implementation Plan: Task Management Core

**Branch**: `feature/007-task-management-core` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-task-management-core/spec.md`

## Summary

Feature 007 adds the first persistent Task aggregate and the employee Tasks
surface. A MANAGER can create a Task for one or more active HELPDESK users and
manage its assignees; a HELPDESK user can create an arising Task only for
themselves. Every Task has one canonical status, an immutable `assigned_date`,
an optional expected Location, append-only lifecycle updates, creator-or-assignee
self scope, four read-time list groups, private staged photo uploads, GPS-backed
FIELD_EVIDENCE completion, and an audited Manager override path. `COMPLETED` is
terminal and freezes every mutable Task field.

The implementation follows the repository's existing per-app inward
architecture by adding `backend/tasks/{domain,application,ports,adapters}` and
wiring cross-module identity/Location access only in `backend/config/`. Task
commands use one Django transaction; status and completion commands lock the
Task row, re-read the latest state, apply the pure domain matrix, append one
`TaskUpdate`, and update the Task snapshot together. `TaskAssignee` uniqueness
and Task snapshot shape are protected in PostgreSQL; at-least-one-assignee is
maintained by full-set replacement while the Task row is locked. Reads derive
business date, group, and `overdue_days` at request time and never write
`assigned_date`.

The API is additive under `/api/v1/tasks/` and is generated into the existing
OpenAPI/TypeScript pipeline. The frontend adds FIELD_EVIDENCE upload/finalize to
the capability-guarded `/tasks` route and standardizes every existing route on a
responsive role-aware shell plus repository-owned shadcn UI composition
patterns. Private S3/R2 storage is accessed behind a Task storage port; no
notification consumer is introduced.

## Technical Context

**Language/Version**: Python `>=3.12,<3.14`; TypeScript 5.9.2; Node.js `>=22`

**Primary Dependencies**: Django 5.2.5, Django REST Framework 3.16.1,
drf-spectacular 0.28.0, psycopg 3.2.9, `django-storages[s3]`/boto3; Next.js
16.3.1, React 19.1.1, `openapi-fetch` 0.14.0, and repository-owned shadcn UI
primitives using the existing CSS-token system.

**Storage**: PostgreSQL plus private S3-compatible object storage. The original
three Task tables are expanded with `tasks_evidenceupload`, `tasks_taskphoto`,
and `tasks_completionidempotency`; existing `identity.User`,
`locations.Location`, and `audit.AuditLog` remain referenced through ports.

**Testing**: Backend pytest unit/API/contract suites plus real-PostgreSQL
integration, transaction, constraint, and competing-worker tests; frontend
Vitest + Testing Library and existing Playwright end-to-end coverage; existing
Ruff, mypy, ESLint, TypeScript, OpenAPI drift/compatibility, architecture, and
migration gates.

**Target Platform**: Existing Linux-hosted Django API and modern mobile/desktop
browsers served through the Next.js same-origin frontend.

**Project Type**: Web application — hexagonal Django backend + Next.js App
Router frontend, contract-linked through generated `contracts/openapi.yaml` and
`frontend/src/shared/api/schema.ts`.

**Performance Goals**: At MVP scale (approximately 50 internal users), at least
95% of authorized Task-list reads return the complete four-group projection in
under 2 seconds. Query work is bounded by scoped indexed Task/assignee reads and
batched related-object loading; no per-row query loop is permitted.

**Constraints**:

- Governance authority is CHOT §4, §6.1–§6.3, §7, §8, §9.1, and §10;
  QUY_TAC §4–§7 and §10; PRD §3.2–§3.3 and §5; and decisions R-44,
  R-66, R-84, R-86, and R-135–R-143. CHOT §4 governs Task-specific GPS,
  §6.2 governs FIELD_EVIDENCE, and §9.1 governs private image storage,
  staging cleanup, and local drafts.
- Authorization order is authentication → action/body-independent gate → DTO →
  object scope → Task invariant/matrix → transaction/constraint → audit.
- `assigned_date` is never accepted by PATCH and is never rewritten by a job.
- `overdue_days` and group membership are response projections using server time
  in `Asia/Ho_Chi_Minh`; neither is a database column.
- `TaskUpdate` is insert-only. The six Task snapshot fields (`status`,
  `completed_by`, `completed_at`, `completion_method`, `completion_note`,
  `block_reason`) change only beside the lifecycle row that produced them.
- Status mutations use `SELECT ... FOR UPDATE`; no optimistic Task version,
  unchecked last-write-wins, or blanket stale-request rejection is added.
- Ordinary status accepts only `TODO`, `IN_PROGRESS`, and `BLOCKED` and cannot
  complete a Task. Completion uses either scoped `FIELD_EVIDENCE` with 1-5
  verified photos and fresh GPS or `MANAGER_OVERRIDE` with a nonblank note and
  no photos or GPS.
- Rejected, invalid, out-of-scope, same-state no-op, and terminal requests create
  no Task/assignment/update/audit/outbox side effect.
- No new Task outbox event is emitted: notification delivery is explicitly out
  of this feature and there is no approved Feature-007 event schema. The Manager
  override AuditLog joins the business transaction.
- Mutating requests are not automatically retried by the client. Status retry is
  governed by R-136/R-138; field finalization uses the committed
  `Idempotency-Key` contract and repeated completion is terminal.
- Upload intents are actor/Task-bound, expire after seven days, use presigned PUT
  URLs lasting at most 15 minutes, and become business evidence only after HEAD,
  checksum/MIME/size validation and atomic binding.
- Task GPS uses Task-specific quality thresholds and existing Location geometry
  through a port; it never imports Attendance policy or treats weak GPS as a
  completion blocker.
- Every route uses the shared shell and page-header contract; reusable shadcn
  primitives own typography, badges, fields, cards, and action spacing. Mobile
  navigation wraps/fits at 360 px and desktop content uses `minmax(0, 1fr)` with
  consistent maximum widths.

**Scale/Scope**: Approximately 50 users and representative Task histories; one
Task business module, six Task tables, additive upload/finalize/photo-access API
operations, all existing frontend routes, and focused backend/frontend coverage.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.1.

| Principle | Gate | Status |
|---|---|---|
| I. Source-of-Truth Governance | CHOT → QUY_TAC → PRD → implementation; R records history only | **PASS** — the design implements synchronized R-135–R-143 and introduces no new business rule. |
| II. Fixed Stack & Inward Architecture | Existing stack; `domain/application/ports/adapters`; no business-module cross-imports | **PASS** — new `tasks` app mirrors established modules; identity and Location models are accessed only by adapters in `config/`. |
| III. Layered, Ordered Authorization | Central actions, RBAC before DTO, object scope after DTO | **PASS** — a Task authorization port maps exact create grants plus implied read/update grants to typed modes; R-140 makes MANAGER ASSIGN-only and HELPDESK SELF-only, so mode selection never inspects payload or role in Task code. |
| IV. Server Authority & Boundary Validation | Actor/time/status outcome are server-owned; unknown/server-owned fields rejected | **PASS** — serializers expose only allowed fields; creator, timestamps, initial status, completion metadata, grouping, and overdue values are server-owned. |
| V. DB-Backed Invariants & Transactions | Constraints/locks and one explicit transaction per write | **PASS** — unique assignees, closed enum/shape checks, row-lock serialization, full-set assignment replacement, lifecycle/snapshot/photo/upload-binding atomicity, and completion audit atomicity are explicit and PostgreSQL-tested. Storage HEAD/checksum/MIME/size preflight occurs before the short database transaction, followed by ownership/state revalidation under lock. |
| VI. Auditability & Safe Observability | Append-only history; completion audit; no unsafe payload | **PASS** — lifecycle/photo/candidate history is insert-only; FIELD_EVIDENCE and Manager override audit records contain only governed IDs/method/state/server time and exclude free-text notes, secrets, GPS, URLs, object keys, and photo data; no unapproved outbox event is fabricated. |
| VII. Stable Generated API Contracts | Versioned routes, canonical errors, generated schema/client, compatibility gate | **PASS** — operations are additive under `/api/v1/`; backend annotations generate OpenAPI and the TypeScript schema through existing scripts. |
| VIII. Safe Schema Evolution | Expand-only, rolling-compatible migration, one leaf | **PASS** — `0001_initial`, `0002_task_evidence`, and `0003_task_correction` use expand-only, nullable/default-safe evolution and preserve a single migration leaf; rolling-compatibility and migration-order checks cover every step. |
| IX. Security, Secrets & Isolation | Backend enforcement, private evidence, no secret exposure | **PASS** — object-scope queries prevent IDOR; buckets are private; object keys and presigned URLs never enter ordinary responses, audit, or logs; photo access is separately authorized. |
| X. Location & GPS Integrity | Expected and actual Location stay distinct; Task-specific GPS policy | **PASS** — expected Location remains planning-only; completion captures device GPS, stores candidate history, warns rather than blocks on weak Task GPS, and never imports Attendance thresholds. |
| XI. Testing at Correct Layer | Pure rules unit-tested; DB/lock/rollback on PostgreSQL; contract/UI/CI gates | **PASS** — matrix/projections are unit-tested, authorization/API are integration-tested, and races/constraints/atomicity run with real PostgreSQL transactions. |
| XII. Maintainable Code & Naming | Canonical names, closed enums, thin adapters/UI, existing complexity limits | **PASS** — `TaskStatus`, `CompletionMethod`, wire `snake_case`, TS `camelCase`, and unit suffixes are retained; no duplicate state or transport layer is added. |

**Result: all pre-design gates pass; Complexity Tracking remains empty.**

## Follow-up design: task correction and evidence validation

- Add nullable/default-safe `expected_location_text` and `deleted_at` Task fields
  in one expand-only migration. Registered Locations remain optional suggestions
  and legacy references; new planning text is independent from geofence evidence.
- Add exact `task.delete.self` authorization, a Task-locked soft-delete command,
  a privacy-safe audit action, and repository-wide `deleted_at IS NULL` scope.
- Align Task GPS serializers with the existing 18/15 coordinate persistence
  shape. Protected validation failures collapse to a generic safe field error
  before canonical envelope validation.
- Extend generated Task contracts/client, reset successful create forms, expose
  free-text expected place, and show the delete action only for eligible
  Helpdesk-created tasks. PostgreSQL, API, contract, unit, UI, and E2E tests own
  the invariants.

The post-design constitution check remains PASS: deletion is recoverable rather
than destructive, audit and Task state commit together, protected coordinates
never enter error/audit payloads, and all dependencies retain inward direction.

**Post-Phase 1 re-check**: re-evaluated after `research.md`, `data-model.md`,
`contracts/task-api.yaml`, and `quickstart.md` were produced. All twelve gates
still pass. The Phase 1 design uses only existing infrastructure, introduces no
unapproved event/dependency/endpoint, keeps all cross-module reads behind ports,
and assigns every concurrency, audit, migration, and contract guarantee to an
executable verification layer.

## Project Structure

### Documentation (this feature)

```text
specs/007-task-management-core/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── task-api.yaml
├── checklists/
│   └── requirements.md
└── tasks.md                     # created later by /speckit-tasks, not by this plan
```

### Source Code (repository root)

```text
backend/
├── tasks/                                      # NEW business module
│   ├── domain/
│   │   ├── tasks.py                            # TaskStatus, CompletionMethod, snapshots
│   │   ├── transitions.py                      # canonical pure transition/no-op policy
│   │   └── projections.py                      # group + overdue derivation from business date
│   ├── application/
│   │   ├── commands.py                         # create/update/status/override orchestration
│   │   ├── queries.py                          # scoped detail and grouped list projections
│   │   ├── dto.py                              # typed commands/results; no raw request objects
│   │   ├── dependencies.py                     # port bundle + unit-of-work factory
│   │   └── container.py                        # service container
│   ├── ports/
│   │   ├── authorization.py                    # typed create/read/update/completion access
│   │   ├── assignees.py                        # active HELPDESK eligibility snapshots
│   │   ├── locations.py                        # expected-Location existence/snapshot lookup
│   │   ├── repositories.py                     # Task/assignee/update reads and writes
│   │   ├── clock.py                            # server time/business date
│   │   └── unit_of_work.py                     # transaction protocol
│   ├── adapters/
│   │   ├── api/
│   │   │   ├── permissions.py                  # auth/action gate before serializers
│   │   │   ├── serializers.py                  # create/update/status/override/read DTOs
│   │   │   ├── views.py                        # thin DRF operations + schema annotations
│   │   │   └── urls.py                         # unversioned fragments composed by config
│   │   ├── persistence/
│   │   │   ├── repositories.py                 # ORM + select_for_update + scoped queries
│   │   │   └── unit_of_work.py                 # Django transaction.atomic
│   │   └── clock.py                            # timezone.now / Asia-Ho_Chi_Minh date
│   ├── migrations/
│   │   ├── 0001_initial.py                   # Task, TaskAssignee, TaskUpdate
│   │   ├── 0002_task_evidence.py             # EvidenceUpload, TaskPhoto, idempotency/GPS fields
│   │   └── 0003_task_correction.py           # expected-place text and recoverable deletion
│   ├── apps.py
│   └── models.py                                # Task aggregate, evidence, photos, idempotency
├── config/
│   ├── task_adapters.py                         # NEW: identity/Location cross-module adapters
│   ├── composition.py                           # add cached task_container
│   ├── settings.py                              # register tasks app
│   └── urls.py                                  # compose task URL fragments at /api/v1/
├── audit/domain/records.py                      # add approved manager-override audit action
├── core/error_codes.py                          # add three approved Task codes
└── tests/
    ├── unit/tasks/                              # matrix, completion, projections, services
    ├── api/tasks/                               # serializers, precedence, responses
    ├── integration/postgres/tasks/              # constraints, locks, rollback, scope, indexes
    ├── contract/tasks/                          # OpenAPI/error/operation contracts
    └── architecture/                            # include tasks in inward-boundary guard

contracts/
└── openapi.yaml                                 # regenerated, never edited by hand

frontend/
├── src/
│   ├── app/(employee)/tasks/page.tsx             # thin capability-guarded route
│   ├── features/tasks/
│   │   ├── api/task-api.ts                       # generated-client wrapper only
│   │   ├── model/
│   │   │   ├── task-state.ts                     # closed async/form/action state
│   │   │   ├── use-task-management.ts            # load/mutate/refetch orchestration
│   │   │   ├── use-task-evidence.ts              # upload/GPS/finalize orchestration
│   │   │   └── evidence-draft.ts                 # account+Task local draft and purge policy
│   │   └── ui/
│   │       ├── TaskManagementPanel.tsx            # thin screen composition
│   │       ├── TaskGroup.tsx                      # Overdue/Today/Upcoming/Completed section
│   │       ├── TaskCard.tsx                       # assignees/date/status/actions
│   │       ├── TaskForm.tsx                       # self vs Manager-assignment fields
│   │       ├── TaskStatusForm.tsx                 # nonterminal transition + block reason
│   │       ├── ManagerOverrideForm.tsx             # note-only completion confirmation
│   │       ├── TaskEvidenceForm.tsx                # image/GPS/Location-choice completion
│   │       └── TaskEvidenceHistory.tsx             # protected photos/address/Maps presentation
│   ├── features/identity/model/IdentityRouteBoundary.tsx  # add tasks capability route
│   └── shared/ui/shell/employee-navigation.ts    # mark existing Tasks entry implemented
└── tests/
    ├── unit/tasks/                               # grouped rendering/forms/errors/state
    ├── contract/task-api.test.ts                 # generated client operation/shape use
    └── e2e/tasks.spec.ts                         # role/scope/lifecycle/list journey

.github/workflows/{quality,contract}.yml           # extend hardcoded module lists only;
                                                    # reuse existing gates/infrastructure
```

**Structure Decision**: Add a peer `tasks` Django business module because the
aggregate has independent domain rules, persistence, authorization scope, and
transactions. Reuse the composition-root adapter precedent from Attendance for
cross-module identity/Location data. On the frontend, add one feature module
inside the existing employee shell and preserve the generated-client and
`authenticatedFetch` chokepoints. Do not place Task rules in `core`, Identity,
Location, serializers, views, or React components.

## Delivery Design

### Backend module and use cases

- `TaskCommandService.create` receives a typed create mode from authorization.
  `SELF` uses an input DTO with no `assignee_ids`, locks/re-authorizes the actor
  inside the transaction, and writes that actor as creator and sole initial
  assignee. `ASSIGN` normalizes duplicate IDs, requires at least one
  ID, and validates all IDs through the assignee eligibility port before commit.
  R-140 guarantees MANAGER resolves only to `ASSIGN` and HELPDESK only to `SELF`.
- `TaskCommandService.update` locks the Task, rejects terminal state, applies
  creator-or-assignee scope for `SELF` or global scope for `ANY`, omits
  `assigned_date` from the DTO, and lets only `ANY` replace the complete
  assignee set. It validates only IDs newly added relative to the locked set.
- `TaskCommandService.change_status` locks and re-reads the Task, checks scope,
  executes the pure matrix, returns without writes for a valid same-state
  nonterminal no-op, otherwise inserts a TaskUpdate and updates all six snapshot
  fields consistently.
- `TaskCommandService.complete_override` requires the exact override action,
  locks the Task, rejects an already completed Task with 409, validates the note,
  creates one COMPLETED/MANAGER_OVERRIDE update, updates completion snapshot, and
  appends one AuditLog inside the same transaction.
- `TaskEvidenceService.create_upload_intent` validates the actor/Task relationship
  and declared JPEG/PNG/WebP MIME, compressed size up to 5 MB, and SHA-256
  checksum before issuing a private presigned PUT lasting at most 15 minutes.
- `TaskEvidenceService.complete_field` performs storage HEAD and metadata checks
  before locking, then revalidates upload ownership/Task/expiry/bound state and
  creator-or-assignee scope under lock. It classifies Task-specific GPS, resolves
  or requests Location selection, persists the immutable candidate snapshot, and
  atomically writes the TaskUpdate, one to five TaskPhotos, upload bindings,
  idempotency result, Task snapshot, and privacy-safe completion AuditLog.
- `EvidenceUploadCleanupService` expires unbound intents and deletes their private
  staging objects after seven days. It is idempotent and must never delete or
  invalidate an object already bound to TaskPhoto evidence.
- `TaskQueryService` obtains a typed read scope. `SELF` composes
  `created_by = actor OR assignee = actor`; `ALL` has no relationship filter.
  Detail and list use the same scope predicate, deduplicate joins, and prefetch
  assignee/Location display snapshots.

### API and error semantics

| Operation | Action/scope | Success | Governed failures |
|---|---|---:|---|
| `GET /api/v1/tasks/` | request `task.view.self`; closed implication maps to SELF or ALL | `200` grouped projection | `401 INVALID_TOKEN`, `403 PERMISSION_DENIED` |
| `GET /api/v1/tasks/{task_id}/` | same read scope | `200` Task detail | scope-safe `404 NOT_FOUND` for absent/out-of-scope |
| `POST /api/v1/tasks/` | exact create grant maps MANAGER to ASSIGN or HELPDESK to SELF | `201` Task | `400 VALIDATION_FAILED`/`SERVER_OWNED_FIELD`, `422 INACTIVE_ASSIGNEE` |
| `PATCH /api/v1/tasks/{task_id}/` | request `task.update.self`; implication maps Manager to ANY | `200` Task | `403` action denial, scope-safe `404`, `400 VALIDATION_FAILED` when terminal, `422 INACTIVE_ASSIGNEE` |
| `POST /api/v1/tasks/{task_id}/status` | SELF or implied ANY update | `200` Task, including no-op | `400 VALIDATION_FAILED` for unsupported/invalid/terminal state, `422 BLOCK_REASON_REQUIRED` |
| `POST /api/v1/tasks/{task_id}/complete-override` | exact `task.complete.override`, global Task scope | `200` Task | `400 VALIDATION_FAILED` for blank note, `409 TASK_ALREADY_COMPLETED` |
| `POST /api/v1/tasks/{task_id}/evidence-uploads` | exact `task.complete.field`, creator-or-assignee scope | `201` private upload intent | validation failure for unsupported MIME/size/checksum; scope-safe `404`; terminal/deleted Task rejection |
| `POST /api/v1/tasks/{task_id}/complete-field` | exact `task.complete.field`, creator-or-assignee scope | `201` idempotent FIELD_EVIDENCE completion | upload/GPS validation; `409 LOCATION_CHOICE_REQUIRED` or `IDEMPOTENCY_CONFLICT`; `422 INVALID_LOCATION_CHOICE`; terminal conflict |
| `GET /api/v1/tasks/{task_id}/photos/{photo_id}/access` | `photo.view.self` scope or implied `photo.view.all` | `200` short-lived private access URL | scope-safe `404`, `403 PERMISSION_DENIED` |
| `DELETE /api/v1/tasks/{task_id}/` | exact `task.delete.self`, Helpdesk creator and sole assignee | `204` recoverable soft delete | scope-safe `404`, eligibility/terminal rejection |

The contract uses string path converters so action authorization precedes ID
interpretation, matching existing route-precedence rules. All Task responses use
the canonical error envelope and `Cache-Control: private, no-store`. Feature 007
adds only the governed recoverable DELETE, evidence-upload, complete-field, and
protected-photo operations above; reopen, notification, and bulk endpoints remain
out of scope.

### Transactions, concurrency, and failure handling

- Create opens one unit of work. SELF locks/re-authorizes its actor User row and
  uses canonical ACCOUNT_INACTIVE/PERMISSION_DENIED failures. ASSIGN normalizes
  IDs, locks requested User rows in ascending order, and revalidates that every
  ID exists and is active HELPDESK before creating Task/TaskAssignees. Any
  missing, wrong-role, inactive, or database failure rolls back the aggregate
  completely and R-141 reports all client-supplied violating IDs together.
- Update, status, and override acquire the Task row first. Full assignee-set
  replacement is serialized by that same lock, so two Manager edits cannot
  independently remove the last assignee or overwrite based on stale sets.
  Update then locks only newly added User rows in ascending ID order and
  revalidates them inside the same transaction, serializing assignment against
  concurrent Identity deactivation or role change.
- Status reads the latest state only after lock acquisition. The second racer
  can commit another valid edge, return the R-136 no-op, or fail with zero side
  effects. Completion wins at most once.
- Metadata, expected-Location, and assignee PATCH use the same Task lock as
  completion; if completion commits first, the later mutation re-reads
  COMPLETED and fails with zero Task/relation/history/audit delta.
- FIELD_EVIDENCE checks object storage before opening the Task transaction, then
  locks the Task and referenced uploads and revalidates mutable ownership, expiry,
  binding, scope, idempotency, and terminal state. The TaskUpdate, immutable
  candidate snapshot, photos, upload bindings, Task snapshot, idempotency record,
  and completion AuditLog commit or roll back together.
- Cleanup handles each expired unbound intent/object independently and safely on
  retry. A concurrent finalize that binds first wins; cleanup rechecks binding and
  must leave the bound object untouched.
- Integrity errors for named constraints are mapped narrowly; unknown database
  failures are not mislabeled as business conflicts.
- The frontend never automatically retries a mutation. On network ambiguity it
  keeps user-entered text and offers explicit retry/refetch; after a 409 it
  refetches the Task before enabling another action.

### Audit and outbox ownership

- Normal creation, metadata edits, assignment edits, and ordinary lifecycle
  updates rely on Task/TaskAssignee/TaskUpdate business evidence and do not add
  an AuditLog or OutboxEvent absent a governing requirement.
- FIELD_EVIDENCE appends a CHOT-approved closed completion audit action in the
  completion transaction. If the existing closed audit vocabulary has no accepted
  FIELD_EVIDENCE value, implementation stops until CHOT and the audit vocabulary
  are updated in authority order. Its payload contains only Task ID,
  previous/resulting status, completion method, completing actor ID, and server
  completion time; it contains no coordinates, candidate IDs, note, image data,
  object key, photo URL, presigned URL, or Maps URL.
- Manager override adds `task.completion.overridden` to the audit-owned closed
  action vocabulary. The record targets the Task and contains only task ID,
  previous/resulting status, completion method, completing actor ID, server
  completion time. Free-text `completion_note` remains on Task/TaskUpdate but is
  excluded from the URL-rejecting audit payload; no GPS/photo/object/URL data
  exists in the audit record.
- Feature 007 emits no outbox event. R-97 notification behavior remains a later
  feature and must define its event schema/consumer atomically before an event
  is added. Same-state and rejected paths explicitly append neither audit nor
  outbox evidence.

### Migration and compatibility

- `tasks/0001_initial.py` creates the core aggregate. `0002_task_evidence.py`
  expands it with evidence tables and nullable/default-safe TaskUpdate fields;
  `0003_task_correction.py` adds nullable/default-safe expected-place and deletion
  fields. All three migrations are expand-only and rolling-compatible with the
  immediately previous application version.
- New required fields on new tables have database defaults or are populated on
  INSERT; fields added to existing tables are nullable or safely defaulted before
  enforcement. Enum/status defaults used by the model are also database defaults
  where rolling compatibility requires them.
- Foreign keys use `PROTECT`; the Task DELETE operation is a recoverable timestamp
  update and never hard-deletes Task/evidence rows. No trigger,
  extension, sequence customization, or privileged runtime migration access is
  introduced.
- Run `migration_check.py check`, `makemigrations --check --dry-run`, migrate from
  the previous leaf, and migrate a fresh database. The app must have one leaf.

### Frontend state and integration

- `/tasks` is guarded by `task.view.self`; the existing capability implication
  means MANAGER/LEADER accounts with `task.view.all` also reach the page.
- `TaskManagementPanel` loads the grouped projection and holds closed states for
  loading, ready, empty, submitting, mutation failure, and refetch failure.
  Mutations refetch the server projection; the client never locally calculates
  authoritative group membership, overdue days, or transitions.
- Capability checks shape controls: Manager assignment/create/edit/override
  controls appear only for their exact capabilities; HELPDESK sees self-create
  and in-scope status controls; LEADER sees no mutation controls. Backend remains
  authoritative for every direct request.
- Manager assignee selection reuses `GET /api/v1/users/?role=HELPDESK&is_active=true`;
  no picker endpoint is added. The server still independently rejects inactive
  IDs. Expected Location selection reuses the existing Location list API and is
  clearly labelled planning context.
- FIELD_EVIDENCE prepares readable HEIC as JPEG when needed, compresses to a
  supported JPEG/PNG/WebP object no larger than 5 MB, stages photos independently,
  requests a new `maximumAge=0` GPS sample, and never reads EXIF GPS. The local
  draft stores only compressed photos and note under account+Task scope; it stores
  no GPS/token/object key/presigned URL and purges on verified finalize, discard,
  logout, account switch, seven-day expiry, or confirmed account disable while
  reporting quota/storage/eviction failures truthfully.
- Evidence history derives `resolved_address` only from the selected Location and
  builds the Google Maps link from the exact stored Task capture coordinates with
  `rel="noopener noreferrer"`; it performs no reverse geocoding, map SDK load, or
  EXIF-based resolution.
- Date/status/error text comes from Task UI mapping modules; unknown errors use
  the shared canonical error renderer. Forms preserve valid user input after
  recoverable failures, prevent duplicate in-flight submission, and refetch on
  conflict or successful mutation.

### Verification and CI

- Pure unit tests cover every state-matrix cell, same-state no-op, block-reason
  normalization, completion snapshot construction, group exclusivity/order,
  timezone midnight, and overdue-day derivation.
- API/integration tests cover RBAC-before-DTO precedence, exact create grants,
  creator-or-assignee scope, Leader read-only, IDOR-safe detail/mutations,
  self-create vs assignment DTOs, immutable date, inactive additions, retained
  inactive assignees, completed freeze, and canonical errors.
- PostgreSQL tests inspect constraints/indexes, force rollback after update/audit
  append, race valid chained transitions, race invalid/terminal transitions,
  race override against metadata/Location/assignee PATCH, race full assignee-set
  replacement, and race assignment against Identity deactivation/role change.
- Contract tests require explicit stable operation IDs, additive OpenAPI changes,
  exact response/error shapes, deterministic regeneration, and generated
  TypeScript usage through `apiClient`/`authenticatedFetch`.
- Frontend tests cover four-group ordering, overdue labels, future exclusion,
  role-shaped controls, form validation, block/override flows, loading/error
  recovery, no automatic mutation retry, and navigation registration.
- Evidence unit/API/contract/PostgreSQL tests cover 1–5 photo bounds, HEIC
  conversion, JPEG/PNG/WebP, 5 MB size, checksum/MIME/HEAD validation,
  owner/Task/expiry/bound state, GPS freshness and quality, candidate recompute
  and immutable snapshots, idempotency pre-commit/committed behavior, atomic
  FIELD_EVIDENCE audit, protected photo reads, and cleanup/finalize races.
- Frontend evidence tests cover partial-upload resume, every local-draft purge and
  storage-failure case, no sensitive draft fields, exact captured-coordinate Maps
  links, Location-only resolved addresses, and absence of reverse geocoding,
  external map SDKs, and EXIF GPS behavior.
- Existing quality and contract workflows remain the infrastructure. Only their
  hardcoded backend module lists are extended with `backend/tasks`; no workflow,
  service, database, broker, or deployment resource is added.
- A controlled PostgreSQL capacity harness records 100 authorized Task-list
  reads at representative data volume and requires p95 below two seconds for
  SC-010; it is release evidence, not a wall-clock CI unit test. SC-011 uses a
  committed moderated-review protocol/evidence artifact for 10 representative
  users and may be marked passed only from recorded participant outcomes.

## Complexity Tracking

No constitution violation requires justification.
