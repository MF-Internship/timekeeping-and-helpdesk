# Frontend Boundary Contract

## `authenticatedFetch`

The function is compatible with the platform `fetch` signature and is the only production API transport seam.

Required behavior:

- Accept only same-origin relative API targets under `/api/v1/`; reject an absolute or off-prefix target before network I/O.
- Preserve the caller's method, body, headers, and `AbortSignal` while applying safe defaults.
- Set `credentials: "include"`, `cache: "no-store"`, and `Accept: application/json` unless a compatible caller header is already present.
- Do not store, parse, refresh, or attach authentication tokens in this feature.
- Do not automatically retry. The operation owner decides whether a recovery action is safe.
- Delegate to the platform fetch exactly once.

Generated `schema.ts` is derived from the committed OpenAPI artifact. Thin `client.ts` assembles openapi-fetch with `authenticatedFetch`; it contains no endpoint-specific business logic or wire-case mapping.

## Failure parsing

Given an unsuccessful response:

1. If the body satisfies the canonical v1 envelope, return `canonical` and preserve canonical fields, valid mirrors, and `request_id`.
2. If it does not, return `unexpected_response` with safe status metadata and a valid `X-Request-Id` header if present; do not display raw HTML or response bodies.
3. If fetch fails before a response, return `network`; do not fabricate a request ID.

Compatibility mirrors are accepted for v1 but canonical fields always win. A mirror mismatch is treated as an unexpected response rather than silently normalized.

## Shared UI states

| State | Observable presentation |
| --- | --- |
| Loading | Non-error progress indication. |
| Empty | Explicit no-data state distinct from loading and failure. |
| Canonical error | Safe message, field details where applicable, and support request ID. |
| Unexpected response | Generic safe recovery message; no raw body. |
| Network failure | Connectivity-oriented recovery message; no invented server identifier. |

Retry/recovery is rendered only when the caller supplies an action. Components expose accessible status/alert semantics and remain free of authentication, authorization, and business rules.

## Boundary enforcement

- Authored production files outside `authenticated-fetch.ts` may not invoke global `fetch` for `/api/v1/` or introduce another authenticated HTTP client.
- `src/shared/api/**` receives the exact directory-level ESLint exclusion required by `QUY_TAC_CLEAN_CODE.md`; `schema.ts` is generated, while handwritten `client.ts` remains thin and is constrained by `tsc --noEmit`, architecture checks, and review. No wider exclusion is permitted.
- Contract tests regenerate `schema.ts` from `contracts/openapi.yaml` and fail with the stale file path when bytes differ.
