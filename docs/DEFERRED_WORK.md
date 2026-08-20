# Deferred Work

## DW-F009-01

Feature: 009 Notifications
Reason: Real Web Push permission and delivery require HTTPS staging, a supported browser/device, user permission, and provider configuration that cannot be proven by CI fake transport tests.
Prerequisites: HTTPS staging deployment, configured Web Push secrets, supported browser with notifications enabled, test MANAGER and HELPDESK accounts.
Steps:
1. Login as HELPDESK in the supported browser.
2. Enable Web Push from the Notifications screen and grant browser permission.
3. Login as MANAGER in another session and assign a Task to that HELPDESK user.
4. Confirm the in-app Notification appears for the HELPDESK user.
5. Confirm the browser/device push arrives.
6. Inspect the lock-screen/browser notification preview.
Expected:
- In-app notification is present and complete.
- Push payload is generic.
- No employee, Task detail, GPS coordinate, photo, map URL, signed URL, token, or private evidence data appears in the push preview.
Related requirement/R-xx: R-97.
Status: PENDING

## DW-F014-01

Feature: 014 Production Readiness
Reason: Real staging/production infrastructure values are not available in the repository.
Prerequisites: Approved staging and production projects, database identities, migration/admin DB identities, buckets, Redis/cache identities, signing keys, origin credentials, and scheduler identities.
Steps:
1. Replace required `UNRESOLVED` identity values in `deploy/environments.yaml` with non-secret real identities.
2. Run `scripts/deployment_check.py isolation`.
3. Run `scripts/deployment_check.py production-ready`.
Expected:
- Isolation passes;
- production-ready passes only when all required production values are resolved and distinct.
Status: PENDING

## DW-F014-02

Feature: 014 Backup and Recovery
Reason: Real backup execution and restore drill require provider infrastructure and a separate restore project/database.
Prerequisites: Backup policy, restore project, `RECOVERY_DATABASE_URL`, operator access, runbook owner.
Steps:
1. Execute a provider backup or PITR restore into the separate recovery database.
2. Run `manage.py verify_restore` with `DATABASE_URL`, `DATABASE_ADMIN_URL`, and `RECOVERY_DATABASE_URL`.
3. Record measured RPO/RTO, categories, restore identity, timestamp, and remediation owner in `deploy/recovery-evidence.yaml`.
4. Run `scripts/deployment_check.py recovery-ready`.
Expected:
- Restore verification uses read-only probes and passes;
- recovery-ready passes only with current evidence within RPO/RTO/retention targets.
Status: PENDING

## DW-F014-03

Feature: 014 Capacity Readiness
Reason: Real capacity evidence requires at least 50 real authorized accounts and a staging/production-like target.
Prerequisites: Temporary identities file kept outside Git, reachable `/api/v1/` capacity probe, concurrency allowance, remediation owner.
Steps:
1. Generate at least 50 real short-lived identities.
2. Run `scripts/capacity_check.py measure --concurrency 20 --target-url <approved /api/v1/...>`.
3. Store sanitized output outside secrets and summarize evidence in `deploy/recovery-evidence.yaml`.
Expected:
- p95 is within target or readiness remains failed with remediation owner;
- identities/tokens are not printed or committed.
Status: PENDING

## DW-F013-01

Feature: 013 Operational Telemetry, Health and Retention
Reason: Real external alert/monitoring delivery requires approved observability infrastructure.
Prerequisites: Staging deployment, configured monitoring sink, alert recipient/channel, operational runbook.
Steps:
1. Configure the approved external monitoring/alert sink.
2. Trigger a controlled outbox dead-letter or stale heartbeat in staging.
3. Confirm the external alert arrives once with sanitized fields.
4. Confirm no URL, token, credential, GPS coordinate, raw request path, or payload data is present.
Expected:
- Application behavior is unaffected if the sink fails;
- external alert content is sanitized and actionable.
Status: PENDING

## DW-F012-01

Feature: 012 Reliable Outbox Relay
Reason: Real external transport delivery requires approved provider/broker infrastructure and credentials.
Prerequisites: Staging deployment, approved transport adapter configuration, provider credentials, reachable consumer endpoint.
Steps:
1. Configure `OUTBOX_RELAY_TRANSPORT` to the approved non-local provider.
2. Append an approved `OutboxEvent` in staging.
3. Run `relay_outbox` with a unique worker id.
4. Confirm the provider receives exactly one delivery attempt for the event id.
5. Confirm duplicate delivery is idempotently suppressed by the consumer.
Expected:
- `OutboxEvent` reaches `PUBLISHED` only after provider success;
- retry/dead-letter behavior matches R-105 on controlled provider failures;
- no payload, URL, token, credential, or GPS-sensitive value appears in logs/provider previews.
Status: PENDING
