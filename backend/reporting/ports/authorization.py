from __future__ import annotations

from typing import Protocol


class ReportingAuthorization(Protocol):
    def authorize_view(self, actor_id: int) -> bool: ...

    def authorize_export(self, actor_id: int) -> None: ...

