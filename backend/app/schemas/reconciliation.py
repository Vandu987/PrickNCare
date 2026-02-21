"""Reconciliation schemas — tasks 9.2 & 9.3."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

# ── Task 9.2 schemas ──────────────────────────────────────────────────


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


# ── Task 9.3 schemas ──────────────────────────────────────────────────


class DiscrepancyItem(BaseModel):
    type: str  # DiscrepancyCategory value
    amount: float
    notes: str | None = None


class ReconciliationCreate(BaseModel):
    phlebotomist_id: uuid.UUID
    date: date
    cash_handed_over: float
    discrepancies: list[DiscrepancyItem] = []


class DiscrepancyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    amount: float
    notes: str | None = None


class ReconciliationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phlebotomist_id: uuid.UUID
    date: date
    expected_cash: float
    cash_handed_over: float
    net_discrepancy: float
    status: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    discrepancies: list[DiscrepancyResponse] = []


class ReconciliationUpdate(BaseModel):
    cash_handed_over: float | None = None
    status: str | None = None
    discrepancies: list[DiscrepancyItem] | None = None
