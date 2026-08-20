from __future__ import annotations

from django.db import IntegrityError

from core.error_codes import NOT_FOUND, VALIDATION_FAILED
from core.errors import IdentityAPIError
from identity.ports.authorization import PermissionAction
from locations.application.dependencies import LocationDependencies
from locations.application.dto import CreateHolidayRequest
from locations.application.evidence import EvidenceRequest, append_evidence, holiday_outbox_payload
from locations.domain.events import LocationEventType
from locations.domain.holidays import HolidaySnapshot


class HolidayService:
    def __init__(self, dependencies: LocationDependencies) -> None:
        self._dependencies = dependencies

    def list(self, actor_id: int) -> tuple[HolidaySnapshot, ...]:
        self._dependencies.authorization.authorize(actor_id, PermissionAction.HOLIDAY_MANAGE)
        return self._dependencies.holidays.list()

    def create(self, actor_id: int, request: CreateHolidayRequest) -> HolidaySnapshot:
        self._dependencies.authorization.authorize(actor_id, PermissionAction.HOLIDAY_MANAGE)
        if not request.name.strip():
            raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
        try:
            with self._dependencies.unit_of_work_factory():
                created = self._dependencies.holidays.create(request.date, request.name.strip())
                append_evidence(
                    self._dependencies.audit,
                    EvidenceRequest(
                        actor_id,
                        LocationEventType.HOLIDAY_CREATED,
                        "Holiday",
                        created.id,
                        {},
                        {"date": request.date.isoformat(), "name": created.name},
                        holiday_outbox_payload(created.id, request.date.isoformat()),
                    ),
                )
                return created
        except IntegrityError as error:
            raise IdentityAPIError(VALIDATION_FAILED, status_code=400) from error

    def delete(self, actor_id: int, holiday_id: int) -> None:
        self._dependencies.authorization.authorize(actor_id, PermissionAction.HOLIDAY_MANAGE)
        with self._dependencies.unit_of_work_factory():
            current = self._dependencies.holidays.get(holiday_id, lock=True)
            if current is None:
                raise IdentityAPIError(NOT_FOUND, status_code=404)
            append_evidence(
                self._dependencies.audit,
                EvidenceRequest(
                    actor_id,
                    LocationEventType.HOLIDAY_DELETED,
                    "Holiday",
                    current.id,
                    {"date": current.date.isoformat(), "name": current.name},
                    {"deleted": True},
                    holiday_outbox_payload(current.id, current.date.isoformat()),
                ),
            )
            self._dependencies.holidays.delete(current.id)
