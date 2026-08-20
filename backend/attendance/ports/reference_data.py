from decimal import Decimal
from typing import Protocol

from attendance.application.dto import ReferenceSnapshot
from attendance.domain.attendance import LocationSnapshot


class ReferenceData(Protocol):
    def load_locked(self) -> ReferenceSnapshot: ...
    def distance_m(
        self, latitude: Decimal, longitude: Decimal, location: LocationSnapshot
    ) -> Decimal: ...
