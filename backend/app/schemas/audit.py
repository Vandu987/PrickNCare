"""Audit log schemas — task 16.6."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None = None
    old_value: dict | None = None
    new_value: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_method: str
    request_path: str
    response_status: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListOut(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int


class AuditCleanupOut(BaseModel):
    deleted_count: int
    retention_days: int
    message: str
