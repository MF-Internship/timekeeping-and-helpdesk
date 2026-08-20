from pathlib import Path

import yaml


def test_job_health_openapi_is_exact_get_only_closed_contract() -> None:
    document = yaml.safe_load(Path("contracts/openapi.yaml").read_text(encoding="utf-8"))
    path = document["paths"]["/api/v1/operations/job-health"]
    assert set(path) == {"get"}
    schema = document["components"]["schemas"]["JobHealth"]
    state_ref = schema["properties"]["state"]["$ref"].split("/")[-1]
    assert set(document["components"]["schemas"][state_ref]["enum"]) == {
        "ok",
        "alert",
        "unknown",
    }
    job_run = document["components"]["schemas"]["JobRun"]
    assert "changed_count" in job_run["properties"]
    assert "closed_count" not in job_run["properties"]
    reasons_ref = schema["properties"]["reason_flags"]["$ref"].split("/")[-1]
    assert set(document["components"]["schemas"][reasons_ref]["required"]) == {
        "no_run_history",
        "missing_timely_success",
        "unfinished_run",
        "stale_running",
        "latest_terminal_failed",
        "run_count_mismatch",
        "persisted_evidence_mismatch",
        "overdue_open_sessions",
    }
