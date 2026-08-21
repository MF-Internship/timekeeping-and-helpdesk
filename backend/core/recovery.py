from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from core.deployment import dsn_identity
from core.event_payload import sanitize_failure_reason

REQUIRED_CATEGORIES = (
    "active_users",
    "audit_rows",
    "effective_token_state",
    "unpublished_outbox",
    "schema_version",
)


@dataclass(frozen=True, slots=True)
class RecoveryInputs:
    runtime_dsn: str
    admin_dsn: str
    recovery_dsn: str


@dataclass(frozen=True, slots=True)
class Probe:
    category: str
    sql: str


@dataclass(frozen=True, slots=True)
class RecoveryResult:
    status: str
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == "passed"


class ReadOnlyConnection(Protocol):
    def execute(self, query: str) -> QueryResult: ...

    def close(self) -> None: ...


class QueryResult(Protocol):
    def fetchone(self) -> Sequence[object] | None: ...


DEFAULT_PROBES = (
    Probe(
        "active_users",
        "SELECT count(*) >= 0 FROM "
        "(SELECT id, is_active FROM identity_user WHERE is_active IS TRUE) AS active_users",
    ),
    Probe(
        "audit_rows",
        "SELECT count(*) >= 0 FROM "
        "(SELECT id, actor_id, action, target_type, target_id, before, after, "
        "recorded_at FROM audit_auditlog) AS audit_rows",
    ),
    Probe(
        "effective_token_state",
        "SELECT count(*) >= 0 FROM token_blacklist_outstandingtoken AS outstanding "
        "LEFT JOIN token_blacklist_blacklistedtoken AS revoked "
        "ON revoked.token_id = outstanding.id "
        "WHERE outstanding.expires_at > CURRENT_TIMESTAMP AND revoked.id IS NULL",
    ),
    Probe(
        "unpublished_outbox",
        "SELECT count(*) >= 0 FROM audit_outboxevent "
        "WHERE publish_state = 'PENDING' AND published_at IS NULL "
        "AND (lease_expires_at IS NULL OR lease_expires_at <= CURRENT_TIMESTAMP)",
    ),
    Probe(
        "schema_version",
        "SELECT current_setting('transaction_read_only') = 'on' AND EXISTS ("
        "SELECT 1 FROM django_migrations "
        "WHERE app = 'operations' AND name = '0001_throttle_cache_table')",
    ),
)


def verify_restore(
    inputs: RecoveryInputs,
    connect: Callable[[str], ReadOnlyConnection],
    probes: Sequence[Probe] = DEFAULT_PROBES,
) -> RecoveryResult:
    collision = _identity_collision(inputs)
    if collision:
        return RecoveryResult("incomplete/unverifiable", (collision,))
    registration_findings = _registration_findings(probes)
    if registration_findings:
        return RecoveryResult("incomplete/unverifiable", tuple(registration_findings))
    return _execute_probes(inputs.recovery_dsn, connect, probes)


def recovery_inputs_from_environment(values: Mapping[str, str]) -> RecoveryInputs:
    required = ("DATABASE_URL", "DATABASE_ADMIN_URL", "RECOVERY_DATABASE_URL")
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise ValueError(",".join(missing))
    return RecoveryInputs(*(values[key] for key in required))


def _identity_collision(inputs: RecoveryInputs) -> str:
    recovery = dsn_identity(inputs.recovery_dsn, "RECOVERY_DATABASE_URL")
    runtime = dsn_identity(inputs.runtime_dsn, "DATABASE_URL")
    admin = dsn_identity(inputs.admin_dsn, "DATABASE_ADMIN_URL")
    return "RECOVERY-IDENTITY" if recovery in {runtime, admin} else ""


def _registration_findings(probes: Sequence[Probe]) -> list[str]:
    registered = {probe.category for probe in probes}
    findings = [
        f"RECOVERY-PROBE:{category}"
        for category in REQUIRED_CATEGORIES
        if category not in registered
    ]
    findings.extend(
        f"RECOVERY-READ-ONLY:{probe.category}"
        for probe in probes
        if not probe.sql.lstrip().upper().startswith("SELECT")
    )
    return findings


def _execute_probes(
    recovery_dsn: str,
    connect: Callable[[str], ReadOnlyConnection],
    probes: Sequence[Probe],
) -> RecoveryResult:
    connection: ReadOnlyConnection | None = None
    failures: list[str] = []
    try:
        connection = connect(recovery_dsn)
        connection.execute("BEGIN TRANSACTION READ ONLY")
        for probe in probes:
            _execute_probe(connection, probe, failures)
        connection.execute("ROLLBACK")
    except Exception as error:
        failures.append(f"RECOVERY-CONNECTION:{sanitize_failure_reason(error)}")
    finally:
        if connection is not None:
            connection.close()
    status = "passed" if not failures else "incomplete/unverifiable"
    return RecoveryResult(status, tuple(failures))


def _execute_probe(connection: ReadOnlyConnection, probe: Probe, failures: list[str]) -> None:
    try:
        row = connection.execute(probe.sql).fetchone()
        if row is None or len(row) != 1 or row[0] is not True:
            failures.append(f"RECOVERY-INCOMPLETE:{probe.category}")
    except Exception as error:
        reason = sanitize_failure_reason(error)
        failures.append(f"RECOVERY-UNVERIFIABLE:{probe.category}:{reason}")
