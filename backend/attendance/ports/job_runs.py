from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ReconciliationFinalization:
    finished_at: datetime
    session_failed: bool
    aborted: bool


class ReconciliationJobRuns(Protocol):
    def create(self, started_at: datetime) -> int: ...

    def record_scan(self, run_id: int, *, changed: bool) -> None: ...

    def record_failed_scan(self, run_id: int) -> None: ...

    def changed_count(self, run_id: int) -> int: ...

    def counts(self, run_id: int) -> tuple[int, int, int]: ...

    def finalize(
        self,
        run_id: int,
        finalization: ReconciliationFinalization,
    ) -> str | None: ...
