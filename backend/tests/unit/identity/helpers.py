from __future__ import annotations

from unittest.mock import Mock

from identity.application.dependencies import IdentityDependencies
from identity.domain.accounts import AccountSnapshot
from identity.domain.authorization import Role


class NoopUnitOfWork:
    def __enter__(self) -> NoopUnitOfWork:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def account(
    *,
    user_id: int = 7,
    role: Role = Role.HELPDESK,
    active: bool = True,
    must_change: bool = False,
) -> AccountSnapshot:
    return AccountSnapshot(
        id=user_id,
        username="worker",
        full_name="Worker",
        phone=None,
        email=None,
        role=role,
        is_active=active,
        must_change_password=must_change,
    )


def dependency_mocks() -> tuple[IdentityDependencies, Mock, Mock, Mock, Mock]:
    users = Mock()
    passwords = Mock()
    sessions = Mock()
    audit = Mock()
    dependencies = IdentityDependencies(users, passwords, sessions, NoopUnitOfWork, audit)
    return dependencies, users, passwords, sessions, audit
