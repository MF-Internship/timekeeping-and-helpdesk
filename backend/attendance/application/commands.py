from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db import IntegrityError

from attendance.application.anomalies import reconcile_punch_anomalies
from attendance.application.dependencies import AttendanceDependencies
from attendance.application.dto import (
    AcceptedPunchRequest,
    AttendanceCommand,
    AttendanceSnapshot,
    CommandResult,
    ReferenceSnapshot,
    SessionProjection,
)
from attendance.application.projections import punch_index
from attendance.domain.attempts import AttendanceAttemptOutcome
from attendance.domain.attendance import (
    AttendanceKind,
    AttendanceResolutionMethod,
    LocationMatch,
    passes_accuracy,
    resolve_location,
)
from attendance.domain.sessions import SessionSnapshot
from attendance.ports.attempts import AttemptDraft
from audit.ports.recording import AuditAction, AuditEntry
from core.error_codes import (
    INVALID_LOCATION_CHOICE,
    LOCATION_CHOICE_REQUIRED,
    NO_OPEN_SESSION,
    OUTSIDE_RADIUS,
    SESSION_ALREADY_OPEN,
    WEAK_GPS,
)
from core.errors import IdentityAPIError

LOGGER = logging.getLogger("attendance.attempts")


@dataclass(slots=True)
class _Observation:
    nearest_location_id: int | None = None
    nearest_distance_m: Decimal | None = None
    candidate_count: int | None = None


@dataclass(slots=True)
class _Execution:
    actor_id: int
    kind: AttendanceKind
    work_date: date
    recorded_at: datetime
    command: AttendanceCommand
    observation: _Observation


@dataclass(slots=True)
class _AcceptedExecution:
    context: _Execution
    session: SessionSnapshot | None
    match: LocationMatch
    resolution: AttendanceResolutionMethod
    reference: ReferenceSnapshot


@dataclass(slots=True)
class _RejectedError(Exception):
    outcome: AttendanceAttemptOutcome
    error_code: str
    status_code: int
    candidates: tuple[LocationMatch, ...] = ()


class AttendanceCommandService:
    def __init__(self, dependencies: AttendanceDependencies) -> None:
        self._dependencies = dependencies

    def check_in(self, actor_id: int, command: AttendanceCommand) -> CommandResult:
        self._dependencies.authorization.authorize_check_in(actor_id)
        return self._execute(actor_id, AttendanceKind.IN, command)

    def check_out(self, actor_id: int, command: AttendanceCommand) -> CommandResult:
        self._dependencies.authorization.authorize_check_out(actor_id)
        return self._execute(actor_id, AttendanceKind.OUT, command)

    def _execute(
        self, actor_id: int, kind: AttendanceKind, command: AttendanceCommand
    ) -> CommandResult:
        recorded_at = self._dependencies.clock.now()
        work_date = recorded_at.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
        observation = _Observation()
        context = _Execution(actor_id, kind, work_date, recorded_at, command, observation)
        try:
            result = self._business(context)
        except _RejectedError as rejection:
            self._append_attempt(self._draft(context, rejection.outcome))
            raise _api_error(rejection) from None
        except IntegrityError as error:
            if kind is not AttendanceKind.IN or not _is_open_session_conflict(error):
                raise
            constraint_rejection = _RejectedError(
                AttendanceAttemptOutcome.SESSION_ALREADY_OPEN,
                SESSION_ALREADY_OPEN,
                409,
            )
            self._append_attempt(self._draft(context, constraint_rejection.outcome))
            raise _api_error(constraint_rejection) from None
        except Exception:
            LOGGER.error("attendance infrastructure failure")
            raise
        self._append_attempt(
            self._draft(context, AttendanceAttemptOutcome.ACCEPTED, result.attendance.id)
        )
        return result

    def _business(self, context: _Execution) -> CommandResult:
        with self._dependencies.unit_of_work_factory():
            reference = self._dependencies.reference_data.load_locked()
            _observe_nearest(self._dependencies, reference, context.command, context.observation)
            session = self._dependencies.repository.open_session(
                context.actor_id, lock=context.kind is AttendanceKind.OUT
            )
            _validate_session(context.kind, session is not None)
            match, resolution = self._resolve_match(context, reference)
            return self._persist(_AcceptedExecution(context, session, match, resolution, reference))

    def _resolve_match(
        self, context: _Execution, reference: ReferenceSnapshot
    ) -> tuple[LocationMatch, AttendanceResolutionMethod]:
        candidates = _candidate_matches(self._dependencies, reference, context.command)
        if not passes_accuracy(
            context.command.accuracy_m, reference.config.max_attendance_accuracy_m
        ):
            raise _RejectedError(AttendanceAttemptOutcome.WEAK_GPS, WEAK_GPS, 422)
        context.observation.candidate_count = len(candidates)
        match, resolution = resolve_location(candidates, context.command.selected_location_id)
        _validate_resolution(candidates, context.command.selected_location_id, match)
        assert match is not None and resolution is not None
        return match, resolution

    def _persist(self, accepted: _AcceptedExecution) -> CommandResult:
        context = accepted.context
        attendance = self._dependencies.repository.create_attendance(
            AcceptedPunchRequest(
                context.actor_id,
                context.kind,
                context.work_date,
                context.recorded_at,
                context.command,
                accepted.match,
                accepted.resolution,
            )
        )
        projection = (
            self._dependencies.repository.open_new_session(attendance)
            if context.kind is AttendanceKind.IN
            else self._dependencies.repository.close_session(accepted.session, attendance)  # type: ignore[arg-type]
        )
        punches = self._dependencies.repository.punches(context.actor_id, context.work_date)
        reconcile_punch_anomalies(
            self._dependencies.repository, punches, attendance, accepted.reference.config
        )
        self._append_audit(context, attendance, projection)
        return CommandResult(attendance, projection, punch_index(punches, attendance.id))

    def _append_audit(
        self,
        context: _Execution,
        attendance: AttendanceSnapshot,
        projection: SessionProjection,
    ) -> None:
        attendance_id = attendance.id
        location_id = attendance.location.id
        session_id = projection.id
        action = (
            AuditAction.ATTENDANCE_CHECK_IN_CREATED
            if context.kind is AttendanceKind.IN
            else AuditAction.ATTENDANCE_CHECK_OUT_CREATED
        )
        self._dependencies.audit.append_audit_entry(
            AuditEntry(
                context.actor_id,
                action,
                "Attendance",
                str(attendance_id),
                {},
                {
                    "attendance_id": attendance_id,
                    "kind": context.kind.value,
                    "work_date": context.work_date.isoformat(),
                    "location_id": location_id,
                    "session_id": session_id,
                },
            )
        )

    def _draft(
        self,
        context: _Execution,
        outcome: AttendanceAttemptOutcome,
        attendance_id: int | None = None,
    ) -> AttemptDraft:
        return AttemptDraft(
            context.actor_id,
            context.kind,
            context.work_date,
            context.recorded_at,
            outcome,
            attendance_id,
            context.command.latitude,
            context.command.longitude,
            context.command.accuracy_m,
            context.observation.nearest_location_id,
            context.observation.nearest_distance_m,
            context.observation.candidate_count,
            context.command.device_metadata or {},
            context.command.request_ip,
        )

    def _append_attempt(self, draft: AttemptDraft) -> None:
        try:
            self._dependencies.attempts.append(draft)
        except Exception:
            LOGGER.error("attendance attempt persistence failed outcome=%s", draft.outcome.value)


