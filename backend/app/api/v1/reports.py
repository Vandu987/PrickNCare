"""Report endpoints — task 14.1."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.orders import Order, OrderStatus
from app.models.users import User
from app.models.zones import Pincode, Zone
from app.schemas.report import DailyCollectionOrderItem, DailyCollectionReport

router = APIRouter(prefix="/reports", tags=["reports"])

_STATUS_MAP = {
    "completed": OrderStatus.COMPLETED,
    "pending": OrderStatus.PENDING,
    "cancelled": OrderStatus.CANCELLED,
    "uncollected": OrderStatus.UNCOLLECTED,
}


@router.get("/daily-collection", response_model=DailyCollectionReport)
async def daily_collection_report(
    date: date = Query(..., description="Report date (YYYY-MM-DD)"),
    city_id: uuid.UUID | None = Query(None, description="Filter by city"),
    zone_id: uuid.UUID | None = Query(None, description="Filter by zone"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin", "city_admin")),
) -> DailyCollectionReport:
    """Return a daily collection report for the given date."""

    stmt = (
        select(Order)
        .options(selectinload(Order.assigned_phlebotomist))
        .where(Order.appointment_date == date)
    )

    # Apply zone/city filters via pincode → zone → city chain
    if zone_id is not None:
        pincode_ids = select(Pincode.id).where(Pincode.zone_id == zone_id)
        stmt = stmt.where(Order.pincode_id.in_(pincode_ids))
    elif city_id is not None:
        zone_ids = select(Zone.id).where(Zone.city_id == city_id)
        pincode_ids = select(Pincode.id).where(Pincode.zone_id.in_(zone_ids))
        stmt = stmt.where(Order.pincode_id.in_(pincode_ids))

    result = await db.execute(stmt)
    orders: list[Order] = list(result.scalars().all())

    # Build counts
    counts: dict[str, int] = {k: 0 for k in _STATUS_MAP}
    for o in orders:
        for key, enum_val in _STATUS_MAP.items():
            if o.status == enum_val:
                counts[key] += 1
                break

    items = [
        DailyCollectionOrderItem(
            order_id=o.id,
            booking_id=o.booking_id,
            patient_name=o.patient_name,
            phlebotomist_name=(
                o.assigned_phlebotomist.name if o.assigned_phlebotomist else None
            ),
            status=o.status.value,
            appointment_date=o.appointment_date,
            created_at=o.created_at,
        )
        for o in orders
    ]

    return DailyCollectionReport(
        date=date,
        total_orders=len(orders),
        completed=counts["completed"],
        pending=counts["pending"],
        cancelled=counts["cancelled"],
        uncollected=counts["uncollected"],
        orders=items,
    )
