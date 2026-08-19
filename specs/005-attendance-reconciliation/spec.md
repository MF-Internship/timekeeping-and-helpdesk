# Feature Specification: Attendance Sessions, Anomalies and Daily Reconciliation

**Feature Branch**: `feature/005-attendance-reconciliation`

**Created**: 2026-08-19

**Status**: Ready for Implementation

**Input**: User description: "Attendance Sessions, Anomalies and Daily Reconciliation covering completed session duration, daily totals, first Check-In and final Check-Out anomaly evaluation and replacement, missing Check-Out reconciliation, JobRun persistence, idempotence, and operational job health."

## Clarifications

### Session 2026-08-19

- Q: If reconciliation fails while processing multiple eligible sessions, what transaction boundary should govern the run? → A: Each session and its `MISSING_CHECK_OUT` anomaly commit atomically; failures may leave partial progress, accurately recorded in `JobRun`, and retries process only remaining sessions.
- Q: Which closed status set should `JobRun` use to distinguish partial progress from total failure? → A: Use `RUNNING`, `SUCCEEDED`, `PARTIAL_FAILED`, and `FAILED`; partial means at least one session committed and at least one failed.
- Q: How are the 01:00 cutoff and stale unfinished runs evaluated? → A: Timely means `finished_at < 01:00:00`; equality is late, a prior-local-day RUNNING alerts before cutoff, and every unfinished RUNNING alerts from the cutoff onward.
- Q: Which module may turn MANAGER/LEADER roles into job-health response shape? → A: Identity authorization alone returns a closed `INVESTIGATE` or `ESCALATE_ONLY` access scope after permission succeeds; operations never branches on role.
- Q: What deployable schedule contract guarantees the daily invocation? → A: The existing external scheduler invokes the canonical command at 00:15 Asia/Ho_Chi_Minh daily, with a repository manifest and deployment binding verification; no new scheduler runtime is added.
- Q: What evidence makes the under-30-second job-health outcome measurable? → A: At least 10 representative authorized MANAGER/LEADER users must all identify the state and, when present, one active reason in under 30 seconds; for `ok` with no active reason they must correctly identify that no alert reason exists, using sanitized aggregate evidence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record trustworthy working time (Priority: P1)

A HELPDESK employee completes one or more work sessions during a work date and sees the duration of each completed session and the correct total worked time for that date.

**Why this priority**: Session duration and the daily total are the core payroll-relevant outcomes of attendance recording.

**Independent Test**: Complete two sessions on one work date, including movement outside the Check-In geofence and a Check-Out at a different Location, then verify each duration and their sum without counting the break or requiring continuous location presence.

**Acceptance Scenarios**:

1. **Given** a session has a server-recorded Check In and Check Out, **When** it is completed, **Then** its duration equals the exact elapsed time between those two records, expressed in minutes to six decimal places.
2. **Given** an employee completes two sessions on one work date, **When** daily worked time is read, **Then** it equals the sum of the two completed session durations and excludes the time between sessions.
3. **Given** an employee checks in at Location A, leaves its geofence while continuing to work, and later checks out at Location B, **When** the session is completed, **Then** the entire Check-In-to-Check-Out interval counts and the two boundary Locations remain distinct.
4. **Given** a session has no Check Out, **When** daily worked time is calculated, **Then** the session contributes no duration.

---

### User Story 2 - Reconcile day-level attendance anomalies (Priority: P1)

A manager reviews attendance anomalies that reflect the employee's work date as a whole: the first Check In determines lateness, and the latest Check Out determines early or late departure.

**Why this priority**: Day-level evaluation prevents breaks and additional sessions from producing false late-arrival or early-departure findings.

**Independent Test**: Record multiple alternating Check In and Check Out events around shift boundaries and verify that only the first Check In and current final Check Out carry the applicable anomalies.

**Acceptance Scenarios**:

