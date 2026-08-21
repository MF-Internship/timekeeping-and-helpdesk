from __future__ import annotations

from typing import Protocol

from identity.domain.accounts import AccountSnapshot, NewAccount
from identity.domain.authorization import Role


class UserRepository(Protocol):
    def get(self, user_id: int) -> AccountSnapshot | None: ...

    def get_by_username(self, username: str) -> AccountSnapshot | None: ...

    def get_for_update(self, user_id: int) -> AccountSnapshot | None: ...

    def get_by_username_for_update(self, username: str) -> AccountSnapshot | None: ...

    def password_hash(self, user_id: int) -> str: ...

    def record_login(self, user_id: int) -> None: ...

    def paginate_users(
        self,
        query: str | None,
        role: Role | None,
        is_active: bool | None,
        window: tuple[int, int],
    ) -> tuple[int, list[AccountSnapshot]]: ...


class MutableUserRepository(UserRepository, Protocol):
    def save(self, account: AccountSnapshot) -> AccountSnapshot: ...

    def create(self, account: NewAccount) -> AccountSnapshot: ...

    def set_password(
        self, user_id: int, password_hash: str, *, must_change: bool
    ) -> AccountSnapshot: ...
