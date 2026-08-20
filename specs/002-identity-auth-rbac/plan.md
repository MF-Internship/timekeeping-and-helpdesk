# Implementation Plan: Identity, Authentication and Canonical RBAC

**Branch**: `002-identity-auth-rbac` (current Git branch: `feature/002-identity-auth-rbac`)

**Date**: 2026-08-18

**Spec**: [spec.md](./spec.md)

**Plan type**: Remediation of the existing Feature 002 design and implementation after specification analysis. This plan does not generate tasks or implement code.

## 1. Technical Context

Feature 002 already has an implemented vertical slice. Remediation must preserve the approved architecture and correct only demonstrated contract, ordering, locking, evidence, and verification gaps.

| Area | Existing baseline to reuse | Planned delta |
|---|---|---|
| Backend | Python 3.12, Django 5.2.5, DRF 3.16.1, SimpleJWT 5.5.1, psycopg 3.2.9 | No dependency change. Verify one canonical `SIMPLE_JWT` configuration and remediate application/adapter behavior in place. |
| Database | PostgreSQL 17; `identity.0001_initial`, `audit.0001_initial`, SimpleJWT blacklist tables | Treat existing migrations as deployed history. Any approved correction is additive `0002+`; do not edit or recreate `0001`. |
| Frontend | TypeScript 5.9, Next.js 16.3.1, React 19.1.1, `openapi-fetch`, one authenticated transport | Preserve the generated `schema.ts` / handwritten `client.ts` boundary and existing identity feature folders. |
| Audit/outbox | Feature 001/002 approved recorders and payload sanitizer | Reuse ports and adapters; do not create another append framework or transaction owner. |
| Testing | pytest/pytest-django, Vitest, real PostgreSQL suites, migration and architecture checks | Extend existing suites for missing precedence, both race orders, production revocation paths, controlled-time expiry, and scope exclusions. |
| CI | `.github/workflows/quality.yml`, `.github/workflows/contract.yml`, `scripts/check_all.sh` | Add only Feature 002 verification to existing gates. No new service or workflow family. |
| Scale and targets | About 50 internal users; p95 application target 500 ms; two-minute Manager user-admin usability criterion | Keep capacity/usability as operator evidence using existing tooling, not fabricated production evidence or a CI performance gate. |

Security constraints remain: access lifetime 15 minutes; refresh lifetime 7 days; refresh rotation and blacklist-after-rotation; no role/permission token claims; no access-token blacklist; refresh only in a host-only `Secure`, `HttpOnly`, `SameSite=Strict` cookie with canonical path; access only in memory; current User reloaded on every authenticated request; no plaintext generated password or token in persistence, logs, audit, outbox, URLs, or browser storage.

## 2. Constitution Check

| Gate | Result | Plan evidence / consequence |
|---|---|---|
| Authority chain | PASS | CHOT §9.2.2/§9.7.1 and R-110…R-112 now close logout idempotency, repeated-operation evidence, and numeric throttle semantics; QUY_TAC, PRD, spec and contracts are synchronized. |
| Ordered authorization | PASS | DRF authentication, action authorization, body-independent target authorization, forced-password gate, DTO validation, owning-module scope, business rules, transaction/constraints, and evidence are mapped explicitly below. |
| Server authority | PASS | Self identity comes from `request.user`; server-owned fields are rejected; frontend capabilities are presentation-only. |
| Database invariants | PASS | PostgreSQL owns uniqueness, checks, immutability, blacklist uniqueness, and aggregate-version uniqueness. Lock claims have corresponding PostgreSQL tests. |
| Atomic evidence | PASS | Business state, session revocation, AuditLog, and OutboxEvent join the caller's transaction where required. |
| Stable contracts | PASS | Existing `/api/v1/` namespace, canonical envelopes, OpenAPI, generated TypeScript schema, and drift/safety checks are reused. |
| Migration safety | PASS | Existing `0001` migrations are immutable; remediation is expand/migrate/contract-compatible and additive. |
| Module boundaries | PASS | Identity owns User and generic action decisions only; Attendance and Task object scope remain deferred. |
| Correct-layer proof | PASS | Pure policy uses unit tests; HTTP ordering uses API tests; locks, FKs, rollback, and constraints use real PostgreSQL. |

### Governance synchronization result

R-110 makes valid-access logout idempotent and actor-derived; R-111 defines no-op versus attributable repeated mutations; R-112 canonically approves the 10/120/5 authentication throttle scopes, keys, errors, shared cache and fail-closed behavior. No Feature 002 governance clarification remains open.

## 3. Scope / Out of Scope

### In scope

- User identity and account state.
- Login, refresh, logout, access/refresh lifecycle, rotation, and global revocation.
- First-password-change enforcement, self password change, generated initial/reset password display boundary.
- User list/read/create/profile update/role/status/reset administration.
- Canonical Role, PermissionAction, direct grants, exactly approved `PERMISSION_IMPLIES`, `PermissionDecision`, and `granted_by` provenance.
- Frontend capabilities, in-memory authentication state, forced-change routing, and user administration integration.
- Technical integration with existing audit/outbox, PostgreSQL locking, OpenAPI, migrations, and CI.

### Out of scope

