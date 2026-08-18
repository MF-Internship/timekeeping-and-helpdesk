# Phase 0 Research: Identity, Authentication and Canonical RBAC

Technical context, repository-pattern questions, and the three former governance gaps are resolved. Decisions follow `CHOT_YEU_CAU.md`; R-decisions below are cited as accepted rationale. R-110…R-112 are synchronized into CHOT §9.2.2/§9.7.1, PRD, QUY_TAC, spec and contracts.

## Authority trace and controlling decisions

**Decision**: Use CHOT §7, §8–§8.3, §9.2–§9.2.2, §9.4, §9.7.1, and §10 as the controlling business/contract source; apply Constitution Principles I–IX/XI/XII and QUY_TAC §3/§5/§7 as mandatory architecture/test rules. Relevant accepted rationale is R-57, R-60–R-72, R-75, R-76, R-78, R-80, R-81, R-87, R-90–R-92, R-103, R-104, and R-110–R-112.

**Rationale**: These sections settle role grants, target protection, validation order, user fields, token/session flows including idempotent logout and repeated operations, audit/outbox transactionality, throttle limits/failures, API shape, scale, password policy, and generated-contract behavior. No Feature 002 governance ambiguity remains.

**Alternatives considered**:

- Treating RA_SOAT as a source of new rules: rejected by Constitution Principle I.
- Inferring behavior from feature-001 code: rejected because that feature deliberately excluded identity and business persistence.

## Business-module ownership

**Decision**: Preserve the existing `backend/identity/` owner for User/authentication/RBAC/user administration and `backend/audit/` owner for AuditLog/OutboxEvent plus append ports. Keep `backend/core/` non-app and `backend/operations/` operational-only. Cross-module callers use `audit.ports.recording`; `config.composition` wires concrete adapters.

**Rationale**: Identity is the first owned business module. Audit/outbox is cross-cutting business persistence required by R-104 and future features; placing it inside identity would force later modules to import identity internals, while core may not own persistence and operations has explicitly limited ownership. Two cohesive modules preserve inward dependencies and reuse the established app/architecture gates.

**Repository finding**: Feature 001 supplied correlation and payload-safety primitives; the current Feature 002 implementation already supplies the concrete R-104 ports/models. Remediation reuses both layers and does not create a second audit/outbox append system.

**Alternatives considered**:

- Put AuditLog/OutboxEvent in identity: rejected as semantically wrong and a future cross-module dependency trap.
- Put them in core: rejected because core is not a Django app and must own no persistence/business rules.
- Put them in operations: rejected because feature 001 limits operations to operational adapters/cache provisioning.
- Add separate audit and outbox apps: rejected for this phase because R-104 deliberately couples their append transaction/safety boundary; one supporting module is sufficient until relay behavior is implemented.

## Authentication dependency and integration

**Decision**: Reuse the already pinned `djangorestframework-simplejwt==5.5.1` and enabled blacklist app, and preserve its identity ports/adapters instead of exposing stock views. Verify the CHOT settings remain in one canonical `SIMPLE_JWT` block; do not add a dependency or a second token configuration.

**Rationale**: CHOT names SimpleJWT and requires outstanding/blacklisted server state. Repository inspection confirms version 5.5.1, the blacklist application, 15-minute/7-day lifetimes, rotation, blacklist-after-rotation, and update-last-login already exist in `backend/config/settings.py`. Remediation therefore verifies and corrects behavior in place rather than proposing new infrastructure.

**Alternatives considered**:

- Stateless refresh JWT: rejected because it cannot support authoritative revocation.
- Django session-only auth: rejected by CHOT's mobile/API decision.
- Handwritten JWT/blacklist implementation: rejected because CHOT selects SimpleJWT and duplication increases security risk.
- Stock SimpleJWT obtain/refresh views: rejected because they expose JSON refresh semantics and do not enforce the project-specific cookie, error, state, revocation, and locking contract.

## Custom User model

**Decision**: Preserve the existing `identity.User` based on `AbstractBaseUser`, with only the canonical business fields plus inherited password hash/last-login support and `AUTH_USER_MODEL` configured before Django auth migrations. Do not add Django Group/Permission or a superuser bypass to API authorization.

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

**Decision**: All login issuance, refresh rotation, password-change replacement, and the four global-revocation flows acquire the affected User row in a caller-owned transaction. Refresh rechecks current account and blacklist state after locking. Logout derives actor only from access authentication, never gates on refresh-cookie validity, and invokes global revocation after acquiring that actor's User lock. Revocation bulk-creates missing blacklist rows conflict-safely and never issues a replacement except after self password change.

Logout is an authenticated-self operation whose actor comes only from valid access. Under R-110, missing, malformed, expired, mismatched-owner, revoked, and active refresh-cookie cases all clear the cookie, invoke global revocation for that actor, and return `204`. Positive revoke count appends one aggregate evidence pair; zero count is an idempotent no-op with no version advance.

**Rationale**: A shared row lock provides one serial order without a new coordination table. If issuance wins first, the later revoker observes and revokes its refresh; if the mutation/revoker wins, later issuance rechecks the resulting session/account/credential state. A genuinely later login after logout remains allowed. Tests must prove both lock orders rather than generalizing from issuance-first coverage.

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

## Authentication throttling

**Decision**: Apply R-112: login 10/60s per canonical client IP, refresh 120/60s per canonical client IP, and password change 5/60s per authenticated User.id. Use only `core.cache.THROTTLE_CACHE_ALIAS`; return canonical `429 THROTTLED` with `Retry-After`, or fail closed with canonical `503 SERVICE_UNAVAILABLE` when storage is unavailable.

**Rationale**: CHOT §9.7.1 now provides implementation authority for the rates previously present only in R-109, while preserving its shared-cache topology. IP keys cover public login/refresh attempts even when no trustworthy User exists; authenticated User.id scopes password change. Fail-closed preserves the security boundary without a second cache or dependency.

## Repeated operation semantics

**Decision**: Apply R-111. Same-state status returns `200` without write/revoke/evidence/version. Zero-session global revocation succeeds with count zero and no evidence/version. Logout repeats return `204` under R-110. Every authorized password reset remains a new mutation and generated-password display with reset evidence; revocation evidence is conditional on positive count.

**Rationale**: Evidence now corresponds to a committed state transition or deliberate reset, rather than a no-op API call. Each committed OutboxEvent advances the User aggregate version exactly once; no-op calls create no artificial gaps.

## Existing composition, migrations, and CI

**Decision**: Treat `identity.0001_initial` and `audit.0001_initial` as deployed baseline, retain one leaf per app, use forward additive `0002+` only for an approved missing invariant, and reuse existing quality/contract jobs. Change typed container/interfaces before changing concrete `config.composition` wiring.

**Rationale**: Repository inspection confirms both initial migrations, composition root, PostgreSQL suites, migration checker, generated-schema tooling, and CI jobs already exist. A remediation plan must not edit historical migrations, build concrete wiring before dependencies, or propose infrastructure already present. Any schema delta follows N-1 expand/migrate/contract compatibility.

**Alternatives considered**:

- Disable or exclude architecture/migration checks: rejected because that removes the governing safety gate.
- Put all migrations in operations to satisfy the old allowlist: rejected as false ownership.
- Add a new CI workflow/job/database: rejected because existing jobs and PostgreSQL service already exercise every required layer.
