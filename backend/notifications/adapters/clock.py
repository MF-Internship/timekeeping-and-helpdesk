from datetime import datetime

from django.utils import timezone


class DjangoClock:
    def now(self) -> datetime:
        return timezone.now()
