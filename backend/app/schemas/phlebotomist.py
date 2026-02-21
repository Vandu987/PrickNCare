"""Phlebotomist schemas — tasks 4.4 & 4.5."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, time
from typing import Literal

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


# ── Zone assignment schemas — task 4.5 ───────────────────────────────────


class ZoneAssignmentUpdate(BaseModel):
    zone_ids: list[uuid.UUID]


class ZoneAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    zone_id: uuid.UUID
    assigned_at: datetime | None = None


# ── Leave schemas — task 4.5 ─────────────────────────────────────────────


class LeaveRequest(BaseModel):
    date: date
    reason: str
    leave_type: Literal["full_day", "half_day"]

    @field_validator("date")
    @classmethod
    def date_must_be_future(cls, v: date) -> date:
        if v <= date.today():
            raise ValueError("Leave date must be in the future")
        return v


class LeaveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phlebotomist_id: uuid.UUID
    date: date
    reason: str | None = None
    leave_type: str
    status: str
    approved_by: uuid.UUID | None = None
    created_at: datetime


class LeaveListResponse(BaseModel):
    items: list[LeaveResponse]
    total: int


# ── Bank details schemas — task 4.5 ──────────────────────────────────────


class BankDetailsUpdate(BaseModel):
    account_number: str | None = None
    ifsc: str | None = None
    bank_name: str | None = None
    upi_id: str | None = None

    @field_validator("ifsc")
    @classmethod
    def validate_ifsc(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", v):
            raise ValueError("IFSC must match format: ^[A-Z]{4}0[A-Z0-9]{6}$")
        return v


class BankDetailsResponse(BaseModel):
    account_number: str | None = None
    ifsc: str | None = None
    bank_name: str | None = None
    upi_id: str | None = None


# ── Availability schema — task 4.5 ───────────────────────────────────────


class AvailabilityUpdate(BaseModel):
    is_available: bool
