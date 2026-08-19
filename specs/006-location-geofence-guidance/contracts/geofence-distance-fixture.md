# Contract: Shared Geofence Distance Fixture (FR-043a)

**Feature**: 006 | **Artifact**: `contracts/fixtures/geofence-distance.json`

## Purpose

Feature 006 computes geofence distance and inside/outside status **on-device**
(research.md §2). To guarantee that the client mirror never drifts from the
canonical server geometry, a single committed fixture is asserted by tests in
**both** languages:

- `backend/tests/contract/locations/test_geofence_distance_fixture.py` against
  `backend/locations/domain/geofence.py`
- `frontend/tests/contract/geofence-parity.test.ts` against
  `frontend/src/features/guidance/model/geofence.ts`

If either implementation drifts, CI fails on that side. This is the mechanism
that makes client-side computation safe without duplicating authority: the client
never decides anything, and its arithmetic is provably the same arithmetic.

## Canonical parameters (both sides, identical)

| Constant | Value |
|---|---|
| Earth radius | `EARTH_RADIUS_M = 6371008.8` |
| Formula | haversine, `2 · R · asin(min(1, sqrt(a)))` |
| Classification | `INSIDE_GEOFENCE` iff `distance_m <= radius_m`, else `OUTSIDE_GEOFENCE` |
| Enum cardinality | exactly two values — no `UNCERTAIN`, ever |
| Accuracy handling | `accuracy_m` is **never** subtracted from `radius_m`; it is an independent quality gate |

## Fixture file shape

`contracts/fixtures/geofence-distance.json`

```jsonc
{
  "earth_radius_m": 6371008.8,
  "tolerance_m": 0.001,          // absolute; distances agree within 1 mm
  "cases": [
    {
      "id": "identical-point",
      "description": "zero distance",
      "origin":      { "latitude": "10.762622", "longitude": "106.660172" },
      "destination": { "latitude": "10.762622", "longitude": "106.660172" },
      "expected_distance_m": 0.0,
      "radius_m": "100.000",
      "expected_status": "INSIDE_GEOFENCE"
    }
    // ... further cases
  ]
}
```

Coordinates and radii are strings, matching the wire representation, so neither
side's test may accidentally rely on a different numeric parse than production
code does.

## Required case coverage

| # | Case | Why it exists |
|---|---|---|
| 1 | identical coordinates | zero-distance edge; no division-by-zero, no NaN |
| 2 | `distance_m` exactly equal to `radius_m` | boundary is **inclusive** → `INSIDE_GEOFENCE` |
| 3 | one millimetre outside the boundary | proves the comparison is not `<` vs `<=` confused |
| 4 | coincident canonical pair `HCM000079` / `HCM010005` | the known duplicate-coordinate pair (R-119); both are candidates when both are active |
| 5–7 | the three known overlapping Location pairs | overlapping geofences are valid; both entries must classify INSIDE from a point in the intersection |
| 8 | short distance (~50 m) | typical in-geofence case |
| 9 | medium distance (~5 km) | typical out-of-geofence case |
| 10 | long distance (~1000 km) | guards a wrong-radius or degrees/radians error |
| 11 | across the equator / hemisphere sign change | latitude sign handling |
| 12 | across the antimeridian (±180° longitude) | longitude wrap handling |
| 13 | near-antipodal points | numerical stability of `asin(min(1, …))` clamping |
| 14 | high latitude (~60°N) | longitude-scaling correctness |

Cases 4–7 must use the real canonical `Location` coordinates and radii from the
seeded 76-record set so that the fixture stays meaningful against production
data.

## Assertions required of both tests

1. For every case, `|computed_distance_m - expected_distance_m| <= tolerance_m`.
2. For every case with a `radius_m`, the computed classification equals
   `expected_status`.
3. The implementation's Earth-radius constant equals `earth_radius_m` in the
   fixture (read the constant, do not hardcode it in the test).
4. Distance is symmetric: `d(a, b) == d(b, a)` within tolerance.
5. The classification enum exposes exactly two members.

## Change control

The fixture is a contract artifact. Adding a case is additive and expected.
**Changing `earth_radius_m`, `tolerance_m`, or an `expected_*` value is a
governance-level change** to Location/GPS domain semantics (Constitution
Principle X) and must be justified in the feature spec before the fixture is
edited — never edited to make a failing implementation pass.
