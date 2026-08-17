# Feature Specification: Project Foundation and API Contract Baseline

**Feature Branch**: `master` (no branch hook configured)

**Created**: 2026-08-17

**Status**: Draft

**Input**: User description: "Create the shared backend, frontend, contract, quality, test, and CI foundation required by all later business features, without implementing any business flow."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build New Features on a Safe Foundation (Priority: P1)

As a product engineer, I can add a later business module within an established project boundary and use shared configuration, correlation, errors, and data-access foundations without inventing a competing convention.

**Why this priority**: Every later feature depends on a stable foundation; inconsistent boundaries at this stage would multiply rework and weaken governance.

**Independent Test**: A minimal non-business probe can be added and exercised through the approved backend and frontend boundaries without introducing a business entity or bypassing a shared service.

**Acceptance Scenarios**:

1. **Given** the baseline repository, **When** an engineer inspects the backend, **Then** there is one composition root, a narrow `backend/core/` kernel, and an explicit domain/application/ports/adapters convention whose dependency direction can be checked automatically.
2. **Given** valid development configuration and an available PostgreSQL service, **When** the backend starts and its test suite runs, **Then** it connects successfully and database integration tests prove they are using PostgreSQL.
3. **Given** a missing, empty, or invalid production-critical setting, **When** startup validation runs, **Then** startup stops with a safe message that identifies the invalid setting without revealing a secret value.
4. **Given** the frontend baseline, **When** a shared or generated client makes a server request, **Then** the request passes through the single authenticated transport chokepoint and uses shared error handling.
5. **Given** a frontend request is loading, returns no data, fails before receiving a contract response, or returns a canonical API error, **When** shared UI handling presents that state, **Then** it distinguishes the state, offers a safe recovery path where possible, and exposes the server request identifier for support without exposing credentials or protected payloads.

---

### User Story 2 - Consume a Stable Versioned Contract (Priority: P1)

As a frontend engineer or API consumer, I can rely on one versioned contract, one wire naming convention, and one predictable error shape for every failure whose semantics are authorized by the governing contract.

**Why this priority**: Later teams cannot work independently if the server contract and client interpretation can drift.

**Independent Test**: Generate the contract and client twice, exercise representative success and failure probes, and compare the observed routes, payloads, headers, and generated artifacts.

**Acceptance Scenarios**:

1. **Given** any registered application API route, **When** the contract is generated, **Then** the route is under `/api/v1/`, wire properties use `snake_case`, and operation identifiers are explicit, unique, and stable.
2. **Given** a failure whose `error_code` and HTTP status are already authorized by CHOT, including request validation and request-forgery denial, **When** the response is returned, **Then** it contains `error_code`, `message`, `details`, and `request_id`, plus the v1 compatibility mirrors; this feature does not assign new codes to framework statuses.
3. **Given** a request carrying an arbitrary `X-Request-Id`, **When** the server processes it, **Then** the server ignores that value, creates its own identifier, returns it in both the response header and error body when applicable, and binds it to correlation context.
4. **Given** an unchanged source tree, **When** the API schema and client are each generated twice, **Then** each pair is byte-identical and matches the committed artifacts.
5. **Given** API documentation is disabled, **When** a caller requests `/api/v1/schema/`, **Then** the route is absent and returns `404`; when explicitly enabled, the machine-readable schema is available without an interactive documentation UI.

---

### User Story 3 - Detect Unsafe Changes Before Merge (Priority: P2)

As a reviewer, I receive automated evidence that code quality, architecture, contracts, migrations, and supported runtime behavior remain safe before a change can merge.

**Why this priority**: A written convention is insufficient unless regressions are detected consistently.

**Independent Test**: Run the repository's complete quality pipeline, then introduce one controlled violation for each gate and verify that the relevant gate fails with an actionable diagnosis.

**Acceptance Scenarios**:

