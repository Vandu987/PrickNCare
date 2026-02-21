"""City, Zone, Pincode & Locality CRUD endpoints — tasks 5.1–5.4."""

from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.users import User
from app.models.zones import City, Locality, Pincode, Zone
from app.schemas.zone import (
    BulkLocalityCreate,
    BulkPincodeCreate,
    CityCreate,
    CityListResponse,
    CityResponse,
    CityServiceableUpdate,
    CityUpdate,
    ImportSummaryResponse,
    LocalityCreate,
    LocalityListResponse,
    LocalityResponse,
    PincodeCreate,
    PincodeListResponse,
    PincodeResponse,
    PincodeSuggestion,
    PincodeZoneUpdate,
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


# ── Pincode CRUD endpoints — task 5.3 ───────────────────────────────────

pincode_router = APIRouter(prefix="/pincodes", tags=["pincodes"])


def _pincode_to_response(pincode: Pincode) -> dict:
    return {
        "id": pincode.id,
        "pincode": pincode.pincode,
        "zone_id": pincode.zone_id,
        "zone_name": pincode.zone.name,
        "created_at": pincode.created_at,
    }


@pincode_router.post(
    "", response_model=PincodeResponse, status_code=status.HTTP_201_CREATED
)
async def create_pincode(
    body: PincodeCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> dict:
    # Validate zone exists
    result = await db.execute(
        select(Zone).where(Zone.id == body.zone_id).options(selectinload(Zone.city))
    )
    zone = result.scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found"
        )

    # Check uniqueness
    existing = await db.execute(select(Pincode).where(Pincode.pincode == body.pincode))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pincode {body.pincode} already exists",
        )

    pincode = Pincode(pincode=body.pincode, zone_id=body.zone_id)
    db.add(pincode)
    await db.commit()
    await db.refresh(pincode)

    return {
        "id": pincode.id,
        "pincode": pincode.pincode,
        "zone_id": pincode.zone_id,
        "zone_name": zone.name,
        "created_at": pincode.created_at,
    }


@pincode_router.post("/bulk", response_model=ImportSummaryResponse)
async def bulk_create_pincodes(
    body: BulkPincodeCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> dict:
    created = 0
    errors = 0
    error_details: list[str] = []

    for item in body.pincodes:
        # Check zone exists
        zone_result = await db.execute(select(Zone).where(Zone.id == item.zone_id))
        if zone_result.scalar_one_or_none() is None:
            errors += 1
            error_details.append(f"Zone not found for pincode {item.pincode}")
            continue

        # Skip duplicates
        existing = await db.execute(
            select(Pincode).where(Pincode.pincode == item.pincode)
        )
        if existing.scalar_one_or_none() is not None:
            errors += 1
            error_details.append(f"Pincode {item.pincode} already exists, skipped")
            continue

        pincode = Pincode(pincode=item.pincode, zone_id=item.zone_id)
        db.add(pincode)
        created += 1

    await db.commit()

    return {
        "total_rows": len(body.pincodes),
        "created": created,
        "errors": errors,
        "error_details": error_details,
    }


@pincode_router.get("", response_model=PincodeListResponse)
async def list_pincodes(
    zone_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin", "city_admin")),
) -> dict:
    query = select(Pincode).options(selectinload(Pincode.zone))
    count_query = select(func.count()).select_from(Pincode)

    if zone_id is not None:
        query = query.where(Pincode.zone_id == zone_id)
        count_query = count_query.where(Pincode.zone_id == zone_id)

    if search:
        query = query.where(Pincode.pincode.ilike(f"{search}%"))
        count_query = count_query.where(Pincode.pincode.ilike(f"{search}%"))

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(query.offset(skip).limit(limit).order_by(Pincode.pincode))
    pincodes = list(result.scalars().all())

    items = [_pincode_to_response(p) for p in pincodes]
    return {"items": items, "total": total}


@pincode_router.get("/suggest", response_model=list[PincodeSuggestion])
async def suggest_pincodes(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(Pincode)
        .where(Pincode.pincode.ilike(f"{q}%"))
        .options(selectinload(Pincode.zone).selectinload(Zone.city))
        .limit(10)
        .order_by(Pincode.pincode)
    )
    pincodes = list(result.scalars().all())

    return [
        {
            "id": p.id,
            "pincode": p.pincode,
            "zone_name": p.zone.name,
            "city_name": p.zone.city.name,
        }
        for p in pincodes
    ]


@pincode_router.put("/{pincode_id}/zone", response_model=PincodeResponse)
async def reassign_pincode_zone(
    pincode_id: uuid.UUID,
    body: PincodeZoneUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> dict:
    result = await db.execute(
        select(Pincode)
        .where(Pincode.id == pincode_id)
        .options(selectinload(Pincode.zone))
    )
    pincode = result.scalar_one_or_none()
    if pincode is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pincode not found"
        )

    # Validate new zone exists
    zone_result = await db.execute(
        select(Zone).where(Zone.id == body.zone_id).options(selectinload(Zone.city))
    )
    zone = zone_result.scalar_one_or_none()
    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found"
        )

    pincode.zone_id = body.zone_id
    await db.commit()
    await db.refresh(pincode)

    return {
        "id": pincode.id,
        "pincode": pincode.pincode,
        "zone_id": pincode.zone_id,
        "zone_name": zone.name,
        "created_at": pincode.created_at,
    }


