# Quickstart Validation: Feature 003

This guide validates the implemented feature after tasks/code exist. It does not replace
the automated suites or prescribe implementation bodies.

## Prerequisites

- Python/Node versions and locked dependencies from the repository.
- Local PostgreSQL from the existing project compose setup.
- Feature 001 migrations and implemented Feature 002 Identity/Audit foundations.
- One active Manager account id for attributable initialization/seed.
- Canonical CSV files unchanged under `docs/`.

Use the existing environment variables documented by the project; do not print DSNs,
credentials, access tokens, or source coordinates.

## 1. Static source preflight

Verify the two files have their separate headers and source counts:

```bash
python3 -c 'import csv, pathlib
for name in ("dia_chi_ttkd.csv", "dia_chi_cua_hang.csv"):
    path = pathlib.Path("docs") / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        print(name, reader.fieldnames, sum(1 for _ in reader))'
```

Expected: center headers use `Mã TTKD`/`Tên` and 7 rows; shop headers use
`SHOP_CODE`/`NAME` and 69 rows.

## 2. Migrate and initialize Config

Run existing migrations, then the implemented controlled Config initialization command with
the real active Manager id and approved deployment values:

```bash
uv run --project backend python backend/manage.py migrate
uv run --project backend python backend/manage.py initialize_location_config \
  --actor-id <manager-id> \
  --shift-start <HH:MM> \
  --shift-end <HH:MM> \
  --late-grace-minutes <n> \
  --early-checkout-grace-minutes <n>
```

Expected: exactly one complete Config id=1. Repeating initialization exits nonzero and
leaves the existing row/evidence unchanged.

## 3. Seed twice

```bash
uv run --project backend python backend/manage.py seed_locations --actor-id <manager-id>
uv run --project backend python backend/manage.py seed_locations --actor-id <manager-id>
```

Expected first run: 7 centers, 69 shops, 76 total; warnings may report overlap/duplicate
coordinates but do not fail. Expected second run: zero changed rows and no new audit/outbox
evidence.

Before enabling Feature 003 routes/UI, run the implemented read-only readiness command:

```bash
uv run --project backend python backend/manage.py verify_location_reference_ready
```

Expected: exit zero only after complete Config plus canonical 76/7/69 source state. A test
environment with missing/drifted data exits nonzero without repairing or appending evidence.

Run the deterministic PostgreSQL seed suite to prove exact source decimals, hierarchy,
atomicity, duplicate-code failure, duplicate-coordinate acceptance, and idempotency:

```bash
uv run --project backend pytest -m postgres backend/tests/integration/postgres/locations
```

## 4. Pure GPS/geofence verification

```bash
uv run --project backend pytest backend/tests/unit/locations
```

Expected coverage:

- NaN/infinity/out-of-range/negative accuracy rejected before geometry;
- zero, poles, antimeridian, known-distance and symmetry cases;
- exact radius is `INSIDE_GEOFENCE`, immediately outside is `OUTSIDE_GEOFENCE`;
- enum has exactly two values and classifier accepts no accuracy argument;
- duplicate coordinates/overlaps never become hard failures.

## 5. API/RBAC and optimistic update

```bash
uv run --project backend pytest backend/tests/integration/api/locations
```

Expected:

- all roles can list Locations and read Config;
- only Manager can update Location/Config or access Holidays;
- permission denial wins over malformed filter/body;
- server-owned Location fields are rejected;
- stale Location version returns 409 and retains submitted reason with no mutation/evidence;
- current-version same-value Location and same-value Config PATCH return 200 with no
  save/evidence/version advance; stale comparison still wins;
- Config rejects `NaN`, positive infinity, and negative infinity for every meter-valued
  radius/accuracy field before ordering comparisons, with no partial state/evidence;
- lowering Config maximum below an active or inactive Location radius returns 400 without
  rewriting Location;
- malformed/nonpositive and nonexistent Location/Holiday ids return the same 404 after
  permission/account gates;
- every success/error/conflict is private/no-store and error request id matches the header;
- warning-only updates return success;
- Location POST/DELETE routes are absent;
- Config has no create/version-conflict contract;
- Holiday duplicate/missing target semantics match `contracts/api.md`.

## 6. PostgreSQL transaction/race verification

The suite must use real workers/connections and transaction markers:

```bash
uv run --project backend pytest -m postgres \
  backend/tests/integration/postgres/locations \
  backend/tests/integration/postgres/audit
```

Expected: exactly one same-version Location winner, consistent Config→Location lock order,
two different Location updates serialized with independent versions, Config-cap races with
no final radius above maximum, atomic seed rollback, unique Holiday dates, singleton
initialization, and consecutive aggregate versions with no coordinate leakage.

## 7. Contract/frontend verification

```bash
uv run --project backend python scripts/generate_openapi.py --check
uv run --project backend python scripts/check_openapi.py --all
uv run --project backend python scripts/check_contract_drift.py
npm --prefix frontend run api:check
npm --prefix frontend run typecheck
npm --prefix frontend run test
npm --prefix frontend run build
```

Expected: generated artifacts match, no precise source coordinate appears in examples, and
frontend tests prove warning display, Manager-only controls, and stale-draft preservation.

## 8. Architecture and full gates

```bash
scripts/check_all.sh
```

Expected: no `locations` import of Identity/Audit internals, no Django/DRF in domain, no
Attendance/Task workflow helper or table, one migration leaf, and all existing Feature
001/002 behavior remains green.

## 9. Manual acceptance evidence

Using a non-production acceptance environment, time a Manager performing one eligible
Location update, Config update, and Holiday mutation. Record actual evidence under the
feature evidence directory only after implementation; do not fabricate p95 or usability
results and do not turn wall-clock timing into a CI assertion.

Capacity evidence is valid only with at least 50 identities, concurrency at least 20, and
p95 at most 500 ms; otherwise record failure and a remediation owner.
