# Phase 0 Research: Identity, Authentication and Canonical RBAC

All technical-context questions are resolved. Decisions follow `CHOT_YEU_CAU.md`; R-decisions below are cited only as history/rationale.

## Authority trace and controlling decisions

**Decision**: Use CHOT §7, §8–§8.3, §9.2–§9.2.1, §9.4, and §10 as the controlling business/contract source; apply Constitution Principles I–IX/XI/XII and QUY_TAC §3/§5/§7 as mandatory architecture/test rules. Relevant accepted rationale is R-57, R-60–R-72, R-75, R-76, R-78, R-80, R-81, R-87, R-90–R-92, R-103, and R-104.

**Rationale**: These sections collectively settle role grants, target protection, validation order, user fields, token/session behavior, audit/outbox transactionality, API shape, scale, password policy, and generated-contract behavior. No current-source conflict remains.

**Alternatives considered**:

- Treating RA_SOAT as a source of new rules: rejected by Constitution Principle I.
- Inferring behavior from feature-001 code: rejected because that feature deliberately excluded identity and business persistence.

## Business-module ownership

**Decision**: Create `backend/identity/` for User/authentication/RBAC/user administration and `backend/audit/` for AuditLog/OutboxEvent plus append ports. Keep `backend/core/` non-app and `backend/operations/` operational-only. Cross-module callers use `audit.ports.recording`; `config.composition` wires concrete adapters.

**Rationale**: Identity is the first owned business module. Audit/outbox is cross-cutting business persistence required by R-104 and future features; placing it inside identity would force later modules to import identity internals, while core may not own persistence and operations has explicitly limited ownership. Two cohesive modules preserve inward dependencies and reuse the established app/architecture gates.

**Repository finding**: Feature 001 supplies correlation and payload-safety primitives but explicitly deferred AuditLog, OutboxEvent, and append ports. The feature-spec dependency statement is therefore implemented as reuse of those primitives plus creation of the concrete R-104 ports/models in feature 002; the plan does not pretend nonexistent ports already exist.

**Alternatives considered**:

- Put AuditLog/OutboxEvent in identity: rejected as semantically wrong and a future cross-module dependency trap.
- Put them in core: rejected because core is not a Django app and must own no persistence/business rules.
- Put them in operations: rejected because feature 001 limits operations to operational adapters/cache provisioning.
- Add separate audit and outbox apps: rejected for this phase because R-104 deliberately couples their append transaction/safety boundary; one supporting module is sufficient until relay behavior is implemented.

## Authentication dependency and integration

**Decision**: Add only `djangorestframework-simplejwt==5.5.1`, enable its blacklist app, and wrap its token primitives in identity ports/adapters instead of exposing stock views. Keep the five CHOT settings in one `SIMPLE_JWT` block.

