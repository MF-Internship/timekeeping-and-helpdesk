from pathlib import Path

ROOT = Path(__file__).parents[4]
FEATURE = ROOT / "specs/002-identity-auth-rbac"


def test_feature_owned_artifacts_have_no_unresolved_marker_or_secret_example() -> None:
    owned = [*FEATURE.rglob("*.md"), *FEATURE.rglob("*.yaml")]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in owned)
    assert "UNRESOLVED" not in combined
    assert "Bearer ey" not in combined
    assert "postgresql://" not in combined


def test_identity_runtime_has_no_future_module_or_outbox_relay_behavior() -> None:
    sources = [
        *(ROOT / "backend/identity").rglob("*.py"),
        *(ROOT / "backend/audit").rglob("*.py"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in sources)
    for forbidden in (
        "attendance.models",
        "task.models",
        "reporting.models",
        "publish_outbox",
        "celery",
        "kafka",
    ):
        assert forbidden not in combined.casefold()


def test_dependency_manifests_add_only_the_approved_auth_library() -> None:
    backend = (ROOT / "backend/pyproject.toml").read_text(encoding="utf-8")
    frontend = (ROOT / "frontend/package.json").read_text(encoding="utf-8")
    assert '"djangorestframework-simplejwt==5.5.1"' in backend
    for forbidden in ("axios", "redux", "zustand", "celery", "kafka"):
        assert forbidden not in backend.casefold()
        assert forbidden not in frontend.casefold()
