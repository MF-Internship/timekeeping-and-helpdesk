# Seed and Configuration Initialization Contract

## Source files

Canonical defaults:

- `docs/dia_chi_ttkd.csv`
- `docs/dia_chi_cua_hang.csv`

Both commands are controlled deployment operations. They require an existing active Manager
actor id and invoke canonical authorization; they do not bypass RBAC because they run
outside HTTP.

## Header contracts

Center required headers: `Mã TTKD`, `Tên`, `ADDRESS`, `LATITUDE`, `LONGITUDE`.
`STT` may be present and is ignored.

Shop required headers: `SHOP_CODE`, `NAME`, `ADDRESS`, `LATITUDE`, `LONGITUDE`.

Mappings are separate constants. No fallback probing or shared `code/name` lookup is
allowed. Optional UTF-8 BOM is accepted. Both files are header-validated and fully parsed
before the transaction begins.

## Preflight failures

The command exits nonzero without DB mutation/evidence for:

- missing file/header or unreadable input;
- blank/invalid code/name/address;
- nonfinite/out-of-range coordinate;
- duplicate code within one file or across files;
- any count other than 7 centers and 69 shops;
- invalid/uninitialized Config;
- database identity outside the canonical 76 codes;
- unauthorized/inactive/non-Manager actor.

Diagnostics name file, header/category, and safe code where useful; they never print precise
coordinates or row payloads.

## Reconciliation

- Identity key: Location code only.
- Centers: kind BUSINESS_CENTER, parent null.
- Shops: kind SHOP, parent derived only as `SHOP_CODE[:5] + "0000"`; unmatched center
  yields null.
- Source code/name/address/decimal coordinates are preserved; no inference, correction,
  merging, or float parse.
- Radius comes from locked Config.default_radius_m; active becomes true.
- Existing mutable drift is restored and Location version advances once.
- Missing canonical row is inserted at version 1.
- Unexpected database identity causes rollback; it is not deleted.

## Expected success

After commit:

- exactly 7 BUSINESS_CENTER;
- exactly 69 SHOP;
- exactly 76 total Location rows;
- all active with the Config default radius;
- canonical hierarchy including null `HCM000079` parent;
- source coordinates compare exactly as Decimal;
- duplicate-coordinate pair remains two rows;
- overlaps are warnings only.

An unchanged second run reports zero changed rows, writes no Location/AuditLog/OutboxEvent,
and leaves every version unchanged.

## Config initialization

The separate initialization command requires complete shift start/end, late grace, and
early-checkout grace plus an actor id. Approved numeric defaults fill the remaining values,
including late-checkout grace 60. The complete candidate must satisfy all Config invariants.

If Config id=1 exists, initialization fails without mutation/evidence. Public Config PATCH
is used for later changes; there is no API create operation.

## Reference-data readiness

Before Feature 003 routes/UI are enabled, a separate read-only check must exit successfully
only when Config id=1 is complete and valid and the Location table matches the canonical
76/7/69 codes, hierarchy, and source coordinates. Missing Config, count/kind drift, unknown
or missing code, parent drift, or coordinate drift produces a nonzero exit status with safe
diagnostics. The check never initializes, seeds, reconciles, or appends evidence; operators
must run the attributable commands to repair state and then rerun readiness.
