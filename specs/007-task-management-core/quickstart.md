# Quickstart: Task Management Core

**Feature**: 007 | **Branch**: `feature/007-task-management` | **Date**: 2026-08-20

This is the implementation/acceptance validation guide. Feature 007 is complete
only when Task business behavior, PostgreSQL transactions, generated contracts,
and the employee UI agree.

## Prerequisites

- PostgreSQL configured through the repository's existing typed environment.
- Current migrations and canonical seed/reference data applied.
- Accounts for one MANAGER, one LEADER, three active HELPDESK users, and one
  inactive HELPDESK user.
- At least one existing Location for expected planning context.
- Backend and frontend dependencies installed with the existing lockfiles. No
  new runtime dependency should appear.

## Start the application

```bash
# from repository root after loading the untracked runtime environment
cd backend
uv run python manage.py migrate
uv run python manage.py runserver

# second terminal
cd frontend
npm install
npm run dev
```

Open `/tasks`. The employee shell must show Tasks only when the authenticated
account has effective `task.view.self` capability.

## Automated verification

```bash
# repository quality/type/architecture gates
uv run --project backend ruff check backend scripts
uv run --project backend mypy backend/core backend/config backend/operations \
  backend/identity backend/audit backend/locations backend/attendance backend/tasks scripts

# backend Task tests (PostgreSQL is mandatory for integration/race proof)
cd backend
uv run pytest tests/unit/tasks tests/integration/api/tasks tests/contract/tasks -v
uv run pytest tests/integration/postgres/tasks -v
uv run pytest tests/architecture/test_task_feature_boundary.py -v
uv run python manage.py cleanup_task_evidence_uploads --limit 500

# migration and generated contract gates
cd ..
uv run --project backend python scripts/migration_check.py check
cd backend
uv run python manage.py makemigrations --check --dry-run
cd ../frontend
npm run api:check
npm run test
npm run lint
npx tsc --noEmit
```

Expected: every command is green, `makemigrations` reports no model drift, and
`api:check` reports no backend/OpenAPI/client drift. The checked-in canonical
OpenAPI and TypeScript schema must have been generated, never hand-edited.

## Scenario 1 — Manager create with multiple assignees

1. Sign in as MANAGER and open Tasks.
2. Create a Task with title, optional description, a past/today/future
   `assigned_date`, one expected Location, and two active HELPDESK users.
3. Inspect the response/detail.

Pass criteria:

- one Task exists in TODO;
- creator is the authenticated Manager;
- exactly two unique TaskAssignee rows exist, even if an ID was duplicated in
  the request;
- each `assigned_at` is server-owned;
- expected Location is planning context only;
- no TaskUpdate exists just for creation;
- no photo/GPS/evidence row or request exists for ordinary status changes; all
  evidence is created only through a specialized completion operation.

## Scenario 2 — Helpdesk arising self-create

1. Sign in as active HELPDESK.
2. Create an arising Task without selecting an assignee.
3. Attempt another create with `assignee_ids` in the raw payload.

Pass criteria:

- first request creates the actor as creator and sole initial assignee;
- second request fails after action authorization but at DTO ownership
  validation, and creates no Task or TaskAssignee;
- Helpdesk UI contains no coworker assignment control.

## Scenario 3 — Inactive assignment is atomic

1. As Manager, create with one active, one inactive, one wrong-role, and one
   nonexistent assignee ID.
2. Confirm `422 INACTIVE_ASSIGNEE` includes every violating ID once in ascending
   order.
3. Create a valid Task for an active user, deactivate that user through the
   existing identity flow, then edit only the Task description.
4. Remove the inactive assignee while leaving another active assignee, then try
   to add the inactive ID again.
5. On PostgreSQL, race Helpdesk SELF create against actor deactivation and role
   change in both lock orders.

Pass criteria:

- mixed create leaves zero Task/TaskAssignee rows;
- deactivation itself leaves the existing relation/status/date unchanged;
- unrelated metadata edit succeeds while the inactive relation is retained;
- removal succeeds only while at least one assignee remains;
- re-add fails atomically with INACTIVE_ASSIGNEE.
- SELF create that loses the actor lock race returns canonical
  ACCOUNT_INACTIVE/PERMISSION_DENIED with no Task; SELF create that commits first
  leaves a valid historical link when the account change commits afterward.

