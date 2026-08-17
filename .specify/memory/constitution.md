<!--
Sync Impact Report
- Version change: template (unratified) -> 1.0.0
- Modified principles: none; initial project constitution
- Added principles: I-XII
- Added sections: Engineering Constraints; Development Workflow & Quality Gates
- Removed sections: none; template placeholders were resolved
- Follow-up TODOs: TODO(RATIFICATION_DATE): original adoption date was not recorded
-->
# Phần mềm Web Chấm công và Quản lý công việc Helpdesk Constitution

## Core Principles

### I. Source-of-Truth Governance (NON-NEGOTIABLE)

- Business and implementation decisions MUST follow this authority order:
  `CHOT_YEU_CAU.md` -> `QUY_TAC_CLEAN_CODE.md` -> PRD -> current implementation.
- `RA_SOAT_YEU_CAU.md` MUST be treated only as decision history, rationale, and a
  checklist; it MUST NOT introduce a new business rule.
- Conflicts MUST NOT be guessed, merged silently, or resolved from implementation
  precedent. `CHOT_YEU_CAU.md` wins, and the conflict MUST be reported and corrected
  downstream in the same change.
- A new or changed business rule MUST be accepted in `CHOT_YEU_CAU.md` before code,
  schema, API artifacts, or tests are changed. The PRD and clean-code rules MUST then
  be synchronized in authority order.

Rationale: one explicit authority chain prevents code, UX prose, and historical notes
from becoming competing specifications. Verify by traceability in the specification/PR
and a cross-document consistency review.

### II. Fixed Stack and Inward Architecture

- The product MUST use Next.js for the frontend, Django REST Framework for the backend,
  PostgreSQL for persistence, and private S3-compatible storage (AWS S3 or Cloudflare R2)
  for evidence images.
- Backend business modules MUST expose `domain/`, `application/`, `ports/`, and
  `adapters/`. Dependencies MUST point inward: adapters depend on ports/application;
  application coordinates use cases; domain contains pure rules and MUST NOT import
  Django, DRF, boto3, or UI policy.
- Views/controllers, serializers, React components, and management commands MUST remain
  thin. They MUST parse/format, invoke an application use case, and map results; they
  MUST NOT own business transitions, authorization policy, or persistence invariants.
- Production code in one business module MUST NOT import another module's
  `models`, `domain`, or `adapters`; cross-module state access MUST go through an
  application port. Only tests, migrations, and the `config/` composition root are exempt.

Rationale: inward dependencies isolate volatile frameworks and keep rules testable.
Verify with import-boundary tests, architecture review, and dependency/lint checks.

### III. Authorization Is Layered and Ordered (NON-NEGOTIABLE)

- Backend authorization MUST use the centralized `PermissionAction` RBAC matrix and its
  closed implication map. Frontend capabilities MAY control presentation but MUST NOT be
  the enforcement boundary. Direct role checks MUST NOT be scattered through views or
  services.
- RBAC and object-scope authorization MUST both be enforced. Passing an action check MUST
  NOT bypass ownership, creator/assignee scope, target restrictions, or state invariants.
- Every scoped read or mutation MUST execute in this order:
  authentication -> action RBAC and body-independent target authorization -> DTO/input
  validation -> object scope/ownership -> business invariant/state transition -> atomic
  transaction/DB constraint -> audit/event.
- RBAC MUST run before DTO validation. A caller lacking permission MUST receive the
  authorization result even when its payload is malformed; server-owned-field checks
  belong to DTO validation after that permission gate.

Rationale: the order prevents schema leakage, IDOR, and inconsistent policy enforcement.
Verify with allow/deny tests, malformed-body precedence tests, and object-scope tests.

### IV. Server Authority and Boundary Validation

- Input DTOs MUST expose only client-owned or client-reported data. Authenticated actor,
  route-derived action/kind, server timestamps, work date, permission/scope, computed
  distance/result/quality, transition result, anomaly, and audit timestamps MUST remain
  server-owned.
- Client attempts to submit a server-owned field MUST be rejected explicitly; they MUST
  NOT be silently ignored or accepted as optional input.
