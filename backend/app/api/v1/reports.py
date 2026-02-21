"""Report endpoints — tasks 14.1, 14.2 & 14.3."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.clients import Client, PaymentTerms
from app.models.orders import Order, OrderStatus
from app.models.payments import Payment
from app.models.phlebotomists import Phlebotomist, PhlebotomistZoneAssignment
from app.models.users import User
from app.models.zones import Pincode, Zone
from app.schemas.report import (
    ClientWiseReport,
    ClientWiseReportItem,
    DailyCollectionOrderItem,
    DailyCollectionReport,
    PhlebotomistPerformanceItem,
    PhlebotomistPerformanceReport,
    ZoneWiseReport,
    ZoneWiseReportItem,
)

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


@router.get("/phlebotomist-performance", response_model=PhlebotomistPerformanceReport)
async def phlebotomist_performance_report(
    date_from: date = Query(..., description="Start date (inclusive)"),
    date_to: date = Query(..., description="End date (inclusive)"),
    phlebotomist_id: uuid.UUID | None = Query(
        None, description="Filter by phlebotomist"
    ),
    city_id: uuid.UUID | None = Query(None, description="Filter by city"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin", "city_admin")),
) -> PhlebotomistPerformanceReport:
    """Return performance metrics per phlebotomist for a date range."""

    # Base filter: orders in date range with an assigned phlebotomist
    order_filter = [
        Order.appointment_date >= date_from,
        Order.appointment_date <= date_to,
        Order.assigned_phlebotomist_id.isnot(None),
    ]

    if phlebotomist_id is not None:
        order_filter.append(Order.assigned_phlebotomist_id == phlebotomist_id)

    if city_id is not None:
        zone_ids = select(Zone.id).where(Zone.city_id == city_id)
        pincode_ids = select(Pincode.id).where(Pincode.zone_id.in_(zone_ids))
        order_filter.append(Order.pincode_id.in_(pincode_ids))

    # 1) Aggregate counts per phlebotomist
    count_stmt = (
        select(
            Order.assigned_phlebotomist_id,
            func.count(Order.id).label("total"),
            func.count(Order.id)
            .filter(Order.status.in_([OrderStatus.COMPLETED, OrderStatus.COLLECTED]))
            .label("completed"),
        )
        .where(*order_filter)
        .group_by(Order.assigned_phlebotomist_id)
    )
    count_rows = (await db.execute(count_stmt)).all()

    if not count_rows:
        return PhlebotomistPerformanceReport(
            date_from=date_from, date_to=date_to, phlebotomists=[]
        )

    phleb_ids = [r[0] for r in count_rows]
    counts_map: dict[uuid.UUID, dict] = {
        r[0]: {"total": r[1], "completed": r[2]} for r in count_rows
    }

    # 2) Phlebotomist names
    phleb_stmt = select(Phlebotomist.id, Phlebotomist.name).where(
        Phlebotomist.id.in_(phleb_ids)
    )
    phleb_rows = (await db.execute(phleb_stmt)).all()
    name_map = {r[0]: r[1] for r in phleb_rows}

    # 3) Average TAT: assigned_at → collected_at on orders
    tat_stmt = (
        select(
            Order.assigned_phlebotomist_id,
            func.avg(
                func.extract("epoch", Order.collected_at)
                - func.extract("epoch", Order.assigned_at)
            ).label("avg_tat_seconds"),
        )
        .where(
            *order_filter,
            Order.assigned_at.isnot(None),
            Order.collected_at.isnot(None),
        )
        .group_by(Order.assigned_phlebotomist_id)
    )
    tat_rows = (await db.execute(tat_stmt)).all()
    tat_map: dict[uuid.UUID, float | None] = {r[0]: r[1] for r in tat_rows}

    # 4) Earnings: sum of payments collected by each phlebotomist's user
    # Map phlebotomist_id → user_id
    phleb_user_stmt = select(Phlebotomist.id, Phlebotomist.user_id).where(
        Phlebotomist.id.in_(phleb_ids)
    )
    phleb_user_rows = (await db.execute(phleb_user_stmt)).all()
    phleb_to_user = {r[0]: r[1] for r in phleb_user_rows}
    user_to_phleb = {v: k for k, v in phleb_to_user.items()}
    user_ids = list(user_to_phleb.keys())

    earnings_map: dict[uuid.UUID, Decimal] = {}
    if user_ids:
        # Join Payment with Order to respect date range
        earnings_stmt = (
            select(
                Payment.collected_by,
                func.sum(Payment.amount).label("total_earnings"),
            )
            .join(Order, Payment.order_id == Order.id)
            .where(
                Payment.collected_by.in_(user_ids),
                Order.appointment_date >= date_from,
                Order.appointment_date <= date_to,
            )
            .group_by(Payment.collected_by)
        )
        earnings_rows = (await db.execute(earnings_stmt)).all()
        for row in earnings_rows:
            pid = user_to_phleb.get(row[0])
            if pid:
                earnings_map[pid] = row[1] or Decimal(0)

    # Build response
    items = []
    for pid in phleb_ids:
        c = counts_map[pid]
        total = c["total"]
        completed = c["completed"]
        rate = round((completed / total) * 100, 2) if total > 0 else 0.0
        avg_tat = tat_map.get(pid)
        avg_tat_min = round(avg_tat / 60, 2) if avg_tat is not None else None
        items.append(
            PhlebotomistPerformanceItem(
                phlebotomist_id=pid,
                phlebotomist_name=name_map.get(pid, "Unknown"),
                total_collections=total,
                completed=completed,
                success_rate=rate,
                average_tat_minutes=avg_tat_min,
                earnings=float(earnings_map.get(pid, Decimal(0))),
            )
        )

    return PhlebotomistPerformanceReport(
        date_from=date_from,
        date_to=date_to,
        phlebotomists=items,
    )


# ---------------------------------------------------------------------------
# Task 14.3 — Client-wise report
# ---------------------------------------------------------------------------


@router.get("/client-wise", response_model=ClientWiseReport)
async def client_wise_report(
    date_from: date = Query(..., description="Start date (inclusive)"),
    date_to: date = Query(..., description="End date (inclusive)"),
    client_id: uuid.UUID | None = Query(None, description="Filter by client"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin", "city_admin")),
) -> ClientWiseReport:
    """Per-client aggregated report over a date range."""

    # Base order filter
    base = (
        select(Order)
        .where(Order.appointment_date >= date_from)
        .where(Order.appointment_date <= date_to)
    )
    if client_id is not None:
        base = base.where(Order.client_id == client_id)

    result = await db.execute(base)
    orders: list[Order] = list(result.scalars().all())

    # Load clients we need
    client_ids = {o.client_id for o in orders}
    if client_id is not None:
        client_ids.add(client_id)

    clients_map: dict[uuid.UUID, Client] = {}
    if client_ids:
        res = await db.execute(select(Client).where(Client.id.in_(client_ids)))
        for c in res.scalars().all():
            clients_map[c.id] = c

    # Aggregate per client
    agg: dict[uuid.UUID, dict] = {}
    for o in orders:
        bucket = agg.setdefault(
            o.client_id,
            {
                "total_orders": 0,
                "completed": 0,
                "cancelled": 0,
                "rejected_samples": 0,
                "total_revenue": 0.0,
            },
        )
        bucket["total_orders"] += 1
        if o.status == OrderStatus.COMPLETED:
            bucket["completed"] += 1
            bucket["total_revenue"] += float(o.amount)
        elif o.status == OrderStatus.CANCELLED:
            bucket["cancelled"] += 1
        elif o.status == OrderStatus.SAMPLE_REJECTED:
            bucket["rejected_samples"] += 1

    # Outstanding = sum(amount) for postpaid clients where payment_status != 'paid'
    # across orders in the date range
    outstanding: dict[uuid.UUID, float] = {}
    for o in orders:
        cl = clients_map.get(o.client_id)
        if cl and cl.payment_terms == PaymentTerms.POSTPAID:
            if o.payment_status.value != "paid":
                outstanding[o.client_id] = outstanding.get(o.client_id, 0.0) + float(
                    o.amount
                )

    items: list[ClientWiseReportItem] = []
    for cid in sorted(agg, key=lambda x: str(x)):
        cl = clients_map.get(cid)
        bucket = agg[cid]
        items.append(
            ClientWiseReportItem(
                client_id=cid,
                client_name=cl.name if cl else "Unknown",
                payment_terms=cl.payment_terms.value if cl else "unknown",
                total_orders=bucket["total_orders"],
                completed=bucket["completed"],
                cancelled=bucket["cancelled"],
                rejected_samples=bucket["rejected_samples"],
                total_revenue=bucket["total_revenue"],
                outstanding_amount=outstanding.get(cid, 0.0),
            )
        )

    return ClientWiseReport(date_from=date_from, date_to=date_to, items=items)


# ---------------------------------------------------------------------------
# Task 14.3 — Zone-wise report
# ---------------------------------------------------------------------------


@router.get("/zone-wise", response_model=ZoneWiseReport)
async def zone_wise_report(
    date_from: date = Query(..., description="Start date (inclusive)"),
    date_to: date = Query(..., description="End date (inclusive)"),
    city_id: uuid.UUID | None = Query(None, description="Filter by city"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin", "city_admin")),
) -> ZoneWiseReport:
    """Per-zone aggregated report over a date range."""

    # Load zones (optionally filtered by city)
    zone_stmt = select(Zone)
    if city_id is not None:
        zone_stmt = zone_stmt.where(Zone.city_id == city_id)
    zone_res = await db.execute(zone_stmt)
    zones: list[Zone] = list(zone_res.scalars().all())
    zone_map = {z.id: z for z in zones}

    if not zone_map:
        return ZoneWiseReport(date_from=date_from, date_to=date_to, items=[])

    # Pincode → zone mapping
    pin_stmt = select(Pincode).where(Pincode.zone_id.in_(zone_map.keys()))
    pin_res = await db.execute(pin_stmt)
    pincodes = list(pin_res.scalars().all())
    pin_to_zone: dict[uuid.UUID, uuid.UUID] = {p.id: p.zone_id for p in pincodes}

    # Orders in date range for these pincodes
    order_stmt = (
        select(Order)
        .where(Order.appointment_date >= date_from)
        .where(Order.appointment_date <= date_to)
        .where(Order.pincode_id.in_(pin_to_zone.keys()))
    )
    order_res = await db.execute(order_stmt)
    orders: list[Order] = list(order_res.scalars().all())

    # Aggregate per zone
    agg: dict[uuid.UUID, dict] = {
        zid: {
            "total_orders": 0,
            "completed": 0,
            "cancelled": 0,
            "tat_sum": 0.0,
            "tat_count": 0,
        }
        for zid in zone_map
    }
    for o in orders:
        zid = pin_to_zone.get(o.pincode_id)
        if zid is None or zid not in agg:
            continue
        bucket = agg[zid]
        bucket["total_orders"] += 1
        if o.status == OrderStatus.COMPLETED:
            bucket["completed"] += 1
            # TAT: assigned_at → collected_at
            if o.assigned_at and o.collected_at:
                tat_seconds = (o.collected_at - o.assigned_at).total_seconds()
                bucket["tat_sum"] += tat_seconds
                bucket["tat_count"] += 1
        elif o.status == OrderStatus.CANCELLED:
            bucket["cancelled"] += 1

    # Active phlebotomists per zone
    phleb_stmt = (
        select(
            PhlebotomistZoneAssignment.zone_id,
            func.count(PhlebotomistZoneAssignment.phlebotomist_id.distinct()),
        )
        .where(PhlebotomistZoneAssignment.zone_id.in_(zone_map.keys()))
        .group_by(PhlebotomistZoneAssignment.zone_id)
    )
    phleb_res = await db.execute(phleb_stmt)
    phleb_counts: dict[uuid.UUID, int] = dict(phleb_res.all())

    items: list[ZoneWiseReportItem] = []
    for zid, z in sorted(zone_map.items(), key=lambda x: x[1].name):
        bucket = agg[zid]
        avg_tat = None
        if bucket["tat_count"] > 0:
            avg_tat = round(bucket["tat_sum"] / bucket["tat_count"] / 60, 2)
        items.append(
            ZoneWiseReportItem(
                zone_id=zid,
                zone_name=z.name,
                city_id=z.city_id,
                total_orders=bucket["total_orders"],
                completed=bucket["completed"],
                cancelled=bucket["cancelled"],
                active_phlebotomists=phleb_counts.get(zid, 0),
                avg_tat=avg_tat,
            )
        )

    return ZoneWiseReport(date_from=date_from, date_to=date_to, items=items)
