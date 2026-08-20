from django.db.models import CheckConstraint, UniqueConstraint

from tasks.models import Task, TaskAssignee, TaskUpdate


def test_task_snapshot_fields_constraints_and_indexes_are_closed() -> None:
    assert {field.name for field in Task._meta.fields} == {
        "id",
        "title",
        "description",
        "created_by",
        "assigned_date",
        "assignment_version",
        "status",
        "location",
        "expected_location_text",
        "deleted_at",
        "completed_by",
        "completed_at",
        "completion_method",
        "completion_note",
        "block_reason",
    }
    assert Task._meta.get_field("status").db_default is not None
    assert Task._meta.get_field("assignment_version").default == 1
    assert Task._meta.get_field("assignment_version").db_default is not None
    assert {
        constraint.name
        for constraint in Task._meta.constraints
        if isinstance(constraint, CheckConstraint)
    } == {
        "task_title_nonblank",
        "task_status_valid",
        "task_block_reason_shape",
        "task_completion_shape",
        "task_assignment_version_positive",
    }
    assert {index.name for index in Task._meta.indexes} == {
        "task_status_date_id_idx",
        "task_creator_status_idx",
    }


def test_assignee_is_unique_and_has_no_lifecycle_status() -> None:
    assert {field.name for field in TaskAssignee._meta.fields} == {
        "id",
        "task",
        "user",
        "assigned_at",
    }
    assert {
        tuple(constraint.fields)
        for constraint in TaskAssignee._meta.constraints
        if isinstance(constraint, UniqueConstraint)
    } == {("task", "user")}
    assert {index.name for index in TaskAssignee._meta.indexes} == {"task_assignee_user_idx"}


def test_update_completion_shape_and_history_index_are_closed() -> None:
    assert {field.name for field in TaskUpdate._meta.fields} == {
        "id",
        "task",
        "user",
        "status",
        "recorded_at",
        "note",
        "block_reason",
        "completion_method",
        "completion_note",
        "captured_latitude",
        "captured_longitude",
        "accuracy_m",
        "captured_at",
        "gps_quality",
        "actual_location",
        "validation_result",
        "resolution_method",
        "distance_m",
        "location_candidates",
    }
    assert {
        constraint.name
        for constraint in TaskUpdate._meta.constraints
        if isinstance(constraint, CheckConstraint)
    } == {
        "task_update_status_valid",
        "task_update_note_nonblank",
        "task_update_block_shape",
        "task_update_completion_shape",
    }
    assert {index.name for index in TaskUpdate._meta.indexes} == {"task_update_task_id_idx"}
