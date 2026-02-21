"""File upload service with folder organization and CloudFront URL generation."""

from __future__ import annotations

import logging
import mimetypes
import uuid
from pathlib import PurePosixPath

from fastapi import UploadFile

from app.core.config import Settings, get_settings
from app.core.storage import S3Storage, get_storage

logger = logging.getLogger(__name__)

# Valid folder names
VALID_FOLDERS = frozenset({"documents", "collection_photos", "signatures", "reports"})

# MIME types mapped from common extensions
_MIME_MAP: dict[str, str] = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


class FileUploadError(Exception):
    """Raised for file upload validation / processing errors."""


class FileUploadService:
    """Handles file uploads with validation, folder organization, and URL generation."""

    def __init__(
        self,
        storage: S3Storage | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._storage = storage or get_storage()
        self._settings = settings or get_settings()
        self._allowed_extensions = self._build_allowed_extensions()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def upload_file(
        self,
        file: UploadFile,
        folder: str,
        filename: str | None = None,
    ) -> str:
        """Upload a file to the given folder. Returns the public URL.

        Args:
            file: FastAPI UploadFile instance.
            folder: One of VALID_FOLDERS.
            filename: Optional custom filename (extension preserved from original).

        Returns:
            Public (CloudFront/S3/local) URL of the uploaded file.

        Raises:
            FileUploadError: On validation failure.
        """
        self._validate_folder(folder)
        ext = self._extract_extension(file.filename or "")
        self._validate_extension(ext, folder)
        await self._validate_file_size(file)

        safe_name = self._build_filename(filename, ext)
        key = str(PurePosixPath(folder) / safe_name)
        content_type = self._resolve_content_type(ext, file.content_type)

        logger.info("Uploading file: key=%s content_type=%s", key, content_type)

        url = self._storage.upload_fileobj(file.file, key, content_type)
        return url

    def get_url(self, key: str) -> str:
        """Return the public URL for an existing key (CloudFront when available)."""
        return self._storage._public_url(key)

    def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        content_disposition: str | None = None,
        validate_exists: bool = True,
    ) -> str:
        """Return a pre-signed URL for private access.

        Args:
            key: S3 object key.
            expires_in: Expiration in seconds (default 3600 = 1 hour).
            content_disposition: ``"inline"``, ``"attachment"``, or a full
                header value like ``"attachment; filename=report.pdf"``.
                Shorthand values ``"inline"`` and ``"attachment"`` are
                expanded automatically.
            validate_exists: When *True* (default), verify the object exists
                before generating a URL.

        Raises:
            FileUploadError: If *validate_exists* is True and the key is missing.
        """
        if validate_exists and not self._storage.object_exists(key):
            raise FileUploadError(f"Object not found: {key}")

        # Expand shorthand disposition values
        disposition = content_disposition
        if disposition in ("inline", "attachment"):
            # Extract filename from key for attachment header
            filename = PurePosixPath(key).name
            if disposition == "attachment":
                disposition = f'attachment; filename="{filename}"'
            # "inline" stays as-is (browsers handle it)

        return self._storage.generate_presigned_url(
            key, expires_in=expires_in, content_disposition=disposition
        )

    def delete_file(self, key: str) -> None:
        """Delete a file by its storage key."""
        self._storage.delete_object(key)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_folder(self, folder: str) -> None:
        if folder not in VALID_FOLDERS:
            raise FileUploadError(
                f"Invalid folder '{folder}'. Must be one of: {sorted(VALID_FOLDERS)}"
            )

    def _validate_extension(self, ext: str, folder: str) -> None:
        allowed = self._allowed_extensions.get(folder, set())
        if ext.lower() not in allowed:
            raise FileUploadError(
                f"File extension '{ext}' not allowed in folder '{folder}'. "
                f"Allowed: {sorted(allowed)}"
            )

    async def _validate_file_size(self, file: UploadFile) -> None:
        max_bytes = self._settings.MAX_FILE_SIZE_MB * 1024 * 1024
        # Read content to check size (seek back after)
        content = await file.read()
        size = len(content)
        await file.seek(0)
        if size > max_bytes:
            raise FileUploadError(
                f"File size ({size} bytes) exceeds maximum "
                f"({self._settings.MAX_FILE_SIZE_MB} MB)."
            )
        if size == 0:
            raise FileUploadError("Empty file is not allowed.")

    # ------------------------------------------------------------------
    # Filename helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_extension(original_filename: str) -> str:
        suffix = PurePosixPath(original_filename).suffix
        if not suffix:
            raise FileUploadError(
                "Cannot determine file extension from the uploaded file."
            )
        return suffix.lower()  # e.g. ".pdf"

    @staticmethod
    def _build_filename(custom_name: str | None, ext: str) -> str:
        unique = uuid.uuid4().hex[:16]
        if custom_name:
            # Strip any existing extension from the custom name
            stem = PurePosixPath(custom_name).stem
            # Sanitise: keep only alnum, dash, underscore
            safe_stem = "".join(c if (c.isalnum() or c in "-_") else "_" for c in stem)
            return f"{safe_stem}_{unique}{ext}"
        return f"{unique}{ext}"

    @staticmethod
    def _resolve_content_type(ext: str, upload_content_type: str | None) -> str:
        if upload_content_type and upload_content_type != "application/octet-stream":
            return upload_content_type
        return _MIME_MAP.get(
            ext, mimetypes.guess_type(f"file{ext}")[0] or "application/octet-stream"
        )

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def _build_allowed_extensions(self) -> dict[str, set[str]]:
        def _parse(raw: str) -> set[str]:
            return {f".{e.strip().lower()}" for e in raw.split(",") if e.strip()}

        return {
            "documents": _parse(self._settings.ALLOWED_EXTENSIONS_DOCUMENTS),
            "collection_photos": _parse(
                self._settings.ALLOWED_EXTENSIONS_COLLECTION_PHOTOS
            ),
            "signatures": _parse(self._settings.ALLOWED_EXTENSIONS_SIGNATURES),
            "reports": _parse(self._settings.ALLOWED_EXTENSIONS_REPORTS),
        }


# ------------------------------------------------------------------
# Singleton / FastAPI dependency
# ------------------------------------------------------------------

_service_instance: FileUploadService | None = None


def get_file_upload_service() -> FileUploadService:
    global _service_instance
    if _service_instance is None:
        _service_instance = FileUploadService()
    return _service_instance


def reset_file_upload_service() -> None:
    global _service_instance
    _service_instance = None
