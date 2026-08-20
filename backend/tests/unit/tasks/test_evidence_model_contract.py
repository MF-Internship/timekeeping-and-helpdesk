from tasks.models import CompletionIdempotency, EvidenceUpload, TaskPhoto


def test_evidence_upload_has_private_binding_and_expiry_guards() -> None:
    assert {field.name for field in EvidenceUpload._meta.fields} == {
        "id",
        "task",
        "user",
        "object_key",
        "mime",
        "size_bytes",
        "checksum_sha256",
        "status",
        "created_at",
        "expires_at",
        "bound_update",
    }
    constraints = {constraint.name for constraint in EvidenceUpload._meta.constraints}
    assert constraints == {"evidence_upload_size_valid", "evidence_upload_bound_shape"}
    assert EvidenceUpload._meta.get_field("object_key").unique


def test_task_photo_is_one_to_one_with_upload_and_keeps_private_key() -> None:
    assert TaskPhoto._meta.get_field("evidence_upload").one_to_one
    assert TaskPhoto._meta.get_field("object_key").unique


def test_completion_idempotency_is_unique_per_actor_task_and_key() -> None:
    assert {constraint.name for constraint in CompletionIdempotency._meta.constraints} == {
        "task_completion_idempotency_unique"
    }
    assert CompletionIdempotency._meta.get_field("task_update").one_to_one