1. **Given** the first Check In is after `shift_start + late_grace_minutes`, **When** it is accepted, **Then** that Check In receives `LATE_CHECK_IN`.
2. **Given** the first Check In is on or before the lateness boundary and a later Check In is after it, **When** the day is reviewed, **Then** neither Check In receives `LATE_CHECK_IN` because only the first Check In is evaluated.
3. **Given** the current final Check Out is before `shift_end - early_checkout_grace_minutes`, **When** it is accepted, **Then** it receives `EARLY_CHECK_OUT`.
4. **Given** the current final Check Out is after `shift_end + late_checkout_grace_minutes`, **When** it is accepted, **Then** it receives `LATE_CHECK_OUT`.
5. **Given** a Check Out currently carries a final-departure anomaly, **When** a later Check Out is accepted on the same work date, **Then** the prior Check Out's final-departure anomaly is removed and only the new final Check Out is evaluated.
6. **Given** a later final Check Out falls within both departure grace boundaries, **When** it replaces a previously anomalous final Check Out, **Then** the previous anomaly is removed and no departure anomaly is created for the new final Check Out.

---

### User Story 3 - Close stale sessions without inventing time (Priority: P1)

Operations runs end-of-day reconciliation every calendar day so an employee who forgot to Check Out is not permanently blocked from starting another session.

**Why this priority**: An old open session otherwise prevents future Check Ins and leaves attendance data operationally stuck.

**Independent Test**: Create eligible open sessions for a weekday, Sunday, and Holiday, run reconciliation repeatedly, and verify that each is job-closed exactly once with one missing-Check-Out anomaly and no fabricated Check Out or duration.

**Acceptance Scenarios**:

1. **Given** a session remains open and its work date is earlier than the current Asia/Ho_Chi_Minh date, **When** reconciliation runs, **Then** the session is marked `closed_by_job`, its Check Out and duration remain absent, and `MISSING_CHECK_OUT` is attached to its Check In.
2. **Given** an open session belongs to the current work date, **When** reconciliation runs, **Then** the session remains open and receives no `MISSING_CHECK_OUT`.
3. **Given** an eligible open session falls on Sunday or a configured Holiday, **When** reconciliation runs, **Then** it is reconciled by the same rules as any other date.
4. **Given** a session was already reconciled, **When** the job runs again, **Then** no duplicate anomaly is created and no session or attendance value is changed.
5. **Given** an employee's old session was job-closed, **When** the employee checks in again, **Then** the old session does not count as open and the new Check In is not blocked by it.

---

### User Story 4 - Monitor reconciliation health (Priority: P2)

A MANAGER or LEADER can inspect whether daily missing-Check-Out reconciliation is current, internally consistent, and leaving overdue sessions behind.

**Why this priority**: Persisted run evidence and a concise health view allow failures to be detected before they affect attendance operations.

**Independent Test**: Exercise successful, partial-failure, total-failure, interrupted, overdue, and count-mismatch run histories and verify the `ok`/`alert`/`unknown` result, counts, overdue-session count, and role-appropriate investigation guidance.

**Acceptance Scenarios**:

1. **Given** reconciliation is invoked, **When** it finishes successfully, partially fails, totally fails, or is interrupted, **Then** one `JobRun` preserves the canonical job name, start, applicable finish, status, committed counts, and allowed safe error code.
2. **Given** a current-day successful run finished strictly before 01:00 with matching closed-session and anomaly counts and no overdue open sessions, **When** job health is read, **Then** it reports `ok` and shows the latest run, latest successful run, timezone, cutoff, and counts.
3. **Given** no timely successful run exists at or after 01:00 for the current date, a run remains unfinished at or after that boundary, or the latest terminal run failed, **When** job health is read, **Then** it reports `alert`; no run history reports `unknown`, never `ok`.
4. **Given** run counts or persisted data show a closed-session versus `MISSING_CHECK_OUT` mismatch, **When** job health is read, **Then** it reports an invariant violation.
5. **Given** a LEADER reads job health, **When** investigation guidance is returned, **Then** it contains no account-specific or AuditLog link; a MANAGER may receive an authorized operational investigation link.

