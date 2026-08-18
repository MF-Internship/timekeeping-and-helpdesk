from scripts.generate_openapi import schema_document


def test_today_contract_is_actor_only_snake_case_and_nullable() -> None:
    document = schema_document()
    operation = document["paths"]["/api/v1/attendance/today"]["get"]
    assert operation["operationId"] == "attendance_today_retrieve"
    assert "parameters" not in operation and "requestBody" not in operation
    schemas = document["components"]["schemas"]
    today = schemas["TodayAttendance"]
    assert set(today["properties"]) == {
        "work_date",
        "punches",
        "sessions",
        "total_duration_minutes",
        "has_open_session",
    }
    session = schemas["AttendanceSession"]["properties"]
    assert session["check_out_at"]["nullable"] is True
    assert session["duration_minutes"]["nullable"] is True
    punch = schemas["AttendancePunch"]["properties"]
    assert "example" not in punch["captured_latitude"]
    assert "example" not in punch["captured_longitude"]
