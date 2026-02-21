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
    submitted_cash: float | None = None
    submitted_notes: str | None = None
    net_discrepancy: float
    status: str
    created_by: uuid.UUID
    verified_by: uuid.UUID | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    discrepancies: list[DiscrepancyResponse] = []


class ReconciliationUpdate(BaseModel):
    cash_handed_over: float | None = None
    status: str | None = None
    discrepancies: list[DiscrepancyItem] | None = None


# ── Task 9.4 schemas ──────────────────────────────────────────────────


class CashSubmissionCreate(BaseModel):
    total_cash: float
    notes: str | None = None


class CashSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phlebotomist_id: uuid.UUID
    date: date
    expected_cash: float
    submitted_cash: float | None = None
    submitted_notes: str | None = None
    submitted_at: datetime | None = None
    status: str


class ReconciliationReportResponse(BaseModel):
    date_from: date
    date_to: date
    total_cash_collected: float
    total_handed_over: float
    discrepancies_by_type: dict[str, float]
    outstanding_dues: float
    total_online_collected: float
    reconciliation_count: int
    pending_count: int


class ReconciliationVerifyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phlebotomist_id: uuid.UUID
    date: date
    expected_cash: float
    cash_handed_over: float
    submitted_cash: float | None = None
    submitted_notes: str | None = None
    net_discrepancy: float
    status: str
    created_by: uuid.UUID
    verified_by: uuid.UUID | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    discrepancies: list[DiscrepancyResponse] = []
