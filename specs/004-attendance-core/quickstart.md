# Phase 1 Quickstart: Validate Attendance Core

This guide defines the post-implementation validation flow. It does not contain
implementation code or production credentials.

## Prerequisites

- Python and Node versions accepted by `backend/pyproject.toml` and
  `frontend/package.json`.
- Backend and frontend dependencies already installed through the repository's
  standard setup.
- Local PostgreSQL database accessible through the approved development DSNs.
- Feature 003 reference-data initialization completed: one Config and exactly 76
  canonical Locations (7 business centers, 69 shops).
- Test users for HELPDESK and MANAGER; never reuse production identities.

## Artifact review

Before running code, confirm the implementation matches:

- [Specification](spec.md)
- [Implementation plan](plan.md)
- [Research decisions](research.md)
- [Data model](data-model.md)
- [Attendance API design contract](contracts/attendance-api.yaml)

The design contract is not the generated production contract. Implementation
must regenerate `contracts/openapi.yaml` and
`frontend/src/shared/api/schema.ts` from the backend.

## Database preparation

Apply migrations with the privileged local migration connection before starting
the runtime application. Then run the established reference-data readiness check.
Expected result:

- The new attendance tables, check constraints, indexes, and named conditional
  unique constraint exist.
- No existing Attendance data is synthesized.
- Existing identity and Location/Config behavior remains available.
- Exactly one migration leaf exists for the attendance app.

## Focused automated validation

From the repository root, run the attendance unit suite, API integration suite,
contract suite, and PostgreSQL suite using the repository's pytest environment.
The PostgreSQL suite must use the `postgres` marker and a real PostgreSQL DSN;
SQLite or mocked repositories are not acceptable evidence for constraints,
rollback behavior, or races.

Expected focused groups:

```text
backend/tests/unit/attendance/
backend/tests/integration/api/attendance/
backend/tests/integration/postgres/attendance/
backend/tests/contract/attendance/
frontend/tests/unit/attendance/
```

Run the existing full verification entry point afterward:

```sh
scripts/check_all.sh
```

Expected result: backend formatting/lint/type checks, all pytest layers,
frontend format/lint/typecheck/Vitest, architecture boundaries, migration safety,
OpenAPI drift/compatibility, and generated-client drift all pass.

## Acceptance walkthrough

Use canonical seeded test Locations selected by test helper identifiers. Do not
copy precise coordinates into committed examples, logs, screenshots, or issue
text.

### 1. Authorization and attempt boundary

1. Call Check In without authentication; expect `401` and zero new attempts.
2. Call as MANAGER; expect `403 PERMISSION_DENIED` and zero new attempts.
3. Call as HELPDESK with client `user_id` or `kind`; expect
   `400 SERVER_OWNED_FIELD` and zero new attempts.
4. Submit malformed/out-of-range or stale GPS; expect a boundary validation error
   and zero new attempts.

### 2. First session and duplicate tap

1. Submit fresh, accurate HELPDESK Check In inside exactly one active Location.
2. Expect `201`, route-derived `IN`, server UTC time, local work date,
   `AUTO_SINGLE`, `punch_index=1`, one open session, one sanitized
   `attendance.check_in.created` AuditLog, no OutboxEvent, and one `ACCEPTED`
   attempt.
3. Submit Check In again while open.
4. Expect `409 SESSION_ALREADY_OPEN`, no second Attendance, the same one open
   session, and one additional rejected attempt.

### 3. Check Out and multiple same-day sessions

1. Submit valid Check Out, optionally at a different active Location.
2. Expect `201`, `OUT`, the existing session closed, server-time duration
   quantized once to six decimal minutes with `ROUND_HALF_UP`, separate Check
   In/Out Location ids, `punch_index=2`, one sanitized
   `attendance.check_out.created` AuditLog, and no OutboxEvent.
3. Submit Check Out again; expect `409 NO_OPEN_SESSION` and its rejected attempt.
4. Complete another valid `IN → OUT` pair on the same local date.
5. Read today and expect four punches indexed `1,2,3,4`, two sessions, no open
   session, and total duration equal to the sum of the two closed sessions.

