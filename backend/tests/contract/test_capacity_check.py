from __future__ import annotations

import json
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import pytest

if TYPE_CHECKING:
    from scripts.capacity_check import CapacityIdentity


class Resource:
    def __init__(self, sample_ms: float, *, fail: bool = False) -> None:
        self.sample_ms = sample_ms
        self.fail = fail
        self.closed = False

    def measure(self, _identity: str) -> float:
        if self.fail:
            raise RuntimeError("password=hunter2 https://example.invalid")
        return self.sample_ms

    def close(self) -> None:
        self.closed = True


def identities(count: int = 50) -> tuple[CapacityIdentity, ...]:
    from scripts.capacity_check import CapacityIdentity

    return tuple(
        CapacityIdentity(
            identity_id=f"employee-{index:03d}",
            bearer_token=f"short-lived-token-{index:03d}",
        )
        for index in range(count)
    )


def identity_file_contents(count: int = 50) -> str:
    return (
        "\n".join(
            json.dumps(
                {
                    "identity_id": f"employee-{index:03d}",
                    "bearer_token": f"short-lived-token-{index:03d}",
                }
            )
            for index in range(count)
        )
        + "\n"
    )


class CapacityRequestHandler(BaseHTTPRequestHandler):
    authorizations: ClassVar[list[str]] = []

    def do_GET(self) -> None:
        type(self).authorizations.append(self.headers.get("Authorization", ""))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, _format: str, *args: object) -> None:
        del args


@contextmanager
def capacity_server() -> Iterator[str]:
    CapacityRequestHandler.authorizations = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), CapacityRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}/api/v1/capacity-probe/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize(
    ("identity_count", "concurrency", "rule"),
    [(49, 20, "CAPACITY-IDENTITIES"), (50, 19, "CAPACITY-CONCURRENCY")],
)
def test_ineligible_input_rejects_before_resources_open(
    identity_count: int, concurrency: int, rule: str
) -> None:
    from scripts.capacity_check import CapacityEligibilityError, CapacityInputs, measure_capacity

    opened = 0

    def open_resource() -> Resource:
        nonlocal opened
        opened += 1
        return Resource(500)

    with pytest.raises(CapacityEligibilityError, match=rule):
        measure_capacity(
            CapacityInputs(identities(identity_count), concurrency, "ops"), open_resource
        )
    assert opened == 0


def test_different_tokens_for_one_account_reject_before_resources_open() -> None:
    from scripts.capacity_check import (
        CapacityEligibilityError,
        CapacityIdentity,
        CapacityInputs,
        measure_capacity,
    )

    opened = 0

    def open_resource() -> Resource:
        nonlocal opened
        opened += 1
        return Resource(500)

    records = tuple(
        CapacityIdentity("same-account", f"rotated-token-{index:03d}") for index in range(50)
    )
    with pytest.raises(CapacityEligibilityError, match="CAPACITY-IDENTITIES"):
        measure_capacity(CapacityInputs(records, 20, "ops"), open_resource)
    assert opened == 0


def test_exact_boundary_passes_and_every_resource_closes() -> None:
    from scripts.capacity_check import CapacityInputs, measure_capacity

    resources: list[Resource] = []

    def open_resource() -> Resource:
        resource = Resource(500)
        resources.append(resource)
        return resource

    result = measure_capacity(CapacityInputs(identities(), 20, "ops"), open_resource)
    assert result.status == "passed"
    assert result.measured_p95_ms == 500
    assert len(resources) == 50
    assert all(resource.closed for resource in resources)


def test_above_boundary_fails_with_owner_and_no_identities_in_result() -> None:
    from scripts.capacity_check import CapacityInputs, measure_capacity

    result = measure_capacity(
        CapacityInputs(identities(), 20, "capacity-owner"), lambda: Resource(501)
    )
    assert result.status == "failed"
    assert result.remediation_owner == "capacity-owner"
    assert "employee-" not in repr(result)


def test_measurement_failure_closes_resources_and_does_not_expose_reason() -> None:
    from scripts.capacity_check import CapacityInputs, measure_capacity

    resources: list[Resource] = []

    def open_resource() -> Resource:
        resource = Resource(500, fail=True)
        resources.append(resource)
        return resource

    result = measure_capacity(CapacityInputs(identities(), 20, "ops"), open_resource)
    assert result.status == "failed"
    assert all(resource.closed for resource in resources)
    assert "hunter2" not in repr(result)
    assert "example.invalid" not in repr(result)


def test_result_writer_cannot_mutate_recovery_evidence(tmp_path: Path) -> None:
    from scripts.capacity_check import CapacityEligibilityError, CapacityResult, write_result

    evidence = Path("deploy/recovery-evidence.yaml")
    before = evidence.read_bytes()
    result = CapacityResult("passed", 50, 20, 500, "ops")
    with pytest.raises(CapacityEligibilityError, match="CAPACITY-EVIDENCE-BOUNDARY"):
        write_result(evidence, result)
    output = tmp_path / "capacity.json"
    write_result(output, result)
    assert evidence.read_bytes() == before
    assert "identities" not in output.read_text(encoding="utf-8").replace("distinct_identities", "")


