"""Package/Test Master CRUD endpoints — task 7.1."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.packages import Package, SampleType
from app.models.users import User
from app.schemas.package import (
    PackageCreate,
    PackageListResponse,
    PackageResponse,
    PackageUpdate,
)

router = APIRouter(prefix="/packages", tags=["packages"])

_super_admin = require_roles("super_admin")


@router.post(
    "",
    response_model=PackageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_package(
    body: PackageCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_super_admin),
) -> Package:
    # Check code uniqueness
    existing = await db.execute(select(Package).where(Package.code == body.code))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Package with code '{body.code}' already exists",
        )

    data = body.model_dump()
    # Convert SampleType enums to strings for JSON storage
    data["sample_types"] = [st.value for st in data["sample_types"]]
    package = Package(**data)
    db.add(package)
    await db.commit()
    await db.refresh(package)
    return package


@router.get("", response_model=PackageListResponse)
async def list_packages(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    sample_type: SampleType | None = Query(None),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin", "city_admin")),
) -> dict:
    query = select(Package)
    count_query = select(func.count()).select_from(Package)

    if search:
        pattern = f"%{search}%"
        condition = Package.name.ilike(pattern) | Package.code.ilike(pattern)
        query = query.where(condition)
        count_query = count_query.where(condition)

    if is_active is not None:
        query = query.where(Package.is_active == is_active)
        count_query = count_query.where(Package.is_active == is_active)

    if sample_type is not None:
        # Filter packages whose sample_types JSON array contains the value
        json_condition = Package.sample_types.contains([sample_type.value])
        query = query.where(json_condition)
        count_query = count_query.where(json_condition)

    total = (await db.execute(count_query)).scalar_one()
    items = (
        (
            await db.execute(
                query.order_by(Package.created_at.desc()).offset(skip).limit(limit)
            )
        )
        .scalars()
        .all()
    )

    return {
        "items": items,
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit,
    }


@router.get("/{package_id}", response_model=PackageResponse)
async def get_package(
    package_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin", "city_admin")),
) -> Package:
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    return package


@router.put("/{package_id}", response_model=PackageResponse)
async def update_package(
    package_id: uuid.UUID,
    body: PackageUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_super_admin),
) -> Package:
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    update_data = body.model_dump(exclude_unset=True)

    # Check code uniqueness if updating code
    if "code" in update_data and update_data["code"] != package.code:
        existing = await db.execute(
            select(Package).where(Package.code == update_data["code"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Package with code '{update_data['code']}' already exists",
            )

    # Convert SampleType enums to strings for JSON storage
    if "sample_types" in update_data and update_data["sample_types"] is not None:
        update_data["sample_types"] = [st.value for st in update_data["sample_types"]]

    for field, value in update_data.items():
        setattr(package, field, value)

    await db.commit()
    await db.refresh(package)
    return package


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_package(
    package_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_super_admin),
) -> None:
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    package.is_active = False
    await db.commit()