**Rationale**: CHOT names SimpleJWT and requires outstanding/blacklisted server state. Version 5.5.1 is the latest published stable release found during planning and declares Python 3.12 and Django 5.2 support, matching the pinned repository stack. Custom adapters are necessary for cookie-only refresh, exact canonical errors/claims, row-lock serialization, and global revocation. Sources: [PyPI package metadata](https://pypi.org/project/djangorestframework-simplejwt/) and [SimpleJWT blacklist/rotation documentation](https://django-rest-framework-simplejwt.readthedocs.io/en/stable/blacklist_app.html).

**Alternatives considered**:

- Stateless refresh JWT: rejected because it cannot support authoritative revocation.
- Django session-only auth: rejected by CHOT's mobile/API decision.
- Handwritten JWT/blacklist implementation: rejected because CHOT selects SimpleJWT and duplication increases security risk.
- Stock SimpleJWT obtain/refresh views: rejected because they expose JSON refresh semantics and do not enforce the project-specific cookie, error, state, revocation, and locking contract.

## Custom User model

**Decision**: Define `identity.User` from `AbstractBaseUser`, with only the canonical business fields plus the inherited password hash/last-login support; configure it as `AUTH_USER_MODEL` before enabling Django auth migrations. Do not use Django Group/Permission or a superuser bypass in API authorization.

**Rationale**: The project currently has no auth app or stock user migration, so this is the safe point to establish the custom model. AbstractBaseUser supplies secure password hashing without adding competing role/permission behavior. API Manager provisioning remains forbidden; controlled seed/management provisioning is outside this feature's public contract.

**Alternatives considered**:

- `AbstractUser`: rejected because its Group/Permission/is_staff behavior invites a second authorization source and adds noncanonical user-admin fields.
- A profile table beside stock auth_user: rejected because username/active/password identity would be split across two sources and stock user has not been adopted.
- Deferring the custom User: rejected because later replacement after auth migrations would be destructive and incompatible.

## Authorization decision and permission-provenance foundation

**Decision**: Store Role, PermissionAction, direct grants, `ASSIGNABLE_ROLES`, and exactly five implications in pure identity domain code. Return a permission decision containing the direct `granted_by` action; expose effective capability strings for the frontend and future scope policies.

**Rationale**: A boolean alone cannot distinguish Helpdesk's direct self grant from Manager's implied all/any grant, which CHOT §8.1 requires for correct object scope. Grant provenance lets later Task/Attendance modules filter creator/assignee only when the effective source requires it, without embedding scope in middleware.

**Alternatives considered**:

- Hierarchical role inheritance: rejected because PERMISSION_IMPLIES is closed and action-specific.
- Put the policy in core: rejected because RBAC is business policy.
- Put scope rules directly in DRF permissions: rejected because object scope belongs after DTO validation and inside each owning business module/query.
- Encode role/capabilities in JWT: rejected because role changes must apply at the next request.

## Authorization and validation order

**Decision**: Authentication loads current User; required action and body-independent Manager-target checks run first in ordered permission adapters; the forced-password gate runs only after those authorization checks and before serializer construction; serializers then reject server-owned fields/validate types; application services then apply payload authorization, owning-module scope/business rules, and the UoW.

**Rationale**: This exactly realizes CHOT §8.2, R-72, and R-87 while preventing forced-password state from masking an action denial. The target guard can inspect the route target without parsing body, whereas `role=MANAGER` in a create/role DTO must be parsed before policy evaluation. The same target rule is rechecked under lock solely to preserve the already-decided authorization invariant against races.

**Alternatives considered**:

- Serializer role checks: rejected because unauthorized actors would receive schema details first.
- One multipurpose serializer/viewset PATCH: rejected because field ownership, action selection, and target rules become ambiguous.
- Middleware-only action checks: rejected because endpoints require exact method/action and object-target behavior.

## Token claims, cookies, and client storage

**Decision**: Access and refresh JWT claims are exactly `user_id`, `exp`, `jti`, and `token_type`; remove SimpleJWT's noncanonical `iat` claim. Return access in JSON, refresh only in a host-only Secure/HttpOnly/SameSite=Strict cookie with Path `/api/v1/auth/`, and store access only in frontend memory.

**Rationale**: This preserves immediate database-backed role/account changes, blocks JavaScript access to refresh, and follows CHOT's explicit claim/storage contract. The existing same-origin proxy and `credentials: include` transport already support the cookie path.

**Alternatives considered**:

- Put both credentials in JSON/localStorage: rejected for token-exfiltration risk and direct conflict with CHOT.
- Put access in an HttpOnly cookie: rejected because CHOT selects in-memory bearer access and cookie refresh.
- Add a session-version claim/table: rejected because no approved model/claim exists; User-row locking plus blacklist state provides the required concurrency behavior.

## Session issuance, revocation, and concurrency

**Decision**: All login issuance, refresh rotation, password-change replacement, and the four global-revocation flows acquire the affected User row in a caller-owned transaction. Rotation/revocation rechecks current account and blacklist state after locking. Revocation bulk-creates missing blacklist rows conflict-safely and never issues a replacement except after self password change.

Logout is a protected dual-credential operation: it requires a valid bearer access credential and a valid, unrevoked refresh cookie owned by that same current User. A missing, malformed, expired, mismatched-user, or already-blacklisted refresh cookie uses the existing `INVALID_TOKEN` result and performs no global revocation or success audit/outbox append.

**Rationale**: A shared row lock provides one serial order without a new coordination table. If refresh wins first, its replacement is outstanding before the revoker scans and is revoked; if revocation wins, refresh observes blacklist/new state and fails. The same lock prevents reset/deactivation from racing issuance.

**Alternatives considered**:

- Scan outstanding tokens without coordinating issuance: rejected because a new refresh token can appear after the scan.
- Add per-user session generation/version: rejected because CHOT does not define the field or claim and blacklist tables already exist.
- Global advisory lock: rejected as broader and less explicit than the existing User aggregate.
- Blacklist only the submitted token on logout: rejected explicitly by CHOT.

## Manager-target concurrency

**Decision**: Run the Manager-target guard once before DTO validation for correct 403 precedence and again after `SELECT FOR UPDATE` inside the mutation UoW. All role/profile/status/reset mutations lock the same target row.

**Rationale**: The precheck satisfies the externally visible pipeline; the locked recheck prevents a concurrent role promotion from turning an eligible target into Manager between check and write. It is the same invariant, not a new validation stage.

**Alternatives considered**:

- Precheck only: rejected due to time-of-check/time-of-use exposure.
- Lock before action permission: rejected because it performs unnecessary target database work for actors who lack the action and complicates authorization order.
- Optimistic version field: rejected because User has no authoritative version field and row-level contention is tiny at 50 users.

## Transaction, audit, and outbox design

**Decision**: Application services own one UoW through a port. User/blacklist mutations and AuditLog/OutboxEvent inserts share it. Append adapters validate with `core.event_payload` before insert, read ambient correlation for OutboxEvent, and never own `atomic()` or `on_commit()`.

**Rationale**: This is the exact R-104 unit-of-work promise and reuses the existing sanitizer/correlation foundation. The audit/outbox supporting module provides stable ports for later publishers. Events remain durable PENDING records; relay/transport is R-105 scope and is not implemented here.

**Alternatives considered**:

- Audit in each view after the service: rejected because response errors could leave mutation without evidence or evidence without mutation.
- `transaction.on_commit()` event creation: rejected because the event would not be part of the same atomic outcome.
- Implement relay now: rejected because identity has no delivery-dependent consumer and the user forbids unrelated infrastructure/dependencies.

## Database constraints, indexes, and immutability

**Decision**: Enforce username uniqueness, closed role, nonblank username/full_name, positive outbox aggregate version, event/aggregate uniqueness, and valid publish state in PostgreSQL. Use triggers to reject username updates and AuditLog update/delete. Add only query-backed indexes: unique username, AuditLog actor/time and target/time, and OutboxEvent pending/time; rely on fixed-size scans for the 50-user directory.

**Rationale**: These are the final protections for immutable/security invariants. Search uses contains matching on at most ~50 rows; a trigram dependency/index is unnecessary. Explicit audit/outbox indexes support evidence lookup and later ordered pending reads without speculative infrastructure.

**Alternatives considered**:

- Service-only immutability: rejected because commands/adapters could bypass it.
- Case-insensitive username index: rejected because CHOT says unique but does not define case folding; silently adding it changes identity semantics.
- Trigram/full-text search: rejected at the accepted scale and because it adds extension/index complexity.

## Generated password handling

**Decision**: Generate with `secrets.token_urlsafe`, loop until pure and configured password validation passes, hash immediately, and return through a non-repr `GeneratedPasswordDisplayResult` serialized only by create/reset responses as `generated_password`. Never store plaintext or place it in audit/outbox/error/log state.

**Rationale**: One shared helper prevents create/reset drift. A dedicated response schema avoids contaminating ordinary User schemas. Exact-key filtering permits legitimate `must_change_password` while forbidding `password` at safety boundaries.

**Alternatives considered**:

- Let Manager enter a password: rejected by CHOT.
- Store encrypted/recoverable plaintext: rejected because display is exactly once and loss requires reset.
- Treat it as OTP/TTL credential: rejected by R-70/CHOT.

## User listing and pagination

**Decision**: Use one page-number list with fixed server page size, optional `q`, `role`, `is_active`, and stable ordering by full_name/username/id. No default active filter and no picker endpoint.

**Rationale**: This directly implements R-81 and CHOT §10. Fixed ordering prevents page drift for stable data; the task picker will reuse the same endpoint later with explicit filters. Page size remains server-owned.

**Alternatives considered**:

- Separate lightweight picker endpoint: rejected explicitly.
- Default `is_active=true`: rejected because deactivated users must remain administrable.
- Cursor pagination/page_size: rejected by the canonical v1 contract for this directory.

## Frontend authentication state

**Decision**: Use a small plain in-memory session store plus React context/provider; extend the existing authenticatedFetch with bearer injection, a single shared refresh promise, and at most one replay. Use typed wrappers over the handwritten thin shared client and generated schema, with local component state for forms/password dialog. Add no frontend dependency.

**Rationale**: The current project already centralizes all authenticated traffic in one transport and has React, generated OpenAPI types, canonical errors, and AsyncState. A new state/query library is unnecessary for three screens and 50 users. Single-flight refresh prevents a burst of expired requests from rotating one cookie multiple times.

**Alternatives considered**:

- Persist access in localStorage/sessionStorage: rejected by CHOT.
- Add Redux/Zustand/React Query/Axios: rejected as unapproved and unnecessary.
- Refresh independently per failed request: rejected because rotation makes concurrent reuse fail and can create retry storms.

## Canonical path preservation through the frontend proxy

**Decision**: Update the existing Next.js rewrite destination to preserve the incoming path rather than append `/` unconditionally. Register backend routes with the exact CHOT shapes and test slashless auth/change-password alongside slashed self/user routes.

**Rationale**: The current foundation rewrite ends every destination with `/`, while CHOT §10's auth and change-password paths do not. Relying on Django redirect behavior for POST risks body loss/rejection and makes generated paths differ from runtime proxy paths. Path preservation reuses the same proxy/middleware and changes no namespace or infrastructure.

**Alternatives considered**:

- Normalize every new endpoint to trailing slash: rejected because it changes the authoritative v1 paths.
- Depend on APPEND_SLASH/redirects: rejected for unsafe POST semantics and contract drift.
- Add duplicate slash/no-slash routes: rejected because one operation would have two public contracts.

## API/error/contract evolution

**Decision**: Add the identity endpoint contract under `/api/v1/`, explicit operation IDs, canonical error codes/messages, bearer security scheme, and response schemas. Regenerate OpenAPI and TypeScript; extend safety/drift/compatibility tests. Permit the canonical exact `password` property only in the login request schema, use `generated_password` only in create/reset success, and never expose a JSON `refresh_token` or credential example.

**Rationale**: This reuses the feature-001 generation pipeline and respects R-103. CHOT requires login to accept `password`, so the foundation scanner must distinguish an authorized structural input name from a forbidden secret value; its current whole-document payload-filter call is too broad for an auth contract. New paths and response fields are additive, and distinct schemas make field ownership and the exactly-once secret boundary inspectable.

**Alternatives considered**:

- Hand-edit OpenAPI/client: rejected by constitution and CI.
- Omit/rename the login password field solely to satisfy the old scanner: rejected because it would violate the canonical API.
- Put refresh in request/response schema: rejected by the cookie-only contract.
- Model Role/capabilities as schema enums: rejected because CHOT requires open strings to keep additions nonbreaking.

## Migration and CI evolution

**Decision**: Add identity/audit as explicit approved local persistence owners, retain one leaf per app, test migration from feature-001 state on PostgreSQL, and expand existing quality/contract jobs rather than adding a workflow or infrastructure service.

**Rationale**: Feature-001 allowlists intentionally reject every business app until owned. Feature 002 now owns exactly identity and audit, so the checks must become policy-aware rather than be bypassed. All changes are additive and N-1 code ignores the new tables.

**Alternatives considered**:

- Disable or exclude architecture/migration checks: rejected because that removes the governing safety gate.
- Put all migrations in operations to satisfy the old allowlist: rejected as false ownership.
- Add a new CI workflow/job/database: rejected because existing jobs and PostgreSQL service already exercise every required layer.
