# API Contract: Identity, Authentication and User Administration

This design contract guides backend annotations and generated OpenAPI. `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts` remain generated artifacts and are not edited by hand.

## Common rules

- Canonical namespace: `/api/v1/`, declared once by `config.urls`.
- JSON wire fields are snake_case.
- Every response is `Cache-Control: private, no-store` and returns server-issued `X-Request-Id`.
- Errors use `{error_code, message, details, request_id, error}` plus deprecated top-level field mirrors where applicable.
- Protected operations use bearer access credentials. The access claim set is exactly `user_id`, `exp`, `jti`, `token_type`.
- Refresh credentials appear only in a host-only `Secure; HttpOnly; SameSite=Strict` cookie with no Domain and Path `/api/v1/auth/`. They never appear in JSON, URLs, logs, audit, outbox, browser storage, examples, or generated client values.
- Role and capability schema items are strings without OpenAPI enum constraints. Server validation still uses the closed runtime vocabulary.

## Shared representations

### SelfUser

| Field | Type | Rule |
|---|---|---|
| `id` | integer | Authenticated User id. |
| `username` | string | Read-only and immutable. |
| `full_name` | string | Required/nonblank. |
| `phone` | string/null | Optional and non-unique. |
| `email` | string/null | Optional and non-unique. |
| `role` | string | Runtime Role value; schema remains open string. |
| `is_active` | boolean | Current database state. |
| `must_change_password` | boolean | Current database state. |
| `last_login` | date-time/null | Server state. |
| `created_at` | date-time | Server state. |
| `capabilities` | string[] | Sorted effective PermissionAction values. |

### AdminUser

Same as SelfUser except capabilities are omitted because they describe the authenticated actor, not the target.

### UserPage

`{count, next, previous, results}` with results of AdminUser. `next`/`previous` are nullable relative links. Page size is server-owned and absent from request/response controls.

### GeneratedUserResult

`{user: AdminUser, generated_password: string}`. `generated_password` exists only in successful create/reset response schemas, is never exemplified, and never appears in an AdminUser/SelfUser schema.

## Authentication endpoints

### POST `/api/v1/auth/login`

**Operation ID**: `auth_login_create`

**Authorization**: public credential verification; origin boundary still applies.

Request:

| Field | Required | Rule |
|---|:---:|---|
| `username` | yes | Nonempty string. |
| `password` | yes | Nonempty string accepted only by this credential-check operation. |

Success `200`:

```json
{
  "access": "<redacted>",
  "role": "HELPDESK",
  "is_active": true,
  "must_change_password": false,
  "capabilities": ["attendance.check_in.self"]
}
```

The example marker is documentation-only; generated OpenAPI MUST omit credential examples. The response rotates/sets the protected refresh cookie.

Errors:

| Status/code | Condition |
|---|---|
| `400 VALIDATION_FAILED` | Missing/malformed required fields. |
| `401 INVALID_CREDENTIALS` | Unknown username, wrong password, or inactive account; same safe message/details for all. |

### POST `/api/v1/auth/refresh`

**Operation ID**: `auth_refresh_create`

**Authorization**: valid protected refresh cookie; no request body.

Success `200`: `{access}` and rotated protected refresh cookie. The submitted refresh is blacklisted before success.

Errors:

- `401 INVALID_TOKEN` for missing, expired, malformed, invalid-signature, blacklisted, or reused refresh.
- `401 ACCOUNT_INACTIVE` when the refresh is cryptographically valid but current User is inactive.
- `403 PASSWORD_CHANGE_REQUIRED` when the refresh is valid but current User still requires password change; no rotation/replacement occurs. The user signs in again with the still-valid generated password to obtain access for change-password.

No JSON refresh field is accepted or returned.

### POST `/api/v1/auth/logout`

**Operation ID**: `auth_logout_create`

**Authorization**: valid bearer access for the current User; no body. Refresh cookie state never selects the actor and does not block logout.

Success `204`: no body; the refresh cookie is always cleared with matching attributes and global revocation always runs for the access-token actor. No new credential is issued.

