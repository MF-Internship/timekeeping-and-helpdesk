# Implementation Plan: In-App Notifications and Web Push

**Branch**: `008-in-app-web-push` | **Date**: 2026-08-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-in-app-web-push/spec.md`

## Summary

Add a dedicated `notifications` business module whose PostgreSQL-backed inbox is the complete source for exactly five approved Task/Attendance occurrences. Task, Attendance, and Identity keep ownership of their state and call locally defined output/revocation ports; the composition root injects notification adapters so Notification and suppression/revocation changes join the source transaction without cross-module imports. Two externally scheduled, idempotent management commands create due scheduled occurrences and deliver leased `PushDelivery` rows. Web-push transport uses VAPID and encrypted subscriptions outside database transactions; generic payloads carry only an opaque Notification reference. A Next.js inbox, read action, browser opt-in control, service worker, and safe target resolver integrate through the generated client and existing authenticated transport.

## Technical Context

**Language/Version**: Python 3.12–3.13; TypeScript 5.9; Node.js 22+

**Primary Dependencies**: Django 5.2.5, Django REST Framework 3.16.1, drf-spectacular 0.28.0, Next.js 16.3.1, React 19.1.1; add direct pinned `pywebpush==2.3.0` for RFC Web Push/VAPID and `cryptography==50.0.0` for explicit encrypted-at-rest ownership

**Storage**: PostgreSQL 17 for `Notification`, `PushSubscription`, `PushDelivery`, and `Task.assignment_version`; encrypted subscription material only, no push payload persistence

**Testing**: pytest/pytest-django with real PostgreSQL transaction races; Ruff, strict mypy, migration/architecture/contract checks; Vitest/Testing Library, Playwright, ESLint, TypeScript, Prettier; generated OpenAPI/client drift and compatibility checks

**Target Platform**: Linux-hosted Django/Next.js web application; modern secure-context browsers with Service Worker, Notifications, and Push APIs; in-app remains supported when those APIs or push delivery are unavailable

**Project Type**: Existing full-stack web application with separate backend/frontend projects and an external deployment scheduler

**Performance Goals**: At the approved 50-user MVP scale, inbox reads and read mutations remain interactive; each minute-level scheduler run finishes before the next interval under normal load; a delivery provider call never holds a database transaction

**Constraints**: Exactly five event types; Asia/Ho_Chi_Minh time; quiet interval `[21:00,07:00)`; 24-hour push TTL; generic payload; no email/SMS/native push/WebSocket/SSE/Celery/Redis broker/in-process timer; server-owned recipient/time/state; private/no-store API responses; push endpoint material never logged or returned

**Scale/Scope**: 50 internal users, multiple browser subscriptions per user, minute-level occurrence and delivery jobs, existing Task/Attendance/Identity modules and generated `/api/v1/` contract

## Constitution Check

*GATE: Passed before Phase 0 and re-checked after Phase 1.*

- **I — Source of truth**: PASS. CHOT §7/§8/§9.1.1/§10, QUY_TAC, R-97 and accepted R-144–R-147 control the design. The missing self-service actions, assignment version, resolver, durable delivery shape, and assignee-completer condition were corrected in CHOT before code.
- **II — Fixed stack/inward architecture**: PASS. `notifications` has `domain/application/ports/adapters`; source modules depend only on their own ports. `config/` alone composes cross-module adapters. PostgreSQL and the existing web stack remain fixed.
- **III — Authorization order**: PASS. APIs use R-144 actions before DTO validation, then recipient/object scope and target authorization. The target resolver invokes the owning Task/Attendance application boundary and never treats a Notification as a grant.
- **IV — Server authority**: PASS. Recipient, event type, target, dedupe/collapse key, timestamps, state, TTL, schedule, read time, user-agent family, endpoint hash, and delivery result are server-owned. `user_id` and server-owned fields are explicitly rejected.
- **V — DB invariants/transactions**: PASS. Unique/check/FK/index constraints are final guards. Source state + Notification/PushDelivery/suppression/revocation share source transactions. Push HTTP calls occur only after a short claim transaction commits.
- **VI — Audit/observability safety**: PASS. No new AuditAction/Outbox vocabulary is invented. Notification/read/subscription/delivery rows are their owning evidence; rejected/idempotent reads and revokes create no audit/outbox side effect. Logs/telemetry carry closed codes and opaque IDs only.
- **VII — Generated contracts**: PASS. DRF remains the source; OpenAPI and TypeScript are regenerated deterministically, additive-compatible, snake_case, sanitized, and private/no-store.
- **VIII — Safe schema evolution**: PASS. `Task.assignment_version` is an expand migration with `db_default=1`; the new app begins with one leaf. Migration checks, prior-version compatibility, constraints, and catalog indexes are tested.
- **IX — Security/secrets**: PASS. VAPID private key and subscription key ring are typed secrets; the public application key alone reaches the browser. Subscription material is encrypted, endpoint hash is non-reversible, allowed push origins are fail-closed, and deployment egress is inventoried.
- **X — Location integrity**: PASS. No notification/push/audit/log/schema field contains GPS, address, photo, or map data; no location policy is changed.
- **XI — Tests at correct layer**: PASS. Pure policy gets unit boundary tests; APIs/contracts/privacy get integration/contract tests; dedupe, leases, transaction rollback, and source races run on PostgreSQL with competing connections.
- **XII — Maintainability/naming**: PASS. Canonical `Notification`, `PushSubscription`, `PushDelivery`, five event values, R-144 actions, and snake_case wire fields are used. New technical thresholds are centralized and tested.

**Post-design re-check**: PASS. The data model, API contract, transactions, scheduler, frontend boundary, dependency choice, and verification guide introduce no unresolved violation or clarification.

## Project Structure

### Documentation (this feature)

```text
specs/008-in-app-web-push/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── notifications-api.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── notifications/
│   ├── domain/                 # five-event vocabulary, policy, keys, delivery states
│   ├── application/            # inbox, subscription, occurrence, delivery, resolver use cases
│   ├── ports/                  # persistence/UoW/clock/source facts/auth/crypto/transport
│   ├── adapters/
│   │   ├── api/                # thin DRF permissions/serializers/views/urls
│   │   ├── persistence/        # PostgreSQL repositories and UoW
│   │   ├── security/           # subscription encryption and endpoint-origin validation
│   │   ├── web_push.py         # pywebpush transport adapter
│   │   └── clock.py
│   ├── management/commands/    # thin dispatch/delivery shims
│   ├── migrations/
│   ├── apps.py
│   └── models.py
├── tasks/
│   ├── ports/notifications.py
│   ├── adapters/notification_facts.py
│   ├── application/{commands.py,evidence.py,dependencies.py}
│   ├── models.py
│   └── migrations/0004_task_assignment_version.py
├── attendance/
│   ├── ports/notifications.py
│   ├── adapters/notification_facts.py
│   └── application/{commands.py,dependencies.py}
├── identity/
│   ├── ports/push_subscriptions.py
│   ├── adapters/notification_facts.py
│   ├── domain/authorization.py
│   └── application/{authentication.py,user_admin.py,dependencies.py}
├── config/
│   ├── composition.py
│   ├── notification_adapters.py
│   ├── settings.py
│   └── urls.py
└── tests/
    ├── unit/notifications/
    ├── integration/api/notifications/
    ├── integration/postgres/notifications/
    ├── contract/notifications/
    └── architecture/