- Raw payloads MUST be validated at the API boundary before they reach domain logic.
  Domain services MUST receive typed, validated values rather than JSON primitives.
- Server time MUST own time-sensitive business decisions. Client capture time MAY be
  retained for audit/debug but MUST NOT replace server time.

Rationale: authority must reside where identity, time, policy, and invariants can be
trusted. Verify with serializer schema inspection and negative boundary tests.

### V. Database-Backed Invariants and Transaction Boundaries

- PostgreSQL constraints, unique/partial indexes, foreign keys, and compare-and-set or
  row locks MUST be the final protection for concurrency-sensitive invariants. A service
  pre-check alone MUST NOT be considered sufficient.
- Each business use case MUST define one explicit transaction boundary covering the
  state change and every invariant-bound audit/outbox record. Audit/outbox append ports
  MUST join the caller's transaction and MUST NOT commit independently.
- External network or object-storage calls MUST NOT be held inside long database
  transactions. Required external metadata MUST be checked before locking, then mutable
  ownership/state MUST be revalidated inside the transaction.
- Observational records intentionally required to survive a business rollback MUST be
  written only after that business transaction ends, on both success and failure paths,
  and MUST be clearly distinguished from invariant-bound audit/event records.

Rationale: correctness under races depends on PostgreSQL and precise units of work, not
request timing. Verify with schema inspection and PostgreSQL transaction/race tests.

### VI. Auditability, History, and Safe Observability

- Security-sensitive administration, overrides, configuration/location changes, and
  corrections to attendance/task data MUST create immutable, attributable audit evidence.
- Business history MUST be append-only where CHOT defines it as history; cached/snapshot
  state MUST be updated in the same transaction as the history entry that produced it.
- Business state, `AuditLog`, and `OutboxEvent` for one action MUST commit or roll back
  together. Correlation context MUST be infrastructure-owned rather than threaded through
  domain DTOs.
- Secrets, credentials, cookies, tokens, passwords, presigned/photo/map URLs, image data,
  object keys, and precise coordinates MUST NOT appear in audit payloads, outbox payloads,
  or telemetry where forbidden by CHOT. Shared filtering/sanitization MUST run at the
  owning port/sink, not rely on every caller remembering it.
- Telemetry MUST NOT cause the observed business operation to fail. Missing telemetry
  MUST be represented as unknown rather than healthy when health semantics require it.

Rationale: evidence must be durable and useful without becoming a second security leak.
Verify with rollback, immutability, redaction, retention, and health-state tests.

### VII. Stable, Generated API Contracts

- REST JSON APIs MUST follow the canonical versioned namespace and error envelope defined
  by CHOT. Wire fields MUST remain `snake_case`; handwritten duplicate case-mapping layers
  MUST NOT be introduced.
- `contracts/openapi.yaml` MUST be generated deterministically from the backend and
  committed. The TypeScript client/schema MUST be generated from that artifact and
  committed; generated artifacts MUST NOT be edited by hand.
- CI MUST fail on backend/OpenAPI drift, OpenAPI/client drift, or an unapproved breaking
  change. Additive optional changes MAY remain in the current major version; breaking
  changes MUST use the contract evolution/versioning rules in CHOT.
- Schema, examples, generated clients, and public documentation MUST NOT contain secrets,
  credentials, cookies, tokens, passwords, presigned URLs, or precise location examples
  prohibited by the governing documents.

Rationale: one generated contract prevents backend and frontend interpretations from
drifting. Verify by deterministic regeneration, byte-drift checks, and compatibility
comparison against the merge base.

### VIII. Safe Schema Evolution and Deployment

- Migrations MUST use expand-migrate-contract and MUST be compatible with the immediately
  previous application version during rolling deployment. Migration MUST precede rollout.
- A newly required database field MUST have a database-level default or an explicitly safe
  staged backfill before enforcement; a Python/ORM default alone MUST NOT be treated as
  compatibility for old processes.
- Destructive contract operations MUST be delayed to a later release and explicitly marked.
  Each app MUST maintain a single migration leaf unless an intentional merge migration is
  supplied.
