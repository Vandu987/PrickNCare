"""Package/Test Master CRUD endpoints — tasks 7.1 & 7.2."""

from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.packages import Package, SampleType
from app.models.users import User
from app.schemas.package import (
    BulkImportResult,
    PackageCreate,
    PackageListResponse,
    PackageResponse,
    PackageUpdate,
)

router = APIRouter(prefix="/packages", tags=["packages"])

_super_admin = require_roles("super_admin")


EXPECTED_COLUMNS = [
    "name",
    "code",
    "sample_types",
    "base_price",
    "description",
    "preparation_instructions",
    "tat_hours",
]

REQUIRED_FIELDS = {"name", "code", "base_price"}

_VALID_SAMPLE_TYPES = {st.value for st in SampleType}


def _parse_rows_from_csv(content: bytes) -> list[dict[str, str]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _parse_rows_from_xlsx(content: bytes) -> list[dict[str, str]]:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip().lower() if h else "" for h in next(rows_iter)]
    result: list[dict[str, str]] = []
    for row in rows_iter:
        record = {
            headers[i]: (str(row[i]).strip() if row[i] is not None else "")
            for i in range(len(headers))
            if i < len(row)
        }
        result.append(record)
    wb.close()
    return result


def _validate_and_build(
    row_num: int, row: dict[str, str], seen_codes: set[str]
) -> tuple[dict | None, list[dict]]:
    """Validate a single row. Returns (package_dict | None, errors)."""
    errors: list[dict] = []

    # Required fields
    for field in REQUIRED_FIELDS:
        val = row.get(field, "").strip()
        if not val:
            errors.append(
                {"row": row_num, "field": field, "message": f"{field} is required"}
            )

    # Code uniqueness within file
    code = row.get("code", "").strip()
    if code:
        if code in seen_codes:
            errors.append(
                {
                    "row": row_num,
                    "field": "code",
                    "message": f"Duplicate code '{code}' in file",
                }
            )
        seen_codes.add(code)

    # Numeric: base_price
    base_price_str = row.get("base_price", "").strip()
    base_price = 0.0
    if base_price_str:
        try:
            base_price = float(base_price_str)
            if base_price < 0:
                errors.append(
                    {
                        "row": row_num,
                        "field": "base_price",
                        "message": "base_price must be >= 0",
                    }
                )
        except ValueError:
            errors.append(
                {
                    "row": row_num,
                    "field": "base_price",
                    "message": "base_price must be numeric",
                }
            )

    # Numeric: tat_hours
    tat_str = row.get("tat_hours", "").strip()
    tat_hours = 24
    if tat_str:
        try:
            tat_hours = int(float(tat_str))
            if tat_hours < 0:
                errors.append(
                    {
                        "row": row_num,
                        "field": "tat_hours",
                        "message": "tat_hours must be >= 0",
                    }
                )
        except ValueError:
            errors.append(
                {
                    "row": row_num,
                    "field": "tat_hours",
                    "message": "tat_hours must be numeric",
                }
            )

    # Sample types
    sample_types_str = row.get("sample_types", "").strip()
    sample_types: list[str] = []
    if sample_types_str:
        for st in sample_types_str.split(","):
            st = st.strip()
            if st not in _VALID_SAMPLE_TYPES:
                errors.append(
                    {
                        "row": row_num,
                        "field": "sample_types",
                        "message": f"Invalid sample type '{st}'",
                    }
                )
            else:
                sample_types.append(st)

    if errors:
        return None, errors

    return {
        "name": row.get("name", "").strip(),
        "code": code,
        "description": row.get("description", "").strip() or None,
        "preparation_instructions": row.get("preparation_instructions", "").strip()
        or None,
        "tat_hours": tat_hours,
        "sample_types": sample_types,
        "base_price": base_price,
    }, []


@router.post("/bulk-import", response_model=BulkImportResult)
async def bulk_import_packages(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_super_admin),
) -> dict:
    filename = (file.filename or "").lower()
    content = await file.read()

    if filename.endswith(".csv"):
        rows = _parse_rows_from_csv(content)
    elif filename.endswith(".xlsx"):
        rows = _parse_rows_from_xlsx(content)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv and .xlsx files are supported",
        )

    if not rows:
        return {
            "total_rows": 0,
            "successful": 0,
            "failed": 0,
            "errors": [],
        }

    # Fetch existing codes from DB
    existing_result = await db.execute(select(Package.code))
    existing_codes = {r[0] for r in existing_result.all()}

    all_errors: list[dict] = []
    successful = 0
    seen_codes: set[str] = set()

    for idx, row in enumerate(rows, start=2):  # row 1 is header
        pkg_data, row_errors = _validate_and_build(idx, row, seen_codes)
        if row_errors:
            all_errors.extend(row_errors)
            continue

        assert pkg_data is not None
        if pkg_data["code"] in existing_codes:
            all_errors.append(
                {
                    "row": idx,
                    "field": "code",
                    "message": (
                        f"Package with code '{pkg_data['code']}'"
                        " already exists in database"
                    ),
                }
            )
            continue

        package = Package(**pkg_data)
        db.add(package)
        existing_codes.add(pkg_data["code"])
        successful += 1

    if successful > 0:
        await db.commit()

    return {
        "total_rows": len(rows),
        "successful": successful,
        "failed": len(rows) - successful,
        "errors": all_errors,
    }


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


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
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
