from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import time
from threading import Barrier

import pytest
from django.db import close_old_connections

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from locations.application.config_admin import default_config
from locations.models import Config
from tests.integration.api.identity.helpers import create_user


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_competing_initializers_leave_one_complete_config_and_evidence_pair() -> None:
    actor = create_user("config-init-race", "MANAGER")
    candidate = default_config(
        shift_start=time(8),
        shift_end=time(17),
        late_grace_minutes=15,
        early_checkout_grace_minutes=10,
    )
    barrier = Barrier(2)

    def initialize(_: int) -> str:
        close_old_connections()
        barrier.wait()
        try:
            locations_container().config_admin.initialize(actor.pk, candidate)
        except Exception as error:  # one PK/check loser is expected
            result = type(error).__name__
        else:
            result = "OK"
        close_old_connections()
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(initialize, range(2)))
    assert results.count("OK") == 1
    assert Config.objects.count() == 1
    assert AuditLog.objects.filter(target_type="Config").count() == 1
    assert OutboxEvent.objects.filter(aggregate_type="Config").count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.parametrize("recorder_method", ["append_audit_entry", "append_outbox_event"])
def test_initialization_rolls_back_when_evidence_fails(
    monkeypatch: pytest.MonkeyPatch, recorder_method: str
) -> None:
    actor = create_user("config-init-rollback", "MANAGER")
    service = locations_container().config_admin
    monkeypatch.setattr(
        service._dependencies.audit,
        recorder_method,
        lambda event: (_ for _ in ()).throw(RuntimeError("injected")),
    )
    with pytest.raises(RuntimeError, match="injected"):
        service.initialize(
            actor.pk,
            default_config(
                shift_start=time(8),
                shift_end=time(17),
                late_grace_minutes=0,
                early_checkout_grace_minutes=0,
            ),
        )
    assert not Config.objects.exists()
    assert not AuditLog.objects.exists()
    assert not OutboxEvent.objects.exists()
