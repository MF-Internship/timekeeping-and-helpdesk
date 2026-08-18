from __future__ import annotations

import pytest
from scripts.generate_openapi import schema_document

from tests.integration.api.identity.helpers import manager_client
from tests.integration.api.locations.helpers import create_config, create_location


@pytest.mark.contract
def test_feature003_openapi_paths_statuses_and_warning_enum() -> None:
    document = schema_document()
    paths = document["paths"]
    assert set(paths) >= {
        "/api/v1/locations/",
        "/api/v1/locations/{location_id}/",
        "/api/v1/config/",
        "/api/v1/holidays/",
        "/api/v1/holidays/{holiday_id}/",
    }
    assert set(paths["/api/v1/locations/"]) == {"get"}
    assert set(paths["/api/v1/locations/{location_id}/"]) == {"patch"}
    assert set(paths["/api/v1/config/"]) == {"get", "patch"}
    assert set(paths["/api/v1/holidays/"]) == {"get", "post"}
    assert set(paths["/api/v1/holidays/{holiday_id}/"]) == {"delete"}
    assert set(paths["/api/v1/locations/"]["get"]["responses"]) == {
        "200",
        "400",
        "401",
        "403",
    }
    assert set(paths["/api/v1/locations/{location_id}/"]["patch"]["responses"]) == {
        "200",
        "400",
        "401",
        "403",
        "404",
        "409",
    }
    expected_responses = {
        ("/api/v1/config/", "get"): {"200", "401", "403", "404"},
        ("/api/v1/config/", "patch"): {"200", "400", "401", "403", "404"},
        ("/api/v1/holidays/", "get"): {"200", "401", "403"},
        ("/api/v1/holidays/", "post"): {"201", "400", "401", "403"},
        ("/api/v1/holidays/{holiday_id}/", "delete"): {"204", "401", "403", "404"},
    }
    for (path, method), statuses in expected_responses.items():
        assert set(paths[path][method]["responses"]) == statuses
    for path_name in (
        "/api/v1/locations/",
        "/api/v1/locations/{location_id}/",
        "/api/v1/config/",
        "/api/v1/holidays/",
        "/api/v1/holidays/{holiday_id}/",
    ):
        path = paths[path_name]
        for operation in path.values():
            for status, response in operation["responses"].items():
                if status.startswith(("2", "3")):
                    continue
                assert response["content"]["application/json"]["schema"] == {
                    "$ref": "#/components/schemas/FoundationError"
                }
    request_schema = paths["/api/v1/locations/{location_id}/"]["patch"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    request_name = request_schema["$ref"].rsplit("/", 1)[-1]
    assert "version" in document["components"]["schemas"][request_name]["required"]
    assert set(document["components"]["schemas"]["CodeEnum"]["enum"]) == {
        "RADIUS_BELOW_ATTENDANCE_ACCURACY",
        "GEOFENCE_OVERLAP",
    }
    warning = document["components"]["schemas"]["Warning"]
    assert set(warning["properties"]) >= {
        "code",
        "related_location_ids",
        "related_location_codes",
        "radius_m",
        "threshold_m",
    }
    kind_parameter = next(
        item for item in paths["/api/v1/locations/"]["get"]["parameters"] if item["name"] == "kind"
    )
    assert kind_parameter["schema"]["enum"] == [
        "BUSINESS_CENTER",
        "SHOP",
    ]


@pytest.mark.django_db(transaction=True)
@pytest.mark.contract
def test_feature003_private_headers_error_shape_and_absent_routes() -> None:
    create_config()
    target = create_location()
    api, _manager = manager_client("contract-location-manager")
    request_id = "123e4567-e89b-42d3-a456-426614174003"
    response = api.get("/api/v1/locations/", HTTP_X_REQUEST_ID=request_id)
    assert response.status_code == 200
    assert {value.strip() for value in response.headers["Cache-Control"].split(",")} == {
        "private",
        "no-store",
    }
    assert response.headers["X-Request-ID"]
    stale = api.patch(
        f"/api/v1/locations/{target.pk}/",
        {"version": 99, "name": "stale"},
        format="json",
        HTTP_X_REQUEST_ID=request_id,
    )
    assert stale.status_code == 409
    assert stale.json()["error_code"] == "LOCATION_VERSION_CONFLICT"
    assert stale.json()["details"] == {"current_version": 1}
    assert stale.json()["request_id"] == stale.headers["X-Request-ID"]
    assert api.post("/api/v1/locations/", {}, format="json").status_code == 404
    assert api.delete(f"/api/v1/locations/{target.pk}/").status_code == 404
