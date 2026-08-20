from __future__ import annotations

from dataclasses import dataclass

from identity.domain.accounts import AccountSnapshot
from identity.domain.authorization import Role
from identity.ports.users import UserRepository

PAGE_SIZE = 20


@dataclass(frozen=True, slots=True)
class UserPage:
    count: int
    page: int
    results: tuple[AccountSnapshot, ...]


@dataclass(frozen=True, slots=True)
class UserFilters:
    query: str | None = None
    role: Role | None = None
    is_active: bool | None = None


class UserQueryService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def list(self, filters: UserFilters, page: int) -> UserPage:
        records = self.users.list_users(filters.query, filters.role, filters.is_active)
        count = len(records)
        start = (page - 1) * PAGE_SIZE
        if page < 1 or (count == 0 and page != 1) or (count > 0 and start >= count):
            raise ValueError("page")
        return UserPage(count, page, tuple(records[start : start + PAGE_SIZE]))