- Attendance rows or `.self` ownership; Feature 004 owns them.
- Task rows, creator/assignee scope, or state transitions; Feature 006 owns them.
- Notification business delivery, reporting behavior, and outbox relay execution.
- Placeholder Task/Attendance models, endpoints, or test fixtures.
- Cross-module history-preservation tests against tables that do not yet exist.
- MFA, email/SMS delivery, access-token blacklist, new cache/broker/state-management infrastructure.

## 4. Module Ownership

| Module | Owns | Must not own |
|---|---|---|
| `identity.domain` | Role/action vocabularies, exact grants/implications, permission provenance, pure password/account rules | Django/DRF, token libraries, Task/Attendance ownership helpers |
| `identity.application` | Authentication, self-service, user-admin and query orchestration; transaction sequencing through ports | HTTP parsing/cookies, ORM models, concrete audit/session adapters |
| `identity.ports` | User, credential, session, UoW and evidence-facing protocols | Concrete Django/SimpleJWT behavior |
| `identity.adapters` | Django persistence, SimpleJWT/password adapters, DRF authentication/permissions/serializers/views | New business rules or future-module object scope |
| `audit` | Existing immutable AuditLog/OutboxEvent records, ports, persistence adapter | Identity business orchestration, independent transactions, relay behavior |
| `core` | Existing errors, correlation, cache alias, payload sanitizer | Business models or a second auth/audit subsystem |
| `config` | Composition root and framework settings/routes | Business decisions or service logic |
| `frontend/features/identity` | UI/session presentation and typed calls | Authoritative authorization decisions or token persistence |

Architecture checks must forbid Identity imports of Task/Attendance implementations and symbols named `is_task_creator`, `is_task_assignee`, `can_view_task`, `can_update_task`, or `owns_attendance`.

## 5. Request Authorization Pipeline

Every protected endpoint follows this order:

1. `DatabaseBackedJWTAuthentication` verifies the bearer access token, reloads User, and rejects invalid/expired access or inactive current state.
2. `CanonicalIdentityPermission.has_permission()` evaluates the declared action when the endpoint has one.
3. The same permission layer performs body-independent target authorization where required: existing Manager route targets on the four admin mutations. Logout derives actor only from authenticated access and does not authorize from its cookie.
4. The same permission layer applies `must_change_password` after action/target authorization. Change-password alone is exempt.
5. For the R-112 password-change scope, DRF throttle runs after authentication/permission/account gates and before serializer construction. Public login/refresh throttles run before their DTO/credential business evaluation.
6. The view instantiates the operation-specific serializer and validates route/filter/body syntax and server-owned fields.
7. Identity applies object scope it owns: authenticated self, global admin read, or route target. Payload authorization such as `ASSIGNABLE_ROLES` follows syntactic DTO parsing.
8. Application service enforces current business invariants, repeating Manager-target checks under the lock when TOCTOU is possible.
9. Caller-owned UoW plus PostgreSQL constraints commit state, session changes, audit, and outbox atomically.

Self operations (`logout`, `/me/`, `change-password`) are canonical authenticated-self/session operations and have **no invented PermissionAction**. Routes retain string identifiers so Django path conversion cannot validate an integer before action authorization. Route identifier parsing occurs in the view after permission gates.

### Operation pipeline matrix

| Operation | Authorization action | Target authorization | DTO validation | Object-scope owner | Business gate | Transaction / constraint | Audit / outbox | Concurrency lock | Primary tests |
|---|---|---|---|---|---|---|---|---|---|
| Login | Public; no RBAC action; 10/60s per canonical IP before DTO | None | Login serializer | Identity account lookup | Credentials and active state | User UoW; update `last_login`; issue session | No success event required | Lock User found by username through issuance | login service/API/throttle; login race suites |
| Refresh | Public cookie-credential operation; no RBAC action; 120/60s per canonical IP before credential evaluation | Cookie cryptographic owner precheck | Empty JSON boundary; reject JSON refresh | Identity session owner | Active, not forced-change; current unrevoked JTI | User UoW; blacklist old then issue rotated pair | No routine success event | Lock owner User; recheck token/state under lock | refresh/API/throttle/reuse/same-refresh races |
| Logout | N/A — authenticated self | None; refresh cookie never chooses actor or blocks logout | Empty serializer; JSON refresh rejected | Identity derives actor from access authentication | Forced-change gate | User UoW; always call global revoke and clear cookie; return `204` | One revocation audit/outbox only when count > 0; zero-count repeat has none | Lock actor User through revoke/evidence | logout idempotency/API/precedence + login/refresh races |
| GET `/me/` | N/A — authenticated self | None | None | Identity derives self from `request.user` | Forced-change gate | Read-only | None | None | self-profile/API precedence |
| PATCH `/me/` | N/A — authenticated self | None | Profile serializer; `user_id` and other server-owned fields rejected | Identity derives self from `request.user` | Forced-change; profile rules | User UoW + DB checks | Profile audit/outbox | Lock self User through state/evidence | self-profile/service/rollback |
| Change password | N/A — authenticated self; 5/60s per User after permission/account gates | None | Password-change serializer | Identity derives self from `request.user` | Sole forced-change exemption; current password and policy | User UoW; password state, revoke all, issue replacement last | Password-change; session-revoked evidence only for positive count | Lock self User from recheck through replacement issue | change-password/API/throttle/expiry/races |
| List/read users | `user.view` | Manager remains readable; no mutation guard | Filters or route-id after action/forced gates | Identity global admin-read scope | Forced-change | Read-only; deterministic query/pagination | None | None | query/API negative matrix |
| Create user | `user.manage` | No existing route target | Create serializer | Identity create scope | Forced-change; `ASSIGNABLE_ROLES` after DTO | Insert User; unique username; aggregate v1 | User-created audit/outbox | No pre-existing row; uniqueness serializes duplicate code path | create/API/duplicate race |
| Admin profile update | `user.manage` | Existing Manager rejected pre-DTO | Profile serializer | Identity route target | Forced-change; locked Manager recheck | Target User UoW + checks | Profile audit/outbox | Lock target User through evidence | target precedence/promotion race |
| Change role | `user.assign_role` | Existing Manager rejected pre-DTO | Role serializer | Identity route target | Forced-change; `ASSIGNABLE_ROLES`; locked recheck | Target User UoW + role check | Role audit/outbox | Lock target User through evidence | role API/promotion race |
| Activate/deactivate | `user.manage` | Existing Manager rejected pre-DTO | Status serializer | Identity route target | Forced-change; locked recheck; same-state is no-op; `true→false` revokes | Target User UoW; transition state + optional revoke | Transition status evidence; revocation evidence only when count > 0; same-state none | Lock target User through state/revoke/evidence | status API/races/repeated no-op |
| Reset password | `user.manage` | Existing Manager rejected pre-DTO | Empty serializer | Identity route target | Forced-change; locked recheck; generate random password | Target User UoW; hash + forced flag + revoke all | Reset + session-revoked evidence | Lock target User through revoke/evidence | reset/API/races; successive reset uniqueness |