### 4. GPS quality and radius independence

1. Submit accuracy above `max_attendance_accuracy_m`; expect `422 WEAK_GPS`,
   null candidate count, no Attendance, and one attempt with approximate nearest.
2. Submit a good-accuracy point outside every active radius; expect
   `422 OUTSIDE_RADIUS`, candidate count zero, and no Attendance.
3. Exercise exact equality at the accuracy threshold and Location radius; both
   boundaries pass.
4. Verify no implementation adds/subtracts accuracy from Location radius.

### 5. Candidate resolution and R-118

1. Use a point within one active Location; expect automatic selection.
2. Use the canonical coincident/overlap fixture; omit selection and expect
   `409 LOCATION_CHOICE_REQUIRED` with current candidates and one attempt.
3. Resubmit a fresh sample with a candidate id; expect `USER_SELECTED` only when
   that id remains in the recomputed active set.
4. Submit an id outside the recomputed set; expect
   `422 INVALID_LOCATION_CHOICE` plus the latest candidates and one attempt.
   If the fresh sample instead produces zero candidates, expect
   `422 OUTSIDE_RADIUS` without a candidate-choice payload.
5. Make the geographically nearest Location inactive while leaving another
   active-candidate setup controlled. Verify the inactive Location is stored as
   attempt nearest, but never appears as a candidate, is never auto-selected, and
   cannot be validated as the selected Location.
6. Submit at the exact coincident `HCM000079`/`HCM010005` point. Verify nearest
   diagnostic attribution is `HCM000079` by canonical-code order while both
   active Locations remain separate candidates requiring a user choice.

### 6. PostgreSQL rollback and concurrency proof

1. Force an expected business rollback after the attempt boundary and verify the
   business rows roll back while the correct rejected AttendanceAttempt remains.
2. Inspect PostgreSQL catalogs to confirm `uniq_open_session_per_user` has exactly
   `check_out_id IS NULL AND closed_by_job = FALSE` as its predicate.
3. Create a job-closed session with null Check Out and verify a later Check In is
   not blocked.
4. Run 100 double-tap trials with two independent connections/workers synchronized
   at a barrier. Every trial must produce one accepted Attendance/open session,
   one `SESSION_ALREADY_OPEN` result, and exactly two attempts.
5. Verify no unique constraint exists on Attendance user/date/kind by completing
   two same-day Check In/Out pairs.
6. Start two Check Out requests against one open session on independent
   connections. Verify one closes it successfully, the other returns
   `NO_OPEN_SESSION`, and both requests retain their attempts.
7. Inspect the three AttendanceAttempt indexes: timeline
   `(user, work_date, recorded_at, id)`, `(work_date, outcome)`, and
   `(nearest_location, outcome)`.
8. Force the post-transaction attempt writer to fail on both an accepted and an
   expected-rejection path. Verify the original response/exception is preserved,
   no automatic retry occurs, and sanitized telemetry contains no GPS/device/IP.
9. Force an unexpected infrastructure exception after the boundary. Verify the
   canonical 5xx is preserved, attempt count changes by zero, no business outcome
   is fabricated, and telemetry contains no GPS/device/IP.

## Frontend walkthrough

1. Sign in as HELPDESK and open `/attendance`.
2. Confirm browser position access starts only after a user gesture, displays
   readiness/accuracy, and stops on tab hide, navigation, cancel, timeout, or
   submission.
3. Confirm each action uses a `maximumAge: 0` sample; candidate confirmation
   obtains a new sample rather than silently reusing the first one.
4. Confirm the button shown follows `has_open_session`, is disabled during an
   in-flight request, and still handles server state conflicts correctly.
5. Confirm success refreshes today's canonical timeline and renders separate
   punch/session Locations and total time. Each Maps link must use the stored
   captured decimals exactly, open in a new tab with `noopener noreferrer`, and
   no iframe or map SDK may be present.
6. Sign in as MANAGER or LEADER and confirm no action control is presented; then
   retain the backend `403` test as the enforcement proof.

