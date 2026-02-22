"""Attendance endpoints for phlebotomist check-in/check-out."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.rbac import require_roles
from app.models.user import User

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
    check_in_time: str | None = None
    check_out_time: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None

    class Config:
        from_attributes = True


# ── In-memory store (replace with DB table later) ────────────────────
# Key: (user_id, date_str) → record dict
_attendance_store: dict[tuple[str, str], dict] = {}


def _today_str() -> str:
    return date.today().isoformat()


def _get_record(user_id: str) -> dict | None:
    return _attendance_store.get((user_id, _today_str()))


def _set_record(user_id: str, record: dict) -> None:
    _attendance_store[(user_id, _today_str())] = record


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/today", response_model=AttendanceResponse)
async def get_today_attendance(
    user: User = Depends(require_roles("phlebotomist")),
) -> AttendanceResponse:
    """Get today's attendance record for the current phlebotomist."""
    record = _get_record(str(user.id))
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No attendance record for today",
        )
    return AttendanceResponse(**record)


@router.post("/check-in", response_model=AttendanceResponse)
async def check_in(
    data: CheckInRequest,
    user: User = Depends(require_roles("phlebotomist")),
) -> AttendanceResponse:
    """Check in for today."""
    existing = _get_record(str(user.id))
    if existing and existing.get("check_in_time"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already checked in today",
        )

    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": str(uuid.uuid4()),
        "user_id": str(user.id),
        "date": _today_str(),
        "check_in_time": now,
        "check_out_time": None,
        "latitude": data.latitude,
        "longitude": data.longitude,
        "location_name": "Verified Location",
    }
    _set_record(str(user.id), record)
    return AttendanceResponse(**record)


@router.post("/check-out", response_model=AttendanceResponse)
async def check_out(
    data: CheckOutRequest,
    user: User = Depends(require_roles("phlebotomist")),
) -> AttendanceResponse:
    """Check out for today."""
    record = _get_record(str(user.id))
    if not record or not record.get("check_in_time"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must check in before checking out",
        )
    if record.get("check_out_time"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already checked out today",
        )

    now = datetime.now(timezone.utc).isoformat()
    record["check_out_time"] = now
    _set_record(str(user.id), record)
    return AttendanceResponse(**record)