def _observe_nearest(
    dependencies: AttendanceDependencies,
    reference: ReferenceSnapshot,
    command: AttendanceCommand,
    observation: _Observation,
) -> None:
    matches = tuple(
        LocationMatch(
            location,
            dependencies.reference_data.distance_m(command.latitude, command.longitude, location),
        )
        for location in reference.locations
    )
    nearest = min(matches, key=lambda item: (item.distance_m, item.location.code))
    observation.nearest_location_id = nearest.location.id
    observation.nearest_distance_m = nearest.distance_m


def _candidate_matches(
    dependencies: AttendanceDependencies,
    reference: ReferenceSnapshot,
    command: AttendanceCommand,
) -> tuple[LocationMatch, ...]:
    if not passes_accuracy(command.accuracy_m, reference.config.max_attendance_accuracy_m):
        return ()
    matches = (
        LocationMatch(
            location,
            dependencies.reference_data.distance_m(command.latitude, command.longitude, location),
        )
        for location in reference.locations
        if location.is_active
    )
    return tuple(match for match in matches if match.distance_m <= match.location.radius_m)


def _validate_session(kind: AttendanceKind, has_open_session: bool) -> None:
    if kind is AttendanceKind.IN and has_open_session:
        raise _RejectedError(
            AttendanceAttemptOutcome.SESSION_ALREADY_OPEN, SESSION_ALREADY_OPEN, 409
        )
    if kind is AttendanceKind.OUT and not has_open_session:
        raise _RejectedError(AttendanceAttemptOutcome.NO_OPEN_SESSION, NO_OPEN_SESSION, 409)


def _validate_resolution(
    candidates: tuple[LocationMatch, ...],
    selected_location_id: int | None,
    match: LocationMatch | None,
) -> None:
    if not candidates:
        raise _RejectedError(AttendanceAttemptOutcome.OUTSIDE_RADIUS, OUTSIDE_RADIUS, 422)
    if selected_location_id is None and len(candidates) > 1:
        raise _RejectedError(
            AttendanceAttemptOutcome.LOCATION_CHOICE_REQUIRED,
            LOCATION_CHOICE_REQUIRED,
            409,
            candidates,
        )
    if match is None:
        raise _RejectedError(
            AttendanceAttemptOutcome.INVALID_LOCATION_CHOICE,
            INVALID_LOCATION_CHOICE,
            422,
            candidates,
        )


def _api_error(rejection: _RejectedError) -> IdentityAPIError:
    details: dict[str, object] = {}
    if rejection.candidates:
        details["location_candidates"] = [
            {
                "id": item.location.id,
                "code": item.location.code,
                "name": item.location.name,
                "distance_m": str(item.distance_m),
            }
            for item in rejection.candidates
        ]
    return IdentityAPIError(
        rejection.error_code, status_code=rejection.status_code, details=details
    )


def _is_open_session_conflict(error: IntegrityError) -> bool:
    cause = error.__cause__
    diagnostics = getattr(cause, "diag", None)
    return getattr(diagnostics, "constraint_name", None) == "uniq_open_session_per_user"
