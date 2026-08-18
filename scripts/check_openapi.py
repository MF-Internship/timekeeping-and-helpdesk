from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import yaml

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.event_payload import (  # noqa: E402
    ProtectedPayloadError,
    sanitize_failure_reason,
    validate_event_payload,
)

_SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")
_ALLOWED_PROTECTED_SCHEMA_PATHS = frozenset(
    {
        "$.components.schemas.Login.properties.password",
        "$.components.schemas.GeneratedUserResult.properties.generated_password",
        "$.components.schemas.ResetPasswordResult.properties.generated_password",
        # Coordinates are approved Location API fields. The safety check still
        # rejects coordinate values/examples anywhere in the schema.
        "$.components.schemas.Location.properties.latitude",
        "$.components.schemas.Location.properties.longitude",
        "$.components.schemas.LocationUpdate.properties.latitude",
        "$.components.schemas.LocationUpdate.properties.longitude",
        "$.components.schemas.PatchedLocationUpdate.properties.latitude",
        "$.components.schemas.PatchedLocationUpdate.properties.longitude",
        # Attendance coordinates are approved request/response field names;
        # values and examples remain forbidden by the recursive string check.
        "$.components.schemas.AttendanceCommand.properties.latitude",
        "$.components.schemas.AttendanceCommand.properties.longitude",
        "$.components.schemas.AttendancePunch.properties.captured_latitude",
        "$.components.schemas.AttendancePunch.properties.captured_longitude",
        "$.components.schemas.IndexedAttendancePunch.properties.captured_latitude",
        "$.components.schemas.IndexedAttendancePunch.properties.captured_longitude",
        "$.components.schemas.AttendanceCommandResult.properties.session",
    }
)


class OpenAPISafetyError(ValueError):
    pass


def check_openapi_text(text: str, artifact: str) -> None:
    try:
        document = yaml.safe_load(text)
        validate_event_payload(document, allowed_paths=_ALLOWED_PROTECTED_SCHEMA_PATHS)
        _check_strings(document, "$")
        _check_property_names(document, "$")
    except (yaml.YAMLError, ProtectedPayloadError, ValueError) as error:
        path = error.path if isinstance(error, ProtectedPayloadError) else "$"
        raise OpenAPISafetyError(f"OPENAPI-SAFETY: {artifact}:{path}") from error


def _check_strings(value: object, path: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            _check_strings(item, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, item in enumerate(value):
            _check_strings(item, f"{path}[{index}]")
    elif isinstance(value, str) and value and sanitize_failure_reason(value) != value:
        raise ValueError(path)


def _check_property_names(value: object, path: str) -> None:
    if not isinstance(value, Mapping):
        return
    properties = value.get("properties")
    if isinstance(properties, Mapping):
        for name in properties:
            if not _SNAKE_CASE.fullmatch(str(name)):
                raise ValueError(f"{path}.properties.{name}")
    for key, item in value.items():
        _check_property_names(item, f"{path}.{key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", required=True)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=BACKEND_ROOT.parent / "contracts/openapi.yaml",
    )
    arguments = parser.parse_args()
    try:
        check_openapi_text(
            arguments.artifact.read_text(encoding="utf-8"),
            str(arguments.artifact),
        )
    except (OSError, OpenAPISafetyError) as error:
        print(sanitize_failure_reason(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
