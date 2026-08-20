from __future__ import annotations

from typing import Any, ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

from identity.domain.authorization import Role


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(self, username: str, password: str | None = None, **fields: Any) -> User:
        if not username.strip():
            raise ValueError("username must not be blank")
        user = self.model(username=username.strip(), **fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    username: models.CharField[str, str] = models.CharField(max_length=150, unique=True)
    full_name: models.CharField[str, str] = models.CharField(max_length=255)
    phone: models.CharField[str | None, str | None] = models.CharField(
        max_length=32, null=True, blank=True
    )
    email: models.EmailField[str | None, str | None] = models.EmailField(null=True, blank=True)
    role: models.CharField[str, str] = models.CharField(
        max_length=16, choices=[(role.value, role.value) for role in Role]
    )
    is_active: models.BooleanField[bool, bool] = models.BooleanField(default=True, db_default=True)
    must_change_password: models.BooleanField[bool, bool] = models.BooleanField(
        default=True, db_default=True
    )
    created_at: models.DateTimeField[Any, Any] = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "username"

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=~models.Q(username__regex=r"^\s*$"),
                name="identity_user_username_nonblank",
            ),
            models.CheckConstraint(
                condition=~models.Q(full_name__regex=r"^\s*$"),
                name="identity_user_full_name_nonblank",
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=[role.value for role in Role]),
                name="identity_user_role_valid",
            ),
        ]

    def __str__(self) -> str:
        return self.username
