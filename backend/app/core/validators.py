"""Pydantic validators for detecting common attack patterns in freetext fields."""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator

from app.core.security_utils import contains_sql_injection, contains_xss


def _reject_xss(value: str) -> str:
    if contains_xss(value):
        raise ValueError("Input contains potentially unsafe HTML/script content")
    return value


def _reject_sql_injection(value: str) -> str:
    if contains_sql_injection(value):
        raise ValueError("Input contains potentially unsafe SQL fragments")
    return value


def _reject_attacks(value: str) -> str:
    """Combined XSS + SQL-injection check."""
    _reject_xss(value)
    _reject_sql_injection(value)
    return value


# Annotated types for use in Pydantic models:
#   name: SafeString
SafeString = Annotated[str, AfterValidator(_reject_attacks)]
NoXSSString = Annotated[str, AfterValidator(_reject_xss)]
NoSQLiString = Annotated[str, AfterValidator(_reject_sql_injection)]