## Scenario 4 — Canonical matrix and BLOCKED reason

Exercise every matrix cell at the pure domain layer and representative API
paths in both creator/assignee SELF and Manager ANY scope.

```text
TODO        -> IN_PROGRESS, BLOCKED
IN_PROGRESS -> BLOCKED
BLOCKED     -> IN_PROGRESS
```

Pass criteria:

- each allowed edge inserts one TaskUpdate and makes all six Task snapshot
  fields equal the latest update;
- TODO/IN_PROGRESS/BLOCKED same-state requests return 200 and change no row,
  audit, outbox, or aggregate version;
- same-state BLOCKED requires no repeated reason;
- entering BLOCKED with missing/whitespace reason returns
  `422 BLOCK_REASON_REQUIRED` and changes nothing;
- BLOCKED → IN_PROGRESS keeps the old reason in history and clears the current
  Task.block_reason;
- invalid edges return VALIDATION_FAILED with no history;
- ordinary target COMPLETED is rejected and cannot bypass the completion path.

## Scenario 5 — Manager override and terminal freeze

1. As Manager, complete a nonterminal Task through complete-override with a
   nonblank `completion_note`.
2. Inspect Task, latest TaskUpdate, and AuditLog inside PostgreSQL.
3. Retry override; then attempt status, title, description, expected Location,
   and assignee changes as Manager, Helpdesk, and Leader.

Pass criteria:

- one COMPLETED/MANAGER_OVERRIDE TaskUpdate exists;
- Task.completed_by/completed_at/method/note/status match that update;
- exactly one `task.completion.overridden` AuditLog committed with the same
  transaction, containing only ID/status/method/actor/time metadata and no
  free-text completion note;
- a valid completion note containing `https://` succeeds and remains on
  Task/TaskUpdate without entering AuditLog;
- Manager override without uploads creates zero photo/GPS rows and zero
  OutboxEvent; FIELD_EVIDENCE uses its separate governed path;
- override retry returns `409 TASK_ALREADY_COMPLETED`; ordinary terminal
  mutations return `400 VALIDATION_FAILED` (or an earlier 403 for an actor
  lacking the action), all with no duplicate evidence;
- reads remain available under their normal scope.

## Scenario 6 — Self scope and Leader read-only

For one Task, test its creator, one assignee, unrelated Helpdesk, Manager,
Leader, and anonymous caller.

Pass criteria:

- creator OR assignee can read and perform allowed core status/content updates;
- unrelated Helpdesk gets a scope-safe not-found response and no side effect;
- Manager reads/updates any Task but cannot violate the matrix, assignment
  eligibility, immutable date, or terminal rule;
- Leader reads all Tasks and sees no mutation controls, while every direct
  mutation call returns 403 before malformed-body details leak;
- anonymous calls fail before Task lookup.

## Scenario 7 — Assigned date is immutable and overdue is derived

1. Create incomplete Tasks for business date minus 3 days, today, and plus 2
   days; complete another Task with an old assigned date.
2. Read the grouped list around a simulated Asia/Ho_Chi_Minh midnight.
3. Attempt to send `assigned_date` through PATCH.

Pass criteria:

- arrays are presented Overdue, Today, Upcoming, Completed;
- every Task is in exactly one array;
- old incomplete Task retains its original date and returns
  `overdue_days = 3` for that business date;
- non-overdue Tasks return null rather than a positive overdue value;
- completed Task is only in Completed regardless of assigned date;
- after midnight the projection changes on read while no Task row is updated;
- PATCH rejects assigned_date as server-owned and the stored date is unchanged.

## Scenario 8 — Competing status requests (PostgreSQL only)

Use `pytest.mark.django_db(transaction=True)` and two real worker connections.

1. Race TODO → IN_PROGRESS and target BLOCKED. Arrange lock order so the second
   reads the first committed state.
2. Race two requests that result in the same target after the first commit.
3. Race override completion against another transition/override and separately
   against metadata, expected-Location, and assignee PATCH requests.
4. Race create/update assignment against Identity deactivation and role change.

Pass criteria:

- valid resulting sequence commits two ordered TaskUpdates;
- same resulting state makes the later request a no-op;
- invalid resulting edge makes the later request fail without update/audit;
- only one completion TaskUpdate/AuditLog exists;
- a mutation losing to completion and an assignment losing to identity change
  re-read committed state and leave zero partial deltas;
