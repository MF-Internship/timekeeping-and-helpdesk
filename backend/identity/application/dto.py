from __future__ import annotations

from dataclasses import dataclass, field

from identity.domain.accounts import AccountSnapshot
from identity.domain.authorization import Role


@dataclass(frozen=True, slots=True)
class LoginRequest:
    username: str
    password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class SessionResult:
    access: str = field(repr=False)
    account: AccountSnapshot
    capabilities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UserCreateRequest:
    username: str
    full_name: str
    role: Role
    phone: str | None = None
    email: str | None = None


@dataclass(frozen=True, slots=True)
class GeneratedPasswordDisplayResult:
    account: AccountSnapshot
    generated_password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class ProfileUpdateRequest:
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    provided_fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class PasswordChangeRequest:
    current_password: str = field(repr=False)
    new_password: str = field(repr=False)
