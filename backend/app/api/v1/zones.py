"""City & Zone CRUD endpoints — tasks 5.1 & 5.2."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.users import User
from app.models.zones import City, Pincode, Zone
from app.schemas.zone import (
    CityCreate,
    CityListResponse,
    CityResponse,
    CityServiceableUpdate,
    CityUpdate,
    ZoneActiveUpdate,
    ZoneCreate,
    ZoneListResponse,
    ZoneResponse,
    ZoneUpdate,
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


# ── Zone CRUD endpoints — task 5.2 ──────────────────────────────────────

zone_router = APIRouter(prefix="/zones", tags=["zones"])


def _zone_to_response(zone: Zone, pincode_count: int) -> dict:
    return {
        "id": zone.id,
        "name": zone.name,
        "city_id": zone.city_id,
        "city_name": zone.city.name,
        "is_active": zone.is_active,
        "pincode_count": pincode_count,
        "created_at": zone.created_at,
        "updated_at": zone.updated_at,
    }


@zone_router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(
    body: ZoneCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> dict:
    # Validate city exists and is serviceable
    result = await db.execute(select(City).where(City.id == body.city_id))
    city = result.scalar_one_or_none()
    if city is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="City not found"
        )
    if not city.is_serviceable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="City is not serviceable",
        )

    zone = Zone(name=body.name, city_id=body.city_id)
    db.add(zone)
    await db.commit()
    await db.refresh(zone)

    # Attach city for response
    zone.city = city  # type: ignore[assignment]

    return _zone_to_response(zone, 0)


@zone_router.get("", response_model=ZoneListResponse)
async def list_zones(
    city_id: uuid.UUID | None = Query(None),
    is_active: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin", "city_admin")),
) -> dict:
    query = select(Zone).options(selectinload(Zone.city))
    count_query = select(func.count()).select_from(Zone)

    if city_id is not None:
        query = query.where(Zone.city_id == city_id)
        count_query = count_query.where(Zone.city_id == city_id)

    if is_active is not None:
        query = query.where(Zone.is_active == is_active)
        count_query = count_query.where(Zone.is_active == is_active)

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(query.offset(skip).limit(limit).order_by(Zone.name))
    zones = list(result.scalars().all())

    # Get pincode counts
    if zones:
        zone_ids = [z.id for z in zones]
        pc_query = (
            select(Pincode.zone_id, func.count().label("cnt"))
            .where(Pincode.zone_id.in_(zone_ids))
            .group_by(Pincode.zone_id)
        )
        pc_result = await db.execute(pc_query)
        pc_map = {row.zone_id: row.cnt for row in pc_result}
    else:
        pc_map = {}

    items = [_zone_to_response(z, pc_map.get(z.id, 0)) for z in zones]
    return {"items": items, "total": total}


@zone_router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin", "city_admin")),
) -> dict:
    result = await db.execute(
        select(Zone).where(Zone.id == zone_id).options(selectinload(Zone.city))
    )
    zone = result.scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found"
        )

    # Pincode count
    pc_result = await db.execute(
        select(func.count()).select_from(Pincode).where(Pincode.zone_id == zone_id)
    )
    pincode_count = pc_result.scalar_one()

    return _zone_to_response(zone, pincode_count)


@zone_router.put("/{zone_id}", response_model=ZoneResponse)
async def update_zone(
    zone_id: uuid.UUID,
    body: ZoneUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> dict:
    result = await db.execute(
        select(Zone).where(Zone.id == zone_id).options(selectinload(Zone.city))
    )
    zone = result.scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found"
        )

    update_data = body.model_dump(exclude_unset=True)

    # If city_id is being changed, validate the new city
    if "city_id" in update_data:
        city_result = await db.execute(
            select(City).where(City.id == update_data["city_id"])
        )
        city = city_result.scalar_one_or_none()
        if city is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="City not found"
            )

    for field, value in update_data.items():
        setattr(zone, field, value)

    await db.commit()
    await db.refresh(zone)

    # Reload with city
    result = await db.execute(
        select(Zone).where(Zone.id == zone.id).options(selectinload(Zone.city))
    )
    zone = result.scalar_one()

    pc_result = await db.execute(
        select(func.count()).select_from(Pincode).where(Pincode.zone_id == zone_id)
    )
    pincode_count = pc_result.scalar_one()

    return _zone_to_response(zone, pincode_count)


@zone_router.put("/{zone_id}/active", response_model=ZoneResponse)
async def toggle_zone_active(
    zone_id: uuid.UUID,
    body: ZoneActiveUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> dict:
    result = await db.execute(
        select(Zone).where(Zone.id == zone_id).options(selectinload(Zone.city))
    )
    zone = result.scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found"
        )

    zone.is_active = body.is_active
    await db.commit()
    await db.refresh(zone)

    result = await db.execute(
        select(Zone).where(Zone.id == zone.id).options(selectinload(Zone.city))
    )
    zone = result.scalar_one()

    pc_result = await db.execute(
        select(func.count()).select_from(Pincode).where(Pincode.zone_id == zone_id)
    )
    pincode_count = pc_result.scalar_one()

    return _zone_to_response(zone, pincode_count)


@zone_router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    zone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> None:
    result = await db.execute(
        select(Zone).where(Zone.id == zone_id).options(selectinload(Zone.pincodes))
    )
    zone = result.scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found"
        )

    # Check for active pincodes
    active_pincodes = [p for p in zone.pincodes if True]  # all pincodes are "active"
    if active_pincodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete zone with existing pincodes. Remove pincodes first.",
        )

    await db.delete(zone)
    await db.commit()
