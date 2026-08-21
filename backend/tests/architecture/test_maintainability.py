from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures/maintainability"
ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("name", "rule"),
    [
        ("long_function.py", "MAINT-FUNCTION-LENGTH"),
        ("too_many_parameters.py", "MAINT-PARAMETERS"),
        ("deep_nesting.py", "MAINT-NESTING"),
        ("complex_function.py", "MAINT-COMPLEXITY"),
        ("badName.py", "MAINT-NAMING"),
    ],
)
def test_unsafe_python_fixture_has_one_expected_finding(name: str, rule: str) -> None:
    from scripts.check_function_length import check_paths

    findings = check_paths([FIXTURES / name])
    assert [finding.rule for finding in findings] == [rule]
    assert findings[0].path.endswith(name)


def test_safe_fixture_passes() -> None:
    from scripts.check_function_length import check_paths

    assert check_paths([FIXTURES / "safe.py"]) == []


@pytest.mark.parametrize(
    "path",
    [
        Path("contracts/openapi.yml"),
        Path("contracts/openapi.yaml.bak"),
        Path("frontend/src/shared/api/schema.tsx"),
        Path("frontend/src/shared/api/client.ts"),
        Path("frontend/src/shared/errors/api-error.ts"),
    ],
)
def test_nearby_authored_paths_are_not_generated_exclusions(path: Path) -> None:
    from scripts.check_function_length import is_generated_exclusion

    assert not is_generated_exclusion(path)


def test_generated_exclusions_are_exact() -> None:
    from scripts.check_function_length import is_generated_exclusion

    assert is_generated_exclusion(Path("contracts/openapi.yaml"))
    assert is_generated_exclusion(Path("frontend/src/shared/api/schema.ts"))


def test_thin_client_business_logic_has_one_expected_finding() -> None:
    from scripts.check_function_length import check_paths

    client = FIXTURES / "thin_client" / "frontend/src/shared/api/client.ts"
    findings = check_paths([client])
    assert [finding.rule for finding in findings] == ["MAINT-THIN-CLIENT"]
    assert findings[0].path.replace("\\", "/").endswith("frontend/src/shared/api/client.ts")


def test_repository_thin_client_passes() -> None:
    from scripts.check_function_length import check_paths

    assert check_paths([ROOT / "frontend/src/shared/api/client.ts"]) == []


def test_attendance_production_code_passes_maintainability_rules() -> None:
    from scripts.check_function_length import check_paths

    assert check_paths([ROOT / "backend/attendance"]) == []


def test_operations_production_code_passes_maintainability_rules() -> None:
    from scripts.check_function_length import check_paths

    assert check_paths([ROOT / "backend/operations"]) == []


def test_tasks_production_code_passes_maintainability_rules() -> None:
    from scripts.check_function_length import check_paths

    assert check_paths([ROOT / "backend/tasks"]) == []
