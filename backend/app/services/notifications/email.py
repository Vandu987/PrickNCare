"""Email notification sender — SendGrid & AWS SES support."""

from __future__ import annotations

import logging
from string import Template
from typing import Any

import httpx

from app.core.config import settings

from .base import BaseChannelSender, NotificationChannel

logger = logging.getLogger(__name__)

# Simple HTML wrapper for plain-text messages
_DEFAULT_HTML_TEMPLATE = Template(
    "<!DOCTYPE html><html><body>"
    '<div style="font-family:sans-serif;max-width:600px;margin:auto;">'
    "<h2>${subject}</h2>"
    "<div>${body}</div>"
    "</div></body></html>"
)

_MAX_RETRIES = 3


class EmailService(BaseChannelSender):
    """Send emails via SendGrid or AWS SES."""

    channel = NotificationChannel.EMAIL

    def __init__(self) -> None:
        self._provider: str = getattr(settings, "EMAIL_PROVIDER", "sendgrid")
        self._from_email: str = getattr(settings, "EMAIL_FROM", "")
        self._sendgrid_key: str = getattr(settings, "SENDGRID_API_KEY", "")
        self._ses_region: str = getattr(settings, "AWS_SES_REGION", "ap-south-1")

    # -- public interface ----------------------------------------------------

    async def send(
        self,
        recipient: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send an email to *recipient*.

        ``data`` may carry optional keys:
        - ``subject``: email subject line (default "Notification")
        - ``html``: pre-built HTML body (skips auto-wrapping)
        """
        data = data or {}
        subject = data.get("subject", "Notification")
        html_body = data.get("html") or self._render_html(subject, message)

        if not self._from_email:
            logger.warning("EMAIL_FROM not configured — skipping email send")
            return False

        provider = self._provider.lower()
        if provider == "ses":
            return await self._send_with_retry(
                self._send_ses, recipient, subject, html_body
            )
        # default to sendgrid
        return await self._send_with_retry(
            self._send_sendgrid, recipient, subject, html_body
        )

    # -- providers -----------------------------------------------------------

    async def _send_sendgrid(
        self, recipient: str, subject: str, html_body: str
    ) -> bool:
        if not self._sendgrid_key:
            logger.warning("SENDGRID_API_KEY not configured — skipping")
            return False

        payload = {
            "personalizations": [{"to": [{"email": recipient}]}],
            "from": {"email": self._from_email},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}],
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._sendgrid_key}",
                    "Content-Type": "application/json",
                },
            )
        if resp.status_code in (200, 202):
            logger.info("Email sent via SendGrid to %s", recipient)
            return True
        logger.error("SendGrid error %s: %s", resp.status_code, resp.text[:200])
        # Treat 5xx and 429 as transient (will be retried)
        if resp.status_code >= 500 or resp.status_code == 429:
            raise _TransientEmailError(f"SendGrid {resp.status_code}")
        return False

    async def _send_ses(self, recipient: str, subject: str, html_body: str) -> bool:
        """Send email via AWS SES using httpx (v2 REST API stub).

        For production use, swap to ``boto3`` or ``aioboto3``.
        """
        try:
            import boto3  # type: ignore[import-untyped]

            ses = boto3.client("ses", region_name=self._ses_region)
            ses.send_email(
                Source=self._from_email,
                Destination={"ToAddresses": [recipient]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                    },
                },
            )
            logger.info("Email sent via SES to %s", recipient)
            return True
        except ImportError:
            logger.error("boto3 not installed — cannot use SES provider")
            return False
        except Exception as exc:
            logger.error("SES error: %s", exc)
            raise _TransientEmailError(str(exc)) from exc

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _render_html(subject: str, body: str) -> str:
        return _DEFAULT_HTML_TEMPLATE.safe_substitute(subject=subject, body=body)

    @staticmethod
    async def _send_with_retry(
        fn: Any, recipient: str, subject: str, html_body: str
    ) -> bool:
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return await fn(recipient, subject, html_body)
            except _TransientEmailError as exc:
                last_exc = exc
                logger.warning(
                    "Email attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc
                )
        logger.error("All %d email attempts exhausted: %s", _MAX_RETRIES, last_exc)
        return False


class _TransientEmailError(Exception):
    """Raised on transient failures to trigger retry."""
