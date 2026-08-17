from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import UUID, uuid4

_request_id: ContextVar[str] = ContextVar("request_id", default="")
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


@dataclass(frozen=True, slots=True)
class CorrelationToken:
    request_id: Token[str]
    correlation_id: Token[str]


def bind_correlation(
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> CorrelationToken:
    canonical_request_id = str(uuid4()) if request_id is None else _validate_uuid4(request_id)
    canonical_correlation_id = (
        canonical_request_id if correlation_id is None else _validate_uuid4(correlation_id)
    )
    return CorrelationToken(
        request_id=_request_id.set(canonical_request_id),
        correlation_id=_correlation_id.set(canonical_correlation_id),
    )


def get_correlation() -> tuple[str, str]:
    return _request_id.get(), _correlation_id.get()


def get_request_id() -> str:
    return _request_id.get()


def get_correlation_id() -> str:
    return _correlation_id.get()


def reset_correlation(token: CorrelationToken) -> None:
    _correlation_id.reset(token.correlation_id)
    _request_id.reset(token.request_id)


def _validate_uuid4(value: str) -> str:
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise ValueError("request identity must be a canonical UUIDv4") from error
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("request identity must be a canonical UUIDv4")
    return value
