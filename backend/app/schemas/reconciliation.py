"""Reconciliation schemas — task 9.2."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class PhlebotomistSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phlebotomist_id: uuid.UUID
    user_id: uuid.UUID
    name: str

    total_appointments: int
    cash_collected: float
    online_collected: float
    total_collected: float


class PendingReconciliationResponse(BaseModel):
    date: date
    items: list[PhlebotomistSummary]
