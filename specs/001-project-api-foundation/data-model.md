# Data Model: Project Foundation and API Contract Baseline

This feature introduces no business database entity. It introduces exactly one approved technical persistence artifact: the Django DatabaseCache table provisioned by an `operations` migration under R-109. The remaining “entities” below are technical value objects, generated artifacts, validation results, and frontend state and must not become persistent tables merely because they appear here.

## RuntimeSettings

Immutable configuration value created before Django settings load.

| Field | Type | Rules |
| --- | --- | --- |
| `environment` | enum | Exactly `development`, `staging`, or `production`. |
| `debug` | boolean | Explicitly parsed; production cannot enable unsafe defaults. |
| `secret_key` | secret string | Required and non-empty; value never appears in diagnostics or repr. |
| `database_url` | secret DSN | PostgreSQL only; runtime connection only. |
| `api_docs_enabled` | boolean | Controls registration of the machine-readable schema route only. |
| `cache_backend` | closed choice | `locmem`, `database`, or `redis`; empty/unknown fails. Process-local choices are development-only. |
| environment-specific identities | non-secret identifiers | Cross-checked against the committed inventory. |

Lifecycle: raw environment → normalized presence/type validation → cross-field validation → immutable `RuntimeSettings` → Django settings translation. Any failure terminates startup with key names only.

`RuntimeSettings` intentionally has no migration-admin field or reader. A separate deployment-check process receives `MigrationAdminSettings`, compares its safe identity with the runtime identity, and is never imported by `backend/config/` or application runtime.

## ResourceIdentity and EnvironmentInventory

Credential-free deployment identities used only for repository/deployment validation.

| Field | Type | Rules |
| --- | --- | --- |
| `environment` | enum | One entry for each approved environment. |
| `database_identity` | string / `UNRESOLVED` | Unique across environments; no DSN, username, or password. |
| `migration_identity` | string / `UNRESOLVED` | Distinct from runtime identity and unavailable to app runtime. |
| `bucket_identity` | string / `UNRESOLVED` | Unique, although object-storage implementation is deferred. |
| `cache_queue_namespace` | string / `UNRESOLVED` | Unique cache/queue namespace identity; never a credential. |
| `cache.backend` | closed non-secret choice | Resolved for every environment; shipped staging/production value is `database`; process-local is development-only. |
| `signing_key_identity` | string / `UNRESOLVED` | Identifier only, never key material. |
| `credential_identity` | string / `UNRESOLVED` | Identifier only, never credential material. |

State: an inventory can be `source_valid` while production readiness is `blocked_by_unresolved`. Replacing `UNRESOLVED` requires an approved infrastructure/governance decision, not an implementation guess.

## CacheConfiguration

Pure technical configuration whose vocabulary is owned only by `core.cache`.

| Field | Type | Rules |
| --- | --- | --- |
| `alias` | canonical string | `THROTTLE_CACHE_ALIAS`; settings and throttle consumers use the same value. |
| `table` | canonical string | `THROTTLE_CACHE_TABLE`; settings and the operations migration use the same value. |
| `backend` | closed choice | One of `CACHE_BACKEND_CHOICES`: `locmem`, `database`, `redis`. |
| `process_local` | boolean classification | Derived from the canonical classification; `LocMemCache`, `DummyCache`, and `FileBasedCache` are rejected outside development. |

`core.cache` imports no Django. Settings translate the selected choice into one
Django `CACHES` entry; deployment checks and future throttle code import the
same canonical definitions rather than copying literals.

## ThrottleCacheTable

The sole technical table introduced by this foundation.

| Attribute | Rule |
| --- | --- |
| Persistence owner | Approved `operations` Django application. |
| Provisioning | One operations migration using the approved create-cache-table mechanism. |
| Name | Exactly `core.cache.THROTTLE_CACHE_TABLE`; not environment-configurable. |
| Sequence | Next valid migration number from the actual operations graph; currently `0001`. |
| Verification | Static ownership/identity/leaf checks plus a real PostgreSQL migration/provisioning test. |

It stores framework cache entries, not business entities, audit records, outbox
events, credentials, or recovery/capacity evidence.

## RequestCorrelationContext

Execution-context-local infrastructure value.

| Field | Type | Rules |
| --- | --- | --- |
| `request_id` | UUIDv4 string or empty | Always server-generated in requests; empty outside a request. |
| `correlation_id` | UUIDv4 string or empty | Defaults to `request_id`; no client header can establish it. |

State transitions:

1. `empty` before request entry.
2. `bound` after middleware creates identifiers.
3. `visible` to infrastructure during request execution and spawned context-aware work.
4. `reset` in `finally`, including exception paths.

Concurrent contexts must never observe or clear one another.

## ApiErrorEnvelope

Client-visible JSON value.

