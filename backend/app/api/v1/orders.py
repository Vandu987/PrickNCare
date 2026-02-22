"""Order endpoints — task 6.1."""

from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
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
from app.models.packages import Package
from app.models.phlebotomist_leaves import PhlebotomistLeave
from app.models.phlebotomists import Phlebotomist, PhlebotomistZoneAssignment
from app.models.users import User, UserRole
from app.models.zones import Pincode
from app.schemas.order import (
    AutoAssignRequest,
    AutoAssignResult,
    BulkAssignFailedItem,
    BulkAssignRequest,
    BulkAssignResult,
    BulkAssignSuccessItem,
    BulkOrderUploadResult,
    BulkRowError,
    CollectionData,
    OrderAssignRequest,
    OrderCancelRequest,
    OrderCreate,
    OrderDetailResponse,
    OrderListResponse,
    OrderRescheduleRequest,
    OrderResponse,
    OrderStatusUpdate,
    RejectReason,
    StatusHistoryResponse,
)

router = APIRouter(prefix="/orders", tags=["orders"])

# State machine: valid status transitions
_VALID_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.PENDING: [OrderStatus.ASSIGNED, OrderStatus.CANCELLED],
    OrderStatus.ASSIGNED: [
        OrderStatus.ACCEPTED,
        OrderStatus.PENDING,
        OrderStatus.CANCELLED,
    ],
    OrderStatus.ACCEPTED: [OrderStatus.IN_TRANSIT, OrderStatus.PENDING],
    OrderStatus.IN_TRANSIT: [
        OrderStatus.COLLECTED,
        OrderStatus.UNCOLLECTED,
        OrderStatus.NSA,
    ],
    OrderStatus.COLLECTED: [
        OrderStatus.COMPLETED,
        OrderStatus.SAMPLE_REJECTED,
        OrderStatus.SAMPLE_HOLD,
    ],
    OrderStatus.SAMPLE_HOLD: [
        OrderStatus.COMPLETED,
        OrderStatus.SAMPLE_REJECTED,
    ],
    OrderStatus.SAMPLE_REJECTED: [],
    OrderStatus.COMPLETED: [],
    OrderStatus.UNCOLLECTED: [OrderStatus.PENDING],
    OrderStatus.CANCELLED: [],
    OrderStatus.NSA: [OrderStatus.PENDING],
}


def validate_transition(current: OrderStatus, target: OrderStatus) -> bool:
    """Check whether a status transition is allowed."""
    return target in _VALID_TRANSITIONS.get(current, [])


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


