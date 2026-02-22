"""Phlebotomist CRUD endpoints — tasks 4.4 & 4.5."""

from __future__ import annotations

import logging
import os
import secrets
import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_roles
from app.core.database import get_db
from app.models.phlebotomist_documents import PhlebotomistDocument
from app.models.phlebotomist_leaves import PhlebotomistLeave
from app.models.phlebotomist_locations import PhlebotomistLocation
from app.models.phlebotomists import Phlebotomist, PhlebotomistZoneAssignment
from app.models.users import User, UserRole
from app.schemas.phlebotomist import (
    AvailabilityUpdate,
    BankDetailsResponse,
    BankDetailsUpdate,
    LeaveListResponse,
    LeaveRequest,
    LeaveResponse,
    LocationHistoryResponse,
    LocationResponse,
    LocationUpdate,
    PerformanceMetricsResponse,
    PhlebotomistCreate,
    PhlebotomistDocumentListResponse,
    PhlebotomistDocumentResponse,
    PhlebotomistListResponse,
    PhlebotomistResponse,
    PhlebotomistUpdate,
    ZoneAssignmentResponse,
    ZoneAssignmentUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/phlebotomists", tags=["phlebotomists"])

_admin_roles = require_roles("super_admin", "city_admin")

# ── S3 upload helper ─────────────────────────────────────────────────────

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


async def _upload_to_s3(
    file: UploadFile,
    phlebotomist_id: uuid.UUID,
    doc_type: str,
) -> str:
    """Upload file to S3 or fall back to local storage."""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 5MB limit",
        )

    timestamp = int(datetime.now(UTC).timestamp())
    filename = f"{timestamp}_{file.filename}"
    s3_key = f"phlebotomists/{phlebotomist_id}/{doc_type}/{filename}"

    bucket = os.environ.get("S3_BUCKET_NAME")
    region = os.environ.get("AWS_REGION", "ap-south-1")

    if bucket:
        try:
            import boto3

            s3_client = boto3.client(
                "s3",
                region_name=region,
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            )
            s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=content,
                ContentType=file.content_type or "application/octet-stream",
            )
            return f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
        except (ImportError, Exception):
            logger.warning("S3 upload failed, falling back to local storage")

    # Local fallback
    local_dir = f"/tmp/phlebotomists/{phlebotomist_id}/{doc_type}"  # noqa: S108
    os.makedirs(local_dir, exist_ok=True)
    local_path = f"{local_dir}/{filename}"
    with open(local_path, "wb") as f:
        f.write(content)
    return local_path


# ── CRUD endpoints ───────────────────────────────────────────────────────


