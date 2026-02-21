"""Client CRUD endpoints — task 4.1."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.client_rate_history import ClientRateHistory
from app.models.clients import Client
from app.models.users import User
from app.schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientRateHistoryListResponse,
    ClientRateUpdate,
    ClientResponse,
    ClientUpdate,
)

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
