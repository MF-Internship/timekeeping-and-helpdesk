# Frontend Contract

## Generated/authored boundary

- `contracts/openapi.yaml`: generated from backend and committed.
- `frontend/src/shared/api/schema.ts`: generated from OpenAPI and committed.
- `frontend/src/shared/api/client.ts`: existing handwritten thin wrapper around
  `authenticatedFetch`; never generated and no business logic added.
- `frontend/src/features/locations/api/location-api.ts`: handwritten typed feature calls
  using `apiClient` and `parseApiFailure`.

No component trusts capability presentation as backend enforcement.

## Routes and capability presentation

| Page | Read capability | Mutation capability | Presentation |
|---|---|---|---|
| `/locations` | `location.view` | `location.manage` | All roles see directory; only Manager sees edit controls |
| `/config` | `config.view` | `config.manage_attendance` | All roles see values; only Manager sees editor |
| `/holidays` | `holiday.manage` | `holiday.manage` | Manager-only navigation/page |

The route boundary still handles loading, authentication failure, inactive account, and
forced-password routing through existing Identity state.

## Location UI state

- Fetch unpaginated 76-row list and expose kind/parent/active filters.
- Display code with name so overlapping/coincident records are distinguishable.
- Show coordinates as server-provided decimal strings; do not round and do not load a map.
- Edit draft contains only mutable fields, current version, and optional reason.
- A successful response updates the row/version and displays structured warnings as
  nonblocking notices.
- A same-value `200` keeps the current version and shows no false “change recorded” evidence;
  stale version still follows the conflict flow before no-op handling.
- On `LOCATION_VERSION_CONFLICT`, retain draft and reason, fetch the latest row/list, show
  current version, and require explicit resubmission. Never silently retry or last-write-win.
- Location create/delete buttons, routes, DTOs, and calls do not exist.

## Config UI state

- Read and display timezone, workweek, radii, independent Attendance/Task thresholds,
  shift, and all grace periods.
- Manager editor submits a partial typed request, but displays validation against the
  complete returned singleton.
- Warning-only saves remain success and identify affected Locations without modifying them.
- Lowering `max_radius_m` below any active or inactive Location radius is a field-visible
  validation failure listing safe Location codes; the UI never offers an automatic bulk
  radius rewrite.
- A same-value `200` leaves the form synchronized without claiming that history changed.
- There is no version-conflict flow or Config-create UI.

## Holiday UI state

- Manager sees ordered list, create form, and explicit delete confirmation.
- Duplicate date remains a field-visible `VALIDATION_FAILED`; it does not replace the
  existing row.
- Missing delete target refreshes the list after showing not-found failure.

## Security/storage

- All calls reuse authenticatedFetch, relative `/api/v1/` paths, credential inclusion,
  no-store behavior, and the existing single refresh replay.
- No token enters localStorage/sessionStorage/URL/log.
- No map SDK, Geolocation API call, continuous tracking, reverse geocoding, Attendance
  state, or Task state is added by this feature.
