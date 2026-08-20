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

`backend/identity/` owns the canonical User aggregate, authentication sessions,
RBAC policy, self-service, and user-administration use cases. `backend/audit/`
owns immutable audit evidence and the transactional outbox. Their domain and
application layers remain framework-independent; Django models, SimpleJWT,
serializers, views, and recording adapters stay at the adapter boundary.

Identity request processing is ordered as authentication, action RBAC,
body-independent Manager-target authorization, forced-password gate, DTO
validation, owning-module object scope, business rules, transaction/database
constraints, then audit/outbox. Permission decisions expose direct or approved
implication provenance only. Attendance self ownership is deferred to Feature
004, and Task creator/assignee ownership is deferred to Feature 006; Identity
does not query or write either module. Audit/outbox appends join the caller's
transaction. An asynchronous outbox relay remains outside Feature 002.

## Dependency direction

Future business modules use `domain/`, `application/`, `ports/`, and `adapters/`.
Dependencies point inward: adapters implement ports, application services
coordinate use cases, and domain code stays framework-free. Production code may
not import another business module's models, domain, or adapters.

The closed cross-module exemptions are tests, migrations, and the `config/`
composition root. An exemption changes wiring or verification only; it never
moves business rules into an adapter, command, serializer, view, or component.

## Notification feature boundary

`backend/notifications/` owns the complete in-app inbox, browser subscriptions,
delivery policy and durable PostgreSQL push-delivery queue for exactly five
approved event types. Task, Attendance and Identity retain their aggregates and
expose output ports; only `backend/config/` wires notification adapters into them.
Delivery is driven by the external scheduler, never an in-process timer, broker,
WebSocket or SSE relay. Email, SMS and account-security notifications remain out
of scope.

The cache remains the sole technical table; notification tables are owned
business persistence and do not expand `core` or `operations` ownership.

## Dependency provenance

Every dependency below is pinned in its owning lockfile or workflow and exists
only for the stated foundation requirement.

| Dependency | Rationale |
| --- | --- |
| `django` | Web composition, middleware, management-command discovery, migrations, and DatabaseCache. |
| `djangorestframework` | Versioned JSON API boundary and validation adapters. |
| `djangorestframework-simplejwt` | Fifteen-minute bearer access credentials plus server-tracked, rotating, revocable seven-day refresh credentials. |
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
| `@playwright/test` | Browser-level employee journey and generated-client integration verification. |
| `@axe-core/playwright` | Accessibility assertions within approved Playwright browser journeys. |
| `jsdom` | Browser DOM implementation for frontend tests. |
| `@testing-library/react` | Accessible React component behavior tests. |
| `@testing-library/jest-dom` | DOM assertions for shared UI states. |
| `@types/node` | Node and build-script TypeScript definitions. |
| `@types/react` | React TypeScript definitions. |
| `@types/react-dom` | React DOM TypeScript definitions. |
| `pywebpush` | Standards-compliant encrypted Web Push delivery and VAPID signing. |
| `cryptography` | Explicit encryption at rest for browser push subscription material. |

CI additionally uses GitHub `actions/checkout`, `actions/setup-node`,
`astral-sh/setup-uv`, checksum-verified `oasdiff` 1.26.1, and the official
PostgreSQL 17 service image. Feature 008 adds no queue, broker, observability
product, application-owned alternate HTTP client, or Redis runtime; the pinned
Web Push library owns its locked transport/crypto dependency graph.
### Feature 007 UI and evidence dependencies

The source-owned UI layer uses `@radix-ui/react-slot`, `class-variance-authority`,
`clsx`, `lucide-react`, `tailwind-merge`, `tailwindcss`, `@tailwindcss/postcss`,
`tw-animate-css`, and `vite` for the shared shadcn-style primitives, icons,
styling pipeline, and test runner. Private task evidence uses `django-storages`
for the S3-compatible adapter; storage credentials and object keys remain
server-owned.