@router.post(
    "/auto-assign",
    response_model=AutoAssignResult,
)
async def auto_assign_orders(
    payload: AutoAssignRequest | None = None,
    user: User = Depends(require_roles("super_admin", "city_admin")),
    db: AsyncSession = Depends(get_db),
) -> AutoAssignResult:
    """Auto-assign PENDING orders using zone matching and workload balancing."""
    from app.schemas.order import AutoAssignFailure

    # 1. Fetch target orders
    query = select(Order).where(Order.status == OrderStatus.PENDING)
    if payload and payload.order_ids:
        query = query.where(Order.id.in_(payload.order_ids))
    query = query.order_by(
        Order.appointment_date.asc(), Order.appointment_time_slot.asc()
    )

    result = await db.execute(query)
    orders = list(result.scalars().all())

    assigned_count = 0
    failures: list[AutoAssignFailure] = []

    for order in orders:
        # 2. Resolve pincode → zone
        pin_result = await db.execute(
            select(Pincode).where(Pincode.id == order.pincode_id)
        )
        pincode_row = pin_result.scalar_one_or_none()
        if pincode_row is None or pincode_row.zone_id is None:
            failures.append(
                AutoAssignFailure(
                    order_id=order.id,
                    booking_id=order.booking_id,
                    reason="Pincode has no zone assigned",
                )
            )
            continue

        zone_id = pincode_row.zone_id

        # 3. Find phlebotomists assigned to this zone
        zone_phleb_result = await db.execute(
            select(PhlebotomistZoneAssignment.phlebotomist_id).where(
                PhlebotomistZoneAssignment.zone_id == zone_id
            )
        )
        zone_phleb_ids = [r[0] for r in zone_phleb_result.all()]
        if not zone_phleb_ids:
            failures.append(
                AutoAssignFailure(
                    order_id=order.id,
                    booking_id=order.booking_id,
                    reason="No phlebotomists assigned to zone",
                )
            )
            continue

        # 4. Filter: is_available, is_active, not on leave
        phleb_result = await db.execute(
            select(Phlebotomist).where(
                Phlebotomist.id.in_(zone_phleb_ids),
                Phlebotomist.is_available.is_(True),
            )
        )
        candidates = list(phleb_result.scalars().all())

        eligible = []
        for phleb in candidates:
            # Check user is_active
            user_result = await db.execute(select(User).where(User.id == phleb.user_id))
            phleb_user = user_result.scalar_one_or_none()
            if phleb_user is None or not phleb_user.is_active:
                continue

            # Check leave
            leave_result = await db.execute(
                select(PhlebotomistLeave).where(
                    PhlebotomistLeave.phlebotomist_id == phleb.id,
                    PhlebotomistLeave.date == order.appointment_date,
                    PhlebotomistLeave.status == "approved",
                )
            )
            if leave_result.scalar_one_or_none() is not None:
                continue

            eligible.append(phleb)

        if not eligible:
            failures.append(
                AutoAssignFailure(
                    order_id=order.id,
                    booking_id=order.booking_id,
                    reason="No eligible phlebotomists available",
                )
            )
            continue

        # 5. Workload balancing: pick the one with fewest orders on that day
        best_phleb = None
        best_count = float("inf")
        for phleb in eligible:
            count_result = await db.execute(
                select(func.count())
                .select_from(Order)
                .where(
                    Order.assigned_phlebotomist_id == phleb.id,
                    Order.appointment_date == order.appointment_date,
                    Order.status.in_(
                        [
                            OrderStatus.ASSIGNED,
                            OrderStatus.ACCEPTED,
                            OrderStatus.IN_TRANSIT,
                            OrderStatus.COLLECTED,
                            OrderStatus.COMPLETED,
                        ]
                    ),
                )
            )
            workload = count_result.scalar_one()
            if workload < best_count:
                best_count = workload
                best_phleb = phleb

        # 6. Assign
        order.assigned_phlebotomist_id = best_phleb.id  # type: ignore[union-attr]
        order.status = OrderStatus.ASSIGNED
        order.assigned_at = datetime.now(UTC)

        history = OrderStatusHistory(
            order_id=order.id,
            status=OrderStatus.ASSIGNED,
            changed_by=user.id,
            notes=f"Auto-assigned to phlebotomist {best_phleb.id}",  # type: ignore[union-attr]
        )
        db.add(history)
        assigned_count += 1

    await db.commit()

    return AutoAssignResult(
        total_processed=len(orders),
        assigned=assigned_count,
        failed=len(failures),
        failures=failures,
    )


