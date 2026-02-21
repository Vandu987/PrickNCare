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
from app.models.orders import Order, OrderStatus, OrderStatusHistory
from app.models.packages import OrderPackage
from app.models.samples import SampleAccessioning, SampleIntegrity, SampleStatus
from app.models.users import User
from app.schemas.accessioning import (
    AccessioningCreate,
    AccessioningDetailItem,
    AccessioningDetailResponse,
    AccessioningReportResponse,
    ClientInfo,
    IntegrityBreakdownItem,
    OrderSummaryResponse,
    OrderTestSummary,
    PendingAccessioningResponse,
    PendingSampleItem,
    PhlebotomistInfo,
    RejectedSampleDetail,
    SampleAccessioningSummary,
    SampleItemUpdate,
    StatusBreakdownItem,
)
from app.services.notifications import notify_sample_hold, notify_sample_rejection

router = APIRouter(prefix="/accessioning", tags=["accessioning"])

_admin_only = RoleChecker("super_admin", "city_admin")


async def _determine_and_update_order_status(
    order: Order,
    samples: list[SampleAccessioning],
    user: User,
    db: AsyncSession,
) -> None:
    """Determine order status from accessioning results and update if changed."""
    statuses = {s.status for s in samples}

    if SampleStatus.REJECTED in statuses:
        new_status = OrderStatus.SAMPLE_REJECTED
    elif SampleStatus.HOLD in statuses:
        new_status = OrderStatus.SAMPLE_HOLD
    else:
        new_status = OrderStatus.COMPLETED

    old_status = order.status
    if new_status == old_status:
        return

    order.status = new_status
    db.add(
        OrderStatusHistory(
            order_id=order.id,
            changed_by=user.id,
            status=new_status,
            notes=f"Auto-set by accessioning: {old_status.value} → {new_status.value}",
        )
    )

    # Notifications
    rejected = [s for s in samples if s.status == SampleStatus.REJECTED]
    held = [s for s in samples if s.status == SampleStatus.HOLD]
    if rejected:
        await notify_sample_rejection(order, rejected)
    if held and new_status == OrderStatus.SAMPLE_HOLD:
        await notify_sample_hold(order, held)


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


# ── Task 8.2 — Accessioning CRUD ────────────────────────────────────────


