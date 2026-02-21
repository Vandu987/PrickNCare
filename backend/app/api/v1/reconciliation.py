"""Reconciliation API — tasks 9.2 & 9.3."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.payments import OrderPaymentMode, OrderPaymentStatus, Payment
from app.models.phlebotomists import Phlebotomist
from app.models.reconciliation import (
    DiscrepancyCategory,
    Reconciliation,
    ReconciliationDiscrepancy,
    ReconciliationStatus,
)
from app.models.users import User
from app.schemas.reconciliation import (
    PendingReconciliationResponse,
    PhlebotomistSummary,
    ReconciliationCreate,
    ReconciliationResponse,
    ReconciliationUpdate,
)

router = APIRouter(tags=["reconciliation"])

_ONLINE_MODES = {
    OrderPaymentMode.UPI,
    OrderPaymentMode.CARD,
    OrderPaymentMode.WALLET,
}

# Discrepancy types treated as approved deductions when computing net discrepancy
_APPROVED_DEDUCTIONS = {
    DiscrepancyCategory.FUEL_ALLOWANCE,
    DiscrepancyCategory.PATIENT_REFUND,
}


# ── GET /reconciliation/pending (task 9.2) ────────────────────────────


@router.get(
    "/reconciliation/pending",
    response_model=PendingReconciliationResponse,
)
async def get_pending_reconciliation(
    date_param: date | None = Query(None, alias="date"),
    user: User = Depends(require_roles("super_admin", "city_admin")),
    db: AsyncSession = Depends(get_db),
) -> PendingReconciliationResponse:
    """Return per-phlebotomist cash summary for unreconciled payments on a date."""

    target_date = date_param or datetime.now(UTC).date()

    stmt = (
        select(
            Payment.collected_by,
            func.count(func.distinct(Payment.order_id)).label("total_appointments"),
            func.coalesce(
                func.sum(
                    case(
                        (Payment.mode == OrderPaymentMode.CASH, Payment.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("cash_collected"),
            func.coalesce(
                func.sum(
                    case(
                        (Payment.mode.in_(_ONLINE_MODES), Payment.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("online_collected"),
            func.coalesce(func.sum(Payment.amount), 0).label("total_collected"),
        )
        .where(
            Payment.status != OrderPaymentStatus.RECONCILED,
            cast(Payment.collected_at, Date) == target_date,
        )
        .group_by(Payment.collected_by)
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return PendingReconciliationResponse(date=target_date, items=[])

    user_ids = [r.collected_by for r in rows]

    phleb_stmt = (
        select(Phlebotomist, User)
        .join(User, Phlebotomist.user_id == User.id)
        .where(Phlebotomist.user_id.in_(user_ids))
    )
    phleb_result = await db.execute(phleb_stmt)
    phleb_map: dict = {}
    for phleb, u in phleb_result.all():
        phleb_map[u.id] = (phleb, u)

    items: list[PhlebotomistSummary] = []
    for row in rows:
        phleb_info = phleb_map.get(row.collected_by)
        if not phleb_info:
            continue
        phleb, u = phleb_info
        items.append(
            PhlebotomistSummary(
                phlebotomist_id=phleb.id,
                user_id=u.id,
                name=phleb.name,
                total_appointments=row.total_appointments,
                cash_collected=float(row.cash_collected),
                online_collected=float(row.online_collected),
                total_collected=float(row.total_collected),
            )
        )

    return PendingReconciliationResponse(date=target_date, items=items)


# ── POST /reconciliation (task 9.3) ──────────────────────────────────


@router.post(
    "/reconciliation",
    response_model=ReconciliationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reconciliation(
    body: ReconciliationCreate,
    user: User = Depends(require_roles("super_admin", "city_admin")),
    db: AsyncSession = Depends(get_db),
) -> ReconciliationResponse:
    """Create a cash reconciliation for a phlebotomist on a given date."""

    # 1. Verify phlebotomist exists
    phleb = await db.get(Phlebotomist, body.phlebotomist_id)
    if not phleb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phlebotomist not found",
        )

    # 2. Check for duplicate reconciliation
    dup_stmt = select(Reconciliation).where(
        Reconciliation.phlebotomist_id == body.phlebotomist_id,
        Reconciliation.date == body.date,
    )
    existing = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reconciliation already exists for this phlebotomist on this date",
        )

    # 3. Calculate expected_cash: sum of cash payments for phlebotomist on date
    cash_stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.collected_by == phleb.user_id,
        Payment.mode == OrderPaymentMode.CASH,
        Payment.status != OrderPaymentStatus.RECONCILED,
        cast(Payment.collected_at, Date) == body.date,
    )
    expected_cash = float((await db.execute(cash_stmt)).scalar_one())

    # 4. Calculate approved deductions from discrepancies
    approved_deductions = Decimal(0)
    for d in body.discrepancies:
        cat = DiscrepancyCategory(d.type)
        if cat in _APPROVED_DEDUCTIONS:
            approved_deductions += Decimal(str(d.amount))

    # net_discrepancy = expected - handed_over - approved_deductions
    net_discrepancy = (
        Decimal(str(expected_cash))
        - Decimal(str(body.cash_handed_over))
        - approved_deductions
    )

    # 5. Create reconciliation
    reconciliation = Reconciliation(
        phlebotomist_id=body.phlebotomist_id,
        date=body.date,
        expected_cash=float(expected_cash),
        cash_handed_over=body.cash_handed_over,
        net_discrepancy=float(net_discrepancy),
        status=ReconciliationStatus.CONFIRMED,
        created_by=user.id,
    )
    db.add(reconciliation)

    # 6. Create discrepancy records
    for d in body.discrepancies:
        disc = ReconciliationDiscrepancy(
            reconciliation_id=reconciliation.id,
            type=DiscrepancyCategory(d.type),
            amount=d.amount,
            notes=d.notes,
        )
        db.add(disc)

    # 7. Mark associated cash payments as RECONCILED
    payment_stmt = select(Payment).where(
        Payment.collected_by == phleb.user_id,
        Payment.mode == OrderPaymentMode.CASH,
        Payment.status != OrderPaymentStatus.RECONCILED,
        cast(Payment.collected_at, Date) == body.date,
    )
    payment_result = await db.execute(payment_stmt)
    for payment in payment_result.scalars().all():
        payment.status = OrderPaymentStatus.RECONCILED

    await db.commit()

    # Reload with discrepancies
    reloaded = await db.execute(
        select(Reconciliation)
        .options(selectinload(Reconciliation.discrepancies))
        .where(Reconciliation.id == reconciliation.id)
    )
    rec = reloaded.scalar_one()

    return ReconciliationResponse.model_validate(rec)


# ── GET /reconciliation/{id} (task 9.3) ──────────────────────────────


@router.get(
    "/reconciliation/{reconciliation_id}",
    response_model=ReconciliationResponse,
)
async def get_reconciliation(
    reconciliation_id: uuid.UUID,
    user: User = Depends(require_roles("super_admin", "city_admin")),
    db: AsyncSession = Depends(get_db),
) -> ReconciliationResponse:
    """Get a reconciliation by ID."""
    stmt = (
        select(Reconciliation)
        .options(selectinload(Reconciliation.discrepancies))
        .where(Reconciliation.id == reconciliation_id)
    )
    rec = (await db.execute(stmt)).scalar_one_or_none()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reconciliation not found",
        )
    return ReconciliationResponse.model_validate(rec)


# ── PUT /reconciliation/{id} (task 9.3) ──────────────────────────────


@router.put(
    "/reconciliation/{reconciliation_id}",
    response_model=ReconciliationResponse,
)
async def update_reconciliation(
    reconciliation_id: uuid.UUID,
    body: ReconciliationUpdate,
    user: User = Depends(require_roles("super_admin", "city_admin")),
    db: AsyncSession = Depends(get_db),
) -> ReconciliationResponse:
    """Update a reconciliation."""
    stmt = (
        select(Reconciliation)
        .options(selectinload(Reconciliation.discrepancies))
        .where(Reconciliation.id == reconciliation_id)
    )
    rec = (await db.execute(stmt)).scalar_one_or_none()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reconciliation not found",
        )

    if body.status is not None:
        rec.status = ReconciliationStatus(body.status)

    if body.cash_handed_over is not None:
        rec.cash_handed_over = body.cash_handed_over

    # If discrepancies provided, replace them
    if body.discrepancies is not None:
        # Remove old
        for old_d in list(rec.discrepancies):
            await db.delete(old_d)

        # Add new
        for d in body.discrepancies:
            disc = ReconciliationDiscrepancy(
                reconciliation_id=rec.id,
                type=DiscrepancyCategory(d.type),
                amount=d.amount,
                notes=d.notes,
            )
            db.add(disc)

    # Recalculate net_discrepancy if cash_handed_over or discrepancies changed
    if body.cash_handed_over is not None or body.discrepancies is not None:
        await db.flush()
        # Reload discrepancies
        await db.refresh(rec, attribute_names=["discrepancies"])

        approved_deductions = Decimal(0)
        for d in rec.discrepancies:
            if d.type in _APPROVED_DEDUCTIONS:
                approved_deductions += Decimal(str(d.amount))

        rec.net_discrepancy = float(
            Decimal(str(rec.expected_cash))
            - Decimal(str(rec.cash_handed_over))
            - approved_deductions
        )

    await db.commit()
    await db.refresh(rec, attribute_names=["discrepancies"])

    return ReconciliationResponse.model_validate(rec)