1. **Given** a conforming change, **When** the local and CI quality suites run, **Then** formatting, linting, typing, unit tests, frontend tests, backend integration tests, architecture checks, and build checks all pass.
2. **Given** a server change without regenerated contract artifacts or a generated-client change without its source contract change, **When** CI runs, **Then** the drift check fails and names the stale artifact.
3. **Given** a candidate contract that removes or changes an existing response/property, changes a type, or adds a required request property, **When** compatibility is compared with the merge base, **Then** CI rejects it; an additive optional change remains eligible for the current major version.
4. **Given** an unsafe migration, **When** static migration checks run, **Then** CI rejects multiple migration leaves, unsafe newly required fields, or unmarked/destructively mixed contract operations before connecting to a database.
5. **Given** committed environment and recovery inventories, **When** their executable checks run, **Then** shared resource identities are rejected, unresolved production choices prevent a production-ready result, and absent/stale/failed recovery evidence prevents a recovery-ready result without pretending that an operational drill occurred.
6. **Given** the approved operational module and composition root, **When** Django command discovery and migration ownership are inspected, **Then** `verify_restore` and the cache-table migration belong to `operations`, while `config/` and `core/` are not Django applications and own no persistence.
7. **Given** cache configuration for any environment, **When** startup and isolation checks run, **Then** one canonical cache alias and table identity are used, process-local storage is rejected outside development, and no component duplicates the approved backend vocabulary.

---

### User Story 4 - Diagnose Requests Across Shared Boundaries (Priority: P3)

As a support engineer, I can use a server-issued request identifier and correlation context to connect a client-visible failure to safe server diagnostics without exposing protected values.

**Why this priority**: The foundation must make later operational diagnosis possible, while business-specific audit and telemetry remain outside this feature.

**Independent Test**: Send concurrent probe requests, trigger representative failures, and verify unique identifiers, matching response values, isolated correlation contexts, and safe behavior outside an HTTP request.

**Acceptance Scenarios**:

1. **Given** two concurrent requests, **When** both are handled, **Then** each has a distinct request identifier and neither request observes the other's context.
2. **Given** request processing creates downstream correlation context, **When** no upstream chain identifier exists, **Then** the correlation identifier defaults to the server-issued request identifier.
3. **Given** execution outside an HTTP request, **When** shared correlation context is read, **Then** absence is represented safely without fabricating a request identifier.
4. **Given** a log record is emitted inside or outside a request, **When** shared logging processes it, **Then** the record carries the bound request and correlation identifiers or empty values, and a logging failure does not change the API response.

### Edge Cases

- A client supplies a malformed, duplicate, oversized, or non-UUID `X-Request-Id`; it is never trusted or echoed.
- Validation, CSRF, or origin denial occurs before or during endpoint dispatch; when CHOT already authorizes its code/status, the response follows the canonical contract. An ungoverned framework status is not assigned a code by this feature.
- Error details are empty, contain field-level validation issues, or use keys that overlap canonical envelope keys; canonical keys remain authoritative and compatibility mirrors remain consistent.
- A configuration variable is present but empty; it is treated as invalid rather than as permission to use a fallback.
- Contract generation runs under different stable local/CI environments; ordering, operation identifiers, and output bytes remain unchanged.
- The schema source contains an example or description resembling a token, password, cookie, signed URL, object key, image data, or precise coordinates; the safety check rejects the artifact.
- A migration combines expansion and destructive contraction, adds a new `NOT NULL` field without `db_default`, leaves a destructive operation unmarked or in the same release as expansion, or creates more than one leaf for an application; the static check fails.
- The PostgreSQL test service is unavailable or tests accidentally target another database engine; integration tests fail clearly rather than silently substituting a weaker database.
- A generated client attempts to bypass the authenticated transport; an automated boundary check detects the second transport path.
- A deployment setting is present but empty, the environment name is outside the closed development/staging/production vocabulary, runtime and migration database identities are the same, or two environments reuse a protected resource identity; validation fails and names the setting or manifest field without printing its value.
- A shared safety filter receives nested forbidden keys or protected URL/credential/location values; it rejects the payload without including the protected value in its own diagnostic, while exact allowed keys that merely contain a forbidden word as a substring remain valid.
- A browser supplies the configured source-credential header; the web proxy removes it before attaching the server-held value, and a direct origin request with a missing or wrong value receives a canonical 403 without revealing which credential check failed.
- Recovery or capacity evidence is absent, stale, marked failed, failed without a remediation owner, or exceeds a target; readiness remains nonzero and names only the unresolved field or safe measurement.
- Cache backend configuration is empty, unknown, missing from the inventory, or process-local outside development; startup or isolation fails while naming only the setting/path. `DJANGO_DEBUG=true` does not bypass the environment rule.
- A capacity request contains fewer than 50 distinct real identities or concurrency below 20; it is rejected before network activity. A valid 50/20 run with p95 exactly 500 ms may pass, while p95 above 500 ms must fail with a remediation owner.
- Django command discovery is inspected after assembly; `verify_restore` resolves to `operations`, and any `config/apps.py`, `config/management/`, `config/migrations/`, registration of `core`, or unapproved local app fails the architecture check.

