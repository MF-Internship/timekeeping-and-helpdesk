from __future__ import annotations

import logging
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import authenticated_client, create_user
from tests.integration.api.locations.helpers import create_config, create_location

ROOT = Path(__file__).parents[4]

#: The two read operations the on-device guidance preview consumes, and the only
#: server work this feature adds a caller to.
GUIDANCE_REFERENCE_PATHS = ("/api/v1/locations/", "/api/v1/config/")

#: Packages that take part in serving those two paths: the views and application
#: services, the middleware and logging around them, and the authorization that
#: admits the caller.
REQUEST_PATH_PACKAGES = ("locations", "core", "config", "identity")

#: Metric clients whose presence would create labelled series. A coordinate can
#: only reach a label that exists, so the assertion below is that none does. This
#: test must be rewritten, not deleted, if a metrics stack is ever adopted.
METRIC_EMITTERS = (
    "prometheus_client",
    "django_prometheus",
    "statsd",
    "datadog",
    "opentelemetry",
)


@pytest.mark.django_db(transaction=True)
@pytest.mark.contract
def test_source_coordinates_never_enter_schema_evidence_or_command_output() -> None:
    create_config()
    actor = create_user("coordinate-safety-manager", "MANAGER")
    center = ROOT / "docs/dia_chi_ttkd.csv"
    first_coordinate = center.read_text(encoding="utf-8-sig").splitlines()[1].split(",")[-2]
    output = StringIO()
    call_command("seed_locations", actor_id=actor.pk, stdout=output)
    serialized = " ".join(
        [Path("contracts/openapi.yaml").read_text(encoding="utf-8"), output.getvalue()]
        + [str(value) for value in AuditLog.objects.values_list("before", "after")]
        + [str(value) for value in OutboxEvent.objects.values_list("payload", flat=True)]
    )
    assert first_coordinate not in serialized


@pytest.mark.django_db(transaction=True)
@pytest.mark.contract
def test_guidance_reference_reads_write_no_coordinate_into_any_log_record(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The two operations guidance reads may answer with coordinates, never log them.

    A Location's stored coordinates belong in the response body, which is what
    lets the browser measure a distance without asking the server. They do not
    belong in a log line, where they would outlive the request and be readable
    by anyone holding the log rather than the `location.view` grant (FR-033).

    Capture is proved live by a sentinel record, so an empty scan means nothing
    was logged rather than that nothing was captured.
    """
    create_config()
    location = create_location()
    api = authenticated_client(create_user("coordinate-log-reader", "HELPDESK"))
    probe = "coordinate-safety-capture-probe"

    with caplog.at_level(logging.DEBUG):
        logging.getLogger(__name__).debug(probe)
        for path in GUIDANCE_REFERENCE_PATHS:
            assert api.get(path).status_code == 200

    records = caplog.records
    logged = " ".join(
        [record.getMessage() for record in records]
        + [str(value) for record in records for value in vars(record).values()]
    )
    assert probe in logged
    for coordinate in (str(location.latitude), str(location.longitude)):
        assert coordinate not in logged


@pytest.mark.contract
def test_guidance_reference_reads_have_no_metric_label_to_carry_a_coordinate() -> None:
    """No module serving those two paths emits a metric, so no label can hold one.

    Stated structurally rather than by observation, because an absent emitter
    produces nothing to observe (FR-033).
    """
    offenders = sorted(
        f"{source.relative_to(ROOT)}: {emitter}"
        for package in REQUEST_PATH_PACKAGES
        for source in (ROOT / "backend" / package).rglob("*.py")
        for emitter in METRIC_EMITTERS
        if emitter in source.read_text(encoding="utf-8")
    )
    assert offenders == []