## 6. Domain Design

- Preserve the closed `Role` and `PermissionAction` value sets from CHOT.
- `ROLE_PERMISSIONS` contains direct grants only. `PERMISSION_IMPLIES` contains exactly the five approved ordered pairs; tests fail on any extra or missing pair.
- `PermissionDecision` returns `requested_action`, `allowed`, and nullable `granted_by`; an implied grant reports the stronger direct action.
- `ASSIGNABLE_ROLES` is one shared pure policy used by create and change-role services.
- Password policy keeps approved minimum length, difference from username, and configured validators. Do not invent Unicode normalization or uniqueness for phone/email.
- Use `GeneratedPasswordDisplayResult` (or equivalent non-`repr` result). The value is a generated password whose **display** is one-time; it is not an OTP and has no special TTL.
- Pure account transitions distinguish same-state no-op from real activation/deactivation transitions according to R-111.

## 7. Application Services

Preserve cohesive services for login, refresh, logout, self profile, self password change, user queries, create, admin profile, role, status, and reset.

- Services receive typed DTOs and authenticated identifiers; they do not parse HTTP, cookies, or URL strings.
- Login and refresh issue only after acquiring the same User serialization lock used by revokers.
- Logout ignores cookie validity for authorization, locks the access-token actor, calls global revocation, and returns a zero-count or positive-count result according to R-110.
- Admin mutation services repeat Manager-target protection after `SELECT FOR UPDATE`.
- Self password change order is immutable: reverify under lock → update password/forced flag → revoke all old refresh sessions → append required evidence → issue the replacement pair last → commit.
- Reset, logout, and deactivation issue no replacement pair.
- A repeated authorized password reset is a new mutation with a new random password, new hash, forced-change state, revocation, and evidence.
- No service writes Task, Attendance, Reporting, or Notification state.

## 8. Ports

Reuse and refine existing typed protocols rather than introduce infrastructure:

- User repository: get by username/id, list filters, insert, and lock-by-id/username.
- Credential policy: verify/hash/generate without exposing plaintext beyond the display result.
- Session repository/service: validate cookie/JTI, issue pair, rotate, revoke all, and return safe counts/reasons only.
- UoW: caller-owned atomic boundary covering User, SimpleJWT blacklist, AuditLog, and OutboxEvent writes.
- Audit/outbox recorders: append to the ambient caller transaction; no internal `atomic()` or `on_commit()`.
- Dependency/container interfaces: framework-neutral typed surfaces available before concrete wiring.

Ports must not leak Django model instances across the application boundary or accept plaintext secrets in evidence payloads.

## 9. Adapters

- `DatabaseBackedJWTAuthentication` owns bearer parsing, exact authentication claims, User reload, and `INVALID_TOKEN` / `ACCOUNT_INACTIVE` mapping.
- `CanonicalIdentityPermission` owns pre-serializer action, body-independent Manager-target protection, then forced-password ordering. It does not parse or authorize from the logout cookie.
- Operation serializers own syntax and `SERVER_OWNED_FIELD`, but no action or target authorization.
- Views keep raw route IDs until permission gates complete, then validate/convert and call services.
- Django user/session repositories use `select_for_update` only inside caller UoWs.
- Existing `DjangoAuditRecorder` and outbox adapter sanitize then insert without opening another transaction.
- Composition is staged:
  - **Stage A, early**: change typed dependency/container definitions only.
  - **Stage B, late**: after service and adapter changes exist, update concrete repository/service/permission/audit/outbox wiring in `config/composition.py`.
