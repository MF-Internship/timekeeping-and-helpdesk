from __future__ import annotations

from uuid import UUID

import pytest


def test_context_is_empty_then_bindable_and_resettable() -> None:
    from core.correlation import bind_correlation, get_correlation, reset_correlation

    assert get_correlation() == ("", "")
    token = bind_correlation()
    request_id, correlation_id = get_correlation()
    assert request_id == correlation_id
    parsed = UUID(request_id)
    assert parsed.version == 4
    assert str(parsed) == request_id
    reset_correlation(token)
    assert get_correlation() == ("", "")


def test_nested_context_restores_parent_even_after_exception() -> None:
    from core.correlation import bind_correlation, get_correlation, reset_correlation

    outer = bind_correlation("00000000-0000-4000-8000-000000000001")
    try:
        assert get_correlation()[0].endswith("1")
        inner = bind_correlation("00000000-0000-4000-8000-000000000002")
        try:
            assert get_correlation()[0].endswith("2")
            raise RuntimeError("controlled")
        except RuntimeError:
            pass
        finally:
            reset_correlation(inner)
        assert get_correlation()[0].endswith("1")
    finally:
        reset_correlation(outer)
    assert get_correlation() == ("", "")


@pytest.mark.parametrize("value", ["", "not-a-uuid", "00000000-0000-1000-8000-000000000000"])
def test_explicit_request_id_must_be_canonical_uuid4(value: str) -> None:
    from core.correlation import bind_correlation

    with pytest.raises(ValueError):
        bind_correlation(value)
