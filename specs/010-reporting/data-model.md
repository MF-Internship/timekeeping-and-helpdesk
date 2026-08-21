# Data Model: Reporting, Dashboard and Export

## ReportFilters

- `actor_id`: authenticated server actor
- `start_date`, `end_date`: inclusive date range
- `user_id`: optional all-scope filter
- `include_sensitive_coordinates`: explicit export opt-in flag

## AttendanceReport

Read model containing open-session counts, no-check-in counts, checked-out counts, punch count, valid worked minutes, system-closed sessions, anomaly counts, attempt counts, rejected diagnostics, nearest-location diagnostics, and failure rate.

## TaskReport

Read model containing task totals, status counts, completion method counts, GPS quality counts, actual completer counts, and assigned-task-closed count.

## Export Audit

Immutable audit entry with actor, report type, filters, coordinate opt-in flag, and row count. It does not include coordinate values.