### Edge Cases

- A duration whose exact microsecond delta produces a repeating decimal in minutes is rounded once to six decimal places using half-up rounding.
- A Check In exactly at `shift_start + late_grace_minutes` is not late; only a later time is late.
- A Check Out exactly at either departure grace boundary is neither early nor late because the anomaly conditions are strict inequalities.
- A work date may have multiple completed sessions and one later open session; only completed sessions contribute to the daily total.
- A job-closed session retains an absent Check Out and duration and must not be mistaken for an open session.
- Reconciliation invoked concurrently or retried after success must not close a session twice, create duplicate `MISSING_CHECK_OUT`, or inflate changed/anomaly counts.
- When Check Out and reconciliation race for the same prior-date session, both revalidate under the session lock: Check Out winning makes the job skip it; reconciliation winning makes Check Out observe no open session. Exactly one transition wins.
- When two reconciliation invocations race for one session, only the winner changes it; the loser may count the locked/revalidated session as scanned but not changed or anomalous.
- A reconciliation failure for one eligible session rolls back only that session/anomaly pair; other sessions continue when possible, and a later run completes only the remaining eligible sessions.
- A job run with zero eligible sessions is a successful run with zero changed and anomaly counts.
- A success finishing exactly at 01:00:00 Asia/Ho_Chi_Minh is late. Before that boundary, a RUNNING begun before the current local date is stale; at or after it, every unfinished RUNNING alerts.
- Holiday and working-weekday configuration may affect reporting labels but never reconciliation eligibility.
- No MVP session spans work dates; a session still open after its Check-In work date becomes eligible for reconciliation rather than rolling into the new date.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: An `AttendanceSession` MUST represent working time from an accepted Check In to its paired accepted Check Out, not continuous geofence presence.
- **FR-002**: Leaving a Location or its geofence MUST NOT automatically close an open session, reduce its duration, or require continuous location tracking.
- **FR-003**: A session's Check In and Check Out MAY occur at different active Locations, and each boundary MUST retain its own Location identity.
- **FR-004**: Every session MUST belong to exactly the Check-In Attendance's Asia/Ho_Chi_Minh work date; MVP MUST NOT carry a session into another work date.
- **FR-005**: When a user completes a session, its `duration_minutes` MUST equal the exact difference between server-recorded Check Out and Check In timestamps, converted to minutes and rounded once to six decimal places using `ROUND_HALF_UP`.
- **FR-006**: Open sessions and sessions closed by reconciliation MUST have no duration; the system MUST NOT infer a duration for either state.
- **FR-007**: Daily worked time MUST equal the sum of non-null durations of completed sessions for the user and work date; breaks and incomplete sessions MUST not contribute.
- **FR-008**: The system MUST preserve and expose individual sessions alongside daily worked time so multiple-session days remain explainable; the displayed session count MUST be derived as the length of that session collection, not persisted or transported as a second count.
- **FR-009**: Shift anomaly evaluation MUST use server-recorded timestamps converted to Asia/Ho_Chi_Minh and MUST use configured `shift_start`, `shift_end`, `late_grace_minutes`, `early_checkout_grace_minutes`, and `late_checkout_grace_minutes`.
- **FR-010**: Only the earliest accepted Check In for a user and work date MUST be evaluated for `LATE_CHECK_IN`; it MUST be late only when its time is strictly later than `shift_start + late_grace_minutes`.
- **FR-011**: Later Check Ins on the same work date MUST NOT create or replace `LATE_CHECK_IN`.
- **FR-012**: Only the latest accepted Check Out for a user and work date MUST be evaluated for departure anomalies.
- **FR-013**: The latest Check Out MUST receive `EARLY_CHECK_OUT` only when its time is strictly earlier than `shift_end - early_checkout_grace_minutes`.
- **FR-014**: The latest Check Out MUST receive `LATE_CHECK_OUT` only when its time is strictly later than `shift_end + late_checkout_grace_minutes`.
- **FR-015**: `EARLY_CHECK_OUT` and `LATE_CHECK_OUT` MUST be mutually exclusive for a user's work date, and a boundary-equal or between-boundaries final Check Out MUST receive neither.
- **FR-016**: When a later accepted Check Out becomes final for the work date, the system MUST remove any `EARLY_CHECK_OUT` or `LATE_CHECK_OUT` from the previous final Check Out and evaluate the new final Check Out in the same business transaction.
- **FR-017**: For each user and work date, the system MUST permit at most one `LATE_CHECK_IN` and at most one anomaly from the final-departure group.
- **FR-018**: Attendance anomaly reasons in this scope MUST remain the closed set `LATE_CHECK_IN`, `EARLY_CHECK_OUT`, `LATE_CHECK_OUT`, and `MISSING_CHECK_OUT`; `MISSING_CHECK_IN` and inferred assignment/location anomalies are outside scope.
- **FR-019**: Daily reconciliation MUST be invoked every calendar day and MUST evaluate all sessions whose `work_date` is earlier than the current Asia/Ho_Chi_Minh date and whose Check Out is absent and `closed_by_job` is false.
- **FR-019A**: The existing deployment scheduler MUST invoke the canonical `reconcile_missing_checkouts` command once daily at 00:15 Asia/Ho_Chi_Minh, including weekends and Holidays. A non-secret repository schedule manifest and environment-binding check MUST verify the cron, timezone, command, enabled state, and exactly one scheduler identity per staging/production environment; MVP MUST NOT add an in-process timer, Celery, or broker.
- **FR-020**: Reconciliation MUST NOT consult or skip based on configured working weekdays or Holiday records; weekday, weekend, Sunday, and Holiday sessions MUST follow identical eligibility rules.
- **FR-021**: For each eligible session, reconciliation MUST atomically set `closed_by_job` to true and create exactly one `MISSING_CHECK_OUT` anomaly attached to that session's Check-In Attendance.
- **FR-022**: Reconciliation MUST leave the session's Check Out and duration absent and MUST NOT create an Attendance record or timestamp to simulate a Check Out.
- **FR-023**: The canonical open-session condition MUST be: Check Out is absent and `closed_by_job` is false. Every attendance write, read, uniqueness rule, and reconciliation query MUST use the complete condition.
- **FR-024**: A job-closed session MUST not block a subsequent Check In and MUST appear separately as missing attendance data rather than completed work.
- **FR-025**: Reconciliation MUST be safe under retries, overlapping invocations, and repeated execution: each eligible session can transition only once, can have only one `MISSING_CHECK_OUT`, and already-reconciled sessions are unchanged.
- **FR-026**: Reconciliation MUST preserve the invariant that every job-closed session has exactly one `MISSING_CHECK_OUT` anomaly and every `MISSING_CHECK_OUT` identifies one job-closed session.
- **FR-026A**: Each eligible session MUST be reconciled in its own atomic unit that revalidates and locks that session, commits `closed_by_job` with its single `MISSING_CHECK_OUT`, or rolls both back for that session. A failure MUST NOT roll back previously committed sessions; processing MUST continue for other sessions when possible, and batch-level or whole-run commits MUST NOT be used.
- **FR-027**: Each reconciliation invocation MUST persist one `JobRun`, including job name, start time, finish time when finished, outcome status, scanned-session count, changed-session count, anomaly count, and a safe machine-readable error code when it fails.
- **FR-027A**: `JobRun.job_name` MUST be `MISSING_CHECK_OUT`, and status MUST be the closed set `RUNNING`, `SUCCEEDED`, `PARTIAL_FAILED`, and `FAILED`. The run MUST commit as `RUNNING` before scanning; only `RUNNING` may omit `finished_at`. No processing error produces `SUCCEEDED`, even with zero work; at least one committed session plus at least one error produces `PARTIAL_FAILED`; an error with no committed session or an aborted scan produces `FAILED`. `RUNNING` and `SUCCEEDED` MUST have no error code; failure statuses MUST use only `SESSION_PROCESSING_FAILED` or `RUN_ABORTED` as applicable.
- **FR-028**: `scanned_count` MUST count sessions locked and revalidated by the invocation, `changed_count` MUST count newly job-closed sessions committed by it, and `anomaly_count` MUST count newly committed `MISSING_CHECK_OUT` anomalies. Every run MUST preserve `changed_count = anomaly_count <= scanned_count`; a zero-work run MUST be `SUCCEEDED` with all three counts zero.
- **FR-028A**: A process interruption MUST leave the committed `RUNNING` row and its durable counts available for stale-run detection; it MUST NOT be inferred as success. Introducing JobRun MUST NOT fabricate historical executions, so health remains unknown until the first real run.
- **FR-029**: A `JobRun` with any per-session failure MUST remain available for operations review, reflect the successfully committed partial progress and the presence of failure, and MUST not count unprocessed or rolled-back sessions as changed. A later retry MUST process only sessions that remain eligible.
- **FR-030**: The operational job-health read model MUST expose the latest run, latest successful run, overall state, Asia/Ho_Chi_Minh timezone, the daily 01:00 expected-completion cutoff, scanned/closed/anomaly counts, current overdue open-session count, reason flags, closed/anomaly invariant indication, and last refresh time. In display language, a run's “closed” count is exactly its canonical `changed_count`; no second `closed_count` field may be stored or added to the API.
- **FR-031**: Overall job health MUST use `ok`, `alert`, and `unknown` with precedence `alert > unknown > ok`. No JobRun MUST be `unknown`. A current-day success is timely only when `finished_at < 01:00:00` Asia/Ho_Chi_Minh; equality is late and belongs to the at/after-cutoff branch. Before cutoff, overdue sessions MUST remain visible but MUST NOT alone cause alert, a current-local-day RUNNING is allowed, and any RUNNING begun before the current local date MUST alert as stale; failures and invariant violations MUST alert immediately. At or after cutoff, absence of a timely current-day `SUCCEEDED` run, any unfinished `RUNNING` run, a latest terminal failure, overdue open sessions, count mismatch, or closed/anomaly invariant violation MUST be `alert`; only timely success with no overdue or invariant issue is `ok`.
- **FR-032**: Job health MUST report an invariant violation when run counts disagree or persisted job-closed sessions and `MISSING_CHECK_OUT` anomalies are not one-to-one.
- **FR-033**: Job health MUST require the canonical `operations.job_health.view` action, granted directly to MANAGER and LEADER and not to HELPDESK. It is a global aggregate read with no per-user object scope and no permission implication. After authorization succeeds, Identity MUST return the closed access scope `INVESTIGATE` for MANAGER or `ESCALATE_ONLY` for LEADER; HELPDESK MUST be denied before any scope is issued, and no other module may inspect role to shape this response.
- **FR-034**: `INVESTIGATE` job health MAY provide an authorized account investigation link; `ESCALATE_ONLY` job health MUST be read-only, MUST provide escalation guidance to a MANAGER, and MUST NOT expose account-specific or AuditLog links.
- **FR-035**: MVP MUST NOT provide a job rerun or repair action through the job-health interface.
- **FR-036**: Job-health responses MUST be private and non-cacheable and MUST exclude precise GPS, user lists, raw exceptions, and secrets. Health reads and automatic per-session closure MUST create neither AuditLog nor OutboxEvent; JobRun, AttendanceSession, and AttendanceAnomaly are the canonical evidence. Any `INVESTIGATE` link MUST lead to an independently authorized endpoint.

