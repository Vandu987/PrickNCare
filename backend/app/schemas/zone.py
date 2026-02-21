"""Zone-related schemas — task 5.1 (cities only)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

# ── City schemas ─────────────────────────────────────────────────────────


class CityCreate(BaseModel):
    name: str
    state: str


class CityUpdate(BaseModel):
    name: str | None = None
    state: str | None = None


class CityServiceableUpdate(BaseModel):
    is_serviceable: bool


class CityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    state: str
    is_serviceable: bool
    created_at: datetime
    updated_at: datetime


class CityListResponse(BaseModel):
    items: list[CityResponse]
    total: int


# ── Zone schemas ─────────────────────────────────────────────────────────


class ZoneCreate(BaseModel):
    name: str
    city_id: uuid.UUID


class ZoneUpdate(BaseModel):
    name: str | None = None
    city_id: uuid.UUID | None = None


class ZoneActiveUpdate(BaseModel):
    is_active: bool


class ZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    city_id: uuid.UUID
    city_name: str
    is_active: bool
    pincode_count: int
    created_at: datetime
    updated_at: datetime


class ZoneListResponse(BaseModel):
    items: list[ZoneResponse]
    total: int


# ── Pincode schemas ──────────────────────────────────────────────────────


class PincodeCreate(BaseModel):
    pincode: str
    zone_id: uuid.UUID

    @field_validator("pincode")
    @classmethod
    def validate_pincode_format(cls, v: str) -> str:
        import re

        if not re.fullmatch(r"\d{6}", v):
            raise ValueError("Pincode must be exactly 6 digits")
        return v


class BulkPincodeCreate(BaseModel):
    pincodes: list[PincodeCreate]


class PincodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pincode: str
    zone_id: uuid.UUID
    zone_name: str
    created_at: datetime


class PincodeListResponse(BaseModel):
    items: list[PincodeResponse]
    total: int


class PincodeSuggestion(BaseModel):
    id: uuid.UUID
    pincode: str
    zone_name: str
    city_name: str


class PincodeZoneUpdate(BaseModel):
    zone_id: uuid.UUID


class ImportSummaryResponse(BaseModel):
    total_rows: int
    created: int
    errors: int
    error_details: list[str]


# ── Locality schemas ─────────────────────────────────────────────────────


class LocalityCreate(BaseModel):
    name: str
    pincode_id: uuid.UUID


class BulkLocalityCreate(BaseModel):
    localities: list[LocalityCreate]


class LocalityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    pincode_id: uuid.UUID
    pincode: str
    zone_name: str


class LocalityListResponse(BaseModel):
    items: list[LocalityResponse]
    total: int


# ── NSA / Service Availability schemas — task 5.5 ───────────────────────


class ServiceAvailability(BaseModel):
    is_serviceable: bool
    zone_name: str | None = None
    city_name: str | None = None
    available_phlebotomists: int = 0
    nsa_reason: str | None = None


class NSAMarkRequest(BaseModel):
    pincode: str
    reason: str | None = None

    @field_validator("pincode")
    @classmethod
    def validate_pincode_format(cls, v: str) -> str:
        import re

        if not re.fullmatch(r"\d{6}", v):
            raise ValueError("Pincode must be exactly 6 digits")
        return v


class NSARecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pincode: str
    reason: str | None
    marked_at: datetime
    marked_by: uuid.UUID | None
    is_active: bool


class NSAListResponse(BaseModel):
    items: list[NSARecordResponse]
    total: int
