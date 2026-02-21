"""S3 storage client with local filesystem fallback."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class S3Storage:
    """Thin wrapper around boto3 S3 client with local-file fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = None
        self._use_local = False
        self._init_storage()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_storage(self) -> None:
        if not self._has_credentials():
            logger.warning(
                "AWS credentials not configured – falling back to local file storage "
                "(dir=%s)",
                self._settings.LOCAL_STORAGE_DIR,
            )
            self._use_local = True
            Path(self._settings.LOCAL_STORAGE_DIR).mkdir(parents=True, exist_ok=True)
            return

        self._client = boto3.client(
            "s3",
            aws_access_key_id=self._settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self._settings.AWS_SECRET_ACCESS_KEY,
            region_name=self._settings.AWS_REGION,
            config=BotoConfig(signature_version="s3v4"),
        )

    def _has_credentials(self) -> bool:
        return bool(
            self._settings.AWS_ACCESS_KEY_ID
            and self._settings.AWS_SECRET_ACCESS_KEY
            and self._settings.S3_BUCKET_NAME
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def is_local(self) -> bool:
        return self._use_local

    @property
    def bucket(self) -> str:
        return self._settings.S3_BUCKET_NAME

    def validate_connection(self) -> bool:
        """Return True if the S3 bucket is reachable, False otherwise."""
        if self._use_local:
            return Path(self._settings.LOCAL_STORAGE_DIR).is_dir()
        try:
            self._client.head_bucket(Bucket=self._settings.S3_BUCKET_NAME)  # type: ignore[union-attr]
            return True
        except (BotoCoreError, ClientError) as exc:
            logger.error("S3 connection validation failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Upload / download
    # ------------------------------------------------------------------

    def upload_fileobj(
        self,
        fileobj: BinaryIO,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file-like object; returns the public URL or local path."""
        if self._use_local:
            return self._save_local(fileobj, key)

        self._client.upload_fileobj(  # type: ignore[union-attr]
            fileobj,
            self._settings.S3_BUCKET_NAME,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return self._public_url(key)

    def object_exists(self, key: str) -> bool:
        """Check whether an object exists in the bucket (or locally)."""
        if self._use_local:
            return (Path(self._settings.LOCAL_STORAGE_DIR) / key).is_file()
        try:
            self._client.head_object(  # type: ignore[union-attr]
                Bucket=self._settings.S3_BUCKET_NAME, Key=key
            )
            return True
        except (BotoCoreError, ClientError):
            return False

    def generate_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        content_disposition: str | None = None,
    ) -> str:
        """Generate a pre-signed GET URL (S3) or local path.

        Args:
            key: S3 object key.
            expires_in: URL expiration in seconds (default 3600 = 1 hour).
            content_disposition: Optional disposition header, e.g.
                ``"inline"`` or ``"attachment; filename=report.pdf"``.
        """
        if self._use_local:
            return str(Path(self._settings.LOCAL_STORAGE_DIR) / key)

        params: dict = {"Bucket": self._settings.S3_BUCKET_NAME, "Key": key}
        if content_disposition:
            params["ResponseContentDisposition"] = content_disposition

        return self._client.generate_presigned_url(  # type: ignore[union-attr]
            "get_object",
            Params=params,
            ExpiresIn=expires_in,
        )

    def delete_object(self, key: str) -> None:
        if self._use_local:
            local_path = Path(self._settings.LOCAL_STORAGE_DIR) / key
            local_path.unlink(missing_ok=True)
            return

        self._client.delete_object(  # type: ignore[union-attr]
            Bucket=self._settings.S3_BUCKET_NAME,
            Key=key,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _save_local(self, fileobj: BinaryIO, key: str) -> str:
        dest = Path(self._settings.LOCAL_STORAGE_DIR) / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            shutil.copyfileobj(fileobj, f)
        return str(dest)

    def _public_url(self, key: str) -> str:
        if self._settings.CLOUDFRONT_DOMAIN:
            domain = self._settings.CLOUDFRONT_DOMAIN.rstrip("/")
            return f"https://{domain}/{key}"
        return (
            f"https://{self._settings.S3_BUCKET_NAME}"
            f".s3.{self._settings.AWS_REGION}.amazonaws.com/{key}"
        )


# ------------------------------------------------------------------
# Singleton / FastAPI dependency
# ------------------------------------------------------------------

_storage_instance: S3Storage | None = None


def get_storage() -> S3Storage:
    """Return a module-level singleton of S3Storage."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = S3Storage()
    return _storage_instance


def reset_storage() -> None:
    """Reset the singleton (useful in tests)."""
    global _storage_instance
    _storage_instance = None
