from pathlib import Path


def test_every_external_diagnostic_gate_uses_canonical_sanitizer() -> None:
    gates = [
        "scripts/check_architecture.py",
        "scripts/check_contract_drift.py",
        "scripts/check_function_length.py",
        "scripts/check_openapi.py",
        "scripts/deployment_check.py",
        "scripts/migration_check.py",
    ]
    for gate in gates:
        source = Path(gate).read_text(encoding="utf-8")
        assert "sanitize_failure_reason" in source, gate


def test_aggregate_gate_supports_a_controlled_maintainability_fixture() -> None:
    source = Path("scripts/check_all.sh").read_text(encoding="utf-8")
    assert "CHECK_ALL_MAINTAINABILITY_PATH" in source
    assert "check_function_length.py" in source
