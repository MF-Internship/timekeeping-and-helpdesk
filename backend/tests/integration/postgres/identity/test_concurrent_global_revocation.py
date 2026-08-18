from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections, transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from audit.adapters.persistence.recording import DjangoAuditRecorder
from audit.domain.records import AuditAction, AuditEntry, IdentityEventType, OutboxRecord
from audit.models import OutboxEvent
from identity.adapters.security.sessions import SimpleJWTSessionRepository
from identity.ports.sessions import RevocationReason
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

    def revoke(worker: int) -> None:
        close_old_connections()
        barrier.wait()
        with transaction.atomic():
            count = SimpleJWTSessionRepository().revoke_all(account.pk, RevocationReason.LOGOUT)
            evidence = {"reason": "LOGOUT", "revoked_count": count, "worker": worker}
            recorder = DjangoAuditRecorder()
            recorder.append_audit_entry(
                AuditEntry(
                    account.pk,
                    AuditAction.SESSIONS_REVOKED,
                    "User",
                    str(account.pk),
                    {},
                    evidence,
                )
            )
            recorder.append_outbox_event(
                OutboxRecord(
                    IdentityEventType.SESSIONS_REVOKED,
                    "User",
                    str(account.pk),
                    evidence,
                )
            )
        close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(revoke, range(2)))
    assert OutstandingToken.objects.filter(user=account).count() == 4
    assert BlacklistedToken.objects.filter(token__user=account).count() == 4
    assert list(
        OutboxEvent.objects.filter(aggregate_id=str(account.pk))
        .order_by("aggregate_version")
        .values_list("aggregate_version", flat=True)
    ) == [1, 2]
    for session in issued:
        assert_refresh_rejected(session.refresh)
