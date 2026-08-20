from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AccountNotificationEligibility:
    user_id: int
    is_active: bool


class AccountNotificationFacts(Protocol):
    def get_eligibility(self, user_id: int) -> AccountNotificationEligibility | None: ...
