"""Payment API — task 9.1."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.orders import Order, OrderStatus
from app.models.payments import OrderPaymentMode, OrderPaymentStatus, Payment
from app.models.users import User, UserRole
from app.schemas.payment import (
    PaymentCreate,
    PaymentListResponse,
    PaymentReportResponse,
    PaymentResponse,
)

router = APIRouter(tags=["payments"])

# Statuses where payment recording is allowed
_PAYABLE_STATUSES = {
    OrderStatus.COLLECTED,
    OrderStatus.COMPLETED,
    OrderStatus.ACCEPTED,
    OrderStatus.IN_TRANSIT,
}


@router.post(
    "/orders/{order_id}/payment",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_payment(
    order_id: uuid.UUID,
    body: PaymentCreate,
    user: User = Depends(require_roles("phlebotomist")),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Record a payment for an order (PHLEBOTOMIST role)."""
    # Validate order exists
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Validate order status
    if order.status not in _PAYABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot record payment for order in '{order.status.value}' status",
        )

    # Validate mode
    try:
        mode = OrderPaymentMode(body.mode)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid payment mode: {body.mode}",
        ) from None

    payment = Payment(
        order_id=order_id,
        amount=body.amount,
        mode=mode,
        status=OrderPaymentStatus.COLLECTED,
        transaction_ref=body.transaction_ref,
        collected_by=user.id,
        collected_at=datetime.now(UTC),
        notes=body.notes,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    return PaymentResponse.model_validate(payment)


@router.get("/payments", response_model=PaymentListResponse)
async def list_payments(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    phlebotomist_id: uuid.UUID | None = None,
    client_id: uuid.UUID | None = None,
    mode: str | None = None,
    payment_status: str | None = Query(None, alias="status"),
    user: User = Depends(require_roles("super_admin", "city_admin", "phlebotomist")),
    db: AsyncSession = Depends(get_db),
) -> PaymentListResponse:
    """List payments with filters. Admin sees all, phlebotomist sees own."""
    query = select(Payment)
    count_query = select(func.count()).select_from(Payment)

    # RBAC: phlebotomist can only see own payments
    if user.role == UserRole.PHLEBOTOMIST:
        query = query.where(Payment.collected_by == user.id)
        count_query = count_query.where(Payment.collected_by == user.id)

    # Filters
    if date_from:
        query = query.where(Payment.collected_at >= date_from)
        count_query = count_query.where(Payment.collected_at >= date_from)
    if date_to:
        query = query.where(Payment.collected_at <= date_to)
        count_query = count_query.where(Payment.collected_at <= date_to)
    if phlebotomist_id:
        query = query.where(Payment.collected_by == phlebotomist_id)
        count_query = count_query.where(Payment.collected_by == phlebotomist_id)
    if client_id:
        query = query.join(Order, Payment.order_id == Order.id).where(
            Order.client_id == client_id
        )
        count_query = count_query.join(Order, Payment.order_id == Order.id).where(
            Order.client_id == client_id
        )
    if mode:
        try:
            mode_enum = OrderPaymentMode(mode)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid payment mode filter: {mode}",
            ) from None
        query = query.where(Payment.mode == mode_enum)
        count_query = count_query.where(Payment.mode == mode_enum)
    if payment_status:
        try:
            status_enum = OrderPaymentStatus(payment_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid payment status filter: {payment_status}",
            ) from None
        query = query.where(Payment.status == status_enum)
        count_query = count_query.where(Payment.status == status_enum)

    # Total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Pagination
    offset = (page - 1) * size
    query = query.order_by(Payment.collected_at.desc()).offset(offset).limit(size)
    result = await db.execute(query)
    payments = result.scalars().all()

    return PaymentListResponse(
        items=[PaymentResponse.model_validate(p) for p in payments],
        total=total,
        page=page,
        size=size,
    )


# ── GET /payments/report (task 9.6) ──────────────────────────────────


@router.get("/payments/report", response_model=PaymentReportResponse)
async def get_payment_report(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    client_id: uuid.UUID | None = Query(None),
    phlebotomist_id: uuid.UUID | None = Query(None),
    user: User = Depends(require_roles("super_admin", "city_admin")),
    db: AsyncSession = Depends(get_db),
) -> PaymentReportResponse:
    """Aggregated payment report for a date range."""

    filters: list = [
        Payment.collected_at >= date_from,
        Payment.collected_at <= date_to,
    ]
    needs_order_join = False

    if phlebotomist_id:
        filters.append(Payment.collected_by == phlebotomist_id)
    if client_id:
        filters.append(Order.client_id == client_id)
        needs_order_join = True

    # Total + count
    base = select(
        func.coalesce(func.sum(Payment.amount), 0).label("total_amount"),
        func.count().label("count"),
    )
    if needs_order_join:
        base = base.join(Order, Payment.order_id == Order.id)
    base = base.where(*filters)
    agg = (await db.execute(base)).one()

    # Breakdown by mode
    mode_stmt = select(
        Payment.mode, func.coalesce(func.sum(Payment.amount), 0).label("total")
    )
    if needs_order_join:
        mode_stmt = mode_stmt.join(Order, Payment.order_id == Order.id)
    mode_stmt = mode_stmt.where(*filters).group_by(Payment.mode)
    mode_rows = (await db.execute(mode_stmt)).all()
    breakdown_by_mode = {str(r.mode.value): float(r.total) for r in mode_rows}

    # Breakdown by status
    status_stmt = select(
        Payment.status, func.coalesce(func.sum(Payment.amount), 0).label("total")
    )
    if needs_order_join:
        status_stmt = status_stmt.join(Order, Payment.order_id == Order.id)
    status_stmt = status_stmt.where(*filters).group_by(Payment.status)
    status_rows = (await db.execute(status_stmt)).all()
    breakdown_by_status = {str(r.status.value): float(r.total) for r in status_rows}

    return PaymentReportResponse(
        date_from=date_from,
        date_to=date_to,
        total_amount=float(agg.total_amount),
        breakdown_by_mode=breakdown_by_mode,
        breakdown_by_status=breakdown_by_status,
        count=int(agg.count),
    )
