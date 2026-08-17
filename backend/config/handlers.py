from __future__ import annotations

from django.http import HttpRequest, JsonResponse

from core.correlation import get_request_id
from core.error_codes import PERMISSION_DENIED
from core.errors import build_error_envelope


def csrf_failure(request: HttpRequest, reason: str = "") -> JsonResponse:
    del request, reason
    return JsonResponse(
        build_error_envelope(PERMISSION_DENIED, get_request_id()),
        status=403,
    )
