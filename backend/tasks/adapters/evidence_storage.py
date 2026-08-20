from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import boto3  # type: ignore[import-untyped]
from django.conf import settings
from django.utils import timezone

from tasks.ports.evidence import EvidenceObject, PresignedUpload, StoredEvidenceObject


class S3EvidenceStorage:
    def __init__(
        self,
        *,
        client: Any | None = None,
        bucket: str | None = None,
        now: Callable[[], datetime] = timezone.now,
    ) -> None:
        self._client = client or boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
        )
        self._bucket = bucket or settings.S3_BUCKET
        self._now = now

    def presign_put(self, evidence: EvidenceObject) -> PresignedUpload:
        metadata = {"checksum-sha256": evidence.checksum_sha256}
        params = {
            "Bucket": self._bucket,
            "Key": evidence.object_key,
            "ContentType": evidence.mime,
            "ContentLength": evidence.size_bytes,
            "Metadata": metadata,
        }
        url = self._client.generate_presigned_url("put_object", Params=params, ExpiresIn=900)
        return PresignedUpload(
            url,
            {
                "content-type": evidence.mime,
                "content-length": str(evidence.size_bytes),
                "x-amz-meta-checksum-sha256": evidence.checksum_sha256,
            },
            self._now() + timedelta(minutes=15),
        )

    def inspect(self, object_key: str) -> StoredEvidenceObject:
        response = self._client.head_object(Bucket=self._bucket, Key=object_key)
        metadata = response.get("Metadata") or {}
        return StoredEvidenceObject(
            str(response.get("ContentType", "")),
            int(response.get("ContentLength", 0)),
            str(metadata.get("checksum-sha256", "")),
        )

    def presign_get(self, object_key: str) -> tuple[str, datetime]:
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": object_key},
            ExpiresIn=900,
        )
        return url, self._now() + timedelta(minutes=15)

    def delete(self, object_key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=object_key)