## Requirements *(mandatory)*

### Functional Requirements

#### Foundation Boundaries

- **FR-001**: The product MUST provide runnable backend and frontend application foundations using the project constitution's fixed technology stack and PostgreSQL as the persistence engine.
- **FR-002**: The backend MUST expose one composition boundary for assembling runtime dependencies and MUST define a reusable business-module convention with domain, application, ports, and adapters boundaries.
- **FR-003**: Automated architecture checks MUST reject framework or persistence dependencies in domain code and reject direct production imports across business-module internals; the exemption list is closed to tests, migrations, and the `config/` composition root, with each exemption carrying its documented reason.
- **FR-004**: The canonical `backend/core/` kernel MUST be limited to reusable technical primitives, correlation, canonical error construction, cross-cutting ports, configuration support, and shared safety filters; it MUST NOT contain feature-specific business rules.
- **FR-005**: Runtime configuration MUST be loaded through a single typed validation foundation that runs before application-framework configuration, recognizes only development, staging, and production, fails closed for missing, empty, unresolved, or invalid production-critical values, and identifies the invalid setting without exposing its value.
- **FR-006**: Application runtime configuration MUST use the normal PostgreSQL connection and MUST NOT read or use the privileged migration connection; configuration validation MUST reject identical runtime and migration database identities.
- **FR-006a**: Outside development, runtime validation MUST require an encrypted password-protected Redis URL, environment-qualified Redis key prefix and private bucket name, and MUST reject a configured result backend; the committed inventory MUST keep every environment's database, bucket, Redis namespace, signing-key identity, edge credential identity, and backup identity separate.
- **FR-007**: This feature MUST NOT create authentication business flows or domain behavior for locations, attendance, tasks, reporting, or notifications.

#### API and Correlation Contract

- **FR-008**: Every application API route and every path in the generated contract MUST use the canonical `/api/v1/` namespace, declared from one authoritative routing boundary.
- **FR-009**: Every JSON API error with an error code already authorized by CHOT MUST use the canonical v1 envelope containing `error_code`, a centralized safe displayable Vietnamese `message`, `details`, and `request_id`; `details` MUST be an object and MUST be `{}` when no structured details exist. This feature MUST NOT invent codes, statuses, or semantics for framework failures that CHOT has not assigned.
- **FR-010**: Throughout v1, every error MUST also include deprecated `error` equal to `error_code`; field-level errors MUST appear both in `details` and as deprecated top-level mirrors for compatibility with the previous frontend bundle.
- **FR-011**: Canonical and compatibility error fields MUST be produced through one shared error-construction behavior, including failures created outside normal endpoint handlers.
- **FR-012**: The server MUST generate a new UUID version 4 request identifier for every request, MUST NOT trust a client-provided identifier, and MUST return the generated value in `X-Request-Id`.
- **FR-013**: When an error body is returned, its `request_id` MUST exactly match the response `X-Request-Id`.
- **FR-014**: Correlation context MUST be infrastructure-owned, isolated across concurrent work, available to shared infrastructure without adding correlation fields to domain inputs, and use the request identifier as the correlation identifier when no trusted upstream chain exists; client headers MUST NOT establish either identifier.
- **FR-015**: Outside a request, absent request and correlation identifiers MUST be represented as empty context rather than fabricated identifiers.
- **FR-016**: JSON wire field names MUST remain `snake_case` end to end, without a handwritten case-conversion layer.

#### Generated Contract and Frontend Consumption

