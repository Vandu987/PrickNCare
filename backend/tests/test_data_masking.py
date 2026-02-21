"""Tests for sensitive data masking (task 16.5)."""

from __future__ import annotations

import logging

from app.core.masking import (
    HIPAALogFilter,
    mask_aadhaar,
    mask_dict,
    mask_email,
    mask_name,
    mask_pan,
    mask_phone,
)

# ── Individual masking functions ──────────────────────────────────────────


class TestMaskPhone:
    def test_ten_digit(self):
        assert mask_phone("9876543210") == "******3210"

    def test_with_country_code(self):
        assert mask_phone("+91-9876543210") == "********3210"

    def test_short(self):
        assert mask_phone("1234") == "1234"


class TestMaskEmail:
    def test_normal(self):
        assert mask_email("sunny@example.com") == "s***@example.com"

    def test_no_at(self):
        assert mask_email("invalid") == "***"


class TestMaskName:
    def test_normal(self):
        assert mask_name("Sunny") == "S***"

    def test_empty(self):
        assert mask_name("") == "***"


class TestMaskAadhaar:
    def test_twelve_digits(self):
        assert mask_aadhaar("1234 5678 9012") == "XXXX XXXX 9012"

    def test_no_spaces(self):
        assert mask_aadhaar("123456789012") == "XXXX XXXX 9012"


class TestMaskPan:
    def test_standard(self):
        assert mask_pan("ABCDE1234F") == "AB******4F"

    def test_short(self):
        assert mask_pan("AB") == "****"


# ── mask_dict ─────────────────────────────────────────────────────────────


class TestMaskDict:
    def test_masks_sensitive_fields(self):
        data = {
            "phone": "9876543210",
            "email": "sunny@example.com",
            "first_name": "Sunny",
            "aadhaar": "1234 5678 9012",
            "pan": "ABCDE1234F",
            "amount": 500,
        }
        result = mask_dict(data)
        assert result["phone"] == "******3210"
        assert result["email"] == "s***@example.com"
        assert result["first_name"] == "S***"
        assert result["aadhaar"] == "XXXX XXXX 9012"
        assert result["pan"] == "AB******4F"
        assert result["amount"] == 500  # non-sensitive untouched

    def test_nested_dict(self):
        data = {"patient": {"phone": "9876543210", "city": "Delhi"}}
        result = mask_dict(data)
        assert result["patient"]["phone"] == "******3210"
        assert result["patient"]["city"] == "Delhi"

    def test_non_sensitive_passthrough(self):
        data = {"order_id": "abc-123", "status": "completed"}
        assert mask_dict(data) == data


# ── HIPAA log filter ──────────────────────────────────────────────────────


class TestHIPAALogFilter:
    def test_masks_email_in_log(self, caplog):
        logger = logging.getLogger("test_hipaa")
        logger.addFilter(HIPAALogFilter())
        with caplog.at_level(logging.INFO, logger="test_hipaa"):
            logger.info("User email is sunny@example.com ok")
        assert "sunny@example.com" not in caplog.text
        assert "s***@example.com" in caplog.text

    def test_masks_pan_in_log(self, caplog):
        logger = logging.getLogger("test_hipaa_pan")
        logger.addFilter(HIPAALogFilter())
        with caplog.at_level(logging.INFO, logger="test_hipaa_pan"):
            logger.info("PAN: ABCDE1234F")
        assert "ABCDE1234F" not in caplog.text
        assert "AB******4F" in caplog.text
