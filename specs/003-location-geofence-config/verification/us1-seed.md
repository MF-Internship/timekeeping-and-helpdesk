# US1 seed verification

Verified 2026-08-18 with PostgreSQL integration tests. The canonical seed produced exactly
76 rows (7 `BUSINESS_CENTER`, 69 `SHOP`), preserved hierarchy and coordinates, accepted the
source duplicate-coordinate pair, and a second execution produced zero state/evidence changes.

Command: `pytest backend/tests/integration/postgres/locations/test_seed_exact_data.py -q`

Result: pass as part of the 13-test Feature 003 PostgreSQL/API run and the 445-test backend gate.