- **FR-017**: The backend MUST be the authoritative source for a committed machine-readable API contract at `contracts/openapi.yaml`.
- **FR-018**: Contract generation MUST be deterministic: repeated generation from an unchanged source tree MUST produce byte-identical output, explicit unique operation identifiers, stable ordering, and a fixed contract version.
- **FR-019**: The machine-readable schema route MUST be registered only when `API_DOCS_ENABLED` is enabled and MUST NOT expose an interactive documentation interface.
- **FR-020**: Schema content, descriptions, properties, and examples MUST exclude secrets, credentials, cookies, passwords, tokens—including any JSON `refresh_token` property—signed URLs, image/object references, and precise location examples prohibited by the governing documents.
- **FR-021**: A committed generated frontend schema/client foundation at `frontend/src/shared/api/schema.ts` MUST be derived only from the committed API contract and MUST be reproducible without manual edits.
- **FR-022**: The frontend MUST expose one shared `authenticatedFetch` transport chokepoint for authenticated API traffic; generated and handwritten API wrappers MUST use it and MUST NOT create a parallel authenticated transport.
- **FR-023**: The frontend MUST provide shared loading, empty, canonical-error, unexpected-response, and network-failure handling that preserves canonical error fields, compatibility with v1 mirrors, request identifiers for support, and a safe retry or recovery path where the operation permits it.
- **FR-024**: Generated-code exclusions MUST match `QUY_TAC_CLEAN_CODE.md` exactly: `contracts/` and `frontend/src/shared/api/**` are the only broad generated paths. The handwritten `client.ts` remains thin and is enforced by review, architecture checks, and `tsc --noEmit`; no business logic may use the exclusion.

#### Quality, Test, and Delivery Gates

