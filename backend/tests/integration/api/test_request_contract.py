from __future__ import annotations

import json
from uuid import UUID

import pytest
from django.http import JsonResponse
from django.test import RequestFactory, override_settings


@pytest.mark.integration
@pytest.mark.parametrize(
    "client_value",
    [None, "00000000-0000-4000-8000-000000000001", "malformed", "x" * 4096],
)
def test_server_issues_request_id_and_ignores_client_value(client_value: str | None) -> None:
    from core.correlation import get_correlation
    from core.middleware import RequestIdentityMiddleware

    observed: list[tuple[str, str]] = []

    def endpoint(_request: object) -> JsonResponse:
        observed.append(get_correlation())
        return JsonResponse({"ok": True})

    headers = {} if client_value is None else {"HTTP_X_REQUEST_ID": client_value}
    request = RequestFactory().get("/api/v1/probe/", **headers)
    response = RequestIdentityMiddleware(endpoint)(request)
    issued = response["X-Request-Id"]
    assert UUID(issued).version == 4
    assert issued != client_value
    assert observed == [(issued, issued)]
    assert response["Cache-Control"] == "private, no-store"
    assert get_correlation() == ("", "")


@pytest.mark.integration
def test_duplicate_client_request_ids_are_ignored() -> None:
    from core.middleware import RequestIdentityMiddleware

    request = RequestFactory().get("/api/v1/probe/", HTTP_X_REQUEST_ID="one,two")
    response = RequestIdentityMiddleware(lambda _request: JsonResponse({"ok": True}))(request)
    assert response["X-Request-Id"] not in {"one", "two", "one,two"}


@pytest.mark.integration
def test_context_is_cleaned_when_endpoint_raises() -> None:
    from core.correlation import get_correlation
    from core.middleware import RequestIdentityMiddleware

    def failing_endpoint(_request: object) -> JsonResponse:
        assert get_correlation()[0]
        raise RuntimeError("controlled")

    with pytest.raises(RuntimeError, match="controlled"):
        RequestIdentityMiddleware(failing_endpoint)(RequestFactory().get("/api/v1/probe/"))
    assert get_correlation() == ("", "")


@pytest.mark.integration
@override_settings(ORIGIN_CREDENTIAL="z" * 32, ORIGIN_CREDENTIAL_HEADER="X-Origin-Credential")
def test_error_body_request_id_equals_header() -> None:
    from core.middleware import OriginCredentialMiddleware, RequestIdentityMiddleware

    chain = RequestIdentityMiddleware(OriginCredentialMiddleware(lambda _request: JsonResponse({})))
    response = chain(RequestFactory().get("/api/v1/probe/"))
    assert response.status_code == 403
    assert json.loads(response.content)["request_id"] == response["X-Request-Id"]
