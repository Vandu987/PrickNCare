"""Tests for audit logging middleware and service — task 16.1."""

from app.middleware.audit import (
    AuditMiddleware,
    _derive_action,
    _derive_entity_type,
)
from app.models.audit import AuditLog

# ---------------------------------------------------------------------------
# Helper action / entity derivation
# ---------------------------------------------------------------------------


class TestDeriveAction:
    def test_post_create(self) -> None:
        assert _derive_action("POST", "/api/v1/orders") == "create"

    def test_put_update(self) -> None:
        assert _derive_action("PUT", "/api/v1/orders/123") == "update"

    def test_patch_update(self) -> None:
        assert _derive_action("PATCH", "/api/v1/orders/123") == "update"

    def test_delete(self) -> None:
        assert _derive_action("DELETE", "/api/v1/orders/123") == "delete"

    def test_auth_login(self) -> None:
        assert _derive_action("POST", "/api/v1/auth/login") == "login"

    def test_auth_logout(self) -> None:
        assert _derive_action("POST", "/api/v1/auth/logout") == "logout"

    def test_auth_otp(self) -> None:
        assert _derive_action("POST", "/api/v1/auth/otp/verify") == "login"

    def test_auth_generic(self) -> None:
        assert _derive_action("GET", "/api/v1/auth/me") == "auth"


class TestDeriveEntityType:
    def test_orders(self) -> None:
        assert _derive_entity_type("/api/v1/orders") == "Order"

    def test_clients(self) -> None:
        assert _derive_entity_type("/api/v1/clients/123") == "Client"

    def test_packages(self) -> None:
        assert _derive_entity_type("/api/v1/packages") == "Package"


# ---------------------------------------------------------------------------
# Model fields — request_method, request_path, response_status
# ---------------------------------------------------------------------------


class TestAuditLogNewFields:
    def test_request_method_stored(self) -> None:
        log = AuditLog(
            action="create",
            entity_type="Order",
            request_method="POST",
            request_path="/api/v1/orders",
            response_status=201,
        )
        assert log.request_method == "POST"

    def test_request_path_stored(self) -> None:
        log = AuditLog(
            action="create",
            entity_type="Order",
            request_method="POST",
            request_path="/api/v1/orders",
            response_status=201,
        )
        assert log.request_path == "/api/v1/orders"

    def test_response_status_stored(self) -> None:
        log = AuditLog(
            action="delete",
            entity_type="Client",
            request_method="DELETE",
            request_path="/api/v1/clients/abc",
            response_status=204,
        )
        assert log.response_status == 204


# ---------------------------------------------------------------------------
# Middleware should_audit logic
# ---------------------------------------------------------------------------


class _FakeRequest:
    def __init__(self, method: str = "GET", path: str = "/") -> None:
        self.method = method

        class _URL:
            def __init__(self, p: str) -> None:
                self.path = p

        self.url = _URL(path)


class _FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code


class TestShouldAudit:
    def test_post_audited(self) -> None:
        assert AuditMiddleware._should_audit(
            _FakeRequest("POST", "/api/v1/orders"), _FakeResponse(201)
        )

    def test_get_not_audited(self) -> None:
        assert not AuditMiddleware._should_audit(
            _FakeRequest("GET", "/api/v1/orders"), _FakeResponse(200)
        )

    def test_401_audited(self) -> None:
        assert AuditMiddleware._should_audit(
            _FakeRequest("GET", "/api/v1/orders"), _FakeResponse(401)
        )

    def test_403_audited(self) -> None:
        assert AuditMiddleware._should_audit(
            _FakeRequest("GET", "/api/v1/me"), _FakeResponse(403)
        )

    def test_auth_path_always_audited(self) -> None:
        assert AuditMiddleware._should_audit(
            _FakeRequest("GET", "/api/v1/auth/me"), _FakeResponse(200)
        )

    def test_delete_audited(self) -> None:
        assert AuditMiddleware._should_audit(
            _FakeRequest("DELETE", "/api/v1/orders/1"), _FakeResponse(204)
        )

    def test_patch_audited(self) -> None:
        assert AuditMiddleware._should_audit(
            _FakeRequest("PATCH", "/api/v1/orders/1"), _FakeResponse(200)
        )
