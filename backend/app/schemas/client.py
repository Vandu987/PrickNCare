"""Client schemas — task 4.1."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.clients import PaymentTerms


# ── Create / Update ──────────────────────────────────────────────────────

class ClientCreate(BaseModel):
    name: str
    gst_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    payment_terms: PaymentTerms = PaymentTerms.PREPAID
    credit_limit: float = 0
    rate_first_collection: float = 0
    rate_second_collection: float = 0
    rate_priority: float = 0


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    gst_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    payment_terms: Optional[PaymentTerms] = None
    credit_limit: Optional[float] = None
    rate_first_collection: Optional[float] = None
    rate_second_collection: Optional[float] = None
    rate_priority: Optional[float] = None
    is_active: Optional[bool] = None


# ── Response ─────────────────────────────────────────────────────────────

class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    gst_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    payment_terms: PaymentTerms
    credit_limit: float
    rate_first_collection: float
    rate_second_collection: float
    rate_priority: float
    created_by: Optional[uuid.UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    page: int
    page_size: int
