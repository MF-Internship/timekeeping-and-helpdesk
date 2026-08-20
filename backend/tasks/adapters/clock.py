from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.utils import timezone

BUSINESS_TIME_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")


class DjangoClock:
    def now(self) -> datetime:
        return timezone.now()

    def business_date(self) -> date:
        return timezone.localdate(self.now(), BUSINESS_TIME_ZONE)
