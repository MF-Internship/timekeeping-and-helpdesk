from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import close_old_connections

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from core.errors import IdentityAPIError
from locations.application.dto import CreateHolidayRequest
from locations.models import Holiday
from tests.integration.api.identity.helpers import create_user


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_competing_same_date_creates_have_one_winner() -> None:
    actor = create_user("holiday-race-manager", "MANAGER")
    barrier = Barrier(2)

    def create(name: str) -> str:
        close_old_connections()
        barrier.wait()
        try:
            locations_container().holidays.create(
                actor.pk, CreateHolidayRequest(date(2027, 1, 1), name)
            )
        except IdentityAPIError as error:
            result = error.error_code
        else:
            result = "OK"
        close_old_connections()
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, ("A", "B")))
    assert sorted(results) == ["OK", "VALIDATION_FAILED"]
    assert Holiday.objects.count() == 1
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_competing_deletes_have_one_winner_and_one_evidence_pair() -> None:
    actor = create_user("holiday-delete-race-manager", "MANAGER")
    holiday = Holiday.objects.create(date=date(2027, 1, 2), name="Delete")
    barrier = Barrier(2)

    def delete(_: int) -> str:
        close_old_connections()
        barrier.wait()
        try:
            locations_container().holidays.delete(actor.pk, holiday.pk)
        except IdentityAPIError as error:
            result = error.error_code
        else:
            result = "OK"
        close_old_connections()
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(delete, range(2)))
    assert sorted(results) == ["NOT_FOUND", "OK"]
    assert not Holiday.objects.exists()
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 1
    assert OutboxEvent.objects.get().aggregate_version == 1
