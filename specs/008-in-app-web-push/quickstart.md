# Quickstart Verification: In-App Notifications and Web Push

This guide validates Feature 008 after implementation. It does not replace automated tests or contain implementation code.

## Prerequisites

- PostgreSQL test database configured through the existing backend test environment.
- Backend dependencies synchronized from the updated lockfile.
- Frontend dependencies installed from `package-lock.json`.
- Controlled clocks/fake push transport for automated tests; CI must not call a real push provider.
- For manual browser acceptance, HTTPS (or localhost secure-context allowance), a valid VAPID key pair, subscription-encryption key, and reviewed push-origin allowlist.

## 1. Authority and artifact checks

Confirm Feature 008 traces to CHOT §7/§8/§9.1.1/§10, R-97 and R-144–R-147, and that specification/checklist/plan/data model/API contract contain exactly five event types with no clarification marker.

Expected: no email/SMS/native/account-security notification; no unresolved Constitution violation.

## 2. Backend focused static and unit gates

From the repository root:

```text
uv run --project backend ruff format --check backend scripts
uv run --project backend ruff check backend scripts
uv run --project backend mypy backend/core backend/config backend/operations backend/identity backend/audit backend/locations backend/attendance backend/tasks backend/notifications scripts
cd backend
uv run pytest tests/unit/notifications tests/architecture -v
```

Expected: exact enum cardinality, key formats, recipient matrices, 21:00/07:00 and TTL equality, payload privacy, endpoint-origin policy, encryption rotation, import boundaries, and maintainability pass.

## 3. API and contract gates

```text
cd backend
uv run pytest tests/integration/api/notifications tests/contract/notifications -v
uv run python manage.py makemigrations --check --dry-run
cd ..
uv run --project backend python scripts/migration_check.py check
uv run --project backend python scripts/generate_openapi.py --check
uv run --project backend python scripts/check_openapi.py --all
uv run --project backend python scripts/check_contract_drift.py
```

Run the existing OpenAPI compatibility command supported by the local shell, then:

```text
npm --prefix frontend run api:check
```

Expected: additive routes/projections, canonical errors, action-before-body ordering, self scope, safe resolver, no secret/schema examples, deterministic OpenAPI and generated TypeScript.

## 4. PostgreSQL invariants and races

```text
cd backend
uv run pytest -m postgres tests/integration/postgres/notifications -v
```

Required evidence:

- All Notification/PushSubscription/PushDelivery checks, uniques, FKs, defaults, partial indexes, and due indexes exist in PostgreSQL.
- Competing duplicate handlers/scans produce one Notification and one delivery per subscription.
- Task assignment remove/re-add increments assignment version and yields a new assignment occurrence; no-op does not.
- Task transaction rollback removes its Notification/PushDelivery rows.
- Completion racing upcoming/overdue and Check Out racing open-session scan has a serialized, suppression-safe result.
- Concurrent reads preserve the first `read_at`.
- Concurrent endpoint registration/account switch has one active endpoint owner.
- Logout/deactivation racing delivery prevents any claim that linearizes after revocation.
- Expired leases are reclaimed; TTL equality expires; source/provider failure never changes Task/Attendance/read state.
- Migration executor proves previous leaves → new leaves and rolling-compatible Task default.

## 5. Frontend focused gates

```text
npm --prefix frontend run format:check
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test
npm --prefix frontend run build
```

Expected: inbox load/empty/error/refresh, unread count, explicit/idempotent read, account-state reset, browser unsupported/denied/failure, server-before-local revoke ordering, generic service-worker payload, same-origin click, safe resolver navigation, responsive/accessibility, and generated-client transport boundary pass.

## 6. Controlled end-to-end acceptance

With push disabled, create each occurrence and verify exactly one in-app row for each eligible recipient:

1. Newly assign a Helpdesk user.
2. Advance controlled local time past 17:00 before an incomplete Task's assigned date.
3. Advance past 08:00 after assigned date.
4. Keep a session open through `shift_end - 30 minutes`.
5. Complete a multi-assignee Task and verify every other assignee, not `completed_by`.

Then verify read/unread and cross-account denial. Expected: all inbox behavior works with zero active subscription and zero provider call.

With fake push transport enabled:

- 20:59 delivers immediately; 21:00 and 06:59 defer; 07:00 releases after revalidation.
- Exactly 24 hours expires.
- Complete Task/remove assignee/Check Out/revoke/logout/deactivate before delivery suppresses it.
- Provider transient/permanent failures follow retry/revoke policy without touching inbox/read/source state.
- Captured payload/headers contain generic content, opaque reference, TTL/collapse only; no sensitive values.

## 7. Manual browser opt-in acceptance

- Open the authenticated Notifications page in a supported secure-context browser.
- Choose opt-in; verify permission is requested only after that gesture and UI reports the server-confirmed state.
- Trigger a generic fake/test-environment notification and verify lock-screen text reveals no Task/person/location/photo detail.
- Click it; verify `/notifications/open/<opaque>` resolves authorization before navigation and does not mark read.
- Logout, log into another account, and verify the old marker/subscription/inbox never appears or auto-binds.
- Deny permission and repeat in an unsupported browser; in-app remains complete and UI does not claim success.

## 8. Deployment and final repository gate

Validate both new singleton scheduler bindings, preserved reconciliation binding, typed secret identities, allowed egress, key rotation runbook, and no committed values. Run the repository's full gate:

```text
scripts/check_all.sh
```

If Bash is unavailable on the host, run every command enumerated by that script and both CI workflow matrices individually; do not treat a skipped shell script as a pass.

Definition of done: every automated gate is green, all controlled acceptance cases above pass, no CRITICAL analysis finding remains, generated artifacts are clean, and the feature contains exactly five notification event types.

## Automated verification record — 2026-08-21

Executed on Windows/PowerShell with an isolated PostgreSQL 17 test container and fake Web Push transport:

- Notification-focused backend/unit/API/contract checks: passed; focused application/config/privacy set `72 passed`.
- Notification PostgreSQL constraints, rollback, dedupe, endpoint ownership, read, lease, revoke, and suppression races: `11 passed`.
- Complete PostgreSQL integration marker suite: `214 passed, 2 deselected`.
- Complete non-PostgreSQL backend suite, excluding the two documented platform-only files below: `948 passed, 217 deselected`.
- Backend Ruff, strict mypy, maintainability, migration drift, Django system check, deterministic OpenAPI, privacy scan, client drift, deployment scheduler/egress contracts: passed.
- Frontend generated API, Prettier, TypeScript, Vitest (`85 files / 450 tests`), production build, and notification Playwright (`3 passed`, including mobile/accessibility and stale-link denial): passed.

Platform-specific fallback: `scripts/check_all.sh` and the OASDiff compatibility test harness are Bash executables and cannot be launched directly by Win32 (`WinError 193`); their constituent cross-platform gates were run individually. The repository-wide capacity benchmark also remains timing-sensitive on this Windows host (observed p95 above its fixed threshold); it is unrelated to Feature 008. Full ESLint reports only three pre-existing max-function-length errors outside notifications (`LocationDirectory.tsx`, `use-task-management.ts`, and `FieldEvidenceForm.tsx`); focused notification ESLint is green.

Not claimed as executed: real push-provider delivery, physical lock-screen inspection, and manual multi-browser permission acceptance. CI uses fake transport by design; these remain deployment/manual acceptance steps requiring provisioned VAPID credentials and an approved provider endpoint.
