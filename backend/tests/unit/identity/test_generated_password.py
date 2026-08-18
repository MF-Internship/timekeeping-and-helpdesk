from identity.application.dto import GeneratedPasswordDisplayResult, UserCreateRequest
from identity.application.user_admin import UserAdminService
from identity.domain.authorization import Role
from tests.unit.identity.helpers import account, dependency_mocks


def test_generated_password_result_never_exposes_plaintext_in_repr() -> None:
    value = GeneratedPasswordDisplayResult(account=account(), generated_password="SecretValue123!")
    assert "SecretValue123!" not in repr(value)


def test_create_returns_plaintext_only_in_response_scoped_result() -> None:
    dependencies, users, passwords, _sessions, audit = dependency_mocks()
    users.create.return_value = account()
    passwords.generate.return_value = "GeneratedValue123!"
    passwords.encode.return_value = "encoded"
    result = UserAdminService(dependencies).create(
        1, UserCreateRequest("worker", "Worker", Role.HELPDESK)
    )
    assert result.generated_password == "GeneratedValue123!"
    assert "GeneratedValue123!" not in repr(users.create.call_args)
    assert "GeneratedValue123!" not in repr(audit.mock_calls)
