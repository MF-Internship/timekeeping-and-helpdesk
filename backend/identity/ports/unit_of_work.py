from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self


class UnitOfWork(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...
