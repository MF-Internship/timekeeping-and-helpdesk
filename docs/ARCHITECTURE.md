# Architecture

## Approved ownership

`backend/config/` is the sole Django composition root. It assembles settings,
URLs, middleware, and adapters, but it is not a Django application and owns no
models, migrations, management commands, or persistence.

`backend/core/` is the narrow pure technical kernel. It is not a Django
application. It owns framework-independent configuration, cache vocabulary,
correlation, error construction, safety filtering, and recovery evaluation; it
must not become a business-module substitute.

`backend/operations/` is the only approved local operational Django application.
It owns operational framework adapters, the thin restore command,
and the R-109 technical cache-table migration. This ownership does not authorize
business entities or another persistence owner.

## Dependency direction

Future business modules use `domain/`, `application/`, `ports/`, and `adapters/`.
Dependencies point inward: adapters implement ports, application services
coordinate use cases, and domain code stays framework-free. Production code may
not import another business module's models, domain, or adapters.

The closed cross-module exemptions are tests, migrations, and the `config/`
composition root. An exemption changes wiring or verification only; it never
moves business rules into an adapter, command, serializer, view, or component.

## Current feature boundary

Feature 001 creates no authentication flow, location behavior, attendance,
task-management behavior, notifications, reporting logic, business model,
audit/outbox model, or public business endpoint. The sole technical table is
the Django DatabaseCache table provisioned by the `operations` migration from
the identity owned by `core.cache`.

## Dependency provenance

Every dependency below is pinned in its owning lockfile or workflow and exists
only for the stated foundation requirement.

| Dependency | Rationale |
| --- | --- |
| `django` | Web composition, middleware, management-command discovery, migrations, and DatabaseCache. |
| `djangorestframework` | Versioned JSON API boundary and validation adapters. |
| `drf-spectacular` | Backend-authoritative OpenAPI generation. |
| `psycopg` | PostgreSQL-only runtime, migration, and restore verification. |
| `pyyaml` | Safe parsing of deployment, recovery, and OpenAPI YAML documents. |
| `django-stubs` | Strict typing for Django composition code. |
| `djangorestframework-stubs` | Strict typing for DRF boundary code. |
| `mypy` | Strict backend and script type gate. |
| `pytest` | Backend unit, architecture, contract, HTTP, and PostgreSQL tests. |
| `pytest-django` | Django test initialization without a SQLite fallback. |
| `ruff` | Python formatting, naming, lint, and complexity gate. |
| `next` | Approved frontend framework and production build. |
| `react` | Next.js view runtime. |
| `react-dom` | Browser rendering for the React shell. |
| `openapi-fetch` | Typed API client assembly with injected `authenticatedFetch`. |
| `openapi-typescript` | Deterministic TypeScript schema generation from committed OpenAPI. |
| `typescript` | Strict frontend type gate. |
| `eslint` | Authored frontend naming, complexity, depth, and transport lint. |
| `eslint-config-next` | Next.js and React lint rules. |
| `@eslint/eslintrc` | ESLint configuration compatibility used by the pinned Next toolchain. |
| `prettier` | Deterministic frontend formatting. |
| `vitest` | Frontend unit, architecture, and contract test runner. |
| `jsdom` | Browser DOM implementation for frontend tests. |
| `@testing-library/react` | Accessible React component behavior tests. |
| `@testing-library/jest-dom` | DOM assertions for shared UI states. |
| `@types/node` | Node and build-script TypeScript definitions. |
| `@types/react` | React TypeScript definitions. |
| `@types/react-dom` | React DOM TypeScript definitions. |

CI additionally uses GitHub `actions/checkout`, `actions/setup-node`,
`astral-sh/setup-uv`, checksum-verified `oasdiff` 1.26.1, and the official
PostgreSQL 17 service image. No queue,
object-storage SDK, observability product, alternate HTTP client, or Redis
runtime package is approved by this feature.
