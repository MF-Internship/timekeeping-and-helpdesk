from __future__ import annotations

import uuid

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from audit.models import AuditLog, OutboxEvent
from identity.models import User


def actor() -> User:
    return User.objects.create_user(
        username="audit-actor", password="SafePassword123!", full_name="Actor", role="MANAGER"
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_audit_shape_immutability_and_protective_actor_fk() -> None:
    account = actor()
    entry = AuditLog.objects.create(
        actor=account,
        action="identity.user.created",
        target_type="User",
        target_id="1",
        before={},
        after={"role": "HELPDESK"},
    )
    columns = {field.column for field in AuditLog._meta.concrete_fields}
    assert columns == {
        "id",
        "actor_id",
        "action",
        "target_type",
        "target_id",
        "before",
        "after",
        "recorded_at",
    }
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditLog.objects.filter(pk=entry.pk).update(action="changed")
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditLog.objects.filter(pk=entry.pk).delete()
    with pytest.raises(ProtectedError):
        account.delete()


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_outbox_checks_uniqueness_defaults_and_pending_index() -> None:
    event = OutboxEvent.objects.create(
        event_type="identity.user.created",
        aggregate_type="User",
        aggregate_id="1",
        aggregate_version=1,
        payload={"role": "HELPDESK"},
    )
    assert event.schema_version == 1
    assert event.publish_state == "PENDING"
    with pytest.raises(IntegrityError), transaction.atomic():
        OutboxEvent.objects.create(
            event_type="identity.user.created",
            aggregate_type="User",
            aggregate_id="1",
            aggregate_version=1,
            payload={},
        )
    for field, value in (("schema_version", 0), ("aggregate_version", 0), ("publish_state", "BAD")):
        values = {
            "event_type": "identity.user.created",
            "aggregate_type": "User",
            "aggregate_id": field,
            "aggregate_version": 2,
            "payload": {},
        }
        values[field] = value
        with pytest.raises(IntegrityError), transaction.atomic():
            OutboxEvent.objects.create(**values)
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, OutboxEvent._meta.db_table)
    assert constraints["audit_outbox_pending_idx"]["index"] is True


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_outbox_ddl_defaults_and_event_id_uniqueness_without_orm_defaults() -> None:
    event_id = uuid.uuid4()
    table = OutboxEvent._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO {table}
                (event_id, event_type, aggregate_type, aggregate_id,
                 aggregate_version, payload, created_at)
            VALUES (%s, %s, %s, %s, %s, '{{}}'::jsonb, %s)
            RETURNING schema_version, request_id, correlation_id, publish_state
            """,
            [event_id, "identity.user.created", "User", "raw-defaults", 1, timezone.now()],
        )
        assert cursor.fetchone() == (1, "", "", "PENDING")

    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO {table}
                (event_id, event_type, aggregate_type, aggregate_id,
                 aggregate_version, payload, created_at)
            VALUES (%s, %s, %s, %s, %s, '{{}}'::jsonb, %s)
            """,
            [event_id, "identity.user.created", "User", "duplicate-event", 1, timezone.now()],
        )
