from pathlib import Path


def test_precommit_contains_only_fast_non_mutating_gates() -> None:
    source = Path(".pre-commit-config.yaml").read_text(encoding="utf-8")
    for command in (
        "ruff format --check",
        "ruff check",
        "check_function_length.py",
        "tests/architecture",
        "migration_check.py check",
        "check_contract_drift.py",
        "typecheck",
        "api:check",
        "check_feature_002_convergence.sh --fast",
    ):
        assert command in source
    forbidden = (
        "--write",
        "api:generate",
        "production-ready",
        "recovery-ready",
        "smoke",
        "capacity",
    )
    assert all(value not in source for value in forbidden)
