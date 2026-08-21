# Feature Specification: Code Quality, Build, CI/CD and Production Release Hardening

**Feature Branch**: `feature/016-release-hardening`

**Created**: 2026-08-21

**Status**: Draft

**Input**: Final engineering hardening of the functionally complete Helpdesk Attendance and Task Management application without changing business behavior.

## User Scenarios & Testing

### User Story 1 - Trust One Reproducible Quality Gate (Priority: P1)

As a maintainer, I can run one documented release verification from a clean repository and receive the same pass or fail decision that pull-request validation uses.

**Why this priority**: A release decision is unsafe when local, automated, and production-build assumptions disagree.

**Independent Test**: Run the release gate from a clean checkout with declared non-production prerequisites and confirm every machine-verifiable category reports a deterministic result without modifying source files.

**Acceptance Scenarios**:

1. **Given** a clean checkout with supported runtimes and services, **When** the release gate runs, **Then** formatting, static quality, typing, architecture, migrations, contracts, tests, builds, backend checks, and deployment-isolation checks all execute through canonical commands.
2. **Given** a source, generated-contract, migration, or test defect, **When** the same gate runs locally and in pull-request validation, **Then** both fail in the owning category with an actionable diagnostic.
3. **Given** unresolved real-production evidence, **When** machine-verifiable checks pass, **Then** production and recovery readiness remain pending rather than being reported as passed.

---

### User Story 2 - Reproduce Builds and Tests on Clean Machines (Priority: P1)

As a release engineer, I can install locked dependencies and build and test the application on a clean machine without developer caches, uncommitted generated files, local-only assets, or secret production values.

**Why this priority**: A successful developer build is not evidence that a clean release runner can reproduce it.

**Independent Test**: Remove only disposable caches, install from committed dependency locks, regenerate/check owned artifacts, and execute frontend and backend production-oriented checks.

**Acceptance Scenarios**:

1. **Given** no previous dependency or build cache, **When** declared dependencies are installed, **Then** lockfiles remain unchanged and installation succeeds with the canonical package managers and runtime versions.
2. **Given** scoped non-production configuration, **When** frontend production build and backend system checks run, **Then** they succeed without weakening fail-closed production configuration.
3. **Given** a missing committed asset or generated artifact, **When** the clean build runs, **Then** it fails and identifies the missing or drifting artifact.

---

### User Story 3 - Diagnose Automation Failures at Their Root Cause (Priority: P2)

As a maintainer, I can inspect every validation workflow and understand its purpose, prerequisites, commands, and failures, with required failures corrected instead of bypassed.

**Why this priority**: Green automation is meaningful only when required checks still enforce the governing rules.

**Independent Test**: Review every workflow and inject or reproduce representative format, type, contract, migration, test, and build defects to confirm the owning job fails without optional-error mechanisms.

**Acceptance Scenarios**:

1. **Given** the workflow inventory, **When** each job is compared with canonical local commands, **Then** runtime, working-directory, service, dependency, environment, and artifact assumptions are consistent.
2. **Given** a required job failure, **When** it is resolved, **Then** the record identifies the actual cause, corrective change, and targeted verification.
3. **Given** a pull request from a non-release branch, **When** validation runs, **Then** production deployment credentials are not exposed and production deployment is not triggered.

---

### User Story 4 - Preserve Contract and Migration Safety (Priority: P2)

As an operator, I can rely on automated release validation to reject API drift, unsafe schema evolution, database-model drift, and concurrency claims not proven against the required database engine.

**Why this priority**: Contract and schema defects can break rolling releases or corrupt production state despite passing shallow checks.

**Independent Test**: Regenerate contracts, inspect migration state and graph policy, and execute integration and concurrency suites against the required database service.

**Acceptance Scenarios**:

1. **Given** unchanged backend behavior, **When** contracts are regenerated, **Then** committed backend and frontend generated artifacts remain byte-stable and operation identifiers remain explicit, unique, and stable.
2. **Given** model definitions and committed migrations, **When** migration validation runs, **Then** drift, multiple unintended leaves, and unsafe expand/contract patterns fail.
3. **Given** transaction, constraint, rollback, deduplication, and race guarantees, **When** their suites run, **Then** evidence comes from real PostgreSQL behavior and not a substitute database.

### Edge Cases

- A check passes only because a stale incremental cache or locally generated file exists.
- A test depends on wall clock, timezone, random order, leaked global browser state, or race timing.
- A production build reads a developer-only environment file or absolute local path.
- A required environment value is absent for a system check but must remain mandatory in production.
- A workflow cache restores dependencies for a different runtime or lockfile.
- A contract generator emits nondeterministic ordering or duplicate operation identifiers.
- A migration history has multiple leaves or model drift but generating a new migration would hide an unsafe historical defect.
- Production, recovery, capacity, device, DNS/TLS, or external-service evidence cannot truthfully be produced in development or CI.

## Requirements

### Functional Requirements