| Field | Type | Rules |
| --- | --- | --- |
| `error_code` | governed string vocabulary | This feature uses only CHOT-authorized codes; later codes require authority-chain and contract ownership. |
| `message` | safe Vietnamese string | Displayable; no exception internals or protected values. |
| `details` | object | `{}` when absent; field errors are arrays of safe messages. |
| `request_id` | UUIDv4 string | Equal to response `X-Request-Id`. |
| `error` | deprecated string mirror | Exactly equal to `error_code` throughout v1. |
| top-level field mirrors | deprecated arrays | Derived from field entries in `details`; cannot overwrite canonical keys. |

Canonical keys are authoritative. Any incoming detail whose key collides with a canonical or reserved compatibility key is kept only in a safe nested representation or rejected by the builder; it never changes canonical fields.

## ApiContractArtifact

Committed generated file at `contracts/openapi.yaml`.

| Attribute | Rule |
| --- | --- |
| Format | OpenAPI 3.0.3 YAML with normalized UTF-8/LF output. |
| Version | Fixed `info.version: 1.0.0` for this v1 baseline. |
| Paths | Every application operation begins `/api/v1/`. |
| Operations | Explicit, unique, stable operation IDs. |
| Properties | `snake_case`; protected schema content prohibited. |
| Provenance | Backend source only; never handwritten. |

Lifecycle: backend source → candidate generation → schema validation → safety/path/name scans → second generation byte comparison → explicit committed update → frontend generation.

## GeneratedClientArtifact

Committed generated file at `frontend/src/shared/api/schema.ts`.

| Attribute | Rule |
| --- | --- |
| Input | Only committed `contracts/openapi.yaml`. |
| Output | TypeScript schema/path types preserving `snake_case`. |
| Ownership | Generated; manual edits forbidden. |
| Transport | The handwritten client assembly injects `authenticatedFetch`; generated output owns no fetch policy. |

## MigrationSafetyFinding

Static result produced without imports or a database.

| Field | Type | Rules |
| --- | --- | --- |
| `rule_id` | closed string | Identifies leaf, required-field, release-phase, or mixed-operation rule. |
| `path` | repository-relative path | Always present and safe to print. |
| `line` | positive integer / absent | Included when AST location exists. |
| `message` | safe string | Explains remediation without evaluating application data. |
| `severity` | `error` | Foundation rules are merge-blocking. |

No source literal containing a secret or protected example may be echoed in a finding.

## RecoveryEvidence

Committed non-secret document whose policy and evidence are deliberately separate.

| Field group | Rules |
| --- | --- |
| `targets` | RPO 24 hours, RTO 4 hours, backup retention 30 days, and p95 500 ms. |
| `drill` | Timestamp, measured RPO/RTO, verified categories, isolated restore identity, `passed`/`failed`, and remediation owner when failed; initially `UNRESOLVED`. |
| `capacity` | Timestamp, at least 50 distinct real identities, concurrency at least 20, measured p95 at most 500 ms for `passed`, otherwise `failed` with remediation owner; under-minimum input is rejected before network activity; all opened resources close on success/failure; stdout, stderr, and result artifacts exclude identities, passwords, tokens, Bearer values, credentialed URLs, and secrets; initially `UNRESOLVED`. |

`recovery-ready` is false for unresolved, stale, failed,
failed-without-remediation-owner, or
target-exceeding evidence. The file records operator evidence; creating the file
does not assert that a restore or measurement happened.
Controlled fixtures and command output are not operator evidence and cannot by
themselves make production/recovery readiness true.

## OriginCredentialSettings

Server-only technical configuration: an approved header name and secret value of
at least 32 characters. The browser cannot set the effective value because the
edge removes the incoming header before attaching its own. The origin compares
in constant time and emits only the already-authorized canonical permission
denial; neither value is a frontend/public field.

## Frontend ApiFailure and AsyncState

`ApiFailure` is a discriminated union:

- `canonical`: validated `ApiErrorEnvelope`, including optional field mirrors and support request ID.
- `unexpected_response`: an HTTP response that is not a valid canonical envelope; may preserve a safe server request-ID header.
- `network`: no contract response was received; must not fabricate a request ID.

`AsyncState<T>` transitions among `idle`, `loading`, `success`, `empty`, and `failure`. A retry action exists only when the owning operation supplies a callback; the state model does not claim idempotency.

## Database schema, constraints, and indexes

There is one approved technical DatabaseCache table and no business table,
foreign key, business unique constraint/index, audit/outbox record, or business
data migration. The table is owned only by the `operations` migration and its
identity cannot drift from settings. Django's connection and migration executor
are exercised against PostgreSQL to prove provisioning. The first business
feature that introduces persistence must define its own schema,
expand/migrate/contract path, transaction boundary, constraints, indexes,
authorization scope, audit/outbox behavior, and PostgreSQL race tests.
