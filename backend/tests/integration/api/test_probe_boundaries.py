from __future__ import annotations

import ast
from pathlib import Path

import pytest


@pytest.mark.architecture
def test_test_urls_contain_no_business_or_auth_route() -> None:
    path = Path(__file__).with_name("urls.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    routes = [
        argument.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "path"
        and node.args
        for argument in node.args[:1]
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
    ]
    assert routes == ["probe/success/", "probe/validation/", "probe/csrf/"]
    assert not any(
        term in route
        for route in routes
        for term in ("auth", "login", "location", "attendance", "task", "report", "notification")
    )


@pytest.mark.architecture
def test_probe_source_does_not_invent_framework_error_codes() -> None:
    source = Path(__file__).with_name("views.py").read_text(encoding="utf-8")
    unauthorized_codes = (
        "NOT_FOUND",
        "METHOD_NOT_ALLOWED",
        "UNSUPPORTED_MEDIA",
        "INTERNAL_ERROR",
    )
    assert not any(code in source for code in unauthorized_codes)
