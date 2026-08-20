from __future__ import annotations

from datetime import date

import pytest

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from core.errors import IdentityAPIError
from locations.application.dto import CreateHolidayRequest
from locations.models import Holiday
from tests.integration.api.identity.helpers import create_user


@pytest.mark.django_db
@pytest.mark.unit
def test_holiday_service_orders_creates_deletes_and_rejects_duplicates() -> None:
    actor = create_user("holiday-service-manager", "MANAGER")
    service = locations_container().holidays
    later = service.create(actor.pk, CreateHolidayRequest(date(2027, 2, 1), "Later"))
    earlier = service.create(actor.pk, CreateHolidayRequest(date(2027, 1, 1), " Earlier "))
    assert [item.id for item in service.list(actor.pk)] == [earlier.id, later.id]
    with pytest.raises(IdentityAPIError) as error:
        service.create(actor.pk, CreateHolidayRequest(date(2027, 1, 1), "Duplicate"))
    assert error.value.error_code == "VALIDATION_FAILED"
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 2
    service.delete(actor.pk, earlier.id)
    assert not Holiday.objects.filter(pk=earlier.id).exists()
    with pytest.raises(IdentityAPIError) as error:
        service.delete(actor.pk, earlier.id)
    assert error.value.error_code == "NOT_FOUND"
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 3
    assert list(OutboxEvent.objects.order_by("id").values_list("payload", flat=True)) == [
        {
            "action": "locations.holiday.created",
            "holiday_id": later.id,
            "date": "2027-02-01",
        },
        {
            "action": "locations.holiday.created",
            "holiday_id": earlier.id,
            "date": "2027-01-01",
        },
        {
            "action": "locations.holiday.deleted",
            "holiday_id": earlier.id,
            "date": "2027-01-01",
        },
    ]
