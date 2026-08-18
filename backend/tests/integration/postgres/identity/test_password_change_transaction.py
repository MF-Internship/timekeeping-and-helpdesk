import pytest
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import authenticated_client, create_user


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_password_change_commits_state_revocation_and_consecutive_evidence() -> None:
    account = create_user("password-transaction", must_change=True)
    api = authenticated_client(account)
    response = api.post(
        "/api/v1/change-password",
        {"current_password": "SafePassword123!", "new_password": "ChangedPassword456!"},
    )
    assert response.status_code == 200
    account.refresh_from_db()
    assert account.check_password("ChangedPassword456!")
    assert not account.must_change_password
    assert BlacklistedToken.objects.filter(token__user=account).exists()
    assert OutstandingToken.objects.filter(user=account, blacklistedtoken__isnull=True).count() == 1
    assert AuditLog.objects.filter(target_id=str(account.pk)).count() == 2
    assert list(
        OutboxEvent.objects.filter(aggregate_id=str(account.pk))
        .order_by("aggregate_version")
        .values_list("aggregate_version", flat=True)
    ) == [1, 2]
