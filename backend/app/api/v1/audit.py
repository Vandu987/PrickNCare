"""Audit log API endpoints — task 16.6."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.config import settings
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.users import User
from app.schemas.audit import AuditCleanupOut, AuditLogListOut, AuditLogOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=AuditLogListOut)
async def list_audit_logs(
    user_id: uuid.UUID | None = Query(None),
    entity_type: str | None = Query(None),
    entity_id: uuid.UUID | None = Query(None),
    action: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_roles("super_admin")),
) -> AuditLogListOut:
    """List audit logs with filters. SUPER_ADMIN only."""
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
        count_stmt = count_stmt.where(AuditLog.user_id == user_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
        count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
        count_stmt = count_stmt.where(AuditLog.entity_id == entity_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= date_from)
        count_stmt = count_stmt.where(AuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= date_to)
        count_stmt = count_stmt.where(AuditLog.created_at <= date_to)

    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        stmt.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return AuditLogListOut(
        items=[AuditLogOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/logs/{log_id}", response_model=AuditLogOut)
async def get_audit_log(
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_roles("super_admin")),
) -> AuditLogOut:
    """Get single audit log detail."""
    row = await db.get(AuditLog, log_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )
    return AuditLogOut.model_validate(row)


@router.delete("/logs/cleanup", response_model=AuditCleanupOut)
async def cleanup_audit_logs(
    retention_days: int | None = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_roles("super_admin")),
) -> AuditCleanupOut:
    """Delete audit logs older than retention period. SUPER_ADMIN only."""
    days = retention_days or settings.AUDIT_RETENTION_DAYS
    cutoff = datetime.now(UTC) - timedelta(days=days)

    result = await db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
    await db.commit()

    return AuditCleanupOut(
        deleted_count=result.rowcount,
        retention_days=days,
        message=f"Deleted {result.rowcount} audit logs older than {days} days",
    )
