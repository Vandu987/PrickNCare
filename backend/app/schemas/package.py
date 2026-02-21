"""Package schemas — task 7.1."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.packages import SampleType


class PackageCreate(BaseModel):
    name: str
    code: str
    description: str | None = None
    preparation_instructions: str | None = None
    tat_hours: int = 24
    sample_types: list[SampleType] = []
    base_price: float = 0


class PackageUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    preparation_instructions: str | None = None
    tat_hours: int | None = None
    sample_types: list[SampleType] | None = None
    base_price: float | None = None
    is_active: bool | None = None


class PackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    description: str | None = None
    preparation_instructions: str | None = None
    tat_hours: int
    sample_types: list[str]
    base_price: float
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PackageListResponse(BaseModel):
    items: list[PackageResponse]
    total: int
    page: int
    page_size: int


class BulkImportError(BaseModel):
    row: int
    field: str
    message: str


class BulkImportResult(BaseModel):
    total_rows: int
    successful: int
    failed: int
    errors: list[BulkImportError]
