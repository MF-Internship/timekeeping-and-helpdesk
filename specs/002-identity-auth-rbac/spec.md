# Feature Specification: Identity, Authentication and Canonical RBAC

**Feature Branch**: `feature/002-identity-auth-rbac`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Implement the authoritative identity, authentication, user-administration, and canonical RBAC model, with allow/deny acceptance scenarios and complete security-focused test coverage."

## Clarifications

### Session 2026-08-18

- Q: How does logout behave for missing, invalid, revoked, or active refresh cookies? → A: R-110 makes authenticated logout idempotent: always `204`, clear cookie, revoke all by access-token actor; evidence only when at least one active refresh is revoked.
- Q: What happens when account-state or global-revocation operations repeat an already-achieved state? → A: R-111 makes same-state status and zero-session revocation no-ops without evidence/version; repeated reset remains a new attributable mutation.
- Q: What are the canonical authentication throttles? → A: R-112 sets login 10/min/IP, refresh 120/min/IP, password change 5/min/User through the shared alias, with `429 THROTTLED` and fail-closed `503 SERVICE_UNAVAILABLE`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign In and Maintain a Revocable Session (Priority: P1)

As an active user, I can sign in with my username and password and remain signed in during normal work while the system can reliably revoke my ability to renew the session.

**Why this priority**: Every protected workflow depends on trustworthy identity and account-state enforcement.

**Independent Test**: Sign in as an active user, refresh repeatedly through rotation, attempt reuse of an old refresh credential, log out from one of two devices with valid access across every refresh-cookie state, and verify idempotent global revocation without using another feature.

**Acceptance Scenarios**:

1. **Given** an active user with valid credentials, **When** the user signs in, **Then** the response supplies a 15-minute access credential, stores a 7-day refresh credential in the protected refresh channel, and reports the user's account state, role, and capabilities without placing the refresh credential in the response body.
2. **Given** an unknown username, wrong password, or inactive account, **When** a login is attempted, **Then** every case returns the same `401 INVALID_CREDENTIALS` outcome and message so account existence is not disclosed.
3. **Given** a valid refresh credential, **When** it is used, **Then** a new access credential and rotated refresh credential are issued and the old refresh credential is revoked.
4. **Given** a refresh credential that is expired, malformed, has an invalid signature, is already revoked, or was consumed by rotation, **When** it is used, **Then** refresh is denied with `401 INVALID_TOKEN` and no replacement credential is issued.
5. **Given** the same user has active refresh sessions on two devices, **When** the user logs out from either device, **Then** all refresh sessions for that user are revoked, subsequent refresh from both devices is denied, an audit record is created, and no new credential is issued.
6. **Given** logout has revoked refresh sessions, **When** a previously issued access credential is used before its 15-minute lifetime ends, **Then** it remains usable unless the account is inactive or requires a password change; after expiry, renewal is denied.
7. **Given** logout has a valid access credential but its refresh cookie is missing, malformed, expired, belongs to another user, or is already revoked, **When** logout is attempted, **Then** it returns `204`, clears the cookie, and globally revokes by the access-token actor; audit/outbox evidence is added only if at least one active refresh is actually revoked.
8. **Given** no active refresh session remains, **When** the same authenticated user logs out again, **Then** it still returns `204` but creates no AuditLog, OutboxEvent, state write, or aggregate-version advance.

---

### User Story 2 - Complete a Required or Voluntary Password Change (Priority: P1)

As a user with a generated password, I am required to choose my own compliant password before accessing business functions, and as any authenticated user I can change my password without being forced through a second login.

**Why this priority**: Server-generated credentials are safe only when the account cannot use business functions before replacing them.

**Independent Test**: Sign in with a generated password, verify all protected business actions are blocked except password change, change the password, and verify the old session is revoked while the replacement session works.

**Acceptance Scenarios**:

