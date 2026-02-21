"""Accessioning endpoints — tasks 8.1 & 8.4."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import RoleChecker, require_roles
from app.core.database import get_db
from app.models.orders import Order, OrderStatus
from app.models.packages import OrderPackage
from app.models.samples import SampleAccessioning
from app.models.users import User
from app.schemas.accessioning import (
    ClientInfo,
    OrderSummaryResponse,
    OrderTestSummary,
    PendingAccessioningResponse,
    PendingSampleItem,
    PhlebotomistInfo,
    SampleAccessioningSummary,
)

router = APIRouter(prefix="/accessioning", tags=["accessioning"])

_admin_only = RoleChecker("super_admin", "city_admin")


# ── Task 8.1 — Pending samples listing ──────────────────────────────────


@router.get("/pending", response_model=PendingAccessioningResponse)
async def list_pending_samples(
    collection_date: date | None = Query(None, description="Filter by collection date"),
    phlebotomist_id: uuid.UUID | None = Query(
        None, description="Filter by phlebotomist"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(_admin_only),
    db: AsyncSession = Depends(get_db),
) -> PendingAccessioningResponse:
    """List orders with status=COLLECTED that have no accessioning records."""

    # Base filter
    base = select(Order).where(
        Order.status == OrderStatus.COLLECTED,
        Order.id.notin_(select(SampleAccessioning.order_id).distinct()),
    )

    if collection_date is not None:
        base = base.where(func.date(Order.collected_at) == collection_date)

    if phlebotomist_id is not None:
        base = base.where(Order.assigned_phlebotomist_id == phlebotomist_id)

    # Count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Fetch with eager loads
    rows_q = (
        base.options(
            selectinload(Order.client),
            selectinload(Order.assigned_phlebotomist),
            selectinload(Order.packages).selectinload(OrderPackage.package),
        )
        .order_by(Order.collected_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(rows_q)
    orders = result.scalars().unique().all()

    items: list[PendingSampleItem] = []
    for order in orders:
        # Collect sample types from all packages
        sample_types: list[str] = []
        for op in order.packages:
            if op.package and op.package.sample_types:
                sample_types.extend(op.package.sample_types)
        sample_types = sorted(set(sample_types))

        phleb_info = None
        if order.assigned_phlebotomist:
            p = order.assigned_phlebotomist
            phleb_info = PhlebotomistInfo(id=p.id, name=p.name, phone=p.phone)

        items.append(
            PendingSampleItem(
                order_id=order.id,
                booking_id=order.booking_id,
                patient_name=order.patient_name,
                patient_age=order.patient_age,
                patient_gender=order.patient_gender.value,
                patient_phone=order.patient_phone,
                client=ClientInfo(id=order.client.id, name=order.client.name),
                expected_sample_types=sample_types,
                collection_timestamp=order.collected_at,
                phlebotomist=phleb_info,
            )
        )

    return PendingAccessioningResponse(total=total, items=items)


# ── Task 8.4 — Barcode scan ─────────────────────────────────────────────


@router.get("/scan/{barcode}", response_model=list[OrderSummaryResponse])
async def scan_barcode(
    barcode: str,
    user: User = Depends(require_roles("super_admin", "city_admin")),
    db: AsyncSession = Depends(get_db),
) -> list[OrderSummaryResponse]:
    """Look up orders by barcode (booking_id). Supports partial matching."""

    stmt = (
        select(Order)
        .where(Order.booking_id.ilike(f"%{barcode}%"))
        .options(
            selectinload(Order.client),
            selectinload(Order.assigned_phlebotomist),
            selectinload(Order.packages).selectinload(OrderPackage.package),
            selectinload(Order.samples),
        )
    )

    result = await db.execute(stmt)
    orders = result.scalars().all()

    if not orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No orders found for barcode '{barcode}'",
        )

    return [_build_response(order) for order in orders]


def _build_response(order: Order) -> OrderSummaryResponse:
    ordered_tests = [
        OrderTestSummary(
            package_name=op.package.name,
            package_code=op.package.code,
            sample_types=op.package.sample_types or [],
        )
        for op in order.packages
    ]

    accessioning = [
        SampleAccessioningSummary(
            id=s.id,
            vial_type=s.vial_type,
            quantity=s.quantity,
            integrity=s.integrity.value,
            status=s.status.value,
            received_at=s.received_at,
        )
        for s in order.samples
    ]

    return OrderSummaryResponse(
        order_id=order.id,
        booking_id=order.booking_id,
        patient_name=order.patient_name,
        patient_age=order.patient_age,
        patient_gender=order.patient_gender.value,
        client_name=order.client.name if order.client else "Unknown",
        collected_at=order.collected_at,
        phlebotomist_name=(
            order.assigned_phlebotomist.name if order.assigned_phlebotomist else None
        ),
        ordered_tests=ordered_tests,
        status=order.status.value,
        accessioning=accessioning,
    )
