from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections, transaction

from identity.adapters.security.sessions import InvalidSessionError, SimpleJWTSessionRepository
from tests.integration.postgres.identity.session_race_helpers import (
    assert_refresh_rejected,
    make_user,
)


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_same_refresh_has_at_most_one_rotation_winner() -> None:
    account = make_user("rotation-race")
    sessions = SimpleJWTSessionRepository()
    with transaction.atomic():
        seed = sessions.issue(account.pk)
    barrier = Barrier(2)

    def rotate() -> str:
        close_old_connections()
        barrier.wait()
        try:
            with transaction.atomic():
                result = SimpleJWTSessionRepository().rotate(seed.refresh)
            return result.refresh
        except InvalidSessionError:
            return "denied"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: rotate(), range(2)))
    winners = [value for value in results if value != "denied"]
    assert len(winners) == 1
    assert_refresh_rejected(seed.refresh)