@router.post(
    "/bulk-assign",
    response_model=BulkAssignResult,
)
async def bulk_assign_orders(
    payload: BulkAssignRequest,
    user: User = Depends(require_roles("super_admin", "city_admin")),
    db: AsyncSession = Depends(get_db),
) -> BulkAssignResult:
    """Bulk-assign phlebotomists to orders. Each pair processed individually."""
    success: list[BulkAssignSuccessItem] = []
    failed: list[BulkAssignFailedItem] = []

    for item in payload.assignments:
        try:
            # Fetch order
            result = await db.execute(select(Order).where(Order.id == item.order_id))
            order = result.scalar_one_or_none()
            if order is None:
                failed.append(
                    BulkAssignFailedItem(
                        order_id=item.order_id, reason="Order not found"
                    )
                )
                continue

            if order.status != OrderStatus.PENDING:
                failed.append(
                    BulkAssignFailedItem(
                        order_id=item.order_id,
                        reason=f"Order status is {order.status.value}, must be pending",
                    )
                )
                continue

            # Fetch phlebotomist
            phleb_result = await db.execute(
                select(Phlebotomist).where(Phlebotomist.id == item.phlebotomist_id)
            )
            phleb = phleb_result.scalar_one_or_none()
            if phleb is None:
                failed.append(
                    BulkAssignFailedItem(
                        order_id=item.order_id, reason="Phlebotomist not found"
                    )
                )
                continue

            if not phleb.is_available:
                failed.append(
                    BulkAssignFailedItem(
                        order_id=item.order_id,
                        reason="Phlebotomist is not available",
                    )
                )
                continue

            # Check user is_active
            phleb_user_result = await db.execute(
                select(User).where(User.id == phleb.user_id)
            )
            phleb_user = phleb_user_result.scalar_one_or_none()
            if phleb_user is None or not phleb_user.is_active:
                failed.append(
                    BulkAssignFailedItem(
                        order_id=item.order_id,
                        reason="Phlebotomist user account is not active",
                    )
                )
                continue

            # Zone validation
            pincode_result = await db.execute(
                select(Pincode).where(Pincode.id == order.pincode_id)
            )
            pincode_row = pincode_result.scalar_one()

            zone_check = await db.execute(
                select(PhlebotomistZoneAssignment).where(
                    PhlebotomistZoneAssignment.phlebotomist_id == phleb.id,
                    PhlebotomistZoneAssignment.zone_id == pincode_row.zone_id,
                )
            )
            if zone_check.scalar_one_or_none() is None:
                failed.append(
                    BulkAssignFailedItem(
                        order_id=item.order_id,
                        reason="Phlebotomist is not assigned to the order's zone",
                    )
                )
                continue

            # Leave check
            leave_result = await db.execute(
                select(PhlebotomistLeave).where(
                    PhlebotomistLeave.phlebotomist_id == phleb.id,
                    PhlebotomistLeave.date == order.appointment_date,
                    PhlebotomistLeave.status == "approved",
                )
            )
            if leave_result.scalar_one_or_none() is not None:
                failed.append(
                    BulkAssignFailedItem(
                        order_id=item.order_id,
                        reason="Phlebotomist is on leave for the appointment date",
                    )
                )
                continue

            # Assign
            order.assigned_phlebotomist_id = phleb.id
            order.status = OrderStatus.ASSIGNED
            order.assigned_at = datetime.now(UTC)

            history = OrderStatusHistory(
                order_id=order.id,
                status=OrderStatus.ASSIGNED,
                changed_by=user.id,
                notes=f"Bulk assigned to phlebotomist {phleb.id}",
            )
            db.add(history)

            # Get phlebotomist name
            phleb_name = (
                phleb_user.full_name
                if hasattr(phleb_user, "full_name")
                else phleb_user.email
            )
            success.append(
                BulkAssignSuccessItem(
                    order_id=item.order_id, phlebotomist_name=phleb_name
                )
            )

        except Exception as exc:
            failed.append(BulkAssignFailedItem(order_id=item.order_id, reason=str(exc)))

    if success:
        await db.commit()

    return BulkAssignResult(success=success, failed=failed)


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


