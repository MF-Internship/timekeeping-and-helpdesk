# Tasks: In-App Notifications and Web Push

**Input**: Design documents from `/specs/008-in-app-web-push/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are mandatory per the feature request, Constitution XI, plan verification strategy, and Definition of Done. Within each behavior group, add the failing test before implementation and run the listed focused gate after the group.

**Organization**: Tasks are dependency ordered and grouped by independently testable user story. Every task has one verifiable outcome and concrete paths.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Genuinely independent files/outcomes that can proceed concurrently after their phase prerequisites
- **[Story]**: User story from spec.md

## Phase 1: Setup and Governed Module Registration

**Purpose**: Add only the approved dependency/module/config scaffolding and make repository gates aware of the new owner before behavior work.

- [X] T001 Add reviewed direct pins `pywebpush==2.3.0` and `cryptography==50.0.0`, notification package ownership, and regenerated resolution in `backend/pyproject.toml`, `backend/uv.lock`, and `docs/ARCHITECTURE.md`; verify no unrelated dependency changes
- [X] T002 Create the empty inward-layer package structure and Django app metadata in `backend/notifications/{__init__.py,apps.py,domain/__init__.py,application/__init__.py,ports/__init__.py,adapters/__init__.py,adapters/api/__init__.py,adapters/persistence/__init__.py,adapters/security/__init__.py,migrations/__init__.py,management/__init__.py,management/commands/__init__.py}` and register only `notifications` in `backend/config/settings.py`
- [X] T003 [P] Extend module/import ownership checks for `notifications` and the existing `tasks` module in `scripts/check_architecture.py`, `backend/tests/architecture/test_module_boundaries.py`, and `backend/tests/architecture/test_task_feature_boundary.py`; prove cross-module internals fail while `config/`, tests, migrations, and local ports remain the closed exemptions
- [X] T004 [P] Extend migration-owner, maintainability, mypy, package, pre-commit, local full-gate, and CI path enumerations for `backend/notifications` in `scripts/migration_check.py`, `scripts/check_all.sh`, `.pre-commit-config.yaml`, `.github/workflows/quality.yml`, `.github/workflows/contract.yml`, and `backend/pyproject.toml`
- [X] T005 [P] Add failing typed-configuration tests for disabled in-app-only mode and enabled push with missing/empty/malformed VAPID key pair, subject, encryption key ring, and exact HTTPS origin allowlist in `backend/tests/unit/core/test_notification_settings.py` and `backend/tests/contract/test_deployment_checks.py`
- [X] T006 Implement typed `WEB_PUSH_*` configuration, public-key derivation/consistency, fail-closed enabled mode, safe variable-name-only diagnostics, and disabled in-app-only mode in `backend/core/deployment.py`, `backend/config/settings.py`, `backend/tests/settings.py`, and `.env.example`
- [X] T007 [P] Add non-secret Web Push secret identities, public-key identity, exact egress origins, and rotation/incident procedure to `deploy/environments.yaml`, `docs/TRIEN_KHAI.md`, and `docs/ARCHITECTURE.md`; verify no actual key, endpoint, credential, or DSN is committed
- [X] T008 [P] Add failing R-144 matrix/cardinality/Leader-exception tests in `backend/tests/unit/identity/test_authorization.py`, `backend/tests/unit/identity/test_permission_provenance.py`, and `backend/tests/integration/api/identity/test_authorization_matrix.py`
- [X] T009 Implement exactly the three R-144 actions, direct grants for all roles, no sixth implication, and mutation classification limited to the two self-service writes in `backend/identity/domain/authorization.py`

**Gate 1**: Ruff/mypy architecture, configuration, dependency, and authorization focused tests pass; no notification behavior exists yet.

---

## Phase 2: Foundational Notification Persistence and Ports

**Purpose**: Build the authoritative Notification foundation and cross-module abstractions that block all user stories.

**⚠️ CRITICAL**: No user story work starts until this phase passes on PostgreSQL.

- [X] T010 [P] Add failing pure-domain tests for exact five-event cardinality, target vocabulary, safe titles, stable occurrence/collapse key formats, assignment-version identity, and rejection of a sixth/account-security event in `backend/tests/unit/notifications/test_event_policy.py`
- [X] T011 Implement `NotificationEventType`, `NotificationTargetType`, occurrence inputs, safe titles, deterministic dedupe keys, and collapse-key normalization in `backend/notifications/domain/events.py`
- [X] T012 [P] Add failing model-contract and PostgreSQL catalog tests for Notification UUID/dedupe uniqueness, closed values, positive target, nonblank title/key, read-time shape, owner/target/unread indexes, and FK protection in `backend/tests/unit/notifications/test_model_contract.py` and `backend/tests/integration/postgres/notifications/test_notification_constraints.py`
- [X] T013 Add `Notification` with all constraints/indexes/defaults from data-model.md and the expand-only initial migration in `backend/notifications/models.py` and `backend/notifications/migrations/0001_notification.py`
- [X] T014 [P] Define framework-free protocols/snapshots for Notification persistence, UoW, clock, account eligibility, Task facts/authorization, Attendance facts/authorization, and source occurrence/suppression sinks in `backend/notifications/ports/{repositories.py,unit_of_work.py,clock.py,accounts.py,targets.py}` and `backend/notifications/application/dto.py`
- [X] T015 [P] Define source-owned notification/revocation port contracts with primitive/local typed inputs in `backend/tasks/ports/notifications.py`, `backend/attendance/ports/notifications.py`, and `backend/identity/ports/push_subscriptions.py`; add protocol tests proving no source module imports notification internals in `backend/tests/architecture/test_notification_boundaries.py`
- [X] T016 Implement PostgreSQL Notification insert-on-named-conflict, recipient list/count, conditional first-read primitive, target lookup, and ambient transaction UoW adapters in `backend/notifications/adapters/persistence/{repositories.py,unit_of_work.py}` and clock adapter in `backend/notifications/adapters/clock.py`
- [X] T017 Create dependency/container types without business logic in `backend/notifications/application/{dependencies.py,container.py}` and wire the notification container plus source fact/output adapter placeholders only in `backend/config/{composition.py,notification_adapters.py}`
- [X] T018 [P] Add migration-executor tests for no previous notifications leaf → `0001_notification`, PostgreSQL constraint/index survival, and Task previous leaf compatibility fixture in `backend/tests/integration/postgres/notifications/test_migration_compatibility.py`

**Gate 2**: Domain/model/architecture tests and the notification PostgreSQL constraint/migration suite pass; the new module is an inert persistence owner.

---

## Phase 3: User Story 1 — Complete Authoritative In-App Inbox (Priority: P1) 🎯 MVP

**Goal**: Persist and list exactly the five supported occurrences for only eligible recipients even when Web Push is disabled.

**Independent Test**: Disable push, exercise all five source/scheduled occurrences, and prove exactly one in-app Notification per eligible recipient, zero for every excluded recipient/event, complete newest-first self-only inbox, and rollback with source transactions.

### Tests for User Story 1

- [X] T019 [P] [US1] Add failing API/contract tests for authenticated self-only `GET /api/v1/notifications/`, newest-first items/unread count, empty inbox, no `user_id`, private/no-store, R-144 action precedence, canonical errors, and zero read/audit/outbox/delivery side effects in `backend/tests/integration/api/notifications/test_inbox_api.py` and `backend/tests/contract/notifications/test_inbox_contract.py`
- [X] T020 [P] [US1] Add failing Task unit tests for create/add/remove/no-op assignment occurrence recipients, assignment-version increments, rollback-safe sink calls, both completion paths suppressing stale reminders, and event 5 occurring only for a current-assignee completer with at least two assignees—not Manager override/non-assignee/single-assignee cases—in `backend/tests/unit/tasks/test_notification_occurrences.py` and `backend/tests/unit/tasks/test_evidence_notification_occurrences.py`
- [X] T021 [P] [US1] Add failing scheduled-occurrence unit tests for 17:00 upcoming, 08:00 per-local-day overdue, configured `shift_end - 30 minutes`, active/current-assignee/session eligibility, late scheduler look-back, weekend/holiday inclusion, and exact five-event output in `backend/tests/unit/notifications/test_occurrence_dispatch.py`
- [X] T022 [P] [US1] Add failing PostgreSQL races for duplicate immediate/scan handlers, Task create/update/completion rollback after Notification insert, assignee remove/re-add version, completion-vs-upcoming/overdue, and Check-Out-vs-open-session scan in `backend/tests/integration/postgres/notifications/test_occurrence_concurrency.py` and `backend/tests/integration/postgres/notifications/test_source_atomicity.py`
- [X] T023 [P] [US1] Add failing frontend API/state/UI tests for typed inbox fetch, load/empty/error/refresh, server unread count, event labels, account-state isolation, no target inference, and no push dependency in `frontend/tests/unit/notifications/{notification-api.test.ts,notification-state.test.tsx,notification-inbox.test.tsx}`

### Implementation for User Story 1

- [X] T024 [US1] Add positive `Task.assignment_version` with Python/DB default 1 and expand migration in `backend/tasks/models.py` and `backend/tasks/migrations/0004_task_assignment_version.py`; update model/migration contract expectations in `backend/tests/unit/tasks/test_model_contract.py` and `backend/tests/integration/postgres/tasks/test_task_migration.py`
- [X] T025 [US1] Increment assignment version exactly once under the existing Task lock for real assignee-set changes and keep create/no-op/content/status semantics stable in `backend/tasks/application/commands.py`, `backend/tasks/application/dto.py`, `backend/tasks/ports/repositories.py`, and `backend/tasks/adapters/persistence/repositories.py`
- [X] T026 [US1] Inject and call the Task-owned occurrence/suppression sink inside Task create/update/override transactions and FIELD_EVIDENCE completion in `backend/tasks/application/{dependencies.py,commands.py,evidence.py,container.py}`; suppress stale reminders for every completion but emit event 5 only when the completer is a current assignee of a multi-assignee Task, without provider calls or new Task audit/outbox behavior
- [X] T027 [US1] Inject and call the Attendance-owned open-session suppression sink inside successful Check Out before commit in `backend/attendance/application/{dependencies.py,commands.py,container.py}`
- [X] T028 [P] [US1] Implement Task candidate/lock/revalidation and target-authorization adapters using only Task internals in `backend/tasks/adapters/notification_facts.py`, including current active assignees, completed state, assignment version, and both read scopes
- [X] T029 [P] [US1] Implement Attendance open-session candidate/lock/revalidation and target-authorization adapters using only Attendance/Config-approved ports in `backend/attendance/adapters/notification_facts.py`, preserving the canonical session lock used by Check Out
- [X] T030 [P] [US1] Implement active-account/recipient projection adapter using only Identity internals in `backend/identity/adapters/notification_facts.py`
- [X] T031 [US1] Implement atomic immediate occurrence recording and source-state suppression application services, including named unique-conflict handling and no push requirement, in `backend/notifications/application/occurrences.py`
- [X] T032 [US1] Implement look-back-safe scheduled Task/Attendance dispatch with per-candidate transaction/lock/revalidation and Asia/Ho_Chi_Minh server clock in `backend/notifications/application/dispatch.py`
- [X] T033 [US1] Implement the thin idempotent `dispatch_notification_occurrences` command and container entry point in `backend/notifications/management/commands/dispatch_notification_occurrences.py` and `backend/notifications/application/container.py`
- [X] T034 [US1] Complete source-output/fact adapter composition in `backend/config/notification_adapters.py` and inject dependencies into existing Task, Attendance, and notification containers via `backend/config/composition.py`
- [X] T035 [US1] Implement R-144 permission, output serializer, thin list view, URL fragment, and operation ID in `backend/notifications/adapters/api/{permissions.py,serializers.py,views.py,urls.py}` and compose it beneath the single prefix in `backend/config/urls.py`
- [X] T036 [US1] Regenerate and verify the additive inbox operation in `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts` using `scripts/generate_openapi.py` and `frontend/scripts/generate-api.mjs`; do not hand-edit generated artifacts
- [X] T037 [US1] Implement generated-client inbox wrapper/state hook and reset-on-account-change behavior in `frontend/src/features/notifications/api/notification-api.ts` and `frontend/src/features/notifications/model/{notification-state.ts,use-notifications.ts}`
- [X] T038 [US1] Implement accessible inbox UI, unread badge projection, authenticated R-144 route handling (including loading/anonymous/inactive/forced-change denies), and responsive shell navigation in `frontend/src/features/notifications/ui/NotificationInbox.tsx`, `frontend/src/app/notifications/page.tsx`, `frontend/src/features/identity/model/IdentityRouteBoundary.tsx`, `frontend/src/shared/ui/shell/{employee-navigation.ts,AppShell.tsx,AppHeader.tsx}`, and centralized messages/styles

**Gate 3 / MVP**: With push disabled, all US1 unit/API/contract/PostgreSQL/frontend tests pass for exactly five complete in-app occurrences and source rollback.

---

## Phase 4: User Story 2 — Track Read and Unread State (Priority: P1)

**Goal**: Let a recipient explicitly mark only their own Notification read once while preserving the first server timestamp and unread count.

**Independent Test**: Two users have notifications; one owner performs concurrent/repeated reads and only that row changes once, while foreign/malformed/server-owned-field attempts disclose nothing and create no side effect.

### Tests for User Story 2

- [X] T039 [P] [US2] Add failing API/contract tests for empty-body read, first timestamp, idempotent repetition, `user_id`/`read_at`/unknown-field rejection, action-before-body order, foreign/malformed/nonexistent non-disclosure, and no audit/outbox/delivery side effects in `backend/tests/integration/api/notifications/test_read_api.py` and `backend/tests/contract/notifications/test_read_contract.py`
- [X] T040 [P] [US2] Add failing PostgreSQL two-connection read/read race proving one first timestamp and correct unread count in `backend/tests/integration/postgres/notifications/test_read_concurrency.py`
- [X] T041 [P] [US2] Add failing frontend tests for explicit mark-read only, pending/failure/retry, server-confirmed timestamp/count, and no implicit read on item open/push click in `frontend/tests/unit/notifications/notification-read.test.tsx`

### Implementation for User Story 2

- [X] T042 [US2] Implement owner-scoped conditional first-read use case and unchanged-repeat projection in `backend/notifications/application/inbox.py`
- [X] T043 [US2] Implement strict empty input serializer, R-144 permission, thin read view/URL, canonical non-disclosing lookup, private/no-store, and stable operation ID in `backend/notifications/adapters/api/{serializers.py,permissions.py,views.py,urls.py}`
- [X] T044 [US2] Regenerate the read contract/client and implement typed read wrapper/state update in `contracts/openapi.yaml`, `frontend/src/shared/api/schema.ts`, `frontend/src/features/notifications/api/notification-api.ts`, and `frontend/src/features/notifications/model/use-notifications.ts`
- [X] T045 [US2] Add explicit accessible read action and stable unread presentation without open-on-read behavior in `frontend/src/features/notifications/ui/NotificationInbox.tsx`

**Gate 4**: US2 API/PostgreSQL/frontend tests pass independently over US1 inbox persistence.

---

## Phase 5: User Story 3 — Opt In and Revoke Best-Effort Web Push (Priority: P2)

**Goal**: Register/revoke encrypted self-owned browser subscriptions and send a generic best-effort push outside quiet hours without affecting the inbox.

**Independent Test**: One supported browser opts in, receives only a generic fake-transport push, revokes, and receives no later delivery; unsupported/denied/provider failure leaves the complete inbox unchanged.

### Tests for User Story 3

- [X] T046 [P] [US3] Add failing encryption/origin/payload unit tests for key-ring rotation, ciphertext-only persistence boundary, SHA-256 identity, exact allowed HTTPS origins, invalid key material, constant generic payload, TTL/Topic headers, timeout, and provider-error redaction in `backend/tests/unit/notifications/{test_subscription_security.py,test_web_push_transport.py}`
- [X] T047 [P] [US3] Add failing model/PostgreSQL tests for PushSubscription/PushDelivery constraints, active endpoint partial uniqueness, owner indexes, unique Notification × subscription, state/time/lease shapes, and due indexes in `backend/tests/unit/notifications/test_delivery_model_contract.py` and `backend/tests/integration/postgres/notifications/test_delivery_constraints.py`
- [X] T048 [P] [US3] Add failing API/contract tests for owner-only idempotent subscription upsert/revoke, strict body/no `user_id`, no endpoint/key/ciphertext/schema/example/log leakage, disabled-push 503 with working inbox, foreign denial, and repeated revoke in `backend/tests/integration/api/notifications/test_subscription_api.py` and `backend/tests/contract/notifications/test_subscription_contract.py`
- [X] T049 [P] [US3] Add failing PostgreSQL races for same-user duplicate registration, cross-account active-endpoint ownership transfer after revoke, and revoke-versus-delivery creation in `backend/tests/integration/postgres/notifications/test_subscription_concurrency.py`
- [X] T050 [P] [US3] Add failing frontend config/browser/UI tests for absent/malformed/valid public VAPID key, disabled inbox-only state, unsupported APIs, permission denied, user-gesture-only consent, successful subscribe/upsert, truthful storage/API failure, owner marker restore/mismatch, repeated unsubscribe, and no automatic new-account opt-in in `frontend/tests/unit/notifications/{web-push-config.test.ts,browser-push.test.ts,push-opt-in-control.test.tsx}`
- [X] T051 [P] [US3] Extend AuthProvider tests for server logout before local unsubscribe/token clear, account-switch cleanup, inactive cleanup, and local failure not blocking logout in `frontend/tests/unit/identity/auth-provider.test.tsx`

### Implementation for User Story 3

- [X] T052 [US3] Add `PushSubscription` and `PushDelivery` models with all defaults/checks/partial uniques/indexes and the linear expand migration in `backend/notifications/models.py` and `backend/notifications/migrations/0002_push_delivery.py`; preserve `0001_notification` and one migration leaf
- [X] T053 [P] [US3] Implement authenticated encryption/key-ring and exact-origin/URL-safe-key validation adapters in `backend/notifications/adapters/security/{subscription_cipher.py,endpoint_policy.py}` with no raw-value diagnostics
- [X] T054 [P] [US3] Implement the `pywebpush` transport adapter with constant generic payload, VAPID, remaining TTL, collapse Topic, bounded timeout, and closed sanitized results in `backend/notifications/adapters/web_push.py`
- [X] T055 [US3] Implement atomic owner-bound subscription upsert/revoke, active endpoint conflict handling, permanent provider revoke primitive, and pending-delivery suppression in `backend/notifications/application/subscriptions.py` and `backend/notifications/adapters/persistence/repositories.py`
- [X] T056 [US3] Materialize one PushDelivery for each active subscription during Notification creation with unique-pair enforcement and immediate `not_before` outside quiet hours in `backend/notifications/application/occurrences.py`
- [X] T057 [US3] Implement a single-candidate claim/send/finalize path for immediately due valid deliveries with network outside transactions and inbox/source/read isolation in `backend/notifications/application/delivery.py`
- [X] T058 [US3] Implement strict subscription serializer, R-144 permission, thin POST/DELETE views/URLs, opaque response, disabled-push error, and stable operation IDs in `backend/notifications/adapters/api/{serializers.py,permissions.py,views.py,urls.py}`
- [X] T059 [US3] Inject identity-owned revoke calls into logout and active→inactive transactions regardless of refresh-revoke count in `backend/identity/application/{dependencies.py,authentication.py,user_admin.py,container.py}` and implement the adapter only in `backend/config/notification_adapters.py`
- [X] T060 [US3] Regenerate subscription contract/client and verify privacy/compatibility in `contracts/openapi.yaml`, `frontend/src/shared/api/schema.ts`, `scripts/check_openapi.py`, and `backend/tests/contract/test_openapi_safety.py`
- [X] T061 [US3] Implement typed public-VAPID-key validation/disabled state, native service-worker registration/subscription/unsubscribe, account marker isolation, and generated-client upsert/revoke in `frontend/src/features/notifications/adapters/{web-push-config.ts,browser-push.ts}` and `frontend/src/features/notifications/api/notification-api.ts`
- [X] T062 [US3] Implement truthful accessible opt-in/revoke states and AuthProvider lifecycle integration in `frontend/src/features/notifications/ui/PushOptInControl.tsx`, `frontend/src/features/identity/model/AuthProvider.tsx`, and the Notifications page
- [X] T063 [US3] Add the static generic-only push/service-worker click shell without target resolution in `frontend/public/notification-sw.js` and a privacy architecture guard in `frontend/tests/architecture/notification-privacy.test.ts`

**Gate 5**: US3 subscription, crypto, fake transport, API, PostgreSQL, frontend, privacy, and auth-lifecycle tests pass; in-app tests pass with push disabled/provider failure.

---

## Phase 6: User Story 4 — Quiet Hours, TTL, Dedupe, Retry, and Suppression (Priority: P2)

**Goal**: Deliver only due, current, nonduplicate push through leased PostgreSQL work while respecting exact quiet/TTL boundaries and every stale-state suppression rule.

**Independent Test**: Controlled clocks at 20:59/21:00/06:59/07:00 and exactly 24 hours plus competing workers/source mutations prove correct not-before, one claim, lease recovery, retry, expiry, and suppression with unchanged inbox/read/source state.

### Tests for User Story 4

- [X] T064 [P] [US4] Add failing pure policy tests for half-open quiet interval, next-07:00 across midnight, exact 24-hour expiry, remaining TTL, bounded retry/backoff, lease expiry, transition matrix, and stable collapse identity in `backend/tests/unit/notifications/test_delivery_policy.py`
- [X] T065 [P] [US4] Add failing delivery-service tests for account/subscription/recipient/object/state revalidation, completed/unassigned/checked-out/completer suppression, transient retry, permanent revoke, expired delivery, provider timeout, and no Task/Attendance/read mutation in `backend/tests/unit/notifications/test_delivery_service.py`
- [X] T066 [P] [US4] Add failing PostgreSQL competing-worker/expired-lease tests proving disjoint claims, conditional finalization, reclaim, unique delivery, and no transaction held during fake network call in `backend/tests/integration/postgres/notifications/test_delivery_concurrency.py`
- [X] T067 [P] [US4] Add failing PostgreSQL source races for completion/removal/Check Out/logout/deactivation against delivery claim in both commit orders, asserting sends only when claim revalidation linearizes first and all later claims suppress in `backend/tests/integration/postgres/notifications/test_delivery_suppression_races.py`
- [X] T068 [P] [US4] Add failing scheduler-manifest/readiness tests preserving reconciliation and requiring exactly one enabled staging/production binding for both minute notification jobs in `backend/tests/contract/test_deployment_checks.py` and `backend/tests/contract/test_deployment_runbook.py`

### Implementation for User Story 4

- [X] T069 [US4] Implement quiet-hour release, exact TTL, retry/backoff, lease, and delivery transition domain rules in `backend/notifications/domain/delivery.py`
- [X] T070 [US4] Set quiet-aware `not_before`, exact expiry, retry metadata, and stable collapse key on every PushDelivery in `backend/notifications/application/occurrences.py`
- [X] T071 [US4] Implement source-first revalidation, `skip_locked` lease claim, transaction-free provider call, conditional finalize, retry, permanent revoke, suppression, expiry, and lease reclaim in `backend/notifications/application/delivery.py` and `backend/notifications/adapters/persistence/repositories.py`
- [X] T072 [US4] Ensure assignment removal, both completion paths, Check Out, logout, active→inactive, and explicit revoke suppress eligible PENDING/LEASED rows inside their existing source transactions in `backend/config/notification_adapters.py` and the source use-case call sites
- [X] T073 [US4] Implement the thin idempotent `deliver_web_push` management command with bounded batch progress and safe exit/failure reporting in `backend/notifications/management/commands/deliver_web_push.py`
- [X] T074 [US4] Add both minute singleton commands while preserving the daily reconciliation contract in `deploy/scheduled-jobs.yaml` and generalize exact command/timezone/calendar/binding validation in `scripts/deployment_check.py` and `deploy/environments.yaml`
- [X] T075 [US4] Add egress/default-deny and VAPID/encryption rotation operational verification for configured push origins in `scripts/deployment_check.py` and `docs/TRIEN_KHAI.md`
- [X] T076 [US4] Run and record controlled boundary/suppression verification references in `specs/008-in-app-web-push/quickstart.md`, correcting only discovered documentation drift and leaving no wall-clock assertion in CI

**Gate 6**: US4 policy/service/PostgreSQL race/deployment tests pass, both commands are overlap-safe, and all US1–US3 gates remain green.

---

## Phase 7: User Story 5 — Authorization-Safe Deep Links (Priority: P2)

**Goal**: Resolve an opaque Notification reference to a minimal destination only after current owner, action, object-scope, account, and target-state checks.

**Independent Test**: A valid recipient resolves and navigates; after assignment/permission/account loss or under another account the same reference discloses nothing, changes no read state, and never fetches the target before resolver success.

### Tests for User Story 5

- [X] T077 [P] [US5] Add failing resolver unit tests for Task and Attendance success, removed assignment, role/capability loss, inactive account, stale/deleted target, foreign recipient, closed destination vocabulary, and no implicit read in `backend/tests/unit/notifications/test_target_resolver.py`
- [X] T078 [P] [US5] Add failing API/contract tests for owner-first lookup, independent target authorization/object scope, malformed/nonexistent/cross-account non-disclosure, minimal union response, action precedence, private/no-store, and zero side effects in `backend/tests/integration/api/notifications/test_target_api.py` and `backend/tests/contract/notifications/test_target_contract.py`
- [X] T079 [P] [US5] Add failing frontend tests for opaque open route, resolver-before-navigation, Task focus/Attendance destination, safe denial, no target fetch before resolve, no implicit read, and copied cross-account reference in `frontend/tests/unit/notifications/notification-open.test.tsx`

### Implementation for User Story 5

- [X] T080 [US5] Implement owner-scoped target resolution and injected Task/Attendance current authorization/object-scope calls returning only closed destination/minimal target identity in `backend/notifications/application/targets.py`
- [X] T081 [US5] Implement thin R-144 target view/URL, UUID handling, canonical non-disclosing errors, response union serializer, private/no-store, and stable operation ID in `backend/notifications/adapters/api/{serializers.py,views.py,urls.py}`
- [X] T082 [US5] Regenerate resolver contract/client and compatibility checks in `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`
- [X] T083 [US5] Implement typed resolver wrapper and safe `/notifications/open/[reference]` route that redirects only after success in `frontend/src/features/notifications/api/notification-api.ts` and `frontend/src/app/notifications/open/[reference]/page.tsx`
- [X] T084 [US5] Add already-authorized Task focus handling without widening Task list scope and finalize service-worker same-origin click behavior in `frontend/src/features/tasks/model/use-task-management.ts`, `frontend/src/features/tasks/ui/TaskManagementPanel.tsx`, and `frontend/public/notification-sw.js`

**Gate 7**: US5 unit/API/contract/frontend tests pass for success and every deny/stale/cross-account path; notification read state remains explicit-only.

---

## Phase 8: Polish and Cross-Cutting Verification

**Purpose**: Close privacy, contract, migration, CI, accessibility, and complete-feature gates without expanding behavior.

- [X] T085 [P] Extend backend and frontend static privacy/redaction scans across notification sources, service worker, API schema/examples, logs, audit/outbox, telemetry, and fixtures in `backend/tests/contract/notifications/test_privacy.py`, `backend/tests/contract/test_sanitized_outputs.py`, `frontend/tests/architecture/notification-privacy.test.ts`, and `scripts/check_openapi.py`
- [X] T086 [P] Add end-to-end inbox/read/opt-in/revoke/safe-link success and deny flows with mocked browser Push APIs and no real provider in `frontend/tests/e2e/notifications.spec.ts`
- [X] T087 [P] Add responsive and accessibility coverage for inbox, unread badge, opt-in states, error/retry, and keyboard/screen-reader operation in `frontend/tests/e2e/notifications-responsive.spec.ts` and `frontend/tests/e2e/notifications-accessibility.spec.ts`
- [X] T088 [P] Add exact-scope regression tests proving no email/SMS/native/account-lock/reset notification, no sixth event, no Celery/Redis/WebSocket/SSE/timer, and no notification import leakage in `backend/tests/architecture/test_notification_scope.py` and `frontend/tests/architecture/notification-scope.test.ts`
- [X] T089 Verify deterministic OpenAPI generation twice, backend/OpenAPI/client drift, additive compatibility, operation-ID uniqueness, snake_case, private/no-store, and no sensitive examples with `scripts/generate_openapi.py`, `scripts/check_openapi.py`, `scripts/check_contract_drift.py`, the compatibility command, and `npm --prefix frontend run api:check`
- [X] T090 Verify all migration leaves/defaults/expand-only operations and run Notification plus affected Task/Attendance/Identity PostgreSQL constraint/atomicity/concurrency suites with `scripts/migration_check.py` and `backend/tests/integration/postgres/`
- [X] T091 Run backend Ruff format/check, strict mypy, maintainability, unit, architecture, contract, API integration, complete PostgreSQL marker suite, and `manage.py makemigrations --check --dry-run`; fix only Feature 008 regressions in their owning files
- [X] T092 Run frontend Prettier check, ESLint, TypeScript, Vitest, generated API check, production build, and notification Playwright suites from `frontend/package.json`; fix only Feature 008 regressions in their owning files
- [X] T093 Run deployment isolation/scheduler/egress/readiness and secret scans against `.env.example`, `deploy/`, docs, schema, generated client, fixtures, and git diff; ensure production has no unresolved Feature 008 secret identity/binding
- [X] T094 Execute every automated scenario in `specs/008-in-app-web-push/quickstart.md` using controlled clocks/fake transport, mark verified outcomes without claiming manual/provider evidence that was not executed, and resolve every observed discrepancy
- [X] T095 Run the complete repository gate `scripts/check_all.sh` or, when Bash remains unavailable, every command it and both CI workflows enumerate; record the exact fallback and require all executed gates green
- [X] T096 Perform final traceability review across Constitution, CHOT, QUY_TAC, R-97/R-144–R-147, `spec.md`, `plan.md`, `tasks.md`, generated contracts, migrations, implementation, and tests; remove no requirement and leave no unresolved TODO/CRITICAL finding

---

## Dependencies and Execution Order

### Phase dependencies

- **Phase 1 Setup**: starts immediately; T006 depends on T005, T009 depends on T008.
- **Phase 2 Foundation**: depends on Gate 1; T013 depends on T012, T016 depends on T013/T014, T017 depends on T014–T016, and blocks all stories.
- **US1 / Phase 3**: depends on Gate 2. Tests T019–T023 can be authored in parallel; implementation follows migration/ports → source integrations/fact adapters → services/composition → API/contract → frontend.
- **US2 / Phase 4**: depends on US1 Notification/list foundation but not Web Push.
- **US3 / Phase 5**: depends on US1 Notification occurrence creation; can overlap US2 after Gate 3 because it owns different behavior/files except shared API/repository integration, which must be serialized.
- **US4 / Phase 6**: depends on US3 PushSubscription/PushDelivery/transport.
- **US5 / Phase 7**: depends on US1 inbox and source target ports; can overlap US3/US4 after Gate 3 except generated-contract/shared frontend API edits must be serialized.
- **Phase 8**: depends on all selected stories; for this request all five are required.

### User-story dependency graph

```text
Setup → Foundation → US1 (authoritative inbox)
                         ├──→ US2 (read/unread)
                         ├──→ US3 (opt-in/revoke/basic push) → US4 (quiet/TTL/retry/suppression)
                         └──→ US5 (safe target resolution)
