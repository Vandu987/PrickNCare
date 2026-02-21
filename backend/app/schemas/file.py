"""Pydantic schemas for file upload/download — task 15.4."""

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    url: str = Field(..., description="Public URL of the uploaded file")
    key: str = Field(..., description="Storage key for future reference")


class FileDownloadResponse(BaseModel):
    presigned_url: str = Field(
        ..., description="Pre-signed URL for downloading the file"
    )


class FileDeleteResponse(BaseModel):
    detail: str = "File deleted successfully"
