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
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        self._atomic.__exit__(exception_type, exception, traceback)
        return None
