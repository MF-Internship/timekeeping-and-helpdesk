# Research: Project Foundation and API Contract Baseline

## Repository and governance baseline

**Decision**: Treat the repository as a greenfield application workspace and create no compatibility bridge to nonexistent code. Use `backend/core/` as the single shared kernel, with `backend/config/` as the sole composition root.

**Rationale**: Repository inspection found governing documents and feature artifacts but no Django project, Next.js project, dependency manifest, CI workflow, or existing module pattern to reuse. CHOT §9.4 and accepted decisions R-104/R-106 establish `backend/core/`; QUY_TAC and the PRD are synchronized to that authority before implementation. The two location CSVs are later-domain source data and are intentionally neither parsed nor validated by this feature.

**Alternatives considered**:

- Create both `core` and `shared`: rejected because it fragments the shared kernel.
- Create empty business apps to demonstrate the convention: rejected because it would imply ownership and domain decisions explicitly outside this feature.
- Create a second shared-kernel path: rejected under the project's authority order.

## Runtime versions and package managers

**Decision**: Target Python 3.12 with Django 5.2 LTS and DRF 3.16; target Node.js 22 LTS with Next.js 16, React 19, and strict TypeScript 5.x. Use uv with committed `uv.lock` for Python and npm with committed `package-lock.json` for frontend dependencies.

**Rationale**: The clean-code policy names Python 3.12. Django 5.2 is an LTS release and officially supports Python 3.12; DRF 3.16 officially supports Django 5.2. Next.js 16 requires Node 20.9 or newer, so Node 22 LTS is a conservative supported runtime. uv's documented locked/frozen synchronization supports reproducible CI, while npm is the smallest standard toolchain for the new Next.js project.

**Alternatives considered**:

- Python 3.13: supported by Django but not the repository's named target.
- Latest DRF without a documented pairing: unnecessary churn for a foundation baseline.
- pnpm/yarn: no approved repository precedent or requirement justifies another package manager.