@zone_router.post("/import", response_model=ImportSummaryResponse)
async def import_zones_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> dict:
    """Import cities, zones, pincodes, and localities from a CSV file.

    Expected columns: city, zone, pincode, locality
    Auto-creates cities and zones if they don't exist.
    """
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded CSV",
        ) from None

    reader = csv.DictReader(io.StringIO(text))

    # Validate required columns
    if reader.fieldnames is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty CSV file"
        )
    required_cols = {"city", "zone", "pincode"}
    missing = required_cols - {f.strip().lower() for f in reader.fieldnames}
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(missing)}",
        )

    # Normalize field names
    field_map = {f.strip().lower(): f for f in reader.fieldnames}

    created = 0
    errors = 0
    error_details: list[str] = []
    total_rows = 0

    # Caches to avoid repeated lookups
    city_cache: dict[str, City] = {}
    zone_cache: dict[tuple[str, str], Zone] = {}

    for row_num, row in enumerate(reader, start=2):
        total_rows += 1

        city_name = (row.get(field_map.get("city", "city")) or "").strip()
        zone_name = (row.get(field_map.get("zone", "zone")) or "").strip()
        pincode_val = (row.get(field_map.get("pincode", "pincode")) or "").strip()
        locality_name = (
            row.get(field_map.get("locality", "locality"), "") or ""
        ).strip()

        if not city_name or not zone_name or not pincode_val:
            errors += 1
            error_details.append(f"Row {row_num}: missing city, zone, or pincode")
            continue

        # Validate pincode format
        import re

        if not re.fullmatch(r"\d{6}", pincode_val):
            errors += 1
            error_details.append(f"Row {row_num}: invalid pincode '{pincode_val}'")
            continue

        # Get or create city
        city_key = city_name.lower()
        if city_key not in city_cache:
            result = await db.execute(
                select(City).where(func.lower(City.name) == city_key)
            )
            city = result.scalar_one_or_none()
            if city is None:
                city = City(name=city_name, state="")
                db.add(city)
                await db.flush()
            city_cache[city_key] = city

        city = city_cache[city_key]

        # Get or create zone
        zone_key = (city_key, zone_name.lower())
        if zone_key not in zone_cache:
            result = await db.execute(
                select(Zone).where(
                    Zone.city_id == city.id,
                    func.lower(Zone.name) == zone_name.lower(),
                )
            )
            zone = result.scalar_one_or_none()
            if zone is None:
                zone = Zone(name=zone_name, city_id=city.id)
                db.add(zone)
                await db.flush()
            zone_cache[zone_key] = zone

        zone = zone_cache[zone_key]

        # Create pincode (skip if exists)
        existing = await db.execute(
            select(Pincode).where(Pincode.pincode == pincode_val)
        )
        existing_pincode = existing.scalar_one_or_none()
        if existing_pincode is None:
            pincode_obj = Pincode(pincode=pincode_val, zone_id=zone.id)
            db.add(pincode_obj)
            await db.flush()
            created += 1
        else:
            pincode_obj = existing_pincode

        # Create locality if provided (skip if exists)
        if locality_name:
            loc_existing = await db.execute(
                select(Locality).where(
                    Locality.pincode_id == pincode_obj.id,
                    func.lower(Locality.name) == locality_name.lower(),
                )
            )
            if loc_existing.scalar_one_or_none() is None:
                locality = Locality(name=locality_name, pincode_id=pincode_obj.id)
                db.add(locality)

    await db.commit()

    return {
        "total_rows": total_rows,
        "created": created,
        "errors": errors,
        "error_details": error_details,
    }


