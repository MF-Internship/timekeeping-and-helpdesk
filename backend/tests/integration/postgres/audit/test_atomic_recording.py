from __future__ import annotations

import pytest
from django.db import transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from audit.adapters.persistence.recording import DjangoAuditRecorder
from audit.domain.records import AuditAction, AuditEntry, IdentityEventType, OutboxRecord
from audit.models import AuditLog, OutboxEvent
from core.event_payload import ProtectedPayloadError
from identity.adapters.security.sessions import SimpleJWTSessionRepository
from identity.models import User
from identity.ports.sessions import RevocationReason


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_later_exception_rolls_back_user_blacklist_audit_and_outbox() -> None:
    account = User.objects.create_user(
        username="rollback", password="SafePassword123!", full_name="Before", role="HELPDESK"
    )
    with transaction.atomic():
        SimpleJWTSessionRepository().issue(account.pk)
    with pytest.raises(RuntimeError, match="rollback"), transaction.atomic():
        account.full_name = "After"
        account.save(update_fields=["full_name"])
        SimpleJWTSessionRepository().revoke_all(account.pk, RevocationReason.PASSWORD_RESET)
        recorder = DjangoAuditRecorder()
        recorder.append_audit_entry(
            AuditEntry(
                account.pk,
                AuditAction.USER_PROFILE_UPDATED,
                "User",
                str(account.pk),
                {},
                {"full_name": "After"},
            )
        )
        recorder.append_outbox_event(
            OutboxRecord(
                IdentityEventType.USER_PROFILE_UPDATED,
                "User",
                str(account.pk),
                {"full_name": "After"},
            )
        )
        raise RuntimeError("rollback")
    account.refresh_from_db()
    assert account.full_name == "Before"
    assert BlacklistedToken.objects.count() == 0
    assert AuditLog.objects.count() == 0
    assert OutboxEvent.objects.count() == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_protected_payload_failure_rolls_back_the_caller_transaction() -> None:
    account = User.objects.create_user(
        username="payload-rollback",
        password="SafePassword123!",
        full_name="Before",
        role="HELPDESK",
    )

    with pytest.raises(ProtectedPayloadError), transaction.atomic():
        account.full_name = "After"
        account.save(update_fields=["full_name"])
        DjangoAuditRecorder().append_outbox_event(
            OutboxRecord(
                IdentityEventType.USER_PROFILE_UPDATED,
                "User",
                str(account.pk),
                {"diagnostic": "private://credential"},
            )
        )

    account.refresh_from_db()
    assert account.full_name == "Before"
    assert AuditLog.objects.count() == 0
    assert OutboxEvent.objects.count() == 0
