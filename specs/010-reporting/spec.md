# Feature Specification: Reporting, Dashboard and Export

**Feature Branch**: `feature/010-reporting`

**Created**: 2026-08-21

**Status**: Ready for validation

**Input**: User description: "Feature 010: Reporting, Dashboard and Export"

## Clarifications

### Session 2026-08-21

- Q: How is attendance failure rate calculated? -> A: Numerator is canonical failed attempts; denominator excludes `LOCATION_CHOICE_REQUIRED`; zero denominator is reported as `N/A`/null.
- Q: Are anomalies and rejected attempts the same dataset? -> A: No. `AttendanceAnomaly` and rejected `AttendanceAttempt` diagnostics are separate report fields.
- Q: Can exports include coordinates by default? -> A: No. Sensitive coordinate export is explicit opt-in, export-authorized only, audited, and no-store.

## User Scenarios & Testing

### User Story 1 - Review Attendance Health (Priority: P1)

Managers and leaders review attendance status, punch counts, duration, anomalies, rejected attempts, nearest-location coverage, and failure rate without mutating operational data.

**Why this priority**: Attendance reporting is the main management workflow and must preserve payroll/location semantics.

**Independent Test**: Seed accepted attempts, rejected attempts, anomalies, and sessions; fetch the attendance report and verify datasets remain separate and source tables are unchanged.

**Acceptance Scenarios**:

1. **Given** accepted, rejected, and location-choice-required attempts, **When** the attendance report is viewed, **Then** the failure-rate numerator, denominator, excluded count, and nullable rate follow CHOT.
2. **Given** an incomplete system-closed session, **When** the report totals worked duration, **Then** no fabricated duration is added.

### User Story 2 - Review Task Progress (Priority: P1)

Managers and leaders review Task totals, status buckets, completion method, GPS evidence quality, actual completer, and assigned-task-closed metrics separately.

**Why this priority**: Task reporting must not collapse different operational meanings into one metric.

**Independent Test**: Seed Tasks and TaskUpdates with different statuses and completion methods; fetch the task report and verify all counts remain separate.

### User Story 3 - Use Scoped Self Reports (Priority: P2)

Helpdesk users can view only their own report scope even if they submit a different `user_id` filter.

**Why this priority**: Report visibility must follow backend RBAC and object scope.

**Independent Test**: A Helpdesk user requests reports with another user id and receives only self-scoped rows.

### User Story 4 - Export Authorized Reports (Priority: P2)

Managers and leaders export attendance/task CSV reports with no-store headers and audit evidence.

**Why this priority**: Exported files leave the application boundary and require privacy and traceability controls.

**Independent Test**: HELPDESK export is denied before producing evidence; MANAGER export returns CSV, no-store, and one audit row without coordinates by default.

### Edge Cases

- `LOCATION_CHOICE_REQUIRED` is excluded from both numerator and denominator.
- Zero denominator returns `rate_percent = null`.
- Attendance anomalies and rejected AttendanceAttempts are never merged.
- Current user state must not rewrite historical report facts.
- Reporting endpoints must not mutate source data.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide read-only attendance and task report endpoints.
- **FR-002**: System MUST enforce `report.view.self`, `report.view.all`, and `report.export` on the backend.
- **FR-003**: System MUST scope Helpdesk reports to the authenticated actor regardless of supplied `user_id`.
- **FR-004**: System MUST report open sessions, no Check-In today, checked-out today, punch count, valid worked duration, system-closed sessions, anomalies, attempts, rejected diagnostics, nearest-location diagnostics, and failure rate.
- **FR-005**: System MUST keep `AttendanceAnomaly` and rejected `AttendanceAttempt` datasets separate.
- **FR-006**: System MUST calculate failure rate with numerator, denominator, excluded count, and nullable percentage according to CHOT.
- **FR-007**: System MUST report task status counts, completion methods, GPS quality, actual completing actor, and assigned-task-closed count separately.
- **FR-008**: System MUST export attendance/task reports only for export-authorized users with `Cache-Control: private, no-store`.
- **FR-009**: System MUST audit report exports with filters, report type, coordinate opt-in flag, and row count but not sensitive coordinate values.
- **FR-010**: System MUST exclude sensitive coordinates, maps, photo URLs, signed URLs, tokens, and private evidence data by default.

### Key Entities

- **AttendanceReport**: Read model for attendance status, attempts, anomalies, and failure rate.
- **TaskReport**: Read model for task status, completion, GPS quality, and assigned closure metrics.
- **ReportFilters**: Server-validated date range, optional user filter, actor scope, and coordinate opt-in flag.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Failure-rate reports expose numerator, denominator, excluded count, and null percentage for zero denominator.
- **SC-002**: Helpdesk self-scope tests return no other user's rows even with a `user_id` filter.
- **SC-003**: Export tests prove HELPDESK denial, MANAGER audit, CSV content type, and no-store response.
- **SC-004**: OpenAPI and generated TypeScript schema include all report endpoints without drift.

## Assumptions

- CSV is the implemented export format for this slice; additional XLSX/PDF can be added later without weakening authorization or privacy rules.
- Operational job-health projection remains owned by the existing operations feature and is not duplicated in reporting.
