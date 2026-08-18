# Data Model: Identity, Authentication and Canonical RBAC

## Ownership and relationship overview

```text
identity.User 1 ── * token_blacklist.OutstandingToken 1 ── 0..1 BlacklistedToken
      │
      ├── * audit.AuditLog (actor)
      └── * audit.OutboxEvent (logical aggregate_type/id, no FK)
```

- `identity` owns User and authentication/RBAC behavior.
- SimpleJWT's blacklist app owns OutstandingToken and BlacklistedToken; identity accesses them only through its session adapter.
- `audit` owns AuditLog and OutboxEvent. Outbox uses logical aggregate identity to remain generic across future modules.
- There is no delete-user API. Historical records retain user identity; database foreign keys use protective deletion behavior where applicable.

## Domain value models

### Role

Closed values: `LEADER`, `MANAGER`, `HELPDESK`.

- Stored as a User field and converted to the pure domain value at repository boundaries.
- Only `LEADER` and `HELPDESK` are in `ASSIGNABLE_ROLES` for API create/role change.
- `MANAGER` is syntactically valid but authorization-protected; it is provisioned only outside public API scope.

### PermissionAction

Closed action strings are copied exactly from spec FR-029. Direct grants are data in one immutable map; no Django Group/Permission, `is_staff`, or superuser bypass participates in API decisions.

`PERMISSION_IMPLIES` contains exactly:

| Direct action | Implied requested action |
|---|---|
| `task.view.all` | `task.view.self` |
| `task.update.any` | `task.update.self` |
| `attendance.view.all` | `attendance.view.self` |
| `report.view.all` | `report.view.self` |
| `photo.view.all` | `photo.view.self` |

### PermissionDecision

Pure result used by backend policy and future object-scope owners.

| Field | Rule |
|---|---|
| `requested_action` | Canonical PermissionAction required by the operation. |
| `allowed` | True only for a direct grant or one of the five implications. |
| `granted_by` | Direct action that opened the gate; null for deny. A direct self grant remains self; an implied self request records its all/any source. |

Frontend capabilities contain the effective action strings only; grant provenance remains server-side.

### AccountSnapshot

Framework-free representation passed into policy/application logic.

| Field | Rule |
|---|---|
| `id` | Positive user identifier. |
| `username` | Immutable display/login identifier. |
| `full_name` | Trimmed, nonempty. |
| `phone` | Optional; not unique. |
| `email` | Optional; not unique. |
| `role` | Role value. |
| `is_active` | Current authoritative account gate. |
| `must_change_password` | Current authoritative forced-change gate. |
| `last_login` | Optional server time. |
| `created_at` | Server time. |

It never contains a password hash, generated password, JWT, cookie, token ID, or blacklist row.

## Persistent entities

### identity.User

Custom authentication user backed by PostgreSQL.

| Field | Type / nullability | Default / validation | Index / constraint |
|---|---|---|---|
| `id` | Big integer PK | Server generated | Primary key |
| `username` | varchar(150), NOT NULL | Trimmed at boundary; nonempty | UNIQUE; database nonblank check; immutable-update trigger |
| `password` | password-hash varchar, NOT NULL | Written only through password hasher; never serialized/audited/evented | No plaintext; no client direct field |
| `full_name` | varchar(255), NOT NULL | Trimmed; nonempty | Database `btrim(full_name) <> ''` check |
| `phone` | varchar(32), NULL | Optional; blank input normalized to null | Not unique; no secondary index |
| `email` | varchar(254), NULL | Optional; syntactically validated when present; blank input normalized to null | Not unique; no secondary index |
| `role` | varchar(16), NOT NULL | Required on creation; no implicit role | Database check in `{LEADER, MANAGER, HELPDESK}` |
| `is_active` | boolean, NOT NULL | Python and DDL default true | No standalone index at ~50-user scale |
| `must_change_password` | boolean, NOT NULL | Python and DDL default true for created/reset users | No standalone index |
| `last_login` | timestamp with time zone, NULL | Updated on successful login | Optional |
| `created_at` | timestamp with time zone, NOT NULL | Server-generated once | Stable tie-break uses id |