- `config` remains wiring/settings/routes only; no business condition is moved there.

## 10. Data Model

### User

- `username`: required, unique, immutable after creation.
- `full_name`: required and nonblank.
- `phone`, `email`: nullable and non-unique; email syntax is API-validated when supplied.
- `role`: canonical closed value with a database check.
- `is_active`: canonical boolean with safe DDL default.
- `must_change_password`: canonical boolean with safe DDL default.
- Django password hash and framework-required identity fields remain persistence details; plaintext never persists.

### Session records

Reuse SimpleJWT `OutstandingToken` and `BlacklistedToken`. Its User relationship remains nullable with the vendor `SET_NULL` deletion policy; blacklist history remains attached to the outstanding-token row. Access tokens have no blacklist table or custom access-session model.

### AuditLog and OutboxEvent

- Keep the approved AuditLog shape exactly; `actor` uses the approved protective User FK and immutable database behavior.
- Keep unique `event_id`, positive aggregate version, and unique `(aggregate_type, aggregate_id, aggregate_version)` on OutboxEvent.
- Existing-User aggregate versions are allocated while that User row remains locked. Create inserts User first and writes version 1.

No Task, Attendance, Notification, Reporting, or Location table is added.

## 11. Migrations / DB Constraints

- `identity.0001_initial` and `audit.0001_initial` are deployed baseline migrations and must not be edited.
- Create an additive `0002+` only if a settled invariant is absent from the deployed schema.
- Preserve unique username, nonblank username/full_name, closed role, boolean defaults, username immutability trigger, AuditLog immutability, protective actor FK, outbox unique/check constraints, and required indexes.
- Keep one migration leaf per app. Do not change Feature 001 cache migration ownership.
- Do not add phone/email uniqueness or Unicode-normalization constraints.
- Migration tests use PostgreSQL and start from the prior Feature 001/Feature 002 graph as applicable; SQLite is not acceptable constraint evidence.

## 12. Authentication Token Lifecycle

- Keep one canonical `SIMPLE_JWT` block: access 15 minutes, refresh 7 days, rotation enabled, blacklist-after-rotation enabled, token blacklist app enabled, approved last-login behavior.
- Token claims are exactly approved authentication claims: `user_id`, `exp`, `jti`, `token_type`; no role, permissions, capabilities, or profile claims.
- Every authenticated request reloads User and checks `is_active`; `must_change_password` is applied later according to authorization precedence.
- Refresh cookie: host-only, no `Domain`, `Secure`, `HttpOnly`, `SameSite=Strict`, `Path=/api/v1/auth/`.
- Refresh never appears in JSON request/response, localStorage, sessionStorage, URL, logs, audit, or outbox.
- Login intentionally maps bad username/password to `INVALID_CREDENTIALS`; token failures use `INVALID_TOKEN`.
- Access is never blacklisted. Controlled-time tests prove valid immediately before expiry and invalid at/after expiry without wall-clock sleeps.
- R-112 adds DRF scopes using `core.cache.THROTTLE_CACHE_ALIAS`: login 10/60s per canonical client IP, refresh 120/60s per canonical client IP, and password change 5/60s per authenticated User.id. Over-limit is canonical `429 THROTTLED` with `Retry-After`; cache failure is fail-closed canonical `503 SERVICE_UNAVAILABLE`. Both stop before the application service and evidence ports.

## 13. Revocation Semantics

Four settled business sites invoke global refresh revocation under the User lock:

1. successful logout;
2. Manager password reset;
3. self password change;
4. account transition `is_active=true → false`.

Only self password change returns a replacement pair, and it revokes before issuing. Login/refresh are serialized with these revokers on the same User row.

Logout's credential boundary is explicit under R-110:

- valid bearer access identifies the actor; cookie state never selects or changes that actor;
- missing, malformed, expired, blacklisted, mismatched-owner, and active cookie cases all clear the cookie, call global revocation, and return `204`;
- positive revoke count appends exactly one aggregate revocation audit/outbox pair; zero count appends none and does not advance version;
- `401 INVALID_TOKEN` at logout applies to invalid access, while refresh endpoint token errors remain unchanged;
- logout globally revokes every outstanding refresh for the authenticated User and issues nothing.

Old access behavior remains independent from refresh revocation:

- logout: old access stays usable until expiry;
- reset: cryptographically valid old access is blocked by `PASSWORD_CHANGE_REQUIRED` until expiry;
- self password change: old access stays usable until expiry;
- deactivation: cryptographically valid old access is blocked immediately by `ACCOUNT_INACTIVE`.

Do not use `RefreshToken(cookie).blacklist()` as the complete logout behavior. R-111 makes same-state status and zero-live-session revocation no-ops; repeated reset remains attributable.

## 14. RBAC / Permission Provenance

- Action authorization is pure and centralized; no view/service role branching duplicates the policy.
- `PERMISSION_IMPLIES` must equal the approved five pairs exactly.
- A decision for `task.view.self` may be allowed with `granted_by=task.view.all`; this proves only action provenance.
- Identity must not decide Task creator/assignee or Attendance ownership.
- Feature 002 tests direct/effective matrices, denials, exact implication cardinality/content, and provenance only.
- Frontend receives effective capabilities as strings for presentation. Backend recomputes authority from the current User.

## 15. User Target Authorization

