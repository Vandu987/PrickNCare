"""Input validation and sanitization utilities for XSS/SQL-injection prevention."""

import html
import re
from typing import Any

# ---------------------------------------------------------------------------
# HTML / XSS sanitization
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(
    r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL
)
_EVENT_HANDLER_RE = re.compile(r"\bon\w+\s*=", re.IGNORECASE)
_JAVASCRIPT_URI_RE = re.compile(r"javascript\s*:", re.IGNORECASE)


def strip_html_tags(value: str) -> str:
    """Remove all HTML tags from *value*."""
    return _TAG_RE.sub("", value)


def escape_html(value: str) -> str:
    """HTML-escape special characters (&, <, >, \", ')."""
    return html.escape(value, quote=True)


def sanitize_user_input(value: str) -> str:
    """Strip tags, remove event handlers and javascript: URIs, then escape."""
    value = _SCRIPT_RE.sub("", value)
    value = _EVENT_HANDLER_RE.sub("", value)
    value = _JAVASCRIPT_URI_RE.sub("", value)
    value = strip_html_tags(value)
    return value.strip()


# ---------------------------------------------------------------------------
# SQL-injection pattern detection
# ---------------------------------------------------------------------------

# Common SQL injection fragments (case-insensitive).
_SQL_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|EXECUTE)\b"
        r"\s+(ALL\s+)?)",
        r"(--\s|/\*)",  # SQL comment tokens (require space after --)
        r"('\s*(OR|AND)\s+')",  # tautology: ' OR '
        r"(;\s*(DROP|DELETE|UPDATE|INSERT))",  # statement chaining
        r"(\bSLEEP\s*\()",  # time-based blind
        r"(\bBENCHMARK\s*\()",
        r"(\bWAITFOR\s+DELAY\b)",
        r"(\bLOAD_FILE\s*\()",
        r"(\bINTO\s+(OUT|DUMP)FILE\b)",
    )
]


def contains_sql_injection(value: str) -> bool:
    """Return True if *value* contains suspicious SQL-injection patterns."""
    return any(p.search(value) for p in _SQL_INJECTION_PATTERNS)


# ---------------------------------------------------------------------------
# XSS pattern detection
# ---------------------------------------------------------------------------

_XSS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"<\s*script",
        r"<\s*iframe",
        r"<\s*object",
        r"<\s*embed",
        r"<\s*img\s+[^>]*\bonerror\b",
        r"\bjavascript\s*:",
        r"\bvbscript\s*:",
        r"\bon(load|error|click|mouseover|focus|blur)\s*=",
    )
]


def contains_xss(value: str) -> bool:
    """Return True if *value* contains common XSS attack vectors."""
    return any(p.search(value) for p in _XSS_PATTERNS)


# ---------------------------------------------------------------------------
# Generic recursive sanitizer (for dicts / lists coming from JSON bodies)
# ---------------------------------------------------------------------------


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize all string values in a dict."""
    out: dict[str, Any] = {}
    for key, val in data.items():
        if isinstance(val, str):
            out[key] = sanitize_user_input(val)
        elif isinstance(val, dict):
            out[key] = sanitize_dict(val)
        elif isinstance(val, list):
            out[key] = [
                (
                    sanitize_dict(v)
                    if isinstance(v, dict)
                    else sanitize_user_input(v) if isinstance(v, str) else v
                )
                for v in val
            ]
        else:
            out[key] = val
    return out
