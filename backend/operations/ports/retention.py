from __future__ import annotations

from datetime import datetime
from typing import Protocol


class RetentionRepository(Protocol):
    def delete_processed_events(self, *, older_than: datetime, limit: int) -> int: ...

    def delete_published_outbox(self, *, older_than: datetime, limit: int) -> int: ...

    def delete_dead_letter_outbox(self, *, older_than: datetime, limit: int) -> int: ...
