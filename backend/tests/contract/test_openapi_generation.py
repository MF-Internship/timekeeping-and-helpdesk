from __future__ import annotations

from scripts.generate_openapi import generate_openapi_bytes


def test_openapi_is_deterministic_and_canonical() -> None:
    first = generate_openapi_bytes()
    second = generate_openapi_bytes()
    assert first == second
    assert b"\r\n" not in first
    text = first.decode()
    assert text.startswith("openapi: 3.0.3\n")
    assert "version: 1.0.0" in text
    assert "operationId:" in text
    assert "timestamp" not in text.casefold()
    assert str(__file__) not in text


def test_all_paths_operation_ids_and_properties_are_canonical() -> None:
    from scripts.generate_openapi import schema_document

    document = schema_document()
    paths = document["paths"]
    assert paths
    operation_ids: list[str] = []
    for path, item in paths.items():
        assert path.startswith("/api/v1/")
        for operation in item.values():
            operation_ids.append(operation["operationId"])
    assert len(operation_ids) == len(set(operation_ids))
    assert operation_ids == [
        "attendance_check_in",
        "attendance_check_out",
        "attendance_today_retrieve",
        "auth_login_create",
        "auth_logout_create",
        "auth_refresh_create",
        "identity_change_password_create",
        "config_retrieve",
        "config_partial_update",
        "holidays_list",
        "holidays_create",
        "holidays_destroy",
        "locations_list",
        "locations_partial_update",
        "identity_me_retrieve",
        "identity_me_partial_update",
        "notifications_list",
        "notifications_mark_read",
        "notifications_resolve_target",
        "operations_job_health_retrieve",
        "push_subscriptions_upsert",
        "push_subscriptions_revoke",
        "reports_attendance_retrieve",
        "reports_attendance_export",
        "reports_tasks_retrieve",
        "reports_tasks_export",
        "api_schema_retrieve",
        "tasks_list",
        "tasks_create",
        "tasks_destroy",
        "tasks_retrieve",
        "tasks_partial_update",
        "tasks_complete_field_create",
        "tasks_complete_override_create",
        "tasks_evidence_uploads_create",
        "tasks_photos_access_create",
        "tasks_status_create",
        "users_list",
        "users_create",
        "users_retrieve",
        "users_partial_update",
        "users_reset_password_create",
        "users_role_partial_update",
        "users_status_partial_update",
    ]


def test_task_evidence_protected_fields_are_narrowly_allowlisted() -> None:
    from scripts.check_openapi import check_openapi_text

    generated = generate_openapi_bytes().decode("utf-8")
    assert "TaskFieldCompletion" in generated
    assert "EvidenceUploadIntent" in generated
    assert "PhotoAccess" in generated
    check_openapi_text(generated, "generated-task-evidence")