US2 + US4 + US5 → Polish/full verification
```

### Parallel examples

- **US1**: T019 API contract, T020 Task unit, T021 scheduler unit, T022 PostgreSQL races, and T023 frontend tests touch independent test files; after ports exist, T028 Task, T029 Attendance, and T030 Identity fact adapters are independent.
- **US2**: T039 API, T040 PostgreSQL race, and T041 frontend tests are independent before implementation.
- **US3**: T046 security/transport, T047 models, T048 API, T049 PostgreSQL, T050 browser UI, and T051 AuthProvider tests are independent; T053 encryption and T054 transport implementation are independent after T052.
- **US4**: T064 policy, T065 service, T066 worker concurrency, T067 source races, and T068 deployment tests are independent test-first outcomes.
- **US5**: T077 backend unit, T078 API/contract, and T079 frontend route tests are independent before resolver implementation.

## Implementation Strategy

### MVP first

1. Complete Setup and Foundational gates.
2. Complete US1 only and validate with Web Push disabled.
3. This proves the authoritative complete inbox and exactly five event types before optional transport work.

### Full requested delivery

1. Add US2 read/unread.
2. Add US3 explicit subscription lifecycle and generic fake-transport push.
3. Add US4 durable quiet-hours/TTL/retry/suppression and deployment jobs.
4. Add US5 authorization-safe target resolution.
5. Complete every Phase 8 gate, then run analyze/converge again and append any real missing work rather than weakening tests.

## Notes

## Phase 9: Convergence

- [X] T097 Make disabled in-app-only configuration ignore absent or placeholder Web Push secrets while enabled mode remains fail-closed, with focused tests, per FR-013 and plan: configuration decision (partial)
- [X] T098 Validate enabled VAPID public/private consistency and implement a read-old/write-new subscription encryption key ring with safe diagnostics and rotation tests per Constitution IX and plan: configuration decision (partial)
- [X] T099 Add PostgreSQL same-endpoint registration, competing delivery worker, lease reclaim, revoke/logout/deactivate, source-suppression, and first-read concurrency tests; fix any exposed race without weakening constraints per FR-016, FR-025–FR-028, and SC-004–SC-005 (partial)
- [X] T100 Add application tests covering all scheduled dispatch boundaries and delivery revalidation/failure transitions, including rollback and zero source/read mutation per FR-003–FR-006 and FR-021–FR-028 (missing)
- [X] T101 Extend static OpenAPI/log/audit/outbox/telemetry privacy checks to reject exposed subscription material and detailed push payload fields or examples per FR-015, FR-019–FR-020, and SC-006 (partial)
- [X] T102 Add mocked-browser notification Playwright success/deny, responsive, keyboard, and accessibility journeys without a real push provider per US3/AC1–AC3, US5/AC1–AC3, and plan: frontend verification (missing)
- [X] T103 Record controlled automated quickstart outcomes and exact platform-specific fallback gates without claiming manual provider/browser evidence per SC-001–SC-010 and plan: verification strategy (partial)

- `[P]` never authorizes simultaneous edits to the same generated artifact or shared composition file.
- Tests precede implementation and must fail for the prohibited behavior, not for fixture/setup mistakes.
- Real PostgreSQL is mandatory for every constraint, lease, rollback, and race guarantee.
- Provider calls are always faked in CI and always outside database transactions.
- Generated OpenAPI/client files are regenerated, never hand-edited.
- No implementation may begin while a CRITICAL consistency finding remains.
