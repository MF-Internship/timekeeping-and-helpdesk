import pytest

from identity.domain.accounts import AccountSnapshot
from identity.domain.authorization import Role


@pytest.mark.unit
def test_account_snapshot_trims_owned_text() -> None:
    account = AccountSnapshot(1, " helpdesk01 ", " Nguyễn Văn A ", None, None, Role.HELPDESK)
    assert account.username == "helpdesk01"
    assert account.full_name == "Nguyễn Văn A"


@pytest.mark.unit
@pytest.mark.parametrize("field", ["username", "full_name"])
def test_account_snapshot_rejects_blank_required_text(field: str) -> None:
    values = {"username": "user01", "full_name": "User One"}
    values[field] = "   "
    with pytest.raises(ValueError, match=field):
        AccountSnapshot(1, values["username"], values["full_name"], None, None, Role.LEADER)
