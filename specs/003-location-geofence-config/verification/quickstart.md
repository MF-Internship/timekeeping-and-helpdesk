# Quickstart execution evidence

Executed 2026-08-18 in the isolated local verification environment.

- CSV preflight: exact separate headers; center count 7; shop count 69.
- Migrations: `makemigrations --check --dry-run` reported no drift; migration safety and one-leaf
  tests passed.
- Config initialization, repeated initialization, complete locked-Config validation, seed twice,
  exact active/default-radius readiness success, and drift failure: passed through the real
  management-command/application PostgreSQL suites.
- Unit GPS/geofence suite: passed.
- API/RBAC/optimistic update suite: passed.
- PostgreSQL transaction/race, both audit/outbox recorder rollback paths, Holiday double-delete,
  and audit aggregate-version suites: passed.
- OpenAPI, safety, contract drift, generated client, frontend type/test/build: passed.
- Full `scripts/check_all.sh`: passed with 533 non-PostgreSQL tests, 90 PostgreSQL tests
  (2 intentionally deselected), and 81 frontend tests.
- Focused Feature 003 contract/unit/API/PostgreSQL suite: 181 passed, including the
  exhaustive Config invalid-value matrix and complete fail-closed readiness drift matrix.

No credential, token, DSN, or source coordinate was copied into this evidence.