- **FR-001**: The repository MUST provide deterministic check-only and write-mode formatting workflows for all applicable authored frontend and backend source while excluding generated, dependency, build, coverage, and disposable test-result artifacts.
- **FR-002**: Required automated validation MUST run formatting in check-only mode and MUST NOT modify committed source.
- **FR-003**: Frontend and backend lint/static-quality configurations MUST be valid, enforce existing approved rules, and use only narrow documented suppressions where a tool cannot model correct behavior.
- **FR-004**: Strict frontend type validation and existing backend static/framework validation MUST pass independently of production builds.
- **FR-005**: The real frontend production build MUST pass without disabled type or lint validation and without relying on development-server behavior.
- **FR-006**: Backend system and deployment-oriented checks MUST use explicit scoped non-production configuration while preserving fail-closed production requirements.
- **FR-007**: Frontend and backend unit, contract, architecture, integration, and required concurrency tests MUST pass and MUST be deterministic with respect to time, timezone, random state, ordering, browser globals, transactions, and synchronization.
- **FR-008**: PostgreSQL-specific constraints, transactions, rollback, deduplication, migration behavior, and concurrency guarantees MUST continue to be verified using PostgreSQL.
- **FR-009**: Committed OpenAPI and generated frontend API artifacts MUST be reproducible from their canonical owners, remain synchronized, and fail validation on drift or unapproved incompatibility.
- **FR-010**: API operation identifiers MUST remain explicit, unique, and stable unless an authoritative contract correction requires change.
- **FR-011**: Model definitions and committed migrations MUST remain synchronized, and validation MUST enforce graph, leaf, expand/contract, compatibility, and privileged-identity separation rules.
- **FR-012**: Every repository validation workflow MUST have an inventory of purpose, trigger, dependencies, services, required configuration, commands, and known defect status.
- **FR-013**: Required automation failures MUST be fixed at root cause; required checks MUST NOT be bypassed, skipped, weakened, retried until green, or replaced with less representative validation.
- **FR-014**: Local and automated validation MUST call shared canonical repository commands wherever practical so quality rules and command grouping do not drift.
- **FR-015**: Dependency installation MUST use one canonical frontend package manager with the committed lockfile in immutable mode and preserve the existing reproducible backend dependency process.
- **FR-016**: Supported runtime and service versions MUST be consistent across declarations, local guidance, containers, and automation, without an unrelated major upgrade.
- **FR-017**: The committed environment example MUST distinguish build-time, runtime, test, and production-only requirements, contain no secrets, and preserve production fail-closed behavior.
- **FR-018**: Validation workflows MUST avoid logging credentials or sensitive headers, MUST keep validation separate from deployment, and MUST NOT grant production deployment access to ordinary pull requests.
- **FR-019**: A clean-build simulation MUST prove that verification does not depend on old dependency directories, build caches, bytecode, uncommitted files, developer secrets, or absolute local paths.
- **FR-020**: The repository MUST expose one reproducible final release-check entry point that orchestrates existing canonical checks without duplicating their implementation logic.
- **FR-021**: Real-environment prerequisites that cannot truthfully run in development or CI MUST be recorded as pending deferred work with feature, reason, environment, prerequisites, steps, and expected result.
- **FR-022**: Production and recovery readiness checks MUST continue to fail while mandatory real-environment configuration or evidence remains unresolved.
- **FR-023**: Business behavior, authorization, contracts, data rules, and production migration history MUST NOT change merely to satisfy a quality tool or test.
- **FR-024**: The feature branch MUST be validated before merge, and the same release gate MUST pass again on the integration branch before that branch is pushed; the production branch is outside scope.

### Key Entities

- **Canonical Check**: A named, locally runnable validation with one owner, prerequisites, inputs, pass criteria, and non-mutating check mode.
- **Workflow Job Record**: A compact inventory entry describing an automated job's trigger, dependencies, services, configuration, commands, and defect status.
- **Failure Record**: A diagnostic entry linking a failed command or job to its actual cause, corrective change, and verification evidence.
- **Generated Contract Pair**: The committed backend API description and its derived frontend schema that must remain synchronized.
- **Deferred Verification**: A pending operational prerequisite that requires a real staging, production, device, network, recovery, or external-service environment.

## Success Criteria

### Measurable Outcomes

- **SC-001**: One clean-run release command executes 100% of required machine-verifiable release categories and returns a non-zero result for any failed category.
- **SC-002**: Check-only formatting, lint/static quality, strict typing, architecture, migration, contract, backend system, deployment isolation, all automated tests, and frontend production build complete with zero required failures.
- **SC-003**: Reinstalling dependencies from committed locks and regenerating owned artifacts produces zero lockfile or generated-artifact changes.
- **SC-004**: Every workflow and job under repository automation is represented exactly once in the workflow inventory, and every observed failure has a cause, fix, and verification record.
- **SC-005**: Required local validation and automated validation use the same canonical command for every shared quality category where their environments permit it.
- **SC-006**: All PostgreSQL-specific and concurrency guarantees execute against PostgreSQL, with zero such tests skipped or substituted in the release gate.
- **SC-007**: Production and recovery readiness remain explicitly pending while any mandatory external evidence is unresolved, with 100% of those prerequisites represented in deferred work.
- **SC-008**: No required validation bypass, committed secret, production credential exposure, unintended deployment trigger, or unapproved business-behavior change is introduced.

## Assumptions

- Existing architecture, business rules, generated-contract ownership, database engine, quality tools, package managers, and test runners remain canonical.
- `develop` is the integration branch; `main` and actual production deployment are outside this feature.
- Real production secrets, infrastructure, recovery evidence, physical devices, DNS/TLS, and external delivery credentials are not fabricated for automated validation.
- The authority order is `docs/CHOT_YEU_CAU.md` → resolved decisions in `docs/RA_SOAT_YEU_CAU.md` → PRD → `docs/QUY_TAC_CLEAN_CODE.md` → constitution → this feature.
- Existing production-readiness gates and unresolved evidence from Feature 014 remain authoritative and fail closed.
