from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from audit.models import AuditLog, OutboxEvent, ProcessedEvent
from config.operations_adapters import DjangoRetentionRepository
from identity.models import User
from operations.application.retention import prune_retention


def outbox(index: int, state: str) -> OutboxEvent:
    published_at = timezone.now() - timedelta(days=31) if state == "PUBLISHED" else None
    row = OutboxEvent.objects.create(
        event_type="identity.user.created",
        aggregate_type="User",
        aggregate_id=str(index),
        aggregate_version=1,
        payload={},
        publish_state=state,
        published_at=published_at,
    )
    return row


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_retention_prunes_only_allowed_categories_in_batches() -> None:
    now = timezone.now()
    actor = User.objects.create_user(
        username="retention-manager",
        password="SafePassword123!",
        full_name="Manager",
        role="MANAGER",
    )
    AuditLog.objects.create(
        actor=actor,
        action="identity.user.created",
        target_type="User",
        target_id=str(actor.pk),
        before={},
        after={},
    )
    for index in range(3):
        ProcessedEvent.objects.create(
            consumer="consumer",
            event_id=f"00000000-0000-4000-8000-00000000000{index}",
        )
    ProcessedEvent.objects.update(processed_at=now - timedelta(days=31))
    old_published = [outbox(index, "PUBLISHED") for index in range(3)]
    pending = outbox(100, "PENDING")
    dead = outbox(200, "DEAD_LETTER")
    dead.created_at = now - timedelta(days=91)
    dead.save(update_fields=["created_at"])

    result = prune_retention(DjangoRetentionRepository(), now=now, batch_size=2)

    assert result.processed_event == 3
    assert result.outbox_published == 3
    assert result.outbox_dead_letter == 1
    assert not ProcessedEvent.objects.exists()
    assert not OutboxEvent.objects.filter(pk__in=[row.pk for row in old_published]).exists()
    assert OutboxEvent.objects.filter(pk=pending.pk, publish_state="PENDING").exists()
    assert AuditLog.objects.exists()
