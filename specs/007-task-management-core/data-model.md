# Phase 1 Data Model: Task Management Core

**Feature**: 007 | **Date**: 2026-08-20 | **Database**: PostgreSQL

Feature 007 owns one Task aggregate with six tables: the original Task,
TaskAssignee, and TaskUpdate tables plus private-upload intents, immutable Task
photos, and committed completion-idempotency records. Notifications remain out
of scope.

## Canonical enums

### TaskStatus

| Value | Meaning |
|---|---|
| `TODO` | Work has not started |
| `IN_PROGRESS` | Work is in progress |
| `BLOCKED` | Work cannot proceed; current `block_reason` is required |
| `COMPLETED` | Terminal, fully read-only record |

### CompletionMethod

| Value | Feature 007 persistence |
|---|---|
| `MANAGER_OVERRIDE` | Manager-only exceptional completion; nonblank note, no photos or GPS |
| `FIELD_EVIDENCE` | Creator-or-assignee completion; 1-5 photos and fresh GPS required |

Both values are persisted by dedicated completion operations. Ordinary status
updates still cannot target COMPLETED.

### TaskListGroup (derived, not persisted)

`OVERDUE`, `TODAY`, `UPCOMING`, `COMPLETED`, in that presentation order.

## Entity: Task

Current aggregate snapshot and editable planning content.

| Field | PostgreSQL/Django shape | Required | Ownership and rule |
|---|---|---:|---|
| `id` | `BigAutoField` | yes | server primary key |
| `title` | `TextField` | yes | client on create/update; trimmed, not blank |
| `description` | `TextField(blank=True)` | no | client on create/update; empty string is allowed |
| `created_by_id` | FK → user, `PROTECT` | yes | authenticated actor, immutable |
| `assigned_date` | `DateField` | yes | client on create; immutable thereafter; past/today/future valid |
| `status` | `CharField`, DB default `TODO` | yes | server/domain only; closed TaskStatus |
| `location_id` | nullable FK → Location, `PROTECT` | no | expected planning Location, not evidence or attendance assignment |
| `expected_location_text` | `TextField`, default empty | no | normalized free-text planning place; independent from registered Location and GPS evidence |
| `deleted_at` | nullable timestamptz | no | server-owned soft-delete marker; normal Task queries require null |
| `completed_by_id` | nullable FK → user, `PROTECT` | no | server snapshot from latest completion update |
| `completed_at` | nullable timestamptz | no | server snapshot from latest completion update |
| `completion_method` | nullable char | no | server snapshot; MANAGER_OVERRIDE or FIELD_EVIDENCE |
| `completion_note` | nullable text | no | server snapshot; required only for MANAGER_OVERRIDE |
| `block_reason` | nullable text | no | server snapshot; nonblank exactly while BLOCKED |

### Task checks

1. `title` is not whitespace-only.
2. `status` is one of the four TaskStatus values.
3. If `status = BLOCKED`, `block_reason` is non-null/nonblank; otherwise
   `block_reason IS NULL`.
4. If `status = COMPLETED`, `completed_by_id`, `completed_at`, and one canonical
   completion method are required. MANAGER_OVERRIDE requires a nonblank
   `completion_note`; FIELD_EVIDENCE permits a nullable note and requires its
   TaskUpdate to own valid GPS plus 1-5 TaskPhoto rows.
5. If `status != COMPLETED`, all four completion fields are null.

Checks 3–5 make the six R-84 snapshot fields a coherent row. The application
still changes them only beside a TaskUpdate within one transaction.

### Task immutability and recoverable deletion

- No hard-delete API or repository operation exists. Exact Helpdesk self-delete
  sets `deleted_at` under the Task lock and appends its AuditLog atomically.
- Soft-deleted Tasks and their assignments/history/evidence remain stored but are
  absent from ordinary list, detail, mutation, completion, upload, and photo scope.
- Create sets `created_by_id` and `assigned_date`; update DTO/repository methods
  do not contain either field.
- No rollover job is created. Grouping never updates this row.
- After `status = COMPLETED`, every command rejects before changing title,
  description, Location, assignees, status, or snapshot fields.