@router.put(
    "/{order_id}/status",
    response_model=StatusHistoryResponse,
)
async def update_order_status(
    order_id: uuid.UUID,
    payload: OrderStatusUpdate,
    user: User = Depends(
        require_roles("super_admin", "city_admin", "client_user", "phlebotomist")
    ),
    db: AsyncSession = Depends(get_db),
) -> OrderStatusHistory:
    """Update order status with state machine validation."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    try:
        target_status = OrderStatus(payload.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {payload.status}",
        ) from None

    if not validate_transition(order.status, target_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot transition from {order.status.value}"
                f" to {target_status.value}"
            ),
        )

    order.status = target_status

    history = OrderStatusHistory(
        order_id=order.id,
        status=target_status,
        changed_by=user.id,
        notes=payload.reason,
    )
    db.add(history)

    await db.commit()
    await db.refresh(history)
    return history


@router.put(
    "/{order_id}/assign",
    response_model=OrderResponse,
)
async def assign_order(
    order_id: uuid.UUID,
    payload: OrderAssignRequest,
    user: User = Depends(require_roles("super_admin", "city_admin")),
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Manually assign a phlebotomist to an order with full validation."""

    # 1. Fetch order
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # 2. Order must be PENDING
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order status is {order.status.value}, must be pending",
        )

    # 3. Fetch phlebotomist
    phleb_result = await db.execute(
        select(Phlebotomist).where(Phlebotomist.id == payload.phlebotomist_id)
    )
    phleb = phleb_result.scalar_one_or_none()
    if phleb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phlebotomist not found",
        )

    # 4. Check is_available
    if not phleb.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phlebotomist is not available",
        )

    # 5. Check user is_active
    phleb_user_result = await db.execute(select(User).where(User.id == phleb.user_id))
    phleb_user = phleb_user_result.scalar_one_or_none()
    if phleb_user is None or not phleb_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phlebotomist user account is not active",
        )

    # 6. Zone validation
    pincode_result = await db.execute(
        select(Pincode).where(Pincode.id == order.pincode_id)
    )
    pincode_row = pincode_result.scalar_one()

    zone_check = await db.execute(
        select(PhlebotomistZoneAssignment).where(
            PhlebotomistZoneAssignment.phlebotomist_id == phleb.id,
            PhlebotomistZoneAssignment.zone_id == pincode_row.zone_id,
        )
    )
    if zone_check.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phlebotomist is not assigned to the order's zone",
        )

    # 7. Leave check for appointment date
    leave_result = await db.execute(
        select(PhlebotomistLeave).where(
            PhlebotomistLeave.phlebotomist_id == phleb.id,
            PhlebotomistLeave.date == order.appointment_date,
            PhlebotomistLeave.status == "approved",
        )
    )
    if leave_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phlebotomist is on leave for the appointment date",
        )

    # 8. Assign and update status
    order.assigned_phlebotomist_id = phleb.id
    order.status = OrderStatus.ASSIGNED
    order.assigned_at = datetime.now(UTC)

    # 9. Log status change
    history = OrderStatusHistory(
        order_id=order.id,
        status=OrderStatus.ASSIGNED,
        changed_by=user.id,
        notes=f"Manually assigned to phlebotomist {phleb.id}",
    )
    db.add(history)

    await db.commit()
    await db.refresh(order)
    return order


