# Phase 1 Quickstart: Validate Attendance Reconciliation and Job Health

This is the post-implementation validation guide. It contains no implementation code, production credentials, or production data.

## Prerequisites and artifacts

- Use versions and locked dependencies from `backend/pyproject.toml` and `frontend/package.json`.
- Use a real local PostgreSQL database through approved test DSNs.
- Use Feature 004 attendance fixtures and test HELPDESK, MANAGER, and LEADER identities.
- Review [spec](spec.md), [plan](plan.md), [research](research.md), [data model](data-model.md), and [design contract](contracts/job-health-api.yaml).

The design contract is not production source. Regenerate `contracts/openapi.yaml` from DRF and `frontend/src/shared/api/schema.ts` from that artifact.

## Database and schedule preparation

1. Apply operations and attendance migrations with the privileged local migration connection before runtime deployment.
2. Inspect migration leaves and PostgreSQL catalogs.
3. Confirm the reconciliation management command is discoverable.
4. Validate `deploy/scheduled-jobs.yaml`: one `missing-check-out-reconciliation` entry with `working_directory: backend`, arguments `python manage.py reconcile_missing_checkouts`, `15 0 * * *`, timezone Asia/Ho_Chi_Minh, `calendar: every_day`, `singleton_per_environment: true`, and exactly one enabled binding for each staging/production `scheduler_identity`; then bind the existing external scheduler exactly as declared.

Expected: one additive JobRun table, one exact-predicate partial attendance index declared in both model and migration state, no synthesized history, no existing-row/source-data rewrite, one leaf per affected app, and a passing deployment schedule contract.

## Automated validation

Run focused suites under the existing tooling:

```text
backend/tests/unit/{attendance,operations,identity}/
backend/tests/integration/api/operations/
backend/tests/integration/postgres/{attendance,operations}/
backend/tests/contract/operations/
backend/tests/architecture/
frontend/tests/unit/operations/
```

PostgreSQL locks, rollback, constraints, partial indexes, migrations, and races must use the real PostgreSQL marker/DSN. Then run:

```sh
scripts/check_all.sh
```

Expected: formatting, lint, typing, Django checks, all test layers, frontend build, architecture, migration safety, OpenAPI generation/compatibility, and client drift checks pass.

## Acceptance walkthrough

### 1. Duration and day anomalies

1. Complete two same-date sessions with a gap and different boundary Locations.
2. Verify each exact six-decimal HALF_UP duration and their sum; an open later session contributes zero.
3. Parameterize the daily projection from 1 through 20 completed sessions, always with open and job-closed incomplete rows present; verify the rendered count is derived from the returned session array and totals include only completed rows.
4. Prove Task GPS/movement outside the attendance geofence produces no session mutation, auto-close, duration reduction, or frontend background location polling.
5. Prove only first IN can be late and exact grace equality is normal.
6. Create an early/late final OUT, then a later normal OUT; verify the old anomaly is removed atomically and early/late remain mutually exclusive.

### 2. Daily reconciliation

1. Create stale open sessions for a weekday, Sunday, and configured Holiday, plus one current-date open session.
2. Invoke the command. Expect SUCCEEDED; stale rows become job-closed with null checkout/duration and exactly one missing anomaly; current-date row remains open.
3. Verify the use case reads no weekday/Holiday Config and creates no Attendance, Attempt, AuditLog, or OutboxEvent.
4. Verify a later Check In is not blocked by a job-closed row.

### 3. Idempotence, failure, and retry

1. Reinvoke with no work; expect a new SUCCEEDED `0/0/0` run and no changed evidence.
2. With three eligible sessions, force the middle anomaly write to fail. Verify earlier/later pairs commit, the failing pair rolls back, processing continues, and JobRun is PARTIAL_FAILED/SESSION_PROCESSING_FAILED with honest counts.
3. Remove failure and retry; only the remaining canonical-open row changes.
4. Force the JobRun changed/anomaly counter update to fail after the session/anomaly writes inside one eligible-session transaction; verify the flag, anomaly, and main-transaction deltas roll back together, then the recovery transaction records only the observed `scanned_count + 1`.
5. Force error before any commit; expect FAILED/SESSION_PROCESSING_FAILED. Force enumeration abort; expect FAILED/RUN_ABORTED when finalization is possible.
6. Stop after RUNNING commit and before finalization; verify RUNNING and committed counters remain durable, never success.

### 4. PostgreSQL races

1. Release two reconciliation workers on independent connections against one stale row. Exactly one changes it/creates the anomaly; the other may scan but is a no-op.
2. Race Check Out against reconciliation. Exactly one wins: either completed duration exists and job skips, or job closes incompletely and Check Out sees no canonical open session.
3. Repeat each deterministic barrier trial at least three times and assert no duplicate anomaly, invented OUT, inflated changed count, or stuck open row.

### 5. Health and cutoff

Use an injected server clock, not wall time.

1. No JobRun with no immediate invariant issue returns unknown.
2. Before 01:00, overdue rows are visible but alone do not alert; a current-day RUNNING is allowed.
3. Terminal failure, stale prior-day RUNNING, run-count mismatch, or either persisted anti-join mismatch alerts immediately.
4. At/after cutoff, missing timely success, any unfinished run, or overdue rows alerts.
5. A current-day SUCCEEDED run completed strictly before cutoff with no issue returns ok. A success exactly at or after cutoff does not erase the missed-SLA alert.

### 6. API, privacy, and frontend

1. Unauthenticated GET returns 401; HELPDESK with malformed input returns 403 before validation; MANAGER/LEADER return 200 global aggregates.
2. Verify `Cache-Control: private, no-store` and absence of users, ids identifying sessions/users, GPS, map/presigned URLs, raw exceptions, tokens, cookies, and secrets.
3. Verify Identity maps MANAGER to `INVESTIGATE` and LEADER to `ESCALATE_ONLY`, denies HELPDESK before issuing a scope, and no operations/config code compares role. `INVESTIGATE` may receive only `/api/v1/users/`; independently verify that target's `user.view`. `ESCALATE_ONLY` gets no links and receives escalation guidance.
4. Confirm no rerun/repair route or UI control exists.
5. On `/operations/job-health`, verify loading/error, manual refresh, 60-second visible-tab refresh, last-good-data preservation, hidden-tab pause, and timer cleanup.
6. Verify `IdentityRouteBoundary.tsx` includes the route/capability mapping and the frontend performs no background location tracking for this view or an open session.

## Migration compatibility and rollout

- The previous application continues after the additive schema is installed.
- The new application fails clearly if migrations are absent.
- Deploy migrations, then backend/API/frontend, then enable the daily schedule.
- Run the deployment contract check and retain non-secret evidence that staging/production each have exactly one enabled scheduler binding matching the manifest.
- Health is unknown before the first genuine run; never seed a synthetic success.

## Completion signal

Feature 005 is ready only when every DoD item maps to an automated test, PostgreSQL proves every transaction/race promise, role/privacy contract tests pass, generated artifacts are byte-clean, migration compatibility and the full verification suite pass, a sanitized pre-release run at the approved 50-user scale completes strictly before 01:00, and all of at least 10 representative MANAGER/LEADER users identify the health state plus one active reason when present in under 30 seconds, or correctly identify that an `ok` state has no alert reason.