Database invariants:

1. `username` is exact-value unique and nonblank. No unapproved case-folding uniqueness is added.
2. `full_name` cannot be empty or whitespace-only.
3. Role is one of the three canonical values.
4. A PostgreSQL BEFORE UPDATE trigger rejects any changed username, including ORM/command writes.
5. Phone and email duplicates are explicitly valid.
6. No role or password default is silently assigned from an omitted API field.

Query behavior:

- Directory base query includes active/inactive and all roles.
- Optional `q` uses case-insensitive contains over full_name OR username.
- Optional role and active filters are exact.
- Stable order is full_name, username, id.
- Page size is server-owned. No `page_size`, cursor, trigram extension, or search index is introduced for ~50 users.

### token_blacklist.OutstandingToken

Library-owned server record for each refresh credential.

| Attribute | Rule |
|---|---|
| Owner | `rest_framework_simplejwt.token_blacklist`; do not copy into identity models. |
| User | FK to `identity.User`. |
| JTI | Unique token identifier; never logged/audited/evented. |
| Expiry | 7-day refresh lifetime. Expired rows are not active sessions. |
| Creation | Occurs only through session adapter while User row is locked. |

### token_blacklist.BlacklistedToken

Library-owned revocation record with one-to-one/unique relationship to OutstandingToken.

- Rotation blacklists the consumed refresh token.
- Logout, reset, password change, and deactivation blacklist every unexpired outstanding token for the user.
- Conflict-safe insertion makes concurrent attempts idempotent without breaking the caller transaction.
- No individual access-token blacklist exists.

### audit.AuditLog

Exactly the eight fields mandated by CHOT §7/R-104.

| Field | Type / nullability | Rule |
|---|---|---|
| `id` | Big integer PK | Server generated. |
| `actor` | FK User, NOT NULL | Authenticated actor; protective deletion. |
| `action` | varchar(100), NOT NULL | Closed feature-002 audit action string. |
| `target_type` | varchar(64), NOT NULL | `User` for this feature. |
| `target_id` | varchar(64), NOT NULL | String form of target id. |
| `before` | JSON object, NOT NULL | Minimal pre-state; `{}` if no prior state. |
| `after` | JSON object, NOT NULL | Minimal post-state/result. |
| `recorded_at` | timestamp with time zone, NOT NULL | Server-generated. |

Indexes:

- `(actor_id, recorded_at DESC)` for actor history.
- `(target_type, target_id, recorded_at DESC)` for target history.

Invariants:

- Database trigger rejects UPDATE and DELETE; records are append-only.
- No request_id/correlation_id columns may be added.
- `before`/`after` pass the canonical payload filter before insert.
- Forbidden keys/values include password/hash/generated password, token/JTI/credential, cookie/session secret, object key/image, exact coordinates, any string containing `://`, and UI/push prose.
- Failure of payload validation aborts the caller's entire transaction with a path-only diagnostic.

### audit.OutboxEvent

Durable event envelope appended with the business mutation.

| Field | Type / nullability | Default / constraint |
|---|---|---|
| `id` | Big integer PK | Server generated. |
| `event_id` | UUID, NOT NULL | Server-generated; UNIQUE; stable across later delivery retries. |
| `event_type` | varchar(100), NOT NULL | Closed feature event string. |
| `schema_version` | positive integer, NOT NULL | `1` for feature-002 events. |
| `aggregate_type` | varchar(64), NOT NULL | `User`. |
| `aggregate_id` | varchar(64), NOT NULL | String User id. |
| `aggregate_version` | positive integer, NOT NULL | Monotonic per aggregate; UNIQUE with type/id. |
| `payload` | JSON object, NOT NULL | Minimal filtered data. |
| `created_at` | timestamp with time zone, NOT NULL | Server-generated. |
| `request_id` | varchar(64), NOT NULL | Python + DDL default `""`; ambient context. |
| `correlation_id` | varchar(64), NOT NULL | Python + DDL default `""`; ambient context. |
| `publish_state` | varchar(16), NOT NULL | Python + DDL default `PENDING`; check in `{PENDING, PUBLISHED, DEAD_LETTER}`. |
| `published_at` | timestamp with time zone, NULL | Null on append. |
| `lease_expires_at` | timestamp with time zone, NULL | Null on append; reserved for approved relay behavior. |