- Application runtime MUST NOT possess or read the privileged migration connection.
  Backup/restore readiness and migration safety MUST be represented by executable checks,
  not documentation claims alone.

Rationale: old and new processes share one schema during rollout, so compatibility is a
runtime invariant. Verify with static migration checks, migration tests, and recovery gates.

### IX. Security, Secrets, and Environment Isolation

- Secrets MUST enter processes through the deployment secret store/environment and MUST
  NOT be committed, logged, echoed, embedded in browser bundles, URLs, schema examples,
  audit, or telemetry.
- Deployment configuration MUST be typed and fail closed at startup. Invalid, empty, or
  unresolved production-critical values MUST NOT silently fall back to defaults.
- Development, staging, and production MUST use distinct databases, buckets, cache/queue
  namespaces, signing keys, and credentials. A committed non-secret inventory and CI
  isolation checks MUST make that separation verifiable.
- Private evidence storage, authenticated authorization on every read, short-lived signed
  access, secure token handling, and server-side account-state checks MUST be preserved.
  Authentication MUST NOT replace RBAC/object-scope authorization.

Rationale: secrets and personnel/location evidence require defense in depth across code,
storage, transport, and deployment. Verify with secret scanning, startup validation,
environment-isolation checks, cookie/token tests, and access-control tests.

### X. Location and GPS Domain Integrity

- GPS reported by the device MUST be the sole location measurement for attendance and
  field evidence; image EXIF MUST NOT be used as a location source or cross-check.
- Location identity, hierarchy, coordinates, and seed behavior MUST follow CHOT and the two
  source CSV files. Coincident coordinates and overlapping geofences MUST remain valid;
  records MUST NOT be merged or inferred from display name/address.
- GPS numeric/range validation MUST occur before geometry. Measurement quality and
  geofence membership MUST remain separate gates, with business-specific thresholds read
  from configuration and never cross-used or hardcoded.
- Multiple valid locations MUST NOT be silently resolved by nearest distance, history, or
  business context. Any client selection MUST be recomputed and verified by the backend.
- Attendance and task evidence MUST retain their distinct location semantics as specified
  by CHOT; shared geometry code MUST NOT collapse their different policies.

Rationale: location evidence is safety- and payroll-relevant, while real source data
contains legitimate overlaps. Verify with source-data integrity, boundary, ambiguity, and
domain-specific GPS tests.

### XI. Testing Proves Behavior at the Correct Layer

- Pure domain rules MUST have fast unit and property/boundary tests. API contracts,
  authorization order, object scope, state transitions, audit, and module boundaries MUST
  have integration/contract tests at their owning boundary.
- Every database constraint, transaction promise, lock behavior, rollback rule, and
  concurrency invariant MUST be tested on real PostgreSQL. SQLite and mocks MUST NOT be
  cited as proof of PostgreSQL behavior; concurrency tests MUST use real transactions and
  competing workers/requests where applicable.
- Every fixed bug or changed invariant MUST add a regression test that fails under the
  prohibited behavior. Tests MUST cover both allowed and denied paths and MUST assert the
  absence of forbidden side effects.
- Generated contract checks, migration checks, seed/data checks, architecture checks,
  security/redaction checks, and frontend/backend static checks MUST be automated in CI.

Rationale: the test environment must exercise the mechanism making the guarantee. Verify
through the CI matrix and test markers/configuration proving PostgreSQL-backed execution.

### XII. Maintainable Code and Canonical Naming

- Canonical domain names and enums defined by CHOT/QUY_TAC MUST be used consistently;
  alternate synonyms, raw business-state strings, and boolean substitutes for domain enums
  MUST NOT be introduced.
- Python identifiers MUST use `snake_case`; TypeScript-authored identifiers MUST use
  `camelCase`; classes/types/enums MUST use `PascalCase`; constants MUST use
  `UPPER_SNAKE_CASE`; JSON wire fields MUST use `snake_case`. Measured quantities MUST
  include a unit suffix.
- Business configuration and thresholds MUST come from validated configuration or data.
  Business values MUST NOT be hardcoded or duplicated across modules.
