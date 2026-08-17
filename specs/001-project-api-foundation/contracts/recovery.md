# Recovery Verification Contract

This contract defines repository-side recovery verification. It does not claim
that a restore drill occurred and does not create recovery evidence.

## Ownership and discovery

- Django MUST discover `verify_restore` from the already-approved `operations`
  application.
- The command shim lives at
  `backend/operations/management/commands/verify_restore.py` and only parses,
  delegates, formats a safe summary, and chooses an exit status.
- Pure orchestration lives at `backend/core/recovery.py` and owns the ordered
  read-only verification workflow.
- `config/` remains composition root only. It MUST NOT contain `apps.py`,
  `management/`, `migrations/`, models, or persistence.
- `core/` MUST NOT be registered as a Django application.
- No recovery-specific or infrastructure-only Django application may be added.

Command-discovery verification succeeds only when Django reports:

```text
verify_restore -> operations
```

and the approved local-app allowlist contains no new owner.

## Connection safety

- The command reads the restore DSN only from `RECOVERY_DATABASE_URL`.
- It compares the safe DSN identity with `DATABASE_URL` and
  `DATABASE_ADMIN_URL` before any socket is opened.
- An identity collision exits nonzero and proves that no connection attempt was
  made.
- The restore connection MUST NOT be added to Django `DATABASES`.
- Verification begins a read-only transaction and contains no
  `INSERT`, `UPDATE`, `DELETE`, `CREATE`, or other write-capable branch.

## Verification result

The orchestrator checks the CHOT-required categories: active users, audit rows,
effective token state, unpublished outbox state, and schema version. A
successful verification requires every required probe to be registered,
available, executed, complete, schema-compatible, and passed. The aggregate
result distinguishes `passed` from `incomplete/unverifiable`; there is no soft
pass.

The command exits nonzero with `incomplete/unverifiable` when any required
relation/table is missing, a required probe category is unavailable, a probe
returns a partial or incomplete result, a required probe is not registered, the
restored schema is incompatible with the verification contract, or probe
execution fails. None of those states may emit PASS or OK or contribute to a
ready result. Tests cover each state before orchestration is implemented, plus
a complete successful read-only verification.

Failure output names only safe identifiers, table/category names, counts,
thresholds, and environment-variable names. Every external failure string uses
`core.event_payload.sanitize_failure_reason`. Alert metadata uses `failed=` and
MUST NOT attempt to overwrite reserved `LogRecord` attributes such as `name`.

## Evidence boundary

- Running controlled tests or command discovery does not update
  `deploy/recovery-evidence.yaml`.
- A real isolated operator drill is the only source of restore evidence.
- `recovery-ready` remains nonzero while evidence is unresolved, stale, failed,
  failed without a remediation owner, or target-exceeding.
- `verify_restore`, `recovery-ready`, and restore drills are not CI gates.
