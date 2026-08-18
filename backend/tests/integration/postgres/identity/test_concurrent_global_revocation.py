from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections, transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from audit.adapters.persistence.recording import DjangoAuditRecorder
from audit.models import AuditLog, OutboxEvent
from identity.adapters.persistence.unit_of_work import DjangoUnitOfWork
from identity.adapters.persistence.users import DjangoUserRepository
from identity.adapters.security.passwords import DjangoPasswordService
from identity.adapters.security.sessions import SimpleJWTSessionRepository
from identity.application.authentication import AuthenticationService
from identity.application.dependencies import IdentityDependencies
from tests.integration.postgres.identity.session_race_helpers import (
    assert_refresh_rejected,
    make_user,
)


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_concurrent_global_revocations_serialize_for_one_user() -> None:
    account = make_user("global-revoke")
    sessions = SimpleJWTSessionRepository()
    with transaction.atomic():
        issued = [sessions.issue(account.pk) for _ in range(4)]
    barrier = Barrier(2)

    class BarrierUserRepository:
        def __init__(self) -> None:
            self.delegate = DjangoUserRepository()

        def get_for_update(self, user_id: int):
            barrier.wait()
            return self.delegate.get_for_update(user_id)

        def __getattr__(self, name: str):
            return getattr(self.delegate, name)

    def revoke(_worker: int) -> None:
        close_old_connections()
        try:
            dependencies = IdentityDependencies(
                BarrierUserRepository(),
                DjangoPasswordService(),
                SimpleJWTSessionRepository(),
                DjangoUnitOfWork,
                DjangoAuditRecorder(),
            )
            AuthenticationService(dependencies).logout(account.pk)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(revoke, range(2)))
    assert OutstandingToken.objects.filter(user=account).count() == 4
    assert BlacklistedToken.objects.filter(token__user=account).count() == 4
    assert AuditLog.objects.filter(target_id=str(account.pk)).count() == 1
    assert list(
        OutboxEvent.objects.filter(aggregate_id=str(account.pk))
        .order_by("aggregate_version")
        .values_list("aggregate_version", flat=True)
    ) == [1]
    for session in issued:
        assert_refresh_rejected(session.refresh)
