"""Tests for S3Storage configuration and local fallback."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.core.storage import S3Storage, get_storage, reset_storage

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _settings(**overrides) -> Settings:
    defaults = dict(
        DATABASE_URL="sqlite+aiosqlite:///test.db",
        REDIS_URL="redis://localhost:6379/0",
        AWS_ACCESS_KEY_ID="",
        AWS_SECRET_ACCESS_KEY="",
        AWS_REGION="ap-south-1",
        S3_BUCKET_NAME="",
        CLOUDFRONT_DOMAIN="",
        LOCAL_STORAGE_DIR="/tmp/prickncare_test_uploads",
    )
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def _s3_settings() -> Settings:
    return _settings(
        AWS_ACCESS_KEY_ID="AKIATEST",
        AWS_SECRET_ACCESS_KEY="secret",
        S3_BUCKET_NAME="test-bucket",
    )


# ------------------------------------------------------------------
# Initialisation
# ------------------------------------------------------------------


class TestS3StorageInit:
    def test_local_fallback_when_no_credentials(self, tmp_path: Path):
        s = _settings(LOCAL_STORAGE_DIR=str(tmp_path / "uploads"))
        storage = S3Storage(settings=s)
        assert storage.is_local is True
        assert storage._client is None

    @patch("app.core.storage.boto3.client")
    def test_s3_client_created_with_credentials(self, mock_boto):
        storage = S3Storage(settings=_s3_settings())
        assert storage.is_local is False
        mock_boto.assert_called_once()
        # Verify signature v4
        call_kwargs = mock_boto.call_args
        assert call_kwargs[1]["config"].signature_version == "s3v4"

    def test_local_dir_created(self, tmp_path: Path):
        d = tmp_path / "new_dir"
        S3Storage(settings=_settings(LOCAL_STORAGE_DIR=str(d)))
        assert d.is_dir()


# ------------------------------------------------------------------
# Connection validation
# ------------------------------------------------------------------


class TestValidateConnection:
    def test_local_validate(self, tmp_path: Path):
        storage = S3Storage(settings=_settings(LOCAL_STORAGE_DIR=str(tmp_path)))
        assert storage.validate_connection() is True

    @patch("app.core.storage.boto3.client")
    def test_s3_validate_success(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        storage = S3Storage(settings=_s3_settings())
        assert storage.validate_connection() is True
        mock_client.head_bucket.assert_called_once_with(Bucket="test-bucket")

    @patch("app.core.storage.boto3.client")
    def test_s3_validate_failure(self, mock_boto):
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"
        )
        mock_boto.return_value = mock_client
        storage = S3Storage(settings=_s3_settings())
        assert storage.validate_connection() is False


# ------------------------------------------------------------------
# Upload / local fallback
# ------------------------------------------------------------------


class TestLocalUpload:
    def test_upload_and_read(self, tmp_path: Path):
        storage = S3Storage(settings=_settings(LOCAL_STORAGE_DIR=str(tmp_path)))
        data = b"hello world"
        path = storage.upload_fileobj(io.BytesIO(data), "test/file.txt")
        assert Path(path).read_bytes() == data

    def test_delete_local(self, tmp_path: Path):
        storage = S3Storage(settings=_settings(LOCAL_STORAGE_DIR=str(tmp_path)))
        storage.upload_fileobj(io.BytesIO(b"x"), "del.txt")
        storage.delete_object("del.txt")
        assert not (tmp_path / "del.txt").exists()

    def test_presigned_url_local(self, tmp_path: Path):
        storage = S3Storage(settings=_settings(LOCAL_STORAGE_DIR=str(tmp_path)))
        url = storage.generate_presigned_url("foo/bar.jpg")
        assert "foo/bar.jpg" in url


# ------------------------------------------------------------------
# URL generation
# ------------------------------------------------------------------


class TestPublicUrl:
    @patch("app.core.storage.boto3.client")
    def test_cloudfront_url(self, mock_boto):
        s = _s3_settings()
        s = _settings(
            AWS_ACCESS_KEY_ID="AKIATEST",
            AWS_SECRET_ACCESS_KEY="secret",
            S3_BUCKET_NAME="test-bucket",
            CLOUDFRONT_DOMAIN="cdn.example.com",
        )
        storage = S3Storage(settings=s)
        url = storage._public_url("images/photo.jpg")
        assert url == "https://cdn.example.com/images/photo.jpg"

    @patch("app.core.storage.boto3.client")
    def test_s3_direct_url(self, mock_boto):
        storage = S3Storage(settings=_s3_settings())
        url = storage._public_url("images/photo.jpg")
        assert "test-bucket" in url
        assert "images/photo.jpg" in url


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------


class TestSingleton:
    def test_get_storage_returns_same_instance(self):
        reset_storage()
        with patch("app.core.storage.get_settings", return_value=_settings()):
            a = get_storage()
            b = get_storage()
            assert a is b
        reset_storage()