1. **Given** an authenticated user has `must_change_password = true`, **When** the user requests any protected endpoint other than password change, **Then** the request is denied with `403 PASSWORD_CHANGE_REQUIRED` before business processing or side effects.
2. **Given** that same user, **When** the user requests the password-change endpoint, **Then** the request is allowed to proceed.
3. **Given** a correct current password and a new password of at least 12 characters that differs from the username and satisfies the configured password rules, **When** the user changes the password, **Then** `must_change_password` becomes false, every prior refresh session is revoked, and a fresh access/refresh pair issued after revocation works immediately on the current device.
4. **Given** an incorrect current password or a noncompliant new password, **When** password change is attempted, **Then** the change is denied, the old password and sessions remain unchanged, and no new credential is issued.
5. **Given** a password-change or self-profile request contains `user_id` or attempts to change `username`, **When** the request is evaluated, **Then** it is rejected with `400 SERVER_OWNED_FIELD` and always remains bound to the authenticated user.
6. **Given** a generated initial or reset password has not yet been changed, **When** the user signs in more than once or signs in days later, **Then** login remains possible but all business endpoints remain blocked until password change; the generated password is not treated as a one-time code and has no time-to-live.

---

### User Story 3 - Administer Eligible User Accounts (Priority: P1)

As a Manager, I can find and administer Leader and Helpdesk accounts while protected Manager accounts remain visible but cannot be modified through user administration.

**Why this priority**: The organization needs operational account management without allowing a compromised Manager to create, disable, reset, or demote another Manager.

**Independent Test**: Use only user-administration functions to list all account types, create and update eligible users, exercise state and role changes, and prove all writes to Manager targets are rejected.

**Acceptance Scenarios**:

1. **Given** a Manager, **When** the user list is requested with no filters, **Then** active and inactive users of all three roles, including Manager accounts, are returned with page-based pagination.
2. **Given** a Manager, **When** optional free-text, role, and active-state filters are combined, **Then** matching users are returned; free text searches `full_name` and `username`.
3. **Given** unique `username`, nonblank `full_name`, and role `LEADER` or `HELPDESK`, with optional phone and email, **When** a Manager creates a user, **Then** the account is active, requires password change, and a server-generated password is displayed in that response exactly once.
4. **Given** a create request omits `username`, `full_name`, or `role`, **When** it is validated after authorization, **Then** creation is denied with field-required details and no default role is assigned.
5. **Given** an existing Leader or Helpdesk, **When** a Manager updates `full_name`, phone, or email, changes the role between `LEADER` and `HELPDESK`, activates/deactivates the account, or resets its password, **Then** only the requested allowed change occurs and the security-sensitive change is audited.
6. **Given** an existing Manager target, **When** any Manager attempts profile update, role change, activation/deactivation, or password reset through user administration—even against their own account and even with an empty body—**Then** the request is denied with `403 PERMISSION_DENIED`, nothing changes, and no success audit/event is created.
7. **Given** a create or role-change request specifies `MANAGER`, **When** a Manager submits it, **Then** the request is denied with `403 PERMISSION_DENIED`, no Manager account is created or assigned, and no partial mutation occurs.
8. **Given** an eligible profile-update request contains `username`, `role`, `password`, or `is_active`, **When** the Manager submits it, **Then** the request is rejected with `400 SERVER_OWNED_FIELD` and no field is changed.
9. **Given** an account has been deactivated, **When** it is viewed in user administration, **Then** it remains visible and can be reactivated if it is not a Manager; Identity performs no call or write into Task, Attendance, Reporting, or another business module, while row-preservation integration proof remains with each owning feature.
10. **Given** an eligible account already has the requested active state, **When** a Manager repeats that status request, **Then** it returns `200` with current state but performs no User write, revocation, audit/outbox append, or aggregate-version advance.

---

### User Story 4 - Receive a Generated Password Exactly Once (Priority: P1)

As a Manager creating or resetting an eligible account, I can relay a strong generated password to the user once without the product retaining a readable copy.

**Why this priority**: This prevents shared predictable passwords and prevents the password display mechanism from becoming a secret-recovery channel.

**Independent Test**: Create and reset an eligible account, capture the immediate responses, then inspect every later read, audit record, event, diagnostic, and application log to prove the plaintext cannot be recovered.

**Acceptance Scenarios**:

