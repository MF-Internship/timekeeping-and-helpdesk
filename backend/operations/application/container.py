from dataclasses import dataclass

from operations.application.job_health import JobHealthService


@dataclass(frozen=True, slots=True)
class OperationsContainer:
    job_health: JobHealthService
