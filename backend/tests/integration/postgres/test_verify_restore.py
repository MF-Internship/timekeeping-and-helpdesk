from __future__ import annotations

import os
from collections.abc import Callable, Sequence

import psycopg
import pytest
from psycopg import Connection

from core.recovery import DEFAULT_PROBES, Probe, RecoveryInputs, verify_restore

LOCAL_DATABASE_URL = "postgresql://app_runtime:local_runtime_only@127.0.0.1:5432/timekeeping"


def postgres_test_database_url() -> str:
    return os.environ.get("POSTGRES_TEST_DATABASE_URL", LOCAL_DATABASE_URL)


def recovery_inputs() -> RecoveryInputs:
    return RecoveryInputs(
        "postgresql://runtime:secret@runtime-db/app",
        "postgresql://admin:secret@admin-db/app",
        postgres_test_database_url(),
    )


def prepared_connection(
    *,
    omitted_relations: Sequence[str] = (),
    audit_columns: str = "id integer, actor_id integer, action text, "
    "target_type text, target_id text, before jsonb, after jsonb, "
    "recorded_at timestamptz",
) -> Connection[tuple[object, ...]]:
    connection = psycopg.connect(postgres_test_database_url())
    definitions = {
        "identity_user": "id integer, is_active boolean",
        "audit_auditlog": audit_columns,
        "token_blacklist_outstandingtoken": "id integer, expires_at timestamptz",
        "token_blacklist_blacklistedtoken": "id integer, token_id integer",
        "operations_outboxevent": (
            "id integer, publish_state text, published_at timestamptz, lease_expires_at timestamptz"
        ),
        "django_migrations": "app text, name text",
    }
    for relation, columns in definitions.items():
        if relation not in omitted_relations:
            connection.execute(f"CREATE TEMP TABLE {relation} ({columns})")
    if "django_migrations" not in omitted_relations:
        connection.execute(
            "INSERT INTO django_migrations (app, name) VALUES (%s, %s)",
            ("operations", "0001_throttle_cache_table"),
        )
    # Keep this fixture isolated from relations installed in the development
    # database; omitted relations must remain genuinely absent for the probe.
    connection.execute("SET search_path TO pg_temp")
    connection.commit()
    return connection


def connector(
    **connection_options: object,
) -> tuple[
    Callable[[str], Connection[tuple[object, ...]]],
    list[Connection[tuple[object, ...]]],
]:
    opened: list[Connection[tuple[object, ...]]] = []

    def connect(_dsn: str) -> Connection[tuple[object, ...]]:
        connection = prepared_connection(**connection_options)
        opened.append(connection)
        return connection

    return connect, opened


@pytest.mark.postgres
@pytest.mark.integration
def test_identity_collision_rejects_before_connection() -> None:
    attempts = 0

    def connect(_dsn: str) -> Connection[tuple[object, ...]]:
        nonlocal attempts
        attempts += 1
        return prepared_connection()

    inputs = RecoveryInputs(
        "postgresql://runtime:secret@db/app",
        "postgresql://admin:secret@admin/app",
        "postgresql://runtime:secret@db/app",
    )
    result = verify_restore(inputs, connect)
    assert result.status == "incomplete/unverifiable"
    assert attempts == 0


@pytest.mark.postgres
@pytest.mark.integration
def test_missing_probe_registration_is_unverifiable_before_connection() -> None:
    attempts = 0

    def connect(_dsn: str) -> Connection[tuple[object, ...]]:
        nonlocal attempts
        attempts += 1
        return prepared_connection()

    result = verify_restore(recovery_inputs(), connect, DEFAULT_PROBES[:-1])
    assert result.status == "incomplete/unverifiable"
    assert attempts == 0
    assert "schema_version" in " ".join(result.failures)


@pytest.mark.postgres
@pytest.mark.integration
def test_missing_required_relation_is_unverifiable_on_postgresql() -> None:
    connect, opened = connector(omitted_relations=("audit_auditlog",))
    result = verify_restore(recovery_inputs(), connect)
    assert result.status == "incomplete/unverifiable"
    assert "audit_rows" in " ".join(result.failures)
    assert opened[0].closed


@pytest.mark.postgres
@pytest.mark.integration
def test_incompatible_restored_schema_is_unverifiable_on_postgresql() -> None:
    connect, opened = connector(audit_columns="id integer")
    result = verify_restore(recovery_inputs(), connect)
    assert result.status == "incomplete/unverifiable"
    assert "audit_rows" in " ".join(result.failures)
    assert opened[0].closed


@pytest.mark.postgres
@pytest.mark.integration
def test_partial_probe_and_execution_failure_are_unverifiable() -> None:
    probes = tuple(
        Probe(probe.category, "SELECT FALSE")
        if probe.category == "active_users"
        else Probe(probe.category, "SELECT missing_recovery_probe()")
        if probe.category == "audit_rows"
        else probe
        for probe in DEFAULT_PROBES
    )
    connect, opened = connector()
    result = verify_restore(recovery_inputs(), connect, probes)
    assert result.status == "incomplete/unverifiable"
    assert "active_users" in " ".join(result.failures)
    assert "audit_rows" in " ".join(result.failures)
    assert "PASS" not in " ".join(result.failures)
    assert "OK" not in " ".join(result.failures)
    assert opened[0].closed


@pytest.mark.postgres
@pytest.mark.integration
def test_complete_verification_passes_inside_read_only_transaction() -> None:
    connect, opened = connector()
    result = verify_restore(recovery_inputs(), connect)
    assert result.passed
    assert result.failures == ()
    assert opened[0].closed
    assert all(probe.sql.lstrip().upper().startswith("SELECT") for probe in DEFAULT_PROBES)
    schema_probe = next(probe for probe in DEFAULT_PROBES if probe.category == "schema_version")
    assert "transaction_read_only" in schema_probe.sql
