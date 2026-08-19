from __future__ import annotations

from typing import Protocol

from identity.ports.authorization import JobHealthAccessScope


class JobHealthAuthorization(Protocol):
    def authorize_job_health(self, actor_id: int) -> JobHealthAccessScope: ...
