"""Attendance endpoints for phlebotomist check-in/check-out."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.api.deps import require_roles
from app.models.attendance import Attendance, AttendanceStatus
from app.models.users import User

router = APIRouter(prefix="/attendance", tags=["attendance"])


# ── Schemas ──────────────────────────────────────────────────────────


class CheckInRequest(BaseModel):
    latitude: float
    longitude: float
    timestamp: str | None = None


class CheckOutRequest(BaseModel):
    latitude: float
    longitude: float
    timestamp: str | None = None


class AttendanceResponse(BaseModel):
    id: str
    user_id: str
    date: str
    status: str
    check_in_time: str | None = None
    check_out_time: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None
    check_out_latitude: float | None = None
    check_out_longitude: float | None = None

    class Config:
        from_attributes = True


def _to_response(record: Attendance) -> AttendanceResponse:
    return AttendanceResponse(
        id=str(record.id),
        user_id=str(record.user_id),
        date=record.date.isoformat(),
        status=record.status.value,
        check_in_time=record.check_in_time.isoformat() if record.check_in_time else None,
        check_out_time=record.check_out_time.isoformat() if record.check_out_time else None,
        latitude=record.check_in_latitude,
        longitude=record.check_in_longitude,
        location_name=record.check_in_location_name,
        check_out_latitude=record.check_out_latitude,
        check_out_longitude=record.check_out_longitude,
    )


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/today", response_model=AttendanceResponse)
async def get_today_attendance(
    user: User = Depends(require_roles("phlebotomist")),
    db: AsyncSession = Depends(get_db),
) -> AttendanceResponse:
    """Get today's attendance record for the current phlebotomist."""
    today = date.today()
    result = await db.execute(
        select(Attendance).where(
            Attendance.user_id == user.id,
            Attendance.date == today,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No attendance record for today",
        )
    return _to_response(record)


@router.post("/check-in", response_model=AttendanceResponse)
async def check_in(
    data: CheckInRequest,
    user: User = Depends(require_roles("phlebotomist")),
    db: AsyncSession = Depends(get_db),
) -> AttendanceResponse:
    """Check in for today."""
    today = date.today()

    # Check if already checked in
    result = await db.execute(
        select(Attendance).where(
            Attendance.user_id == user.id,
            Attendance.date == today,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already checked in today",
        )

    now = datetime.now(timezone.utc)
    record = Attendance(
        user_id=user.id,
        date=today,
        status=AttendanceStatus.CHECKED_IN,
        check_in_time=now,
        check_in_latitude=data.latitude,
        check_in_longitude=data.longitude,
        check_in_location_name="Verified Location",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _to_response(record)


@router.post("/check-out", response_model=AttendanceResponse)
async def check_out(
    data: CheckOutRequest,
    user: User = Depends(require_roles("phlebotomist")),
    db: AsyncSession = Depends(get_db),
) -> AttendanceResponse:
    """Check out for today."""
    today = date.today()
    result = await db.execute(
        select(Attendance).where(
            Attendance.user_id == user.id,
            Attendance.date == today,
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must check in before checking out",
        )
    if record.check_out_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already checked out today",
        )

    now = datetime.now(timezone.utc)
    record.status = AttendanceStatus.CHECKED_OUT
    record.check_out_time = now
    record.check_out_latitude = data.latitude
    record.check_out_longitude = data.longitude
    record.check_out_location_name = "Verified Location"

    await db.commit()
    await db.refresh(record)
    return _to_response(record)


@router.get("/history", response_model=list[AttendanceResponse])
async def get_attendance_history(
    skip: int = 0,
    limit: int = 30,
    user: User = Depends(require_roles("phlebotomist")),
    db: AsyncSession = Depends(get_db),
) -> list[AttendanceResponse]:
    """Get attendance history for the current phlebotomist."""
    result = await db.execute(
        select(Attendance)
        .where(Attendance.user_id == user.id)
        .order_by(Attendance.date.desc())
        .offset(skip)
        .limit(limit)
    )
    records = list(result.scalars().all())
    return [_to_response(r) for r in records]
