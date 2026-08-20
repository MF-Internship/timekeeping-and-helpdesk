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