- **FR-025**: The repository MUST provide repeatable formatting, linting, static typing, and structural complexity checks for authored backend and frontend code in accordance with the clean-code rules.
- **FR-026**: The repository MUST provide fast unit-test foundations plus integration-test foundations for HTTP boundaries, architecture boundaries, configuration startup, generated contracts, frontend transport, and error handling.
- **FR-027**: All claims involving database constraints, transactions, migrations, concurrency, or PostgreSQL-specific behavior MUST be verified against real PostgreSQL; SQLite or mocks MUST NOT be accepted as equivalent evidence.
- **FR-028**: PostgreSQL integration tests MUST prove the active database vendor and fail if the required database service is unavailable rather than silently falling back.
- **FR-029**: CI MUST run backend and frontend formatting/lint/type checks, unit tests, PostgreSQL integration tests, architecture checks, builds, deterministic generation checks, security checks for generated artifacts, and migration static checks.
- **FR-030**: CI MUST fail when regenerating the backend contract changes `contracts/openapi.yaml` or regenerating the frontend schema/client changes `frontend/src/shared/api/schema.ts`, and MUST identify the stale artifact.
- **FR-031**: CI MUST compare the candidate API contract with the merge-base contract and reject unapproved breaking changes, including removals, incompatible type changes, and newly required request fields; additive optional changes MUST be accepted within v1.
- **FR-032**: Static migration checks MUST inspect migration files without importing application code or connecting to a database and MUST reject multiple leaves per application unless intentionally merged.
- **FR-033**: `scripts/migration_check.py check` MUST inspect files by AST without imports or database access and reject multiple leaves, every new `NOT NULL` field lacking `db_default`, every destructive remove/rename/contraction lacking `RELEASE_PHASE = "contract"`, and every contract migration mixed with expansion. Migration runs once before rollout, remains N-1 compatible, and destructive contract work waits for a later release.
- **FR-034**: Quality and contract gates MUST produce actionable failure output that identifies the violated rule and affected artifact without printing secrets or protected example values.
- **FR-035**: A committed non-secret environment inventory MUST identify development, staging, and production resources without storing credentials or full connection strings; CI MUST reject protected resource reuse across environments, while explicitly unresolved choices MUST remain marked `UNRESOLVED`.
- **FR-036**: A production-readiness check MUST fail and enumerate unresolved production choices until they are decided, but those unresolved provider choices MUST NOT be silently guessed or cause unrelated code-quality checks to report false success.
- **FR-037**: Shared logging MUST attach the ambient `request_id` and `correlation_id` to records, use empty values outside a request, and contain logging/telemetry failures so they cannot change an API response or business outcome.
- **FR-038**: The `backend/core/` safety-filter foundation MUST recursively reject the protected payload categories fixed by the governing documents, match forbidden keys exactly rather than by substring, and report only the path of a violation—not its protected value. Integration with business audit and outbox ports is deferred to the feature that owns those ports.
- **FR-039**: All backend and frontend display strings owned by this foundation MUST be centralized in `backend/core/messages.py` or `frontend/src/shared/messages.ts`; error builders and UI state components MUST NOT embed alternate copies.
- **FR-040**: Every telemetry/log/metric/alert path capable of receiving external failure text MUST use the one canonical `core.event_payload.sanitize_failure_reason` before emission, preserve the R-104 forbidden categories, bound output length, and contain sink failures. No alternate sanitizer is permitted.
- **FR-041**: The web edge MUST remove any client-supplied source-credential header before attaching a server-only value of at least 32 characters for `/api/v1/*`; its static matcher MUST equal the configured rewrite source. The committed inventory may contain the non-secret header name, but the credential value MUST NOT use `NEXT_PUBLIC_` or appear in logs, browser bundles, or responses.
- **FR-042**: The origin MUST compare the source credential in constant time and return the already-authorized canonical `403 PERMISSION_DENIED` response for missing or wrong credentials without identifying the failed credential; every `/api/v1/` response MUST be `private, no-store`.
- **FR-043**: The repository MUST contain reproducible deployment documentation and executable `isolation`, `production-ready`, and status-only `smoke` checks. Only `isolation` is a CI gate; unresolved production values intentionally keep `production-ready` nonzero.
- **FR-044**: The repository MUST contain `deploy/recovery-evidence.yaml` with policy targets separated from measured drill/capacity evidence; unknown measurements MUST remain `UNRESOLVED` and MUST NOT be represented as completed evidence.
- **FR-045**: Recovery-readiness MUST fail for unresolved, stale, failed, failed-without-remediation-owner, or target-exceeding evidence. A read-only restore verification command MUST use only `RECOVERY_DATABASE_URL`, reject runtime/admin identity matches before connection, and verify every CHOT-required database/schema category without writes. A missing required relation, unavailable category, incomplete probe result, unregistered required probe, incompatible restored schema, or probe execution failure MUST produce an incomplete/unverifiable non-success result and MUST NOT produce PASS, OK, or readiness.
- **FR-046**: The repository MUST provide a capacity-measurement command that refuses fewer than 50 distinct real identities or concurrency below 20 before network activity and treats identity files as secrets. An eligible result with p95 at or below 500 ms may be `passed`; p95 above 500 ms MUST be `failed` with a remediation owner. Every opened connection or resource MUST close on both success and failure. Identities, passwords, tokens, Bearer values, credentialed URLs, and secret values MUST be absent from stdout, stderr, and every returned/result artifact. Actual capacity measurement and restore drills remain operator-owned evidence, not CI gates; controlled fixtures are not operational evidence, command output MUST NOT itself make production/recovery readiness true, and controlled fixtures MUST NOT write evidence.
- **FR-047**: The deployment runbook MUST state backup targets, isolated restore procedure, session revocation and stale-outbox-lease clearing before recovered consumers start, migration-before-rollout order, credential rotation, and every egress destination. It MUST document the approved production topology—at least two availability zones, one public load balancer, private application instances accepting only load-balancer traffic, per-zone egress, and exactly one scheduler—while stating that IaC is deferred and APAC placement is not a legal residency guarantee.
- **FR-048**: `config/` MUST remain the sole Django composition/environment boundary and MUST NOT be registered as an application or own `apps.py`, management commands, migrations, models, or persistence. `core/` MUST remain a pure technical boundary and MUST NOT be registered as a Django application.
- **FR-049**: The already-approved `operations` module MUST own the thin discoverable `verify_restore` management-command shim and the database-cache-table migration. The shim MUST delegate recovery decisions to the shared recovery orchestration; neither `config/` nor the command shim may own recovery policy.
- **FR-050**: `core.cache` MUST be the single canonical owner of `THROTTLE_CACHE_ALIAS`, `THROTTLE_CACHE_TABLE`, `CACHE_BACKEND_CHOICES`, and process-local backend classification; it MUST remain importable without Django configuration and MUST NOT import Django.
- **FR-051**: Runtime settings MUST configure exactly one Django cache alias selected through `DJANGO_CACHE_BACKEND`. Settings, deployment checks, throttles, and cache-table provisioning MUST consume the canonical definitions rather than duplicate alias, table, vocabulary, or process-local classification.
- **FR-052**: The approved backend vocabulary MUST be closed to `locmem`, `database`, and `redis`. Empty or unknown values MUST fail and name `DJANGO_CACHE_BACKEND`; outside development, `LocMemCache`, `DummyCache`, and `FileBasedCache` MUST stop startup even when debug is enabled. The shipped staging/production selection MUST be `database`; development/test may retain the approved `locmem` fallback.
- **FR-053**: Django DatabaseCache provisioning MUST be an `operations` migration using the canonical table identity and the approved create-cache-table mechanism. Its number MUST be the next valid number in the actual `operations` migration graph; the current empty graph implies `0001_throttle_cache_table`, while an evolved graph requires recalculation rather than a hard-coded historical number. Static and PostgreSQL migration tests MUST prove one leaf, ownership, provisioning, and settings/migration identity equality.