@router.post(
    "/{order_id}/reroute",
    response_model=OrderResponse,
)
async def reroute_order(
    order_id: uuid.UUID,
    payload: RerouteRequest,
    user: User = Depends(require_roles("super_admin", "city_admin")),
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Re-route an order to a different phlebotomist."""

    # 1. Fetch order
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # 2. Order must be ASSIGNED or ACCEPTED
    if order.status not in (OrderStatus.ASSIGNED, OrderStatus.ACCEPTED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order status is {order.status.value}, must be assigned or accepted",
        )

    # 3. Fetch new phlebotomist
    phleb_result = await db.execute(
        select(Phlebotomist).where(Phlebotomist.id == payload.new_phlebotomist_id)
    )
    phleb = phleb_result.scalar_one_or_none()
    if phleb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phlebotomist not found",
        )

    # 4. Check is_available
    if not phleb.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phlebotomist is not available",
        )

    # 5. Check user is_active
    phleb_user_result = await db.execute(select(User).where(User.id == phleb.user_id))
    phleb_user = phleb_user_result.scalar_one_or_none()
    if phleb_user is None or not phleb_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phlebotomist user account is not active",
        )

    # 6. Zone validation
    pincode_result = await db.execute(
        select(Pincode).where(Pincode.id == order.pincode_id)
    )
    pincode_row = pincode_result.scalar_one()

    zone_check = await db.execute(
        select(PhlebotomistZoneAssignment).where(
            PhlebotomistZoneAssignment.phlebotomist_id == phleb.id,
            PhlebotomistZoneAssignment.zone_id == pincode_row.zone_id,
        )
    )
    if zone_check.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phlebotomist is not assigned to the order's zone",
        )

    # 7. Leave check
    leave_result = await db.execute(
        select(PhlebotomistLeave).where(
            PhlebotomistLeave.phlebotomist_id == phleb.id,
            PhlebotomistLeave.date == order.appointment_date,
            PhlebotomistLeave.status == "approved",
        )
    )
    if leave_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phlebotomist is on leave for the appointment date",
        )

    # 8. Update assignment
    old_phleb_id = order.assigned_phlebotomist_id
    order.assigned_phlebotomist_id = phleb.id
    order.status = OrderStatus.ASSIGNED
    order.assigned_at = datetime.now(UTC)

    # 9. Log history with reroute reason
    history = OrderStatusHistory(
        order_id=order.id,
        status=OrderStatus.ASSIGNED,
        changed_by=user.id,
        notes=f"Rerouted from {old_phleb_id} to {phleb.id}: {payload.reason}",
    )
    db.add(history)

    await db.commit()
    await db.refresh(order)
    return order


@router.get(
    "/{order_id}/history",
    response_model=list[StatusHistoryResponse],
)
async def get_order_history(
    order_id: uuid.UUID,
    user: User = Depends(
        require_roles("super_admin", "city_admin", "client_user", "phlebotomist")
    ),
    db: AsyncSession = Depends(get_db),
) -> list[OrderStatusHistory]:
    """Return chronological list of status changes for an order."""
    order_result = await db.execute(select(Order.id).where(Order.id == order_id))
    if order_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    result = await db.execute(
        select(OrderStatusHistory)
        .where(OrderStatusHistory.order_id == order_id)
        .order_by(OrderStatusHistory.created_at.asc())
    )
    return list(result.scalars().all())


# Cancellable statuses — not IN_TRANSIT or beyond
_CANCELLABLE_STATUSES = {
    OrderStatus.PENDING,
    OrderStatus.ASSIGNED,
    OrderStatus.ACCEPTED,
}


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
)
async def cancel_order(
    order_id: uuid.UUID,
    payload: OrderCancelRequest,
    user: User = Depends(require_roles("super_admin", "city_admin", "client_user")),
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Cancel an order with a mandatory reason."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # RBAC: client_user can only cancel own orders
    if user.role == UserRole.CLIENT_USER:
        cu_result = await db.execute(
            select(ClientUser.client_id).where(ClientUser.user_id == user.id)
        )
        user_client_id = cu_result.scalar_one_or_none()
        if user_client_id is None or order.client_id != user_client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own orders",
            )

    if order.status not in _CANCELLABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order in {order.status.value} status",
        )

    order.status = OrderStatus.CANCELLED
    # Clear phlebotomist if was assigned
    if order.assigned_phlebotomist_id is not None:
        order.assigned_phlebotomist_id = None

    history = OrderStatusHistory(
        order_id=order.id,
        status=OrderStatus.CANCELLED,
        changed_by=user.id,
        notes=f"Cancelled: {payload.reason}",
    )
    db.add(history)

    await db.commit()
    await db.refresh(order)
    return order


@router.post(
    "/{order_id}/reschedule",
    response_model=OrderResponse,
)
async def reschedule_order(
    order_id: uuid.UUID,
    payload: OrderRescheduleRequest,
    user: User = Depends(require_roles("super_admin", "city_admin", "client_user")),
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Reschedule an order to a new date and time slot."""
    result = await db.execute(
        select(Order).options(selectinload(Order.pincode)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # RBAC: client_user can only reschedule own orders
    if user.role == UserRole.CLIENT_USER:
        cu_result = await db.execute(
            select(ClientUser.client_id).where(ClientUser.user_id == user.id)
        )
        user_client_id = cu_result.scalar_one_or_none()
        if user_client_id is None or order.client_id != user_client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only reschedule your own orders",
            )

    if order.status not in _CANCELLABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reschedule order in {order.status.value} status",
        )

    # Validate pincode still serviceable (not in NSA)
    # Get the pincode string from the related pincode record
    pincode_result = await db.execute(
        select(Pincode).where(Pincode.id == order.pincode_id)
    )
    pincode_row = pincode_result.scalar_one_or_none()
    if pincode_row is not None:
        nsa_result = await db.execute(
            select(NSARecord).where(
                NSARecord.pincode == pincode_row.pincode,
                NSARecord.is_active.is_(True),
            )
        )
        if nsa_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pincode is no longer serviceable",
            )

    old_date = order.appointment_date
    old_slot = order.appointment_time_slot

    order.appointment_date = payload.new_date
    order.appointment_time_slot = payload.new_time_slot

    # Reset status to PENDING if was ASSIGNED/ACCEPTED, clear phlebotomist
    if order.status in {OrderStatus.ASSIGNED, OrderStatus.ACCEPTED}:
        order.status = OrderStatus.PENDING
        order.assigned_phlebotomist_id = None

    history = OrderStatusHistory(
        order_id=order.id,
        status=order.status,
        changed_by=user.id,
        notes=(
            f"Rescheduled from {old_date} {old_slot}"
            f" to {payload.new_date} {payload.new_time_slot}"
        ),
    )
    db.add(history)

    await db.commit()
    await db.refresh(order)
    return order


