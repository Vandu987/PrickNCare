"""Accessioning schemas — tasks 8.1 & 8.4."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ── Task 8.1 — Pending samples listing ───────────────────────────────────


class PhlebotomistInfo(BaseModel):
    id: uuid.UUID
    name: str
    phone: str

    model_config = ConfigDict(from_attributes=True)


class ClientInfo(BaseModel):
    id: uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class PendingSampleItem(BaseModel):
    order_id: uuid.UUID
    booking_id: str
    patient_name: str
    patient_age: int
    patient_gender: str
    patient_phone: str
    client: ClientInfo
    expected_sample_types: list[str]
    collection_timestamp: datetime | None
    phlebotomist: PhlebotomistInfo | None

    model_config = ConfigDict(from_attributes=True)


class PendingAccessioningResponse(BaseModel):
    total: int
    items: list[PendingSampleItem]


# ── Task 8.4 — Barcode scan / order summary ─────────────────────────────


class OrderTestSummary(BaseModel):
    package_name: str
    package_code: str
    sample_types: list[str]

    model_config = ConfigDict(from_attributes=True)


class SampleAccessioningSummary(BaseModel):
    id: uuid.UUID
    vial_type: str
    quantity: int
    integrity: str
    status: str
    received_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ── Task 8.2 — Accessioning CRUD ─────────────────────────────────────────


class SampleItemCreate(BaseModel):
    vial_type: str
    quantity: int = 1
    integrity: str = "ok"
    status: str = "accepted"
    rejection_reason: str | None = None


class AccessioningCreate(BaseModel):
    samples: list[SampleItemCreate]
    notes: str | None = None


class SampleItemUpdate(BaseModel):
    vial_type: str | None = None
    quantity: int | None = None
    integrity: str | None = None
    status: str | None = None
    rejection_reason: str | None = None
    notes: str | None = None


class AccessioningDetailItem(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    vial_type: str
    quantity: int
    integrity: str
    status: str
    rejection_reason: str | None
    notes: str | None
    accessioned_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccessioningDetailResponse(BaseModel):
    order_id: uuid.UUID
    items: list[AccessioningDetailItem]


class OrderSummaryResponse(BaseModel):
    order_id: uuid.UUID
    booking_id: str
    patient_name: str
    patient_age: int
    patient_gender: str
    client_name: str
    collected_at: datetime | None
    phlebotomist_name: str | None
    ordered_tests: list[OrderTestSummary]
    status: str
    accessioning: list[SampleAccessioningSummary]

    model_config = ConfigDict(from_attributes=True)