Constraints/indexes:

- Unique event_id.
- Unique `(aggregate_type, aggregate_id, aggregate_version)`.
- Check `schema_version >= 1` and `aggregate_version >= 1`.
- Check closed publish_state.
- Index `(publish_state, created_at, id)` for deterministic pending traversal.

Append rules:

- Caller holds the User row lock before allocating the next per-user aggregate version.
- The adapter reads request/correlation context itself; no application DTO carries it.
- Empty correlation values are valid outside an HTTP request.
- Payload passes the same canonical filter used for AuditLog before insert.
- New event is always PENDING with no published/lease time.
- Relay claim, retry, backoff, delivery, consumer dedupe, and dead-letter operations are not implemented by this feature.

## DTOs and result models

### Request DTOs

| DTO | Client-owned fields | Explicitly rejected fields |
|---|---|---|
| `LoginRequest` | username, password | Any extra server-owned field |
| `RefreshRequest` | none (refresh cookie is transport-owned) | JSON refresh/token/user fields |
| `CreateUserRequest` | username, full_name, role, optional phone/email | password, user_id, is_active, must_change_password |
| `UpdateAdminProfileRequest` | optional full_name/phone/email, at least one field | username, role, password, is_active, user_id |
| `AssignRoleRequest` | role only | Every other field |
| `SetStatusRequest` | is_active only | Every other field |
| `ResetPasswordRequest` | no fields | Any field, especially password |
| `UpdateSelfProfileRequest` | optional full_name/phone/email, at least one field | user_id, username, role, password, is_active, must_change_password |
| `ChangePasswordRequest` | current_password, new_password | user_id, username, role, is_active |

Action/Manager-target checks run before these DTOs are validated. Within DTO validation, explicit server-owned-field rejection precedes allowed-field value validation.

### GeneratedPasswordDisplayResult

| Field | Rule |
|---|---|
| `user` / `user_id` | Non-secret created/reset result. |
| `generated_password` | Plaintext only in memory for the immediate response; excluded from repr, logging, exceptions, audit, event, and persistence. |

It has no repository serialization and no read operation. Once the HTTP response/UI state is gone, reset is the only recovery.

### SessionResult

| Field | Rule |
|---|---|
| `access` | 15-minute bearer value returned in JSON; response is no-store. |
| refresh | Never a JSON/result field exposed to the generated client; adapter sets protected cookie. |
| account state | Login returns role, is_active, must_change_password, and effective capabilities. |

## State transitions

### Account state

```text
create/reset ──> active + must_change_password
password change ──> active + password changed + must_change_password=false
status(false) ──> inactive (all refresh revoked immediately)
status(true) ──> active (password-change flag preserved)
status(current value) ──> no-op (no write/evidence/version)
```

- Deactivation changes only Identity-owned state and refresh-blacklist/evidence state. Identity must not call or write Task, Attendance, Reporting, or another business module; integration proof for those modules' row preservation is deferred to their owning features.
- Reactivation does not clear must_change_password or issue a session.
- Role transitions through API are only Leader ↔ Helpdesk; any current Manager is not an eligible target.

### Refresh credential

```text
outstanding + valid + active user
  ├─ refresh wins lock ─> old blacklisted + new outstanding
  ├─ rotation reuse ───> denied INVALID_TOKEN
  ├─ global revoke ────> blacklisted
  └─ expiry ───────────> denied INVALID_TOKEN
```

### Forced password change

```text
must_change_password=true
  ├─ login allowed (repeatable, no TTL)
  ├─ change-password allowed
  └─ every other protected operation -> PASSWORD_CHANGE_REQUIRED

successful change:
  validate -> lock User -> verify unchanged current hash/state
  -> revoke all old refresh -> set new hash/flag false
  -> audit/outbox -> issue new access+refresh -> commit
```

