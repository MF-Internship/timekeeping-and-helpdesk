# Feature 004 Latency Acceptance

- Run time (UTC): `2026-08-18T16:23:35.498739+00:00`
- Harness: `scripts/attendance_interaction_check.py`
- PostgreSQL-backed command-plus-today-read trials: `100`
- Distinct test users: `50`
- Canonical Locations: `76`
- Baseline same-day sessions for measured actor: `20`
- Target: `< 2 seconds` for at least `95/100` trials
- Trials within target: `100/100`
- Measured p95: `26.226 ms`
- Result: **PASS**

The harness ran inside an outer transaction and deliberately rolled it back.
Post-run verification found zero benchmark users and zero benchmark Attendance
rows. This evidence intentionally contains no GPS coordinates, credentials, or
secrets.