frontend/
├── public/notification-sw.js
├── src/app/notifications/page.tsx
├── src/app/notifications/open/[reference]/page.tsx
├── src/features/notifications/
│   ├── api/notification-api.ts
│   ├── adapters/browser-push.ts
│   ├── model/{notification-state.ts,use-notifications.ts}
│   └── ui/{NotificationInbox.tsx,PushOptInControl.tsx}
├── src/features/identity/model/AuthProvider.tsx
├── src/shared/ui/shell/
└── tests/{unit,architecture,e2e}/notifications/

deploy/scheduled-jobs.yaml
scripts/{deployment_check.py,migration_check.py,check_architecture.py,check_all.sh}
contracts/openapi.yaml
```

**Structure Decision**: Reuse the repository's separate backend/frontend layout and established business-module layering. Notification owns its rows and policies. Task, Attendance, and Identity expose only local ports/fact adapters; `config/notification_adapters.py` is the sole production cross-module composition point. Management commands contain no policy.

## Design and Ownership

### Domain vocabulary and policies

- `NotificationEventType` has exactly `TASK_ASSIGNED`, `TASK_UPCOMING`, `TASK_OVERDUE`, `ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END`, and `MULTI_ASSIGNEE_TASK_COMPLETED`; a cardinality test rejects additions.
- Pure policy computes recipient occurrence keys, local due times, quiet-hour release, 24-hour expiry, stable collapse keys, and allowed state transitions.
- `TASK_ASSIGNED` uses Task + recipient + `assignment_version`; upcoming uses Task + recipient + `assigned_date`; overdue adds local occurrence date; open-session uses session + owner; multi-completion uses Task + other recipient.
- In-app title may be event-specific but contains no unverified target data. Push title/body are constant generic strings; only opaque `Notification.public_id` is included as data.

### Immediate source integration

- Task create/update calls a Task-owned occurrence sink after assignee rows and `assignment_version` are finalized but before the Task UoW commits. Added assignees receive `TASK_ASSIGNED`; removed assignees' pending deliveries are suppressed.
- Both `complete_override` and FIELD_EVIDENCE completion call the sink inside the locked Task transaction to suppress pending upcoming/overdue deliveries. It persists event 5 only when `completed_by` is a current assignee and the current set has at least two members; Manager override/non-assignee completion emits no event 5.
- Attendance Check Out calls an Attendance-owned suppression sink after closing the locked session and before commit.
- Identity logout always invokes the identity-owned subscription revoker in its User transaction, even if zero refresh sessions were revoked. Active→inactive does the same for the target. No source module imports `notifications` internals.
- The adapter inserts Notification and PushDelivery rows with PostgreSQL conflict handling scoped to the named unique constraint. It performs no network call and no independent commit.

### Scheduled occurrence dispatch

- `dispatch_notification_occurrences` is an idempotent external-scheduler command run every minute. The application service uses server time in Asia/Ho_Chi_Minh and look-back-safe predicates: upcoming is due once local time is at/after 17:00 on the previous date, overdue is due once local time is at/after 08:00 for that local date, and open-session is due once local time is at/after configured `shift_end - 30 minutes`.
- Task/Attendance fact adapters select candidates without cross-module imports, then lock and revalidate each source row inside one transaction before inserting. Dedupe keys make overlapping/retried runs safe. Holidays and working weekdays are not consulted.
- Immediate and scheduled notification creation also materializes one `PushDelivery` per active subscription. Quiet policy sets `not_before` to the next 07:00; otherwise it is immediately due. `expires_at = occurred_at + 24 hours`.

### Push delivery and suppression

- `deliver_web_push` runs every minute. A worker reads an eligible candidate ID, locks/revalidates source facts first, then conditionally leases the delivery with `select_for_update(skip_locked)` and a persisted lease. Revoked/inactive/stale/expired rows become terminal without transport.
- The claim transaction commits before decrypting/calling the push origin. Transport gets a timeout, TTL remaining in seconds, and a stable Topic/collapse header. Raw provider exceptions/responses are mapped to closed failure codes and never logged.
- Success finalization is conditional on the same lease. Permanent invalid-subscription responses revoke that subscription and suppress its pending rows; transient errors increment attempts and set bounded `next_attempt_at` no later than expiry. A crashed worker's expired lease is reclaimable.
- A source mutation may suppress PENDING/LEASED delivery under the same source lock. If delivery has already crossed its revalidation/claim linearization point, best-effort semantics allow the unavoidable provider race; no source/read state is altered.

### Inbox, read state, subscriptions, and target resolution

- APIs are the additive contracts in [contracts/notifications-api.md](contracts/notifications-api.md). All responses use `Cache-Control: private, no-store` and canonical errors.
- R-144 action permission runs before serializer validation. Listing and target resolution use `notification.view.self`; read uses `notification.update.self`; subscription upsert/delete uses `push_subscription.manage.self`.
- List is recipient-filtered newest-first and returns the server unread count. Read uses a conditional owner-scoped update so two requests retain the first server timestamp.
- Subscription upsert accepts only endpoint + browser keys, validates an exact configured HTTPS origin, hashes the endpoint, encrypts the full material, and atomically makes that active endpoint identity belong to the current account. Response returns only opaque subscription ID/state/timestamps.
- Target resolver finds Notification by opaque public UUID and recipient, then invokes an injected Task/Attendance authorization/fact port. It returns only a closed destination plus an already-authorized target ID where needed; it does not mark read.

### Frontend behavior

- The generated client remains above `authenticatedFetch`. Notification state resets immediately when authenticated account ID changes or becomes anonymous/inactive/forced-change.
- Inbox supports load/empty/error/refresh, unread badge, explicit mark-read, and safe open. No push click or open action marks read.
- Opt-in registers the static service worker only after a user gesture, requests browser permission, subscribes with the public VAPID key, then upserts server state. Unsupported/denied/storage/API failures are truthful UI states.
- A non-sensitive local marker stores only account ID + opaque server subscription ID. On logout/account switch/inactive status the server revoke occurs before tokens are cleared, then browser unsubscribe/marker purge runs best-effort.
- The service worker accepts only the fixed generic payload schema and same-origin `/notifications/open/<opaque-reference>` path. Notification click opens/focuses that route; the route resolves server authorization before navigation to `/tasks` or `/attendance`.
- Inbox refreshes on route load, explicit refresh, successful read, and document visibility return; no realtime transport is added.

### Configuration, dependencies, and deployment

- Add pinned direct `pywebpush==2.3.0` and `cryptography==50.0.0`, update `uv.lock`, provenance documentation, secret scan, licenses, and dependency review. Native browser APIs require no npm dependency.
- Typed configuration owns `WEB_PUSH_ENABLED`, VAPID private/public key pair, VAPID subject, subscription-encryption key ring, and exact allowed HTTPS push origins. A typed frontend adapter validates optional `NEXT_PUBLIC_WEB_PUSH_APPLICATION_SERVER_KEY`; when absent it reports push unavailable while inbox remains usable, and when present it must be a valid P-256 public-key encoding. Other values never enter the browser bundle.
- Development/test may disable push so in-app still runs; enabling push with missing/empty/malformed keys or origins fails closed. Staging/production deployment readiness requires enabled, resolved secret identities and matching public-key identity without committing values.
- Extend the non-secret environment inventory, egress/runbook, secret rotation procedure, and scheduler readiness. Approved outbound network is only configured exact push-service origins; no arbitrary endpoint origin, broker, or new hosted service is added.
- Preserve the existing `missing-check-out-reconciliation` job and add singleton minute jobs for dispatch and delivery in `deploy/scheduled-jobs.yaml`. Generalize readiness validation instead of hardcoding a single job.

### Migration, constraints, and indexes

- `tasks.0004` adds positive `assignment_version` with Python and database default 1; no backfill loop or contract removal. Old processes can continue inserting Tasks during rolling deployment.
- `notifications.0001_notification` creates Notification; `notifications.0002_push_delivery` later expands with PushSubscription and PushDelivery. Both are additive, form one linear migration leaf, and contain the checks, FKs, UUID identities, unique keys, state/time shapes, and indexes described in [data-model.md](data-model.md).
- Extend `scripts/migration_check.py` ownership and architecture/module enumerations. Each app retains one leaf. Catalog tests inspect every constraint/index on PostgreSQL and migrate from previous leaves.

### Audit, outbox, and failure semantics

- No email/SMS/account-security event, new AuditAction, or business OutboxEvent is introduced. Notification insertion is a direct transactional output port because the repository has no approved outbox relay implementation; `PushDelivery` is the durable feature-owned delivery queue.
- Notification read/upsert/revoke/delivery rows are not copied into AuditLog/OutboxEvent. Idempotent and rejected paths create no forbidden evidence. Subscription plaintext/payload/provider response is absent from every sink.
- Task/Attendance business audit behavior remains unchanged; injected notification writes roll back with the source transaction and never make the source operation fail due to provider/network behavior.
- Canonical existing errors are reused: authentication/account/password gates, `PERMISSION_DENIED`, `SERVER_OWNED_FIELD`, `NOT_FOUND`, `VALIDATION_FAILED`, and `SERVICE_UNAVAILABLE`. No provider-specific details cross the API.

## Verification Strategy

- **Unit**: five-value cardinality; all occurrence keys/recipients; exact local boundaries; TTL equality; delivery transition/backoff/lease rules; generic payload; endpoint origin; encryption round-trip/rotation; resolver decisions.
- **API/contract**: auth/action-before-body precedence; self-only/no `user_id`; cross-user non-disclosure; list/unread/read idempotency; opt-in/revoke; safe target; no secret response/schema/example; private/no-store; deterministic generated artifacts.
- **PostgreSQL**: unique/check/FK/index catalog; duplicate occurrence races; assignment remove/re-add version; Task rollback; completion-vs-reminder and checkout-vs-scan; read/read; endpoint registration/account switch; logout/deactivation-vs-claim; lease reclaim; suppression/expiry; prior-version migration compatibility.
- **Frontend**: provider/state isolation, full inbox states, explicit read, browser capability/consent failures, server-before-local logout ordering, generic worker payload, same-origin allowlist, safe target route, responsive/accessibility and e2e flows.
- **CI/static**: include `notifications` in Ruff/mypy/hatch/architecture/function-size/pre-commit/check-all lists; PostgreSQL marker suite; dependency/secret checks; scheduler/deployment checks; OpenAPI generation/safety/compatibility/client drift; frontend format/lint/type/test/build.

## Complexity Tracking

No Constitution violation requires a waiver. The two new direct dependencies are the minimum reviewed implementation of explicitly approved Web Push cryptography/VAPID and encrypted-at-rest subscription storage; hand-rolled cryptography was rejected. `PushDelivery` uses the existing PostgreSQL and external scheduler rather than adding queue infrastructure.