# ── Phlebotomist helper ─────────────────────────────────────────────────


async def _get_order_for_phleb(
    order_id: uuid.UUID,
    user: User,
    db: AsyncSession,
    required_status: OrderStatus,
) -> Order:
    """Load order, verify the requesting phlebotomist owns it and status matches."""
    # Resolve phleb record
    phleb_result = await db.execute(
        select(Phlebotomist.id).where(Phlebotomist.user_id == user.id)
    )
    phleb_id = phleb_result.scalar_one_or_none()
    if phleb_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phlebotomist profile not found",
        )

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    if order.assigned_phlebotomist_id != phleb_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Order not assigned to you",
        )

    if order.status != required_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Order status must be {required_status.value},"
                f" got {order.status.value}"
            ),
        )

    return order


# ── Phlebotomist order action endpoints ─────────────────────────────────


@router.post(
    "/{order_id}/accept",
    response_model=StatusHistoryResponse,
)
async def accept_order(
    order_id: uuid.UUID,
    user: User = Depends(require_roles("phlebotomist")),
    db: AsyncSession = Depends(get_db),
) -> OrderStatusHistory:
    """Phlebotomist accepts an assigned order."""
    order = await _get_order_for_phleb(order_id, user, db, OrderStatus.ASSIGNED)

    order.status = OrderStatus.ACCEPTED
    order.accepted_at = datetime.now(UTC)

    history = OrderStatusHistory(
        order_id=order.id,
        status=OrderStatus.ACCEPTED,
        changed_by=user.id,
        notes="Order accepted by phlebotomist",
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)
    return history


@router.post(
    "/{order_id}/reject",
    response_model=StatusHistoryResponse,
)
async def reject_order(
    order_id: uuid.UUID,
    payload: RejectReason,
    user: User = Depends(require_roles("phlebotomist")),
    db: AsyncSession = Depends(get_db),
) -> OrderStatusHistory:
    """Phlebotomist rejects an assigned order, returning it to PENDING."""
    order = await _get_order_for_phleb(order_id, user, db, OrderStatus.ASSIGNED)

    order.status = OrderStatus.PENDING
    order.assigned_phlebotomist_id = None
    order.assigned_at = None

    history = OrderStatusHistory(
        order_id=order.id,
        status=OrderStatus.PENDING,
        changed_by=user.id,
        notes=f"Rejected by phlebotomist: {payload.reason}",
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)
    return history


