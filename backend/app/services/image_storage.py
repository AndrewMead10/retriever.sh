from __future__ import annotations

import mimetypes
import os
import secrets
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError

from ..config import settings


class R2ImageStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredImage:
    storage_key: str
    url: str


class R2ImageStorage:
    def __init__(self) -> None:
        account_id = settings.r2_account_id.strip()
        access_key = settings.r2_access_key_id.strip()
        secret_key = settings.r2_secret_access_key.strip()
        bucket = settings.r2_images_bucket.strip() or settings.r2_bucket.strip()

        if not account_id:
            raise R2ImageStorageError("R2 account ID is not configured")
        if not access_key or not secret_key:
            raise R2ImageStorageError("R2 access credentials are not configured")
        if not bucket:
            raise R2ImageStorageError("R2 image bucket is not configured")

        self._bucket = bucket
        self._public_base_url = settings.r2_images_public_base_url.strip().rstrip("/")
        self._presign_ttl_seconds = max(60, settings.r2_images_presign_ttl_seconds)
        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def upload_image(
        self,
        *,
        project_id: str,
        image_id: int,
        image_bytes: bytes,
        content_type: str,
        filename: Optional[str],
    ) -> StoredImage:
        extension = self._resolve_extension(filename=filename, content_type=content_type)
        random_suffix = secrets.token_hex(8)
        key = f"projects/{project_id}/images/{image_id}/{random_suffix}{extension}"

        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=image_bytes,
            ContentType=content_type,
        )
        return StoredImage(storage_key=key, url=self.resolve_url(key))

    def delete_image(self, *, storage_key: str) -> bool:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=storage_key)
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    def resolve_url(self, storage_key: str) -> str:
        if self._public_base_url:
            return f"{self._public_base_url}/{quote(storage_key)}"
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": storage_key},
            ExpiresIn=self._presign_ttl_seconds,
        )

    def _resolve_extension(self, *, filename: Optional[str], content_type: str) -> str:
        if filename:
            _, ext = os.path.splitext(filename)
            if ext:
                return ext.lower()
        guessed = mimetypes.guess_extension(content_type or "")
        if guessed:
            return guessed
        return ".bin"


@lru_cache(maxsize=1)
def get_r2_image_storage() -> R2ImageStorage:
    return R2ImageStorage()
