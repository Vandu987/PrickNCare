"""Tests for the data encryption service."""

from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from app.services.encryption import EncryptedString, EncryptionService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture
def svc():
    return EncryptionService(key=TEST_KEY)


# ---------------------------------------------------------------------------
# EncryptionService core
# ---------------------------------------------------------------------------


class TestEncryptionService:
    def test_encrypt_decrypt_roundtrip(self, svc):
        plaintext = "Hello, World!"
        ciphertext = svc.encrypt(plaintext)
        assert ciphertext != plaintext
        assert svc.decrypt(ciphertext) == plaintext

    def test_encrypt_produces_different_ciphertexts(self, svc):
        """Fernet includes a timestamp + IV so repeated encryptions differ."""
        ct1 = svc.encrypt("same")
        ct2 = svc.encrypt("same")
        assert ct1 != ct2

    def test_decrypt_invalid_token(self, svc):
        with pytest.raises(ValueError, match="Decryption failed"):
            svc.decrypt("not-a-valid-ciphertext")

    def test_invalid_key_raises(self):
        with pytest.raises(ValueError, match="Invalid ENCRYPTION_KEY"):
            EncryptionService(key="bad-key")

    def test_missing_key_raises(self):
        with patch("app.services.encryption.settings") as mock_settings:
            mock_settings.ENCRYPTION_KEY = ""
            with pytest.raises(ValueError, match="ENCRYPTION_KEY is not set"):
                EncryptionService()

    def test_generate_key(self):
        key = EncryptionService.generate_key()
        # Should be valid Fernet key (url-safe base64, 44 chars)
        assert len(key) == 44
        Fernet(key.encode())  # should not raise

    # -- field helpers -------------------------------------------------------

    def test_phone_roundtrip(self, svc):
        phone = "+919876543210"
        assert svc.decrypt_phone(svc.encrypt_phone(phone)) == phone

    def test_address_roundtrip(self, svc):
        addr = "123 MG Road, Bengaluru, Karnataka 560001"
        assert svc.decrypt_address(svc.encrypt_address(addr)) == addr

    def test_medical_info_roundtrip(self, svc):
        info = "Blood type: O+, Allergies: Penicillin"
        assert svc.decrypt_medical_info(svc.encrypt_medical_info(info)) == info

    def test_unicode_roundtrip(self, svc):
        text = "रोगी का नाम: सुनील कुमार"
        assert svc.decrypt(svc.encrypt(text)) == text


# ---------------------------------------------------------------------------
# EncryptedString TypeDecorator
# ---------------------------------------------------------------------------


class TestEncryptedString:
    @pytest.fixture
    def col(self):
        return EncryptedString(length=512)

    def test_bind_param_none(self, col):
        assert col.process_bind_param(None, MagicMock()) is None

    def test_result_value_none(self, col):
        assert col.process_result_value(None, MagicMock()) is None

    def test_bind_and_result_roundtrip(self, col):
        with patch("app.services.encryption.get_encryption_service") as mock_get:
            svc = EncryptionService(key=TEST_KEY)
            mock_get.return_value = svc

            dialect = MagicMock()
            encrypted = col.process_bind_param("secret", dialect)
            assert encrypted != "secret"
            decrypted = col.process_result_value(encrypted, dialect)
            assert decrypted == "secret"

    def test_result_value_corrupted_returns_raw(self, col):
        with patch("app.services.encryption.get_encryption_service") as mock_get:
            svc = EncryptionService(key=TEST_KEY)
            mock_get.return_value = svc

            result = col.process_result_value("corrupted-data", MagicMock())
            assert result == "corrupted-data"
