"""Tests for EmailService (SendGrid & SES providers)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.notifications.email import EmailService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def email_svc(monkeypatch):
    """Return an EmailService with sensible test defaults."""
    monkeypatch.setattr("app.core.config.settings.EMAIL_PROVIDER", "sendgrid")
    monkeypatch.setattr("app.core.config.settings.SENDGRID_API_KEY", "test-key")
    monkeypatch.setattr("app.core.config.settings.EMAIL_FROM", "noreply@prickncare.com")
    monkeypatch.setattr("app.core.config.settings.AWS_SES_REGION", "ap-south-1")
    return EmailService()


# ---------------------------------------------------------------------------
# SendGrid
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sendgrid_success(email_svc):
    mock_resp = MagicMock(status_code=202, text="")
    with patch(
        "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp
    ):
        result = await email_svc.send("user@example.com", "Hello", {"subject": "Hi"})
    assert result is True


@pytest.mark.asyncio
async def test_sendgrid_client_error(email_svc):
    """4xx (non-429) should return False without retry."""
    mock_resp = MagicMock(status_code=400, text="Bad request")
    with patch(
        "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp
    ):
        result = await email_svc.send("user@example.com", "Hello", {"subject": "Hi"})
    assert result is False


@pytest.mark.asyncio
async def test_sendgrid_retries_on_5xx(email_svc):
    """5xx triggers transient error → retries up to 3 times."""
    mock_resp = MagicMock(status_code=500, text="Internal")
    with patch(
        "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp
    ) as mock_post:
        result = await email_svc.send("user@example.com", "Hello", {"subject": "Hi"})
    assert result is False
    assert mock_post.call_count == 3


@pytest.mark.asyncio
async def test_sendgrid_retries_on_429(email_svc):
    mock_resp = MagicMock(status_code=429, text="Rate limited")
    with patch(
        "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp
    ) as mock_post:
        result = await email_svc.send("user@example.com", "Hello", {"subject": "Hi"})
    assert result is False
    assert mock_post.call_count == 3


# ---------------------------------------------------------------------------
# AWS SES
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ses_success(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.EMAIL_PROVIDER", "ses")
    monkeypatch.setattr("app.core.config.settings.SENDGRID_API_KEY", "")
    monkeypatch.setattr("app.core.config.settings.EMAIL_FROM", "noreply@prickncare.com")
    monkeypatch.setattr("app.core.config.settings.AWS_SES_REGION", "ap-south-1")
    svc = EmailService()

    mock_ses_client = MagicMock()
    mock_ses_client.send_email = MagicMock(return_value={"MessageId": "abc123"})
    mock_boto3 = MagicMock()
    mock_boto3.client = MagicMock(return_value=mock_ses_client)

    import sys

    monkeypatch.setitem(sys.modules, "boto3", mock_boto3)
    result = await svc.send("user@example.com", "Hello", {"subject": "Hi"})
    assert result is True
    mock_ses_client.send_email.assert_called_once()


@pytest.mark.asyncio
async def test_ses_boto3_missing(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.EMAIL_PROVIDER", "ses")
    monkeypatch.setattr("app.core.config.settings.EMAIL_FROM", "noreply@prickncare.com")
    svc = EmailService()

    with patch.dict("sys.modules", {"boto3": None}):
        # Force ImportError by patching the import inside the method
        with patch("builtins.__import__", side_effect=_make_import_error("boto3")):
            result = await svc.send("user@example.com", "Hello", {"subject": "Hi"})
    assert result is False


# ---------------------------------------------------------------------------
# Graceful fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_from_email_skips(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.EMAIL_FROM", "")
    svc = EmailService()
    result = await svc.send("user@example.com", "Hello", {"subject": "Hi"})
    assert result is False


@pytest.mark.asyncio
async def test_no_sendgrid_key_skips(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.EMAIL_PROVIDER", "sendgrid")
    monkeypatch.setattr("app.core.config.settings.SENDGRID_API_KEY", "")
    monkeypatch.setattr("app.core.config.settings.EMAIL_FROM", "noreply@prickncare.com")
    svc = EmailService()
    result = await svc.send("user@example.com", "Hello", {"subject": "Hi"})
    assert result is False


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------


def test_render_html():
    html = EmailService._render_html("Test Subject", "Hello world")
    assert "Test Subject" in html
    assert "Hello world" in html
    assert "<html>" in html


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_import_error(name: str):
    """Return a side_effect function that raises ImportError for a specific module."""
    _real_import = (
        __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
    )

    def _import(mod_name, *args, **kwargs):
        if mod_name == name:
            raise ImportError(f"No module named '{name}'")
        return _real_import(mod_name, *args, **kwargs)

    return _import
