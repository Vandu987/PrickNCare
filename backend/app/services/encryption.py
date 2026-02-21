"""Data encryption service for sensitive fields using Fernet symmetric encryption."""

import logging

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import String, TypeDecorator

from app.core.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """Encrypt/decrypt sensitive data using Fernet (AES-128-CBC via cryptography)."""

    def __init__(self, key: str | None = None):
        raw_key = key or settings.ENCRYPTION_KEY
        if not raw_key:
            raise ValueError(
                "ENCRYPTION_KEY is not set. Generate one with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        # Accept both url-safe-base64 keys and plain strings
        try:
            self._fernet = Fernet(
                raw_key.encode() if isinstance(raw_key, str) else raw_key
            )
        except (ValueError, Exception) as exc:
            raise ValueError(f"Invalid ENCRYPTION_KEY: {exc}") from exc

    # -- core -----------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext → url-safe base64 ciphertext string."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext → plaintext string."""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            logger.error("Decryption failed – invalid token or corrupted data")
            raise ValueError(
                "Decryption failed: invalid or corrupted ciphertext"
            ) from exc

    # -- field-level helpers --------------------------------------------------

    def encrypt_phone(self, phone: str) -> str:
        """Encrypt a phone number."""
        return self.encrypt(phone)

    def decrypt_phone(self, ciphertext: str) -> str:
        """Decrypt a phone number."""
        return self.decrypt(ciphertext)

    def encrypt_address(self, address: str) -> str:
        """Encrypt an address."""
        return self.encrypt(address)

    def decrypt_address(self, ciphertext: str) -> str:
        """Decrypt an address."""
        return self.decrypt(ciphertext)

    def encrypt_medical_info(self, info: str) -> str:
        """Encrypt medical/health information."""
        return self.encrypt(info)

    def decrypt_medical_info(self, ciphertext: str) -> str:
        """Decrypt medical/health information."""
        return self.decrypt(ciphertext)

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet key (url-safe base64)."""
        return Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# Module-level singleton (lazy)
# ---------------------------------------------------------------------------

_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Return a module-level EncryptionService singleton."""
    global _service  # noqa: PLW0603
    if _service is None:
        _service = EncryptionService()
    return _service


# ---------------------------------------------------------------------------
# SQLAlchemy TypeDecorator for transparent column encryption
# ---------------------------------------------------------------------------


class EncryptedString(TypeDecorator):
    """A SQLAlchemy column type that transparently encrypts/decrypts values.

    Usage::

        class Patient(Base):
            phone = Column(EncryptedString(length=512), nullable=True)
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int = 1024, **kwargs):
        super().__init__(length=length, **kwargs)

    def process_bind_param(self, value, dialect):
        """Encrypt before writing to DB."""
        if value is None:
            return None
        return get_encryption_service().encrypt(value)

    def process_result_value(self, value, dialect):
        """Decrypt after reading from DB."""
        if value is None:
            return None
        try:
            return get_encryption_service().decrypt(value)
        except ValueError:
            logger.warning("Could not decrypt column value – returning raw")
            return value
