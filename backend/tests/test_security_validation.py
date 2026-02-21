"""Tests for input validation, sanitization, and security headers."""

import pytest
from pydantic import BaseModel, ValidationError

from app.core.security_utils import (
    contains_sql_injection,
    contains_xss,
    escape_html,
    sanitize_dict,
    sanitize_user_input,
    strip_html_tags,
)
from app.core.validators import NoXSSString, SafeString

# ── strip_html_tags ──────────────────────────────────────────────────────


def test_strip_html_tags_basic():
    assert strip_html_tags("<b>hello</b>") == "hello"


def test_strip_html_tags_nested():
    assert strip_html_tags("<div><p>hi</p></div>") == "hi"


def test_strip_html_tags_no_tags():
    assert strip_html_tags("plain text") == "plain text"


# ── escape_html ──────────────────────────────────────────────────────────


def test_escape_html():
    assert escape_html('<img onerror="x">') == "&lt;img onerror=&quot;x&quot;&gt;"


def test_escape_html_ampersand():
    assert escape_html("a & b") == "a &amp; b"


# ── sanitize_user_input ─────────────────────────────────────────────────


def test_sanitize_removes_script():
    assert "script" not in sanitize_user_input("<script>alert(1)</script>safe")


def test_sanitize_removes_event_handlers():
    result = sanitize_user_input('<img onerror="alert(1)">')
    assert "onerror" not in result


def test_sanitize_removes_javascript_uri():
    result = sanitize_user_input("javascript:alert(1)")
    assert "javascript" not in result.lower()


# ── contains_sql_injection ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "payload",
    [
        "1; DROP TABLE users",
        "' OR '1'='1",
        "UNION SELECT * FROM passwords",
        "1; DELETE FROM orders",
        "SLEEP(5)",
        "BENCHMARK(1000000,SHA1('test'))",
    ],
)
def test_sql_injection_detected(payload: str):
    assert contains_sql_injection(payload) is True


@pytest.mark.parametrize(
    "safe",
    [
        "John Doe",
        "My address is 123 Main St",
        "Order #42",
        "hello@example.com",
    ],
)
def test_sql_injection_safe(safe: str):
    assert contains_sql_injection(safe) is False


# ── contains_xss ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "payload",
    [
        "<script>alert(1)</script>",
        "<iframe src='evil.com'>",
        "<img onerror=alert(1)>",
        "javascript:alert(1)",
        '<div onmouseover="steal()">',
    ],
)
def test_xss_detected(payload: str):
    assert contains_xss(payload) is True


@pytest.mark.parametrize(
    "safe",
    [
        "Hello world",
        "Price is $100",
        "a < b and b > c",
    ],
)
def test_xss_safe(safe: str):
    assert contains_xss(safe) is False


# ── sanitize_dict ────────────────────────────────────────────────────────


def test_sanitize_dict_strips_tags():
    data = {"name": "<b>Bob</b>", "age": 30, "notes": "<script>x</script>ok"}
    result = sanitize_dict(data)
    assert "<" not in result["name"]
    assert result["age"] == 30
    assert "script" not in result["notes"]


def test_sanitize_dict_nested():
    data = {"inner": {"val": "<em>hi</em>"}}
    result = sanitize_dict(data)
    assert "<" not in result["inner"]["val"]


# ── Pydantic validators ─────────────────────────────────────────────────


class _TestModel(BaseModel):
    name: SafeString


class _TestXSSModel(BaseModel):
    content: NoXSSString


def test_pydantic_safe_string_accepts_clean():
    m = _TestModel(name="John Doe")
    assert m.name == "John Doe"


def test_pydantic_safe_string_rejects_xss():
    with pytest.raises(ValidationError, match="unsafe HTML"):
        _TestModel(name="<script>alert(1)</script>")


def test_pydantic_safe_string_rejects_sqli():
    with pytest.raises(ValidationError, match="unsafe SQL"):
        _TestModel(name="'; DROP TABLE users; --")


def test_pydantic_no_xss_accepts_clean():
    m = _TestXSSModel(content="Normal text")
    assert m.content == "Normal text"


def test_pydantic_no_xss_rejects_script():
    with pytest.raises(ValidationError, match="unsafe HTML"):
        _TestXSSModel(content="<script>bad</script>")


# ── Security headers (integration via test client) ──────────────────────


@pytest.mark.anyio
async def test_security_headers_present(client):
    resp = await client.get("/api/v1/health")
    # Accept any status — we just care about headers being set
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "max-age" in resp.headers.get("Strict-Transport-Security", "")
    assert "default-src" in resp.headers.get("Content-Security-Policy", "")
