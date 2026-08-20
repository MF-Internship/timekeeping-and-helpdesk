# Data Model: Operational Telemetry, Health and Retention

## JobHeartbeat

- `job_name`
- `started_at`
- `last_success_at`
- `outcome`
- `updated_at`

Constraints:

- unique `job_name`
- `outcome` in `ok`, `failed`, `running`

## Retention categories

- `ProcessedEvent`: 30 days by `processed_at`
- `OutboxEvent(PUBLISHED)`: 30 days by `published_at`
- `OutboxEvent(DEAD_LETTER)`: 90 days by `created_at`

`PENDING` outbox and `AuditLog` are excluded.
