"""Client schemas — tasks 4.1 & 4.2."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

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


# ── Rate schemas (task 4.2) ──────────────────────────────────────────────


# ── ClientUser schemas (task 4.3) ────────────────────────────────────────


class ClientUserCreate(BaseModel):
    email: str
    phone: str
    is_primary: bool = False


class ClientUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    user_id: uuid.UUID
    is_primary: bool
    email: str
    phone: str
    is_active: bool


class ClientUserListResponse(BaseModel):
    items: list[ClientUserResponse]
    total: int
    page: int
    page_size: int


# ── Rate schemas (task 4.2) ──────────────────────────────────────────────


class ClientRateUpdate(BaseModel):
    rate_first_collection: Decimal | None = None
    rate_second_collection: Decimal | None = None
    rate_priority: Decimal | None = None
    credit_limit: Decimal | None = None

    @field_validator(
        "rate_first_collection",
        "rate_second_collection",
        "rate_priority",
        "credit_limit",
        mode="before",
    )
    @classmethod
    def validate_rate(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        v = Decimal(str(v))
        if v <= 0:
            raise ValueError("Value must be greater than 0")
        if v.as_tuple().exponent is not None and abs(int(v.as_tuple().exponent)) > 2:
            raise ValueError("Maximum 2 decimal places allowed")
        return v


class ClientRateHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    field_name: str
    previous_value: float
    new_value: float
    effective_date: datetime
    changed_by: uuid.UUID


class ClientRateHistoryListResponse(BaseModel):
    items: list[ClientRateHistoryResponse]
    total: int
    page: int
    page_size: int
