from datetime import UTC, datetime

from tasks.adapters.evidence_storage import S3EvidenceStorage
from tasks.ports.evidence import EvidenceObject


class FakeS3Client:
    def __init__(self) -> None:
        self.presigned: list[tuple[str, dict[str, object], int]] = []
        self.deleted: list[dict[str, object]] = []

    def generate_presigned_url(self, operation: str, **kwargs: object) -> str:
        params = kwargs["Params"]
        expires_in = kwargs["ExpiresIn"]
        assert isinstance(params, dict)
        assert isinstance(expires_in, int)
        self.presigned.append((operation, params, expires_in))
        return f"https://storage.invalid/{operation}"

    def head_object(self, **_: object) -> dict[str, object]:
        return {
            "ContentType": "image/jpeg",
            "ContentLength": 123,
            "Metadata": {"checksum-sha256": "a" * 64},
        }

    def delete_object(self, **kwargs: object) -> None:
        self.deleted.append(kwargs)


def test_presigned_put_is_private_short_lived_and_metadata_bound() -> None:
    client = FakeS3Client()
    storage = S3EvidenceStorage(
        client=client,
        bucket="private-test",
        now=lambda: datetime(2026, 8, 20, tzinfo=UTC),
    )
    result = storage.presign_put(
        EvidenceObject("task-evidence/staging/1/2/id.jpg", "image/jpeg", 123, "a" * 64)
    )
    operation, params, expiry = client.presigned[0]
    assert operation == "put_object"
    assert expiry == 900
    assert params["Bucket"] == "private-test"
    assert params["ContentLength"] == 123
    assert params["Metadata"] == {"checksum-sha256": "a" * 64}
    assert "x-amz-meta-checksum-sha256" in result.headers


def test_head_verification_returns_declared_metadata_without_url() -> None:
    storage = S3EvidenceStorage(
        client=FakeS3Client(),
        bucket="private-test",
        now=lambda: datetime(2026, 8, 20, tzinfo=UTC),
    )
    stored = storage.inspect("task-evidence/staging/1/2/id.jpg")
    assert stored.mime == "image/jpeg"
    assert stored.size_bytes == 123
    assert stored.checksum_sha256 == "a" * 64


def test_presigned_get_is_short_lived() -> None:
    client = FakeS3Client()
    storage = S3EvidenceStorage(
        client=client,
        bucket="private-test",
        now=lambda: datetime(2026, 8, 20, tzinfo=UTC),
    )
    url, expires_at = storage.presign_get("bound/object.jpg")
    assert url.endswith("get_object")
    assert client.presigned[-1][2] == 900
    assert expires_at.isoformat() == "2026-08-20T00:15:00+00:00"


def test_delete_targets_the_private_bucket_object() -> None:
    client = FakeS3Client()
    storage = S3EvidenceStorage(client=client, bucket="private-test")
    storage.delete("task-evidence/staging/1/2/id.jpg")
    assert client.deleted == [{"Bucket": "private-test", "Key": "task-evidence/staging/1/2/id.jpg"}]
