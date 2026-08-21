from __future__ import annotations

from dataclasses import dataclass

from identity.domain.accounts import AccountSnapshot, UserFilters
from identity.ports.users import UserRepository

PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class UserPage:
    count: int
    offset: int
    limit: int
    results: tuple[AccountSnapshot, ...]


class UserQueryService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def list(self, filters: UserFilters, offset: int = 0, limit: int = PAGE_SIZE) -> UserPage:
        if offset < 0 or limit < 1 or limit > MAX_PAGE_SIZE:
            raise ValueError("pagination")
        count, records = self.users.paginate_users(filters, (offset, limit))
        if count > 0 and offset >= count:
            raise ValueError("pagination")
        return UserPage(count, offset, limit, tuple(records))
