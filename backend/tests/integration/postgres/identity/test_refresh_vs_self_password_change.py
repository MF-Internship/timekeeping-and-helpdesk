import pytest

from identity.ports.sessions import RevocationReason
from tests.integration.postgres.identity.session_race_helpers import run_issuance_revocation_race


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_refresh_issuance_vs_self_password_change() -> None:
    result = run_issuance_revocation_race(
        issuance="refresh", revocation=RevocationReason.PASSWORD_CHANGE
    )
    assert result["replacement"].access
