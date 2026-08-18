from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import close_old_connections

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from core.errors import IdentityAPIError
from locations.application.dto import UpdateLocationRequest
from locations.models import Config
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.locations.helpers import create_config, create_location


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_competing_config_updates_serialize_and_allocate_versions() -> None:
    create_config()
    create_location()
    actor = create_user("config-update-race", "MANAGER")
    barrier = Barrier(2)

    def update(value: int) -> None:
        close_old_connections()
        barrier.wait()
        locations_container().config_admin.update(actor.pk, {"late_grace_minutes": value})
        close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(update, (20, 30)))
    assert Config.objects.get().late_grace_minutes in {20, 30}
    assert list(
        OutboxEvent.objects.filter(aggregate_type="Config")
        .order_by("aggregate_version")
        .values_list("aggregate_version", flat=True)
    ) == [1, 2]
    assert AuditLog.objects.filter(target_type="Config").count() == 2


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_config_cap_vs_location_radius_update_has_exactly_one_winner() -> None:  # noqa: PLR0915
    create_config()
    target = create_location()
    actor = create_user("config-location-race", "MANAGER")
    barrier = Barrier(2)

    def config_update() -> str:
        close_old_connections()
        barrier.wait()
        try:
            locations_container().config_admin.update(actor.pk, {"max_radius_m": Decimal("50")})
        except IdentityAPIError:
            result = "DENIED"
        else:
            result = "OK"
        close_old_connections()
        return result

    def location_update() -> str:
        close_old_connections()
        barrier.wait()
        try:
            locations_container().location_admin.update(
                actor.pk, target.pk, UpdateLocationRequest(version=1, radius_m=Decimal("60"))
            )
        except IdentityAPIError:
            result = "DENIED"
        else:
            result = "OK"
        close_old_connections()
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(config_update), pool.submit(location_update)]
        outcomes = [future.result() for future in results]
    assert sorted(outcomes) == ["DENIED", "OK"]
    config = Config.objects.get()
    target.refresh_from_db()
    assert target.radius_m <= config.max_radius_m


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_config_same_value_vs_mutation_has_consecutive_evidence_only_for_writes() -> None:
    create_config()
    actor = create_user("config-noop-race", "MANAGER")
    barrier = Barrier(2)

    def update(value: int) -> None:
        close_old_connections()
        barrier.wait()
        locations_container().config_admin.update(actor.pk, {"late_grace_minutes": value})
        close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(update, (15, 20)))
    versions = list(
        OutboxEvent.objects.filter(aggregate_type="Config")
        .order_by("aggregate_version")
        .values_list("aggregate_version", flat=True)
    )
    assert versions in ([1], [1, 2])
