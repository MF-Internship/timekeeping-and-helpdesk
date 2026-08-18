import pytest

from identity.ports.sessions import RevocationReason
from tests.integration.postgres.identity.session_race_helpers import (
    run_revocation_issuance_race,
)


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.parametrize("issuance", ["login", "refresh"])
@pytest.mark.parametrize(
    "revocation",
    [
        RevocationReason.LOGOUT,
        RevocationReason.PASSWORD_RESET,
        RevocationReason.PASSWORD_CHANGE,
        RevocationReason.ACCOUNT_DEACTIVATED,
    ],
)
def test_revocation_or_mutation_first_serializes_later_issuance(
    issuance: str, revocation: RevocationReason
) -> None:
    result = run_revocation_issuance_race(issuance=issuance, revocation=revocation)
    assert result["target"].pk > 0