| Refresh cookie | Global revoke | Audit/outbox/version |
|---|---|---|
| Missing | Run for actor | One aggregate pair only if revoked count > 0; otherwise none |
| Malformed, invalid, expired, or belongs to another User | Run for actor | One aggregate pair only if revoked count > 0; otherwise none |
| Valid but already revoked | Run for actor | Evidence only if another active refresh is revoked |
| Valid and active | Run for actor | Exactly one aggregate revocation AuditLog/OutboxEvent pair |

Logout is idempotent: a repeated zero-session call remains `204`, clears the cookie, and creates no state write, AuditLog, OutboxEvent, or aggregate-version advance.

Errors:

- `401 INVALID_TOKEN` for a missing/invalid/expired access credential; refresh-cookie defects do not produce this logout error.
- `401 ACCOUNT_INACTIVE` when access is valid but the current User is inactive.
- `403 PASSWORD_CHANGE_REQUIRED` when self authorization passes but the current User still requires password change. Logout is not the password-change exemption.

An unexpired access credential remains valid until expiry unless the account-state gates block it.

## Self-service endpoints

### GET `/api/v1/me/`

**Operation ID**: `identity_me_retrieve`

**Authorization**: authenticated self; forced-password gate applies.

Success `200`: SelfUser for `request.user`.

### PATCH `/api/v1/me/`

**Operation ID**: `identity_me_partial_update`

**Authorization**: authenticated self; no user.manage requirement; forced-password gate applies.

Allowed request fields: any nonempty subset of full_name, phone, email.

Explicit `400 SERVER_OWNED_FIELD`: presence of user_id, username, role, password, is_active, must_change_password, or another server-owned identity field. Fields are rejected, not ignored.

Success `200`: updated SelfUser. A Manager can update their own allowed fields here even though Manager targets are protected in user administration.

### POST `/api/v1/change-password`

**Operation ID**: `identity_change_password_create`

**Authorization**: authenticated self; sole exemption from forced-password gate.

Request:

| Field | Required | Rule |
|---|:---:|---|
| `current_password` | yes | Must match current hash. |
| `new_password` | yes | At least 12 chars, not equal to username, passes configured validators. |

Presence of user_id, username, role, or is_active returns `400 SERVER_OWNED_FIELD`.

Success `200`: `{access}` plus a new protected refresh cookie. In one transaction, all previous refresh credentials are revoked before the new pair is issued and `must_change_password` is cleared.

A previously issued access credential is not retroactively blacklisted: it continues to work until its original 15-minute expiry, subject to the current account-state and RBAC gates. Every old refresh credential is unusable, while both credentials in the newly issued pair work immediately.

Errors:

- `400 VALIDATION_FAILED` for incorrect current password or invalid new password, with safe field details.
- `401 INVALID_TOKEN` / `401 ACCOUNT_INACTIVE` at authentication.

Failure leaves password, flag, and sessions unchanged.

## User administration endpoints

Global policy:

1. Required action is checked before DTO validation.
2. For four target mutations, current target role Manager is checked before DTO validation and again under lock before write.
3. The forced-password gate runs only after the required action and target guard have succeeded.
4. Only after those gates are payload fields validated.
5. Create/role payload value Manager returns `403 PERMISSION_DENIED` after syntactic DTO validation.

### GET `/api/v1/users/`

**Operation ID**: `users_list`

**Action**: `user.view` (Manager only).

Optional query:

| Parameter | Rule |
|---|---|
| `q` | Case-insensitive contains over full_name OR username. |
| `role` | Exact runtime role string. |
| `is_active` | Boolean. |
| `page` | Positive page number. |

No parameter is required. No default active filter, page_size, cursor, or picker variant exists. Success `200`: UserPage, including Manager and inactive accounts when matching filters. Out-of-range page is `400 VALIDATION_FAILED` with `details.page`, not 404.

Leader/Helpdesk receive `403 PERMISSION_DENIED` without user data.

### GET `/api/v1/users/{id}/`

**Operation ID**: `users_retrieve`

**Action**: `user.view`.

Success `200`: AdminUser, including a Manager target. Missing id is the project's normal not-found policy; it never bypasses authentication/action gating.

### POST `/api/v1/users/`

