from __future__ import annotations

from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
def success_probe(_request: Request) -> Response:
    return Response({"status": "ok"})


@api_view(["POST"])
def validation_probe(_request: Request) -> Response:
    raise ValidationError({"field_name": ["Giá trị không hợp lệ."]})


@api_view(["POST"])
def csrf_probe(_request: Request) -> Response:
    return Response({"status": "csrf_checked"})
