from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from identity.domain.authorization import Role


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    id: int
    username: str
    full_name: str
    phone: str | None
    email: str | None
    role: Role
    is_active: bool = True
    must_change_password: bool = True
    last_login: datetime | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        username = self.username.strip()
        full_name = self.full_name.strip()
        if not username:
            raise ValueError("username must not be blank")
        if not full_name:
            raise ValueError("full_name must not be blank")
        object.__setattr__(self, "username", username)
        object.__setattr__(self, "full_name", full_name)


@dataclass(frozen=True, slots=True)
class NewAccount:
    username: str
    full_name: str
    phone: str | None
    email: str | None
    role: Role
    password_hash: str


@dataclass(frozen=True, slots=True)
class UserFilters:
    query: str | None = None
    role: Role | None = None
    is_active: bool | None = None