1. **Given** an authorized create or reset operation, **When** it succeeds, **Then** the server generates the password, returns it only in that operation's response, sets `must_change_password = true`, and never accepts a client-supplied password for that operation.
2. **Given** the one-time display has been dismissed or the response is no longer available, **When** any user or administrator reads the account later, **Then** no readable password is returned or recoverable; the only recovery path is another reset.
3. **Given** a password reset succeeds, **When** the target's existing refresh credentials are used, **Then** every one is denied, while an unexpired access credential remains usable for at most 15 minutes but is immediately constrained by `must_change_password`.
4. **Given** audit, event, logging, error, or monitoring records for create/reset, **When** they are inspected, **Then** none contains the plaintext generated password or any authentication credential.

---

### User Story 5 - Enforce Canonical Role Capabilities and Permission Provenance (Priority: P1)

As a user, I see actions appropriate to my role, while the server independently enforces the same canonical action map, implication rules, target restrictions, and record scope.

**Why this priority**: Presentation-only restrictions or broad role inheritance would permit unauthorized mutations and cross-user access.

**Independent Test**: Run the complete Role × PermissionAction matrix, the closed implication set, grant-provenance cases, and identity-owned malformed-body precedence cases without invoking or implementing Task or Attendance endpoints.

**Acceptance Scenarios**:

1. **Given** any of the three roles, **When** capabilities are requested for the frontend, **Then** the returned capabilities reflect effective direct and implied actions from the canonical map and do not grant an action outside it.
2. **Given** a Leader, **When** the canonical policy is evaluated for any mutation action, **Then** the decision is denied; an identity-owned user-administration request is also denied with `403 PERMISSION_DENIED` and creates no user, audit-success, or event side effect.
3. **Given** a Helpdesk user, **When** any user-list or user-administration operation is attempted, **Then** it is denied with `403 PERMISSION_DENIED` and no user data or validation detail is disclosed.
4. **Given** a Manager, **When** the canonical policy is evaluated for check-in or check-out, **Then** the decision is denied, while `task.complete.field` remains a distinct direct grant whose record ownership is not evaluated by Feature 002.
5. **Given** an actor lacks the required action and sends a malformed body, **When** the request is evaluated, **Then** `403 PERMISSION_DENIED` is returned before any DTO/input error.
6. **Given** a user-administration request targets an existing Manager and also contains a forbidden field, **When** it is evaluated, **Then** the target restriction wins and `403 PERMISSION_DENIED` is returned before `400 SERVER_OWNED_FIELD`.
7. **Given** a requested self action is opened by a documented all/any implication, **When** the canonical policy returns its decision, **Then** `granted_by` identifies the stronger direct action; when a self action is directly granted, `granted_by` remains that self action.
8. **Given** a future owning business module receives a permission decision, **When** it determines record ownership, **Then** it can distinguish direct-self from implied all/any without Identity encoding Task creator/assignee or Attendance ownership rules.

### Edge Cases

- Two refresh requests race with the same refresh credential; at most one rotation succeeds and reuse of the consumed credential is denied.
- A refresh or protected request arrives immediately after deactivation; refresh is denied and the next protected request with an otherwise valid access credential returns `401 ACCOUNT_INACTIVE`.
- A role changes while an access credential is still valid; the next request uses the current stored role and permission map, not stale role or permission claims.
- Logout is called with one refresh credential while other device credentials exist; all refresh credentials for the user are revoked.
- Logout is called with valid access but a missing, invalid, mismatched, or already-revoked refresh cookie; it returns `204`, clears the cookie, and revokes by access-token actor. A zero-session repeat creates no evidence.
- A generated password is lost before delivery; it cannot be viewed again and must be reset.
- Two concurrent create requests use the same username; exactly one succeeds and the other reports the uniqueness conflict without creating a duplicate.
- `full_name` is absent, empty, or whitespace-only; creation/update is rejected. Phone and email may be omitted, blank according to the canonical contract, or duplicated across users.
- A Manager-target mutation has an empty or malformed body; target protection still returns `403` before body validation.
- A profile update contains a valid role such as `HELPDESK`; it still returns `400 SERVER_OWNED_FIELD` because that endpoint never owns role changes.
- A self endpoint receives another user's identifier; it rejects the field rather than silently ignoring it and never reads or mutates the named user.
- An inactive account uses correct credentials at login; the response remains indistinguishable from other invalid credentials.

## Requirements *(mandatory)*

### Functional Requirements

#### Identity and Account State

