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

**Authorization**: both a valid bearer access credential and a valid, unrevoked refresh cookie owned by the same current User; no body.

Success `204`: no body; all outstanding refresh credentials for the user are blacklisted, audit/outbox evidence is committed, and the refresh cookie is cleared with matching cookie attributes. No new credential is issued.

Errors:

- `401 INVALID_TOKEN` for a missing/invalid/expired access credential or for a missing, malformed, expired, mismatched-user, or already-blacklisted refresh cookie. The failure performs no global revocation, creates no success audit/outbox evidence, and issues no credential.
- `401 ACCOUNT_INACTIVE` when both credentials are otherwise valid but the current User is inactive.
- `403 PASSWORD_CHANGE_REQUIRED` when both credentials and self authorization pass but the current User still requires password change. Logout is not the password-change exemption.

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

The authoritative documents define the active-to-inactive and inactive-to-active transitions but no idempotency-key or duplicate-request evidence contract. Feature 002 therefore adds no promise about the response or audit/outbox count for repeating the already-current status; tests must not invent one.

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

## Canonical error precedence

| Order | Gate | Example |
|---:|---|---|
| 1 | Credential validity/current active account | Invalid token → 401 INVALID_TOKEN; valid token/inactive current User → 401 ACCOUNT_INACTIVE. |
| 2 | Required action | Helpdesk with `must_change_password=true` POST users with empty or malformed body → 403 PERMISSION_DENIED. |
| 3 | Body-independent target authorization | Manager target PATCH containing a forbidden field or empty body → 403 PERMISSION_DENIED. |
| 4 | Forced password change | Actor authorized for the action/target but still flagged on a non-change endpoint → 403 PASSWORD_CHANGE_REQUIRED. |
| 5 | DTO/server-owned fields and value syntax | Eligible target profile PATCH containing role → 400 SERVER_OWNED_FIELD. |
| 6 | Payload authorization | Authorized create/role DTO with role Manager → 403 PERMISSION_DENIED. |
| 7 | Object scope in the owning business module | Deferred: Feature 004 Attendance and Feature 006 Task consume generic permission provenance. |
| 8 | Business invariant/transaction/audit-outbox | Identity-owned state transition and atomic evidence. |

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

## Security and schema assertions

- No operation accepts user_id for self behavior.
- Logout accepts no JSON credential and requires the same-user bearer access plus protected refresh cookie; every invalid-cookie variant uses `INVALID_TOKEN`.
- No user response contains password hash.
- Only create/reset success schemas contain generated_password; no example value.
- The exact `password` schema property exists only in the login request; it is absent from every response and every user create/reset/profile request. No schema has a JSON `refresh_token` property.
- No token/cookie is included in query parameters or audit/event schemas.
- Role/capabilities remain OpenAPI string/string-array, not enum.
- All operation IDs are explicit/unique and generated twice byte-identically.
- Backend/OpenAPI/generated-schema drift, handwritten-client type/static verification, and merge-base compatibility must pass.
