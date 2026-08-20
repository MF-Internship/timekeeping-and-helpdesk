from __future__ import annotations

from datetime import date

import pytest

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from locations.application.dto import CreateHolidayRequest
from locations.models import Holiday
from tests.integration.api.identity.helpers import create_user


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.parametrize("recorder_method", ["append_audit_entry", "append_outbox_event"])
def test_holiday_create_rolls_back_on_evidence_failure(
    monkeypatch: pytest.MonkeyPatch, recorder_method: str
) -> None:
    actor = create_user("holiday-rollback-manager", "MANAGER")
    service = locations_container().holidays
    monkeypatch.setattr(
        service._dependencies.audit,
        recorder_method,
        lambda event: (_ for _ in ()).throw(RuntimeError("injected")),
    )
    with pytest.raises(RuntimeError, match="injected"):
        service.create(actor.pk, CreateHolidayRequest(date(2027, 1, 1), "Holiday"))
    assert not Holiday.objects.exists()
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.parametrize("recorder_method", ["append_audit_entry", "append_outbox_event"])
def test_holiday_delete_rolls_back_on_evidence_failure(
    monkeypatch: pytest.MonkeyPatch, recorder_method: str
) -> None:
    actor = create_user("holiday-delete-rollback-manager", "MANAGER")
    holiday = Holiday.objects.create(date=date(2027, 1, 2), name="Holiday")
    service = locations_container().holidays
    audit_count = AuditLog.objects.count()
    outbox_count = OutboxEvent.objects.count()
    monkeypatch.setattr(
        service._dependencies.audit,
        recorder_method,
        lambda event: (_ for _ in ()).throw(RuntimeError("injected")),
    )

    with pytest.raises(RuntimeError, match="injected"):
        service.delete(actor.pk, holiday.pk)

    assert Holiday.objects.filter(pk=holiday.pk).exists()
    assert AuditLog.objects.count() == audit_count
    assert OutboxEvent.objects.count() == outbox_count
