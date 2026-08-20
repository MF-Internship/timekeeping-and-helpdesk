from typing import Protocol

from notifications.application.dto import AccountEligibility


class AccountEligibilityPort(Protocol):
    def get_eligibility(self, user_id: int) -> AccountEligibility | None: ...
