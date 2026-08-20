from __future__ import annotations

from typing import Protocol


class RecoveryHealthPublisher(Protocol):
    def request_alert(self, reason: object) -> bool: ...

    def emit_health_state(self, state: str) -> bool: ...
