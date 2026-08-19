from __future__ import annotations

from datetime import date
from typing import Protocol


class ReconciliationRepository(Protocol):
    def candidate_ids(self, current_date: date) -> tuple[int, ...]: ...

    def reconcile_locked(self, session_id: int, current_date: date) -> bool: ...
