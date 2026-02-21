"""SMS sender with MSG91/Twilio provider abstraction and retry logic."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings

from .base import BaseChannelSender, NotificationChannel

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 0.5  # seconds

# HTTP status codes considered transient (worth retrying)
_TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class SMSService(BaseChannelSender):
    """SMS sender supporting MSG91 and Twilio providers."""

    channel = NotificationChannel.SMS

    def __init__(self, provider: str | None = None) -> None:
        self.provider = (provider or settings.SMS_PROVIDER).lower()

    async def send(
        self,
        recipient: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send an SMS to *recipient* with retry logic."""
        if self.provider == "msg91":
            return await self._send_with_retry(self._send_msg91, recipient, message)
        elif self.provider == "twilio":
            return await self._send_with_retry(self._send_twilio, recipient, message)
        else:
            logger.warning("Unknown SMS provider '%s'; skipping send.", self.provider)
            return False

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    async def _send_msg91(self, phone: str, message: str) -> bool:
        api_key = settings.SMS_API_KEY
        if not api_key:
            logger.warning("MSG91 API key not configured; skipping SMS.")
            return False

        url = "https://api.msg91.com/api/v5/flow/"
        headers = {"authkey": api_key, "Content-Type": "application/json"}
        payload = {
            "sender": settings.MSG91_SENDER_ID,
            "route": str(settings.MSG91_ROUTE),
            "mobiles": phone,
            "message": message,
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in _TRANSIENT_STATUS_CODES:
                raise _TransientSMSError(
                    f"MSG91 transient error: HTTP {resp.status_code}"
                )
            resp.raise_for_status()
            logger.info("MSG91 SMS sent to %s", phone)
            return True

    async def _send_twilio(self, phone: str, message: str) -> bool:
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        from_number = settings.TWILIO_FROM_NUMBER

        if not all([account_sid, auth_token, from_number]):
            logger.warning("Twilio credentials not configured; skipping SMS.")
            return False

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        payload = {"To": phone, "From": from_number, "Body": message}

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                data=payload,
                auth=(account_sid, auth_token),
            )
            if resp.status_code in _TRANSIENT_STATUS_CODES:
                raise _TransientSMSError(
                    f"Twilio transient error: HTTP {resp.status_code}"
                )
            resp.raise_for_status()
            logger.info("Twilio SMS sent to %s", phone)
            return True

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------

    @staticmethod
    async def _send_with_retry(
        send_fn: Any,
        phone: str,
        message: str,
    ) -> bool:
        """Retry *send_fn* up to _MAX_RETRIES times with exponential backoff."""
        last_exc: BaseException | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                return await send_fn(phone, message)
            except _TransientSMSError as exc:
                last_exc = exc
                wait = _BACKOFF_BASE * (2**attempt)
                logger.warning(
                    "SMS attempt %d/%d failed (%s); retrying in %.1fs",
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)
            except httpx.HTTPStatusError as exc:
                # Non-transient HTTP error — don't retry
                logger.error("SMS send failed (non-transient): %s", exc)
                return False
            except httpx.HTTPError as exc:
                # Network-level errors are transient
                last_exc = exc
                wait = _BACKOFF_BASE * (2**attempt)
                logger.warning(
                    "SMS attempt %d/%d network error (%s); retrying in %.1fs",
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)

        logger.error("SMS send failed after %d attempts: %s", _MAX_RETRIES, last_exc)
        return False


class _TransientSMSError(Exception):
    """Raised internally when provider returns a transient HTTP error."""
