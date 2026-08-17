from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from django.http import JsonResponse
from django.test import RequestFactory


def test_concurrent_success_and_error_responses_have_distinct_ids_and_cleanup() -> None:
    from core.correlation import get_correlation
    from core.middleware import RequestIdentityMiddleware

    def request(index: int) -> str:
        def endpoint(_request: object) -> JsonResponse:
            request_id, correlation_id = get_correlation()
            assert request_id == correlation_id
            return JsonResponse({"index": index})

        response = RequestIdentityMiddleware(endpoint)(RequestFactory().get("/api/v1/probe/"))
        assert get_correlation() == ("", "")
        return str(response["X-Request-Id"])

    with ThreadPoolExecutor(max_workers=20) as executor:
        request_ids = list(executor.map(request, range(100)))
    assert len(set(request_ids)) == 100
    assert get_correlation() == ("", "")


def test_safe_sink_failure_does_not_change_response() -> None:
    import logging

    from core.logging import emit_safe_failure
    from core.middleware import RequestIdentityMiddleware
    from tests.unit.core.test_logging import FailingHandler

    logger = logging.Logger("forced-sink")
    logger.addHandler(FailingHandler())

    def endpoint(_request: object) -> JsonResponse:
        assert not emit_safe_failure(logger, "controlled", rule="RULE", path="path")
        return JsonResponse({"ok": True})

    response = RequestIdentityMiddleware(endpoint)(RequestFactory().get("/api/v1/probe/"))
    assert response.status_code == 200
