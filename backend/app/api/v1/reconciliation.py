"""Reconciliation API — task 9.2."""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.payments import OrderPaymentMode, OrderPaymentStatus, Payment
from app.models.phlebotomists import Phlebotomist
from app.models.users import User
from app.schemas.reconciliation import (
    PendingReconciliationResponse,
    PhlebotomistSummary,
)

router = APIRouter(tags=["reconciliation"])

_ONLINE_MODES = {
    OrderPaymentMode.UPI,
    OrderPaymentMode.CARD,
    OrderPaymentMode.WALLET,
}


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

    # Aggregate payments grouped by collector (phlebotomist user)
    # Only non-reconciled payments on the target date
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

    # Fetch phlebotomist + user info for all collectors
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
