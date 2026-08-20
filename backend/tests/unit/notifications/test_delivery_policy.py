from datetime import datetime, timedelta

from notifications.domain.delivery import (
    LOCAL_ZONE,
    expires_at,
    is_quiet_hour,
    next_delivery_time,
    remaining_ttl_seconds,
    retry_at,
)


def test_quiet_interval_is_half_open_and_releases_at_seven() -> None:
    at_2059 = datetime(2026, 8, 21, 20, 59, tzinfo=LOCAL_ZONE)
    at_2100 = datetime(2026, 8, 21, 21, 0, tzinfo=LOCAL_ZONE)
    at_0659 = datetime(2026, 8, 22, 6, 59, tzinfo=LOCAL_ZONE)
    at_0700 = datetime(2026, 8, 22, 7, 0, tzinfo=LOCAL_ZONE)
    assert not is_quiet_hour(at_2059)
    assert is_quiet_hour(at_2100)
    assert is_quiet_hour(at_0659)
    assert not is_quiet_hour(at_0700)
    assert next_delivery_time(at_2100) == at_0700
    assert next_delivery_time(at_0659) == at_0700


def test_ttl_equality_is_expired_and_retry_never_exceeds_it() -> None:
    occurred = datetime(2026, 8, 21, 12, 0, tzinfo=LOCAL_ZONE)
    expiry = expires_at(occurred)
    assert expiry == occurred + timedelta(hours=24)
    assert remaining_ttl_seconds(expiry, expiry) == 0
    assert retry_at(expiry - timedelta(seconds=1), 20, expiry) == expiry
