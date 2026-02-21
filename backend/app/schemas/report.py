"""Report schemas — task 14.1."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class DailyCollectionOrderItem(BaseModel):
    """Single order row inside the daily collection report."""

    order_id: uuid.UUID
    booking_id: str
    patient_name: str
    phlebotomist_name: str | None = None
    status: str
    appointment_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class DailyCollectionReport(BaseModel):
    """Aggregated daily collection report."""

    date: date
    total_orders: int = 0
    completed: int = 0
    pending: int = 0
    cancelled: int = 0
    uncollected: int = 0
    orders: list[DailyCollectionOrderItem] = Field(default_factory=list)
