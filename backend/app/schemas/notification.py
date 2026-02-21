"""Notification schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.services.notifications.base import (
    NotificationChannel,
    NotificationType,
)


class NotificationSend(BaseModel):
    notification_type: NotificationType
    recipient: str
    data: dict | None = None
    channels: list[NotificationChannel] | None = None
    recipient_id: uuid.UUID | None = None


class NotificationTemplateCreate(BaseModel):
    notification_type: NotificationType
    channel: NotificationChannel
    name: str
    subject: str | None = None
    body_template: str
    is_active: bool = True


class NotificationTemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    body_template: str | None = None
    is_active: bool | None = None


class NotificationTemplateOut(BaseModel):
    id: uuid.UUID
    notification_type: NotificationType
    channel: NotificationChannel
    name: str
    subject: str | None = None
    body_template: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationTemplateListResponse(BaseModel):
    items: list[NotificationTemplateOut]
    total: int


class ManualNotificationSend(BaseModel):
    notification_type: NotificationType
    recipient_id: uuid.UUID | None = None
    phone: str | None = None
    email: str | None = None
    data: dict | None = None
    channels: list[NotificationChannel] | None = None


class NotificationLogOut(BaseModel):
    id: uuid.UUID
    notification_type: str
    channel: str
    recipient_id: uuid.UUID | None = None
    recipient_phone: str | None = None
    recipient_email: str | None = None
    status: str
    message_content: str | None = None
    error_message: str | None = None
    sent_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
