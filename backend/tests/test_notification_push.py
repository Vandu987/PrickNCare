"""Tests for PushNotificationService (FCM)."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from app.services.notifications.push import PushNotificationService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(project_id: str = "test-proj", creds: dict | None = None):
    """Create a PushNotificationService with pre-injected state."""
    svc = PushNotificationService.__new__(PushNotificationService)
    svc._project_id = project_id
    svc._creds_path = "/fake/creds.json"
    svc._credentials = creds or {"type": "service_account"}
    svc._configured = True
    return svc


def _unconfigured_service():
    svc = PushNotificationService.__new__(PushNotificationService)
    svc._project_id = None
    svc._creds_path = None
    svc._credentials = None
    svc._configured = False
    return svc


# ---------------------------------------------------------------------------
# Tests — stub / unconfigured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stub_mode_returns_true():
    svc = _unconfigured_service()
    result = await svc.send("token123", "hello")
    assert result is True


# ---------------------------------------------------------------------------
# Tests — configured, mocked HTTP
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.notifications.push._get_access_token", return_value="fake-token")
async def test_send_success(mock_token):
    svc = _make_service()

    resp = httpx.Response(200, json={"name": "projects/test/messages/123"})
    with patch("httpx.AsyncClient.post", return_value=resp) as mock_post:
        result = await svc.send("device-token", "body text", {"title": "Hello"})

    assert result is True
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert payload["message"]["token"] == "device-token"
    assert payload["message"]["notification"]["title"] == "Hello"


@pytest.mark.asyncio
@patch("app.services.notifications.push._get_access_token", return_value="fake-token")
async def test_send_to_topic(mock_token):
    svc = _make_service()

    resp = httpx.Response(200, json={})
    with patch("httpx.AsyncClient.post", return_value=resp):
        result = await svc.send_to_topic("alerts", "Title", "Body")

    assert result is True


@pytest.mark.asyncio
@patch("app.services.notifications.push._get_access_token", return_value="fake-token")
async def test_invalid_token_returns_false(mock_token):
    svc = _make_service()

    resp = httpx.Response(
        400, text='{"error":{"details":[{"errorCode":"UNREGISTERED"}]}}'
    )
    with patch("httpx.AsyncClient.post", return_value=resp):
        result = await svc.send("bad-token", "hi")

    assert result is False


@pytest.mark.asyncio
@patch("app.services.notifications.push._get_access_token", return_value="fake-token")
async def test_retry_on_503(mock_token):
    svc = _make_service()

    fail = httpx.Response(503, text="unavailable")
    ok = httpx.Response(200, json={})

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return fail if call_count < 3 else ok

    with patch("httpx.AsyncClient.post", side_effect=side_effect):
        result = await svc.send("tok", "msg")

    assert result is True
    assert call_count == 3


@pytest.mark.asyncio
@patch("app.services.notifications.push._get_access_token", return_value="fake-token")
async def test_retry_exhausted(mock_token):
    svc = _make_service()

    fail = httpx.Response(503, text="unavailable")
    with patch("httpx.AsyncClient.post", return_value=fail):
        result = await svc.send("tok", "msg")

    assert result is False


@pytest.mark.asyncio
@patch(
    "app.services.notifications.push._get_access_token",
    side_effect=RuntimeError("no google-auth"),
)
async def test_token_error_retries_and_fails(mock_token):
    svc = _make_service()
    result = await svc.send("tok", "msg")
    assert result is False


@pytest.mark.asyncio
@patch("app.services.notifications.push._get_access_token", return_value="t")
async def test_transport_error_retries(mock_token):
    svc = _make_service()

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.ConnectError("fail")
        return httpx.Response(200, json={})

    with patch("httpx.AsyncClient.post", side_effect=side_effect):
        result = await svc.send("tok", "msg")

    assert result is True


@pytest.mark.asyncio
@patch("app.services.notifications.push._get_access_token", return_value="t")
async def test_non_retryable_error(mock_token):
    svc = _make_service()

    resp = httpx.Response(403, text="forbidden")
    with patch("httpx.AsyncClient.post", return_value=resp):
        result = await svc.send("tok", "msg")

    assert result is False
