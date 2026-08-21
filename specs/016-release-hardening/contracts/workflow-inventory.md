# GitHub Actions Workflow Inventory

| Workflow | Job | Purpose | Trigger | Dependencies and services | Required configuration | Canonical commands | Security boundary | Observed problem/status |
|---|---|---|---|---|---|---|---|---|
| `quality.yml` | `backend-quality` | Backend format, lint, types, architecture, unit/contract/API/PostgreSQL tests, OpenAPI and migration drift | Every push and pull request | uv, Python 3.12, locked backend dependencies, PostgreSQL 17 | Development-only PostgreSQL DSNs and application environment | Ruff, mypy, maintainability, convergence, pytest groups, OpenAPI/drift, model drift, migration safety, backend system/deploy checks | Validation only; read-only contents permission, no production secrets or deploy step | PASS locally and in Quality #62 |
| `quality.yml` | `frontend-quality` | Frontend format, lint, generated contract, types, tests, and production build | Every push and pull request | npm, Node 22, `frontend/package-lock.json` | No production secrets; backend proxy defaults to loopback during build | `format:check`, `lint`, `typecheck`, `test`, `api:check`, `build` | Validation only; read-only contents permission, no production secrets or deploy step | PASS locally and in Quality #62 |
| `contract.yml` | `contract-integration` | API/PostgreSQL integration, generated contract compatibility/drift, migration safety, and deployment isolation | Every push and pull request | uv, npm, Python 3.12, Node 22, PostgreSQL 17, full Git history | Development-only PostgreSQL DSNs and application environment | API/PostgreSQL/contract pytest, OpenAPI generation/safety, frontend API/type checks, compatibility, model drift, migration and isolation checks | Validation only; read-only contents permission, checkout token only, and no deploy step | PASS locally and in Contract #62 |

## Failure Records

| Failure | Root cause | Fix | Verification |
|---|---|---|---|
| Backend formatting | CRLF checkout conflicted with Ruff's canonical LF output | Repository LF normalization and Ruff write pass | PASS: Ruff format check |
| Backend lint/types | Import ordering, redundant cast, and missing QuerySet model parameters | Safe import organization and precise annotations | PASS: Ruff and strict mypy |
| Frontend formatting | Authored drift plus disposable Playwright state included | Prettier write pass and ignore correction | PASS: Prettier check |
| Frontend storage tests | Process storage globals shadowed jsdom and propagated to Vitest workers | Canonical worker launcher disables experimental Node storage | PASS: 471 tests |
| Frontend clean build | Next.js regenerates and changes tracked `next-env.d.ts` by command phase | Ignore the generated file and run `next typegen` before standalone typecheck | PASS: clean typecheck/build |
| PostgreSQL read concurrency | Fixed fixture timestamp eventually preceded database `created_at` | Derive competing read times from persisted creation time | PASS: targeted test and complete 220-test PostgreSQL suite |
| OpenAPI compatibility on Windows | Installer supported Linux/macOS only and assumed `shasum` | Pin upstream Windows archive/checksum and use verified checksum fallback | PASS under Git Bash |
| Frontend dependency audit | Vite 6.1.0 lock resolution carried a high-severity dev-server advisory | Same-major update to Vite 6.4.3 | PASS: npm audit reports zero vulnerabilities |
| Quality #58 `backend-quality` | The unsplit Feature 002 convergence script invoked frontend Vitest from a backend-only job that never installed frontend dependencies; local `node_modules` masked the ownership error | Add explicit backend/frontend convergence scopes and call each only after its owning job installs dependencies | PASS locally and in Quality #62 |
| Quality/Contract action warnings | Checkout, Node setup, and uv setup action majors still targeted GitHub's deprecated Node 20 action runtime | Pin current supported releases (`checkout@v7.0.1`, `setup-node@v7.0.0`, `setup-uv@v10.0.1`) without changing project Node/Python versions | PASS in Quality #62 and Contract #62 without the warnings |
| Contract #59 action resolution | Unlike the GitHub-owned actions, setup-uv does not publish a moving `v10` alias | Pin its published exact `v10.0.1` tag and use exact releases consistently for all actions | PASS in Contract #62 and Quality #62 |
| Quality #60 contract drift | drf-spectacular's automatic common-path detection uses host path semantics, producing generic `api` tags on Windows and resource tags on Linux | Configure the canonical `/api/v1` schema prefix explicitly and regenerate through the owning commands | PASS in clean Linux container, Quality #62, and Contract #62 |
| Quality #61 backend check launch | Windows executes the new shell script without honoring Git's executable bit, while Linux correctly returned exit 126 | Commit `scripts/check_backend.sh` with executable mode and verify direct Linux execution | PASS in Quality #62 |
| GitHub status inspection | GitHub CLI and unauthenticated API cannot read the private repository | Inspect exact runs through the available authenticated GitHub session | PASS: Quality #62 and Contract #62 |
