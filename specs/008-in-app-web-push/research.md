# Research: In-App Notifications and Web Push

## R-01 — Authoritative source and integration mode

**Decision**: Persist Notification and PushDelivery through source-module-owned output ports inside the Task transaction; scheduled occurrences use notification-owned transactions and source fact ports. Do not depend on an outbox relay.

**Rationale**: The repository persists `OutboxEvent` but has no relay/consumer/lease implementation. Direct injected ports preserve atomic inbox creation and inward boundaries without expanding scope to the entire outbox platform.

**Alternatives considered**: `transaction.on_commit` only (not durable); Task outbox consumer (requires unbuilt relay); notifications importing Task models (architecture violation).

## R-02 — Canonical self-service authorization

**Decision**: Use accepted R-144 actions: `notification.view.self`, `notification.update.self`, and `push_subscription.manage.self`, directly granted to all three roles with no implication. Target resolution additionally invokes owning target authorization/object scope.

**Rationale**: CHOT declares the endpoints self-owned while the Constitution requires a centralized action gate. The source docs were corrected before planning.

**Alternatives considered**: authentication-only endpoints (violates Constitution III); role checks in views (forbidden); reusing unrelated Task permissions (wrong resource/action).

## R-03 — Assignment occurrence identity

**Decision**: Add server-owned positive `Task.assignment_version`, initialized with database default 1 and incremented once under Task lock when the assignee set truly changes.

**Rationale**: Existing `TaskAssignee` rows are deleted on removal, so their timestamps cannot distinguish remove/re-add. R-97 explicitly requires assignment-version dedupe.

**Alternatives considered**: TaskAssignee timestamp (history disappears); TaskUpdate count (not assignment-specific); random keys (not deterministic under retry).

## R-04 — Durable delivery scheduling

**Decision**: Add `PushDelivery` per Notification × active PushSubscription with unique pair, not-before/expiry, state, attempt, lease, collapse, and closed error metadata; never persist push payload or endpoint.

**Rationale**: Quiet-hour release, TTL, retry, crash recovery, and suppression need durable concurrency-visible state. PostgreSQL already exists and avoids a new broker.

**Alternatives considered**: scan Notifications without attempt state (repeated spam or missed sends); provider call after commit callback (crash gap); Celery/Redis (unapproved infrastructure).

## R-05 — Scheduler shape

**Decision**: Use two singleton external-scheduler commands every minute: occurrence dispatch and push delivery. Each is idempotent and overlap-safe; existing reconciliation remains unchanged.

**Rationale**: Dynamic shift-end reminder and fixed 17:00/08:00/07:00 policies need bounded cadence. The repo already owns deployment scheduler manifests and forbids timers in web processes.

**Alternatives considered**: three/four schedule-specific jobs (more bindings and drift); in-process loop (unsafe under replicas); Celery beat (new infrastructure).

## R-06 — Look-back-safe due evaluation

**Decision**: Once the local due threshold has passed, scans continue considering that date/session and rely on the unique occurrence key, rather than requiring the command to run in one exact minute.

**Rationale**: Scheduler delay must not lose the authoritative in-app occurrence. Repeated scans are harmless under PostgreSQL uniqueness and source-state revalidation.

**Alternatives considered**: equality to 17:00/08:00 (misses delayed runs); broad blind creation (stale notifications).

## R-07 — Push protocol dependency

**Decision**: Pin `pywebpush==2.3.0`, the current stable PyPI release on 2026-08-21, and direct-pin `cryptography==50.0.0` because application code owns encryption at rest. Native browser Push APIs need no npm dependency.