- **FR-001**: The system MUST represent each user with an identifier, immutable unique `username`, required nonblank `full_name`, optional non-unique phone, optional non-unique email, exactly one role from `LEADER`, `MANAGER`, or `HELPDESK`, active state, `must_change_password`, last-login time when available, and creation time.
- **FR-002**: User creation MUST require exactly `username`, `full_name`, and `role` as mandatory client fields; role MUST NOT default when omitted, and password MUST be server-generated.
- **FR-003**: No API or self-service operation MAY change `username` after account creation.
- **FR-004**: Every authenticated request MUST re-evaluate current `is_active`, `must_change_password`, and role state from the authoritative account record; role or permission claims MUST NOT be trusted from an already-issued token.
- **FR-005**: An otherwise valid authenticated request for an inactive account MUST return `401 ACCOUNT_INACTIVE`; login for an inactive account MUST instead return the same `401 INVALID_CREDENTIALS` response used for invalid credentials.

#### Authentication and Credential Lifecycle

- **FR-006**: Login MUST accept username and password, issue a 15-minute access credential, establish a 7-day refresh credential through the protected refresh channel, update last-login state, and return account state, role, and effective capabilities without returning the refresh credential in JSON.
- **FR-007**: The refresh credential MUST be server-tracked and rotated after each successful refresh; the consumed credential MUST be revoked, and any expired, invalid, revoked, or reused credential MUST return `401 INVALID_TOKEN` without replacement credentials.
- **FR-008**: Logout MUST require valid authenticated access, derive its actor only from that access identity, clear the refresh cookie, call global revocation, and return `204` whether the refresh cookie is missing, invalid, expired, mismatched, revoked, or active. It MUST NOT issue replacement credentials. It MUST append one revocation AuditLog and OutboxEvent only when at least one active refresh is revoked; a zero-session repeat MUST create no evidence or aggregate-version advance.
- **FR-009**: Logout, Manager password reset, self password change, and deactivation MUST each revoke every outstanding refresh credential for the affected user and record the reason; no flow MAY revoke only the submitted refresh credential.
- **FR-010**: Revocation MUST NOT blacklist individual access credentials. An already-issued access credential MUST work before its 15-minute expiry and fail after expiry, except every request remains immediately subject to inactive-account and required-password-change gates. After self password change, the old access credential remains valid until that boundary, every old refresh credential is revoked, and the newly issued access/refresh pair works immediately.
- **FR-011**: Self password change MUST verify the current password, require a new password of at least 12 characters that differs from the username and satisfies configured password rules, clear `must_change_password`, revoke all refresh credentials first, and then return a fresh access/refresh pair for the current device.
- **FR-012**: A failed password change MUST leave the password, account-state flag, and all sessions unchanged.
- **FR-013**: Authentication credentials MUST NOT appear in browser storage, URLs, audit records, events, logs, monitoring output, error details, or account responses; the refresh credential MUST use the authoritative host-only protected-cookie restrictions.

#### First Login and Generated Passwords

- **FR-014**: Every newly created or Manager-reset account MUST have `must_change_password = true`.
- **FR-015**: While `must_change_password = true`, every protected endpoint except self password change MUST return `403 PASSWORD_CHANGE_REQUIRED` before business processing.
- **FR-016**: The system MUST generate initial and reset passwords server-side using a security-grade random source; user create and reset inputs MUST reject any `password` field with `400 SERVER_OWNED_FIELD` after the action and target authorization gates pass.
- **FR-017**: A generated password MUST be returned as plaintext only in the single successful create/reset response, MUST never be stored or exposed in recoverable plaintext, and MUST require another reset if the response is lost.
- **FR-018**: A generated password MUST remain valid until changed and MUST NOT behave as a single-use or expiring code; repeated login remains allowed while the password-change gate remains enforced.

#### User Administration