**Operation ID**: `users_create`

**Action**: `user.manage`.

Request:

| Field | Required | Rule |
|---|:---:|---|
| username | yes | Unique, nonblank. |
| full_name | yes | Nonblank. |
| role | yes | `LEADER` or `HELPDESK`; no default. |
| phone | no | Nullable/non-unique. |
| email | no | Nullable/non-unique and valid when present. |

Password/is_active/user_id/must_change_password fields return `400 SERVER_OWNED_FIELD`. `role=MANAGER` returns `403 PERMISSION_DENIED` after DTO parsing. Missing role is `400 VALIDATION_FAILED` with the normal field-required detail.

Success `201`: GeneratedUserResult. User is active, must_change_password is true, and generated_password is displayed only here.

Concurrent duplicate username: one `201`, one `400 VALIDATION_FAILED` with username detail; no partial audit/event/user.

### PATCH `/api/v1/users/{id}/`

**Operation ID**: `users_partial_update`

**Action**: `user.manage`; Manager target guard.

Allowed fields: nonempty subset of full_name, phone, email. Username/role/password/is_active return `400 SERVER_OWNED_FIELD` only after actor/target gates. A Manager target returns `403 PERMISSION_DENIED` even for empty/malformed/forbidden-field bodies.

Success `200`: updated AdminUser.

### PATCH `/api/v1/users/{id}/role`

**Operation ID**: `users_role_partial_update`

**Action**: `user.assign_role`; Manager target guard.

Request is exactly `{role}`. Leader/Helpdesk values succeed with `200` AdminUser and audit old/new role. Manager value returns `403 PERMISSION_DENIED`. Extra/server-owned fields return `400 SERVER_OWNED_FIELD` after action/target gates.

### PATCH `/api/v1/users/{id}/status`

**Operation ID**: `users_status_partial_update`

**Action**: `user.manage`; Manager target guard.

Request is exactly `{is_active: boolean}`. Success `200`: AdminUser. Deactivation globally revokes refresh sessions in the same transaction and causes the next access request to return ACCOUNT_INACTIVE; reactivation issues no credential and preserves must_change_password.

Repeating the already-current status returns `200` with the current AdminUser and is a no-op: no User write, revocation, AuditLog, OutboxEvent, or aggregate-version advance. A real transition writes one status AuditLog/OutboxEvent; deactivation additionally writes aggregate revocation evidence only when it revokes at least one active refresh.

### POST `/api/v1/users/{id}/reset-password`

**Operation ID**: `users_reset_password_create`

**Action**: `user.manage`; Manager target guard.

Request body is empty. Any client field, especially password, returns `400 SERVER_OWNED_FIELD` after authorization.

Success `200`:

```json
{
  "user_id": 42,
  "must_change_password": true,
  "generated_password": "<redacted>"
}
```

Generated OpenAPI MUST omit the secret example. All previous refresh credentials are blacklisted; audit/outbox excludes plaintext/hash/token identifiers. The current access credential remains usable for at most its original 15 minutes but the forced-change gate applies immediately.

Every authorized reset is a new attributable mutation, even if `must_change_password` is already true: it generates a different password/hash and appends reset AuditLog/OutboxEvent. Its global-revocation append occurs only when at least one active refresh is actually revoked.

## Canonical error precedence

