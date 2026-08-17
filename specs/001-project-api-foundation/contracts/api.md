# API Boundary Contract

## Namespace and schema exposure

- Every runtime application API route is assembled beneath `/api/v1/` from one URL boundary.
- `GET /api/v1/schema/` returns the machine-readable OpenAPI document only when `API_DOCS_ENABLED=true`.
- When disabled, the schema route is not registered. No Swagger UI, ReDoc, login, health, or business route is added by this contract.
- Every `/api/v1/` response includes a server-issued `X-Request-Id` and `Cache-Control: private, no-store`.

## Request identity

- The server creates a lowercase canonical UUIDv4 per request.
- Client `X-Request-Id` values—valid, invalid, repeated, oversized, or otherwise—are ignored and never echoed.
- The ambient `correlation_id` equals the new `request_id` when no trusted server-side upstream context exists. This feature defines no trusted external upstream header.
- Context is cleared on success and failure and is empty outside a request.

## JSON error envelope

```json
{
  "error_code": "VALIDATION_FAILED",
  "message": "Dữ liệu không hợp lệ.",
  "details": {
    "field_name": ["Giá trị không hợp lệ."]
  },
  "request_id": "00000000-0000-4000-8000-000000000000",
  "error": "VALIDATION_FAILED",
  "field_name": ["Giá trị không hợp lệ."]
}
```

Observable rules:

- `details` is always an object and is `{}` when no structured detail exists.
- `error` always equals `error_code` for v1.
- Each field-level `details` entry is mirrored at the top level for v1 compatibility.
- Canonical fields cannot be overwritten by colliding detail keys.
- Body `request_id` exactly equals the response header.
- Messages are safe Vietnamese display text; exception strings, tracebacks, secrets, credentials, URLs, object keys, images, and precise coordinates are never returned.

## Authorized foundation use

This feature does not create error codes. It may exercise only codes already
authorized by CHOT: `VALIDATION_FAILED` for request validation and
`PERMISSION_DENIED` for CSRF/origin denial. It does not assign codes, statuses,
or semantics to generic 404, 405, 415, or 500 failures. A later public mapping
for such a status requires the governance chain to authorize its code first.

The disabled schema route remains absent and is observable only by its HTTP 404
status; this contract does not claim a new JSON error code for that unregistered
path.

## OpenAPI invariants

- OpenAPI version is 3.0.3 and `info.version` is fixed at `1.0.0`.
- All application path keys begin `/api/v1/`; operation IDs are explicit and unique.
- JSON properties are `snake_case`.
- Canonical error schemas include all v1 mirrors and deprecation annotations.
- Generated output has deterministic ordering, LF endings, no timestamp, no absolute path, and no environment-dependent server URL.
- Schema text, names, examples, and nested values pass the protected-content scanner.

## Authorization and object scope

There is no authenticated business operation, permission action, object lookup, or mutation in this feature. The term `authenticatedFetch` names the future client chokepoint; it does not make this contract an authentication specification. Schema-route availability is controlled only by deployment configuration and creates no business authorization precedent.
