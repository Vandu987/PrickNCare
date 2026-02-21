"""Client schemas — task 4.1."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.clients import PaymentTerms

# ── Create / Update ──────────────────────────────────────────────────────


class ClientCreate(BaseModel):
    name: str
    gst_number: str | None = None
    address: str | None = None
    city: str | None = None
    pincode: str | None = None
    payment_terms: PaymentTerms = PaymentTerms.PREPAID
    credit_limit: float = 0
    rate_first_collection: float = 0
    rate_second_collection: float = 0
    rate_priority: float = 0


class ClientUpdate(BaseModel):
    name: str | None = None
    gst_number: str | None = None
    address: str | None = None
    city: str | None = None
    pincode: str | None = None
    payment_terms: PaymentTerms | None = None
    credit_limit: float | None = None
    rate_first_collection: float | None = None
    rate_second_collection: float | None = None
    rate_priority: float | None = None
    is_active: bool | None = None


# ── Response ─────────────────────────────────────────────────────────────


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    gst_number: str | None = None
    address: str | None = None
    city: str | None = None
    pincode: str | None = None
    payment_terms: PaymentTerms
    credit_limit: float
    rate_first_collection: float
    rate_second_collection: float
    rate_priority: float
    created_by: uuid.UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    page: int
    page_size: int
