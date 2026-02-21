"""Order endpoints — task 6.1."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.clients import ClientUser
from app.models.nsa import NSARecord
from app.models.orders import (
    Order,
    OrderPriority,
    OrderStatus,
    OrderStatusHistory,
    PatientGender,
    PatientTitle,
    PaymentMode,
)
from app.models.phlebotomists import Phlebotomist
from app.models.users import User, UserRole
from app.models.zones import Pincode
from app.schemas.order import (
    OrderCreate,
    OrderDetailResponse,
    OrderListResponse,
    OrderResponse,
)

router = APIRouter(prefix="/orders", tags=["orders"])


async def _generate_booking_id(db: AsyncSession, appt_date: date) -> str:
    """Generate PNC-YYYYMMDD-NNNN booking ID."""
    date_str = appt_date.strftime("%Y%m%d")
    prefix = f"PNC-{date_str}-"

    result = await db.execute(
        select(func.count())
        .select_from(Order)
        .where(Order.booking_id.like(f"{prefix}%"))
    )
    count = result.scalar_one()
    return f"{prefix}{count + 1:04d}"


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    payload: OrderCreate,
    user: User = Depends(require_roles("super_admin", "city_admin", "client_user")),
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Create a new order with validation and booking ID generation."""

    # 1. Look up pincode
    result = await db.execute(select(Pincode).where(Pincode.pincode == payload.pincode))
    pincode_row = result.scalar_one_or_none()
    if pincode_row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pincode {payload.pincode} not found",
        )

    # 2. Check NSA
    nsa_result = await db.execute(
        select(NSARecord).where(
            NSARecord.pincode == payload.pincode,
            NSARecord.is_active.is_(True),
        )
    )
    if nsa_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pincode {payload.pincode} is in a Non-Serviceable Area",
        )

    # 3. Generate booking ID
    booking_id = await _generate_booking_id(db, payload.appointment_date)

    # 4. Create order
    order = Order(
        booking_id=booking_id,
        client_id=payload.client_id,
        pincode_id=pincode_row.id,
        locality_id=payload.locality_id,
        patient_title=PatientTitle(payload.patient_title),
        patient_name=payload.patient_name,
        patient_age=payload.patient_age,
        patient_gender=PatientGender(payload.patient_gender),
        patient_phone=payload.patient_phone,
        appointment_date=payload.appointment_date,
        appointment_time_slot=payload.appointment_time_slot,
        address=payload.address,
        landmark=payload.landmark,
        status=OrderStatus.PENDING,
        priority=OrderPriority(payload.priority),
        special_instructions=payload.special_instructions,
        payment_mode=PaymentMode(payload.payment_mode),
        created_by=user.id,
    )
    db.add(order)

    # 5. Initial status history
    history = OrderStatusHistory(
        order_id=order.id,
        status=OrderStatus.PENDING,
        changed_by=user.id,
        notes="Order created",
    )
    db.add(history)

    await db.commit()
    await db.refresh(order)

    # Ensure created_at is populated (may be None before DB round-trip in tests)
    if order.created_at is None:
        order.created_at = datetime.now(UTC)

    return order


@router.get(
    "",
    response_model=OrderListResponse,
)
async def list_orders(
    status: OrderStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    client_id: uuid.UUID | None = None,
    phlebotomist_id: uuid.UUID | None = None,
    priority: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 20,
    user: User = Depends(
        require_roles("super_admin", "city_admin", "client_user", "phlebotomist")
    ),
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    """List orders with filters and RBAC."""
    query = select(Order)
    count_query = select(func.count()).select_from(Order)

    # RBAC filtering
    if user.role == UserRole.CLIENT_USER:
        # Find the client linked to this user
        cu_result = await db.execute(
            select(ClientUser.client_id).where(ClientUser.user_id == user.id)
        )
        user_client_id = cu_result.scalar_one_or_none()
        if user_client_id is None:
            return OrderListResponse(
                items=[], total=0, skip=skip, limit=limit, has_more=False
            )
        query = query.where(Order.client_id == user_client_id)
        count_query = count_query.where(Order.client_id == user_client_id)
    elif user.role == UserRole.PHLEBOTOMIST:
        phleb_result = await db.execute(
            select(Phlebotomist.id).where(Phlebotomist.user_id == user.id)
        )
        phleb_id = phleb_result.scalar_one_or_none()
        if phleb_id is None:
            return OrderListResponse(
                items=[], total=0, skip=skip, limit=limit, has_more=False
            )
        query = query.where(Order.assigned_phlebotomist_id == phleb_id)
        count_query = count_query.where(Order.assigned_phlebotomist_id == phleb_id)

    # Filters
    if status is not None:
        query = query.where(Order.status == status)
        count_query = count_query.where(Order.status == status)
    if date_from is not None:
        query = query.where(Order.appointment_date >= date_from)
        count_query = count_query.where(Order.appointment_date >= date_from)
    if date_to is not None:
        query = query.where(Order.appointment_date <= date_to)
        count_query = count_query.where(Order.appointment_date <= date_to)
    if client_id is not None:
        query = query.where(Order.client_id == client_id)
        count_query = count_query.where(Order.client_id == client_id)
    if phlebotomist_id is not None:
        query = query.where(Order.assigned_phlebotomist_id == phlebotomist_id)
        count_query = count_query.where(
            Order.assigned_phlebotomist_id == phlebotomist_id
        )
    if priority is not None:
        query = query.where(Order.priority == priority)
        count_query = count_query.where(Order.priority == priority)
    if search is not None:
        search_pattern = f"%{search}%"
        search_filter = (
            Order.booking_id.ilike(search_pattern)
            | Order.patient_name.ilike(search_pattern)
            | Order.patient_phone.ilike(search_pattern)
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Fetch
    query = query.order_by(Order.appointment_date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    orders = list(result.scalars().all())

    return OrderListResponse(
        items=orders,
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total,
    )


@router.get(
    "/{order_id}",
    response_model=OrderDetailResponse,
)
async def get_order(
    order_id: uuid.UUID,
    user: User = Depends(
        require_roles("super_admin", "city_admin", "client_user", "phlebotomist")
    ),
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Get order detail with status history."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.status_history))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    return order
