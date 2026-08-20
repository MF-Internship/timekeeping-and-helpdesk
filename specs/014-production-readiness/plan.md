# Implementation Plan: Production Readiness

Existing deployment, migration, recovery, cache, and capacity tooling already covers most R-107/R-108/R-109 behavior. Feature 014 hardens drift found after Features 011–013 and records unresolved infrastructure evidence.

Implementation:

- Align restore probes with the canonical `audit_outboxevent` table.
- Ensure PostgreSQL restore tests use the active test DB DSN.
- Keep capacity checker semantics but make the local contract server suitable for 20-way concurrency.
- Update migration-leaf pins after Feature 013.
- Add Spec Kit trace artifacts and deferred work for real infrastructure evidence.

Verification:

- deployment/readiness contract tests;
- recovery restore PostgreSQL tests;
- migration safety tests;
- cache policy tests;
- capacity checker tests;
- focused lint/type checks.