### Key Entities *(include if feature involves data)*

- **AttendanceSession**: One employee work interval on one work date, bounded by one Check In and an optional Check Out; includes derived duration and `closed_by_job` state. A missing Check Out distinguishes job-closed incomplete data from a completed session.
- **Attendance**: A successful server-timed `IN` or `OUT` event. The first `IN`, latest `OUT`, and Check In of an unreconciled session are anchors for the anomalies in this feature.
- **AttendanceAnomaly**: A reason attached to an existing Attendance event. Its closed reason set is `LATE_CHECK_IN`, `EARLY_CHECK_OUT`, `LATE_CHECK_OUT`, and `MISSING_CHECK_OUT`.
- **JobRun**: Durable operational evidence and heartbeat for one `MISSING_CHECK_OUT` invocation, with the closed lifecycle, committed work counts, and safe failure classification. It replaces any need for a second heartbeat model for this job.
- **Operational Job Health**: A derived, Identity-access-scope-filtered view combining recent JobRun evidence with current overdue-session and closed/anomaly consistency checks; it is not a second source of truth.
- **Config**: The authoritative timezone, shift boundaries, and grace periods used for work-date and anomaly evaluation. Working-weekday data does not control reconciliation.
- **Holiday**: A reporting/configuration date marker that does not affect reconciliation eligibility.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across acceptance fixtures including microsecond timestamps, 100% of completed session durations match the exact timestamp delta rounded once to six decimal minute places.
- **SC-002**: Across days containing 1 to 20 completed sessions plus incomplete sessions, 100% of daily totals equal the sum of completed-session durations and include 0% of incomplete-session or break time.
- **SC-003**: In boundary and multi-session acceptance tests, 100% of work dates place lateness only on the first Check In and early/late departure only on the current final Check Out.
- **SC-004**: After any later Check Out is accepted, 100% of obsolete final-Check-Out anomalies are removed and no work date retains more than one final-departure anomaly.
- **SC-005**: Each daily reconciliation run processes 100% of eligible prior-date open sessions, including weekend and Holiday sessions, without changing any current-date session.
- **SC-006**: Repeating or overlapping reconciliation at least three times over the same data produces no duplicate anomaly, no fabricated Check Out, no duration for incomplete sessions, and no additional session transition.
- **SC-007**: After reconciliation, 100% of job-closed sessions correspond one-to-one with `MISSING_CHECK_OUT` anomalies, and affected employees can start a later session without being blocked by the old one.
- **SC-008**: Every observed reconciliation invocation, whether successful, zero-work, or failed, has one persisted JobRun with accurate outcome and counts.
- **SC-009**: In pre-release acceptance with at least 10 representative authorized users including MANAGER and LEADER, 100% identify `ok`, `alert`, or `unknown` and, when present, at least one active failure, overdue, or invariant reason from the job-health view in under 30 seconds; for `ok` with no active reason they correctly identify that no alert reason exists. `ESCALATE_ONLY` views expose zero account-specific or AuditLog links, and evidence contains only aggregate role/count/timing/pass-fail data.

