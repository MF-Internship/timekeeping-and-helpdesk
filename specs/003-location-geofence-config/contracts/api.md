# API Contract: Location, Config, and Holiday

All paths use `/api/v1/`, bearer authentication, existing account-state checks, canonical
snake_case fields, canonical error envelope, `Cache-Control: private, no-store`, and the
existing origin/correlation middleware. Examples deliberately omit precise coordinates.

## Shared precedence

1. access authentication and active-account reload;
2. canonical action RBAC;
3. forced-password account gate;
4. query/path/body validation;
5. global resource scope/business invariants;
6. transaction/constraint;
7. audit/outbox for successful mutations.

Consequences:

- unauthorized actor plus malformed DTO/filter receives `403 PERMISSION_DENIED`;
- inactive current actor receives `401 ACCOUNT_INACTIVE` before action/DTO;
- authorized forced-change actor receives `403 PASSWORD_CHANGE_REQUIRED` before DTO;
- malformed/missing route id is evaluated only after permission/account gates;
- denied/invalid/stale/missing/rolled-back calls create no success evidence.

## Shared shapes

### Location

```json
{
  "id": 1,
  "code": "HCM010005",
  "name": "...",
  "kind": "SHOP",
  "parent_id": 2,
  "address": "...",
  "latitude": "<decimal string>",
  "longitude": "<decimal string>",
  "radius_m": "50.000",
  "is_active": true,
  "version": 1
}
```

OpenAPI examples must not replace the placeholders with real/source coordinates.

### Warning

```json
{
  "code": "GEOFENCE_OVERLAP",
  "related_location_ids": [2],
  "related_location_codes": ["HCM010000"]
}
```

or:

```json
{
  "code": "RADIUS_BELOW_ATTENDANCE_ACCURACY",
  "radius_m": "20.000",
  "threshold_m": "25.000"
}
```

### Config

```json
{
  "id": 1,
  "timezone": "Asia/Ho_Chi_Minh",
  "working_weekdays": [0, 1, 2, 3, 4, 5],
  "default_radius_m": "50.000",
  "max_radius_m": "70.000",
  "max_attendance_accuracy_m": "25.000",
  "task_gps_good_accuracy_m": "25.000",
  "task_gps_low_accuracy_m": "100.000",
  "shift_start": "08:00:00",
  "shift_end": "17:00:00",
  "late_grace_minutes": 5,
  "early_checkout_grace_minutes": 0,
  "late_checkout_grace_minutes": 60
}
```

Config has no version field in Feature 003.

### Holiday

```json
{"id": 1, "date": "2026-09-02", "name": "Quốc khánh"}
```

## GET `/api/v1/locations/`

**Action**: `location.view` (Leader, Manager, Helpdesk).

Optional query:

- `kind`: `BUSINESS_CENTER` or `SHOP`;
- `parent`: positive Location id;
- `is_active`: canonical boolean.

**200**: unpaginated Location array, stable order `kind`, `code`, `id`. With no filters it
contains exactly 76 entries. Inactive records are not hidden by default.

**400 `VALIDATION_FAILED`**: invalid/unknown filter value after permission.

## PATCH `/api/v1/locations/{location_id}/`

**Action**: `location.manage` (Manager only).

Request:

```json
{
  "version": 4,
  "name": "Tên mới",
  "address": "Địa chỉ mới",
  "latitude": "<decimal string>",
  "longitude": "<decimal string>",
  "radius_m": "45.00",
  "is_active": true,
  "reason": "Hiệu chỉnh dữ liệu đã xác minh"
}
```

`version` is required. Mutable fields are optional, but at least one of name/address/
latitude/longitude/radius/is_active must be supplied. Reason is optional and cannot stand
alone. Unknown fields and `id`, `code`, `kind`, `parent`, `parent_id` return
`400 SERVER_OWNED_FIELD` after permission.

The locked current version is compared before no-op detection. A current-version candidate
whose mutable values all equal current state returns **200** with the current Location and
recomputed warnings, but performs no save and advances neither Location nor aggregate
version and appends no AuditLog/OutboxEvent. A stale version remains **409** even if the
submitted values happen to equal the newer state.

**200**:

```json
{"location": {"...": "Location"}, "warnings": []}
```

Warnings do not change the success status.

**409 `LOCATION_VERSION_CONFLICT`**:

```json
{
  "error_code": "LOCATION_VERSION_CONFLICT",
  "message": "Địa điểm đã được cập nhật bởi yêu cầu khác.",
  "details": {
    "current_version": 5,
    "submitted_reason": "Hiệu chỉnh dữ liệu đã xác minh"
  },
  "request_id": "<server uuid>",
  "error": "LOCATION_VERSION_CONFLICT"
}
```

The response contains no current coordinates and performs no retry/mutation/evidence.

