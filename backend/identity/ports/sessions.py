from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class RevocationReason(StrEnum):
    LOGOUT = "LOGOUT"
    PASSWORD_RESET = "PASSWORD_RESET"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    ACCOUNT_DEACTIVATED = "ACCOUNT_DEACTIVATED"


@dataclass(frozen=True, slots=True)
class IssuedSession:
    access: str = field(repr=False)
    refresh: str = field(repr=False)


class SessionRepository(Protocol):
    def issue(self, user_id: int) -> IssuedSession: ...

    def rotate(self, refresh: str) -> IssuedSession: ...

    def revoke_all(self, user_id: int, reason: RevocationReason) -> int: ...

    def refresh_owner(self, refresh: str) -> int: ...