All four existing-user admin mutations—profile, role, status, reset—reject an existing Manager target before DTO validation. The service repeats that rule under the locked target row before mutation.

Create-user and change-role keep three distinct semantics:

- unknown role syntax → `400 VALIDATION_FAILED`;
- syntactically valid `MANAGER` outside `ASSIGNABLE_ROLES` → `403 PERMISSION_DENIED` after DTO parsing;
- a server-owned field in an otherwise eligible payload → `400 SERVER_OWNED_FIELD`.

Manager accounts remain readable. A nonexistent valid target is reported only after authentication, action authorization, forced-password gate, and route syntax validation. No hard-delete User endpoint is planned.

## 16. Transaction Boundaries

| Flow | Transaction start | Locked rechecks and writes | Issue/revoke point | Transaction end / invariant |
|---|---|---|---|---|
| Login | After syntactic DTO and candidate lookup | Lock User by username; recheck hash and active state; update last login | Issue OutstandingToken while lock held | Commit returns pair; invalid credentials roll back with no token |
| Refresh | After cryptographic cookie owner parse | Lock owner User; recheck active, forced state, expiry, JTI, and blacklist | Blacklist old then issue replacement | Commit exposes one valid rotation result |
| Logout | After permission/DTO gates | Lock access-token actor User; cookie does not gate or choose owner | Revoke all; append session evidence only for positive count | Commit leaves all preexisting refresh sessions revoked; zero-count call commits no evidence and returns `204` |
| Self password change | After DTO | Lock self; reverify current password/state; update hash/flag | Revoke all; append evidence; issue replacement last | Commit leaves exactly the replacement refresh live |
| Reset | After action/target/DTO | Lock target; recheck non-Manager; update hash/forced flag | Revoke all; append reset/revocation evidence | Commit exposes generated password display result, no new session |
| Deactivate | After action/target/DTO | Lock target; recheck non-Manager; set inactive | Revoke all; append state/revocation evidence | Commit blocks all authenticated requests immediately |
| Other User mutation | After all HTTP gates | Lock existing User and recheck target invariant | No token change unless specified | State + audit + outbox commit or roll back together |
| Create User | After action/DTO/payload authorization | Insert User; database resolves username race | No session | User + aggregate version 1 evidence commit atomically |

The recorder never owns a transaction. Failure after any append must roll back state, blacklist rows, AuditLog, and OutboxEvent together.

## 17. Concurrency / Lock Matrix

| Operation | Lock owner | Rows locked | Lock lifetime | Final invariant |
|---|---|---|---|---|
| Login issuance | Authentication service UoW | One `identity_user` selected by username; token rows written afterward | Before credential/current-state recheck through issue and commit | Login is linearizable with every global revoker |
| Refresh rotation | Authentication service UoW | Owner `identity_user`; submitted outstanding/blacklist state re-read | Before state/JTI recheck through blacklist-old, issue-new, commit | One submitted refresh has at most one winner |
| Logout | Authentication service UoW | Access-token actor `identity_user`; live token rows updated | Before global revoke through conditional evidence/commit | Every active session preceding logout in User-lock order is revoked; zero-count logout is evidence-free `204` |
| Reset | User-admin UoW | Target `identity_user`; live token rows updated | Before Manager/password recheck through state/revoke/evidence/commit | Issuance is either before reset and revoked, or after reset and must satisfy new credentials/state |
| Self password change | Self-service UoW | Self `identity_user`; live token rows updated | Before password recheck through revoke, replacement issue, evidence, commit | Exactly the newly issued replacement refresh remains live on success |
| Deactivation | User-admin UoW | Target `identity_user`; live token rows updated | Before target/state recheck through revoke/evidence/commit | Issuance before deactivation is revoked; issuance after lock order fails inactive check |
| Concurrent global revocation | Shared production revocation path | Same `identity_user`, then that User's token rows | Whole revocation/evidence transaction | All preexisting refresh sessions revoked; duplicate blacklist state impossible |
| Existing-User event append | Mutating service UoW | Aggregate `identity_user` held before `MAX(version)+1` and insert | Through all event inserts and commit | Unique, consecutive per-User versions |
| Manager-target mutation | Admin service UoW | Target `identity_user` | Before locked role recheck through mutation/evidence/commit | Promotion and mutation serialize; an existing Manager is never mutated |
| Duplicate username create | Database unique constraint | Unique username index conflict | Insert to commit/conflict | At most one User for a username |

Locks implement linearizability, not a permanent “revocation beats all future issuance” rule. For example, logout-first may be followed by a genuinely later successful login; mutation-first makes old-password login fail; deactivation-first makes issuance fail.

## 18. Audit / Outbox

Reuse `audit.ports.recording`, `audit.adapters.persistence.recording`, and `core.event_payload`.

Required attributable mutations are: user create; self/admin profile update; role change; status change; password reset; self password change; and successful global session revocation. Deactivation, reset, and self password change include both their user mutation and session-revocation evidence in one transaction. Logout records session revocation. Login and routine refresh do not add high-volume success events.

