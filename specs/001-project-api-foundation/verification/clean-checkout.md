# Clean-checkout verification: Feature 001 Phase 8

- Date: 2026-08-17
- Source snapshot repository: `/private/tmp/feature001-source.nMcSRR`
- Actual Git clone: `/private/tmp/feature001-checkout.ymNiaN`
- Start UTC: `2026-08-17T16:56:25Z`
- End UTC: `2026-08-17T16:57:18Z`
- Monotonic start: `486860.036701291`
- Monotonic end: `486913.64168225`
- Elapsed: `53.60498095903313 seconds`, below the 15-minute limit.

The exact Phase 8 working snapshot was committed to a temporary local source
repository and cloned with `git clone`. Verification asserted an empty
`git status --porcelain` before setup. The clone contained no inherited
`.venv`, `node_modules`, `.next`, tool cache, build output, or test cache.
Dependencies were recreated from `backend/uv.lock` and
`frontend/package-lock.json`; oasdiff 1.26.1 was downloaded from its pinned
release asset and accepted only after the platform-specific SHA-256 matched.

## Results

| Check | Result |
| --- | --- |
| PostgreSQL 17 Compose service | Healthy |
| `uv sync --project backend --locked` | PASS |
| `npm --prefix frontend ci` | PASS, 0 vulnerabilities |
| Django system check | PASS |
| Backend unit/architecture/contract tests | PASS, 171 tests |
| Real PostgreSQL integration tests | PASS, 8 tests |
| Ruff format/lint and strict mypy | PASS |
| OpenAPI generation/safety/client drift | PASS |
| Pinned merge-base oasdiff compatibility | PASS |
| Migration static check and environment isolation | PASS |
| Frontend format/lint/type/test | PASS, 23 tests |
| Frontend production build | PASS |
| Backend wheel and source build | PASS |
| Frontend proxy `/api/v1/schema/` | PASS, HTTP 200 machine YAML |
| Direct origin without source credential | Expected canonical HTTP 403 |
| Status-only smoke | PASS, output exactly `200` |
| `production-ready` | Expected nonzero for committed `UNRESOLVED` fields |
| `recovery-ready` | Expected nonzero for unresolved drill/capacity evidence |

SHA-256 values for `deploy/environments.yaml` and
`deploy/recovery-evidence.yaml` were identical before and after readiness,
probe, and smoke commands. No restore drill, capacity measurement, or readiness
evidence was fabricated.

Before the clean-clone run, the workspace aggregate gate also passed 188
backend non-PostgreSQL/API tests, 23 frontend tests, deterministic generation,
compatibility, both static toolchains, and the frontend production build. The
complete PostgreSQL path passed separately against PostgreSQL 17.
