"""Tests for presigned URL generation (task 15.3)."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.storage import S3Storage
from app.services.file_upload import FileUploadError, FileUploadService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def local_storage(tmp_path: Path) -> S3Storage:
    """Return an S3Storage instance backed by a local temp directory."""
    settings = MagicMock()
    settings.AWS_ACCESS_KEY_ID = ""
    settings.AWS_SECRET_ACCESS_KEY = ""
    settings.S3_BUCKET_NAME = ""
    settings.LOCAL_STORAGE_DIR = str(tmp_path)
    return S3Storage(settings=settings)


@pytest.fixture()
def upload_service(local_storage: S3Storage) -> FileUploadService:
    settings = MagicMock()
    settings.ALLOWED_EXTENSIONS_DOCUMENTS = "pdf,doc,docx"
    settings.ALLOWED_EXTENSIONS_COLLECTION_PHOTOS = "jpg,jpeg,png,webp"
    settings.ALLOWED_EXTENSIONS_SIGNATURES = "png,jpg,jpeg"
    settings.ALLOWED_EXTENSIONS_REPORTS = "pdf,xlsx,csv"
    settings.MAX_FILE_SIZE_MB = 10
    return FileUploadService(storage=local_storage, settings=settings)


def _put_local_file(storage: S3Storage, key: str, content: bytes = b"hello") -> None:
    """Write a small file into the local storage backend."""
    storage.upload_fileobj(io.BytesIO(content), key)


# ---------------------------------------------------------------------------
# S3Storage.object_exists
# ---------------------------------------------------------------------------


class TestObjectExists:
    def test_exists_local(self, local_storage: S3Storage) -> None:
        _put_local_file(local_storage, "docs/test.pdf")
        assert local_storage.object_exists("docs/test.pdf") is True

    def test_not_exists_local(self, local_storage: S3Storage) -> None:
        assert local_storage.object_exists("nope.pdf") is False


# ---------------------------------------------------------------------------
# S3Storage.generate_presigned_url
# ---------------------------------------------------------------------------


class TestStoragePresignedUrl:
    def test_local_returns_path(self, local_storage: S3Storage) -> None:
        _put_local_file(local_storage, "docs/test.pdf")
        url = local_storage.generate_presigned_url("docs/test.pdf")
        assert "docs/test.pdf" in url

    def test_custom_expiry_local(self, local_storage: S3Storage) -> None:
        """Local backend ignores expiry but shouldn't crash."""
        url = local_storage.generate_presigned_url("a.txt", expires_in=60)
        assert isinstance(url, str)

    def test_content_disposition_local(self, local_storage: S3Storage) -> None:
        """Local backend ignores disposition but shouldn't crash."""
        url = local_storage.generate_presigned_url(
            "a.txt", content_disposition="attachment"
        )
        assert isinstance(url, str)

    def test_s3_passes_disposition(self) -> None:
        """Verify the boto3 client receives ResponseContentDisposition."""
        settings = MagicMock()
        settings.AWS_ACCESS_KEY_ID = "key"
        settings.AWS_SECRET_ACCESS_KEY = "secret"
        settings.S3_BUCKET_NAME = "bucket"
        settings.AWS_REGION = "us-east-1"

        with patch("app.core.storage.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_boto.client.return_value = mock_client
            mock_client.generate_presigned_url.return_value = "https://signed"

            storage = S3Storage(settings=settings)
            url = storage.generate_presigned_url(
                "f.pdf",
                expires_in=900,
                content_disposition='attachment; filename="f.pdf"',
            )

            mock_client.generate_presigned_url.assert_called_once_with(
                "get_object",
                Params={
                    "Bucket": "bucket",
                    "Key": "f.pdf",
                    "ResponseContentDisposition": 'attachment; filename="f.pdf"',
                },
                ExpiresIn=900,
            )
            assert url == "https://signed"


# ---------------------------------------------------------------------------
# FileUploadService.get_presigned_url
# ---------------------------------------------------------------------------


class TestServicePresignedUrl:
    def test_basic_presigned_url(
        self, upload_service: FileUploadService, local_storage: S3Storage
    ) -> None:
        _put_local_file(local_storage, "documents/report.pdf")
        url = upload_service.get_presigned_url("documents/report.pdf")
        assert "report.pdf" in url

    def test_validate_exists_raises(self, upload_service: FileUploadService) -> None:
        with pytest.raises(FileUploadError, match="Object not found"):
            upload_service.get_presigned_url("missing/file.pdf")

    def test_skip_validation(self, upload_service: FileUploadService) -> None:
        # Should not raise even though file doesn't exist
        url = upload_service.get_presigned_url(
            "missing/file.pdf", validate_exists=False
        )
        assert isinstance(url, str)

    def test_attachment_disposition(
        self, upload_service: FileUploadService, local_storage: S3Storage
    ) -> None:
        _put_local_file(local_storage, "documents/report.pdf")
        url = upload_service.get_presigned_url(
            "documents/report.pdf", content_disposition="attachment"
        )
        assert isinstance(url, str)

    def test_inline_disposition(
        self, upload_service: FileUploadService, local_storage: S3Storage
    ) -> None:
        _put_local_file(local_storage, "documents/report.pdf")
        url = upload_service.get_presigned_url(
            "documents/report.pdf", content_disposition="inline"
        )
        assert isinstance(url, str)

    def test_custom_expiry(
        self, upload_service: FileUploadService, local_storage: S3Storage
    ) -> None:
        _put_local_file(local_storage, "documents/a.pdf")
        url = upload_service.get_presigned_url("documents/a.pdf", expires_in=300)
        assert isinstance(url, str)