- Payloads contain consumer-minimal state and safe revocation reason/count only.
- Plaintext generated passwords, password hashes, access/refresh tokens, cookies, JTIs, and credentials are forbidden.
- Existing-User aggregate allocation occurs while the User lock is held; create starts at aggregate version 1 after insert.
- Add a real PostgreSQL proof that `AuditLog.actor` has the approved protective on-delete behavior.
- Verify the installed SimpleJWT OutstandingToken User `SET_NULL` relationship in migration/relationship tests; Feature 002 exposes no hard-delete User operation, so normal account lifecycle is deactivate/reactivate.
- Assert R-111 precisely: positive-count revocation creates one aggregate evidence pair; zero-count revocation creates none and does not advance version.

## 19. API Contracts

Preserve [contracts/api.md](./contracts/api.md), stable operation IDs, canonical trailing-slash shapes, error envelope, and `Cache-Control: private, no-store` on credential-sensitive responses.

The negative contract suite must assert HTTP status, `error_code`, full canonical response shape, and absence of forbidden persistence/evidence effects where relevant:

| Case | Expected settled result / gate |
|---|---|
| Bad login username/password | `401 INVALID_CREDENTIALS`; enumeration-resistant shape |
| Missing/malformed/expired access on protected endpoint | `401 INVALID_TOKEN` |
| Valid access for inactive current User | `401 ACCOUNT_INACTIVE` |
| Missing/malformed/expired/signature-invalid/revoked refresh on refresh endpoint | `401 INVALID_TOKEN` |
| Logout missing, invalid, mismatched, or revoked refresh with valid access | `204`; clear cookie; global revoke by actor; evidence only when count > 0 |
| Repeated same-state status | `200` current representation; no write/revoke/evidence/version |
| Authentication throttle exceeded | `429 THROTTLED` + `Retry-After`; no service/evidence side effect |
| Shared throttle cache unavailable | `503 SERVICE_UNAVAILABLE`; fail closed; no service/evidence side effect |
| Unauthorized actor with malformed body/filter/route ID | `403 PERMISSION_DENIED`; DTO not evaluated |
| HELPDESK + forced-change on Manager-only action | `403 PERMISSION_DENIED` |
| Authorized actor + forced-change on non-change operation | `403 PASSWORD_CHANGE_REQUIRED` |
| Existing Manager target + malformed/empty/server-owned body | `403 PERMISSION_DENIED` before DTO |
| Eligible target + server-owned field | `400 SERVER_OWNED_FIELD` |
| Syntactically valid but forbidden `MANAGER` role | `403 PERMISSION_DENIED` after DTO |
| Unknown role / invalid role, `is_active`, page/filter type, or email syntax | `400 VALIDATION_FAILED` |
| Authorized normal actor + malformed route ID | `404` after permission gates, before body validation |
| Forced-change actor + malformed route ID | `403 PASSWORD_CHANGE_REQUIRED` before route validation |
| Nonexistent valid target ID | `404` only after authentication/action/forced gates |
| Supplied self `user_id`, username mutation, or other server-owned property | `400 SERVER_OWNED_FIELD` when actor/target gates pass |
| Refresh injected into login/refresh/logout JSON | Rejected; never treated as credential input |
| Token/generated secret leakage in ordinary responses, logs, audit, outbox | No leaked value; safety check fails build/test if present |

Contract documentation cites R-110…R-112 and contains no provisional governance rows.

## 20. Frontend Integration

- Preserve `frontend/src/shared/transport/authenticated-fetch.ts` as the sole authenticated transport: relative `/api/v1/` only, `credentials: include`, in-memory bearer access, single-flight refresh, and at most one replay.
- Preserve generated `frontend/src/shared/api/schema.ts`; regenerate from OpenAPI and drift-check it.
- Preserve handwritten thin `frontend/src/shared/api/client.ts` around `authenticatedFetch`; do not label or overwrite it as generated.
- Reuse `frontend/src/features/identity/{api,model,ui}`. Keep existing state vocabulary (`loading`, `forced_change`, authenticated/inactive outcomes) unless a separately justified internal rename is planned.
- Bootstrap via refresh then `/me/`; stop/re-route correctly on inactive or forced-change outcomes.
- Capabilities hide/show presentation only. Backend action/target/scope decisions remain authoritative.
- Generated password exists only in the immediate create/reset display state and is cleared on dismissal, unmount, logout, or account switch.
- Static and runtime tests prohibit access/refresh storage in localStorage/sessionStorage and prohibit refresh/token values in URLs or analytics/log calls.

## 21. Error Precedence Matrix

| Earlier condition | Later competing condition | Required result | Owning DRF gate |
|---|---|---|---|
| Invalid/expired bearer access | Any RBAC/DTO condition | `401 INVALID_TOKEN` | Authentication class |
| Current User inactive | Any RBAC/DTO condition | `401 ACCOUNT_INACTIVE` | Authentication class after DB reload |
| Missing action grant | Forced-change and malformed DTO | `403 PERMISSION_DENIED` | Permission class action check |
| Existing Manager route target | Forced-change and malformed/server-owned DTO | `403 PERMISSION_DENIED` | Permission class target check |
| Action/target allowed, forced-change true | Malformed DTO or route ID | `403 PASSWORD_CHANGE_REQUIRED` | Permission class post-authorization gate |
| All permission gates pass | Server-owned field | `400 SERVER_OWNED_FIELD` | Operation serializer |
| All permission gates pass | Unknown role/type/email syntax | `400 VALIDATION_FAILED` | Operation serializer |
| DTO parses valid `MANAGER` | Role not assignable | `403 PERMISSION_DENIED` | Application payload authorization |
| Route target absent after gates | Body malformed | `404` | View route parsing/lookup before body serializer where applicable |
| Locked target became Manager | Otherwise valid mutation | `403 PERMISSION_DENIED`, rollback | Application locked recheck |
| Logout cookie missing or changes before lock | Otherwise valid logout | Cookie is non-authoritative; revoke by locked access-token actor and return `204` | Application service under User lock |

