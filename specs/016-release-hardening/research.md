# Research: Release Hardening

## Canonical frontend package and commands

**Decision**: Keep npm, `frontend/package-lock.json`, and `npm ci`; keep Prettier, ESLint, `tsc --noEmit`, Vitest, generated-schema check, and `next build` as owning commands.

**Rationale**: The manifest, only frontend lockfile, both workflows, and tests agree.

**Alternatives considered**: pnpm or yarn; rejected because neither has project ownership.

## Canonical backend package and commands

**Decision**: Keep uv with `backend/uv.lock`; keep Ruff, strict mypy, pytest, and the existing architecture, contract, migration, and deployment scripts.

**Rationale**: This is the approved setup in project configuration, pre-commit, repository gate, and workflows.

**Alternatives considered**: Adding another formatter, linter, dependency manager, or runner; rejected as duplicate tooling.

## Runtime and database versions

**Decision**: Keep Node 22, Python 3.12 in CI, and PostgreSQL 17.

**Rationale**: Both workflows agree, backend supports Python 3.12, frontend requires Node 22+, and no failure requires a major upgrade.

**Alternatives considered**: Downgrading Node to hide the storage issue or upgrading majors; rejected because test globals should be deterministic.

## Formatting and line endings

**Decision**: Preserve Prettier/Ruff, declare LF for authored cross-platform files, and exclude generated, dependency, build, coverage, and disposable result artifacts.

**Rationale**: Ruff owns LF output; Windows checkout otherwise makes hundreds of semantic no-op files fail. Playwright result state is not source.

**Alternatives considered**: Platform-native backend output or broad source exclusions; rejected as non-reproducible or bypassing validation.

## Frontend browser-test determinism

**Decision**: Run Vitest workers with Node's experimental process-level web storage disabled so jsdom remains the authoritative browser storage implementation.

**Rationale**: Application code targets browser storage, while newer Node processes expose an experimental unusable global that workers inherit. The canonical test launcher now supplies the deterministic Node option to every worker without changing application code.

**Alternatives considered**: A shared Node storage file, skips, retries, or application changes; rejected because they leak state or paper over the environment defect.

## Dependency advisory audit

**Decision**: Keep the existing Vite 6 toolchain and update its locked version from 6.1.0 to patched 6.4.3.

**Rationale**: The immutable install exposed high-severity development-server advisories in the old lock resolution. The patched same-major version removes the advisory chain without a test-runner or application-runtime migration.

**Alternatives considered**: Ignoring development dependencies or upgrading to a new Vite/Vitest major; rejected because the former leaves known risk and the latter is unnecessary release scope.

## Backend test working directory and environment

**Decision**: Run backend tests from repository root through `uv run --project backend`, with explicit PostgreSQL test DSNs.

**Rationale**: Contract tests intentionally reference root-owned workflows, contracts, deployment manifests, and scripts. CI already uses this pattern.

**Alternatives considered**: Rewriting every path relative to `backend/` or using SQLite; rejected because root artifacts are under test and PostgreSQL evidence is mandatory.

## Release gate and workflow parity

**Decision**: Retain `scripts/check_all.sh` as the full release gate and reuse canonical owning commands in workflows.

**Rationale**: A protected gate already exists. Improving it is lower risk than inventing a second orchestrator.

**Alternatives considered**: A new task framework or workflow-only mega-script; rejected as unnecessary machinery.

## Production readiness evidence

**Decision**: Keep `production-ready` and `recovery-ready` failing against unresolved committed evidence; record real-environment work as pending.

**Rationale**: CHOT R-107/R-108/R-109, Feature 014, and the constitution prohibit fabricated evidence.

**Alternatives considered**: Treating green CI as readiness or filling placeholders; rejected as false claims.