### Task indexes

| Index | Purpose |
|---|---|
| `(status, assigned_date, id)` | four-group list predicate/order |
| `(created_by_id, status, assigned_date, id)` | creator half of SELF scope |

The Location and completed-by FKs retain Django's normal FK indexes. No index is
created for derived `overdue_days` or group because neither is stored.

## Entity: TaskAssignee

Current Task-to-user assignment relationship. It has no status.

| Field | Shape | Required | Rule |
|---|---|---:|---|
| `id` | `BigAutoField` | yes | server primary key |
| `task_id` | FK → Task, `PROTECT`, related `assignee_links` | yes | aggregate owner |
| `user_id` | FK → user, `PROTECT` | yes | active HELPDESK at the moment it is newly added |
| `assigned_at` | timestamptz | yes | server time at relationship creation |

### TaskAssignee constraints and indexes

- `UNIQUE(task_id, user_id)` is the final duplicate guard.
- `(user_id, task_id)` supports the assignee half of SELF scope.
- The unique constraint already supports Task-to-assignee reads by its leading
  `task_id`; do not add a redundant `(task_id,user_id)` index.

### Assignment lifecycle

- Helpdesk self-create locks and re-authorizes the actor User row inside the
  transaction, then writes exactly one link to that actor.
- Manager create locks normalized requested User IDs in ascending order,
  revalidates existence/HELPDESK/active state, then writes all links atomically.
- Manager PATCH receives the desired full set, locks Task, validates only added
  IDs by locking their User rows in ascending order, deletes removed links, and
  inserts added links in one transaction.
- Concurrent deactivation/role change and assignment therefore serialize on the
  same User rows; the later writer observes the committed state.
- A user becoming inactive does not mutate this table. A retained inactive link
  remains visible. If removed, adding that inactive user again is a new
  assignment and fails.
- Empty desired sets fail before the delta is written. The Task row lock
  serializes competing full-set replacements.

## Entity: TaskUpdate

Append-only lifecycle evidence. No update/delete repository/API exists.

| Field | Shape | Required | Rule |
|---|---|---:|---|
| `id` | `BigAutoField` | yes | increasing history order within Task |
| `task_id` | FK → Task, `PROTECT`, related `updates` | yes | aggregate owner |
| `user_id` | FK → user, `PROTECT` | yes | authenticated transition actor |
| `status` | char | yes | resulting TaskStatus |
| `recorded_at` | timestamptz | yes | server timestamp |
| `note` | nullable text | no | optional general client note, trimmed when supplied |
| `block_reason` | nullable text | no | resolved nonblank block reason for BLOCKED update |
| `completion_method` | nullable char | no | MANAGER_OVERRIDE or FIELD_EVIDENCE for completion |
| `completion_note` | nullable text | no | required nonblank only for MANAGER_OVERRIDE |
| `captured_latitude` | nullable decimal | no | required for FIELD_EVIDENCE; device GPS |
| `captured_longitude` | nullable decimal | no | required for FIELD_EVIDENCE; device GPS |
| `accuracy_m` | nullable decimal | no | required positive horizontal accuracy for FIELD_EVIDENCE |
| `captured_at` | nullable timestamptz | no | optional client capture time; never server completion time |
| `gps_quality` | nullable char | no | GOOD, LOW_ACCURACY, or UNRELIABLE for FIELD_EVIDENCE |
| `actual_location_id` | nullable FK → Location, PROTECT | no | verified actual Location, distinct from Task.location |
| `validation_result` | nullable char | no | INSIDE_GEOFENCE when actual Location is present; otherwise nullable |
| `resolution_method` | nullable char | no | AUTO_SINGLE, USER_SELECTED, or GPS_ONLY |
| `distance_m` | nullable decimal | no | distance to resolved Location when present |
| `location_candidates` | bigint array, default `[]` | yes | immutable candidate IDs evaluated at completion |

When a BLOCKED request supplies both fields, the dedicated nonblank
`block_reason` is the Task snapshot reason; otherwise a nonblank `note` supplies
that reason. Both client fields may be retained on the update when present.