The `must_change_password` check never precedes action RBAC or applicable target authorization.

## 22. Test Strategy

### A. Pure domain/unit

- Exact Role/action grant matrix, all denials, exactly approved implication pairs, and `granted_by` provenance.
- Assignable roles, generated-password policy/display result, password rules, and settled pure account transitions.
- No Django/DRF imports in domain.

### B. Application/service

- Login, refresh, logout, self profile/password change, reset, activation/deactivation, create/update/role/query.
- Authorization precedence and payload authorization with fakes only where database behavior is not claimed.
- Revoke-before-issue and generated-secret payload minimization.
- Logout idempotency across all cookie states; positive/zero revoke-count evidence rules.

### C. PostgreSQL integration

- User checks/uniqueness/immutability/defaults; token persistence and blacklist reuse.
- AuditLog protective FK and immutability; atomic rollback after audit/outbox append.
- All race scenarios in section 23 using `django_db(transaction=True)`, real threads/workers/connections, deterministic barriers, persisted-state inspection, and no lock mocks.
- Migration compatibility and one-leaf checks.

### D. API contract

- Exact paths/statuses/error codes/envelopes/cookies/no-store, server-owned rejection, target precedence, and the full negative matrix in section 19.
- OpenAPI safety: no JSON refresh, no credential examples, login-only password input, generated-password response isolation.

### E. Architecture

- Identity has no Task/Attendance implementation imports or prohibited object-scope helper symbols.
- Domain is framework-free; adapters point inward; config alone performs concrete composition.
- Generated `schema.ts` and handwritten `client.ts` remain distinct.

### F. Frontend

- Login/bootstrap/logout state, forced-change routing, inactive handling, capabilities presentation, user-admin flows, generated-password clearing, generated-schema compatibility, and absence of token browser storage.

### Controlled-time access-expiry coverage

Parameterize logout, reset, self password change, and deactivation:

- access succeeds cryptographically immediately before 15-minute expiry and returns `INVALID_TOKEN` at/after expiry;
- logout and self password change leave old access usable before expiry;
- reset leaves it cryptographically valid but API-blocked by `PASSWORD_CHANGE_REQUIRED`;
- deactivation leaves it cryptographically valid but API-blocked by `ACCOUNT_INACTIVE`.

Use SimpleJWT time controls/patching, not sleeps.

## 23. PostgreSQL Race Test Matrix

Every A–H pair must run with both lock orders. Existing issuance-first tests are reused and extended with revocation/mutation-first cases.

| Race pair | Rows locked | Expected serialization | Final invariant | PostgreSQL test |
|---|---|---|---|---|
| A. Login vs logout | Same `identity_user`; that User's token rows | Login-first: issued refresh then logout revokes it. Logout-first: later login may validly create a new session. | Outcome is linearizable; logout does not block genuinely later login. | `identity/test_login_vs_logout.py` |
| B. Login vs reset | Same User and token rows | Login-first session is revoked; reset-first makes old-password login fail. | No session contradicts serialized password state. | `identity/test_login_vs_password_reset.py` |
| C. Login vs self password change | Same User and token rows | Login-first session revoked; change-first makes old-password login fail. | Replacement/change semantics match lock order. | `identity/test_login_vs_self_password_change.py` |
| D. Login vs deactivation | Same User and token rows | Login-first session revoked; deactivate-first login fails active recheck. | Inactive User has no usable refresh and cannot issue. | `identity/test_login_vs_deactivation.py` |
| E. Refresh vs logout | Same User, submitted/live token rows | Refresh-first replacement revoked; logout-first old submitted refresh fails locked recheck. | No pre-logout-order refresh remains usable. | `identity/test_refresh_vs_logout.py` |
| F. Refresh vs reset | Same User, submitted/live token rows | Refresh-first replacement revoked; reset-first refresh fails forced/session recheck. | No refresh survives inconsistent reset order. | `identity/test_refresh_vs_password_reset.py` |
| G. Refresh vs self password change | Same User, submitted/live token rows | Refresh-first replacement revoked; change-first old refresh fails. | Only change-password replacement remains live when change wins. | `identity/test_refresh_vs_self_password_change.py` |
| H. Refresh vs deactivation | Same User, submitted/live token rows | Refresh-first replacement revoked; deactivate-first refresh fails active recheck. | Inactive User has no usable refresh. | `identity/test_refresh_vs_deactivation.py` |
| I. Global revoke vs global revoke | Same User and all live token rows | One production revocation service waits for the other; conflict-safe blacklist writes. | All preexisting refresh revoked; no duplicate blacklist rows; exactly one positive-count evidence pair, later zero-count caller creates none. | Strengthen `identity/test_concurrent_global_revocation.py` to exercise production service/helper |
| J. Per-User outbox version allocation | Same aggregate User plus outbox unique key | Second mutation waits, then observes next committed version. | Unique consecutive per-User aggregate versions. | `audit/test_aggregate_version_concurrency.py` |
| Same refresh vs same refresh | Same User and submitted token state | One rotation consumes old JTI before the other recheck. | At most one rotation winner. | `identity/test_refresh_rotation_concurrency.py` |
| Manager promotion vs admin mutation | Same target User | Promotion/mutation serialize; locked guard re-evaluates role. | Existing Manager is never mutated by Manager admin route. | `identity/test_manager_target_concurrency.py` |
| Duplicate username create | Unique username index | One insert commits, competing insert conflicts. | Exactly one User; canonical loser result. | `identity/test_concurrent_user_create.py` |

