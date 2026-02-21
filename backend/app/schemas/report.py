"""Report schemas — tasks 14.1, 14.2 & 14.3."""

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


# --- Task 14.3: Client-wise and Zone-wise report schemas ---


class ClientWiseReportItem(BaseModel):
    """Single row in the client-wise report."""

    client_id: uuid.UUID
    client_name: str
    payment_terms: str
    total_orders: int = 0
    completed: int = 0
    cancelled: int = 0
    rejected_samples: int = 0
    total_revenue: float = 0.0
    outstanding_amount: float = 0.0

    model_config = {"from_attributes": True}


class ClientWiseReport(BaseModel):
    """Aggregated client-wise report."""

    date_from: date
    date_to: date
    items: list[ClientWiseReportItem] = Field(default_factory=list)


class ZoneWiseReportItem(BaseModel):
    """Single row in the zone-wise report."""

    zone_id: uuid.UUID
    zone_name: str
    city_id: uuid.UUID
    total_orders: int = 0
    completed: int = 0
    cancelled: int = 0
    active_phlebotomists: int = 0
    avg_tat: float | None = None

    model_config = {"from_attributes": True}


class ZoneWiseReport(BaseModel):
    """Aggregated zone-wise report."""

    date_from: date
    date_to: date
    items: list[ZoneWiseReportItem] = Field(default_factory=list)


# ── Task 14.2: Phlebotomist Performance Report ──────────────────────────


# ── Task 14.4: Revenue & TAT Analysis report schemas ────────────────────


class RevenueDataPoint(BaseModel):
    """Single time-series data point for revenue report."""

    period: str = Field(..., description="Period label (date or week/month range)")
    total_revenue: float = 0.0
    order_count: int = 0
    avg_order_value: float = 0.0


class RevenueReport(BaseModel):
    """Time-series revenue report."""

    date_from: date
    date_to: date
    group_by: str
    data: list[RevenueDataPoint] = Field(default_factory=list)


class TATByPriority(BaseModel):
    """TAT breakdown for a single priority level."""

    priority: str
    avg_assignment_to_collection_minutes: float | None = None
    avg_collection_to_accessioning_minutes: float | None = None
    order_count: int = 0


class TATAnalysisReport(BaseModel):
    """TAT analysis report."""

    date_from: date
    date_to: date
    avg_assignment_to_collection_minutes: float | None = None
    avg_collection_to_accessioning_minutes: float | None = None
    percentile_95_assignment_to_collection_minutes: float | None = None
    by_priority: list[TATByPriority] = Field(default_factory=list)


class PhlebotomistPerformanceItem(BaseModel):
    """Performance metrics for a single phlebotomist."""

    phlebotomist_id: uuid.UUID
    phlebotomist_name: str
    total_collections: int = 0
    completed: int = 0
    success_rate: float = Field(0.0, description="Success rate as percentage")
    average_tat_minutes: float | None = Field(
        None, description="Average turnaround time (assigned → collected) in minutes"
    )
    earnings: float = Field(0.0, description="Total earnings in the period")

    model_config = {"from_attributes": True}


class PhlebotomistPerformanceReport(BaseModel):
    """Aggregated phlebotomist performance report."""

    date_from: date
    date_to: date
    phlebotomists: list[PhlebotomistPerformanceItem] = Field(default_factory=list)
