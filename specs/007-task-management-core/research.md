# Phase 0 Research: Task Management Core

**Feature**: 007 | **Date**: 2026-08-20

This research resolves implementation choices against the authority chain and
the existing repository. It introduces no new business decision.

## 1. Module ownership and composition

**Decision**: Add a peer Django app `tasks` with `domain`, `application`,
`ports`, and `adapters`. Wire it in `config/composition.py` and add
`config/task_adapters.py` for identity and Location access.

**Rationale**: Task is a distinct aggregate with a state machine, history,
scope, persistence, and transaction rules. Attendance and Locations already
establish the approved module pattern. The constitution prohibits Task
production code from importing another module's model/domain/adapter; `config/`
is the approved composition-root exception.

**Alternatives rejected**:

- Put Task models/services in Attendance: conflates work tracking with payroll
  event ownership and creates the wrong dependency direction.
- Put Task rules in `core`: expands the shared kernel with business policy.
- Import `identity.models.User` or `locations.models.Location` in Task services:
  violates the module boundary. Django string FKs remain persistence metadata;
  business reads go through Task-owned ports.

## 2. Authorization modes

**Decision**: A Task authorization port returns closed typed modes:
`TaskCreateMode.SELF|ASSIGN`, `TaskReadScope.SELF|ALL`, and
`TaskUpdateScope.SELF|ANY`. The composition adapter requests the canonical base
action from `DjangoAuthorizationGateway`, inspects `granted_by`, and maps it to
the Task-owned type. Override completion requests its exact action and has global
Task scope. API permission gates execute this before serializer validation.

For `POST /tasks/`, the gate resolves exactly one direct action before DTO
validation: MANAGER has only `task.create.assign` and HELPDESK has only
`task.create.self` under R-140. The selected mode chooses the serializer shape
without inspecting the body. For read/update, request the
`.self` action and use the existing closed implication result to recognize
`.all`/`.any`.

**Rationale**: Identity already owns roles, actions, implications, active account
state, and password-change gating. Tasks needs only a typed access result and
must never reinterpret roles. This preserves RBAC-before-DTO and keeps Manager
assignment distinct from HELPDESK self-create semantics.

**Alternatives rejected**:

- Role checks in Task views/services: duplicates the canonical matrix.
- Let frontend choose a self/assign endpoint: CHOT defines one POST endpoint and
  backend authority.
- Parse `assignee_ids` to decide which permission to check: body-dependent RBAC
  would run after DTO and violate the required order.

## 3. API surface and list representation

**Decision**: Add six operations under the existing `/api/v1/` composition:

- `GET /tasks/` — grouped projection with keys `overdue`, `today`, `upcoming`,
  `completed` in that canonical order, plus server `business_date`.
- `POST /tasks/` — mode-specific create.
- `GET /tasks/{task_id}/` — scoped detail including lifecycle updates.
- `PATCH /tasks/{task_id}/` — metadata and, only in ANY mode, full assignee-set
  replacement. It never accepts `assigned_date` or status.
- `POST /tasks/{task_id}/status` — ordinary nonterminal status operation.
- `POST /tasks/{task_id}/complete-override` — note-only Manager completion.

Use string path converters so action permission precedes identifier parsing and
scope-safe repository lookup returns `404 NOT_FOUND` for absent/out-of-scope
objects. Responses use `snake_case`, explicit stable operation IDs, canonical
error envelopes, and `private, no-store`.

**Rationale**: CHOT §10 already names create/update/status/override. Detail is
required to display append-only history; list is required by the feature. One
server-grouped response makes exclusivity and derived overdue values canonical
and avoids four independent reads around a local-midnight boundary.

**Alternatives rejected**:

- Four list endpoints or a client-side grouping pass: risks different business
  dates and duplicates server-owned classification.
- Status inside PATCH: could bypass the transition use case and completion gate.
- Defer evidence/upload/complete-field: rejected by the accepted Feature-007
  scope extension and synchronized R-137 authority trace.

## 4. Task aggregate and lifecycle persistence

**Superseded scope detail (2026-08-20)**: Feature 007 retains `Task`,
`TaskAssignee`, and `TaskUpdate` as its aggregate core and now expands
TaskUpdate with FIELD_EVIDENCE fields plus EvidenceUpload, TaskPhoto, and
CompletionIdempotency tables. The original migration stays immutable; the
extension is a rolling-compatible second expand migration.

Creation initializes Task status to TODO and creates no synthetic lifecycle
transition. Each later successful transition inserts one TaskUpdate and updates
all snapshot fields in the same transaction. TaskUpdate has insert-only
repository/API semantics.

**Rationale**: R-84 defines Task as a current projection of immutable history.
The accepted scope extension now uses the previously planned nullable-column
expand path and keeps existing rows valid.

