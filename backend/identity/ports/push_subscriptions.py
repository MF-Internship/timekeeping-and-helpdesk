from enum import StrEnum
from typing import Protocol


class PushSubscriptionRevocationReason(StrEnum):
    LOGOUT = "LOGOUT"
    ACCOUNT_SWITCH = "ACCOUNT_SWITCH"
    ACCOUNT_DEACTIVATED = "ACCOUNT_DEACTIVATED"


class PushSubscriptionRevoker(Protocol):
    def revoke_all(self, user_id: int, reason: PushSubscriptionRevocationReason) -> None: ...


class NoopPushSubscriptionRevoker:
    def revoke_all(self, user_id: int, reason: PushSubscriptionRevocationReason) -> None:
        return None
