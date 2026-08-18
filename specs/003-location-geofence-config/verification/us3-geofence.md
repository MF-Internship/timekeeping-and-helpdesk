# US3 geofence verification

Verified 2026-08-18 with 33 Location unit tests: finite GPS/range validation, Haversine including
antimeridian and boundary cases, exact-radius INSIDE behavior, outside behavior, and an exact
two-value result enum. Accuracy is validated independently and is not a classifier input.
