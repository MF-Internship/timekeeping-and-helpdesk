from __future__ import annotations

import secrets
import string

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from identity.domain.passwords import password_rule_errors

_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*"


class DjangoPasswordService:
    def verify(self, encoded: str, raw: str) -> bool:
        return check_password(raw, encoded)

    def encode(self, raw: str) -> str:
        return make_password(raw)

    def validate(self, username: str, raw: str) -> None:
        errors = password_rule_errors(username, raw)
        if errors:
            raise ValueError(",".join(errors))
        validate_password(raw)

    def generate(self, username: str) -> str:
        for _ in range(128):
            candidate = "".join(secrets.choice(_ALPHABET) for _ in range(20))
            try:
                self.validate(username, candidate)
            except (ValueError, ValidationError):
                continue
            return candidate
        raise RuntimeError("unable to generate a compliant password")
