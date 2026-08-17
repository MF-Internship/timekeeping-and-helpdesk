from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from core.event_payload import sanitize_failure_reason  # noqa: E402

MINIMUM_IDENTITIES = 50
MINIMUM_CONCURRENCY = 20
MAXIMUM_P95_MS = 500.0


class CapacityEligibilityError(ValueError):
    pass


class SampleResource(Protocol):
    def measure(self, bearer_token: str) -> float: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class CapacityIdentity:
    identity_id: str
    bearer_token: str


@dataclass(frozen=True, slots=True)
class CapacityInputs:
    identities: tuple[CapacityIdentity, ...]
    concurrency: int
    remediation_owner: str


@dataclass(frozen=True, slots=True)
class CapacityResult:
    status: str
    distinct_identities: int
    concurrency: int
    measured_p95_ms: float | None
    remediation_owner: str


def measure_capacity(
    inputs: CapacityInputs,
    open_resource: Callable[[], SampleResource],
) -> CapacityResult:
    identities = _eligible_identities(inputs)
    timings: list[float] = []
    failed = False
    with ThreadPoolExecutor(max_workers=inputs.concurrency) as executor:
        futures = [
            executor.submit(_measure_one, identity.bearer_token, open_resource)
            for identity in identities
        ]
        for future in futures:
            try:
                timings.append(future.result())
            except Exception:
                failed = True
    p95_ms = _p95(timings) if timings else None
    status = (
        "failed" if failed or p95_ms is None or p95_ms > MAXIMUM_P95_MS else "passed"
    )
    return CapacityResult(
        status, len(identities), inputs.concurrency, p95_ms, inputs.remediation_owner
    )


def _eligible_identities(inputs: CapacityInputs) -> tuple[CapacityIdentity, ...]:
    identities_by_id: dict[str, CapacityIdentity] = {}
    for record in inputs.identities:
        identity_id = record.identity_id.strip()
        bearer_token = record.bearer_token.strip()
        if not identity_id or not bearer_token:
            raise CapacityEligibilityError("CAPACITY-IDENTITY-FORMAT")
        identities_by_id.setdefault(
            identity_id, CapacityIdentity(identity_id, bearer_token)
        )
    identities = tuple(identities_by_id.values())
    if len(identities) < MINIMUM_IDENTITIES:
        raise CapacityEligibilityError("CAPACITY-IDENTITIES")
    if inputs.concurrency < MINIMUM_CONCURRENCY:
        raise CapacityEligibilityError("CAPACITY-CONCURRENCY")
    if not inputs.remediation_owner.strip():
        raise CapacityEligibilityError("CAPACITY-REMEDIATION-OWNER")
    if any(_is_placeholder(identity.identity_id) for identity in identities):
        raise CapacityEligibilityError("CAPACITY-REAL-IDENTITIES")
    return identities


def _is_placeholder(identity: str) -> bool:
    normalized = identity.casefold()
    return normalized.startswith(("test", "fixture", "example"))


def _measure_one(
    bearer_token: str, open_resource: Callable[[], SampleResource]
) -> float:
    resource = open_resource()
    try:
        return float(resource.measure(bearer_token))
    finally:
        resource.close()


def _p95(values: Sequence[float]) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def write_result(path: Path, result: CapacityResult) -> None:
    evidence = (ROOT / "deploy/recovery-evidence.yaml").resolve()
    if path.resolve() == evidence:
        raise CapacityEligibilityError("CAPACITY-EVIDENCE-BOUNDARY")
    path.write_text(json.dumps(asdict(result), sort_keys=True) + "\n", encoding="utf-8")


class HttpSampleResource:
    def __init__(self, target_url: str, timeout_ms: int) -> None:
        self.target_url = _validated_target_url(target_url)
        self.timeout_seconds = timeout_ms / 1000

    def measure(self, bearer_token: str) -> float:
        request = Request(
            self.target_url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {bearer_token}",
            },
            method="GET",
        )
        started = time.perf_counter()
        with urlopen(request, timeout=self.timeout_seconds) as response:
            response.read()
        return (time.perf_counter() - started) * 1000

    def close(self) -> None:
        return None


def _validated_target_url(target_url: str) -> str:
    parsed = urlsplit(target_url)
    is_loopback = parsed.hostname in {"127.0.0.1", "::1", "localhost"}
    if parsed.scheme != "https" and not (parsed.scheme == "http" and is_loopback):
        raise CapacityEligibilityError("CAPACITY-TARGET-HTTPS")
    if parsed.username or parsed.password or not parsed.hostname:
        raise CapacityEligibilityError("CAPACITY-TARGET-URL")
    if not parsed.path.startswith("/api/v1/"):
        raise CapacityEligibilityError("CAPACITY-TARGET-PATH")
    return target_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    measure = subparsers.add_parser("measure")
    measure.add_argument("--identities", type=Path, required=True)
    measure.add_argument("--concurrency", type=int, required=True)
    measure.add_argument("--target-url", required=True)
    measure.add_argument("--timeout-ms", type=int, default=10_000)
    measure.add_argument("--remediation-owner", required=True)
    measure.add_argument("--output", type=Path)
    return parser


def parse_identity_records(document: str) -> tuple[CapacityIdentity, ...]:
    records: list[CapacityIdentity] = []
    for line in document.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise CapacityEligibilityError("CAPACITY-IDENTITY-FORMAT") from error
        if not isinstance(value, dict) or set(value) != {"identity_id", "bearer_token"}:
            raise CapacityEligibilityError("CAPACITY-IDENTITY-FORMAT")
        identity_id = value["identity_id"]
        bearer_token = value["bearer_token"]
        if not isinstance(identity_id, str) or not isinstance(bearer_token, str):
            raise CapacityEligibilityError("CAPACITY-IDENTITY-FORMAT")
        records.append(CapacityIdentity(identity_id, bearer_token))
    return tuple(records)


def read_identity_records(path: Path) -> tuple[CapacityIdentity, ...]:
    try:
        document = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise CapacityEligibilityError("CAPACITY-IDENTITY-FILE") from error
    return parse_identity_records(document)


def _safe_cli_failure(error: Exception) -> str:
    reason: object = error
    if not isinstance(error, CapacityEligibilityError):
        reason = type(error).__name__
    return sanitize_failure_reason(reason)


def main() -> int:
    arguments = build_parser().parse_args()
    try:
        identities = read_identity_records(arguments.identities)
        target_url = _validated_target_url(arguments.target_url)
        inputs = CapacityInputs(
            identities, arguments.concurrency, arguments.remediation_owner
        )
        result = measure_capacity(
            inputs,
            lambda: HttpSampleResource(target_url, arguments.timeout_ms),
        )
        if arguments.output:
            write_result(arguments.output, result)
    except Exception as error:
        print(f"CAPACITY-CHECK: {_safe_cli_failure(error)}", file=sys.stderr)
        return 1
    print(json.dumps(asdict(result), sort_keys=True))
    return int(result.status != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
