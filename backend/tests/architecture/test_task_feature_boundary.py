from __future__ import annotations

import ast
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).parents[2]
TASK_ROOT = BACKEND_ROOT / "tasks"
TASK_URLS = TASK_ROOT / "adapters" / "api" / "urls.py"
TASK_ADAPTERS = BACKEND_ROOT / "config" / "task_adapters.py"

REQUIRED_MODELS = {"EvidenceUpload", "TaskPhoto", "CompletionIdempotency"}
REQUIRED_ROUTE_TERMS = {"complete-field", "evidence-uploads", "photos"}
FORBIDDEN_OUTBOX_NAMES = {
    "OutboxEvent",
    "append_event",
    "outbox",
    "record_event",
}
FORBIDDEN_TELEMETRY_NAMES = {
    "capture_exception",
    "capture_message",
    "record_exception",
    "set_attribute",
    "set_tag",
}
FORBIDDEN_EVIDENCE_AUDIT_TERMS = {
    "accuracy_m",
    "captured_at",
    "completion_note",
    "image",
    "latitude",
    "location_candidates",
    "longitude",
    "maps_url",
    "note",
    "object_key",
    "photo",
    "presigned",
    "upload",
    "url",
}


def _python_sources(root: Path) -> tuple[Path, ...]:
    return tuple(
        path
        for path in root.rglob("*.py")
        if "migrations" not in path.parts and "__pycache__" not in path.parts
    )


def _names_and_attributes(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.id if isinstance(node, ast.Name) else node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Name | ast.Attribute)
    }


def _route_literals(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    routes: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        function = node.func
        name = function.id if isinstance(function, ast.Name) else ""
        route = node.args[0]
        if name == "path" and isinstance(route, ast.Constant) and isinstance(route.value, str):
            routes.append(route.value)
    return tuple(routes)


@pytest.mark.architecture
def test_task_models_contain_governed_photo_gps_and_evidence_shape() -> None:
    from django.apps import apps

    assert TASK_ROOT.is_dir(), "Feature 007 tasks package is missing"
    task_models = tuple(apps.get_app_config("tasks").get_models())
    assert task_models, "Feature 007 must expose its approved core models"

    assert {model.__name__ for model in task_models} >= REQUIRED_MODELS
    task_update = next(model for model in task_models if model.__name__ == "TaskUpdate")
    fields = {field.name for field in task_update._meta.get_fields()}
    assert {"captured_latitude", "captured_longitude", "accuracy_m", "gps_quality"} <= fields


@pytest.mark.architecture
def test_task_routes_expose_governed_completion_surface() -> None:
    assert TASK_URLS.is_file(), "Feature 007 task URL composition is missing"
    routes = _route_literals(TASK_URLS)
    assert all(any(term in route for route in routes) for term in REQUIRED_ROUTE_TERMS)


@pytest.mark.architecture
def test_task_runtime_has_no_outbox_writer() -> None:
    paths = (*_python_sources(TASK_ROOT), TASK_ADAPTERS)
    missing = [str(path) for path in paths if not path.is_file()]
    assert not missing, f"Feature 007 runtime source is missing: {missing}"

    violations = {
        f"{path.relative_to(BACKEND_ROOT)}:{name}"
        for path in paths
        for name in _names_and_attributes(path)
        if name in FORBIDDEN_OUTBOX_NAMES
    }
    assert not violations


@pytest.mark.architecture
def test_task_runtime_has_no_sensitive_telemetry_writer() -> None:
    violations = {
        f"{path.relative_to(BACKEND_ROOT)}:{name}"
        for path in _python_sources(TASK_ROOT)
        for name in _names_and_attributes(path)
        if name in FORBIDDEN_TELEMETRY_NAMES
    }
    assert not violations


@pytest.mark.architecture
def test_task_completion_audit_helpers_cannot_name_evidence_payload_fields() -> None:
    violations: set[str] = set()
    for relative in ("application/commands.py", "application/evidence.py"):
        path = TASK_ROOT / relative
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for function in (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and "audit" in node.name
        ):
            literals = {
                str(node.value).casefold()
                for node in ast.walk(function)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            }
            for term in FORBIDDEN_EVIDENCE_AUDIT_TERMS:
                if term in literals:
                    violations.add(f"{relative}:{function.name}:{term}")
    assert not violations