- no test cites SQLite, a mock lock, or request timing as proof.

## Scenario 9 — Transaction rollback

Force an exception after TaskUpdate insertion and, separately, after the Manager
override AuditLog append but before transaction exit.

Pass criteria:

- Task snapshot, TaskUpdate, assignee delta, and AuditLog all roll back together;
- no OutboxEvent is present;
- a rejected mixed inactive assignment leaves no partial relation;
- unknown database failures remain infrastructure failures rather than being
  mislabeled as business errors.

## Scenario 10 — Frontend state and retry behavior

1. Exercise loading, empty, ready, submit-in-flight, validation error, 409
   conflict, network ambiguity, successful mutation, and refetch failure.
2. Inspect controls for Manager, Helpdesk, and Leader capability sets.

Pass criteria:

- the server's grouped arrays and overdue values are rendered without local
  authoritative regrouping;
- duplicate submit is disabled while a mutation is in flight;
- the client never automatically retries a create/PATCH/status/override;
- user-entered note/content survives a recoverable failure;
- success and 409 trigger a fresh Task read before new actions;
- Manager uses the existing active HELPDESK user query and existing Location
  query; no picker transport exists;
- Leader has a useful read-only list/detail, not disabled mutation buttons.

## Scenario 11 — Migration compatibility

Validate both a fresh database and a database at all pre-Feature-007 leaves.

Pass criteria:

- migrations create only the six governed `tasks_*` tables and their additive
  constraints/indexes;
- previous application code runs after migration because no old table changed;
- app has one migration leaf;
- rollback of the migration drops only the new unused tables in a controlled
  validation database;
- runtime code never reads a privileged migration connection.

## Scenario 12 — MVP list performance acceptance

Run `scripts/task_list_capacity_check.py` against the controlled PostgreSQL
dataset for approximately 50 users and representative task histories. Capture
100 authorized list reads and write the environment/workload summary plus
percentiles to `evidence/task-list-performance.md` without credentials or user
identities.

Pass criteria: at least 95 reads return the complete four-group projection in
under two seconds and measured p95 is below two seconds. This release evidence
does not become a timing-sensitive CI unit test.

## Scenario 13 — Four-group usability acceptance

Moderate the four-group interpretation scenario with at least 10 representative
users and record only aggregate role/count/time/pass data in
`evidence/task-list-usability.md`; never fabricate participant results or store
identity/GPS data.

Pass criteria: at least 9 of 10 independently identify overdue, today, upcoming,
and completed work without assistance.

## Scenario 14 — FIELD_EVIDENCE upload and finalize

1. As an in-scope HELPDESK user, create intents for two valid compressed images.
2. Upload one image successfully, simulate failure on the second, then resume
   without uploading the successful image again.
3. Upload the remaining image, capture a fresh GPS sample, and finalize with an
   `Idempotency-Key`.
4. Retry the same normalized request/key, then retry that key with a changed
   payload. Repeat with cross-user, cross-Task, expired, already-bound, wrong
   checksum/MIME/size, zero-photo, and six-photo inputs.
5. Exercise GOOD GPS with zero, one, and multiple Location candidates plus
   LOW_ACCURACY and UNRELIABLE samples.

Pass criteria:

- staging never changes Task state and partial upload success is reusable;
- valid finalize atomically commits one TaskUpdate, 1-5 TaskPhotos, Task snapshot,
  intent bindings, idempotency result, and exactly one privacy-safe
  `task.completion.field_evidence` AuditLog in the same transaction;
- identical retry returns that result; changed payload returns
  IDEMPOTENCY_CONFLICT without deltas;
- Location-choice/invalid-choice responses do not consume the key;
- GOOD GPS with multiple current candidates cannot commit without a currently
  valid user selection; the committed candidate-ID snapshot never changes when
  the Location catalog, active flag, coordinates, or radius changes later;
- weak Task GPS warns but may complete with GPS_ONLY and no verified Location;
- no object key or presigned URL appears in Task responses, audit, or logs;
- authorized photo access returns a short-lived URL and denied access returns no
  URL or storage metadata.
