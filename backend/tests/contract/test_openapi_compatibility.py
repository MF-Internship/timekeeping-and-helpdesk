from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

import pytest
import yaml

FIXTURES = Path(__file__).parent / "fixtures/compatibility"
GATE = "scripts/check_openapi_compatibility.sh"


def run_gate(baseline: str, candidate: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    result = subprocess.run(
        [
            GATE,
            "--baseline",
            str(FIXTURES / baseline),
            str(FIXTURES / candidate),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    return result


@pytest.mark.parametrize(
    ("baseline", "candidate"),
    [
        ("baseline.yaml", "removal.yaml"),
        ("baseline.yaml", "type_change.yaml"),
        ("baseline.yaml", "response_removal.yaml"),
        ("baseline.yaml", "new_required.yaml"),
        ("request_body_baseline.yaml", "request_body_new_required.yaml"),
    ],
)
def test_breaking_changes_fail(baseline: str, candidate: str) -> None:
    result = run_gate(baseline, candidate)
    assert result.returncode == 1, result.stderr
    assert result.stderr == "COMPAT-BREAKING: contracts/openapi.yaml\n"


def test_additive_optional_change_passes() -> None:
    result = run_gate("baseline.yaml", "additive_optional.yaml")
    assert result.returncode == 0, result.stderr


def test_gate_uses_pinned_oasdiff_not_custom_compatibility_logic() -> None:
    gate = Path(GATE).read_text(encoding="utf-8")
    installer = Path("scripts/install_oasdiff.sh").read_text(encoding="utf-8")
    assert 'version="1.26.1"' in installer
    assert "oasdiff/oasdiff/releases/download" in installer
    assert "shasum -a 256" in installer
    assert '"$oasdiff_binary" breaking' in gate
    assert not Path("scripts/openapi_compatibility.py").exists()


def test_arbitrary_oasdiff_override_cannot_bypass_breaking_change(
    tmp_path: Path,
) -> None:
    override = tmp_path / "always-pass"
    marker = tmp_path / "override-ran"
    override.write_text(
        f"#!/bin/sh\ntouch '{marker}'\nexit 0\n",
        encoding="utf-8",
    )
    override.chmod(0o755)
    environment = dict(os.environ, OASDIFF_BIN=str(override))
    result = subprocess.run(
        [
            GATE,
            "--baseline",
            str(FIXTURES / "baseline.yaml"),
            str(FIXTURES / "removal.yaml"),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    assert result.returncode == 1
    assert not marker.exists()


def test_installer_replaces_tampered_cached_executable(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    trusted_source = tmp_path / "oasdiff"
    trusted_source.write_text("#!/bin/sh\nprintf 'trusted\\n'\n", encoding="utf-8")
    trusted_source.chmod(0o755)
    archive = tmp_path / "trusted.tar.gz"
    subprocess.run(["tar", "-czf", str(archive), "-C", str(tmp_path), "oasdiff"], check=True)
    curl = fake_bin / "curl"
    curl.write_text(
        "#!/bin/sh\n"
        'while [ "$#" -gt 0 ]; do\n'
        '  if [ "$1" = "--output" ]; then\n'
        '    cp "$FAKE_OASDIFF_ARCHIVE" "$2"\n'
        "    exit 0\n"
        "  fi\n"
        "  shift\n"
        "done\n"
        "exit 1\n",
        encoding="utf-8",
    )
    curl.chmod(0o755)
    shasum = fake_bin / "shasum"
    shasum.write_text(
        '#!/bin/sh\nprintf \'%s  %s\\n\' "$FAKE_OASDIFF_CHECKSUM" "$3"\n',
        encoding="utf-8",
    )
    shasum.chmod(0o755)
    expected_checksums = {
        ("Darwin", "arm64"): "ac3f56e9b7f3c717355768bc6943b5b54461f43e5c87d1e20027e2209093d2aa",
        ("Darwin", "x86_64"): "ac3f56e9b7f3c717355768bc6943b5b54461f43e5c87d1e20027e2209093d2aa",
        ("Linux", "x86_64"): "ea0007fe536c7915785f754885d2afdb11352d6a14531950edf9d601a2baa674",
        ("Linux", "aarch64"): "423ef13ac4197b1fca948ccd6839dbaa8a666841b59466542f0332a7e95a1d66",
    }
    environment = dict(
        os.environ,
        PATH=f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        OASDIFF_INSTALL_DIR=str(tmp_path / "install"),
        FAKE_OASDIFF_ARCHIVE=str(archive),
        FAKE_OASDIFF_CHECKSUM=expected_checksums[(platform.system(), platform.machine())],
    )
    first = subprocess.run(
        ["scripts/install_oasdiff.sh"],
        capture_output=True,
        text=True,
        check=True,
        env=environment,
    )
    installed = Path(first.stdout.strip())
    installed.write_text("#!/bin/sh\nprintf 'tampered\\n'\n", encoding="utf-8")
    installed.chmod(0o755)
    second = subprocess.run(
        ["scripts/install_oasdiff.sh"],
        capture_output=True,
        text=True,
        check=True,
        env=environment,
    )
    repaired = Path(second.stdout.strip())
    assert (
        subprocess.run([str(repaired)], capture_output=True, text=True, check=True).stdout
        == "trusted\n"
    )


def test_attendance_paths_and_error_unions_are_committed_compatibility_surface() -> None:
    document = yaml.safe_load(Path("contracts/openapi.yaml").read_text(encoding="utf-8"))
    assert set(document["paths"]) >= {
        "/api/v1/attendance/check-in",
        "/api/v1/attendance/check-out",
        "/api/v1/attendance/today",
    }
    schemas = document["components"]["schemas"]
    assert len(schemas["CheckInConflictError"]["oneOf"]) == 2
    assert len(schemas["CheckOutConflictError"]["oneOf"]) == 2
    assert len(schemas["AttendanceUnprocessableError"]["oneOf"]) == 2