### TaskUpdate checks and index

1. `status` is one of TaskStatus.
2. `status = BLOCKED` requires nonblank `block_reason`; other statuses require
   `block_reason IS NULL`.
3. `status = COMPLETED` requires a completion method. MANAGER_OVERRIDE requires
   a nonblank note and permits nullable GPS; FIELD_EVIDENCE requires all GPS
   evidence fields, a resolution method, and a coherent Location/candidate
   shape. Other statuses require completion/evidence fields null.
4. `(task_id, id)` supports ordered lifecycle reads and latest-row assertions.

There is no uniqueness constraint on `(task,status)`: a valid lifecycle may
visit BLOCKED/IN_PROGRESS repeatedly. Same-state requests create no row by
application policy.

## Entity: EvidenceUpload

Private staging metadata; it is not business completion evidence until bound.

| Field | Shape | Required | Rule |
|---|---|---:|---|
| `id` | UUID | yes | opaque upload identifier |
| `task_id` | FK → Task, PROTECT | yes | immutable owning Task |
| `user_id` | FK → user, PROTECT | yes | immutable authenticated owner |
| `object_key` | text, UNIQUE | yes | canonical staging key; never returned by Task detail or logged |
| `mime` | char | yes | allowlisted normalized image MIME |
| `size_bytes` | bigint | yes | 1..5,242,880 bytes |
| `checksum_sha256` | fixed char | yes | lowercase SHA-256 declaration verified by storage HEAD |
| `status` | char | yes | PENDING, UPLOADED, BOUND, or EXPIRED; BOUND terminal |
| `created_at` / `expires_at` | timestamptz | yes | server-owned; unbound intent expires after seven days |
| `bound_update_id` | nullable FK → TaskUpdate, PROTECT | no | set exactly once inside finalize transaction |

The endpoint can issue a new short-lived presigned PUT for a still-valid
PENDING/UPLOADED intent without changing Task state. Finalize HEAD-checks the
object before locking, then locks/revalidates all selected intents with the Task.

## Entity: TaskPhoto

| Field | Shape | Required | Rule |
|---|---|---:|---|
| `id` | BigAutoField | yes | immutable photo metadata id |
| `task_update_id` | FK → TaskUpdate, PROTECT | yes | must reference a COMPLETED update |
| `evidence_upload_id` | OneToOne → EvidenceUpload, PROTECT | yes | proves one-time binding |
| `object_key` | text, UNIQUE | yes | copied stable private key; never exposed in ordinary API/audit/log |
| `mime` / `size_bytes` / `checksum_sha256` | verified metadata | yes | exact values verified before commit |
| `created_at` | timestamptz | yes | server binding time |

Photo bytes remain private. A separately authorized access operation issues a
short-lived GET URL without persisting or logging that URL.

## Entity: CompletionIdempotency

| Field | Shape | Required | Rule |
|---|---|---:|---|
| `id` | BigAutoField | yes | server primary key |
| `actor_id` | FK → user, PROTECT | yes | idempotency namespace owner |
| `task_id` | FK → Task, PROTECT | yes | target aggregate |
| `key` | char | yes | opaque client key; unique with actor and Task |
| `request_hash` | fixed char | yes | hash of canonical commit-eligible payload |
| `task_update_id` | OneToOne → TaskUpdate, PROTECT | yes | original committed FIELD_EVIDENCE result |
| `created_at` | timestamptz | yes | server commit time |

The row is created only after all pre-commit validation and Location-choice
resolution succeeds. The unique `(actor_id, task_id, key)` constraint serializes
retries; matching hashes return the original detail and mismatches return 409.

## Relationships

```text
identity.User ──< Task.created_by
identity.User ──< Task.completed_by?
locations.Location ──< Task.location?            (expected planning context)

Task ──< TaskAssignee >── identity.User
Task ──< TaskUpdate   >── identity.User           (actor)
Task ──< EvidenceUpload >── identity.User          (staging owner)
TaskUpdate ──< TaskPhoto ── EvidenceUpload         (one-time bound image)
TaskUpdate ── CompletionIdempotency                (committed retry result)

Task.status/completion/block snapshots == latest TaskUpdate after each transition
```

