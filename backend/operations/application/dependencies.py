from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from types import TracebackType
from typing import Protocol

from attendance.ports.clock import Clock
from operations.ports.attendance_health import AttendanceHealthReader
from operations.ports.authorization import JobHealthAuthorization
from operations.ports.job_runs import JobRunRepository


class ReadUnitOfWork(Protocol):
    def __enter__(self) -> ReadUnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class JobHealthDependencies:
    authorization: JobHealthAuthorization
    clock: Clock
    job_runs: JobRunRepository
    attendance_health: AttendanceHealthReader
    read_unit_of_work_factory: Callable[[], ReadUnitOfWork]
