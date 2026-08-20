from __future__ import annotations

from types import TracebackType

from django.db import transaction


class DjangoUnitOfWork:
    def __init__(self) -> None:
        self._atomic = transaction.atomic()

    def __enter__(self) -> DjangoUnitOfWork:
        self._atomic.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._atomic.__exit__(exc_type, exc_value, traceback)