**Alternatives rejected**:

- Derive current state from `MAX(TaskUpdate.id)` on every list read: contradicts
  the approved snapshot model and harms the primary query.
- Store per-assignee status: creates two lifecycle sources of truth.
- Keep evidence deferred: no longer satisfies FR-031/FR-035–FR-043.

## 12. Private evidence storage and transaction boundary

**Decision**: Use `django-storages[s3]`/boto3 behind a Task-owned storage port.
Production objects live in a private S3/R2 bucket. The adapter creates 15-minute
presigned PUT/GET operations and HEAD-verifies MIME, size, checksum, and object
existence. Network validation completes before database locks; the finalize
transaction then locks Task and selected EvidenceUpload rows and revalidates
owner/Task/state before inserting TaskUpdate/TaskPhoto/idempotency and binding
the uploads.

**Rationale**: This follows CHOT §6.2/§9.1 and Constitution V/IX: private bytes,
short transactions, no stored URL, and atomic business binding without trying to
make object storage part of a database transaction. Fakes implement the same port
for unit/contract tests; production configuration fails closed.

**Alternatives rejected**:

- Upload through Django request bodies: increases API memory/bandwidth pressure
  and makes partial retry expensive.
- Hold a row lock during PUT/HEAD: violates the external-network transaction rule.
- Store presigned URLs: creates expiring credentials in persistence/logging risk.

## 13. Shadcn UI integration with the existing design system

**Decision**: Adopt shadcn UI's source-owned composition and variant conventions
for Button, Badge, Card, Input, Textarea, Select, Field, PageHeader, and muted
Typography, while binding them to existing MobiFone CSS variables. Tailwind is
introduced only for shadcn component utilities; existing scoped CSS Modules are
retained where they express complex feature layouts. Shared shell/header and
navigation own page identity and responsive constraints for every route.

**Rationale**: Source-owned primitives meet the user's shadcn request without
forking page-specific styles. Tokens preserve the established brand, CSS Modules
coexist under Next.js 16 guidance, and incremental adoption limits regression
risk across already-tested features.

**Alternatives rejected**:

- Restyle each page directly: duplicates spacing/status/typography decisions.
- Replace every feature stylesheet at once: unnecessary risk with no user value.
- Keep generic global `.actions`/`.form-grid` only: cannot encode semantic
  variants, field descriptions, or maintainable component contracts.

## 5. PostgreSQL constraints and indexes

**Decision**:

- Closed check constraints for Task/TaskUpdate statuses and completion method.
- Nonblank Task title; nonblank `block_reason` when status is BLOCKED.
- Task snapshot shape: BLOCKED iff current block reason is nonblank; COMPLETED
  requires `completed_by`, `completed_at`, MANAGER_OVERRIDE, and nonblank
  completion note; noncompleted rows require completion fields null.
- TaskUpdate shape mirrors the applicable resulting status/method/note rules.
- `UNIQUE(task_id,user_id)` for TaskAssignee.
- Index Task on `(status, assigned_date, id)` for grouping/order; on
  `(created_by_id, status, assigned_date, id)` for creator scope; TaskAssignee on
  `(user_id, task_id)` for assignee scope; TaskUpdate on `(task_id, id)` for
  history. Foreign-key indexes remain enabled.

At-least-one-assignee is a cross-table aggregate invariant, not a portable check
constraint. The service rejects empty normalized sets and performs full-set
replacement while holding the Task row lock; PostgreSQL unique/FK constraints
are the final protection for duplicate and referential races.

**Rationale**: These constraints protect independently checkable row shapes and
the concurrency-sensitive uniqueness invariant without adding triggers or a new
database facility. The query indexes follow the actual scope/group predicates.

**Alternatives rejected**:

- Persist `overdue_days`, group, `original_assigned_date`, carried-over count, or
  due date: prohibited by R-86.
- PostgreSQL trigger for every service invariant: no approved repository pattern
  requires it, and it would duplicate the domain matrix.
- Task optimistic version: explicitly rejected by R-138.

## 6. Assignee eligibility and replacement

**Decision**: Normalize `assignee_ids` by stable de-duplication. Manager create
validates every normalized ID as an active HELPDESK user. Manager PATCH treats
the array as the desired full set, locks the Task, computes additions/removals,
validates only additions, rejects an empty set, then applies the delta in the
same transaction. A retained inactive assignee is never revalidated. Removing
and later adding that inactive ID counts as a new addition and is rejected.

HELPDESK create uses a serializer that rejects `assignee_ids` as a server-owned
field and application logic creates exactly the actor relation. HELPDESK update
uses a serializer that does not expose assignee management.

