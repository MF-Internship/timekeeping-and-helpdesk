from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class HolidaySnapshot:
    id: int
    date: date
    name: str