- **FR-019**: Only actors with `user.view` MAY list or retrieve users; under the canonical map this is Manager only, and both Leader and Helpdesk MUST receive `403 PERMISSION_DENIED`.
- **FR-020**: User list filters MUST all be optional and support page-based pagination, free-text search over full name and username, exact role, and active state. With no filters, active and inactive users of all roles—including Manager—MUST be visible.
- **FR-021**: Only actors with `user.manage` MAY create users, update eligible profiles, change eligible account state, or reset eligible passwords; only actors with `user.assign_role` MAY change an eligible role.
- **FR-022**: User creation and role change MUST accept only `LEADER` or `HELPDESK` as assignable roles. Any attempt to create or assign `MANAGER` MUST return `403 PERMISSION_DENIED` without mutation.
- **FR-023**: Every existing user whose current role is `MANAGER` MUST be protected from all user-administration writes: profile update, role change, activation, deactivation, and password reset MUST return `403 PERMISSION_DENIED`, including when actor and target are the same. Reads MUST remain allowed to authorized viewers.
- **FR-024**: Eligible profile update MUST allow only full name, phone, and email. Presence of username, role, password, or active state MUST return `400 SERVER_OWNED_FIELD` and cause no partial update.
- **FR-025**: Role change, account-state change, and password reset MUST remain distinct operations with narrowly owned input; reset MUST accept no client fields, generate and display the password exactly once, set the password-change flag, revoke all refresh sessions, and exclude the password from audit data.
- **FR-026**: Deactivation MUST prevent login, refresh, and the next authenticated request. Feature 002 MUST make no call or write into Task, Attendance, Reporting, or another business module; architecture boundaries MUST enforce this absence of cross-module mutation. Reactivation through user administration is allowed only for non-Manager targets. Integration proof that existing Task, Attendance, assignment, history, and report rows remain unchanged is deferred to their owning features and the underlying preservation requirement remains mandatory there.
- **FR-027**: Self profile and self password operations MUST derive the target exclusively from authenticated context, require no user-administration action, reject supplied `user_id`, and allow a Manager to maintain their own permitted personal fields and password despite the Manager-target administration guard.
- **FR-028**: Every user creation, allowed profile/role/state change, password reset, password change, logout, and session revocation MUST create attributable audit evidence in the same successful unit of work where applicable; denied or rolled-back operations MUST leave no success audit/event side effect.

#### Canonical Authorization

- **FR-029**: The canonical direct Role × `PermissionAction` map MUST be exactly:

  | PermissionAction | LEADER | MANAGER | HELPDESK |
  |---|:---:|:---:|:---:|
  | `attendance.check_in.self`, `attendance.check_out.self`, `attendance.view.self` | Deny | Deny | Allow |
  | `attendance.view.all` | Allow | Allow | Deny |
  | `task.create.self`, `task.complete.field` | Deny | Allow | Allow |
  | `task.view.self`, `task.update.self` | Deny | Deny | Allow |
  | `task.view.all` | Allow | Allow | Deny |
  | `task.create.assign`, `task.update.any` | Deny | Allow | Deny |
  | `task.complete.override` | Deny | Allow | Deny |
  | `location.view`, `config.view` | Allow | Allow | Allow |
  | `location.manage`, `config.manage_attendance`, `holiday.manage` | Deny | Allow | Deny |
  | `user.view`, `user.manage`, `user.assign_role` | Deny | Allow | Deny |
  | `report.view.self` | Deny | Deny | Allow |
  | `report.view.all`, `report.export`, `photo.view.all` | Allow | Allow | Deny |
  | `photo.view.self` | Deny | Deny | Allow |

- **FR-030**: The permission implication map MUST be closed to exactly these five pairs and MUST infer no other relationship:

  | Direct action | Implied action |
  |---|---|
  | `task.view.all` | `task.view.self` |
  | `task.update.any` | `task.update.self` |
  | `attendance.view.all` | `attendance.view.self` |
  | `report.view.all` | `report.view.self` |
  | `photo.view.all` | `photo.view.self` |

