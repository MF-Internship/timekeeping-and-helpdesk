from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from django.db import close_old_connections

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from core.errors import IdentityAPIError
from locations.application.dto import UpdateLocationRequest
from locations.models import Location
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.locations.helpers import create_config, create_location

ROOT = Path(__file__).parents[5]


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_different_location_updates_compete_without_lost_versions() -> None:
    create_config()
    first = create_location("RACE00001")
    second = create_location("RACE00002")
    actor = create_user("location-cross-race", "MANAGER")
    barrier = Barrier(2)

    def update(item: Location) -> None:
        close_old_connections()
        barrier.wait()
        locations_container().location_admin.update(
            actor.pk, item.pk, UpdateLocationRequest(version=1, name=f"Changed {item.pk}")
        )
        close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(update, (first, second)))
    assert list(Location.objects.order_by("code").values_list("version", flat=True)) == [2, 2]
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 2
    assert set(OutboxEvent.objects.values_list("aggregate_version", flat=True)) == {1}


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_same_value_vs_mutation_linearizes_without_lost_update() -> None:
    create_config()
    target = create_location()
    actor = create_user("location-noop-race", "MANAGER")
    barrier = Barrier(2)

    def update(name: str) -> str:
        close_old_connections()
        barrier.wait()
        try:
            locations_container().location_admin.update(
                actor.pk, target.pk, UpdateLocationRequest(version=1, name=name)
            )
        except IdentityAPIError as error:
            result = error.error_code
        else:
            result = "OK"
        close_old_connections()
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(update, (target.name, "Mutated")))
    target.refresh_from_db()
    assert target.name == "Mutated" and target.version == 2
    assert results.count("OK") >= 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_location_update_vs_seed_serializes_and_preserves_canonical_cardinality() -> None:
    create_config()
    actor = create_user("location-seed-race", "MANAGER")
    paths = (ROOT / "docs/dia_chi_ttkd.csv", ROOT / "docs/dia_chi_cua_hang.csv")
    locations_container().seed.seed(actor.pk, *paths)
    target = Location.objects.get(code="HCM020129")
    barrier = Barrier(2)

    def update() -> None:
        close_old_connections()
        barrier.wait()
        locations_container().location_admin.update(
            actor.pk, target.pk, UpdateLocationRequest(version=1, name="Manager value")
        )
        close_old_connections()

    def seed() -> None:
        close_old_connections()
        barrier.wait()
        locations_container().seed.seed(actor.pk, *paths)
        close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        [future.result() for future in (pool.submit(update), pool.submit(seed))]
    assert Location.objects.count() == 76
    target.refresh_from_db()
    assert target.version in {2, 3}