**Rationale**: Web Push requires payload encryption and VAPID signing. The maintained library exposes TTL/headers/timeouts; hand-written protocol cryptography is disproportionate and unsafe. Sources: [PyPI pywebpush](https://pypi.org/project/pywebpush/), [pywebpush source](https://github.com/web-push-libs/pywebpush), [PyPI cryptography](https://pypi.org/project/cryptography/).

**Alternatives considered**: hand-roll RFC crypto (rejected); use transitive `requests`/crypto without direct ownership (unstable); browser-only push (server cannot publish).

## R-08 — Subscription encryption and rotation

**Decision**: Hash endpoint with SHA-256 for identity and encrypt the complete endpoint/key JSON using a separately configured authenticated-encryption key ring, active key first with old keys accepted for decryption.

**Rationale**: CHOT treats endpoint plaintext as an operational secret. A key ring supports rotation without exposing or bulk rewriting during the same release.

**Alternatives considered**: plaintext JSON (forbidden); Django `SECRET_KEY` reuse (couples unrelated secrets); irreversible encryption (delivery impossible).

## R-09 — Endpoint origin and SSRF control

**Decision**: Accept only syntactically valid HTTPS endpoints whose normalized origin exactly matches a typed deployment allowlist; reject userinfo, fragments, non-default unsafe forms, and any unlisted origin before storage or network use.

**Rationale**: Browser-supplied endpoints otherwise become arbitrary server-side POST targets. Exact configured egress preserves default-deny deployment policy and supports provider changes through reviewed configuration.

**Alternatives considered**: any HTTPS URL (SSRF/egress violation); hardcoded vendor hosts in business code (drift); DNS-only public-IP checks (rebinding and provider CDN complexity).

## R-10 — Generic payload and service worker

**Decision**: Transport a constant generic title/body, closed event hint, and opaque Notification UUID only. A static service worker displays it and permits clicks only to a same-origin `/notifications/open/<uuid>` path.

**Rationale**: Lock screens must not expose business/person/location evidence. MDN confirms Push subscription uses a VAPID application server key and service-worker notifications/click handling require secure context: [PushManager.subscribe](https://developer.mozilla.org/en-US/docs/Web/API/PushManager/subscribe), [showNotification](https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerRegistration/showNotification), [notificationclick](https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerGlobalScope/notificationclick_event).

**Alternatives considered**: target title/name in push (forbidden); raw target URL/ID as authorization (unsafe); main-thread notifications (not background-capable).

## R-11 — Deep-link resolution

**Decision**: Add an owner-scoped `GET /api/v1/notifications/{public_id}/target` resolver. It calls Task/Attendance authorization ports and returns a closed destination plus minimal authorized target identity; it never marks read.

**Rationale**: Push and inbox need navigation, but existing routes alone cannot safely revalidate a stale opaque reference. R-144 accepts the additive resolver.

**Alternatives considered**: put target URL in push (leaks identity and bypass risk); frontend infer from event (no server object-scope check); treat Notification ownership as target authorization (incorrect).

## R-12 — Audit/outbox evidence

**Decision**: Do not add AuditLog/OutboxEvent for list/read/subscription/delivery. Preserve existing Task/Attendance audit behavior; Notification, subscription, and delivery rows are canonical feature evidence.

**Rationale**: CHOT has no approved AuditAction for these self-service operations, and copying subscription/provider data increases leak risk. Idempotent read/revoke should remain side-effect-minimal.

**Alternatives considered**: invent audit events (unapproved vocabulary); push provider receipts as truth (best-effort only).

## R-13 — Frontend state and account isolation

**Decision**: Use feature-local hooks/state, refresh on load/manual/visibility, reset on account ID/state changes, and keep only `{account_id, opaque_subscription_id}` locally. Server revocation precedes local unsubscribe/token clearing.

**Rationale**: The repo has no Redux/query dependency and AuthProvider is the lifecycle chokepoint. This prevents one account from inheriting another's inbox or opt-in.

**Alternatives considered**: persistent inbox cache (cross-account/stale risk); automatic opt-in after login (violates consent); WebSocket/SSE (out of scope).

## R-14 — Delivery failure policy

**Decision**: Provider calls have bounded timeout outside transactions. Permanent invalid-subscription responses revoke; transient failures retry with bounded exponential delay until 24-hour expiry; only closed non-sensitive failure codes persist.

**Rationale**: Push is best effort but crashes/transient outages should not lose a still-valid delivery immediately. TTL is the absolute retry boundary and cannot affect inbox/source state.

**Alternatives considered**: infinite retry (violates TTL); no retry (unnecessarily brittle); raw provider response persistence/logging (secret leak).

## R-15 — Multi-assignee completion eligibility

**Decision**: Emit event 5 only when `completed_by` is a current assignee of a Task with at least two current assignees. All completion paths still suppress stale reminder deliveries.

**Rationale**: The supported event is explicitly “completed by another assignee”; Manager override/non-assignee completion must not be relabeled as that event. Accepted as R-147.

**Alternatives considered**: every completion of a multi-assignee Task (changes event meaning); override-specific sixth event (forbidden).

## R-16 — JobRun scope

**Decision**: Do not add notification names to the existing `JobRun` model or job-health API in Feature 008. Scheduler readiness plus PushDelivery state is the executable operational evidence.

**Rationale**: Current JobRun constraints/read model are specialized to missing-check-out (`changed_count = anomaly_count`) and changing them would expand job-health business behavior beyond this spec.

**Alternatives considered**: reuse `MISSING_CHECK_OUT` rows (incorrect); expand operations health in this feature (scope creep); no scheduler validation (deployment drift).
