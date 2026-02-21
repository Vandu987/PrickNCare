"""Phlebotomist schemas — task 4.4."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, field_validator


# ── Create / Update ──────────────────────────────────────────────────────


class PhlebotomistCreate(BaseModel):
    name: str
    phone: str
    employee_id: str
    working_hours_start: time | None = None
    working_hours_end: time | None = None

    @field_validator("phone")
    @classmethod
    def validate_indian_phone(cls, v: str) -> str:
        if not re.match(r"^\+91\d{10}$", v):
            raise ValueError("Phone must be in Indian format: +91XXXXXXXXXX")
        return v


class PhlebotomistUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    employee_id: str | None = None
    working_hours_start: time | None = None
    working_hours_end: time | None = None
    is_available: bool | None = None
    bank_account_number: str | None = None
    bank_ifsc: str | None = None
    upi_id: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_indian_phone(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^\+91\d{10}$", v):
            raise ValueError("Phone must be in Indian format: +91XXXXXXXXXX")
        return v


# ── Response ─────────────────────────────────────────────────────────────


class PhlebotomistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    employee_id: str
    name: str
    phone: str
    id_proof_url: str | None = None
    certification_url: str | None = None
    photo_url: str | None = None
    bank_account_number: str | None = None
    bank_ifsc: str | None = None
    upi_id: str | None = None
    working_hours_start: time | None = None
    working_hours_end: time | None = None
    current_location_lat: float | None = None
    current_location_lng: float | None = None
    is_available: bool
    created_at: datetime
    updated_at: datetime


class PhlebotomistListResponse(BaseModel):
    items: list[PhlebotomistResponse]
    total: int
    page: int
    page_size: int


# ── Document schemas ─────────────────────────────────────────────────────


class PhlebotomistDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phlebotomist_id: uuid.UUID
    doc_type: str
    s3_url: str
    original_filename: str
    uploaded_at: datetime
    verified: bool
    verified_by: uuid.UUID | None = None
    verified_at: datetime | None = None


class PhlebotomistDocumentListResponse(BaseModel):
    items: list[PhlebotomistDocumentResponse]
