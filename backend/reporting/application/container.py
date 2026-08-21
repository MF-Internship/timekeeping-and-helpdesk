from __future__ import annotations

from dataclasses import dataclass

from reporting.application.queries import ReportingQueryService


@dataclass(frozen=True, slots=True)
class ReportingContainer:
    queries: ReportingQueryService