**Rationale**: This is R-66/R-135 exactly, is atomic for mixed valid/invalid
input, and supports deterministic concurrency under the Task row lock.

**Alternatives rejected**:

- Silently drop duplicates/inactive users and partially succeed: hides client
  errors and violates atomic rejection.
- Revalidate all retained assignees: freezes every Task after an assignee leaves.
- Signal on account deactivation: destroys historical/current assignment data.

## 7. Expected Location semantics

**Decision**: Store one nullable `location_id` with `PROTECT`. Resolve an
existing Location through a Task-owned port and return a small display snapshot.
The core feature adds no active-Location invariant beyond what the accepted spec
states; the UI uses the existing Location list and presents this field as
planning context. Inactivation later never rewrites a Task.

**Rationale**: CHOT distinguishes `Task.location` from user assignment,
Attendance validation, and future actual evidence Location. The spec does not
approve rejecting an existing inactive expected Location, and explicitly leaves
new behavior for changing such a Location outside this feature.

**Alternatives rejected**:

- Import geofence/Attendance policy or require GPS: wrong domain semantics.
- Snapshot Location name/address into Task: creates a second Location source of
  truth not required for historical attribution.

## 8. State machine, no-op, and terminal semantics

**Decision**: Implement the matrix once as a pure domain function returning
`TRANSITION`, `NO_OP`, or rejection. Ordinary status input enum contains only
TODO, IN_PROGRESS, and BLOCKED. Entering BLOCKED requires a trimmed
`block_reason` or note; same-state BLOCKED is checked for no-op before the
conditional-reason rule, but only after permission, DTO shape, and scope have
passed. Leaving BLOCKED clears Task.block_reason while the old reason remains on
the TaskUpdate row. COMPLETED is rejected before every mutation.

**Rationale**: Direct encoding of R-136/R-137/R-139 prevents endpoints and roles
from inventing exceptions.

**Alternatives rejected**:

- Append history on same-state retry: creates false business evidence.
- Allow COMPLETED in ordinary status schema: bypasses completion action/note/audit.
- Reopen or correction through PATCH: explicitly future governance work.

## 9. Transaction and concurrency model

**Decision**: Each command owns one `transaction.atomic` via a Task unit-of-work.
Update/status/override first lock the Task with `select_for_update`, then load the
current assignee set/state and re-evaluate every invariant. Status races are
linearized on that row. Override locks the same row, so only the first request
can observe nonterminal state and create completion history/audit.

Assignee full-set replacement also uses the Task lock. After that lock, update
computes newly added IDs, locks the corresponding Identity User rows in ascending
ID order through the Task-owned eligibility port, and revalidates existence,
HELPDESK role, and active state. Create has no existing aggregate to lock:
ASSIGN locks normalized requested User rows in ascending ID order, while SELF
locks the actor User row and re-runs direct authorization under that lock,
mapping deactivation to ACCOUNT_INACTIVE and lost action to PERMISSION_DENIED.
It then creates the Task. Task rows, relations, and eligibility reads share one transaction;
unique/FK constraints remain final guards. This serializes assignment against
concurrent account deactivation or role change.

**Rationale**: This exactly implements R-138 and uses the same explicit
unit-of-work pattern as current modules. No external call is held in a
transaction; identity/Location lookups are local PostgreSQL reads and mutable
Task state is revalidated after locking.

**Alternatives rejected**:

- Pre-check status outside the transaction: race permits duplicate/invalid
  transitions.
- Optimistic version/expected-version: explicitly outside Feature 007.
- Catch every IntegrityError as a Task conflict: masks unrelated failures.

## 10. Retry and idempotency ownership

**Decision**: Do not add a generic mutation retry or Idempotency-Key facility.
The client suppresses duplicate in-flight submission and does not automatically
retry POST/PATCH. If delivery is ambiguous, it refetches and lets the user retry
explicitly. Status retries are semantically safe only as specified by R-136 and
R-138. Repeated/competing completion returns `409 TASK_ALREADY_COMPLETED` after
the first commit.

**Rationale**: Only future `complete-field` has an approved Idempotency-Key
contract. Pulling it into create/update/override would be a new business/API
decision. Database transactions already guarantee all-or-nothing server
execution, not at-most-once network delivery for create.

**Alternatives rejected**:

- Automatically retry all failed mutations: could create duplicate Tasks after
  a lost successful response.
- Reuse the future evidence idempotency table: implements deferred scope.

## 11. Audit and outbox

**Decision**: Add one audit action, `task.completion.overridden`, and append one
AuditLog for successful Manager override inside the completion transaction. Its
payload contains only IDs, previous/resulting status, completion method, actor,
and server time; the unrestricted business `completion_note` remains on
Task/TaskUpdate and is deliberately excluded from the URL-rejecting audit
payload filter.
Normal core create/edit/assignment/status actions produce canonical business
rows but no AuditLog unless a governing requirement later adds one. No Task
OutboxEvent is emitted in Feature 007.