**Primary references**: [Django 5.2 release notes](https://docs.djangoproject.com/en/dev/releases/5.2/), [DRF 3.16 announcement](https://www.django-rest-framework.org/community/3.16-announcement/), [Next.js 16 upgrade guide](https://nextjs.org/docs/app/guides/upgrading/version-16), [Next.js installation requirements](https://nextjs.org/docs/app/getting-started/installation), [uv project synchronization](https://docs.astral.sh/uv/concepts/projects/sync/).

## Minimal approved dependency set

**Decision**: Limit backend runtime dependencies to Django, DRF, psycopg 3, and drf-spectacular. Limit frontend runtime dependencies to Next.js, React, React DOM, and openapi-fetch; use openapi-typescript and quality/test tools as development dependencies. Pin oasdiff in CI for breaking-change detection.

**Rationale**: Every dependency directly implements an accepted requirement. Standard-library environment parsing avoids adding a configuration package; no queue, cache, storage, telemetry product, task worker, auth SDK, or CSS framework is required. openapi-fetch supports a custom fetch implementation, making the mandatory transport chokepoint possible without handwritten endpoint duplication.

**Alternatives considered**:

- `django-environ` or `dj-database-url`: rejected because typed parsing and safe DSN identity checks are small, security-sensitive foundation code and need no new runtime dependency.
- Axios: rejected because native fetch plus openapi-fetch supplies the required transport and typed client.
- Celery/Redis/Sentry/boto3: rejected as out-of-scope infrastructure.

**Primary references**: [drf-spectacular schema and client workflow](https://drf-spectacular.readthedocs.io/en/latest/client_generation.html), [openapi-typescript](https://openapi-ts.dev/introduction), [openapi-fetch custom fetch API](https://openapi-ts.dev/openapi-fetch/api), [oasdiff breaking-change checks](https://github.com/oasdiff/oasdiff/blob/main/docs/BREAKING-CHANGES.md).

## PostgreSQL-only foundation

**Decision**: Use PostgreSQL 17 for local and CI services with psycopg 3. Do not define a SQLite settings variant. Keep Django installed applications database-minimal so the foundation does not select a user model or create unrelated business tables.

**Rationale**: The constitution requires PostgreSQL evidence for database, transaction, migration, and concurrency claims. A SQLite fallback would let a missing service appear healthy. Avoiding stock auth/admin database apps also prevents this foundation from silently deciding the later authentication model.

**Alternatives considered**:

- SQLite for fast unit tests: unnecessary because pure units do not require Django's database and DB-marked tests must use PostgreSQL.
- Install all default Django contrib apps: rejected because their migrations and stock user model expand the feature into authentication concerns.
- PostgreSQL 16: technically acceptable, but 17 gives one clear pinned service baseline; application SQL must remain portable across currently supported PostgreSQL releases unless a later decision says otherwise.

## Error and request-correlation boundary

**Decision**: Generate a UUIDv4 for every server request in the outer API middleware; ignore all client request-ID values; bind request and correlation identifiers in `contextvars`; clear them in `finally`. Produce errors only through one canonical builder plus adapters for error codes already authorized by CHOT. This feature assigns no new generic framework error vocabulary.

**Rationale**: This directly implements CHOT §10, R-103, R-104, R-106, and FR-009 through FR-015. Context-local binding prevents infrastructure metadata from contaminating domain DTOs. `VALIDATION_FAILED` and `PERMISSION_DENIED` are already authorized; inventing names for 404/405/415/500 would be a new governance decision.

**Alternatives considered**:

- Trust a valid client UUID: explicitly forbidden.
- Thread IDs through every service call: violates infrastructure ownership.
- Let each exception handler construct its own shape: risks compatibility-mirror drift and key collisions.
- Adopt an external tracing SDK now: no approved observability product or infrastructure requirement.

## OpenAPI generation and compatibility

**Decision**: Generate OpenAPI 3.0.3 from drf-spectacular with fixed version `1.0.0`, validate warnings as errors, normalize output deterministically, and commit `contracts/openapi.yaml`. Generate `frontend/src/shared/api/schema.ts` with openapi-typescript. Use byte-drift checks and a pinned oasdiff merge-base check.

**Rationale**: drf-spectacular documents schema generation with validation and is designed for accurate client generation. openapi-typescript preserves wire names and generates types without a second mapping source. oasdiff provides a purpose-built breaking-change classifier. Two-pass byte comparison makes non-determinism visible rather than merely comparing the final working tree.

**Alternatives considered**:

- Handwritten OpenAPI: rejected because the backend must be authoritative.
- Generate the client directly from a live server: rejected because it bypasses the committed contract and makes builds environment-dependent.
- Generic textual diff for compatibility: useful for drift but unable to distinguish additive optional changes from breaking changes.
- Interactive schema UI: explicitly forbidden for this feature.

## Frontend transport and failure ownership

**Decision**: Make `authenticatedFetch` fetch-compatible and inject it into openapi-fetch. It supplies same-origin credentials, no-store caching, JSON defaults, and cancellation but owns no token lifecycle or automatic retries. Parse contract errors into a shared discriminated failure type and render them through shared async-state components.

**Rationale**: A fetch-compatible seam is easy to test and guarantees both generated and handwritten wrappers use one transport. Retry safety depends on the later operation's semantics, so the foundation can expose a retry callback without deciding idempotency.

**Alternatives considered**:

- Embed login/refresh logic: authentication flow is explicitly out of scope.
- Retry all network failures automatically: unsafe for later non-idempotent mutations.
- Let each screen parse errors: duplicates contract semantics and loses request IDs.

## Configuration and environment inventory

**Decision**: Parse environment variables into immutable typed settings before Django loads; accept only development/staging/production; reject empty and unresolved critical values; compare safe database identities; commit a credential-free resource inventory with explicit `UNRESOLVED` production entries.

**Rationale**: R-107 requires fail-closed startup, separation of runtime/admin database access, and verifiable environment isolation without pretending undecided production resources exist. Key/path-only diagnostics allow failures to be actionable without echoing secret values.

**Alternatives considered**:

- Development defaults reused in production: explicitly unsafe.
- Put full DSNs in the environment inventory: violates the non-secret manifest requirement.
- Make unresolved production resources fail every source-quality CI job: incorrectly conflates readiness with code validity.

## Static migration safety

**Decision**: Build `scripts/migration_check.py check` as an AST-only analyzer. It identifies migration graph leaves, rejects every new `NOT NULL` field without `db_default`, recognizes destructive remove/rename/contraction operations, and requires an isolated `RELEASE_PHASE = "contract"` migration in a later release without importing modules or opening a database connection.

**Rationale**: R-108 requires an early, deterministic, side-effect-free gate. AST parsing is sufficient for prohibited structural patterns; it does not replace future PostgreSQL migration tests or deployment recovery checks.

**Alternatives considered**:

- Import migrations through Django: violates the static/no-side-effect requirement and can execute application imports.
- Text regex only: too brittle for Python syntax and structured operations.
- Claim full rolling compatibility from static analysis: rejected; compatibility still needs real schema-owner tests.

## Deployment origin and recovery readiness

**Decision**: Include the complete repository-side R-107/R-108/R-109 controls without
claiming provider work has happened: non-secret environment/backup identities,
source-credential proxy and constant-time origin guard, deployment/runbook
checks, unresolved recovery evidence, read-only restore verification, restore
health, and a capacity-measurement command with minimum input gates.

**Rationale**: These are executable foundation requirements in CHOT. Leaving
them to a later business feature would make environment isolation and recovery
readiness documentation-only. Conversely, filling provider choices or evidence
with guessed values would falsely certify production.

**Alternatives considered**:

- Omit origin controls because WAF/provider configuration is external: rejected;
  R-107 requires an independently testable origin guard in the repository.
- Commit a passing drill/capacity example: rejected; no drill or measurement has
  occurred, so evidence remains `UNRESOLVED` and readiness stays nonzero.
- Put readiness/smoke/capacity in CI: rejected by R-108; only migration static
  checking and environment isolation are CI gates.

## Recovery command discovery without a new Django app

**Decision**: Keep recovery orchestration in pure `backend/core/recovery.py` and
place only the thin discoverable management-command shim at
`backend/operations/management/commands/verify_restore.py`. `operations` is the
already-approved operational integration owner and is also required by R-109
for the cache-table migration. `config/` remains composition root only and
`core/` remains a non-app technical boundary.

**Rationale**: Django discovers management commands only through installed
applications. The repository currently has no implemented `INSTALLED_APPS` or
command pattern to reuse, but QUY_TAC already assigns operational adapters to
`operations` and R-109 fixes migration ownership there. Reusing that approved
owner avoids inventing a command-only app and keeps the command a testable shim.

**Alternatives considered**:

- Add `config/apps.py` or `config/management/`: rejected; composition is not app
  ownership and R-107/R-108 forbid creating an app for this purpose.
- Register `core` as an app: rejected; it must remain pure and importable before
  Django configuration.
- Create `recovery` or `infrastructure` as another app: rejected; no authority
  approves another application or persistence owner.
- Put recovery rules in `Command.handle`: rejected; management commands remain
  thin and recovery behavior must be testable independently.

Recovery verification is successful only when every required relation,
category, and registered probe is available, schema-compatible, executed, and
complete. Missing relations/categories/registrations, partial results,
incompatible schemas, and execution failures are deterministically
`incomplete/unverifiable`, exit nonzero, and cannot produce PASS, OK, or
readiness.

Restore-health state evaluation remains a pure value-model/function in
`core.recovery_health`. Operational evidence orchestration belongs to
`operations.application.recovery_health`, and alert/telemetry emission belongs
to `operations.adapters.recovery_alerts`. This preserves the approved inward
dependency direction and keeps core free of Django and operational adapters.

## Shared throttle-cache ownership and provisioning

**Decision**: Make pure `backend/core/cache.py` the single source for
`THROTTLE_CACHE_ALIAS`, `THROTTLE_CACHE_TABLE`, `CACHE_BACKEND_CHOICES`, and
process-local backend classification. `config/settings.py`,
`scripts/deployment_check.py`, future throttle consumers, and the approved
`operations` migration consume these definitions. Settings expose exactly one
cache alias. Development/test may retain the approved `locmem` fallback; the
shipped staging/production inventory selects `database`.

**Rationale**: R-109 makes throttle counters deployment-wide and explicitly
rejects duplicated alias, table, vocabulary, and process-local classification.
DatabaseCache uses the already-required PostgreSQL and adds no runtime
dependency. Keeping the constants Django-free lets deployment checks run before
framework configuration.

**Migration sequence**: No `operations` migration exists in the current tree or
local Git history, so the current valid path is
`operations/migrations/0001_throttle_cache_table.py`. The implementation task
must inspect the graph again and use the next valid number if earlier migrations
arrive before execution; it must not force historical `0005` onto a different
graph. The migration uses the approved create-cache-table mechanism and the
canonical table constant.

**Alternatives considered**:

- Provision under `config/migrations/`: rejected; `config` is not an app and owns
  no persistence.
- Configure the table name independently in settings and migration: rejected;
  two owners can drift silently.
- Copy the backend vocabulary into deployment tooling: rejected; deployment
  checks must import the pure canonical source.
- Add Redis support as a dependency now: rejected; R-109 permits the vocabulary
  entry but requires fail-closed package-availability checking.
- Fail open when cache storage is unavailable: rejected; that silently removes
  the published throttle guarantee.

## Capacity evidence thresholds

**Decision**: A controlled capacity result is eligible to pass only with at
least 50 distinct real identities, concurrency at least 20, and p95 at most
500 ms. Under-minimum inputs fail before network activity; p95 above 500 ms is
`failed` with a remediation owner. Every opened connection/resource closes on
success and failure. Identities, passwords, tokens, Bearer values, credentialed
URLs, and secret values are absent from stdout, stderr, and returned/result
artifacts. Fixtures are not real evidence, and command output cannot itself make
production/recovery readiness true.

**Rationale**: These values synchronize CHOT/R-108 and PRD NFR-29. Fixtures prove
command semantics but never become operator evidence or production-readiness
evidence.

## CI topology

**Decision**: Split CI into quality and contract/integration workflows while keeping both required for merge. Use pinned Python 3.12, Node 22, and PostgreSQL 17; install only from lockfiles. Preserve a matching pre-commit subset for fast local feedback.

**Rationale**: Separating fast static/unit feedback from service-backed/contract work improves diagnosis without weakening the single merge gate. Every required check remains reproducible and non-interactive.

**Alternatives considered**:

- One monolithic job: simpler YAML but slower feedback and less actionable failures.
- Large runtime/version matrix: not required for the first approved baseline.
- CI-only formatting behavior: rejected because developers need the same commands locally and in pre-commit.
