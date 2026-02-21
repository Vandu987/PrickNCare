"""City CRUD endpoints — task 5.1."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.users import User
from app.models.zones import City
from app.schemas.zone import (
    CityCreate,
    CityListResponse,
    CityResponse,
    CityServiceableUpdate,
    CityUpdate,
)

router = APIRouter(prefix="/cities", tags=["cities"])


@router.post("", response_model=CityResponse, status_code=status.HTTP_201_CREATED)
async def create_city(
    body: CityCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> City:
    city = City(name=body.name, state=body.state)
    db.add(city)
    await db.commit()
    await db.refresh(city)
    return city


@router.get("", response_model=CityListResponse)
async def list_cities(
    is_serviceable: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin", "city_admin")),
) -> dict:
    query = select(City)
    count_query = select(func.count()).select_from(City)

    if is_serviceable is not None:
        query = query.where(City.is_serviceable == is_serviceable)
        count_query = count_query.where(City.is_serviceable == is_serviceable)

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(query.offset(skip).limit(limit).order_by(City.name))
    return {"items": list(result.scalars().all()), "total": total}


@router.get("/{city_id}", response_model=CityResponse)
async def get_city(
    city_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin", "city_admin")),
) -> City:
    result = await db.execute(select(City).where(City.id == city_id))
    city = result.scalar_one_or_none()
    if city is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="City not found"
        )
    return city


@router.put("/{city_id}", response_model=CityResponse)
async def update_city(
    city_id: uuid.UUID,
    body: CityUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> City:
    result = await db.execute(select(City).where(City.id == city_id))
    city = result.scalar_one_or_none()
    if city is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="City not found"
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(city, field, value)

    await db.commit()
    await db.refresh(city)
    return city


@router.put("/{city_id}/serviceable", response_model=CityResponse)
async def toggle_city_serviceable(
    city_id: uuid.UUID,
    body: CityServiceableUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> City:
    result = await db.execute(select(City).where(City.id == city_id))
    city = result.scalar_one_or_none()
    if city is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="City not found"
        )

    city.is_serviceable = body.is_serviceable
    await db.commit()
    await db.refresh(city)
    return city


@router.delete("/{city_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_city(
    city_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> None:
    result = await db.execute(select(City).where(City.id == city_id))
    city = result.scalar_one_or_none()
    if city is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="City not found"
        )

    # Eagerly load zones to check
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(City).where(City.id == city_id).options(selectinload(City.zones))
    )
    city = result.scalar_one()

    if city.zones:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete city with existing zones. Remove zones first.",
        )

    await db.delete(city)
    await db.commit()