### Key Entities

- **API Error Envelope**: A client-visible failure representation with a canonical code, safe human-readable message, structured details, a server-issued request identifier, and temporary v1 compatibility mirrors.
- **Request Correlation Context**: Infrastructure-owned request and chain identifiers bound to the current execution context and isolated from domain inputs and concurrent requests.
- **API Contract Artifact**: The committed, deterministic, versioned description of the public HTTP contract from which frontend types and client bindings are derived.
- **Generated Client Artifact**: Reproducible frontend bindings generated from the committed API contract and routed through the shared transport chokepoint.
- **Runtime Configuration**: Typed environment-specific settings and secret references whose validity is checked before the application accepts work.
- **Migration Safety Finding**: A static result identifying schema evolution that violates single-leaf, rolling compatibility, or expand-migrate-contract rules.
- **Recovery Evidence**: Committed targets plus operator-recorded restore-drill and capacity measurements whose unresolved or failed state is preserved rather than inferred as success.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a clean checkout with documented prerequisites, an engineer can validate configuration, start both applications, and complete one backend-to-frontend probe in 15 minutes or less.
- **SC-002**: 100% of registered application API paths and generated contract paths begin with `/api/v1/`, and 100% of wire properties use `snake_case`.
- **SC-003**: 100% of tested CHOT-authorized JSON API failure classes contain all four canonical error fields; all v1 compatibility mirrors match their canonical values; body and header request identifiers match in every case, and the test corpus contains zero newly invented error codes.
- **SC-004**: Across at least 10,000 generated request identifiers, there are zero collisions, zero accepted client-supplied identifiers, and zero observed cross-request context leaks in concurrent tests.
- **SC-005**: Two consecutive server-contract generations and two consecutive frontend-client generations from the same source are byte-identical, with zero uncommitted artifact differences.
- **SC-006**: Controlled contract-drift, breaking-change, unsafe-example, architecture-boundary, and unsafe-migration fixtures are each rejected by the intended automated gate in 100% of test cases.
- **SC-007**: 100% of database-behavior integration tests identify PostgreSQL as the active engine; no SQLite result or mocked transaction is counted as database-behavior evidence.
- **SC-008**: A conforming change receives one reproducible CI result covering all required quality, build, test, contract, compatibility, and migration gates, with no manual verification needed for merge eligibility.
- **SC-009**: A new engineer can locate the approved backend module boundary, frontend transport entry point, contract artifacts, test entry points, and failure diagnostics on the first attempt using repository guidance.
- **SC-010**: Environment validation rejects 100% of controlled empty-value, invalid-environment-name, duplicate-resource, and identical-runtime/admin-database fixtures without printing any supplied secret value.
- **SC-011**: Correlation tests show the correct identifiers on 100% of in-request log records, empty identifiers on 100% of out-of-request records, and zero changed API outcomes when the diagnostic sink is forced to fail.
- **SC-012**: Shared frontend state tests distinguish loading, empty, canonical API failure, unexpected response, and network failure in 100% of controlled cases and preserve a returned request identifier whenever one exists.
- **SC-013**: Controlled origin tests prove 100% of client credential headers are stripped, missing/wrong origin credentials receive the same canonical 403, matcher and rewrite paths match, and no credential value appears in output.
- **SC-014**: Controlled recovery fixtures reject every unresolved, stale, failed, failed-without-remediation-owner, target-exceeding, identity-collision, write-capable, missing-relation, unavailable-category, incomplete-probe, unregistered-probe, incompatible-schema, and probe-execution-failure case without reporting PASS, OK, or readiness. Capacity fixtures reject under-50-identity and under-20-concurrency inputs before network activity; a controlled 50-identity/concurrency-20 result at p95 500 ms can pass, a result above 500 ms fails with a remediation owner, every opened connection/resource closes on success and failure, identities/passwords/tokens/Bearer values/credentialed URLs/secret values are absent from stdout, stderr, and result artifacts, and no fixture or command output is reported as operational evidence or readiness.
- **SC-015**: Adversarial URL, token-assignment, password, cookie, object-key, image, and precise-coordinate strings are absent from 100% of tested log, metric, alert, error, recovery, deployment, and capacity-command outputs after the single canonical sanitizer runs.
- **SC-016**: Automated ownership checks prove that `verify_restore` resolves to `operations`, the cache-table migration has exactly one `operations` leaf and uses the settings table identity, `config/` and `core/` are not Django applications, and no unapproved local application or persistence owner exists.
- **SC-017**: Controlled cache fixtures reject 100% of empty/unknown backend choices and process-local choices outside development—including with debug enabled—while every settings, deployment, throttle, and migration consumer resolves the canonical alias/table/vocabulary without a duplicate literal.