def test_http_adapter_performs_real_io_for_every_eligible_identity() -> None:
    from scripts.capacity_check import CapacityInputs, HttpSampleResource, measure_capacity

    with capacity_server() as target_url:
        result = measure_capacity(
            CapacityInputs(identities(), 20, "ops"),
            lambda: HttpSampleResource(target_url, 2_000),
        )
    assert result.status == "passed"
    assert result.measured_p95_ms is not None
    assert len(CapacityRequestHandler.authorizations) == 50
    assert set(CapacityRequestHandler.authorizations) == {
        f"Bearer short-lived-token-{index:03d}" for index in range(50)
    }


@pytest.mark.parametrize(
    ("target_url", "rule"),
    [
        ("http://capacity.example.invalid/api/v1/probe/", "CAPACITY-TARGET-HTTPS"),
        ("https://user:secret@example.invalid/api/v1/probe/", "CAPACITY-TARGET-URL"),
        ("https://capacity.example.invalid/health", "CAPACITY-TARGET-PATH"),
    ],
)
def test_http_adapter_rejects_unsafe_targets(target_url: str, rule: str) -> None:
    from scripts.capacity_check import CapacityEligibilityError, HttpSampleResource

    with pytest.raises(CapacityEligibilityError, match=rule):
        HttpSampleResource(target_url, 2_000)


def test_capacity_cli_uses_observed_http_latency_without_leaking_inputs(
    tmp_path: Path,
) -> None:
    identity_file = tmp_path / "operators.identities"
    identity_file.write_text(identity_file_contents(), encoding="utf-8")
    output = tmp_path / "capacity.json"
    with capacity_server() as target_url:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/capacity_check.py",
                "measure",
                "--identities",
                str(identity_file),
                "--concurrency",
                "20",
                "--target-url",
                target_url,
                "--remediation-owner",
                "ops",
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    assert result.returncode == 0, result.stderr
    document = json.loads(result.stdout)
    assert document["measured_p95_ms"] >= 0
    combined_output = result.stdout + result.stderr + output.read_text(encoding="utf-8")
    assert "employee-" not in combined_output
    assert "short-lived-token-" not in combined_output
    assert target_url not in combined_output
    assert "Bearer" not in combined_output


def run_capacity_cli(
    identity_file: Path, output: Path, target_url: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/capacity_check.py",
            "measure",
            "--identities",
            str(identity_file),
            "--concurrency",
            "20",
            "--target-url",
            target_url,
            "--remediation-owner",
            "ops",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_capacity_cli_sanitizes_missing_identity_file(tmp_path: Path) -> None:
    identity_file = tmp_path / "secret-account.identities"
    output = tmp_path / "capacity.json"
    result = run_capacity_cli(
        identity_file, output, "https://capacity.example.invalid/api/v1/probe/"
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "CAPACITY-CHECK: CAPACITY-IDENTITY-FILE\n"
    assert str(identity_file) not in result.stderr
    assert "Traceback" not in result.stderr
    assert not output.exists()


def test_capacity_cli_sanitizes_malformed_identity_record(tmp_path: Path) -> None:
    identity_file = tmp_path / "operators.identities"
    identity_file.write_text(
        '{"identity_id":"private-account","bearer_token":"protected-token"\n',
        encoding="utf-8",
    )
    output = tmp_path / "capacity.json"
    result = run_capacity_cli(
        identity_file, output, "https://capacity.example.invalid/api/v1/probe/"
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "CAPACITY-CHECK: CAPACITY-IDENTITY-FORMAT\n"
    assert "private-account" not in result.stderr
    assert "protected-token" not in result.stderr
    assert "Traceback" not in result.stderr
    assert not output.exists()


def test_capacity_cli_sanitizes_invalid_identity_encoding(tmp_path: Path) -> None:
    identity_file = tmp_path / "operators.identities"
    identity_file.write_bytes(b"private-account protected-token \xff")
    output = tmp_path / "capacity.json"
    result = run_capacity_cli(
        identity_file, output, "https://capacity.example.invalid/api/v1/probe/"
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "CAPACITY-CHECK: CAPACITY-IDENTITY-FILE\n"
    assert "private-account" not in result.stderr
    assert "protected-token" not in result.stderr
    assert "\\xff" not in result.stderr
    assert "Traceback" not in result.stderr
    assert not output.exists()


def test_capacity_cli_sanitizes_target_before_measurement(tmp_path: Path) -> None:
    identity_file = tmp_path / "operators.identities"
    identity_file.write_text(identity_file_contents(), encoding="utf-8")
    output = tmp_path / "capacity.json"
    target_url = "https://private-user:protected-password@example.invalid/api/v1/probe/"
    result = run_capacity_cli(identity_file, output, target_url)
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "CAPACITY-CHECK: CAPACITY-TARGET-URL\n"
    assert target_url not in result.stderr
    assert "private-user" not in result.stderr
    assert "protected-password" not in result.stderr
    assert not output.exists()