## Performance and usability acceptance

1. Run 100 PostgreSQL-backed command-plus-today-read trials with 50 users,
   exactly 76 canonical Locations, and 20 same-day sessions for the actor. At
   least 95 trials must complete within 2 seconds; record p95 as feature evidence,
   not a production capacity claim. Run this as a signed pre-release acceptance,
   not a CI wall-clock test, and write the sanitized result to
   `specs/004-attendance-core/evidence/latency-acceptance.md`.
2. With at least 20 representative HELPDESK participants, run one unambiguous
   punch and one multiple-Location choice scenario. At least 19 must complete
   both without assistance. Record counts and blockers without GPS coordinates
   in `specs/004-attendance-core/evidence/usability-acceptance.md`.

## Migration compatibility check

Validate both application versions around the additive migration:

- Previous application version starts and serves existing Features 001–003 after
  the new tables are added.
- New application version fails clearly if its migration is absent.
- Applying the migration changes no identity, audit, Location, Config, Holiday,
  or canonical source-data row.
- No contraction is included in this release.

## Completion signal

Feature 004 is ready for implementation review only when every Definition of Done
item in `spec.md` is backed by a named automated test, PostgreSQL-specific claims
run against PostgreSQL, generated contracts are byte-clean, and the full existing
verification entry point passes without a new dependency or infrastructure change.

## Verified execution record

Automated verification was completed on 2026-08-18 using the approved local
PostgreSQL environment. `scripts/check_all.sh` passed end to end, including
backend format/lint, strict mypy, Django checks, unit/API/contract/architecture
tests, PostgreSQL integration tests, frontend formatting/lint/typecheck, 94
Vitest tests, generated-contract drift checks, and the production frontend build.
The existing Location test suite reports 13 ESLint warnings and zero errors.

Definition of Done evidence maps as follows:

| DoD area | Passing evidence |
|---|---|
| Check In/Out, state errors, multiple sessions, punch indexes | `backend/tests/integration/api/attendance/test_session_actions.py`, `test_multiple_sessions.py` |
| GPS quality, radius, freshness, and pre-boundary behavior | `backend/tests/integration/api/attendance/test_gps_gates.py`, `backend/tests/unit/attendance/test_gps_policy.py` |
| Candidate cardinality, choice, revalidation, and nearest tie | `backend/tests/integration/api/attendance/test_location_choice.py`, `backend/tests/integration/postgres/attendance/test_nearest_location.py` |
| Seven AttendanceAttempt outcomes and infrastructure/writer failures | `backend/tests/unit/attendance/test_attempt_matrix.py`, `backend/tests/integration/api/attendance/test_attempt_outcomes.py` |
| Audit atomicity, sanitized telemetry, and no routine outbox | `backend/tests/integration/postgres/attendance/test_audit_atomicity.py`, `backend/tests/integration/api/attendance/test_observability.py` |
| Open-session constraint, attempt indexes, and both races | `backend/tests/integration/postgres/attendance/test_open_session_constraint.py`, `test_check_in_concurrency.py`, `test_check_out_concurrency.py` |
| Self scope, timeline, Maps safety, and frontend interaction | `backend/tests/integration/api/attendance/test_today.py`, `frontend/tests/unit/attendance/attendance-panel.test.tsx` |
| Migration and deployment compatibility | `backend/tests/integration/postgres/attendance/test_migration_compatibility.py`, `backend/tests/contract/test_deployment_runbook.py` |
| SC-008, 100-trial latency | [Latency acceptance](evidence/latency-acceptance.md): PASS, 100/100 under 2 seconds, p95 26.226 ms |
| SC-007, representative-user usability | [Usability acceptance](evidence/usability-acceptance.md): deferred at the user's direction on 2026-08-18; test later with at least 20 HELPDESK participants |

All automated walkthrough coverage and SC-008 are complete. Task T076 and the
final T077 completion signal are explicitly deferred until the SC-007 human
exercise can be scheduled. They remain open, and the evidence file is an
execution protocol rather than an acceptance result or waiver.
