from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from django.db import close_old_connections

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from locations.models import Location
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.locations.helpers import create_config

ROOT = Path(__file__).parents[5]


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_competing_seeds_serialize_on_config_and_second_is_noop() -> None:
    create_config()
    actor = create_user("seed-race-manager", "MANAGER")
    barrier = Barrier(2)
    paths = (ROOT / "docs/dia_chi_ttkd.csv", ROOT / "docs/dia_chi_cua_hang.csv")

    def seed(_: int) -> int:
        close_old_connections()
        barrier.wait()
        changed, _total, _warnings = locations_container().seed.seed(actor.pk, *paths)
        close_old_connections()
        return changed

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(seed, range(2))) == [0, 76]
    assert Location.objects.count() == 76
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 76