# ── Locality CRUD endpoints — task 5.4 ──────────────────────────────────

locality_router = APIRouter(prefix="/localities", tags=["localities"])


def _locality_to_response(loc: Locality) -> dict:
    return {
        "id": loc.id,
        "name": loc.name,
        "pincode_id": loc.pincode_id,
        "pincode": loc.pincode.pincode,
        "zone_name": loc.pincode.zone.name,
    }


@locality_router.post(
    "", response_model=LocalityResponse, status_code=status.HTTP_201_CREATED
)
async def create_locality(
    body: LocalityCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> dict:
    # Validate pincode exists
    result = await db.execute(
        select(Pincode)
        .where(Pincode.id == body.pincode_id)
        .options(selectinload(Pincode.zone))
    )
    pincode = result.scalar_one_or_none()
    if pincode is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pincode not found"
        )

    # Check uniqueness
    existing = await db.execute(
        select(Locality).where(
            Locality.pincode_id == body.pincode_id,
            func.lower(Locality.name) == body.name.strip().lower(),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Locality '{body.name}' already exists for this pincode",
        )

    locality = Locality(name=body.name.strip(), pincode_id=body.pincode_id)
    db.add(locality)
    await db.commit()
    await db.refresh(locality)

    return {
        "id": locality.id,
        "name": locality.name,
        "pincode_id": locality.pincode_id,
        "pincode": pincode.pincode,
        "zone_name": pincode.zone.name,
    }


@locality_router.post("/bulk", response_model=ImportSummaryResponse)
async def bulk_create_localities(
    body: BulkLocalityCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin")),
) -> dict:
    created = 0
    errors = 0
    error_details: list[str] = []

    for item in body.localities:
        # Check pincode exists
        pc_result = await db.execute(
            select(Pincode).where(Pincode.id == item.pincode_id)
        )
        if pc_result.scalar_one_or_none() is None:
            errors += 1
            error_details.append(f"Pincode not found for locality '{item.name}'")
            continue

        # Skip duplicates
        existing = await db.execute(
            select(Locality).where(
                Locality.pincode_id == item.pincode_id,
                func.lower(Locality.name) == item.name.strip().lower(),
            )
        )
        if existing.scalar_one_or_none() is not None:
            errors += 1
            error_details.append(f"Locality '{item.name}' already exists, skipped")
            continue

        locality = Locality(name=item.name.strip(), pincode_id=item.pincode_id)
        db.add(locality)
        created += 1

    await db.commit()

    return {
        "total_rows": len(body.localities),
        "created": created,
        "errors": errors,
        "error_details": error_details,
    }


@locality_router.get("", response_model=LocalityListResponse)
async def list_localities(
    pincode_id: uuid.UUID | None = Query(None),
    pincode: str | None = Query(None),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin", "city_admin")),
) -> dict:
    query = select(Locality).options(
        selectinload(Locality.pincode).selectinload(Pincode.zone)
    )
    count_query = select(func.count()).select_from(Locality)

    if pincode_id is not None:
        query = query.where(Locality.pincode_id == pincode_id)
        count_query = count_query.where(Locality.pincode_id == pincode_id)

    if pincode is not None:
        query = query.join(Pincode).where(Pincode.pincode == pincode)
        count_query = count_query.join(Pincode).where(Pincode.pincode == pincode)

    if search:
        query = query.where(Locality.name.ilike(f"%{search}%"))
        count_query = count_query.where(Locality.name.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(query.offset(skip).limit(limit).order_by(Locality.name))
    localities = list(result.scalars().all())

    items = [_locality_to_response(loc) for loc in localities]
    return {"items": items, "total": total}


@locality_router.get("/by-pincode/{pincode}")
async def get_localities_by_pincode(
    pincode: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get all localities for a pincode string. No auth required (for order forms)."""
    result = await db.execute(
        select(Locality)
        .join(Pincode)
        .where(Pincode.pincode == pincode)
        .options(selectinload(Locality.pincode).selectinload(Pincode.zone))
        .order_by(Locality.name)
    )
    localities = list(result.scalars().all())

    return [_locality_to_response(loc) for loc in localities]