**400 `VALIDATION_FAILED`**: non-finite/out-of-range coordinate, blank name/address,
nonpositive radius, radius above current Config maximum, missing/invalid version, or empty
mutation.

**404 `NOT_FOUND`**: malformed/nonpositive id or valid parsed id with no target, after
action/account gates. Both cases have the same envelope and no side effects.

`POST /api/v1/locations/`, `DELETE /api/v1/locations/{id}/`, and a separate detail endpoint
do not exist.

## GET `/api/v1/config/`

**Action**: `config.view` (Leader, Manager, Helpdesk).

**200**: Config singleton. Supported deployment initializes it before enabling routes; no
public create operation exists.

## PATCH `/api/v1/config/`

**Action**: `config.manage_attendance` (Manager only).

Request may contain any subset of:

- `working_weekdays`;
- `default_radius_m`, `max_radius_m`;
- `max_attendance_accuracy_m`;
- `task_gps_good_accuracy_m`, `task_gps_low_accuracy_m`;
- `shift_start`, `shift_end`;
- `late_grace_minutes`, `early_checkout_grace_minutes`,
  `late_checkout_grace_minutes`.

At least one field is required. `id`, `timezone`, `version`, unknown fields, Location ids,
and workflow fields return `400 SERVER_OWNED_FIELD` after permission.

**200**:

```json
{"config": {"...": "Config"}, "warnings": []}
```

`RADIUS_BELOW_ATTENDANCE_ACCURACY` warnings identify affected Location ids/codes. They do
not rewrite Location radius/version.

A complete candidate equal to current Config returns **200** with current warnings but
performs no save, AuditLog/OutboxEvent append, or aggregate-version advance.

Lowering `max_radius_m` below any active or inactive Location radius returns **400
`VALIDATION_FAILED`**. Field details name `max_radius_m` and list only violating Location
ids/codes; no coordinates are returned. Equality with the greatest current radius is valid.
The failure never rewrites Location or creates evidence.

**400 `VALIDATION_FAILED`**: any meter-valued radius/accuracy threshold is `NaN`, positive
infinity, negative infinity, or non-positive; or the complete candidate violates radius or
threshold ordering, weekday, grace, or shift invariants. Non-finite values are rejected
before ordering comparisons. The prior singleton remains unchanged.

No Config-create route, version field, or `CONFIG_VERSION_CONFLICT` exists.

## GET `/api/v1/holidays/`

**Action**: `holiday.manage` (Manager only, including read).

**200**: unpaginated Holiday array ordered by date then id.

## POST `/api/v1/holidays/`

**Action**: `holiday.manage`.

Request:

```json
{"date": "2026-09-02", "name": "Quốc khánh"}
```

**201**: created Holiday.

**400 `VALIDATION_FAILED`**: invalid date, blank name, or duplicate date. Concurrent
duplicates leave exactly one row and only the winning request has audit/outbox evidence.

Unknown/id/server fields return `400 SERVER_OWNED_FIELD` after permission.

## DELETE `/api/v1/holidays/{holiday_id}/`

**Action**: `holiday.manage`.

**204**: existing Holiday deleted atomically with evidence.

**404 `NOT_FOUND`**: malformed/nonpositive id or missing target after action/account gates,
with the same envelope and no evidence.

## Negative contract matrix

| Case | Status/error | Side effects |
|---|---|---|
| Missing/malformed/expired access | 401 `INVALID_TOKEN` | None |
| Current inactive account | 401 `ACCOUNT_INACTIVE` | None |
| Non-Manager mutation plus malformed body | 403 `PERMISSION_DENIED` | DTO not evaluated; none |
| Authorized forced-change actor plus malformed body | 403 `PASSWORD_CHANGE_REQUIRED` | DTO not evaluated; none |
| Server-owned Location/Config/Holiday field | 400 `SERVER_OWNED_FIELD` | None |
| Invalid filter/value/invariant | 400 `VALIDATION_FAILED` | None |
| Stale Location version | 409 `LOCATION_VERSION_CONFLICT` | None; reason retained in details |
| Current-version same-value Location PATCH | 200 | No save/evidence/version advance; current warnings returned |
| Same-value Config PATCH | 200 | No save/evidence/aggregate-version advance; current warnings returned |
| Config maximum below any Location radius | 400 `VALIDATION_FAILED` | Config/Location/evidence unchanged |
| Missing mutation target | 404 `NOT_FOUND` | None |
| Malformed/nonpositive Location/Holiday id after authorization | 404 `NOT_FOUND` | None |
| Duplicate Holiday date | 400 `VALIDATION_FAILED` | Existing row/evidence unchanged |
| Location POST/DELETE | 404 route absence | None |

Every error uses `{error_code, message, details, request_id, error}` plus the approved v1
field-error mirrors where applicable.

Every success, error, and conflict response above includes `Cache-Control: private,
no-store`. On errors, body `request_id` equals the server-generated `X-Request-Id` header.
