from __future__ import annotations

import json

import pytest
from django.http import JsonResponse
from django.test import RequestFactory, override_settings


@pytest.mark.integration
@override_settings(ORIGIN_CREDENTIAL="z" * 32, ORIGIN_CREDENTIAL_HEADER="X-Origin-Credential")
def test_missing_and_wrong_origin_credentials_are_indistinguishable() -> None:
    from core.middleware import OriginCredentialMiddleware, RequestIdentityMiddleware

    chain = RequestIdentityMiddleware(OriginCredentialMiddleware(lambda _request: JsonResponse({})))
    factory = RequestFactory()
    missing = chain(factory.get("/api/v1/probe/"))
    wrong = chain(factory.get("/api/v1/probe/", HTTP_X_ORIGIN_CREDENTIAL="wrong"))
    for response in (missing, wrong):
        assert response.status_code == 403
        body = json.loads(response.content)
        assert body["error_code"] == body["error"] == "PERMISSION_DENIED"
        assert body["details"] == {}
    assert {
        key: value for key, value in json.loads(missing.content).items() if key != "request_id"
    } == {key: value for key, value in json.loads(wrong.content).items() if key != "request_id"}


@pytest.mark.integration
@override_settings(ORIGIN_CREDENTIAL="z" * 32, ORIGIN_CREDENTIAL_HEADER="X-Origin-Credential")
def test_correct_origin_credential_reaches_endpoint() -> None:
    from core.middleware import OriginCredentialMiddleware, RequestIdentityMiddleware

    chain = RequestIdentityMiddleware(
        OriginCredentialMiddleware(lambda _request: JsonResponse({"reached": True}))
    )
    response = chain(RequestFactory().get("/api/v1/probe/", HTTP_X_ORIGIN_CREDENTIAL="z" * 32))
    assert response.status_code == 200
    assert json.loads(response.content) == {"reached": True}
