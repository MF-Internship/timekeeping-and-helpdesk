# Implementation Plan: Identity, Authentication and Canonical RBAC

**Branch**: `002-identity-auth-rbac` (feature context reported by the setup script; current Git branch is `feature/002-identity-auth-rbac`) | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-identity-auth-rbac/spec.md`

## Summary

Introduce the repository's first business capability through an `identity` Django module that owns the custom User, pure canonical RBAC policy, authentication/user-administration application services, ports, and HTTP/persistence adapters. Add a separate `audit` supporting module for the canonical `AuditLog`, `OutboxEvent`, and caller-owned append ports so future business modules do not depend on identity internals. Authentication uses the CHOT-approved SimpleJWT blacklist mechanism with 15-minute access credentials, 7-day rotating refresh credentials, protected cookies, database-backed account-state checks, and User-row serialization for issuance/revocation races. The existing core error/correlation/payload filters, API namespace, generated OpenAPI/schema, handwritten thin frontend client, frontend transport, PostgreSQL test foundation, migration checker, and CI workflows are extended rather than replaced.

## Technical Context

**Language/Version**: Python 3.12; TypeScript 5.9; Node.js 22

**Primary Dependencies**: Existing Django 5.2.5, Django REST Framework 3.16.1, psycopg 3.2.9, drf-spectacular 0.28.0; add only CHOT-required `djangorestframework-simplejwt==5.5.1` and its transitive PyJWT dependency; existing Next.js 16.3.1, React 19.1.1, openapi-fetch 0.14.0, openapi-typescript 7.9.1

**Storage**: PostgreSQL 17; custom User plus canonical AuditLog/OutboxEvent; SimpleJWT OutstandingToken/BlacklistedToken; existing DatabaseCache remains owned by operations

**Testing**: pytest/pytest-django with pure unit, HTTP integration, contract, architecture, migration, and real-PostgreSQL transaction/race suites; Vitest/Testing Library for frontend state/UI; existing deterministic OpenAPI/generated-schema checks plus handwritten-client type/static verification

**Target Platform**: Linux-hosted Django API behind the existing same-origin Next.js proxy; modern mobile/desktop browsers

**Project Type**: Web application with separate backend and frontend projects

**Performance Goals**: For the 50-user MVP, login, refresh, self-account reads, and paginated user-directory interactions remain within the existing p95 500 ms application target; the user list uses fixed server page size and deterministic ordering

**Constraints**: No role/permission claims in credentials; no access-token blacklist; refresh only in host-only `Secure; HttpOnly; SameSite=Strict` cookie at `/api/v1/auth/`; access only in memory; authorization and Manager-target guard before DTO validation; every request reloads current user state; generated password returned once and never logged/audited/evented; all mutations plus audit/outbox share one transaction; no SQLite evidence; no new broker, state library, email/SMS, MFA, or session-management infrastructure

**Scale/Scope**: Approximately 50 internal users, three roles, 25 canonical PermissionAction values, five implication pairs, 13 identity/user HTTP operations across 10 paths, and multiple simultaneous browser sessions per user

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle / gate | Pre-design | Post-design evidence |
|---|---|---|
| I. Source-of-truth governance | PASS | CHOT §7, §8–§8.3, §9.2–§9.2.1, §9.4, and §10 control. QUY_TAC §3/§5/§7 supplies enforcement detail. R-57, R-60–R-72, R-75/76/78/80/81/87/90/91/92/103/104 are rationale only and agree with the current CHOT. No conflict is unresolved. |
| II. Fixed stack and inward architecture | PASS | Existing Django/DRF/PostgreSQL/Next.js structure is retained. `identity` and `audit` each expose domain/application/ports/adapters. Domain imports no framework; config remains the composition root; no module imports another module's models/domain/adapters. |
| III. Layered ordered authorization | PASS | Authentication loads current user; action RBAC and body-independent Manager-target authorization run before the forced-password gate; DTO validation follows; owning modules then apply object scope/business rules/transaction/audit. Pure permission decisions retain the granting action for future object-scope policies. |
| IV. Server authority and validation | PASS | Self actors come only from authentication. Username, user_id, password, active state, and role are accepted only by their owning operations. Server-owned fields are explicitly rejected after authorization, not ignored. |
| V. Database invariants and transactions | PASS | Unique username, nonblank names, closed role, immutable username, immutable AuditLog, unique outbox event/aggregate versions, and blacklist uniqueness are database-backed. Mutations use one caller-owned unit of work; issuance/revocation and Manager-target races serialize on User rows. |
| VI. Auditability and safe observability | PASS | Audit/outbox ports join caller transactions, read ambient correlation at the adapter, and run the existing exact-key/URL payload filter before insert. Passwords, credentials, cookies, and token identifiers never enter audit/event payloads. |
| VII. Stable generated contracts | PASS | All routes remain under the single `/api/v1/` prefix, errors use the existing envelope, operation IDs are explicit, and backend OpenAPI plus generated TypeScript are regenerated and drift/compatibility/safety checked. JSON `refresh_token` and all credential examples/response values remain forbidden; the canonical structural `password` property is allowed only in the login request schema. |
| VIII. Safe schema evolution | PASS | New apps/tables are additive. The migration checker evolves from the feature-001 operations-only allowlist to the explicit `{operations, identity, audit}` local owners, keeps one leaf per app, and verifies feature-001 → feature-002 migration on PostgreSQL. No destructive contract phase exists. |
| IX. Security and environment isolation | PASS | The existing secret/config/origin controls remain. Signing uses the existing environment-provided Django secret; credentials stay out of logs, URLs, browser storage, generated examples, audit, and outbox. Account state is checked on every request. |
| X. Location integrity | PASS (boundary only) | No location model, data, GPS behavior, or location contract is introduced. The RBAC map includes canonical location actions solely as authorization policy. |
| XI. Correct-layer tests | PASS | Pure policy/password rules use unit tests; API ordering and cookie/error semantics use HTTP tests; constraints, rollback, migration, refresh reuse, issuance/revocation races, audit immutability, and target race protection use PostgreSQL. Frontend capability/session behavior uses Vitest. |
| XII. Maintainability and naming | PASS | Canonical Role/PermissionAction/error/event vocabularies are centralized. Existing Ruff/mypy/complexity and ESLint/TypeScript limits expand to authored identity/audit/frontend feature paths. Thin HTTP/framework adapters delegate to cohesive application services. |

No constitution violation or complexity exception is required.

## Project Structure

### Documentation (this feature)

```text
specs/002-identity-auth-rbac/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api.md
│   ├── events.md
│   └── frontend.md
└── tasks.md                 # generated later by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── config/
│   ├── composition.py       # wire identity services, repositories, UoW, audit/outbox ports
│   ├── settings.py          # register auth/blacklist/identity/audit and one SIMPLE_JWT block
│   └── urls.py              # own /api/v1/ once; mount injected identity routes
├── core/
│   ├── error_codes.py       # extend only with CHOT-authorized identity codes
│   ├── errors.py            # canonical identity exception mapping
│   ├── messages.py          # centralized Vietnamese messages
│   └── event_payload.py     # reuse unchanged as the audit/outbox safety boundary
├── identity/
│   ├── apps.py
│   ├── models.py            # Django persistence adapter required by app discovery
│   ├── domain/
│   │   ├── accounts.py      # pure account snapshots and role value
│   │   ├── authorization.py # PermissionAction, grants, five implications, decisions
│   │   └── passwords.py     # pure minimum-length/username rules
│   ├── application/
│   │   ├── container.py      # typed service-container surface; no concrete wiring
│   │   ├── dto.py
│   │   ├── authentication.py
│   │   ├── self_service.py
│   │   ├── user_admin.py
│   │   └── queries.py
│   ├── ports/
│   │   ├── users.py
│   │   ├── credentials.py
│   │   ├── sessions.py
│   │   └── unit_of_work.py
│   ├── adapters/
│   │   ├── persistence/
│   │   │   └── users.py
│   │   ├── security/
│   │   │   ├── authentication.py
│   │   │   ├── passwords.py
│   │   │   └── sessions.py
│   │   └── api/
│   │       ├── permissions.py
│   │       ├── serializers.py
│   │       ├── views.py
│   │       └── urls.py
│   └── migrations/
│       └── 0001_initial.py
├── audit/
│   ├── apps.py
│   ├── models.py            # Django persistence adapter required by app discovery
│   ├── domain/
│   │   └── records.py       # immutable audit/event inputs and vocabularies
│   ├── application/
│   │   └── __init__.py      # no transaction-owning append service
│   ├── ports/
│   │   └── recording.py     # append_audit_entry / append_outbox_event protocols
│   ├── adapters/
│   │   └── persistence/
│   │       └── recording.py # filter then insert; no atomic/on_commit
│   └── migrations/
│       └── 0001_initial.py
└── tests/
    ├── unit/{identity,audit}/
    ├── integration/api/identity/
    ├── integration/postgres/{identity,audit}/
    ├── contract/identity/
    └── architecture/