- Functions and components MUST remain cohesive and within the objective complexity,
  nesting, length, and parameter limits established by `QUY_TAC_CLEAN_CODE.md`; exceptions
  require an explicit PR rationale and MUST NOT hide business logic in adapters/UI.

Rationale: a single ubiquitous language and enforceable size limits keep reviews and
changes reliable. Verify through Ruff, mypy, ESLint, TypeScript, AST checks, and review.

## Engineering Constraints

- The shared kernel MUST remain narrow: typed technical primitives, cross-cutting ports,
  correlation, error construction, and shared safety filters only. It MUST NOT become a
  home for unrelated business rules.
- API errors, authorization actions, state enums, configuration keys, metric names/labels,
  and event envelopes MUST use closed canonical vocabularies when governing documents say
  they are closed. New values require a specification/contract change first.
- Read models and derived presentation fields SHOULD be computed at read time when CHOT
  identifies them as derived; they MUST NOT be persisted as a second source of truth.
- Network dependencies beyond the approved stack MUST be justified by an accepted
  specification change, include failure/privacy behavior, and preserve transaction rules.
- Clean-code rules marked mandatory in `QUY_TAC_CLEAN_CODE.md` are constitution-level
  enforcement details by reference and MUST pass CI. A local summary here MUST NOT be used
  to weaken a stricter CHOT/QUY_TAC rule.

## Development Workflow & Quality Gates

1. Before design or implementation, the author MUST identify the controlling CHOT sections,
   relevant clean-code rules, affected contracts/data, and any conflict. A conflict stops
   implementation until resolved at the higher-authority source.
2. Feature specifications MUST contain business-specific workflows, fields, enums, status
   matrices, endpoint details, numeric defaults/limits, role grants, reports, notifications,
   and acceptance examples. They MUST reference this constitution for global engineering
   invariants rather than duplicating it inconsistently.
3. Plans and tasks MUST state module ownership, dependency direction, authorization order,
   transaction boundary, database constraints, audit/event behavior, API/schema impact,
   migration strategy, and required PostgreSQL tests.
4. Every PR MUST pass formatting/linting, type checks, unit/integration/contract tests,
   PostgreSQL database and concurrency tests when applicable, architecture/import guards,
   OpenAPI/client drift and compatibility checks, migration safety checks, secret/security
   checks, and deterministic seed/data validation when affected.
5. Reviewers MUST reject silent conflict resolution, hardcoded business configuration,
   thin-layer violations, authorization-order violations, handwritten generated artifacts,
   SQLite-only concurrency claims, and changes lacking traceability to the controlling rule.

Definition of Done: a change is done only when its accepted specification and authority
trace are current; implementation respects module and ownership boundaries; authorization,
validation, transaction, constraint, audit, contract, migration, and security effects are
explicit; required tests fail on the prohibited behavior and pass on PostgreSQL where
needed; generated artifacts and documentation are synchronized; CI is green; no unresolved
conflict, secret, unexplained TODO, or unreviewed breaking change remains.

## Governance

- This constitution governs global architecture and engineering invariants. It does not
  replace detailed business rules in `CHOT_YEU_CAU.md`; where a detailed rule is stricter,
  the authority chain in Principle I applies.
- An amendment MUST include rationale, affected principles/sections, migration or adoption
  impact, updated verification gates, and a Sync Impact Report. It MUST be reviewed for
  consistency against CHOT, QUY_TAC, the PRD, and applicable implementation.
- Versioning follows semantic versioning: MAJOR for removal or incompatible redefinition of
  governance; MINOR for a new principle or materially expanded obligation; PATCH for
  non-semantic clarification. Ratification/amendment dates use ISO `YYYY-MM-DD`.
- Every feature specification, implementation plan, task set, and PR review MUST include a
  constitution compliance check. Deviations MUST be documented and approved through an
  amendment; a PR note alone cannot waive a MUST.
- Compliance audits MUST verify both the prose and executable gates. If implementation or a
  lower-authority document conflicts with CHOT or this constitution, work MUST stop at the
  affected scope, the conflict MUST be reported, and sources MUST be corrected in authority
  order before proceeding.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): original adoption date was not recorded | **Last Amended**: 2026-08-17