Cross-module model access is confined to Django relation metadata and
`config/task_adapters.py`. Task domain/application code receives typed user and
Location snapshots through its own ports.

## Canonical lifecycle

| From \ To | TODO | IN_PROGRESS | BLOCKED | COMPLETED |
|---|:---:|:---:|:---:|:---:|
| TODO | no-op | transition | transition | specialized completion only |
| IN_PROGRESS | reject | no-op | transition | specialized completion only |
| BLOCKED | reject | transition | no-op | specialized completion only |
| COMPLETED | reject | reject | reject | reject |

Ordinary status input cannot target COMPLETED. An accepted transition performs:

1. lock Task;
2. re-read latest snapshot;
3. apply matrix/reason/terminal rule;
4. insert exactly one TaskUpdate;
5. update all six Task snapshot fields to the resulting lifecycle values;
6. for Manager override only, append one AuditLog with safe identifiers and
   lifecycle metadata but without free-text `completion_note`;
7. commit all or none.

FIELD_EVIDENCE performs storage HEAD validation before the transaction, then
locks Task and selected EvidenceUpload rows, revalidates owner/scope/state and
storage metadata, inserts TaskUpdate/TaskPhoto/idempotency rows, binds intents,
updates the Task snapshot, and commits atomically. No object-storage network call
is held inside the database transaction.

## Read projection: TaskItem

Returned fields are server-shaped and do not imply stored columns:

| Field | Source |
|---|---|
| Task content/snapshot fields | Task row |
| `created_by` | minimal identity display snapshot `{id, full_name}` |
| `assignees[]` and each `assigned_at` | TaskAssignee + minimal `{id, full_name}` snapshot; inactive retained without exposing account status |
| `expected_location` | optional Location display snapshot |
| `group` | server business date + status + assigned_date |
| `overdue_days` | positive date difference only for OVERDUE; otherwise null |
| `available_statuses` | optional response projection from current matrix, never authority |

## Read projection: GroupedTaskList

```text
business_date: date in Asia/Ho_Chi_Minh
overdue:  TaskItem[]
today:    TaskItem[]
upcoming: TaskItem[]
completed: TaskItem[]
```

Classification is mutually exclusive:

1. COMPLETED always wins and enters `completed`.
2. Otherwise compare immutable `assigned_date` to the one captured server
   `business_date` for this response.
3. Before → overdue with positive day difference; equal → today; after →
   upcoming.

The query service captures business date once per request, so a request spanning
local midnight cannot classify different rows against different dates.

## Audit data

Each successful completion appends one existing `audit.AuditLog` row in the same
transaction. Manager override uses `task.completion.overridden`; FIELD_EVIDENCE
uses `task.completion.field_evidence`. Both share the privacy-safe shape:

```text
action: task.completion.overridden | task.completion.field_evidence
target_type: Task
target_id: task id as string
before: {status}
after: {
  task_id,
  status,
  completion_method,
  completed_by_id,
  completed_at
}
```

The unrestricted business `completion_note` is canonical on Task/TaskUpdate but
is excluded from AuditLog so a valid note containing `://` cannot be rejected by
the shared audit payload filter. Feature 007 contains no GPS, photo, object key,
URL, token, or secret field in audit payload and creates no OutboxEvent.

## Migration shape and rolling compatibility

`tasks/0001_initial.py` remains the original expand migration. A new
`0002_task_evidence.py` expand migration adds nullable/default-safe TaskUpdate
evidence fields and the three evidence tables without rewriting existing rows.
It does not alter Identity, Locations, Audit, or Attendance tables. The previous
application version ignores the additions during rolling deployment.

Verification must prove:

- one migration leaf for `tasks`;
- fresh migrate and migrate from every current app leaf;
- `makemigrations --check --dry-run` clean;
- static `scripts/migration_check.py check` clean;
- constraints/index names within PostgreSQL limits and present in catalog;
- rollback leaves no partial Task/assignee/update/audit rows.
