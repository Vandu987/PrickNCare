"""Audit logging service — task 16.1.

Provides a thin async wrapper around the AuditLog model for persisting
audit records from middleware and application code.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Persist audit log entries to the database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log(
        self,
        *,
        action: str,
        entity_type: str,
        request_method: str = "UNKNOWN",
        request_path: str = "/",
        response_status: int = 0,
        user_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Create and flush an audit log entry."""
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            response_status=response_status,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry
