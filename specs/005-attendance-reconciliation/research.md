# Phase 0 Research: Attendance Reconciliation and Job Health

## Repository baseline

The repository already implements exact session duration, multiple-session totals, first-IN/final-OUT anomaly replacement, the canonical open-session constraint, centralized authorization, generated OpenAPI/client artifacts, Django transactions, and real-PostgreSQL race tests. `operations` exists but has no `JobRun` model or public API. Django management commands and deployment checks exist; Celery and a broker do not.

## Scheduler entry point

**Decision**: Add a thin attendance-owned Django management command. Declare its external schedule in non-secret `deploy/scheduled-jobs.yaml` as `15 0 * * *` with timezone Asia/Ho_Chi_Minh, every calendar day, and exactly one enabled scheduler identity per staging/production environment; validate that binding through the existing deployment-check surface.

**Rationale**: The application service retains all policy while the command reuses deployed infrastructure, the repository gains testable evidence that daily invocation is configured, and no dependency is introduced.

**Alternatives considered**: Celery/beat was rejected because it is not installed or approved; an in-process web timer was rejected because restarts and multiple workers make scheduling unreliable; shell-owned business logic was rejected because it bypasses the application layer.

The manifest uses one `missing-check-out-reconciliation` job with `working_directory: backend`, command arguments `python manage.py reconcile_missing_checkouts`, cron `15 0 * * *`, timezone `Asia/Ho_Chi_Minh`, `calendar: every_day`, `singleton_per_environment: true`, and enabled staging/production bindings. Environment inventory owns the non-secret `scheduler_identity`; no provider credential or URL is stored in the manifest.

## Module ownership and composition

**Decision**: Attendance owns reconciliation; operations owns `JobRun` and health. Each consumer declares its port, and `config/` supplies cross-module adapters.

**Rationale**: This matches QUY_TAC ownership and the enforced production import boundary.

**Alternatives considered**: Attendance-owned JobRun blurs operational ownership; operations importing attendance models violates boundaries; `core` cannot own business data.

## Per-session transaction protocol

**Decision**: Commit `RUNNING` first, enumerate candidate ids, then process every id in a fresh transaction that locks/revalidates and atomically commits session flag, anomaly, and the run's counter deltas.

**Rationale**: This implements R-127, minimizes locks, retains earlier commits after failure, and keeps counts aligned with committed changes.

**Alternatives considered**: A whole-run transaction holds locks and loses partial progress; batch commits obscure retries; updating JobRun after session commit permits crash-induced count drift.

## Failed-session scanned evidence

**Decision**: If failure happens after lock/revalidation, roll back its business transaction, then increment only `scanned_count` in a separate short transaction and continue. Failure of that evidence update aborts the invocation.

**Rationale**: Scanned records observation; changed/anomaly record committed state. The separate write preserves both definitions without a half-closed pair.

**Alternatives considered**: Omitting the scan contradicts R-128; retaining it inside the rolled-back transaction is impossible; persisting raw per-session failure details is not approved and risks data leakage.

## Candidate scanning and concurrency

**Decision**: Query ids by `(work_date, id)` with `work_date < current_local_date` and the canonical open predicate, then repeat the predicate under `SELECT FOR UPDATE`. Do not use `skip_locked`.

**Rationale**: The initial list is only a hint. Waiting and revalidation make checkout/job and job/job races deterministic without hiding eligible work.

**Alternatives considered**: Trusting the first query races; `skip_locked` can leave work behind while reporting success; advisory/distributed job locks are unnecessary because overlap must be safe.

## Reconciliation index

**Decision**: Add a partial `(work_date, id)` index with the exact canonical open predicate.

**Rationale**: The existing `(user, work_date, id)` index cannot lead an all-user job scan, and a partial index excludes closed history.

**Alternatives considered**: Reusing the user-leading index and adding a full work-date index were both rejected as poorer query matches.

## JobRun lifecycle

**Decision**: Persist one row per invocation with the exact R-128 enums, safe error codes, status/finish/error shape, nonnegative counters, and `changed_count = anomaly_count <= scanned_count`. Allow overlapping runs and add no second heartbeat.

**Rationale**: A committed RUNNING row is durable invocation evidence; checks make invalid terminal evidence unrepresentable.

**Alternatives considered**: A singleton loses history; logs are not durable evidence; unique RUNNING would contradict safe overlap.

## Finalization and process failure

**Decision**: Compare-and-set RUNNING to its terminal state in a short transaction. No errors means SUCCEEDED; per-session errors mean PARTIAL_FAILED only with at least one changed row, otherwise FAILED; invocation abort means FAILED/RUN_ABORTED. A crash or failed finalization leaves RUNNING.

**Rationale**: This is R-128's closed lifecycle and never fabricates success.

**Alternatives considered**: Marking success in `finally` mislabels interruptions; deriving partial status from scanned rather than changed counts contradicts the definition.

## Cutoff and stale RUNNING

**Decision**: Today's cutoff is local 01:00 and is exclusive: a timely success has `finished_at < cutoff`; equality is late. Before cutoff, a current-day RUNNING row is normal; a RUNNING row begun before today's local date is stale and alerts. At/after cutoff any unfinished run alerts.

**Rationale**: A legitimate in-window invocation is distinct from a crashed previous invocation, while the completion SLA remains hard.

**Alternatives considered**: Alerting on every RUNNING causes false alerts; ignoring all pre-cutoff RUNNING hides stale evidence; accepting a post-cutoff success as healthy erases the approved missed SLA.

## Health evidence and flags

**Decision**: Derive health from latest/latest-successful runs, overdue canonical-open count, global closed/anomaly counts, and both anti-join mismatch counts. Expose boolean flags: `no_run_history`, `missing_timely_success`, `unfinished_run`, `stale_running`, `latest_terminal_failed`, `run_count_mismatch`, `persisted_evidence_mismatch`, and `overdue_open_sessions`.

**Rationale**: Closed booleans explain precedence without free text, raw exceptions, or user-level evidence. Anti-joins check both directions of the one-to-one relation.

**Alternatives considered**: Free-text reasons are unsafe and unstable; a persisted health table would become a second source of truth.

## Health read consistency

**Decision**: Capture server `refreshed_at` once and evaluate all JobRun and attendance aggregates in one short PostgreSQL `REPEATABLE READ, READ ONLY` transaction, without row locks.

**Rationale**: Several aggregate queries form one response. Under the default READ COMMITTED isolation, a session/anomaly commit between those queries could create a transient false mismatch even though each write is atomic. A repeatable read gives one coherent snapshot and adds no service dependency.

**Alternatives considered**: Independent READ COMMITTED queries can mix states; locking evidence rows would interfere with the job; persisting a health snapshot creates a second source of truth.

## Authorization and role shaping

**Decision**: Add one direct read action for MANAGER/LEADER and reuse permission-before-validation. Identity authorization alone maps MANAGER to closed `JobHealthAccessScope.INVESTIGATE` and LEADER to `ESCALATE_ONLY`; operations shapes from that typed scope and never reads role. Return `/api/v1/users/` only for `INVESTIGATE`; return fixed escalation guidance and no links for `ESCALATE_ONLY`.

**Rationale**: Central role interpretation satisfies the authorization boundary, the user-list target independently checks `user.view`, and no AuditLog endpoint is invented.

**Alternatives considered**: LEADER user-directory access conflicts with governance; hidden forbidden links still leak; adding AuditLog API expands scope.

## API and frontend refresh

**Decision**: Add one generated-contract GET and capability-gated page with manual plus 60-second visible-tab refresh, preserving last-good data.

**Rationale**: This reuses existing DRF/OpenAPI/openapi-fetch and approved dashboard polling without new state or streaming infrastructure.

**Alternatives considered**: Handwritten types violate contract governance; WebSocket/SSE is unapproved; rerun controls are expressly excluded.

## Audit, events, privacy, and migration

**Decision**: Create no AuditLog/OutboxEvent. Store only closed error codes and expose aggregate private/no-store data. Use additive JobRun and partial-index migrations with DB defaults, no backfill, and migration-first rollout.

**Rationale**: R-130 names JobRun/session/anomaly as canonical evidence; the job has no actor. Empty history must honestly produce unknown health.

**Alternatives considered**: Per-session audit invents an actor; outbox has no approved consumer; synthetic history fabricates success; existing-row rewrites are unnecessary.
