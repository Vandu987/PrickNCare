"""Push notification sender using Firebase Cloud Messaging (HTTP v1 API)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

from .base import BaseChannelSender, NotificationChannel

logger = logging.getLogger(__name__)

# FCM HTTP v1 endpoint template
_FCM_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

# Transient HTTP status codes worth retrying
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Max retry attempts for transient failures
_MAX_RETRIES = 3


def _load_credentials(path: str | None) -> dict[str, Any] | None:
    """Load FCM service-account JSON from *path*, or return None."""
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        logger.warning("FCM credentials file not found: %s", path)
        return None
    try:
        return json.loads(p.read_text())  # type: ignore[no-any-return]
    except Exception:
        logger.exception("Failed to read FCM credentials from %s", path)
        return None


def _get_access_token(creds: dict[str, Any]) -> str:
    """Obtain a short-lived OAuth2 access token from service-account creds.

    Uses ``google.oauth2.service_account`` if available; raises
    ``RuntimeError`` otherwise.
    """
    try:
        from google.auth.transport.requests import (
            Request,  # type: ignore[import-untyped]
        )
        from google.oauth2 import service_account as sa  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "google-auth package is required for FCM push notifications"
        ) from exc

    credentials = sa.Credentials.from_service_account_info(
        creds,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"],
    )
    credentials.refresh(Request())
    return credentials.token  # type: ignore[return-value]


class PushNotificationService(BaseChannelSender):
    """Send push notifications via Firebase Cloud Messaging HTTP v1 API."""

    channel = NotificationChannel.PUSH

    def __init__(self) -> None:
        self._project_id: str | None = getattr(settings, "FCM_PROJECT_ID", None) or None
        self._creds_path: str | None = (
            getattr(settings, "FCM_CREDENTIALS_PATH", None) or None
        )
        self._credentials: dict[str, Any] | None = _load_credentials(self._creds_path)
        self._configured = bool(self._project_id and self._credentials)

        if not self._configured:
            logger.info(
                "FCM push notifications not configured — operating as stub. "
                "Set FCM_PROJECT_ID and FCM_CREDENTIALS_PATH to enable.",
            )

    # -- public API (BaseChannelSender) ------------------------------------

    async def send(
        self,
        recipient: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send a push notification.

        *recipient* is an FCM device token **or** a topic name prefixed with
        ``/topics/``.
        *message* is used as the notification body; the ``title`` key in
        *data* provides the title (defaults to ``"PricknCare"``).
        """
        if not self._configured:
            logger.info("STUB [push] -> %s: %s", recipient, message[:100])
            return True

        data = data or {}
        title = str(data.pop("title", "PricknCare"))

        payload = self._build_payload(recipient, title, message, data)
        return await self._send_with_retry(payload)

    # -- topic helper ------------------------------------------------------

    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Convenience wrapper to send to an FCM topic."""
        return await self.send(
            recipient=f"/topics/{topic}",
            message=body,
            data={**(data or {}), "title": title},
        )

    # -- internals ---------------------------------------------------------

    def _build_payload(
        self,
        recipient: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        msg: dict[str, Any] = {
            "notification": {"title": title, "body": body},
        }
        if data:
            # FCM data values must be strings
            msg["data"] = {k: str(v) for k, v in data.items()}

        if recipient.startswith("/topics/"):
            msg["topic"] = recipient.removeprefix("/topics/")
        else:
            msg["token"] = recipient

        return {"message": msg}

    async def _send_with_retry(self, payload: dict[str, Any]) -> bool:
        assert self._credentials is not None
        assert self._project_id is not None

        url = _FCM_URL.format(project_id=self._project_id)

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                token = _get_access_token(self._credentials)
            except Exception:
                logger.exception(
                    "Failed to obtain FCM access token (attempt %d)", attempt
                )
                continue

            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        url,
                        json=payload,
                        headers={"Authorization": f"Bearer {token}"},
                    )
            except httpx.TransportError:
                logger.warning(
                    "FCM transport error (attempt %d/%d)", attempt, _MAX_RETRIES
                )
                continue

            if resp.status_code == 200:
                return True

            # Handle known non-retryable errors
            if resp.status_code == 404 or (
                resp.status_code == 400 and "UNREGISTERED" in resp.text
            ):
                logger.warning(
                    "FCM token invalid/expired — recipient=%s resp=%s",
                    payload.get("message", {}).get("token", "?"),
                    resp.text[:200],
                )
                return False

            if resp.status_code not in _RETRYABLE_STATUS:
                logger.error(
                    "FCM non-retryable error %d: %s",
                    resp.status_code,
                    resp.text[:300],
                )
                return False

            logger.warning(
                "FCM retryable error %d (attempt %d/%d)",
                resp.status_code,
                attempt,
                _MAX_RETRIES,
            )

        logger.error("FCM send failed after %d attempts", _MAX_RETRIES)
        return False