## Assumptions

- The governing source is `docs/CHOT_YEU_CAU.md` §§5.1–5.3, 7, 9, and 10, followed by `docs/QUY_TAC_CLEAN_CODE.md`, existing Feature 004 artifacts, and the project constitution.
- Feature 004 supplies accepted Check In/Check Out events, strict session pairing, the one-open-session invariant, and the self attendance view; this feature completes the derived duration, anomaly reconciliation, end-of-day reconciliation, JobRun, and health behavior.
- The existing deployment scheduler invokes reconciliation at 00:15 each Asia/Ho_Chi_Minh calendar day under the repository-owned manifest/binding contract. The business command remains safe if invoked more often, late, concurrently, or manually by authorized operations outside the product interface.
- `scanned_count` counts sessions locked and revalidated during an invocation; `changed_count` counts sessions newly committed as `closed_by_job`; `anomaly_count` counts newly committed `MISSING_CHECK_OUT` anomalies.
- Job health is derived from JobRun and attendance records at read time and does not persist a competing health state.
- Manual attendance correction, anomaly resolution workflows, overnight shifts, `MISSING_CHECK_IN`, job rerun/repair endpoints, and payroll policy are outside MVP scope.
- Global authorization, transaction, audit, observability, schema-evolution, and PostgreSQL verification rules are governed by the project constitution and are not weakened by this specification.
