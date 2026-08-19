from __future__ import annotations

from dataclasses import dataclass
from zoneinfo import ZoneInfo

from identity.ports.authorization import JobHealthAccessScope
from operations.application.dependencies import JobHealthDependencies
from operations.domain.job_health import JobHealthInputs, JobHealthSnapshot, evaluate_job_health


@dataclass(frozen=True, slots=True)
class ScopedJobHealth:
    health: JobHealthSnapshot
    investigation_links: dict[str, str] | None
    escalation_guidance: str | None


class JobHealthService:
    def __init__(self, dependencies: JobHealthDependencies) -> None:
        self._dependencies = dependencies

    def read(self, actor_id: int) -> ScopedJobHealth:
        scope = self._dependencies.authorization.authorize_job_health(actor_id)
        refreshed_at = self._dependencies.clock.now()
        with self._dependencies.read_unit_of_work_factory():
            latest = self._dependencies.job_runs.latest()
            successful = self._dependencies.job_runs.latest_successful()
            terminal = self._dependencies.job_runs.latest_terminal()
            unfinished = self._dependencies.job_runs.unfinished()
            evidence = self._dependencies.attendance_health.read_evidence(
                refreshed_at.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
            )
        health = evaluate_job_health(
            JobHealthInputs(refreshed_at, latest, successful, terminal, unfinished, evidence)
        )
        investigate = scope is JobHealthAccessScope.INVESTIGATE
        return ScopedJobHealth(
            health,
            {"accounts": "/api/v1/users/"} if investigate else None,
            None if investigate else "Liên hệ MANAGER để điều tra và xử lý.",
        )
