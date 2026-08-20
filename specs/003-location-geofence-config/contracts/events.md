# Event and Audit Contract

Feature 003 reuses `audit.AuditLog`, `audit.OutboxEvent`, the shared payload sanitizer, and
caller-owned transaction semantics. It adds no second append system.

## Closed vocabulary

| Business mutation | Audit action / event type | Aggregate |
|---|---|---|
| Initial canonical Location insert by seed | `locations.location.seeded` | `Location:{id}` |
| Seed restores changed canonical fields | `locations.location.reconciled` | `Location:{id}` |
| Manager Location PATCH | `locations.location.updated` | `Location:{id}` |
| Controlled Config initialization | `locations.config.initialized` | `Config:1` |
| Manager Config PATCH | `locations.config.updated` | `Config:1` |
| Holiday create | `locations.holiday.created` | `Holiday:{id}` |
| Holiday delete | `locations.holiday.deleted` | `Holiday:{id}` |

Reads, geometry evaluation, warnings, denied/invalid/stale requests, missing targets,
duplicate Holiday attempts, unchanged seed rows, and rollbacks emit no success event/audit.
Current-version same-value Location PATCH and same-value Config PATCH are also successful
no-ops: they return current state/warnings but emit no audit/event and advance no business or
aggregate version. Location stale-version comparison occurs before no-op detection.

## Location payload policy

Allowed minimal values include Location id/code/kind, active/radius/version, changed-field
names, warning codes, and sanitized optional reason. Address/name may be present in AuditLog
before/after only when needed to explain the change; they are omitted from outbox.

Forbidden in AuditLog and OutboxEvent:

- latitude/longitude values or coordinate pairs;
- distance calculations or overlap center data;
- tokens, credentials, cookies, passwords, URLs, object keys, image data, UI prose.

When coordinates changed, evidence records `changed_fields: ["latitude", "longitude"]`
without either value.

## Config payload policy

Audit before/after may include non-secret Config values and changed fields. Outbox remains
minimal: Config id, changed fields, warning codes, and event schema version. It never embeds
all 76 Location values.

## Holiday payload policy

Audit before/after may include id/date/name. Outbox contains id/date and action; it omits UI
messages. Delete uses the existing row id as aggregate identity even if the same date is
later recreated.

## Atomicity and aggregate versions

- The business row lock is held from mutation validation through audit and outbox append.
- Existing aggregates allocate `MAX(aggregate_version)+1` while their Location/Config/
  Holiday row is locked.
- New rows are inserted before aggregate version 1.
- State/evidence rollback together; failed append leaves no business change.
- An unchanged seed rerun does not advance Location or aggregate version.
- Seed rows that are reconciled each advance Location version once and append one aggregate
  audit/outbox pair.

Correlation ids remain adapter-owned. Commands legitimately carry empty request/correlation
strings but still require an attributable active Manager actor.
