from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections

from audit.models import AuditLog, OutboxEvent
from config.composition import identity_container
from identity.application.dto import ProfileUpdateRequest
from identity.models import User


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_competing_workers_serialize_per_aggregate_versions() -> None:
    workers = 8
    barrier = Barrier(workers)
    actor = User.objects.create_user(
        username="aggregate-manager",
        password="SafePassword123!",
        full_name="Manager",
        role="MANAGER",
    )
    target = User.objects.create_user(
        username="aggregate-target",
        password="SafePassword123!",
        full_name="Target",
        role="HELPDESK",
    )

    def append(index: int) -> None:
        close_old_connections()
        try:
            barrier.wait()
            identity_container().user_admin.update_profile(
                actor.pk,
                target.pk,
                ProfileUpdateRequest(
                    full_name=f"Target {index}",
                    provided_fields=frozenset({"full_name"}),
                ),
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(append, range(workers)))

    versions = list(
        OutboxEvent.objects.filter(aggregate_type="User", aggregate_id=str(target.pk))
        .order_by("aggregate_version")
        .values_list("aggregate_version", flat=True)
    )
    assert versions == list(range(1, workers + 1))
    assert AuditLog.objects.filter(target_id=str(target.pk)).count() == workers
    assert OutboxEvent.objects.filter(aggregate_id=str(target.pk)).count() == workers