- **FR-031**: The canonical map MUST NOT directly duplicate implied self-actions for Manager. `location.manage` MUST NOT imply `location.view`, `config.manage_attendance` MUST NOT imply `config.view`, and no create, completion, override, holiday, user, or other mutation action may be inferred.
- **FR-032**: Leader MUST remain read-only and MUST hold no mutation action. Helpdesk MUST hold no user-administration action. Manager MUST hold neither check-in nor check-out action. Feature 002 MUST prove those policy decisions and identity-owned user-administration denies; HTTP enforcement and side-effect absence for Attendance and Task actions are deferred to Features 004 and 006 respectively.
- **FR-033**: Frontend capabilities MAY hide, disable, or explain unavailable actions but MUST be computed from the effective canonical action map and MUST NOT replace server authorization.
- **FR-034**: Every protected operation MUST evaluate in this order: authentication; action permission including closed implications; body-independent target authorization; the `must_change_password` account gate for every operation except self password change; any approved endpoint throttle; DTO/input validation; object scope/ownership in the owning business module; business invariant/state transition; atomic state change and persistence constraint; audit/outbox. The password-change gate and throttle MUST NOT precede action or target authorization. Public login/refresh throttles run before their DTO/credential business evaluation.
- **FR-035**: An actor lacking an action MUST receive `403 PERMISSION_DENIED` even when the request body is malformed. A request against a protected Manager target MUST receive the same authorization result before DTO/input errors, including with an empty body. Precedence combinations MUST be deterministic: unauthorized plus `must_change_password` returns `403 PERMISSION_DENIED`; authorized plus `must_change_password` returns `403 PASSWORD_CHANGE_REQUIRED`; unauthorized plus invalid payload returns `403 PERMISSION_DENIED`; and a protected Manager target plus invalid payload returns `403 PERMISSION_DENIED`.
- **FR-036**: A payload-based request for a non-assignable role MUST be evaluated after DTO/input validation but MUST still return `403 PERMISSION_DENIED`, not a generic validation outcome.
- **FR-037**: Feature 002 MUST return a generic permission decision containing the requested action, allow/deny result, and direct `granted_by` action. It MUST prove direct decisions, exactly the five approved implications, and no implicit all-to-self grant outside that map. It MUST NOT encode or execute Task creator/assignee checks or Attendance record ownership. Feature 004 MUST enforce Attendance self object scope; Feature 006 MUST enforce Task creator/assignee object scope and business invariants using the generic decision provenance.
- **FR-038**: Self-scoped reads and writes MUST derive the actor from authentication context and reject any client attempt to override actor, permission, scope, server timestamps, or other server-owned identity/authorization fields.

#### Contract and Verification

- **FR-039**: The identity and access-control contract MUST expose exactly these canonical operation families under the project versioned namespace with their stated ownership and action gates:

  | Method + path | Required action or ownership | Purpose |
  |---|---|---|
  | `POST /api/v1/auth/login` | Public credential check | Sign in with username and password; return access plus account/role state and set the protected refresh credential |
  | `POST /api/v1/auth/refresh` | Valid refresh credential | Rotate refresh and return a new access credential |
  | `POST /api/v1/auth/logout` | Valid authenticated self; cookie is non-authoritative | Idempotently revoke all refresh sessions for the access-token actor and clear the cookie |
  | `GET`, `PATCH /api/v1/me/` | Authenticated self | Read or update permitted personal information derived from authentication context |
  | `POST /api/v1/change-password` | Authenticated self | Change the authenticated user's password and replace the current session after global refresh revocation |
  | `GET /api/v1/users/`, `GET /api/v1/users/{id}/` | `user.view` | List, search/filter, or retrieve users, including Manager and inactive accounts |
  | `POST /api/v1/users/` | `user.manage` | Create an eligible user with a generated password |
  | `PATCH /api/v1/users/{id}/` | `user.manage` | Update only eligible profile fields |
  | `PATCH /api/v1/users/{id}/role` | `user.assign_role` | Assign only Leader or Helpdesk |
  | `PATCH /api/v1/users/{id}/status` | `user.manage` | Activate or deactivate an eligible user |
  | `POST /api/v1/users/{id}/reset-password` | `user.manage` | Generate and display a replacement password once |

