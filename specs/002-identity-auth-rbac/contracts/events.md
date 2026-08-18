# Audit and Outbox Contract: Identity

## Port contract

Identity application services may depend only on `audit.ports.recording`.

### append_audit_entry

Accepts actor id, action, target type/id, before object, and after object.

- Validates before/after with `core.event_payload` before model construction.
- Inserts one AuditLog row in the caller's active transaction.
- Does not call `transaction.atomic()`, `transaction.on_commit()`, commit, retry, log payload values, or swallow failure.

### append_outbox_event

Accepts event type, schema version, aggregate type/id, and minimal payload.

- Validates payload before model construction.
- Reads ambient request_id/correlation_id itself; empty values outside HTTP are valid.
- Allocates the next aggregate version while the caller holds the aggregate User lock.
- Inserts one PENDING OutboxEvent in the caller's active transaction.
- Does not publish, open a transaction, schedule on-commit work, or swallow failure.

Caller rollback after both appends leaves no business, blacklist, audit, or outbox change.

## Audit action vocabulary

| Action | Actor/target | before | after |
|---|---|---|---|
| `identity.user.created` | Manager → new User | `{}` | user_id, username, full_name, phone, email, role, is_active, must_change_password |
| `identity.user.profile_updated` | Actor → User | changed profile values before | changed profile values after |
| `identity.user.role_changed` | Manager → User | role | role |
| `identity.user.status_changed` | Manager → User | is_active | is_active |
| `identity.user.password_reset` | Manager → User | must_change_password | must_change_password=true |
| `identity.user.password_changed` | User → self | must_change_password | must_change_password=false |
| `identity.sessions.revoked` | Actor → affected User | active_refresh_sessions count | active_refresh_sessions=0 plus reason/revoked count |

Rules:

- Password/reset records never contain plaintext, hash, validator input, or generated_password.
- Session records never contain JWT/JTI, cookie, OutstandingToken id, BlacklistedToken id, or credential fragment.
- Logout produces sessions-revoked evidence with reason LOGOUT. Reset/change/deactivation produce sessions-revoked evidence in the same transaction as their user-operation evidence.
- Login and routine refresh rotation do not produce audit rows; last_login/outstanding/blacklist state is sufficient and avoids high-volume audit noise not required by CHOT.
- No AuditLog row has request/correlation columns.

## Outbox event vocabulary (schema_version 1)

### `identity.user.created`

Payload:

```json
{
  "user_id": 42,
  "role": "HELPDESK",
  "is_active": true,
  "must_change_password": true
}
```

No username/contact/generated password is needed by an unspecified future consumer.

### `identity.user.profile_updated`

Payload:

```json
{
  "user_id": 42,
  "changed_fields": ["full_name", "phone"]
}
```

Contact/display values remain in authorized AuditLog evidence, not the event.

### `identity.user.role_changed`

Payload: user_id, previous_role, role.

### `identity.user.status_changed`

Payload: user_id, is_active.

### `identity.user.password_reset`

Payload: user_id, must_change_password=true. No password field/value.

### `identity.user.password_changed`

Payload: user_id, must_change_password=false. No password field/value.

### `identity.sessions.revoked`

Payload:

| Field | Rule |
|---|---|
| `user_id` | Affected User. |
| `reason` | `LOGOUT`, `PASSWORD_RESET`, `PASSWORD_CHANGE`, or `ACCOUNT_DEACTIVATED`. |
| `revoked_refresh_session_count` | Nonnegative count; no token identity. |

The key `must_change_password` and session-count keys are permitted because the shared filter matches forbidden keys exactly, not substrings. A failed logout caused by a missing, invalid, mismatched, or already-revoked refresh cookie appends neither audit nor outbox success evidence.

## Aggregate ordering

- aggregate_type is `User` and aggregate_id is the decimal User id as string.
- Create event is aggregate_version 1.
- Later identity events increment by one while the User row is locked.
- When one use case emits a user event and a sessions-revoked event, they receive consecutive versions in application order.
- There is no ordering promise between different Users.
- Unique `(aggregate_type, aggregate_id, aggregate_version)` is the database backstop.

## Forbidden payload matrix

Both AuditLog before/after and OutboxEvent payload reject:

- exact forbidden keys for password, token, authorization, cookie, image/object/location secret data;
- any string containing `://`;
- nested forbidden keys in objects or lists;
- secret values in diagnostic exceptions.

Rejection reports only the structural path and aborts the entire caller transaction. Tests also prove allowed exact keys such as must_change_password and active_refresh_sessions remain valid.

## Delivery boundary

Feature 002 ends when a valid event is committed PENDING. It does not implement:

- relay claim/lease/backoff;
- broker or transport;
- publish-state transitions;
- consumer idempotency records;
- dead-letter alerts or replay.

Those are governed by CHOT §9.5/R-105 and require their own implementation scope. No identity outcome depends on delivery.
