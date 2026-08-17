from pathlib import Path
from urllib.parse import urlparse

import yaml


def test_quality_workflow_contains_each_required_job_once() -> None:
    source = Path(".github/workflows/quality.yml").read_text(encoding="utf-8")
    assert source.count("  backend-quality:") == 1
    assert source.count("  frontend-quality:") == 1
    for command in ("--locked", "ruff format --check", "ruff check", "mypy", "pytest"):
        assert command in source
    for command in ("format:check", "lint", "typecheck", "test", "build"):
        assert f"frontend run {command}" in source


def test_contract_workflow_contains_only_approved_ci_gates() -> None:
    source = Path(".github/workflows/contract.yml").read_text(encoding="utf-8")
    required = (
        "postgres:17",
        "integration/api",
        "integration/postgres",
        "generate_openapi.py --check",
        "check_openapi.py --all",
        "api:check",
        "check_contract_drift.py",
        "check_openapi_compatibility.sh",
        "migration_check.py check",
        "test_cache_migration.py",
        "deployment_check.py isolation",
    )
    assert all(value in source for value in required)
    forbidden = ("production-ready", "recovery-ready", "smoke", "capacity")
    assert all(value not in source for value in forbidden)


def test_contract_workflow_postgresql_service_matches_test_dsn() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/contract.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["contract-integration"]
    service_environment = job["services"]["postgres"]["env"]
    test_dsn = urlparse(job["env"]["POSTGRES_TEST_DATABASE_URL"])
    assert test_dsn.scheme == "postgresql"
    assert test_dsn.hostname == "127.0.0.1"
    assert test_dsn.port == 5432
    assert test_dsn.username == service_environment["POSTGRES_USER"]
    assert test_dsn.password == service_environment["POSTGRES_PASSWORD"]
    assert test_dsn.path.removeprefix("/") == service_environment["POSTGRES_DB"]
