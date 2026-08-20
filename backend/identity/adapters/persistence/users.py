from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from identity.domain.accounts import AccountSnapshot, NewAccount
from identity.domain.authorization import Role
from identity.models import User


def to_snapshot(user: User) -> AccountSnapshot:
    return AccountSnapshot(
        id=user.pk,
        username=user.username,
        full_name=user.full_name,
        phone=user.phone,
        email=user.email,
        role=Role(user.role),
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        last_login=user.last_login,
        created_at=user.created_at,
    )


class DjangoUserRepository:
    def get(self, user_id: int) -> AccountSnapshot | None:
        user = User.objects.filter(pk=user_id).first()
        return None if user is None else to_snapshot(user)

    def get_by_username(self, username: str) -> AccountSnapshot | None:
        user = User.objects.filter(username=username).first()
        return None if user is None else to_snapshot(user)

    def get_for_update(self, user_id: int) -> AccountSnapshot | None:
        user = User.objects.select_for_update().filter(pk=user_id).first()
        return None if user is None else to_snapshot(user)

    def get_by_username_for_update(self, username: str) -> AccountSnapshot | None:
        user = User.objects.select_for_update().filter(username=username).first()
        return None if user is None else to_snapshot(user)

    def password_hash(self, user_id: int) -> str:
        return str(User.objects.only("password").get(pk=user_id).password)

    def record_login(self, user_id: int) -> None:
        User.objects.filter(pk=user_id).update(last_login=timezone.now())

    def list_users(
        self, query: str | None, role: Role | None, is_active: bool | None
    ) -> list[AccountSnapshot]:
        users = User.objects.all()
        if query:
            users = users.filter(Q(full_name__icontains=query) | Q(username__icontains=query))
        if role is not None:
            users = users.filter(role=role.value)
        if is_active is not None:
            users = users.filter(is_active=is_active)
        return [to_snapshot(user) for user in users.order_by("full_name", "username", "id")]

    def save(self, account: AccountSnapshot) -> AccountSnapshot:
        user = User.objects.get(pk=account.id)
        user.full_name = account.full_name
        user.phone = account.phone
        user.email = account.email
        user.role = account.role.value
        user.is_active = account.is_active
        user.must_change_password = account.must_change_password
        user.save(
            update_fields=[
                "full_name",
                "phone",
                "email",
                "role",
                "is_active",
                "must_change_password",
            ]
        )
        return to_snapshot(user)

    def create(self, account: NewAccount) -> AccountSnapshot:
        user = User.objects.create(
            username=account.username,
            full_name=account.full_name,
            phone=account.phone,
            email=account.email,
            role=account.role.value,
            password=account.password_hash,
            is_active=True,
            must_change_password=True,
        )
        return to_snapshot(user)

    def set_password(
        self, user_id: int, password_hash: str, *, must_change: bool
    ) -> AccountSnapshot:
        user = User.objects.get(pk=user_id)
        user.password = password_hash
        user.must_change_password = must_change
        user.save(update_fields=["password", "must_change_password"])
        return to_snapshot(user)