@router.post("/{order_id}", status_code=status.HTTP_201_CREATED)
async def create_accessioning(
    order_id: uuid.UUID,
    payload: AccessioningCreate,
    user: User = Depends(_admin_only),
    db: AsyncSession = Depends(get_db),
) -> AccessioningDetailResponse:
    """Create accessioning records for an order."""
    # Validate order exists and is COLLECTED
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    if order.status != OrderStatus.COLLECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order status must be COLLECTED, got {order.status.value}",
        )

    # Validate enums and create records
    created: list[SampleAccessioning] = []
    for sample in payload.samples:
        try:
            integrity_val = SampleIntegrity(sample.integrity)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid integrity value: {sample.integrity}",
            ) from None
        try:
            status_val = SampleStatus(sample.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status value: {sample.status}",
            ) from None

        if status_val == SampleStatus.REJECTED and not sample.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="rejection_reason is required when status is rejected",
            )

        record = SampleAccessioning(
            order_id=order_id,
            vial_type=sample.vial_type,
            quantity=sample.quantity,
            integrity=integrity_val,
            status=status_val,
            rejection_reason=sample.rejection_reason,
            notes=payload.notes,
            accessioned_by=user.id,
        )
        db.add(record)
        created.append(record)

    # Determine and update order status based on accessioning results
    await _determine_and_update_order_status(order, created, user, db)

    await db.commit()
    for r in created:
        await db.refresh(r)

    return AccessioningDetailResponse(
        order_id=order_id,
        items=[
            AccessioningDetailItem(
                id=r.id,
                order_id=r.order_id,
                vial_type=r.vial_type,
                quantity=r.quantity,
                integrity=r.integrity.value,
                status=r.status.value,
                rejection_reason=r.rejection_reason,
                notes=r.notes,
                accessioned_by=r.accessioned_by,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in created
        ],
    )


@router.get("/{order_id}", response_model=AccessioningDetailResponse)
async def get_accessioning(
    order_id: uuid.UUID,
    user: User = Depends(_admin_only),
    db: AsyncSession = Depends(get_db),
) -> AccessioningDetailResponse:
    """Get accessioning details for an order."""
    result = await db.execute(
        select(SampleAccessioning).where(SampleAccessioning.order_id == order_id)
    )
    items = result.scalars().all()

    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No accessioning records found for this order",
        )

    return AccessioningDetailResponse(
        order_id=order_id,
        items=[
            AccessioningDetailItem(
                id=r.id,
                order_id=r.order_id,
                vial_type=r.vial_type,
                quantity=r.quantity,
                integrity=r.integrity.value,
                status=r.status.value,
                rejection_reason=r.rejection_reason,
                notes=r.notes,
                accessioned_by=r.accessioned_by,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in items
        ],
    )


@router.put("/record/{accessioning_id}", response_model=AccessioningDetailItem)
async def update_accessioning(
    accessioning_id: uuid.UUID,
    payload: SampleItemUpdate,
    user: User = Depends(_admin_only),
    db: AsyncSession = Depends(get_db),
) -> AccessioningDetailItem:
    """Update a single accessioning record."""
    record = await db.get(SampleAccessioning, accessioning_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accessioning record not found",
        )

    if payload.vial_type is not None:
        record.vial_type = payload.vial_type
    if payload.quantity is not None:
        record.quantity = payload.quantity
    if payload.integrity is not None:
        try:
            record.integrity = SampleIntegrity(payload.integrity)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid integrity value: {payload.integrity}",
            ) from None
    if payload.status is not None:
        try:
            new_status = SampleStatus(payload.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status value: {payload.status}",
            ) from None
        if new_status == SampleStatus.REJECTED and not (
            payload.rejection_reason or record.rejection_reason
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="rejection_reason is required when status is rejected",
            )
        record.status = new_status
    if payload.rejection_reason is not None:
        record.rejection_reason = payload.rejection_reason
    if payload.notes is not None:
        record.notes = payload.notes

    # Recalculate order status from all samples for this order
    all_samples_q = await db.execute(
        select(SampleAccessioning).where(SampleAccessioning.order_id == record.order_id)
    )
    all_samples = list(all_samples_q.scalars().all())
    order = await db.get(Order, record.order_id)
    if order:
        await _determine_and_update_order_status(order, all_samples, user, db)

    await db.commit()
    await db.refresh(record)

    return AccessioningDetailItem(
        id=record.id,
        order_id=record.order_id,
        vial_type=record.vial_type,
        quantity=record.quantity,
        integrity=record.integrity.value,
        status=record.status.value,
        rejection_reason=record.rejection_reason,
        notes=record.notes,
        accessioned_by=record.accessioned_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


# ── Task 8.5 — Accessioning report / analytics ──────────────────────────


@router.get("/report", response_model=AccessioningReportResponse)
async def accessioning_report(
    date_from: date = Query(..., description="Start date (inclusive)"),
    date_to: date = Query(..., description="End date (inclusive)"),
    integrity: SampleIntegrity | None = Query(None, description="Filter by integrity"),
    status: SampleStatus | None = Query(None, description="Filter by status"),
    user: User = Depends(_admin_only),
    db: AsyncSession = Depends(get_db),
) -> AccessioningReportResponse:
    """Accessioning analytics report for a date range."""

    base = select(SampleAccessioning).where(
        func.date(SampleAccessioning.created_at) >= date_from,
        func.date(SampleAccessioning.created_at) <= date_to,
    )
    if integrity is not None:
        base = base.where(SampleAccessioning.integrity == integrity)
    if status is not None:
        base = base.where(SampleAccessioning.status == status)

    result = await db.execute(base.options(selectinload(SampleAccessioning.order)))
    samples = result.scalars().all()

    total = len(samples)

    # Breakdowns
    integrity_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    order_ids: set[uuid.UUID] = set()
    rejected: list[RejectedSampleDetail] = []

    for s in samples:
        i_val = s.integrity.value
        integrity_counts[i_val] = integrity_counts.get(i_val, 0) + 1
        s_val = s.status.value
        status_counts[s_val] = status_counts.get(s_val, 0) + 1
        order_ids.add(s.order_id)
        if s.status == SampleStatus.REJECTED:
            patient_name = s.order.patient_name if s.order else "Unknown"
            rejected.append(
                RejectedSampleDetail(
                    order_id=s.order_id,
                    patient_name=patient_name,
                    rejection_reason=s.rejection_reason,
                    vial_type=s.vial_type,
                )
            )

    def _pct(count: int) -> float:
        return round(count / total * 100, 2) if total else 0.0

    breakdown_integrity = {
        k: IntegrityBreakdownItem(count=v, percentage=_pct(v))
        for k, v in integrity_counts.items()
    }
    breakdown_status = {
        k: StatusBreakdownItem(count=v, percentage=_pct(v))
        for k, v in status_counts.items()
    }

    rejection_count = status_counts.get(SampleStatus.REJECTED.value, 0)
    hold_count = status_counts.get(SampleStatus.HOLD.value, 0)
    avg_per_order = round(total / len(order_ids), 2) if order_ids else 0.0

    return AccessioningReportResponse(
        total_samples_received=total,
        breakdown_by_integrity=breakdown_integrity,
        breakdown_by_status=breakdown_status,
        rejection_rate=_pct(rejection_count),
        hold_rate=_pct(hold_count),
        average_samples_per_order=avg_per_order,
        rejected_samples_list=rejected,
    )


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
