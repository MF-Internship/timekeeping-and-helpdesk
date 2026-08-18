import pytest

from identity.domain.passwords import password_rule_errors


@pytest.mark.unit
def test_password_rules_accept_compliant_value() -> None:
    assert password_rule_errors("helpdesk01", "A-long-passphrase-42") == ()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("password", "error"),
    [("short", "minimum_length"), ("helpdesk01", "different_from_username")],
)
def test_password_rules_reject_canonical_boundaries(password: str, error: str) -> None:
    assert error in password_rule_errors("helpdesk01", password)
