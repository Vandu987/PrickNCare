"""Invoice schemas — task 9.5."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class InvoiceCreate(BaseModel):
    client_id: uuid.UUID
    date_from: date
    date_to: date


class InvoiceLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    order_id: uuid.UUID
    description: str
    amount: float


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    invoice_number: str
    date_from: date
    date_to: date
    subtotal: float
    tax_amount: float
    total: float
    status: str
    payment_ref: str | None = None
    generated_at: datetime
    paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    line_items: list[InvoiceLineItemResponse] = []


class InvoiceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    invoice_number: str
    date_from: date
    date_to: date
    subtotal: float
    tax_amount: float
    total: float
    status: str
    payment_ref: str | None = None
    generated_at: datetime
    paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class InvoiceListResponse(BaseModel):
    items: list[InvoiceListItem]
    total: int


class MarkPaidRequest(BaseModel):
    payment_ref: str