## Assumptions

- This is the first feature specification directory in the repository, so sequential feature number `001` is available.
- No extension hook is configured to create or switch a feature branch; the current branch name is recorded without changing it, and feature-directory numbering remains independent.
- The baseline may include non-business health or probe behavior solely to verify assembly and transport; it does not establish a public business endpoint or domain rule.
- The contract initially contains only foundation-visible operations; later business features add their own routes and schemas through the same generation pipeline.
- Authentication semantics, credentials, login/refresh/logout behavior, RBAC business enforcement, and account state transitions are deferred. `authenticatedFetch` is only the mandatory frontend transport boundary in this feature.
- Production infrastructure provisioning, operator execution of backups/restores/capacity measurements, observability products, object storage integration, and provider-specific choices remain outside this feature; the repository-side origin, deployment, recovery-readiness, restore-verification, capacity-command, evidence-schema, health-check, and runbook primitives explicitly required by CHOT remain in scope.
- The committed environment inventory and its repository-side isolation/readiness checks are in scope; choosing or provisioning the provider resources represented by `UNRESOLVED` entries is not.
- Backward compatibility is evaluated against the merge-base committed contract, and an approved major-version change requires a separate specification decision.
- The two location CSV files are authoritative for the later location feature but are not read, transformed, seeded, or validated by this foundation because locations are explicitly out of scope.
- CHOT §9.4 and decisions R-104/R-106 establish `backend/core/` as the shared-kernel path; `QUY_TAC_CLEAN_CODE.md` §3 has been synchronized to the same canonical name.

## Dependencies

- Project Constitution, especially Principles I, II, VII, VIII, IX, XI, and XII.
- `CHOT_YEU_CAU.md` §1, §7, §8, §9.7, §9.8, §10, and §10.1, including the repository-side origin, deployment, migration, and recovery-readiness controls.
- `QUY_TAC_CLEAN_CODE.md`, including naming, boundary, testing, enforcement-tool, and prohibited-practice rules.
- Decision history R-103 for the contract/error/request-id baseline, R-104 and R-106 for correlation ownership, R-107 for environment validation boundaries, R-108 for migration/recovery checks, and R-109 for shared cache ownership and provisioning.

## Out of Scope

- Authentication and authorization business flows, including login, token lifecycle, password change, user administration, or role behavior.
- Location data, geofencing, or location management.
- Attendance capture, sessions, attempts, anomalies, or reports.
- Task creation, assignment, updates, completion, photos, or field evidence.
- Reporting, exports, notifications, outbox relay behavior, and business audit behavior.
- Provider provisioning, IaC, actual backup/restore/capacity execution, R2 recovery, coordinated database-plus-object recovery, and production readiness certification. Repository-side R-107/R-108/R-109 controls and intentionally failing readiness states are in scope.
- Business `AuditLog`/`OutboxEvent` models, append ports, event delivery, retry/idempotency behavior, and business transaction integration; only the reusable correlation and safety primitives required for those later owners are included.
