"""Payment schemas — task 9.1."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PaymentCreate(BaseModel):
    amount: float
    mode: str  # cash / upi / card / wallet / postpaid
    transaction_ref: str | None = None
    notes: str | None = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    amount: float
    mode: str
    status: str
    transaction_ref: str | None = None
    collected_by: uuid.UUID
    collected_at: datetime
    created_at: datetime
    updated_at: datetime


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    page: int
    size: int