@router.post(
    "",
    response_model=PhlebotomistResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_phlebotomist(
    body: PhlebotomistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> Phlebotomist:
    # Check employee_id uniqueness
    existing = await db.execute(
        select(Phlebotomist).where(Phlebotomist.employee_id == body.employee_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Employee ID already exists")

    # Check phone uniqueness in users
    existing_user = await db.execute(select(User).where(User.phone == body.phone))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Phone already registered")

    # Generate temp password and create user
    temp_password = secrets.token_urlsafe(12)
    email = f"phleb_{body.employee_id}@prickncare.local"
    logger.info(
        "Temp password for phlebotomist %s: %s", body.employee_id, temp_password
    )

    user = User(
        email=email,
        phone=body.phone,
        role=UserRole.PHLEBOTOMIST,
    )
    user.set_password(temp_password)
    db.add(user)
    await db.flush()

    phlebotomist = Phlebotomist(
        user_id=user.id,
        employee_id=body.employee_id,
        name=body.name,
        phone=body.phone,
        working_hours_start=body.working_hours_start,
        working_hours_end=body.working_hours_end,
    )
    db.add(phlebotomist)
    await db.commit()
    await db.refresh(phlebotomist)
    return phlebotomist


@router.get("", response_model=PhlebotomistListResponse)
async def list_phlebotomists(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    is_available: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> dict:
    query = select(Phlebotomist)
    count_query = select(func.count()).select_from(Phlebotomist)

    if search:
        pattern = f"%{search}%"
        condition = (
            Phlebotomist.name.ilike(pattern)
            | Phlebotomist.employee_id.ilike(pattern)
            | Phlebotomist.phone.ilike(pattern)
        )
        query = query.where(condition)
        count_query = count_query.where(condition)

    if is_available is not None:
        query = query.where(Phlebotomist.is_available == is_available)
        count_query = count_query.where(Phlebotomist.is_available == is_available)

    total = (await db.execute(count_query)).scalar_one()
    items = (
        (
            await db.execute(
                query.order_by(Phlebotomist.created_at.desc()).offset(skip).limit(limit)
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


@router.get("/{phlebotomist_id}", response_model=PhlebotomistResponse)
async def get_phlebotomist(
    phlebotomist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> Phlebotomist:
    result = await db.execute(
        select(Phlebotomist).where(Phlebotomist.id == phlebotomist_id)
    )
    phlebotomist = result.scalar_one_or_none()
    if not phlebotomist:
        raise HTTPException(status_code=404, detail="Phlebotomist not found")
    return phlebotomist


@router.put("/{phlebotomist_id}", response_model=PhlebotomistResponse)
async def update_phlebotomist(
    phlebotomist_id: uuid.UUID,
    body: PhlebotomistUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> Phlebotomist:
    result = await db.execute(
        select(Phlebotomist).where(Phlebotomist.id == phlebotomist_id)
    )
    phlebotomist = result.scalar_one_or_none()
    if not phlebotomist:
        raise HTTPException(status_code=404, detail="Phlebotomist not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(phlebotomist, field, value)

    await db.commit()
    await db.refresh(phlebotomist)
    return phlebotomist


@router.delete("/{phlebotomist_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_phlebotomist(
    phlebotomist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> None:
    result = await db.execute(
        select(Phlebotomist).where(Phlebotomist.id == phlebotomist_id)
    )
    phlebotomist = result.scalar_one_or_none()
    if not phlebotomist:
        raise HTTPException(status_code=404, detail="Phlebotomist not found")

    # Soft delete: deactivate user and mark unavailable
    user_result = await db.execute(select(User).where(User.id == phlebotomist.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.is_active = False

    phlebotomist.is_available = False
    await db.commit()


# ── Document endpoints ───────────────────────────────────────────────────


@router.post(
    "/{phlebotomist_id}/documents",
    response_model=PhlebotomistDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    phlebotomist_id: uuid.UUID,
    doc_type: str = Query(..., regex="^(id_proof|certification|photo)$"),
    file: UploadFile = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> PhlebotomistDocument:
    # Verify phlebotomist exists
    result = await db.execute(
        select(Phlebotomist).where(Phlebotomist.id == phlebotomist_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Phlebotomist not found")

    # Validate file type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="File type not allowed. Accepted: jpg, png, pdf",
        )

    s3_url = await _upload_to_s3(file, phlebotomist_id, doc_type)

    doc = PhlebotomistDocument(
        phlebotomist_id=phlebotomist_id,
        doc_type=doc_type,
        s3_url=s3_url,
        original_filename=file.filename or "unknown",
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get(
    "/{phlebotomist_id}/documents",
    response_model=PhlebotomistDocumentListResponse,
)
async def list_documents(
    phlebotomist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> dict:
    # Verify phlebotomist exists
    result = await db.execute(
        select(Phlebotomist).where(Phlebotomist.id == phlebotomist_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Phlebotomist not found")

    items = (
        (
            await db.execute(
                select(PhlebotomistDocument).where(
                    PhlebotomistDocument.phlebotomist_id == phlebotomist_id
                )
            )
        )
        .scalars()
        .all()
    )

    return {"items": items}


@router.put(
    "/{phlebotomist_id}/documents/{doc_id}/verify",
    response_model=PhlebotomistDocumentResponse,
)
async def verify_document(
    phlebotomist_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> PhlebotomistDocument:
    result = await db.execute(
        select(PhlebotomistDocument).where(
            PhlebotomistDocument.id == doc_id,
            PhlebotomistDocument.phlebotomist_id == phlebotomist_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.verified = True
    doc.verified_by = current_user.id
    doc.verified_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(doc)
    return doc


# ── Helper: fetch phlebotomist or 404 ───────────────────────────────────


async def _get_phlebotomist(
    phlebotomist_id: uuid.UUID, db: AsyncSession
) -> Phlebotomist:
    result = await db.execute(
        select(Phlebotomist).where(Phlebotomist.id == phlebotomist_id)
    )
    phlebotomist = result.scalar_one_or_none()
    if not phlebotomist:
        raise HTTPException(status_code=404, detail="Phlebotomist not found")
    return phlebotomist


def _is_own_phlebotomist(user: User, phlebotomist: Phlebotomist) -> bool:
    return user.id == phlebotomist.user_id


def _check_own_or_admin(user: User, phlebotomist: Phlebotomist) -> None:
    if user.role.value in ("super_admin", "city_admin"):
        return
    if _is_own_phlebotomist(user, phlebotomist):
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions")


# ── Zone assignment endpoints — task 4.5 ─────────────────────────────────


@router.put(
    "/{phlebotomist_id}/zones",
    response_model=list[ZoneAssignmentResponse],
)
async def sync_zone_assignments(
    phlebotomist_id: uuid.UUID,
    body: ZoneAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> list[PhlebotomistZoneAssignment]:
    await _get_phlebotomist(phlebotomist_id, db)

    # Delete existing assignments
    await db.execute(
        delete(PhlebotomistZoneAssignment).where(
            PhlebotomistZoneAssignment.phlebotomist_id == phlebotomist_id
        )
    )

    # Insert new assignments
    now = datetime.now(UTC)
    assignments = []
    for zone_id in body.zone_ids:
        assignment = PhlebotomistZoneAssignment(
            phlebotomist_id=phlebotomist_id,
            zone_id=zone_id,
            assigned_at=now,
        )
        db.add(assignment)
        assignments.append(assignment)

    await db.commit()
    return assignments


@router.get(
    "/{phlebotomist_id}/zones",
    response_model=list[ZoneAssignmentResponse],
)
async def list_zone_assignments(
    phlebotomist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> list[PhlebotomistZoneAssignment]:
    await _get_phlebotomist(phlebotomist_id, db)

    result = await db.execute(
        select(PhlebotomistZoneAssignment).where(
            PhlebotomistZoneAssignment.phlebotomist_id == phlebotomist_id
        )
    )
    return list(result.scalars().all())


# ── Availability endpoint — task 4.5 ─────────────────────────────────────


@router.put(
    "/{phlebotomist_id}/availability",
    response_model=PhlebotomistResponse,
)
async def update_availability(
    phlebotomist_id: uuid.UUID,
    body: AvailabilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Phlebotomist:
    phlebotomist = await _get_phlebotomist(phlebotomist_id, db)
    _check_own_or_admin(current_user, phlebotomist)

    phlebotomist.is_available = body.is_available
    await db.commit()
    await db.refresh(phlebotomist)
    return phlebotomist


# ── Leave endpoints — task 4.5 ───────────────────────────────────────────


@router.post(
    "/{phlebotomist_id}/leave",
    response_model=LeaveResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_for_leave(
    phlebotomist_id: uuid.UUID,
    body: LeaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PhlebotomistLeave:
    phlebotomist = await _get_phlebotomist(phlebotomist_id, db)
    _check_own_or_admin(current_user, phlebotomist)

    leave = PhlebotomistLeave(
        phlebotomist_id=phlebotomist_id,
        date=body.date,
        reason=body.reason,
        leave_type=body.leave_type,
        status="pending",
    )
    db.add(leave)
    await db.commit()
    await db.refresh(leave)
    return leave


@router.get(
    "/{phlebotomist_id}/leave",
    response_model=LeaveListResponse,
)
async def list_leaves(
    phlebotomist_id: uuid.UUID,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    phlebotomist = await _get_phlebotomist(phlebotomist_id, db)
    _check_own_or_admin(current_user, phlebotomist)

    query = select(PhlebotomistLeave).where(
        PhlebotomistLeave.phlebotomist_id == phlebotomist_id
    )
    count_query = (
        select(func.count())
        .select_from(PhlebotomistLeave)
        .where(PhlebotomistLeave.phlebotomist_id == phlebotomist_id)
    )

    if date_from:
        query = query.where(PhlebotomistLeave.date >= date_from)
        count_query = count_query.where(PhlebotomistLeave.date >= date_from)
    if date_to:
        query = query.where(PhlebotomistLeave.date <= date_to)
        count_query = count_query.where(PhlebotomistLeave.date <= date_to)

    total = (await db.execute(count_query)).scalar_one()
    items = (
        (await db.execute(query.order_by(PhlebotomistLeave.date.desc())))
        .scalars()
        .all()
    )

    return {"items": items, "total": total}


@router.delete(
    "/{phlebotomist_id}/leave/{leave_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def cancel_leave(
    phlebotomist_id: uuid.UUID,
    leave_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    phlebotomist = await _get_phlebotomist(phlebotomist_id, db)
    _check_own_or_admin(current_user, phlebotomist)

    result = await db.execute(
        select(PhlebotomistLeave).where(
            PhlebotomistLeave.id == leave_id,
            PhlebotomistLeave.phlebotomist_id == phlebotomist_id,
        )
    )
    leave = result.scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")

    if leave.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending leaves can be cancelled",
        )

    leave.status = "cancelled"
    await db.commit()


# ── Bank details endpoints — task 4.5 ────────────────────────────────────


@router.put(
    "/{phlebotomist_id}/bank-details",
    response_model=BankDetailsResponse,
)
async def update_bank_details(
    phlebotomist_id: uuid.UUID,
    body: BankDetailsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> dict:
    phlebotomist = await _get_phlebotomist(phlebotomist_id, db)

    if body.account_number is not None:
        phlebotomist.bank_account_number = body.account_number
    if body.ifsc is not None:
        phlebotomist.bank_ifsc = body.ifsc
    if body.bank_name is not None:
        phlebotomist.bank_name = body.bank_name
    if body.upi_id is not None:
        phlebotomist.upi_id = body.upi_id

    await db.commit()
    await db.refresh(phlebotomist)

    return _mask_bank_details(phlebotomist)


@router.get(
    "/{phlebotomist_id}/bank-details",
    response_model=BankDetailsResponse,
)
async def get_bank_details(
    phlebotomist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    phlebotomist = await _get_phlebotomist(phlebotomist_id, db)

    # Allow admin or own phlebotomist
    if current_user.role.value not in ("super_admin", "city_admin"):
        if not _is_own_phlebotomist(current_user, phlebotomist):
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    return _mask_bank_details(phlebotomist)


# ── Location endpoints — task 4.6 ─────────────────────────────────────────


@router.put(
    "/{phlebotomist_id}/location",
    response_model=LocationResponse,
)
async def update_location(
    phlebotomist_id: uuid.UUID,
    body: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    phlebotomist = await _get_phlebotomist(phlebotomist_id, db)

    if not _is_own_phlebotomist(current_user, phlebotomist):
        raise HTTPException(status_code=403, detail="Can only update own location")

    now = datetime.now(UTC)

    # Update current location on phlebotomist
    phlebotomist.current_location_lat = body.lat
    phlebotomist.current_location_lng = body.lng

    # Store in location history
    location = PhlebotomistLocation(
        phlebotomist_id=phlebotomist_id,
        lat=body.lat,
        lng=body.lng,
        accuracy=body.accuracy,
        recorded_at=now,
    )
    db.add(location)
    await db.commit()

    return {
        "lat": body.lat,
        "lng": body.lng,
        "accuracy": body.accuracy,
        "recorded_at": now,
    }


@router.get(
    "/{phlebotomist_id}/location/current",
    response_model=LocationResponse,
)
async def get_current_location(
    phlebotomist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> dict:
    phlebotomist = await _get_phlebotomist(phlebotomist_id, db)

    if (
        phlebotomist.current_location_lat is None
        or phlebotomist.current_location_lng is None
    ):
        raise HTTPException(status_code=404, detail="No location data available")

    # Get latest record for accuracy and timestamp
    result = await db.execute(
        select(PhlebotomistLocation)
        .where(PhlebotomistLocation.phlebotomist_id == phlebotomist_id)
        .order_by(PhlebotomistLocation.recorded_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()

    return {
        "lat": phlebotomist.current_location_lat,
        "lng": phlebotomist.current_location_lng,
        "accuracy": latest.accuracy if latest else None,
        "recorded_at": latest.recorded_at if latest else datetime.now(UTC),
    }


@router.get(
    "/{phlebotomist_id}/location/history",
    response_model=LocationHistoryResponse,
)
async def get_location_history(
    phlebotomist_id: uuid.UUID,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> dict:
    await _get_phlebotomist(phlebotomist_id, db)

    query = select(PhlebotomistLocation).where(
        PhlebotomistLocation.phlebotomist_id == phlebotomist_id
    )
    count_query = (
        select(func.count())
        .select_from(PhlebotomistLocation)
        .where(PhlebotomistLocation.phlebotomist_id == phlebotomist_id)
    )

    if date_from:
        query = query.where(PhlebotomistLocation.recorded_at >= date_from)
        count_query = count_query.where(PhlebotomistLocation.recorded_at >= date_from)
    if date_to:
        query = query.where(PhlebotomistLocation.recorded_at <= date_to)
        count_query = count_query.where(PhlebotomistLocation.recorded_at <= date_to)

    total = (await db.execute(count_query)).scalar_one()
    items = (
        (
            await db.execute(
                query.order_by(PhlebotomistLocation.recorded_at.desc())
                .offset(skip)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    return {"items": items, "total": total}


# ── Performance metrics endpoint — task 4.6 ──────────────────────────────


@router.get(
    "/{phlebotomist_id}/metrics",
    response_model=PerformanceMetricsResponse,
)
async def get_performance_metrics(
    phlebotomist_id: uuid.UUID,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_admin_roles),
) -> PerformanceMetricsResponse:
    await _get_phlebotomist(phlebotomist_id, db)

    # Stub response — orders table integration comes in task 6
    return PerformanceMetricsResponse()


# ── Bank details helpers ─────────────────────────────────────────────────


def _mask_bank_details(phlebotomist: Phlebotomist) -> dict:
    account = phlebotomist.bank_account_number
    masked = None
    if account and len(account) >= 4:
        masked = "XXXX" + account[-4:]
    elif account:
        masked = "XXXX" + account

    return {
        "account_number": masked,
        "ifsc": phlebotomist.bank_ifsc,
        "bank_name": phlebotomist.bank_name,
        "upi_id": phlebotomist.upi_id,
    }