The issue operation is ordered after revocation and inside the same serialized User transaction.

## Transaction boundaries

| Use case | Locked rows | Atomic writes |
|---|---|---|
| Login | User | last_login + OutstandingToken; no audit/outbox required |
| Refresh | User | old BlacklistedToken + new OutstandingToken only when active and must_change_password=false |
| Logout | User | Always scan/revoke by access actor; positive count writes blacklist + one session AuditLog/OutboxEvent, zero count writes none; always `204` and clear cookie |
| Change password | User | password hash + must_change flag + all blacklist rows + user/session audit/events + new OutstandingToken |
| Create user | Uniqueness constraint; new User becomes aggregate | User + AuditLog + OutboxEvent version 1 |
| Admin profile | Target User | profile fields + AuditLog + OutboxEvent |
| Assign role | Target User | role + AuditLog + OutboxEvent |
| Set status true | Target User | Transition only: active flag + AuditLog + OutboxEvent; already true is no-op |
| Set status false | Target User | Transition only: active flag + user state evidence; positive revoke count additionally writes blacklist + session evidence; already false is no-op |
| Reset password | Target User | Always new hash + must_change flag + reset evidence; positive revoke count additionally writes blacklist + session evidence |

Any exception after append rolls back every row in the use case. Audit/outbox adapters do not create nested independent commit boundaries.

## Concurrency invariants

1. One refresh token can rotate successfully at most once, including simultaneous requests.
2. Login issuance and refresh issuance each serialize against logout, Manager reset, self password change, and deactivation through the same User lock. Tests prove both lock orders: issuance-first refresh state is observed by the later revoker; revocation/mutation-first issuance rechecks the resulting session/account/credential state. Logout does not prohibit a genuinely later login.
3. A later fresh login after logout is allowed; a later login after reset is allowed but remains forced-change; a later login after deactivation is denied.
4. A user-admin target promoted to Manager before a competing mutation obtains its lock is protected; if the eligible mutation commits first, the later promotion observes that committed state. No write occurs after observing Manager under lock.
5. Exactly one concurrent create with a duplicate username commits.
6. Concurrent global revocations for one User serialize and remain conflict-safe without leaving a usable refresh credential. Exactly the positive-count winner appends aggregate revocation evidence; zero-count followers append none.
7. Concurrent OutboxEvent allocation for one User serializes on that User and produces strictly increasing unique aggregate versions; different Users need no global order.

Logout never uses submitted refresh owner as authority. After locking the access-token actor it revokes all active refresh rows regardless of missing/invalid/mismatched/revoked cookie state, then returns `204`; cookie clearing is an HTTP-adapter effect. Positive count creates one aggregate AuditLog/OutboxEvent pair, while zero count creates none.

Repeated `active→active`, `inactive→inactive`, and zero-session revocation are approved no-ops without evidence/version. Successive deliberate password resets remain distinct mutations with new reset evidence. Aggregate version advances once per committed OutboxEvent and never advances for a no-op.

## Migration design

1. Extend approved local apps/migration owners to `operations`, `identity`, and `audit`; keep config/core non-apps.
2. Configure `AUTH_USER_MODEL` before applying `django.contrib.auth` and token-blacklist migrations.
3. Existing deployed `identity.0001_initial` creates User, checks, indexes, and username-immutability trigger; remediation never edits it and uses additive `0002+` only for an approved missing invariant.
4. Existing deployed `audit.0001_initial` depends on the swappable User model, creates AuditLog/OutboxEvent, checks/indexes, and AuditLog-immutability trigger; remediation never edits it.
5. Third-party blacklist migrations create OutstandingToken/BlacklistedToken against the custom User.
6. All operations are additive. No rename/remove/alter contraction occurs; no business data backfill is needed because the prior feature had no User/audit/token tables.
7. A PostgreSQL MigrationExecutor test applies the exact feature-001 migration state, advances to feature 002, verifies the schema and behavior, and confirms one leaf per local app.
