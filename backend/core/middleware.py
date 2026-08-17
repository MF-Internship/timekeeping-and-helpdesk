from __future__ import annotations

import secrets
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

from core.correlation import bind_correlation, get_request_id, reset_correlation
from core.error_codes import PERMISSION_DENIED
from core.errors import build_error_envelope

ResponseHandler = Callable[[HttpRequest], HttpResponse]


class RequestIdentityMiddleware:
    def __init__(self, get_response: ResponseHandler) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        token = bind_correlation()
        request_id = get_request_id()
        try:
            response = self.get_response(request)
            response["X-Request-Id"] = request_id
            if request.path.startswith("/api/v1/"):
                response["Cache-Control"] = "private, no-store"
            return response
        finally:
            reset_correlation(token)


class OriginCredentialMiddleware:
    def __init__(self, get_response: ResponseHandler) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not request.path.startswith("/api/v1/"):
            return self.get_response(request)
        expected = str(settings.ORIGIN_CREDENTIAL)
        supplied = request.headers.get(str(settings.ORIGIN_CREDENTIAL_HEADER), "")
        if not secrets.compare_digest(supplied, expected):
            return JsonResponse(
                build_error_envelope(PERMISSION_DENIED, get_request_id()),
                status=403,
            )
        return self.get_response(request)


def set_response_contract(response: Any, request_id: str) -> Any:
    response["X-Request-Id"] = request_id
    response["Cache-Control"] = "private, no-store"
    return response
