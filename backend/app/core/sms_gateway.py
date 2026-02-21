"""SMS gateway abstraction with MSG91 and Twilio providers."""

import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class SMSProvider(ABC):
    @abstractmethod
    async def send_otp(self, phone: str, otp: str) -> bool:
        """Send *otp* to *phone*.  Returns True on success."""


# ---------------------------------------------------------------------------
# MSG91 provider
# ---------------------------------------------------------------------------


class MSG91Provider(SMSProvider):
    _BASE_URL = "https://api.msg91.com/api/v5/otp"

    async def send_otp(self, phone: str, otp: str) -> bool:
        params = {
            "authkey": settings.SMS_API_KEY,
            "mobile": phone,
            "message": (
                f"Your PricknCare OTP is {otp}. "
                f"Valid for {settings.OTP_EXPIRE_MINUTES} minutes."
            ),
            "sender": settings.MSG91_SENDER_ID,
            "route": settings.MSG91_ROUTE,
            "otp": otp,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self._BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                success = data.get("type") == "success"
                if not success:
                    logger.warning("MSG91 OTP send failed: %s", data)
                return success
        except Exception as exc:
            logger.error("MSG91 send_otp error for %s: %s", phone, exc)
            return False


# ---------------------------------------------------------------------------
# Twilio provider
# ---------------------------------------------------------------------------


class TwilioProvider(SMSProvider):
    async def send_otp(self, phone: str, otp: str) -> bool:
        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{settings.TWILIO_ACCOUNT_SID}/Messages.json"
        )
        data = {
            "From": settings.TWILIO_FROM_NUMBER,
            "To": phone,
            "Body": (
                f"Your PricknCare OTP is {otp}. "
                f"Valid for {settings.OTP_EXPIRE_MINUTES} minutes."
            ),
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url,
                    data=data,
                    auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                )
                resp.raise_for_status()
                return resp.json().get("status") not in ("failed", "undelivered")
        except Exception as exc:
            logger.error("Twilio send_otp error for %s: %s", phone, exc)
            return False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_sms_provider() -> SMSProvider:
    """Return the configured SMS provider based on settings.SMS_PROVIDER."""
    provider = settings.SMS_PROVIDER.lower()
    if provider == "twilio":
        return TwilioProvider()
    return MSG91Provider()  # default
