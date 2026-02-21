"""File upload, download and delete endpoints — task 15.4."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status

from app.api.deps import get_current_active_user, require_roles
from app.models.users import User
from app.schemas.file import (
    FileDeleteResponse,
    FileDownloadResponse,
    FileUploadResponse,
)
from app.services.file_upload import (
    FileUploadError,
    FileUploadService,
    get_file_upload_service,
)

router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED
)
async def upload_file(
    file: UploadFile,
    folder: str = Query(
        ..., description="Target folder (e.g. documents, collection_photos)"
    ),
    _current_user: User = Depends(get_current_active_user),
    svc: FileUploadService = Depends(get_file_upload_service),
) -> FileUploadResponse:
    """Upload a file to the specified folder. Requires authentication."""
    try:
        url = await svc.upload_file(file, folder)
    except FileUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    # Derive key from URL (folder/filename)
    key = "/".join(url.rstrip("/").split("/")[-2:])
    return FileUploadResponse(url=url, key=key)


@router.get("/download", response_model=FileDownloadResponse)
async def download_file(
    key: str = Query(..., description="Storage key of the file"),
    _current_user: User = Depends(get_current_active_user),
    svc: FileUploadService = Depends(get_file_upload_service),
) -> FileDownloadResponse:
    """Get a pre-signed download URL for the given file key. Requires authentication."""
    try:
        presigned_url = svc.get_presigned_url(key, content_disposition="attachment")
    except FileUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return FileDownloadResponse(presigned_url=presigned_url)


@router.delete(
    "/{key:path}",
    response_model=FileDeleteResponse,
    dependencies=[Depends(require_roles("super_admin"))],
)
async def delete_file(
    key: str,
    svc: FileUploadService = Depends(get_file_upload_service),
) -> FileDeleteResponse:
    """Delete a file by its storage key. SUPER_ADMIN only."""
    svc.delete_file(key)
    return FileDeleteResponse()
