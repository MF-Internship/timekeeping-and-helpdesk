# Phase 1 Data Model: Attendance Reconciliation and Job Health

## Existing AttendanceSession

| Field | Rule |
|---|---|
| `user` | At most one canonical open row per user |
| `work_date` | Check-In date in Asia/Ho_Chi_Minh; earlier than current local date is eligible |
| `check_in` | Required IN anchor and `MISSING_CHECK_OUT` target |
| `check_out` | Present only for a user-completed session |
| `duration_minutes` | Exact Decimal(12,6) server-time delta; null for open/job-closed |
| `closed_by_job` | True only for reconciliation-closed incomplete sessions |

| State | `check_out` | `duration_minutes` | `closed_by_job` | Counts as work |
|---|---:|---:|---:|---:|
| OPEN | null | null | false | no |
| COMPLETED | present | non-null | false | yes |
| JOB_CLOSED_INCOMPLETE | null | null | true | no |

Existing `uniq_open_session_per_user`, session-shape, nonnegative-duration, anomaly uniqueness, and closed four-reason checks remain. Add `attendance_reconcile_idx` on `(work_date, id)` where `check_out_id IS NULL AND closed_by_job = FALSE`.

```text
accepted IN:           none -> OPEN
accepted OUT:          OPEN -> COMPLETED
daily reconciliation: stale OPEN -> JOB_CLOSED_INCOMPLETE
```

No transition leaves JOB_CLOSED_INCOMPLETE. Reconciliation creates no Attendance, checkout timestamp, or duration.

## Existing AttendanceAnomaly and projections

`MISSING_CHECK_OUT` attaches to the session's Check-In Attendance. The application transaction plus health anti-joins enforce/monitor:

```text
AttendanceSession.closed_by_job = TRUE
  <=> exactly one AttendanceAnomaly(
        attendance_id = AttendanceSession.check_in_id,
        reason = MISSING_CHECK_OUT)
```

This cross-table equivalence is not expressible as a simple PostgreSQL CHECK. Existing punch reconciliation continues to use the first IN and final OUT; prior final-OUT anomalies are replaced in the accepted punch transaction. Daily total remains the sum of completed session durations only, and boundary Locations remain independent.

The session count shown with a daily projection is always `len(sessions)` from that same response collection. It is neither a stored field nor a duplicate API counter.

## New operations.JobRun

| Field | Storage/default | Validation |
|---|---|---|
| `id` | BigAutoField | Primary key |
| `job_name` | CharField(32) | `MISSING_CHECK_OUT` only |
| `started_at` | DateTimeField | Server time, committed before scan |
| `finished_at` | nullable DateTimeField | Null only for RUNNING; terminal `>= started_at` |
| `status` | CharField(32), DB default RUNNING | RUNNING, SUCCEEDED, PARTIAL_FAILED, FAILED |
| `scanned_count` | PositiveInteger, DB default 0 | Locked/revalidated rows |
| `changed_count` | PositiveInteger, DB default 0 | Newly job-closed commits |
| `anomaly_count` | PositiveInteger, DB default 0 | Newly committed missing anomalies |
| `error_code` | nullable CharField(32) | SESSION_PROCESSING_FAILED or RUN_ABORTED on failure |

UI copy may label `changed_count` as the run's “closed” count. This is one field with one meaning; there is no separate `closed_count` property.

Constraints:

1. Closed job/status/error vocabularies.
2. Error is null for RUNNING/SUCCEEDED and required for failure statuses.
3. `finished_at IS NULL` exactly for RUNNING; terminal finish is not before start.
4. `changed_count = anomaly_count <= scanned_count`.
5. PARTIAL_FAILED requires `changed_count > 0` and SESSION_PROCESSING_FAILED.
6. FAILED/SESSION_PROCESSING_FAILED requires `changed_count = 0`; FAILED/RUN_ABORTED represents invocation abort. SUCCEEDED permits zero work.

Indexes: `(job_name, started_at, id)` and `(job_name, status, finished_at, id)`. No uniqueness suppresses overlapping invocations.

```text
RUNNING -> SUCCEEDED       no processing error, including zero work
RUNNING -> PARTIAL_FAILED  per-session error and changed_count > 0
RUNNING -> FAILED          error with no commit, or invocation abort
RUNNING -> RUNNING         process death/uncommitted finalization
```

Terminalization is a compare-and-set from RUNNING.

## Derived Operational Job Health

```text
JobHealth
├── state: ok | alert | unknown
├── timezone, cutoff_at, refreshed_at
├── latest_run, latest_successful_run
├── overdue_open_session_count
├── evidence_counts
│   ├── job_closed_session_count
│   ├── missing_checkout_anomaly_count
│   ├── job_closed_without_anomaly_count
│   └── anomaly_without_job_closed_count
├── invariant_valid
├── reason_flags
│   ├── no_run_history
│   ├── missing_timely_success
│   ├── unfinished_run
│   ├── stale_running
│   ├── latest_terminal_failed
│   ├── run_count_mismatch
│   ├── persisted_evidence_mismatch
│   └── overdue_open_sessions
├── investigation_links.accounts?   # MANAGER only
└── escalation_guidance?            # LEADER only
```

`cutoff_at` is today's local 01:00 and is exclusive: only a current-date success with `finished_at < cutoff_at` is timely; equality is late. Before cutoff, overdue rows alone do not alert and a current-day RUNNING is allowed; a RUNNING with `started_at` before today's local 00:00, terminal failure, or invariant mismatch alerts immediately. At/after cutoff, missing timely success, any unfinished run, overdue rows, or the immediate conditions alert. If no alert applies and no run exists, state is unknown; otherwise it is ok.

All fields are derived from one short PostgreSQL `REPEATABLE READ, READ ONLY` snapshot using one captured `refreshed_at`; the read takes no row locks and writes no health state.

## Transactional counters

| Outcome | Atomic effect |
|---|---|
| Eligible and changed | scanned +1, changed +1, anomaly +1 with flag/anomaly |
| Revalidated no-op | scanned +1 only |
| Failure after lock | business rollback; separate evidence transaction scanned +1 |
| Failure before lock | no count; continue or abort by failure class |

Each invocation updates only its own JobRun. Aggregate attendance invariants are never inferred by summing historical runs.

## Migration and privacy

- Add JobRun without backfill and declare the attendance partial index in both `AttendanceSession.Meta.indexes` and its migration without row rewrites; `makemigrations --check` must report no drift.
- Old code ignores both additive objects; deploy migrations first.
- No JobRun hard-delete/retention workflow is added.
- JobRun stores no actor, user/session id, coordinates, exception text, payload, AuditLog id, or outbox id.
