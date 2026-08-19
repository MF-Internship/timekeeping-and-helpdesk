# Phase 1 Contracts: Location Awareness and Geofence Guidance

**Feature**: 006 | **Branch**: `feature/006-location-geofence-guidance` | **Date**: 2026-08-20

## 1. HTTP API contract: unchanged

**Feature 006 introduces no new API operation and modifies none.**

- `contracts/openapi.yaml` is byte-identical before and after this feature.
- No `operationId` is added, renamed, or removed.
- `frontend/src/shared/api/schema.ts` is unchanged; `npm run api:check` must
  produce an empty diff, already gated by
  `frontend/tests/contract/api-generation.test.ts`.
- No new permission action, no new DTO, no new serializer.

### Operations consumed (existing, unchanged)

| operationId | Method / Path | Fields used | Purpose |
|---|---|---|---|
| `locations_list` | `GET /api/v1/locations/` | `id`, `code`, `name`, `address`, `kind`, `latitude`, `longitude`, `radius_m`, `is_active` | the authorized Location directory for on-device guidance |
| `config_retrieve` | `GET /api/v1/config/` | `max_attendance_accuracy_m` | GPS quality diagnostic threshold |

Both are already exercised by Feature 003 and are called through
`frontend/src/features/locations/api/location-api.ts` →
`frontend/src/shared/api/client.ts` →
**`frontend/src/shared/transport/authenticated-fetch.ts`**, which remains the
single transport chokepoint. `features/guidance` introduces no alternate
transport; the existing
`frontend/tests/architecture/api-transport-boundary.test.ts` guard covers the new
module automatically.

### Operations deliberately NOT added

| Rejected operation | Reason |
|---|---|
| `locations_nearby` / `GET /api/v1/locations/nearby?lat=&lon=` | FR-034 forbids transmitting live guidance coordinates to the backend; a query string would additionally place precise employee coordinates in server access logs |
| `POST /api/v1/locations/guidance` | same FR-034 violation; a non-writing POST also muddies the command/query split |
| any map-tile or geocoding proxy | CHOT §6.2.1 and QUY_TAC §10 item 16 forbid external geocoding and map SDK/iframe embedding; GR-001 defers interactive maps (resolved by deferral) |

### Attendance operations: untouched

`attendance_check_in`, `attendance_check_out` and `attendance_today_retrieve`
keep their existing request and response shapes. Feature 006 changes only how
their **error responses are presented** in the UI (per-code messages instead of
one generic string) — not the contract.

## 2. Cross-language geometry contract

Because guidance computes distances on-device, the client geometry is pinned to
the canonical server geometry by a committed fixture rather than by an endpoint.
See [`geofence-distance-fixture.md`](./geofence-distance-fixture.md).

## 3. Frontend UI contract

The mobile shell, component ownership, navigation filtering, GPS/Attendance
presentation inputs, progressive disclosure, responsive behavior, and
accessibility semantics are defined in [`frontend-ui.md`](./frontend-ui.md).
This is an internal UI boundary contract only; it introduces no public HTTP
operation, DTO, permission action, persistence, or generated-client change.

## 4. Contract-drift gates that must stay green

| Gate | Location | Expectation for this feature |
|---|---|---|
| OpenAPI ↔ generated client | `frontend/tests/contract/api-generation.test.ts` | no diff |
| Schema probe | `frontend/tests/contract/schema-probe.test.ts` | unchanged |
| Transport boundary | `frontend/tests/architecture/api-transport-boundary.test.ts` | passes for `features/guidance` |
| Origin/proxy boundary | `frontend/tests/architecture/origin-proxy-boundary.test.ts` | passes — no external origin is contacted |
| Geometry parity (new) | `frontend/tests/contract/geofence-parity.test.ts` + `backend/tests/contract/locations/test_geofence_distance_fixture.py` | both assert the same fixture |
| GPS privacy (new) | `frontend/tests/architecture/gps-privacy.test.ts` | no storage / log / URL / external-map-link use of guidance coordinates |