| Earlier condition | Later competing condition | Required result | Owner |
|---|---|---|---|
| Missing/malformed/expired access | Any action, target, forced-state, or DTO condition | `401 INVALID_TOKEN` | Authentication class |
| Valid access but current User inactive | Any action, target, forced-state, or DTO condition | `401 ACCOUNT_INACTIVE` | Authentication class after User reload |
| Actor lacks required action | Forced-change and malformed body/filter/route identifier | `403 PERMISSION_DENIED`; DTO/identifier detail is not exposed | DRF permission action gate |
| Existing Manager target on profile/role/status/reset | Forced-change, empty/malformed body, or server-owned field | `403 PERMISSION_DENIED` | DRF body-independent target gate |
| Action and target pass; forced-change true | Malformed DTO or route identifier | `403 PASSWORD_CHANGE_REQUIRED` | DRF post-authorization account gate |
| All permission/account gates pass | Server-owned field | `400 SERVER_OWNED_FIELD` | Operation serializer |
| All permission/account gates pass | Unknown role, invalid filter/type/email, or malformed identifier | `400 VALIDATION_FAILED` or canonical `404` for route target | View/operation serializer |
| DTO parses canonical `MANAGER` role | Role is outside `ASSIGNABLE_ROLES` | `403 PERMISSION_DENIED` | Application payload authorization |
| Authorized, non-forced actor has malformed route identifier | Malformed body | Canonical `404` before body validation | View target lookup |
| Authorized forced-change actor has malformed route identifier | Route syntax | `403 PASSWORD_CHANGE_REQUIRED` before route validation | DRF permission account gate |
| Valid target identifier does not exist | Body validation | Canonical `404`, only after authentication/action/forced gates | View target lookup |
| Target becomes Manager after precheck | Otherwise valid mutation | `403 PERMISSION_DENIED`; rollback | Application locked target recheck |
| Login/refresh scope is over quota | DTO or credential evaluation | `429 THROTTLED` + `Retry-After` | Public DRF throttle gate |
| Authenticated password-change actor is over quota | Password-change DTO | `429 THROTTLED` + `Retry-After` after authentication/permission gates | Protected DRF throttle gate |
| Shared throttle store fails | Any scoped service call | `503 SERVICE_UNAVAILABLE`; no service/evidence side effect | Throttle adapter, fail closed |

The `must_change_password` check never precedes action RBAC or applicable target authorization. Self endpoints and logout are authenticated-self/session operations and do not invent a User RBAC action.

## Canonical identity error registry

| HTTP | error_code | Client behavior |
|---:|---|---|
| 400 | `VALIDATION_FAILED` | Show field/general validation details. |
| 400 | `SERVER_OWNED_FIELD` | Treat as client contract defect; do not retry unchanged. |
| 401 | `INVALID_CREDENTIALS` | Login only; keep account existence ambiguous. |
| 401 | `INVALID_TOKEN` | Protected request may attempt one refresh; refresh failure clears session and goes to login. |
| 401 | `ACCOUNT_INACTIVE` | Clear in-memory access, stop refresh, show locked-account message. |
| 403 | `PASSWORD_CHANGE_REQUIRED` | Route directly to password change; do not retry business request. |
| 403 | `PERMISSION_DENIED` | Hide/disable capability and show insufficient-permission message. |
| 429 | `THROTTLED` | Honor `Retry-After`; do not retry before the server-provided delay. |
| 503 | `SERVICE_UNAVAILABLE` | Stop the operation and retry later; throttle storage failed closed. |

## Security and schema assertions

- No operation accepts user_id for self behavior.
- Logout accepts no JSON credential, derives actor only from bearer access, and follows the idempotent cookie matrix above.
- No user response contains password hash.
- Only create/reset success schemas contain generated_password; no example value.
- The exact `password` schema property exists only in the login request; it is absent from every response and every user create/reset/profile request. No schema has a JSON `refresh_token` property.
- No token/cookie is included in query parameters or audit/event schemas.
- Role/capabilities remain OpenAPI string/string-array, not enum.
- All operation IDs are explicit/unique and generated twice byte-identically.
- Backend/OpenAPI/generated-schema drift, handwritten-client type/static verification, and merge-base compatibility must pass.

## Authentication throttle contract

| Scope | Limit/key | Placement |
|---|---|---|
| Login | 10 requests per 60 seconds per canonical client IP | Before login DTO/business credential evaluation |
| Refresh | 120 requests per 60 seconds per canonical client IP | Before cookie/business rotation evaluation |
| Password change | 5 requests per 60 seconds per authenticated User.id | After authentication/permission/account gates; before DTO |

Every attempt reaching a scope counts. All scopes use `core.cache.THROTTLE_CACHE_ALIAS`. Over-limit responses are canonical `429 THROTTLED` with `Retry-After`; shared-store failure is canonical fail-closed `503 SERVICE_UNAVAILABLE`. Neither response invokes an application service or creates audit/outbox evidence.
