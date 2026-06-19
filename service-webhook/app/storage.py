"""Fetch-only render storage client. Deliberately lightweight — no font or
render stack here, just the bytes service-render already produced (spec
Section 0 design decision: D never re-renders or re-transliterates).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.config import STORAGE_BACKEND, GCS_BUCKET, R2_BUCKET


class RenderStorage(ABC):
    @abstractmethod
    def get(self, render_id: str) -> bytes:
        """Fetch the PNG by render_id. Raises if not found."""


class GCSRenderStorage(RenderStorage):
    def __init__(self, bucket: str = GCS_BUCKET) -> None:
        self._bucket_name = bucket
        self._client = None

    def _bucket(self):
        if self._client is None:
            from google.cloud import storage as gcs  # type: ignore

            self._client = gcs.Client()
        return self._client.bucket(self._bucket_name)

    def get(self, render_id: str) -> bytes:
        blob = self._bucket().blob(f"renders/{render_id}.png")
        return blob.download_as_bytes()


class R2RenderStorage(RenderStorage):
    def __init__(self, bucket: str = R2_BUCKET) -> None:
        self._bucket_name = bucket
        self._client = None

    def _s3(self):
        if self._client is None:
            import boto3  # type: ignore
            from app.config import R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY

            self._client = boto3.client(
                "s3",
                endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                aws_access_key_id=R2_ACCESS_KEY_ID,
                aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            )
        return self._client

    def get(self, render_id: str) -> bytes:
        key = f"renders/{render_id}.png"
        obj = self._s3().get_object(Bucket=self._bucket_name, Key=key)
        return obj["Body"].read()


def get_storage() -> RenderStorage:
    if STORAGE_BACKEND == "gcs":
        return GCSRenderStorage()
    if STORAGE_BACKEND == "r2":
        return R2RenderStorage()
    raise ValueError(f"unknown STORAGE_BACKEND: {STORAGE_BACKEND!r}")
