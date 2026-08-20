from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from threading import Event

import pytest
from django.db import close_old_connections, transaction

from attendance.adapters.persistence.attempts import DjangoAttemptWriter
from attendance.adapters.persistence.repositories import DjangoAttendanceRepository
from attendance.adapters.persistence.unit_of_work import DjangoUnitOfWork
from attendance.application.commands import AttendanceCommandService
from attendance.application.dependencies import AttendanceDependencies
from attendance.application.dto import AttendanceCommand, ReferenceSnapshot
from audit.adapters.persistence.recording import DjangoAuditRecorder
from config.attendance_adapters import (
    DjangoAttendanceReferenceData,
    _config_snapshot,
    _location_snapshot,
)
from identity.models import User
from locations.models import Config, Location
from tests.integration.api.attendance.helpers import create_reference_data

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


class Authorization:
    def authorize_check_in(self, actor_id: int) -> None:
        return None

    def authorize_check_out(self, actor_id: int) -> None:
        return None

    def authorize_view_self(self, actor_id: int) -> None:
        return None


class Clock:
    def now(self) -> datetime:
        return datetime(2026, 8, 18, 1, tzinfo=UTC)


class PausingReferenceData(DjangoAttendanceReferenceData):
    def __init__(self, locked: Event, release: Event) -> None:
        self.locked = locked
        self.release = release

    def load_locked(self) -> ReferenceSnapshot:
        config = Config.objects.select_for_update().get(pk=1)
        self.locked.set()
        assert self.release.wait(timeout=5)
        rows = tuple(Location.objects.order_by("code", "id"))
        assert len(rows) == 76
        return ReferenceSnapshot(
            _config_snapshot(config), tuple(_location_snapshot(row) for row in rows)
        )


def test_punch_and_reference_mutation_never_mix_snapshot_versions() -> None:
    _, (near,) = create_reference_data()
    user = User.objects.create(
        username="reference-race",
        full_name="Reference Race",
        role="HELPDESK",
        password="!",
        must_change_password=False,
    )
    locked, mutation_started, release = Event(), Event(), Event()
    service = _service(PausingReferenceData(locked, release))
    with ThreadPoolExecutor(max_workers=2) as pool:
        punch = pool.submit(_check_in, service, user.pk)
        mutation = pool.submit(_mutate, near.pk, locked, mutation_started)
        assert mutation_started.wait(timeout=5)
        release.set()
        result = punch.result(timeout=5)
        mutation.result(timeout=5)
    assert result.attendance.location.id == near.pk
    near.refresh_from_db()
    assert near.is_active is False


def _service(reference: PausingReferenceData) -> AttendanceCommandService:
    dependencies = AttendanceDependencies(
        Authorization(),
        Clock(),
        reference,
        DjangoAttendanceRepository(),
        DjangoAttemptWriter(),
        DjangoAuditRecorder(),
        DjangoUnitOfWork,
    )
    return AttendanceCommandService(dependencies)


def _check_in(service: AttendanceCommandService, user_id: int):
    close_old_connections()
    try:
        return service.check_in(
            user_id, AttendanceCommand(Decimal("10"), Decimal("106"), Decimal("5"))
        )
    finally:
        close_old_connections()


def _mutate(location_id: int, locked: Event, started: Event) -> None:
    close_old_connections()
    try:
        assert locked.wait(timeout=5)
        started.set()
        with transaction.atomic():
            config = Config.objects.select_for_update().get(pk=1)
            config.max_attendance_accuracy_m = 10
            config.save(update_fields=["max_attendance_accuracy_m"])
            Location.objects.filter(pk=location_id).update(is_active=False)
    finally:
        close_old_connections()