@router.post(
    "/{order_id}/start-transit",
    response_model=StatusHistoryResponse,
)
async def start_transit(
    order_id: uuid.UUID,
    user: User = Depends(require_roles("phlebotomist")),
    db: AsyncSession = Depends(get_db),
) -> OrderStatusHistory:
    """Phlebotomist starts transit to patient location."""
    order = await _get_order_for_phleb(order_id, user, db, OrderStatus.ACCEPTED)

    order.status = OrderStatus.IN_TRANSIT

    history = OrderStatusHistory(
        order_id=order.id,
        status=OrderStatus.IN_TRANSIT,
        changed_by=user.id,
        notes="Phlebotomist in transit",
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)
    return history


@router.post(
    "/{order_id}/collect",
    response_model=StatusHistoryResponse,
)
async def collect_order(
    order_id: uuid.UUID,
    payload: CollectionData,
    user: User = Depends(require_roles("phlebotomist")),
    db: AsyncSession = Depends(get_db),
) -> OrderStatusHistory:
    """Phlebotomist marks sample as collected with payment and proof data."""
    order = await _get_order_for_phleb(order_id, user, db, OrderStatus.IN_TRANSIT)

    order.status = OrderStatus.COLLECTED
    order.collected_at = datetime.now(UTC)
    order.amount = payload.payment_amount
    order.payment_mode = PaymentMode(payload.payment_mode)
    order.collection_proof_url = payload.photo_url
    order.patient_signature_url = payload.signature_url

    history = OrderStatusHistory(
        order_id=order.id,
        status=OrderStatus.COLLECTED,
        changed_by=user.id,
        notes="Sample collected",
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)
    return history


# ---------------------------------------------------------------------------
# Bulk upload — task 6.9
# ---------------------------------------------------------------------------

_BULK_REQUIRED = {
    "patient_name",
    "patient_age",
    "patient_gender",
    "patient_phone",
    "appointment_date",
    "appointment_time",
    "pincode",
    "address",
    "package_code",
}


def _parse_rows(
    content: bytes, filename: str
) -> tuple[list[dict[str, str]], str | None]:
    """Return (rows, error).  Each row is a dict keyed by header column."""
    lower = filename.lower()
    if lower.endswith(".csv"):
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader), None
    if lower.endswith(".xlsx"):
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        try:
            headers = [str(h).strip().lower() if h else "" for h in next(rows_iter)]
        except StopIteration:
            return [], "File has no rows"
        rows: list[dict[str, str]] = []
        for vals in rows_iter:
            row = {
                headers[i]: (str(v).strip() if v is not None else "")
                for i, v in enumerate(vals)
                if i < len(headers)
            }
            rows.append(row)
        wb.close()
        return rows, None
    return [], "Unsupported file type. Use .csv or .xlsx"


