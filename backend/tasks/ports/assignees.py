from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tasks.domain.tasks import IdentityDisplay


@dataclass(frozen=True, slots=True)
class AssigneeEligibility:
    eligible: tuple[IdentityDisplay, ...]
    violating_ids: tuple[int, ...]


class AssigneeDirectory(Protocol):
    def lock_eligible(self, user_ids: tuple[int, ...]) -> AssigneeEligibility: ...
    def lock_and_reauthorize_self(self, actor_id: int) -> IdentityDisplay: ...