**Rationale**: CHOT/R-137 explicitly mandates audit for Manager override and
R-13 requires audit for task correction, which this feature does not implement.
The spec excludes notification behavior; although R-97 describes a future
notification product, Feature 007 has no approved event type/payload/consumer
contract. An unconsumed guessed outbox event would expand scope. The existing
AuditRecorder joins caller transactions and already validates payload safety.

**Alternatives rejected**:

- Emit guessed `task.assigned`/`task.updated` events: no Feature-007 event schema
  is approved.
- Put audit after commit: violates atomic evidence.
- Audit same-state/rejected calls: prohibited by R-136/R-139.

## 12. Error semantics

**Decision**: Add only the three Task codes already governed by CHOT:
`INACTIVE_ASSIGNEE` (422 with all missing, wrong-role, or inactive IDs under
R-141), `BLOCK_REASON_REQUIRED` (422), and `TASK_ALREADY_COMPLETED` (409 for the
dedicated override endpoint). Unsupported ordinary target COMPLETED, invalid
matrix edges, and ordinary mutations of a terminal Task use existing
`400 VALIDATION_FAILED` with field details; authorization uses existing 401/403
codes. Every response uses the shared envelope and request ID.

**Rationale**: The error vocabulary is closed. Introducing
`INVALID_TASK_TRANSITION` or `ASSIGNEE_REQUIRED` without governance would silently
make a new contract decision. Unconditionally required/invalid fields belong to
normal validation; only the governed conditional rules receive dedicated codes.

**Alternatives rejected**:

- Invent new error codes during planning: violates source-of-truth governance.
- Return 200 for mutations on COMPLETED: contradicts terminal read-only semantics.

## 13. Frontend ownership

**Decision**: Add `features/tasks` using the repository's generated-client
wrapper + React hook + presentational composition pattern. The server owns list
grouping, overdue values, action authorization, and transition results. The
client owns transient form/async state, explicit retry, control visibility by
capability, and accessible presentation. Successful mutations and 409 conflicts
trigger a refetch.

Use the existing employee shell and mark its predeclared Tasks navigation entry
implemented. Add `tasks` to `IdentityRouteBoundary` with
`task.view.self`. Manager assignee options reuse the existing user-list filters;
expected Location options reuse the existing location API.

**Rationale**: No state library exists or is needed at MVP scale. This preserves
`authenticatedFetch` as the only transport and avoids client authority.

**Alternatives rejected**:

- Add React Query/Redux: unnecessary new dependency/infrastructure.
- Optimistically move cards between groups: can display a state the server
  rejected after concurrent mutation.
- Add a Task-specific assignee picker endpoint: forbidden by R-81.

## 14. Migration, testing, and CI

**Decision**: Ship the expand-only `tasks/0001_initial.py`,
`0002_task_evidence.py`, and corrective expand-safe `0003_task_correction.py`;
no pre-Feature-007 table is altered. Verify fresh and previous-leaf migration, one migration leaf, model
drift, constraints/indexes, and rollback/race behavior on PostgreSQL. Extend the
existing hardcoded Ruff/mypy/function-length/module-boundary lists to include
`backend/tasks`; use the current quality/contract workflows rather than adding
CI infrastructure.

Tests are layered:

- unit: matrix, no-op, reason normalization, snapshot shape, group/order/date;
- API/application: permission precedence, serializer ownership, exact create mode,
  self scope, Leader deny, error shape;
- PostgreSQL: constraints, atomic mixed assignment failure, inactive-history
  retention, lifecycle/audit/evidence rollback, status/override/metadata/assignee,
  cleanup/finalize, and candidate-recompute races, plus assignment versus Identity
  deactivation/role-change races;
- contract: explicit operation IDs, additive OpenAPI, generated TS schema;
- frontend: grouped rendering, role-shaped controls, forms, failure/refetch;
- end to end: Manager create/multi-assign/override, Helpdesk self-create/status,
  Leader read-only, overdue rollover.

**Rationale**: The mechanism proving a database or concurrency promise must be
the real PostgreSQL mechanism; pure policy stays fast and framework-free.

**Alternatives rejected**:

- SQLite/mocked concurrency proof: constitution explicitly forbids it.
- New workflow/service: existing gates already cover the required checks.

## Resolved status

No `NEEDS CLARIFICATION` remains. Decisions R-135–R-143 and the synchronized
CHOT/QUY_TAC/PRD/spec close the feature's business ambiguities. Choices above
that are implementation details reuse existing approved patterns and do not
change the governing behavior.
