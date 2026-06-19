"""Persists approved renders so service-webhook can fetch by render_id at
order time without re-rendering (spec Section 0 design decision).

UPDATE ME: this is a placeholder interface. Wire the real GCS or R2 client
once GCS_BUCKET/R2_* credentials in app/config.py are filled in.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.config import STORAGE_BACKEND, GCS_BUCKET, R2_BUCKET


class RenderStorage(ABC):
    @abstractmethod
    def put(self, render_id: str, png_bytes: bytes) -> str:
        """Store the PNG, return a fetchable URL or URI."""

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

    def put(self, render_id: str, png_bytes: bytes) -> str:
        blob = self._bucket().blob(f"renders/{render_id}.png")
        blob.upload_from_string(png_bytes, content_type="image/png")
        return f"gs://{self._bucket_name}/renders/{render_id}.png"

    def get(self, render_id: str) -> bytes:
        blob = self._bucket().blob(f"renders/{render_id}.png")
        return blob.download_as_bytes()


class R2RenderStorage(RenderStorage):
    """UPDATE ME: fill in R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY
    in app/config.py, then wire boto3's S3-compatible client (R2 is S3-compatible)."""

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

    def put(self, render_id: str, png_bytes: bytes) -> str:
        key = f"renders/{render_id}.png"
        self._s3().put_object(Bucket=self._bucket_name, Key=key, Body=png_bytes, ContentType="image/png")
        return f"r2://{self._bucket_name}/{key}"

    def get(self, render_id: str) -> bytes:
        key = f"renders/{render_id}.png"
        obj = self._s3().get_object(Bucket=self._bucket_name, Key=key)
        return obj["Body"].read()


def new_render_id() -> str:
    return uuid.uuid4().hex


def get_storage() -> RenderStorage:
    if STORAGE_BACKEND == "gcs":
        return GCSRenderStorage()
    if STORAGE_BACKEND == "r2":
        return R2RenderStorage()
    raise ValueError(f"unknown STORAGE_BACKEND: {STORAGE_BACKEND!r}")
