"""Tests for FileUploadService."""

from __future__ import annotations

import io
from unittest.mock import MagicMock

import pytest
from fastapi import UploadFile

from app.core.config import Settings
from app.services.file_upload import (
    VALID_FOLDERS,
    FileUploadError,
    FileUploadService,
    reset_file_upload_service,
)

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        MAX_FILE_SIZE_MB=5,
        ALLOWED_EXTENSIONS_DOCUMENTS="pdf,doc,docx,xls,xlsx,csv,txt",
        ALLOWED_EXTENSIONS_COLLECTION_PHOTOS="jpg,jpeg,png,webp",
        ALLOWED_EXTENSIONS_SIGNATURES="jpg,jpeg,png,svg",
        ALLOWED_EXTENSIONS_REPORTS="pdf,jpg,jpeg,png",
        CLOUDFRONT_DOMAIN="cdn.example.com",
        S3_BUCKET_NAME="test-bucket",
        AWS_REGION="ap-south-1",
        LOCAL_STORAGE_DIR="/tmp/test_uploads",
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _make_upload_file(
    filename: str = "test.pdf",
    content: bytes = b"%PDF-fake-content",
    content_type: str = "application/pdf",
) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=io.BytesIO(content),
        headers={"content-type": content_type},  # type: ignore[arg-type]
    )


@pytest.fixture
def storage_mock():
    mock = MagicMock()
    mock.upload_fileobj.return_value = "https://cdn.example.com/documents/abc.pdf"
    mock._public_url.return_value = "https://cdn.example.com/documents/abc.pdf"
    mock.generate_presigned_url.return_value = "https://presigned.url/abc.pdf"
    return mock


@pytest.fixture
def service(storage_mock):
    settings = _make_settings()
    return FileUploadService(storage=storage_mock, settings=settings)


# ------------------------------------------------------------------
# Tests: folder validation
# ------------------------------------------------------------------


class TestFolderValidation:
    @pytest.mark.asyncio
    async def test_valid_folders(self, service, storage_mock):
        for folder in VALID_FOLDERS:
            ext_map = {
                "documents": ("test.pdf", b"data", "application/pdf"),
                "collection_photos": ("photo.jpg", b"data", "image/jpeg"),
                "signatures": ("sig.png", b"data", "image/png"),
                "reports": ("report.pdf", b"data", "application/pdf"),
            }
            fname, content, ct = ext_map[folder]
            f = _make_upload_file(filename=fname, content=content, content_type=ct)
            url = await service.upload_file(f, folder)
            assert url  # non-empty

    @pytest.mark.asyncio
    async def test_invalid_folder_raises(self, service):
        f = _make_upload_file()
        with pytest.raises(FileUploadError, match="Invalid folder"):
            await service.upload_file(f, "invalid_folder")


# ------------------------------------------------------------------
# Tests: extension validation
# ------------------------------------------------------------------


class TestExtensionValidation:
    @pytest.mark.asyncio
    async def test_disallowed_extension(self, service):
        f = _make_upload_file(filename="hack.exe", content=b"data")
        with pytest.raises(FileUploadError, match="not allowed"):
            await service.upload_file(f, "documents")

    @pytest.mark.asyncio
    async def test_no_extension_raises(self, service):
        f = _make_upload_file(filename="noext", content=b"data")
        with pytest.raises(FileUploadError, match="Cannot determine"):
            await service.upload_file(f, "documents")

    @pytest.mark.asyncio
    async def test_photo_in_documents_rejected(self, service):
        f = _make_upload_file(
            filename="photo.webp", content=b"data", content_type="image/webp"
        )
        with pytest.raises(FileUploadError, match="not allowed"):
            await service.upload_file(f, "documents")


# ------------------------------------------------------------------
# Tests: file size
# ------------------------------------------------------------------


class TestFileSize:
    @pytest.mark.asyncio
    async def test_oversized_file_rejected(self, storage_mock):
        settings = _make_settings(MAX_FILE_SIZE_MB=1)
        svc = FileUploadService(storage=storage_mock, settings=settings)
        big = b"x" * (2 * 1024 * 1024)  # 2MB
        f = _make_upload_file(filename="big.pdf", content=big)
        with pytest.raises(FileUploadError, match="exceeds maximum"):
            await svc.upload_file(f, "documents")

    @pytest.mark.asyncio
    async def test_empty_file_rejected(self, service):
        f = _make_upload_file(filename="empty.pdf", content=b"")
        with pytest.raises(FileUploadError, match="Empty file"):
            await service.upload_file(f, "documents")


# ------------------------------------------------------------------
# Tests: filename generation
# ------------------------------------------------------------------


class TestFilename:
    @pytest.mark.asyncio
    async def test_auto_generated_uuid_filename(self, service, storage_mock):
        f = _make_upload_file()
        await service.upload_file(f, "documents")
        key = storage_mock.upload_fileobj.call_args[0][1]
        assert key.startswith("documents/")
        assert key.endswith(".pdf")
        # UUID hex portion
        stem = key.split("/")[1].replace(".pdf", "")
        assert len(stem) == 16

    @pytest.mark.asyncio
    async def test_custom_filename_preserved(self, service, storage_mock):
        f = _make_upload_file()
        await service.upload_file(f, "documents", filename="my-report")
        key = storage_mock.upload_fileobj.call_args[0][1]
        assert key.startswith("documents/my-report_")
        assert key.endswith(".pdf")

    @pytest.mark.asyncio
    async def test_custom_filename_sanitised(self, service, storage_mock):
        f = _make_upload_file()
        await service.upload_file(f, "documents", filename="bad name!@#.pdf")
        key = storage_mock.upload_fileobj.call_args[0][1]
        name_part = key.split("/")[1]
        # Should not contain special chars except - _ and uuid
        assert "!" not in name_part
        assert "@" not in name_part


# ------------------------------------------------------------------
# Tests: URL generation
# ------------------------------------------------------------------


class TestURLGeneration:
    def test_get_url_delegates(self, service, storage_mock):
        service.get_url("documents/abc.pdf")
        storage_mock._public_url.assert_called_once_with("documents/abc.pdf")

    def test_get_presigned_url(self, service, storage_mock):
        service.get_presigned_url("documents/abc.pdf", expires_in=600)
        storage_mock.generate_presigned_url.assert_called_once_with(
            "documents/abc.pdf", 600
        )

    def test_delete_file(self, service, storage_mock):
        service.delete_file("documents/abc.pdf")
        storage_mock.delete_object.assert_called_once_with("documents/abc.pdf")


# ------------------------------------------------------------------
# Tests: content type resolution
# ------------------------------------------------------------------


class TestContentType:
    @pytest.mark.asyncio
    async def test_content_type_from_upload(self, service, storage_mock):
        f = _make_upload_file(content_type="application/pdf")
        await service.upload_file(f, "documents")
        ct = storage_mock.upload_fileobj.call_args[0][2]
        assert ct == "application/pdf"

    @pytest.mark.asyncio
    async def test_content_type_fallback(self, service, storage_mock):
        f = _make_upload_file(content_type="application/octet-stream")
        await service.upload_file(f, "documents")
        ct = storage_mock.upload_fileobj.call_args[0][2]
        assert ct == "application/pdf"


# ------------------------------------------------------------------
# Tests: singleton
# ------------------------------------------------------------------


class TestSingleton:
    def test_reset_clears_instance(self):
        reset_file_upload_service()
        # Just ensure no error
