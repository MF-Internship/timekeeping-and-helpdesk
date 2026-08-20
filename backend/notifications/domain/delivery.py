from __future__ import annotations

from datetime import datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

LOCAL_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")
QUIET_START = time(21, 0)
QUIET_END = time(7, 0)
PUSH_TTL = timedelta(hours=24)
LEASE_DURATION = timedelta(minutes=2)


class PushDeliveryState(StrEnum):
    PENDING = "PENDING"
    LEASED = "LEASED"
    DELIVERED = "DELIVERED"
    SUPPRESSED = "SUPPRESSED"
    EXPIRED = "EXPIRED"


class PushFailureCode(StrEnum):
    TRANSIENT_PROVIDER_FAILURE = "TRANSIENT_PROVIDER_FAILURE"
    SUBSCRIPTION_GONE = "SUBSCRIPTION_GONE"
    ORIGIN_REJECTED = "ORIGIN_REJECTED"
    CONFIGURATION_UNAVAILABLE = "CONFIGURATION_UNAVAILABLE"
    TRANSPORT_TIMEOUT = "TRANSPORT_TIMEOUT"


def is_quiet_hour(moment: datetime) -> bool:
    local_time = moment.astimezone(LOCAL_ZONE).time().replace(tzinfo=None)
    return local_time >= QUIET_START or local_time < QUIET_END


def next_delivery_time(moment: datetime) -> datetime:
    local = moment.astimezone(LOCAL_ZONE)
    if not is_quiet_hour(moment):
        return moment
    release_date = local.date() + timedelta(days=1) if local.time() >= QUIET_START else local.date()
    return datetime.combine(release_date, QUIET_END, LOCAL_ZONE)


def expires_at(occurred_at: datetime) -> datetime:
    return occurred_at + PUSH_TTL


def remaining_ttl_seconds(now: datetime, expiry: datetime) -> int:
    return max(0, int((expiry - now).total_seconds()))


def retry_at(now: datetime, attempt_count: int, expiry: datetime) -> datetime:
    delay_seconds = min(60 * (2 ** max(0, attempt_count - 1)), 3600)
    return min(now + timedelta(seconds=delay_seconds), expiry)


def lease_expiry(now: datetime) -> datetime:
    return now + LEASE_DURATION
