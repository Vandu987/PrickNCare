"""Client CRUD endpoints — task 4.1."""

from __future__ import annotations

import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.client_rate_history import ClientRateHistory
from app.models.clients import Client, ClientUser
from app.models.users import User, UserRole
from app.schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientRateHistoryListResponse,
    ClientRateUpdate,
    ClientResponse,
    ClientUpdate,
    ClientUserCreate,
    ClientUserListResponse,
    ClientUserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clients", tags=["clients"])

# Reusable role deps
_admin_roles = require_roles("super_admin", "city_admin")
_read_roles = require_roles("super_admin", "city_admin", "client_user")


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_client(
    body: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> Client:
    client = Client(**body.model_dump(), created_by=current_user.id)
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


@router.get("", response_model=ClientListResponse)
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    city: str | None = Query(None),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_read_roles),
) -> dict:
    query = select(Client)
    count_query = select(func.count()).select_from(Client)

    # Filters
    if search:
        pattern = f"%{search}%"
        condition = Client.name.ilike(pattern) | Client.gst_number.ilike(pattern)
        query = query.where(condition)
        count_query = count_query.where(condition)

    if city:
        query = query.where(Client.city.ilike(city))
        count_query = count_query.where(Client.city.ilike(city))

    if is_active is not None:
        query = query.where(Client.is_active == is_active)
        count_query = count_query.where(Client.is_active == is_active)

    total = (await db.execute(count_query)).scalar_one()
    items = (
        (
            await db.execute(
                query.order_by(Client.created_at.desc()).offset(skip).limit(limit)
            )
        )
        .scalars()
        .all()
    )

    page = (skip // limit) + 1

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": limit,
    }


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_read_roles),
) -> Client:
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> Client:
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(client, field, value)

    await db.commit()
    await db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> None:
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    client.is_active = False
    await db.commit()


# ── Rate endpoints (task 4.2) ────────────────────────────────────────────

_rate_fields = (
    "rate_first_collection",
    "rate_second_collection",
    "rate_priority",
    "credit_limit",
)


@router.put("/{client_id}/rates", response_model=ClientResponse)
async def update_client_rates(
    client_id: uuid.UUID,
    body: ClientRateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> Client:
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Validate credit_limit required for postpaid clients
    from app.models.clients import PaymentTerms

    if client.payment_terms == PaymentTerms.POSTPAID and "credit_limit" not in updates:
        # Check if any rate is being updated without credit_limit for postpaid
        pass  # credit_limit is only required if not already set
    if (
        client.payment_terms == PaymentTerms.POSTPAID
        and "credit_limit" in updates
        and updates["credit_limit"] is None
    ):
        raise HTTPException(
            status_code=400,
            detail="credit_limit is required for postpaid clients",
        )

    for field in _rate_fields:
        if field not in updates:
            continue
        old_value = float(getattr(client, field))
        new_value = float(updates[field])
        if old_value != new_value:
            history = ClientRateHistory(
                client_id=client.id,
                field_name=field,
                previous_value=old_value,
                new_value=new_value,
                changed_by=current_user.id,
            )
            db.add(history)
            setattr(client, field, new_value)

    await db.commit()
    await db.refresh(client)
    return client


@router.get("/{client_id}/rates")
async def get_client_rates(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_read_roles),
) -> dict:
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return {
        "rate_first_collection": float(client.rate_first_collection),
        "rate_second_collection": float(client.rate_second_collection),
        "rate_priority": float(client.rate_priority),
        "credit_limit": float(client.credit_limit),
    }


@router.get(
    "/{client_id}/rates/history",
    response_model=ClientRateHistoryListResponse,
)
async def get_client_rate_history(
    client_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> dict:
    # Verify client exists
    result = await db.execute(select(Client).where(Client.id == client_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Client not found")

    count_q = (
        select(func.count())
        .select_from(ClientRateHistory)
        .where(ClientRateHistory.client_id == client_id)
    )
    total = (await db.execute(count_q)).scalar_one()

    items_q = (
        select(ClientRateHistory)
        .where(ClientRateHistory.client_id == client_id)
        .order_by(ClientRateHistory.effective_date.desc())
        .offset(skip)
        .limit(limit)
    )
    items = (await db.execute(items_q)).scalars().all()

    return {
        "items": items,
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit,
    }


# ── ClientUser endpoints (task 4.3) ─────────────────────────────────────


def _client_user_to_response(cu: ClientUser) -> dict:
    """Flatten ClientUser + User into ClientUserResponse shape."""
    return {
        "id": cu.id,
        "client_id": cu.client_id,
        "user_id": cu.user_id,
        "is_primary": cu.is_primary,
        "email": cu.user.email,
        "phone": cu.user.phone,
        "is_active": cu.user.is_active,
    }


@router.post(
    "/{client_id}/users",
    response_model=ClientUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_client_user(
    client_id: uuid.UUID,
    body: ClientUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> dict:
    # Verify client exists
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Validate email uniqueness
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate temp password
    temp_password = secrets.token_urlsafe(12)
    logger.info("Temp password for %s: %s", body.email, temp_password)

    # Create user
    user = User(
        email=body.email,
        phone=body.phone,
        role=UserRole.CLIENT_USER,
    )
    user.set_password(temp_password)
    db.add(user)
    await db.flush()

    # Create client-user link
    client_user = ClientUser(
        client_id=client_id,
        user_id=user.id,
        is_primary=body.is_primary,
    )
    db.add(client_user)
    await db.commit()
    await db.refresh(client_user)
    await db.refresh(user)

    return _client_user_to_response(client_user)


@router.get("/{client_id}/users", response_model=ClientUserListResponse)
async def list_client_users(
    client_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_read_roles),
) -> dict:
    # Verify client exists
    result = await db.execute(select(Client).where(Client.id == client_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Client not found")

    # client_user can only see their own org
    if current_user.role == UserRole.CLIENT_USER:
        own_link = await db.execute(
            select(ClientUser).where(
                ClientUser.client_id == client_id,
                ClientUser.user_id == current_user.id,
            )
        )
        if not own_link.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    base = select(ClientUser).where(ClientUser.client_id == client_id)

    count_q = (
        select(func.count())
        .select_from(ClientUser)
        .where(ClientUser.client_id == client_id)
    )
    total = (await db.execute(count_q)).scalar_one()

    items_q = base.offset(skip).limit(limit)
    rows = (await db.execute(items_q)).scalars().all()

    # Eagerly load user relationships
    for cu in rows:
        await db.refresh(cu, ["user"])

    return {
        "items": [_client_user_to_response(cu) for cu in rows],
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit,
    }


@router.delete(
    "/{client_id}/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_client_user(
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> None:
    # Find client-user link
    result = await db.execute(
        select(ClientUser).where(
            ClientUser.client_id == client_id,
            ClientUser.user_id == user_id,
        )
    )
    client_user = result.scalar_one_or_none()
    if not client_user:
        raise HTTPException(status_code=404, detail="Client user not found")

    # Deactivate the user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.is_active = False

    # Remove the link
    await db.delete(client_user)
    await db.commit()
