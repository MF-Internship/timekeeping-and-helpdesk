# Tooling and CI Boundary Contract

The exact task-runner syntax may be finalized during implementation, but each capability below must expose a non-interactive check mode with these observable exit semantics.

## Contract generation

| Capability | Success | Failure |
| --- | --- | --- |
| Generate OpenAPI | Valid candidate generated twice with identical bytes; explicit update mode writes `contracts/openapi.yaml`. | Non-determinism, schema warning/error, unsafe content, bad namespace/name, or unauthorized drift exits nonzero and names the artifact/rule. |
| Generate frontend schema | `schema.ts` is reproducible from committed OpenAPI; explicit update mode writes it. | Invalid input or byte drift exits nonzero and names `frontend/src/shared/api/schema.ts`. |
| Compatibility check | Candidate has no unapproved breaking change against merge-base artifact. | Removal, incompatible type/operation change, or newly required request field exits nonzero with a safe summary. |

The first introduction is the only case where a missing merge-base contract is acceptable. If the merge base contains a contract, inability to load or compare it is a failure.

## Migration static check

Inputs are repository migration `.py` files and controlled fixtures. The checker must not import project/application modules, initialize Django, inspect environment secrets, or connect to a database.

It exits nonzero for:

- a migration owned by `config/` or another unapproved persistence owner;
- cache-table provisioning outside `operations` or a cache-table identity that
  does not consume `core.cache.THROTTLE_CACHE_TABLE`;
- more than one leaf for an app without an intentional merge migration;
- a new `NOT NULL` field without `db_default`;
- destructive remove/rename/type-contraction behavior lacking `RELEASE_PHASE = "contract"`;
- expansion and destructive contraction mixed in one migration.

Diagnostics include rule ID, relative path, and line where available, never evaluated source values.

## Deployment checks

- `isolation`: verifies schema, approved environment names, absence of credentials/full DSNs, uniqueness of protected resource identities, and runtime/admin DB separation. It is a normal CI gate.
- `production-ready`: exits nonzero while any production field is `UNRESOLVED` and lists field paths. It is an explicit readiness command, not a claim made by ordinary quality CI.
- Startup validation independently rejects missing, empty, unresolved, invalid, or cross-field-inconsistent runtime configuration before Django settings load.

## Architecture and maintainability checks

- Domain files cannot import Django, DRF, psycopg, boto3, Next/UI policy, adapters, or ORM code.
- Production cross-module imports of another module's `models`, `domain`, or `adapters` fail; only tests, migrations, and `config/` have closed documented exemptions.
- Any present business module must expose `domain`, `application`, `ports`, and `adapters` boundaries.
- `config/` is composition root only and `core/` is a non-app pure technical
  boundary. Tests reject `config/apps.py`, `config/management/`,
  `config/migrations/`, registration of `config` or `core`, and any local Django
  app outside the approved allowlist.
- Django command discovery must resolve `verify_restore` to `operations`; the
  command remains a thin shim over `core.recovery`.
- Authored Python/TypeScript files satisfy naming, type, function/component length, parameter, nesting, and complexity limits from `QUY_TAC_CLEAN_CODE.md`.
- Generated-code exclusions are exactly `contracts/` and `frontend/src/shared/api/**` as authorized by QUY_TAC; handwritten `client.ts` is kept thin by TypeScript, architecture checks, and review.

## Origin, deployment, and recovery checks

- `deployment_check.py isolation` is a CI gate. `production-ready`,
  `recovery-ready`, and `smoke` are operator commands and MUST NOT become CI
  gates; unresolved values intentionally make readiness nonzero.
- Proxy tests prove client source headers are stripped before a server credential
  is attached and that middleware matcher equals rewrite source. Origin tests
  prove constant-time, indistinguishable canonical 403 denial. Smoke prints only
  status.
- Recovery checks reject unresolved/stale/failed/failed-without-remediation-owner/target-exceeding
  evidence. Restore verification rejects identity matches before connecting and
  is read-only; missing relations/categories/registrations, incomplete probes,
  incompatible schemas, and probe failures are unverifiable non-successes.
  Capacity measurement rejects fewer than 50 distinct real identities or
  concurrency below 20 before network I/O, accepts p95 at most 500 ms, and
  records p95 above 500 ms as failed with a remediation owner. Every opened
  connection/resource closes on success and failure. Identities, passwords,
  tokens, Bearer values, credentialed URLs, and secret values are absent from
  stdout, stderr, and returned/result artifacts. Fixtures are not operational
  evidence, and command output cannot itself make production/recovery readiness
  true.
- Cache checks import `core.cache` definitions, require exactly one alias,
  reject process-local storage outside development regardless of debug, and
  prove that settings and the operations migration use the same table identity.

## Required CI evidence

1. Lockfile-only installation.
2. Backend and frontend formatting, lint, type, structural, unit, and build checks.
3. Live PostgreSQL integration with explicit vendor proof and no fallback.
4. HTTP error/request/correlation integration and concurrency tests.
5. Two-pass OpenAPI and frontend generation, drift, protected-content, and compatibility checks.
6. Migration unsafe/safe fixture checks.
7. Environment inventory isolation checks.
8. Django app/command/migration ownership and cache identity checks.

Every failure names the violated rule and affected path without printing secrets or matched protected values.
