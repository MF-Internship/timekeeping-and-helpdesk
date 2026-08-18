from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import IntegrityError, close_old_connections, transaction

from audit.adapters.persistence.recording import DjangoAuditRecorder
from audit.domain.records import AuditAction, AuditEntry, IdentityEventType, OutboxRecord
from audit.models import AuditLog, OutboxEvent
from identity.models import User


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_concurrent_duplicate_username_has_one_complete_winner() -> None:
    actor = User.objects.create_user(
        username="create-actor", password="SafePassword123!", full_name="Actor", role="MANAGER"
    )
    barrier = Barrier(2)

    def create(worker: int) -> str:
        close_old_connections()
        barrier.wait()
        try:
            with transaction.atomic():
                account = User.objects.create_user(
                    username="same-user",
                    password="SafePassword123!",
                    full_name=f"Worker {worker}",
                    role="HELPDESK",
                )
                recorder = DjangoAuditRecorder()
                values = {"full_name": account.full_name, "role": account.role}
                recorder.append_audit_entry(
                    AuditEntry(
                        actor.pk,
                        AuditAction.USER_CREATED,
                        "User",
                        str(account.pk),
                        {},
                        values,
                    )
                )
                recorder.append_outbox_event(
                    OutboxRecord(
                        IdentityEventType.USER_CREATED,
                        "User",
                        str(account.pk),
                        values,
                    )
                )
            return "created"
        except IntegrityError:
            return "duplicate"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create, range(2)))
    assert sorted(results) == ["created", "duplicate"]
    target = User.objects.get(username="same-user")
    assert AuditLog.objects.filter(target_id=str(target.pk)).count() == 1
    assert OutboxEvent.objects.filter(aggregate_id=str(target.pk)).count() == 1