frontend/
├── src/
│   ├── app/
│   │   ├── login/page.tsx
│   │   ├── change-password/page.tsx
│   │   └── users/page.tsx
│   ├── features/identity/
│   │   ├── api/identity-api.ts
│   │   ├── model/session-store.ts
│   │   ├── model/AuthProvider.tsx
│   │   └── ui/{LoginForm,ChangePasswordForm,UserDirectory,UserEditor,GeneratedPasswordDialog}.tsx
│   └── shared/
│       ├── transport/authenticated-fetch.ts
│       ├── api/{client.ts,schema.ts}
│       ├── errors/api-error.ts
│       └── messages.ts
└── tests/
    ├── unit/identity/
    ├── contract/identity/
    └── architecture/

frontend/next.config.ts       # preserve incoming canonical trailing-slash shape in proxy rewrite

contracts/openapi.yaml       # regenerated, never hand-edited
scripts/{check_all.sh,check_architecture.py,migration_check.py}
.github/workflows/{quality.yml,contract.yml}
.pre-commit-config.yaml
docs/ARCHITECTURE.md
```

**Structure Decision**: `identity` is the single owner of user/authentication/RBAC policy. `audit` is a supporting business-infrastructure owner because AuditLog/OutboxEvent are used by every future business module and cannot live in non-app `core`, operational-only `operations`, or identity internals. Cross-module callers import only `audit.ports.recording`; config imports concrete adapters and performs injection. The architecture and migration-owner allowlists are updated explicitly to these new approved owners while continuing to reject all other business modules until their own features exist.

The conventional `identity/models.py` and `audit/models.py` files are classified as persistence adapters for Django model discovery; domain/application code cannot import them. Keeping model declarations there avoids re-export shims that would point inward from a non-adapter module, and architecture tests treat business `models.py` as an adapter boundary while retaining the cross-module import ban.

## Design and Ownership

### Domain and application boundaries

- `identity.domain.authorization` owns the closed Role and PermissionAction vocabularies, direct Role × Action grants, exactly five implications, `ASSIGNABLE_ROLES`, effective capabilities, and a pure decision that records which direct action granted a requested action. It contains no Django/DRF imports and no scattered role conditions elsewhere.
- `identity.domain.accounts` represents typed user snapshots used by application services. The Django User remains an adapter model; domain code never imports it.
- `identity.domain.passwords` enforces the pure 12-character and username-difference rules. A password-policy port delegates the remaining configured Django validators at the application boundary.
- Application services are separated into login/refresh/logout, self profile/password, user-admin mutations, and list/detail queries. They accept typed DTOs plus authenticated actor/target identifiers and ports; they do not parse JSON, set cookies, shape HTTP responses, or open framework transactions directly.
- `audit.ports.recording` is the only cross-module write surface. Its persistence adapter joins the caller's UoW and never calls `atomic()` or `on_commit()`. `core.event_payload` remains the one shared safety filter.
- `config.composition` owns concrete wiring. Config constructs repositories, session/password adapters, UoW, audit/outbox adapters, and service containers, then passes them to the identity URL/view factory; identity adapters do not import another module's adapters.

### Authentication and session lifecycle

- Add pinned SimpleJWT because CHOT explicitly selects it and requires its blacklist state. Register `django.contrib.auth`, `rest_framework_simplejwt.token_blacklist`, `identity`, and `audit`; set `AUTH_USER_MODEL = "identity.User"` before the first auth migration.
- Keep one `SIMPLE_JWT` block with access 15 minutes, refresh 7 days, rotation true, blacklist-after-rotation true, and update-last-login true. Custom token construction removes noncanonical extra claims and tests the exact `{user_id, exp, jti, token_type}` set.
- A custom bearer authentication adapter validates the access credential, loads the current User on every request, returns `INVALID_TOKEN` for missing/invalid/expired credentials and `ACCOUNT_INACTIVE` for a valid credential whose current account is inactive. It never trusts role/capabilities from claims.
- The required-password-change gate is evaluated only after authentication, required-action RBAC, and body-independent route-target authorization have succeeded, and before serializer/DTO validation. Login remains public; password change is the sole protected exemption. Therefore unauthorized plus forced-change returns `PERMISSION_DENIED`, authorized plus forced-change returns `PASSWORD_CHANGE_REQUIRED`, unauthorized plus malformed input returns `PERMISSION_DENIED`, and a protected Manager target plus malformed input returns `PERMISSION_DENIED`.
- Login/refresh/token replacement issue access JSON plus a refresh cookie. The refresh value never appears in request/response JSON or query parameters. Cookie attributes are exactly host-only, Secure, HttpOnly, SameSite Strict, no Domain, and Path `/api/v1/auth/`; auth responses use `Cache-Control: private, no-store`.
- Logout requires both a valid bearer access credential and a valid, unrevoked refresh cookie owned by the same current User. Missing, invalid, expired, mismatched, or already-blacklisted refresh returns the existing `INVALID_TOKEN` result without global revocation or success evidence. After both credentials pass, logout revokes all outstanding refresh sessions for that user even when multiple devices exist. Reset, self password change, and deactivation use the same revocation port and canonical reason vocabulary. Only self password change issues a new pair, strictly after revocation.

### Authorization and permission-provenance foundation

- Each protected action view declares one required PermissionAction. A shared permission adapter evaluates the required action (direct or documented implication), then—on the four target mutations—current target role, and only then the forced-password account gate before any serializer is instantiated.
- Target lookup for object permission is restricted to the route identifier and reads no body. Existing Manager targets return `403 PERMISSION_DENIED` for profile/role/status/reset, including self-target and empty/malformed bodies; authorized GETs still include them.
- Create/assign role payloads parse Role after action authorization. `MANAGER` is syntactically valid but outside `ASSIGNABLE_ROLES`, so the application policy returns 403 after DTO validation. Unknown role strings remain validation failures. Profile serializers reject any presence of username/role/password/is_active with `SERVER_OWNED_FIELD` before validating allowed values.
- The pure permission decision exposes the stronger direct granting action. Feature 002 stops at requested action, allow/deny, and `granted_by`; it contains no Task creator/assignee helper, Attendance ownership helper, or API test against endpoints those modules do not yet own. Feature 004 must enforce Attendance self scope, and Feature 006 must enforce Task creator/assignee scope and business invariants using this generic provenance.
- Frontend capabilities are the effective action-string set returned by login and `/me`; schema represents each item and Role as open strings, not OpenAPI enums. Capabilities control presentation only.

### API, DTO, and error semantics

- Preserve the endpoint/status/payload contract in [contracts/api.md](./contracts/api.md). Config owns `/api/v1/` exactly once; identity routes are relative beneath it and have explicit stable operation IDs.
- Serializers are operation-specific: login, empty refresh/logout, self profile, password change, user-create, user-profile, role-only, status-only, and empty reset. There is no multipurpose user PATCH.
- User-list uses `q`, `role`, `is_active`, and `page`; all filters are optional, no `page_size`, default results include inactive and Manager accounts, and deterministic ordering is `full_name`, `username`, `id`. At MVP scale no trigram/search dependency or index is introduced.
- Extend the existing canonical error registry/messages/handler only with `INVALID_CREDENTIALS`, `INVALID_TOKEN`, `ACCOUNT_INACTIVE`, `PASSWORD_CHANGE_REQUIRED`, and `SERVER_OWNED_FIELD`; existing `VALIDATION_FAILED` and `PERMISSION_DENIED` remain. All use the canonical envelope and deprecated mirrors.
- Create and reset have distinct response schemas containing `generated_password`; ordinary user/self responses never contain that field. OpenAPI may contain the exact `password` property only in the login request, never in user create/reset/profile or any response; it contains no JSON `refresh_token`, credential example, or cookie value. The OpenAPI safety checker becomes context-aware for this one structural request property while the audit/outbox payload filter remains strict and unchanged.

### Persistence, transactions, and concurrency

- User schema/constraints/indexes and AuditLog/OutboxEvent schema are specified in [data-model.md](./data-model.md). User has a unique username, database checks for nonblank username/full_name and closed role, database defaults for active/forced-change flags, and a PostgreSQL trigger that rejects username changes.
- AuditLog retains exactly eight CHOT fields and has a PostgreSQL trigger rejecting update/delete. OutboxEvent has unique event_id, positive per-aggregate version, unique `(aggregate_type, aggregate_id, aggregate_version)`, PENDING initial state, correlation defaults at DDL level, and pending-order index. Relay/transport/retry execution is explicitly deferred.
- Every state-changing application service owns one UoW through a port. User state, blacklist rows, AuditLog rows, and OutboxEvent rows commit or roll back together. Append adapters filter payloads before insert and never create an independent transaction.
- All credential issuance/rotation and all four revocation flows lock the same User row. Refresh rechecks blacklist/account state after acquiring the lock. Therefore a concurrent issue/refresh is either completed before revocation and then revoked, or runs after and observes the new account/session state.
- The four user-admin target mutations perform the pre-DTO Manager guard for response order, then reacquire the target with `SELECT FOR UPDATE` and recheck role inside the UoW before mutation. This prevents a concurrent promotion to Manager from slipping between authorization and write.
- Duplicate username is protected by PostgreSQL uniqueness. Two concurrent creates yield one commit and one canonical validation failure. Outbox aggregate versions are assigned while the User aggregate row is locked; create begins at version 1.
- The PostgreSQL race suite enumerates every claimed serialization pair: login issuance and refresh issuance each race against logout, Manager reset, self password change, and deactivation; concurrent global revocations race for one User; and concurrent events race for one User's next aggregate version. “No issuance escapes” means no racing refresh remains usable after a completed revocation; it does not retroactively blacklist an issued access credential, whose expiry and current-account gates remain canonical. Tests use real transactions and competing threads/workers, then read final database state and exercise surviving credentials. No broader lock invariant is claimed without a matching test.

| Claimed PostgreSQL lock/competition invariant | Proof task |
|---|---|
| Same refresh credential has at most one rotation winner | T040 |
| Login/session issuance vs logout | T066 |
| Login/session issuance vs Manager password reset | T067 |
| Login/session issuance vs self password change | T068 |
| Login/session issuance vs account deactivation | T069 |
| Refresh issuance vs logout | T070 |
| Refresh issuance vs Manager password reset | T071 |
| Refresh issuance vs self password change | T072 |
| Refresh issuance vs account deactivation | T073 |
| Concurrent global revocations for one User | T074 |
| Concurrent per-User outbox aggregate-version allocation | T023 |
| Concurrent Manager promotion vs protected target mutation | T065 |
| Concurrent duplicate username creation | T064 |

- Initial migrations are additive and have one leaf per new app. PostgreSQL migration tests start at the feature-001 graph, apply identity/audit/auth/blacklist migrations, verify triggers/constraints/indexes, reverse only where safe in an isolated test database, and confirm old feature-001 code has no table dependency. No destructive contract migration is included.

### Audit and outbox

- Security actions use the closed audit/event vocabulary in [contracts/events.md](./contracts/events.md). Audit before/after snapshots never include password hashes, generated passwords, token identifiers, cookies, or credentials.
- Session revocation records reason and count only. Create/profile/role/status/password events include only consumer-minimal state; profile outbox payload contains changed field names rather than contact values.
- Password reset/change may write both the user-operation record and the shared sessions-revoked record in the same transaction. Refresh rotation is not audited/evented per use to avoid high-volume security noise; logout and all other globally revoking flows are.
- Ambient request/correlation values are read only in the outbox persistence adapter. AuditLog retains exactly its eight canonical fields and receives no correlation columns.

### Frontend state and integration

- Extend the existing single `authenticatedFetch`; do not add Axios or a second transport. It attaches the in-memory bearer access value, sends cookies via the existing `credentials: include`, performs one single-flight refresh on `INVALID_TOKEN`, retries an eligible original request at most once, and never refresh-loops on `ACCOUNT_INACTIVE` or `PASSWORD_CHANGE_REQUIRED`.
- Change the existing proxy destination so it preserves the caller's path instead of forcibly appending `/`. Contract tests pin CHOT's mixed canonical shape: auth login/refresh/logout and change-password have no trailing slash; `/me/` and user-directory routes retain theirs. POST behavior never depends on redirecting a body.
- Refresh itself uses an internal raw call inside the approved transport file to avoid recursion. Concurrent 401 responses share one refresh promise. Login/change-password response handling replaces the in-memory access value; logout/account-inactive clears it.
- `AuthProvider` bootstraps a page reload through refresh then `/me`, exposes account/capabilities/loading/failure, redirects forced-change users to the password page, and guards user administration by capabilities. It does not persist access/account data to localStorage/sessionStorage.
- Identity API wrappers use the handwritten thin `frontend/src/shared/api/client.ts` above `authenticatedFetch` and the generated `frontend/src/shared/api/schema.ts`; wire fields stay snake_case. The existing generator writes only `schema.ts`, while `client.ts` is type/static checked as authored code. Components use local/React context state only, reuse AsyncState/error parsing, and add centralized messages for inactive, forced-change, and permission outcomes.
- `GeneratedPasswordDialog` receives plaintext only from the immediate create/reset result, marks it nonpersistent, and clears component state on dismissal/unmount/logout/account switch. No browser storage, URL, analytics, log, or retry cache receives it.

## Verification Strategy

| Layer | Evidence |
|---|---|
| Pure domain unit | Exact three roles, all direct grants/denials, exactly five implications, grant provenance, no inferred actions, Leader no mutation, Manager no check-in/out, assignable roles, password length/username rules. |
| Application unit | Service orchestration with fakes: generated-password display-boundary result, role/Manager guards, actor-derived self operations, revoke-before-issue, audit/event payload minimization, rollback propagation, query filter defaults. |
| HTTP integration | Login enumeration resistance; access/refresh/logout cookies and statuses; forced-password ordering; RBAC-before-DTO and target-before-DTO; all user-admin allow/deny paths; self user_id rejection; page/filter behavior; exact error envelopes/no-store headers. |
| PostgreSQL integration | Migration from feature 001, vendor assertion, User constraints/triggers and protective audit FK, concurrent duplicate username, blacklist persistence/reuse, same-refresh race, the explicit eight issuance-versus-revocation pairs, concurrent global revocation, concurrent aggregate-version allocation, Manager-target TOCTOU protection, audit immutability, and user+audit+outbox rollback after append. |
| RBAC provenance foundation | Parameterized direct/effective Role × Action matrix and source-action provenance only; no Task/Attendance record ownership implementation. Feature 004 and Feature 006 own their corresponding scope integration proof. |
| Contract | Every exact endpoint path/trailing-slash shape/operation ID, logout dual-credential behavior, request/response/status/cookie security description, string capabilities/role, no JSON refresh, login-only structural password input, generated-password response isolation, canonical errors, deterministic generation, safety scan, backend/schema drift, handwritten client type/static verification, and merge-base compatibility. |
| Frontend | In-memory-only token state, bootstrap refresh, one single-flight retry, inactive stop, forced-change redirect, capability-gated UI, admin filters/actions, exact-once password dialog clearing, canonical failure rendering. |
| Architecture/migration | Approved apps become operations/identity/audit only; domain framework ban; inward/cross-module import rules; config-only composition; core/config remain non-apps; one migration leaf per app; additive phase and DDL defaults; scope exclusions continue for later business modules. |
| CI | Existing quality/contract jobs expand mypy/maintainability/test paths, install locked SimpleJWT, run all PostgreSQL identity/audit suites, and retain generated contract/client, architecture, migration, isolation, lint/type/build gates. |

## Delivery Phases

1. Update authority trace, dependency lock, app/migration/architecture allowlists, typed error vocabulary, typed service-container surface, and failing contract/domain tests.
2. Add pure identity policy/account/password domain and port contracts; add audit/outbox domain/ports and payload tests.
3. Add additive User/AuditLog/OutboxEvent migrations, auth/blacklist configuration, persistence adapters, UoW, triggers, and PostgreSQL invariant/rollback tests.
4. Implement authentication/session application services and adapters with row-lock concurrency tests, then self-service flows.
5. Implement user-admin services and HTTP adapters with action/target/forced-change/DTO ordering, pagination, audit/outbox, and the complete PostgreSQL issuance/revocation/aggregate-version race matrix; then wire the concrete service container.
6. Generate and verify OpenAPI plus the TypeScript schema artifact; type-check the handwritten client wrapper; build identity API wrappers, in-memory session state, single-flight refresh, login/change-password/user-admin UI, and frontend tests.
7. Expand CI/pre-commit/architecture/documentation, run the complete quickstart and compatibility/migration gates, and confirm zero unresolved markers or prohibited secret output.

## Risks and Controls

- **Refresh/revocation race**: a token could be issued after a revoker scans outstanding rows. Control: every issue, rotate, and revoke operation locks the same User and rechecks state after locking; explicitly enumerated PostgreSQL competing-worker tests cover login and refresh issuance against all four revocation flows plus concurrent revokers.
- **Manager target changes after permission check**: a target could be promoted between pre-DTO authorization and write. Control: repeat the same canonical target rule under `SELECT FOR UPDATE`; no alternate business rule is introduced.
- **Generated plaintext escapes through diagnostics or object repr**: control with non-repr display-boundary result objects, no exception interpolation, exact response-only serializer ownership, core filter tests, caplog/audit/outbox scans, and frontend state clearing.
- **SimpleJWT defaults drift from CHOT**: control with one settings block, exact claim-set tests, cookie tests, and custom adapters rather than exposing stock token views/serializers.
- **Audit/outbox becomes an identity dependency trap**: control with a separate supporting module, port-only cross-module surface, config composition, architecture fixtures, and no relay/transport responsibilities in this feature.
- **Adding auth after foundation migrations**: control with a migration-history preflight, custom User configured before auth migrations, feature-001→002 MigrationExecutor test, single-leaf checks, and additive-only rollout.
- **Frontend refresh recursion or request storms**: control with one transport implementation, endpoint exclusions, one shared promise, one retry marker, and tests with many simultaneous invalid-token responses.
- **Proxy rewrites POSTs to a different slash form**: control by removing the forced destination slash, preserving the incoming canonical path, and testing exact rewrite results for both slashless auth and slashed user routes.
- **Generated contract leaks cookie/refresh/generated secret examples or accepts password in the wrong operation**: control with response/request schema separation, no credential examples, a context-aware OpenAPI scanner that permits exact `password` only for login input, identity fixtures, and generated-artifact drift checks.

## Complexity Tracking

No constitution violations or justified exceptions.