@router.post(
    "/bulk-upload",
    response_model=BulkOrderUploadResult,
)
async def bulk_upload_orders(
    file: UploadFile = File(...),
    user: User = Depends(require_roles("super_admin", "city_admin")),
    db: AsyncSession = Depends(get_db),
) -> BulkOrderUploadResult:
    """Bulk-create orders from a CSV / XLSX file."""
    content = await file.read()
    fname = file.filename or "upload.csv"
    rows, parse_err = _parse_rows(content, fname)
    if parse_err:
        raise HTTPException(status_code=400, detail=parse_err)
    if not rows:
        raise HTTPException(status_code=400, detail="File contains no data rows")

    # Pre-fetch lookup tables
    pin_result = await db.execute(select(Pincode))
    pincode_map: dict[str, Pincode] = {p.pincode: p for p in pin_result.scalars()}

    nsa_result = await db.execute(
        select(NSARecord.pincode).where(NSARecord.is_active.is_(True))
    )
    nsa_pincodes: set[str] = {r[0] for r in nsa_result.all()}

    pkg_result = await db.execute(select(Package).where(Package.is_active.is_(True)))
    package_map: dict[str, Package] = {p.code: p for p in pkg_result.scalars()}

    errors: list[BulkRowError] = []
    created_ids: list[uuid.UUID] = []
    phone_re = re.compile(r"^\+?\d{10,13}$")

    for idx, row in enumerate(rows, start=2):  # row 1 = header
        # Normalise keys
        row = {k.strip().lower(): v for k, v in row.items()}
        row_errors: list[str] = []

        # Required fields
        for field in _BULK_REQUIRED:
            if not row.get(field):
                row_errors.append(f"Missing required field: {field}")

        if row_errors:
            errors.append(BulkRowError(row=idx, errors=row_errors))
            continue

        # Validate phone
        phone = row["patient_phone"].strip()
        if not phone_re.match(phone):
            row_errors.append(f"Invalid phone format: {phone}")

        # Validate gender
        gender = row["patient_gender"].strip().upper()
        if gender not in ("M", "F", "O"):
            row_errors.append(f"Invalid gender: {gender}. Must be M, F, or O")

        # Validate age
        try:
            age = int(float(row["patient_age"]))
            if age <= 0:
                row_errors.append("patient_age must be > 0")
        except (ValueError, TypeError):
            row_errors.append(f"Invalid patient_age: {row['patient_age']}")
            age = 0

        # Validate date
        try:
            appt_date = date.fromisoformat(row["appointment_date"].strip())
        except ValueError:
            row_errors.append(
                f"Invalid date format: {row['appointment_date']}. Use YYYY-MM-DD"
            )
            appt_date = None

        # Validate time
        appt_time = row["appointment_time"].strip()
        if not re.fullmatch(r"\d{2}:\d{2}", appt_time):
            row_errors.append(f"Invalid time format: {appt_time}. Use HH:MM")

        # Validate pincode
        pincode_str = row["pincode"].strip()
        if not re.fullmatch(r"\d{6}", pincode_str):
            row_errors.append(f"Pincode must be 6 digits: {pincode_str}")
        elif pincode_str not in pincode_map:
            row_errors.append(f"Pincode not found: {pincode_str}")
        elif pincode_str in nsa_pincodes:
            row_errors.append(f"Pincode {pincode_str} is non-serviceable")

        # Validate package_code
        pkg_code = row["package_code"].strip()
        if pkg_code not in package_map:
            row_errors.append(f"Package code not found: {pkg_code}")

        # Priority
        priority = row.get("priority", "normal").strip().lower() or "normal"
        if priority not in ("normal", "high"):
            row_errors.append(f"Invalid priority: {priority}")

        if row_errors:
            errors.append(BulkRowError(row=idx, errors=row_errors))
            continue

        # Create order
        pincode_row = pincode_map[pincode_str]
        pkg = package_map[pkg_code]
        booking_id = await _generate_booking_id(db, appt_date)  # type: ignore[arg-type]

        order = Order(
            booking_id=booking_id,
            client_id=user.id,  # bulk uploads attributed to uploader
            pincode_id=pincode_row.id,
            patient_title=PatientTitle.MR,  # default for bulk
            patient_name=row["patient_name"].strip(),
            patient_age=age,
            patient_gender=PatientGender(gender),
            patient_phone=phone,
            appointment_date=appt_date,
            appointment_time_slot=appt_time,
            address=row["address"].strip(),
            status=OrderStatus.PENDING,
            priority=OrderPriority(priority),
            special_instructions=row.get("special_instructions", "").strip() or None,
            payment_mode=PaymentMode.CASH,
            created_by=user.id,
        )
        db.add(order)

        # Link package
        from app.models.packages import OrderPackage

        op = OrderPackage(
            order_id=order.id,
            package_id=pkg.id,
            quantity=1,
            amount=float(pkg.base_price),
        )
        db.add(op)
        order.amount = float(pkg.base_price)

        history = OrderStatusHistory(
            order_id=order.id,
            status=OrderStatus.PENDING,
            changed_by=user.id,
            notes="Bulk upload",
        )
        db.add(history)
        created_ids.append(order.id)

    if created_ids:
        await db.commit()

    return BulkOrderUploadResult(
        total_rows=len(rows),
        successful=len(created_ids),
        failed=len(errors),
        errors=errors,
        created_order_ids=created_ids,
    )
