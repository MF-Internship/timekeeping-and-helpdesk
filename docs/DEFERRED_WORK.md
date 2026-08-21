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

## Feature 015 Manual Verification

## UI-015-01

- **Feature**: Responsive application shell and primary workflows
- **Reason**: Physical Android browser rendering and device safe-area behavior cannot be proven by desktop automation.
- **Environment**: Android phone, current Chrome, authenticated HELPDESK and MANAGER accounts
- **Steps**: Open Home, Tasks, Attendance, Notifications, and More navigation in portrait and landscape; exercise menus and dialogs.
- **Expected**: No horizontal overflow or overlap; bottom navigation remains reachable and does not cover content.
- **Status**: PENDING

## UI-015-02

- **Feature**: Responsive application shell and overlays
- **Reason**: iOS Safari viewport and safe-area behavior require a physical device.
- **Environment**: Supported iPhone, current Safari, authenticated account
- **Steps**: Open every permitted route; scroll forms and charts; open account, More, and task detail overlays.
- **Expected**: Controls remain usable, overlays fit the viewport, and safe-area insets are respected.
- **Status**: PENDING

## UI-015-03

- **Feature**: Light, Dark, and System themes
- **Reason**: Hardware and browser color rendering cannot be fully assessed in automated screenshots.
- **Environment**: Android and iPhone with light/dark system appearance
- **Steps**: Select each theme on representative routes and restart the browser.
- **Expected**: Preference persists locally, System follows the device, and text/status/chart contrast remains readable.
- **Status**: PENDING

## UI-015-04

- **Feature**: Screen-reader accessibility
- **Reason**: Automated accessibility checks do not validate announcement quality or practical navigation order.
- **Environment**: NVDA with Firefox or VoiceOver with Safari
- **Steps**: Navigate Login, Home, Attendance, Notifications, Reports, Users, and Account using headings, landmarks, forms, menus, and dialogs.
- **Expected**: Labels, errors, status changes, chart summaries, and overlay focus are announced coherently.
- **Status**: PENDING

## UI-015-05

- **Feature**: Attendance location guidance
- **Reason**: Real GPS permissions and map touch/zoom require device sensors and touch input.
- **Environment**: GPS-capable Android and iPhone on a permitted test location
- **Steps**: Grant/deny location permission, refresh position, pan/zoom guidance, and attempt authorized attendance actions.
- **Expected**: Permission guidance is clear, touch gestures work, and canonical geofence decisions remain unchanged.
- **Status**: PENDING

## UI-015-06

- **Feature**: Long production content
- **Reason**: Production names, addresses, task evidence, and notification titles may exceed fixture lengths.
- **Environment**: Staging data containing maximum-length permitted values
- **Steps**: Inspect lists, tables, menus, charts, dialogs, and forms at 320 px and desktop widths.
- **Expected**: Text wraps or truncates intentionally without covering controls or causing document overflow.
- **Status**: PENDING

## UI-015-07

- **Feature**: Browser-specific safe areas and responsive charts
- **Reason**: Engine-specific viewport behavior needs validation beyond Chromium.
- **Environment**: Current Safari and Firefox on supported desktop/mobile devices
- **Steps**: Review navigation, sticky content, report charts, dropdowns, and sheets at representative widths.
- **Expected**: Layout remains stable and all interactive content stays visible and keyboard reachable.
- **Status**: PENDING
