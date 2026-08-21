# Implementation Plan: Code Quality, Build, CI/CD and Production Release Hardening

**Branch**: `feature/016-release-hardening` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/016-release-hardening/spec.md`

## Summary

Harden the existing release pipeline without changing business behavior. Preserve npm/uv, Prettier/Ruff, ESLint/mypy, Vitest/pytest, PostgreSQL 17, deterministic OpenAPI generation, migration safety, and fail-closed deployment readiness. Fix observed formatting, import ordering, strict typing, browser-test environment, working-directory, and scoped environment defects; consolidate canonical commands so local release validation and both GitHub Actions workflows exercise the same rules.

## Technical Context

**Language/Version**: TypeScript 5.9 on Node.js 22; Python 3.12 (project permits `<3.14`)

**Primary Dependencies**: Next.js 16.3, React 19.1, Django 5.2, Django REST Framework 3.16; npm lockfile and uv lockfile

**Storage**: PostgreSQL 17 for all database, transaction, migration, and concurrency evidence; private S3-compatible storage remains an external runtime dependency

**Testing**: Vitest/jsdom and Playwright; pytest/pytest-django; Ruff, strict mypy, ESLint, TypeScript; project architecture, function-length, contract, migration, and deployment scripts

**Target Platform**: Linux GitHub-hosted CI and production-oriented web/server builds, with reproducible developer execution on Windows through Git Bash or equivalent POSIX shell

**Project Type**: Existing Next.js frontend plus Django backend monorepository

**Performance Goals**: No new runtime-performance goal; required machine checks are deterministic and external capacity evidence retains Feature 014 targets

**Constraints**: No business changes; no CI bypass; no SQLite substitution; no secret logging; no fabricated production/recovery evidence; no major runtime upgrade; generated files are never hand-edited

**Scale/Scope**: Entire repository; two workflows, all authored frontend/backend/scripts, 14 frontend routes, all committed migrations/contracts, unit/architecture/contract/API/PostgreSQL/concurrency suites

## Constitution Check

*GATE: Passed before research and re-checked after design.*

- **Authority and behavior**: PASS. Feature 016 changes engineering gates only and defers to CHOT, resolved R decisions, PRD, clean-code rules, and the constitution. Behavioral failures require authority comparison before code or test changes.
- **Architecture and maintainability**: PASS. Existing module boundaries and thin-layer rules remain enforced by architecture, function-length, Ruff, mypy, ESLint, and TypeScript checks.
- **Generated contracts**: PASS. Backend OpenAPI generation, committed OpenAPI, frontend generated schema, byte drift, compatibility, and operation-ID rules remain mandatory.
- **Migration and PostgreSQL evidence**: PASS. Migration graph/policy checks and real PostgreSQL integration/concurrency evidence remain mandatory; SQLite is not introduced.
- **Security and environment isolation**: PASS. Scoped development/test values enable machine checks while production remains fail closed; CI and deployment remain separated and secrets are not printed.
- **Testing**: PASS. Required tests remain required; flaky behavior is corrected through deterministic environment and synchronization rather than retries.
- **Production readiness honesty**: PASS. Machine validation is distinct from unresolved production, recovery, capacity, device, DNS/TLS, and external-service evidence.

Post-design re-check: PASS. The command contract centralizes existing checks without changing API, data, deployment, authorization, or business ownership. Deferred evidence remains pending.

## Project Structure

### Documentation (this feature)

```text
specs/016-release-hardening/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
├── contracts/release-gate.md
└── tasks.md
```

### Source Code (repository root)

```text
.github/workflows/{quality.yml,contract.yml}
backend/{pyproject.toml,uv.lock,config,core,operations,identity,audit,locations,attendance,tasks,notifications,reporting,tests}
frontend/{package.json,package-lock.json,eslint.config.mjs,.prettierrc.json,.prettierignore,tsconfig.json,next.config.ts,vitest.config.ts,tests,src}
contracts/openapi.yaml
scripts/{check_all.sh,generate_openapi.py,check_openapi.py,check_contract_drift.py,migration_check.py,deployment_check.py}
deploy/{environments.yaml,recovery-evidence.yaml,scheduled-jobs.yaml}
.env.example
.pre-commit-config.yaml
```

**Structure Decision**: Preserve the existing monorepository and feature modules. Feature 016 primarily changes repository configuration, canonical scripts, workflows, targeted defects, generated artifacts only through their owners, Feature 016 documentation, and pending deferred-work records.

## Failure-Driven Implementation Phases

1. **Tooling and script inventory**: Record every manifest, runtime, service, environment, canonical command, workflow/job, and local/CI mismatch.
2. **Formatting cleanup**: Correct ignore scope and line-ending normalization, run existing write formatters over applicable authored files, then pass check-only modes.
3. **Lint/static/type fixes**: Fix the observed Ruff import-order defect and three strict-mypy defects; evaluate ESLint warnings without blanket suppression; rerun owning checks.
4. **Test failures**: Normalize jsdom-owned storage globals under Node 22, rerun the 11 affected frontend tests, then all frontend tests. Launch backend tests from repository root with the CI-owned PostgreSQL DSN so repository-relative contract files resolve.
5. **Frontend production build**: Run a cache-clean production build; assess the middleware deprecation separately because it is not a current build failure and a migration must preserve origin security.
6. **Backend checks, migrations, and contracts**: Supply explicit development-only check values, verify Django checks, model/migration drift, leaf/policy checks, OpenAPI/client generation, compatibility, and isolation gates.
7. **GitHub Actions fixes**: Align both workflows with canonical commands, locked installs, declared runtimes/services, scoped environment, secure logging, and validation-only triggers.
8. **Clean-run reproduction**: Remove only disposable caches, use immutable dependency installs, then regenerate/check artifacts and run all required suites on PostgreSQL.
9. **Final release gate**: Make `scripts/check_all.sh` the documented full machine gate, calling smaller existing commands without duplicating validation logic.
10. **Deferred real-environment verification**: Preserve Feature 014 failures and add Feature 016 pending records for production deployment, staging/device/Web Push, recovery, capacity, DNS/TLS, hosting/network, and secret provisioning.

## Observed Failure Table

| Failure | Root cause | Planned fix | Target verification |
|---|---|---|---|
| Frontend format reports two authored files and `test-results/.last-run.json` | Disposable Playwright state is not excluded; two authored files are not canonical Prettier output | Exclude disposable results and format authored files | Frontend format check |
| Ruff format reports 435 files | Checkout line endings conflict with Ruff's canonical LF output and no repository normalization is declared | Add scoped normalization and run Ruff write mode | Backend format check |
| Ruff lint reports one import block | `backend/config/composition.py` is not in canonical import order | Apply Ruff's safe import organization | Backend lint |
| Strict mypy reports three errors | One redundant cast and two unparameterized query sets | Remove cast and add precise model type parameters | Backend mypy |
| 11 frontend tests plus one rejection fail | A newer local Node process exposes experimental storage globals that shadow jsdom without backing files; CI Node 22 masked the drift | Launch Vitest workers with experimental process web storage disabled so jsdom owns browser storage | PASS: 471 frontend tests |
| Backend suite launched from `backend/` produces path failures | Contract tests resolve repository-root artifacts; the local command differed from CI | Canonicalize root invocation | Root-level pytest groups |
| Backend suite also fails DB setup on port 5432 | Local shell inherited a pooled remote DSN; its pool reconnects during Django test-database teardown | Use an isolated PostgreSQL 17 service with the declared CI identity on a non-conflicting local port | PASS: 997 backend/API tests and 220 PostgreSQL tests in the clean gate |
| `manage.py check` rejects missing secret key | Settings correctly fail closed; ad hoc command lacked scoped development values | Add canonical non-secret check environment | Django checks |
| Notification read-race test fails after 10:00 UTC on 2026-08-21 | Candidate read timestamps were derived from a fixed occurrence fixture and became earlier than database-generated `created_at` | Derive candidates from the persisted row creation timestamp while retaining barrier synchronization | PASS: targeted PostgreSQL concurrency test |
| OpenAPI compatibility gate fails under Git Bash | Pinned installer lacked Windows release mapping and assumed `shasum` | Add pinned Windows archive/checksum and verified `sha256sum` fallback | PASS: compatibility comparison under Git Bash |
| Immutable npm install reports high-severity Vite advisory chain | Lockfile resolved Vite 6.1.0/esbuild 0.24.2 | Update within Vite 6 to 6.4.3/esbuild 0.25.12 | PASS: immutable reinstall and zero-vulnerability audit |
| GitHub run status is unavailable locally | GitHub CLI is absent | Inspect after push through available access or report NOT VERIFIED | Required branch checks/manual URLs |

## Complexity Tracking

No constitution violation requires justification.
