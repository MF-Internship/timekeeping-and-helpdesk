# Feature 007 Task-list Performance Evidence

## Status

**PASSED CONTROLLED RUN**. The harness was run against an isolated local
PostgreSQL 17.11 database after all Feature 007 migrations and API wiring were
applied. It was not run against production and remains outside timing-sensitive
CI.

## Controlled profile

- Harness: `scripts/task_list_capacity_check.py`
- Database: PostgreSQL (required; other engines are rejected)
- Authorized actor: one synthetic MANAGER using the normal Task-list API
- Representative users: `50` total (`1` MANAGER and `49` HELPDESK)
- Representative Task history: `400` synthetic rows evenly covering Overdue,
  Today, Upcoming, and Completed projections, including BLOCKED and completion
  lifecycle history
- Measured reads: `100` complete authorized four-group responses after one
  unmeasured warm-up read
- Target: at least `95/100` reads under `2 seconds` and measured p95 strictly
  below `2 seconds`
- Isolation: fixtures are created inside one transaction and deliberately rolled
  back; the harness verifies its synthetic users no longer exist after rollback
- Data safety: output contains only aggregate count/time/result fields, never
  usernames, Task content, credentials, URLs, GPS, photos, or participant data

## Recorded result

- Run time (UTC): `2026-08-19T23:02:12.970958+00:00`
- PostgreSQL-backed reads: `100/100`
- Reads within target: `100/100`
- Measured p95: `57.211 ms`
- Result: **PASSED**

The transaction rollback assertion also passed, confirming that the synthetic
users and Task history were removed after measurement.
