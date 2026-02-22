"""Notification template management & manual send — task 10.5."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.notifications import NotificationTemplate
from app.models.users import User
from app.schemas.notification import (
    ManualNotificationSend,
    NotificationTemplateCreate,
    NotificationTemplateListResponse,
    NotificationTemplateOut,
    NotificationTemplateUpdate,
)
from app.services.notifications.base import NotificationChannel, NotificationType
from app.services.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])

_super_admin = require_roles("super_admin")


@router.post(
    "/templates",
    response_model=NotificationTemplateOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    payload: NotificationTemplateCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_super_admin),
):
    template = NotificationTemplate(
        notification_type=payload.notification_type.value,
        channel=payload.channel.value,
        name=payload.name,
        subject=payload.subject,
        body_template=payload.body_template,
        is_active=payload.is_active,
    )
    db.add(template)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Template for this notification_type and channel already exists.",
        ) from exc
    await db.refresh(template)
    return template


@router.get("/templates", response_model=NotificationTemplateListResponse)
async def list_templates(
    notification_type: NotificationType | None = Query(None),
    channel: NotificationChannel | None = Query(None),
    is_active: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin", "city_admin")),
):
    q = select(NotificationTemplate).where(NotificationTemplate.is_deleted.is_(False))
    count_q = (
        select(func.count())
        .select_from(NotificationTemplate)
        .where(NotificationTemplate.is_deleted.is_(False))
    )

    if notification_type is not None:
        q = q.where(NotificationTemplate.notification_type == notification_type.value)
        count_q = count_q.where(
            NotificationTemplate.notification_type == notification_type.value
        )
    if channel is not None:
        q = q.where(NotificationTemplate.channel == channel.value)
        count_q = count_q.where(NotificationTemplate.channel == channel.value)
    if is_active is not None:
        q = q.where(NotificationTemplate.is_active == is_active)
        count_q = count_q.where(NotificationTemplate.is_active == is_active)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (
        (
            await db.execute(
                q.order_by(NotificationTemplate.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    return NotificationTemplateListResponse(items=rows, total=total)


@router.get("/templates/{template_id}", response_model=NotificationTemplateOut)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("super_admin", "city_admin")),
):
    row = await db.get(NotificationTemplate, template_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    return row


@router.put("/templates/{template_id}", response_model=NotificationTemplateOut)
async def update_template(
    template_id: uuid.UUID,
    payload: NotificationTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_super_admin),
):
    row = await db.get(NotificationTemplate, template_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(row, key, value)

    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_super_admin),
):
    row = await db.get(NotificationTemplate, template_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="Template not found")

    row.is_deleted = True
    await db.commit()


@router.post("/send", status_code=status.HTTP_200_OK)
async def manual_send_notification(
    payload: ManualNotificationSend,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_super_admin),
):
    recipient = payload.phone or payload.email
    if not recipient and not payload.recipient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one of recipient_id, phone, or email.",
        )

    if not recipient:
        recipient = str(payload.recipient_id)

    svc = NotificationService(db=db)
    results = await svc.send(
        notification_type=payload.notification_type,
        recipient=recipient,
        data=payload.data,
        channels=payload.channels,
        recipient_id=payload.recipient_id,
    )
    return {"results": results}
