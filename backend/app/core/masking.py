"""Sensitive data masking utilities and HIPAA-aware logging.

Task 16.5 — provides field-level masking functions and a logging filter
that automatically redacts sensitive data from log output.
"""

from __future__ import annotations

import logging
import re
from typing import Any

# ---------------------------------------------------------------------------
# Masking utilities
# ---------------------------------------------------------------------------


def mask_phone(value: str) -> str:
    """Show only last 4 digits.  e.g. '9876543210' → '******3210'."""
    digits = re.sub(r"\D", "", value)
    if len(digits) <= 4:
        return value
    return "*" * (len(digits) - 4) + digits[-4:]


def mask_email(value: str) -> str:
    """Show first char + '***@domain'.  e.g. 'sunny@ex.com' → 's***@ex.com'."""
    if "@" not in value:
        return "***"
    local, domain = value.rsplit("@", 1)
    return f"{local[0]}***@{domain}" if local else f"***@{domain}"


def mask_name(value: str) -> str:
    """First letter + '***'.  e.g. 'Sunny' → 'S***'."""
    if not value:
        return "***"
    return f"{value[0]}***"


def mask_aadhaar(value: str) -> str:
    """Show last 4 digits of Aadhaar.  e.g. '1234 5678 9012' → 'XXXX XXXX 9012'."""
    digits = re.sub(r"\D", "", value)
    if len(digits) < 4:
        return "XXXX"
    return "XXXX XXXX " + digits[-4:]


def mask_pan(value: str) -> str:
    """Show first and last 2 chars.  e.g. 'ABCDE1234F' → 'AB******4F'."""
    clean = value.strip().upper()
    if len(clean) <= 4:
        return "****"
    return clean[:2] + "*" * (len(clean) - 4) + clean[-2:]


# ---------------------------------------------------------------------------
# Field-pattern → masker mapping (configurable)
# ---------------------------------------------------------------------------

_DEFAULT_FIELD_PATTERNS: dict[re.Pattern[str], Any] = {
    re.compile(r"phone|mobile|cell", re.IGNORECASE): mask_phone,
    re.compile(r"email", re.IGNORECASE): mask_email,
    re.compile(r"name|first.?name|last.?name", re.IGNORECASE): mask_name,
    re.compile(r"aadhaar|aadhar", re.IGNORECASE): mask_aadhaar,
    re.compile(r"pan(?:_?card)?(?:_?number)?$", re.IGNORECASE): mask_pan,
}


def mask_dict(
    data: dict[str, Any],
    *,
    field_patterns: dict[re.Pattern[str], Any] | None = None,
) -> dict[str, Any]:
    """Return a shallow copy of *data* with sensitive fields masked."""
    patterns = field_patterns or _DEFAULT_FIELD_PATTERNS
    masked: dict[str, Any] = {}
    for key, val in data.items():
        if isinstance(val, dict):
            masked[key] = mask_dict(val, field_patterns=patterns)
        elif isinstance(val, str):
            masker = _find_masker(key, patterns)
            masked[key] = masker(val) if masker else val
        else:
            masked[key] = val
    return masked


def _find_masker(field_name: str, patterns: dict[re.Pattern[str], Any]) -> Any | None:
    for pattern, masker in patterns.items():
        if pattern.search(field_name):
            return masker
    return None


# ---------------------------------------------------------------------------
# HIPAA-aware logging filter
# ---------------------------------------------------------------------------

# Regex patterns to detect inline sensitive data in log messages
_INLINE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Phone numbers (10+ digits, optionally with separators/prefix)
    (re.compile(r"\b(\+?\d[\d\s\-]{8,}\d)\b"), lambda m: mask_phone(m.group(0))),
    # Email addresses
    (
        re.compile(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b"),
        lambda m: mask_email(m.group(0)),
    ),
    # Aadhaar (12 digits with optional spaces/dashes)
    (
        re.compile(r"\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4})\b"),
        lambda m: mask_aadhaar(m.group(0)),
    ),
    # PAN (AAAAA0000A format)
    (
        re.compile(r"\b([A-Z]{5}\d{4}[A-Z])\b"),
        lambda m: mask_pan(m.group(0)),
    ),
]


class HIPAALogFilter(logging.Filter):
    """Logging filter that masks sensitive data in log records.

    Attach to any handler or logger to auto-redact PII from messages.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._mask_message(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._mask_message(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._mask_message(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
        return True

    @staticmethod
    def _mask_message(msg: str) -> str:
        for pattern, replacer in _INLINE_PATTERNS:
            msg = pattern.sub(replacer, msg)
        return msg


# ---------------------------------------------------------------------------
# Convenience: configure root / app logger with HIPAA filter
# ---------------------------------------------------------------------------


def configure_hipaa_logging(
    logger_name: str = "app",
    level: int = logging.INFO,
) -> logging.Logger:
    """Return a logger with the HIPAA filter applied."""
    log = logging.getLogger(logger_name)
    log.setLevel(level)
    hipaa_filter = HIPAALogFilter()
    log.addFilter(hipaa_filter)
    for handler in log.handlers:
        handler.addFilter(hipaa_filter)
    return log
