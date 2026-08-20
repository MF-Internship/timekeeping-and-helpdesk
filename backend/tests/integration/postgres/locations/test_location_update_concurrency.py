from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_same_version_competing_updates_have_one_winner() -> None:
    create_config()
    target = create_location()
    actor = create_user("location-race-manager", "MANAGER")
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
        results = list(pool.map(update, ("One", "Two")))
    assert sorted(results) == ["LOCATION_VERSION_CONFLICT", "OK"]
    target.refresh_from_db()
    assert target.version == 2
    assert Location.objects.count() == 1
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 1
    assert OutboxEvent.objects.get().aggregate_version == 1