- AuditLog/outbox/telemetry contain no note, image/photo data, upload/object key,
  presigned/Maps URL, candidate list, or precise GPS coordinates.

## Scenario 15 — Responsive role-aware UI

Use Playwright at 360 px and 1280 px for login, change password, Attendance,
Tasks, users, locations, holidays, config, and job-health with the applicable
HELPDESK, MANAGER, and LEADER sessions.

Pass criteria:

- each route has one shared current-page header and only role-allowed navigation;
- Tasks and Attendance are simultaneously visible in phone navigation without
  horizontal scrolling;
- `document.documentElement.scrollWidth <= clientWidth` on every page;
- cards/forms use consistent width and action spacing; long content wraps;
- status uses semantic badges and descriptions use secondary typography;
- keyboard focus, labels, busy/disabled states, and touch targets pass automated
  checks with zero critical accessibility violations.

## Completion checklist

- [X] Manager create and multi-assignee behavior passes
- [X] Helpdesk self-create and assignee-field rejection passes
- [X] Inactive new assignment is atomic; historical inactive relation survives
- [X] Every state-matrix cell and no-op semantics pass
- [X] BLOCKED conditional reason and resume history pass
- [X] Manager override is audited and atomic; zero-photo/no-GPS remains valid
- [X] FIELD_EVIDENCE upload/finalize/idempotency/photo access passes
- [X] COMPLETED is terminal and fully read-only
- [X] Creator-or-assignee self scope and Leader read-only pass
- [X] Assigned date stays immutable; grouping/overdue derive at read time
- [X] PostgreSQL lock, race, constraint, and rollback tests pass
- [X] Controlled Task-list capacity evidence passes SC-010
- [ ] Recorded 10-user moderated review passes SC-011
- [X] No Task outbox/notification feature leaked into scope
- [X] Every route passes responsive role-aware UI verification
- [X] OpenAPI/client generation and compatibility checks pass
- [X] Frontend route, capability controls, explicit retry, and refetch pass
- [X] Migration safety, architecture boundaries, lint, types, and CI pass

## Scenario 16 — Free expected place, form reset, self-delete, and safe GPS validation

1. As HELPDESK, create a self task with an expected place not present in the
   Location catalog and verify the returned/listed text plus cleared create form.
2. Delete that task and verify list/detail no longer expose it while Task,
   assignment, and one privacy-safe audit record remain in PostgreSQL.
3. Verify another actor, a Manager-created task, and a completed task cannot be
   deleted and create no audit delta.
4. Finalize evidence using latitude/longitude with 15 decimal places; then send
   invalid protected GPS input and verify a redacted canonical 400, never 500.
5. Complete outside known Locations and verify stored coordinates, accuracy
   context, resolution label, and the Google Maps action in history.

Pass criteria: all five flows pass without hard deletion, Location creation,
coordinate disclosure in errors, repeated upload, or internal-server response.

## Scenario 17 — Draft, cleanup, and evidence presentation lifecycle

1. Select and process 1–5 supported images plus a note, reload the same account
   and Task, then inspect browser storage before any submit.
2. Repeat with another Task and account; simulate unavailable storage, quota,
   browser eviction, seven-day expiry, discard, verified finalize, logout,
   account switch, and account disable.
3. Create expired/unexpired/bound staging intents, make one object deletion fail,
   run `cleanup_task_evidence_uploads`, retry it, and race cleanup against finalize.
4. Read FIELD_EVIDENCE history for a selected Location and for GPS_ONLY.

Pass criteria:

- local draft contains only re-encoded/compressed photo bytes, safe file metadata,
  note, and expiry under an account+Task key; it contains no GPS, auth value,
  upload ID/token, object key, presigned URL, or idempotency key;
- UI truthfully reports unavailable/quota/evicted storage and never claims an
  unsaved draft; every required purge event removes only the intended scope;
- cleanup deletes only seven-day expired unbound objects/intents, is idempotent,
  retains failed intents for retry, rechecks under a row lock, and never deletes a
  bound TaskPhoto object regardless of finalize race order;
- `resolved_address` is the selected Location name+address or null without any
  reverse geocoding; `maps_url` is derived from the exact stored capture pair;
- the Maps action uses `target="_blank"` plus `rel="noopener noreferrer"`; no map
  SDK/embed, Location coordinates, or EXIF GPS is used for presentation.