- **FR-040**: Login and refresh MUST be protected against account enumeration and refresh reuse respectively; every deny case MUST produce no forbidden user, token, identity mutation, audit-success, or outbox-success side effect.
- **FR-041**: Verification MUST cover login success/failure, refresh success/rotation/reuse, logout across devices, account-state checks on every request, first-login enforcement, password reset, Manager-target protection, Leader mutation denial, the complete direct and effective RBAC matrix, authorization-before-DTO precedence, generic permission-decision provenance, and explicit record-ownership deferral to Features 004 and 006.
- **FR-042**: User-list pagination MUST accept `page` only, return count/next/previous/results, expose no client-selected page size, and return a field-specific validation failure rather than a missing-resource outcome when the requested page is outside the valid range.
- **FR-043**: Every claimed User-row serialization invariant MUST have a real PostgreSQL competing-worker test covering login issuance and refresh issuance against each of logout, password reset, self password change, and account deactivation; concurrent global revocations for one User; and concurrent per-User outbox aggregate-version allocation. Each test MUST assert final persisted state, that no racing refresh issuance escapes a completed revocation, that no revoked refresh becomes usable, that access credentials retain only the canonical lifetime/account-state behavior, and that aggregate versions remain unique and correctly serialized without replacing database locking with mocks.
- **FR-044**: Setting an eligible User to its existing active state MUST return `200` as a no-op without a User write, revocation call, AuditLog, OutboxEvent, or aggregate-version advance. A real state transition MUST append state evidence; deactivation MUST additionally invoke global revocation.
- **FR-045**: Global refresh revocation with zero active refresh sessions MUST succeed with `revoked_count = 0` and create no blacklist row, AuditLog, OutboxEvent, or version advance. Repeated password reset MUST remain a new mutation with a new generated password and reset evidence; revocation evidence is appended only when its revoked count is positive.
- **FR-046**: The system MUST enforce shared-cache authentication throttles through `core.cache.THROTTLE_CACHE_ALIAS`: login 10 requests per 60 seconds per canonical client IP, refresh 120 per 60 seconds per canonical client IP, and password change 5 per 60 seconds per authenticated User. Exceeding a limit MUST return canonical `429 THROTTLED` with `Retry-After`; throttle-storage failure MUST fail closed with canonical `503 SERVICE_UNAVAILABLE`. Neither failure may call the business service or append audit/outbox evidence.

### Key Entities

- **User**: A person authorized to use the product, identified by immutable username and carrying contact, display, role, active-state, forced-password-change, last-login, and creation attributes.
- **Role**: One of the closed identities `LEADER`, `MANAGER`, or `HELPDESK`, used only through the canonical action policy.
- **PermissionAction**: A closed business action checked for each protected operation; direct grants are defined by the canonical matrix and effective grants may add only the five documented implications.
- **Refresh Session**: A server-tracked renewable authentication session belonging to one user; it can rotate, expire, or be revoked and is revocable across all devices.
- **Revocation Record**: Evidence that a refresh session can no longer be used, including rotation/reuse protection and user-wide security revocation.
- **Frontend Capability Set**: The effective actions presented to the current user for interface decisions; it mirrors but never replaces server enforcement.
- **Audit Record**: Immutable attributable evidence of a security-sensitive successful operation or revocation, excluding passwords and credentials.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of active-user login cases issue a usable session, while 100% of wrong-password, unknown-user, and inactive-account cases return the same non-enumerating login failure.
- **SC-002**: In automated rotation and race tests, 100% of consumed, revoked, expired, invalid, and reused refresh credentials are denied, and no single refresh credential successfully rotates more than once.
- **SC-003**: In multi-device tests, logout, reset, password change, and deactivation revoke 100% of outstanding refresh sessions for the affected user; deactivation blocks 100% of subsequent authenticated requests immediately.
- **SC-004**: 100% of users with `must_change_password = true` are blocked from every tested non-exempt protected Identity endpoint and can reach password change; ordered-gate acceptance tests prove the same reusable decision for future protected business endpoints. After successful change, the newly issued session works on the first attempt and all prior refresh sessions fail.
- **SC-005**: A Manager can complete create, search/filter, eligible profile update, eligible role change, eligible state change, and eligible password reset in no more than two minutes per task in usability validation.
- **SC-006**: Across create/reset verification, generated plaintext passwords appear only in the initiating response and appear zero times in subsequent account reads, audits, events, logs, diagnostics, or monitoring output.
- **SC-007**: 100% of attempted user-administration writes against an existing Manager and 100% of attempts to create/assign the Manager role are denied with no state change; 100% of authorized user reads continue to include Manager accounts.
- **SC-008**: The direct and effective Role × PermissionAction test matrices have 100% expected allow/deny agreement, exactly five implication pairs, zero inferred extra actions, and zero mutation grants for Leader.
- **SC-009**: In every tested insufficient-permission or protected-target request containing malformed or forbidden input, authorization wins before input validation and no schema detail or state mutation is exposed.
- **SC-010**: Permission-provenance tests have 100% agreement for direct-self and implied all/any decisions, identify the direct `granted_by` action in every allow case, and infer zero all-to-self relationship beyond the five approved pairs. Feature 002 contains zero Task creator/assignee or Attendance ownership implementation.
- **SC-011**: Frontend role/capability behavior matches effective server authorization for 100% of tested canonical actions, while direct unauthorized requests remain denied even if the interface is bypassed.
- **SC-012**: The complete Definition of Done authentication, account-state, password, RBAC, Manager-target, Leader-denial, permission-provenance, and scope-deferral suites pass with zero unresolved security-critical failures.
- **SC-013**: Across the ten required authoritative-database competing-worker scenarios, every completed revocation leaves zero usable pre-existing or racing refresh credentials, and concurrent event allocation produces one unique monotonic aggregate version per committed event.
- **SC-014**: Logout-cookie and repeated-state tests have 100% agreement with R-110/R-111: valid-access logout always returns `204`; no-op calls create zero state/evidence/version changes; every positive revocation creates exactly one aggregate revocation evidence pair.
- **SC-015**: Controlled-clock throttle tests prove the exact 10/120/5 limits, key isolation and shared-worker counting, canonical `429`/`Retry-After`, and fail-closed `503` with zero business side effects.

