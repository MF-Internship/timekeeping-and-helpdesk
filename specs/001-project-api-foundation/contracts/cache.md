# Shared Cache Contract

This contract defines the R-109 deployment-wide throttle-cache boundary. It
does not implement authentication or change any throttle rate.

## Canonical ownership

`backend/core/cache.py` is the only source for:

- `THROTTLE_CACHE_ALIAS`;
- `THROTTLE_CACHE_TABLE`;
- `CACHE_BACKEND_CHOICES`;
- classification of process-local cache implementations.

The module is pure Python and imports no Django. Settings, deployment checks,
future throttle code, and cache-table provisioning consume these definitions;
none may copy the alias, table name, vocabulary, or classification.

## Runtime selection

- `DJANGO_CACHE_BACKEND` uses the closed choices `locmem`, `database`, and
  `redis`.
- A present-but-empty or unknown value stops startup and names only
  `DJANGO_CACHE_BACKEND`.
- Django settings contain exactly one alias, keyed by
  `THROTTLE_CACHE_ALIAS`.
- Development/test may use the approved `locmem` fallback.
- The shipped staging and production inventory resolves `cache.backend` to
  `database`.
- Outside development, `LocMemCache`, `DummyCache`, and `FileBasedCache` stop
  startup even when `DJANGO_DEBUG=true`.
- Selecting `redis` without the approved package stops startup; this foundation
  adds no Redis runtime dependency.
- Cache access failure has no fail-open branch.

## Deployment inventory

Every `deploy/environments.yaml` entry has a resolved `cache.backend` value.
`scripts/deployment_check.py isolation` imports the canonical vocabulary and
classification, then rejects missing/unknown values or a process-local choice
outside development. The inventory stores no cache credential or connection
URL.

## DatabaseCache provisioning

- The cache table is provisioned only by an `operations` migration using the
  approved create-cache-table mechanism.
- The migration imports `THROTTLE_CACHE_TABLE`; it does not repeat the table
  literal.
- The migration number is derived from the actual `operations` graph. The
  current empty graph yields `0001_throttle_cache_table`; if the graph changes,
  implementation selects the next valid number.
- Static tests prove that provisioning belongs to `operations`, settings and
  migration share the canonical table identity, the graph has one leaf, and no
  `config` migration/app exists.
- A PostgreSQL migration test proves that the canonical table is created.

`config/` owns no app, migration, model, command, or persistence. `core/` owns no
table and is not a Django app. No other persistence owner is authorized.
