"""Tests for Settings config and health endpoint — task 3.1."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings

# ---------------------------------------------------------------------------
# Settings tests
# ---------------------------------------------------------------------------


class TestSettings:
    def test_default_app_env(self) -> None:
        s = Settings()
        assert s.APP_ENV == "development"

    def test_default_app_version(self) -> None:
        s = Settings()
        assert s.APP_VERSION == "0.1.0"

    def test_default_debug(self) -> None:
        s = Settings()
        assert s.DEBUG is True

    def test_default_jwt_algorithm(self) -> None:
        s = Settings()
        assert s.JWT_ALGORITHM == "HS256"

    def test_default_access_token_expire(self) -> None:
        s = Settings()
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 15

    def test_default_refresh_token_expire(self) -> None:
        s = Settings()
        assert s.REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_default_session_timeout(self) -> None:
        s = Settings()
        assert s.SESSION_TIMEOUT_MINUTES == 30

    def test_default_otp_expire(self) -> None:
        s = Settings()
        assert s.OTP_EXPIRE_MINUTES == 5

    def test_default_otp_length(self) -> None:
        s = Settings()
        assert s.OTP_LENGTH == 6

    def test_default_otp_max_attempts(self) -> None:
        s = Settings()
        assert s.OTP_MAX_ATTEMPTS == 3

    def test_default_sms_provider(self) -> None:
        s = Settings()
        assert s.SMS_PROVIDER == "msg91"

    def test_default_rate_limit_default(self) -> None:
        s = Settings()
        assert s.RATE_LIMIT_DEFAULT == 100

    def test_default_rate_limit_admin(self) -> None:
        s = Settings()
        assert s.RATE_LIMIT_ADMIN == 500

    def test_default_rate_limit_login(self) -> None:
        s = Settings()
        assert s.RATE_LIMIT_LOGIN == 5

    def test_allowed_origins_list_single(self) -> None:
        s = Settings(ALLOWED_ORIGINS="http://localhost:3000")
        assert s.allowed_origins_list == ["http://localhost:3000"]

    def test_allowed_origins_list_multiple(self) -> None:
        s = Settings(ALLOWED_ORIGINS="http://localhost:3000,http://localhost:3001")
        assert s.allowed_origins_list == [
            "http://localhost:3000",
            "http://localhost:3001",
        ]

    def test_allowed_origins_list_strips_whitespace(self) -> None:
        s = Settings(ALLOWED_ORIGINS=" http://a.com , http://b.com ")
        assert s.allowed_origins_list == ["http://a.com", "http://b.com"]

    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_ENV", "production")
        s = Settings()
        assert s.APP_ENV == "production"

    def test_get_settings_returns_settings_instance(self) -> None:
        s = get_settings()
        assert isinstance(s, Settings)

    def test_get_settings_is_cached(self) -> None:
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2


# ---------------------------------------------------------------------------
# Health endpoint tests
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    @pytest.fixture
    def client(self) -> TestClient:
        from app.main import app

        return TestClient(app)

    def test_health_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_health_response_has_status(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.json()["status"] == "healthy"

    def test_health_response_has_version(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert "version" in resp.json()

    def test_health_response_has_environment(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert "environment" in resp.json()

    def test_health_version_matches_settings(self, client: TestClient) -> None:
        from app.core.config import settings

        resp = client.get("/api/v1/health")
        assert resp.json()["version"] == settings.APP_VERSION
