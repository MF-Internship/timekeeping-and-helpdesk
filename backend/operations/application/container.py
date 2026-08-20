from dataclasses import dataclass

from audit.application.relay import OutboxRelayService
from operations.application.job_health import JobHealthService


@dataclass(frozen=True, slots=True)
class OperationsContainer:
    job_health: JobHealthService
    outbox_relay: OutboxRelayService
