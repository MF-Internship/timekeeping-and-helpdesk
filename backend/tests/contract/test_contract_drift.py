from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures/drift"


def test_conforming_artifacts_pass_without_mutation() -> None:
    from scripts.check_contract_drift import check_artifacts

    openapi = Path("contracts/openapi.yaml")
    schema = Path("frontend/src/shared/api/schema.ts")
    before = (openapi.read_bytes(), schema.read_bytes())
    assert check_artifacts(openapi, schema) == []
    assert (openapi.read_bytes(), schema.read_bytes()) == before


def test_stale_backend_and_client_paths_are_reported_without_mutation() -> None:
    from scripts.check_contract_drift import check_artifacts

    openapi = FIXTURES / "openapi-stale.yaml"
    schema = FIXTURES / "schema-stale.ts"
    before = (openapi.read_bytes(), schema.read_bytes())
    findings = check_artifacts(openapi, schema)
    assert {finding.rule for finding in findings} == {"DRIFT-OPENAPI", "DRIFT-CLIENT"}
    assert (openapi.read_bytes(), schema.read_bytes()) == before