Race harnesses must synchronize workers at the actual lock boundary, use separate database connections, prove both workers genuinely compete, inspect final User/token/audit/outbox state, and avoid mocked `select_for_update`. No concurrency guarantee is claimed beyond these tests.

## 24. Migration Compatibility

- Preserve N-1 runtime compatibility: old code must tolerate additive Identity/Audit schema; new code must run after migrations.
- Use expand → migrate/backfill if needed → contract in a later approved release. No destructive contraction belongs in this remediation.
- Any new required non-null field uses nullable/default expansion and backfill before constraint tightening.
- Static migration checks enforce no destructive operation, one leaf per app, and approved app ownership.
- PostgreSQL `MigrationExecutor` tests cover the prior graph to current graph, constraints/triggers/indexes, and safe reversibility only where governance permits.
- No Task/Attendance tables and no changes to operations-owned cache migrations.

## 25. CI / Verification

Reuse existing gates:

- backend Ruff, mypy, maintainability/architecture checks;
- pure and application tests;
- API/contract/schema safety and drift tests;
- real PostgreSQL integration and race suites;
- migration static checker and migration compatibility;
- frontend format/lint/type/Vitest/build;
- generated OpenAPI and `schema.ts` compatibility, while statically checking handwritten `client.ts`.

Do not create another CI workflow or database/cache service. Add controlled-clock/shared-cache tests for R-112 to existing suites. Real capacity runs remain operator evidence under `specs/002-identity-auth-rbac/evidence/` using existing Feature 001 capacity tooling; they do not become a CI gate or a claim of production performance. The two-minute user-admin criterion is verified by a documented usability script/session, not inferred from unit tests.

## 26. Deferred Requirements / Future Feature Ownership

| Deferred item | Owner / next action |
|---|---|
| Attendance `.self` ownership and history preservation | Feature 004; use generic permission provenance, implement and integration-test scope there |
| Task creator/assignee scope and transitions | Feature 006; no Identity helper or placeholder model |
| Task/Attendance/Reporting preservation on User deactivation | Owning future features; Feature 002 proves no cross-module destructive writes and protective Identity/Audit relationships only |
| Notification business behavior and outbox delivery/retry | Future owning feature / infrastructure plan |
| Production capacity/environment readiness | Operator/environment-readiness evidence, not Feature 002 CI |

## 27. Implementation Dependency Order

Tests required by the Constitution precede the code they constrain. This is remediation ordering, not a generated task list:

1. Use synchronized R-110…R-112 contracts as the baseline; no further governance decision is required for G1–G3.
2. Correct pure domain expectations for exact actions, implications, provenance, assignable roles, and generated-password terminology.
3. Add/adjust failing User schema and migration compatibility tests against the deployed `0001` baseline.
4. Remediate User persistence only if a settled invariant is missing; use additive migrations.
5. Refine token/revocation and UoW ports, including positive/zero revoke-count results and actor-derived logout.
6. Add authentication service tests for token claims, cookie boundary, revoke-before-issue, and controlled-time access behavior.
7. Remediate authentication services without changing approved dependencies.
8. Add failing authorization precedence tests for authentication → action → target → forced gate → DTO.
9. Remediate DRF authentication/permission/view placement; keep serializers free of action authorization.
10. Add user-admin service/API tests for target Manager protection, payload authorization, server-owned fields, and repeated reset.
11. Remediate user-admin/self services with locked target rechecks and atomic evidence.
12. Extend PostgreSQL race tests to both lock orders for A–H; add production-service proof for I and preserve J.
13. Remediate User-row serialization and idempotent actor-derived logout until all settled race invariants pass.
14. Add/adjust audit/outbox atomicity, payload-safety, FK-protection, and aggregate-version tests.
15. Remediate audit/outbox integration by reusing existing ports/adapters; do not duplicate infrastructure.
16. Remediate API serializers/views/contracts and the complete negative matrix.
17. Update concrete `config` composition only after service and adapter surfaces exist.
18. Regenerate OpenAPI and `frontend/src/shared/api/schema.ts`; keep `client.ts` handwritten and thin.
19. Remediate frontend session, forced-change, inactive, capabilities, admin, and generated-password flows.
20. Run contract, architecture, migration, lint/type, frontend, PostgreSQL, and CI-equivalent verification.
21. Capture non-CI usability/capacity evidence where applicable; do not fabricate environment results.

Concrete composition is intentionally late. Task/Attendance placeholders, new dependencies, or a second cache subsystem are not authorized by this plan.
