from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:password@localhost:5432/prickncare"
    )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-this-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SESSION_TIMEOUT_MINUTES: int = 30

    # OTP
    OTP_EXPIRE_MINUTES: int = 5
    OTP_LENGTH: int = 6
    OTP_MAX_ATTEMPTS: int = 3
    OTP_RATE_LIMIT_PER_HOUR: int = 20

    # SMS Gateway
    SMS_PROVIDER: str = "msg91"  # msg91 | twilio
    SMS_API_KEY: str = ""
    MSG91_SENDER_ID: str = "PRKNCA"
    MSG91_ROUTE: int = 4
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # Email
    EMAIL_PROVIDER: str = "sendgrid"  # sendgrid | ses
    SENDGRID_API_KEY: str = ""
    AWS_SES_REGION: str = "ap-south-1"
    EMAIL_FROM: str = ""

    # Firebase Cloud Messaging (Push)
    FCM_PROJECT_ID: str = ""
    FCM_CREDENTIALS_PATH: str = ""

    # Rate Limiting (requests per minute)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: int = 100
    RATE_LIMIT_ADMIN: int = 500
    RATE_LIMIT_CLIENT: int = 200
    RATE_LIMIT_PHLEBOTOMIST: int = 100
    RATE_LIMIT_AUTH: int = 10  # auth endpoints (login, OTP, register)
    RATE_LIMIT_LOGIN: int = 5  # brute-force protection

    # AWS / S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str = ""
    CLOUDFRONT_DOMAIN: str = ""
    LOCAL_STORAGE_DIR: str = "uploads"

    # File Upload
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS_DOCUMENTS: str = "pdf,doc,docx,xls,xlsx,csv,txt"
    ALLOWED_EXTENSIONS_COLLECTION_PHOTOS: str = "jpg,jpeg,png,webp"
    ALLOWED_EXTENSIONS_SIGNATURES: str = "jpg,jpeg,png,svg"
    ALLOWED_EXTENSIONS_REPORTS: str = "pdf,jpg,jpeg,png"

    # Encryption
    ENCRYPTION_KEY: str = (
        ""  # Fernet key; generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
    )

    # Audit
    AUDIT_RETENTION_DAYS: int = 90

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