## Assumptions

- The authoritative values and semantics come from `docs/CHOT_YEU_CAU.md`; the project constitution, clean-code rules, and PRD constrain consistency but do not override CHOT.
- The current `feature/002-identity-auth-rbac` branch was already active; no extension hook was configured or invoked, and the spec directory remains independently numbered.
- The existing project/API foundation supplies the versioned contract, shared error envelope, authenticated frontend transport, configuration, PostgreSQL integration-test foundation, correlation/payload-safety primitives, and safety filtering needed by this feature. Feature 002 creates the concrete audit/outbox ports and persistence ownership described in its plan.
- “Display exactly once” means the plaintext appears only in the successful create/reset response. It does not mean the generated password is a one-time or expiring login credential.
- Multiple simultaneous devices are permitted, but users do not manage a visible device/session list in this feature.
- Active state defaults to active for newly created users, consistent with the current authoritative user flow.
- Phone and email validation follows normal boundary validation when values are supplied; neither is used for login, password recovery, invitation, email, or SMS in this feature.

## Dependencies

- Project Constitution Principles I, III, IV, V, VI, VII, IX, XI, and XII, plus its Definition of Done.
- `docs/CHOT_YEU_CAU.md` §7 (User model), §8–§8.3 (canonical RBAC, implication, scope, and authorization order), §9.2–§9.2.2 (password, revocable authentication, and repeated-operation semantics), §9.7.1 (canonical authentication throttles), and §10 (canonical identity/user operations and mandatory tests), including R-110–R-112.
- `docs/QUY_TAC_CLEAN_CODE.md` §5 (RBAC and identity boundary rules) and §7 (mandatory acceptance coverage).
- `docs/phan_mem_web_cham_cong_va_quan_ly_cong_viec_helpdesk.md` §3.5 and §5 for stakeholder-facing user administration and role behavior.
- Feature `001-project-api-foundation`, whose contract, frontend transport, configuration, test, and delivery foundations this feature consumes.

## Out of Scope

- Creating Manager accounts through user-facing operations; Manager accounts remain provisioned only through controlled administrative seed/command paths outside this feature.
- Email invitation, SMS, email-based password recovery, one-time password login, social login, single sign-on, multifactor authentication, and user-visible session/device management.
- Blacklisting individual access credentials or promising immediate expiry after logout/reset/password change beyond the authoritative account-state gates.
- Attendance, task, location, configuration, holiday, photo, reporting, notification, and export business implementation; this feature defines and tests canonical action decisions, the closed implication map, and generic grant provenance only.
- Attendance record ownership enforcement is deferred to Feature 004; Feature 002 supplies only generic permission provenance.
- Task creator/assignee ownership and Task business-invariant enforcement are deferred to Feature 006; Feature 002 supplies only generic permission provenance.
- Changing the canonical role list, permission matrix, five implication pairs, access/refresh lifetimes, or the protected Manager-target policy.
