from __future__ import annotations

import ast
import json
from pathlib import Path

from django.test import RequestFactory
from rest_framework.exceptions import ValidationError


def test_runtime_defines_no_unauthorized_framework_error_code() -> None:
    backend = Path(__file__).parents[3]
    forbidden = {"METHOD_NOT_ALLOWED", "UNSUPPORTED_MEDIA_TYPE", "INTERNAL_ERROR"}
    found: set[str] = set()
    for path in [*backend.joinpath("core").glob("*.py"), *backend.joinpath("config").glob("*.py")]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found.update(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and node.value in forbidden
        )
    assert not found


def test_validation_and_csrf_adapters_use_the_single_envelope() -> None:
    from config.handlers import csrf_failure
    from core.correlation import bind_correlation, reset_correlation
    from core.errors import drf_exception_handler

    token = bind_correlation("00000000-0000-4000-8000-000000000009")
    try:
        validation = drf_exception_handler(
            ValidationError({"field_name": ["Giá trị không hợp lệ."]}), {}
        )
        csrf = csrf_failure(RequestFactory().post("/api/v1/probe/"))
    finally:
        reset_correlation(token)
    assert validation is not None
    assert validation.data["error_code"] == "VALIDATION_FAILED"
    assert validation.data["field_name"] == validation.data["details"]["field_name"]
    assert json.loads(csrf.content)["error_code"] == "PERMISSION_DENIED"
