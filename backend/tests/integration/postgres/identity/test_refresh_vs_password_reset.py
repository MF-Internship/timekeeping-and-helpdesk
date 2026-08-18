import pytest

from identity.ports.sessions import RevocationReason
from tests.integration.postgres.identity.session_race_helpers import run_issuance_revocation_race


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_refresh_issuance_vs_password_reset() -> None:
    result = run_issuance_revocation_race(
        issuance="refresh", revocation=RevocationReason.PASSWORD_RESET
    )
    assert result["target"].must_change_password is True
