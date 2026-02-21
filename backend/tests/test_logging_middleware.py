"""Tests for logging, error handling, and audit middleware — task 3.7."""

from __future__ import annotations

import logging

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.middleware.audit import _ALWAYS_AUDIT_PREFIXES, AuditMiddleware
from app.middleware.error_handler import (
    _status_to_code,
    register_exception_handlers,
)
from app.middleware.logging import CORRELATION_ID_HEADER, RequestLoggingMiddleware

# ---------------------------------------------------------------------------
# Shared test app factory
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ok")
    async def _ok() -> dict:
        return {"status": "ok"}

    @app.get("/boom")
    async def _boom() -> dict:
        raise RuntimeError("unexpected error")

    @app.get("/http-err")
    async def _http_err() -> dict:
        raise HTTPException(status_code=404, detail="not found")

    @app.post("/mutate")
    async def _mutate() -> dict:
        return {"mutated": True}

    @app.get("/api/v1/auth/login")
    async def _login() -> dict:
        return {"token": "abc"}

    return app


# ---------------------------------------------------------------------------
# RequestLoggingMiddleware — correlation ID
# ---------------------------------------------------------------------------


class TestCorrelationId:
    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(_make_app())

    def test_response_has_correlation_id_header(self, client: TestClient) -> None:
        resp = client.get("/ok")
        assert CORRELATION_ID_HEADER in resp.headers

    def test_correlation_id_is_uuid_format(self, client: TestClient) -> None:
        import uuid

        resp = client.get("/ok")
        cid = resp.headers[CORRELATION_ID_HEADER]
        # Should parse as a valid UUID4 without raising.
        parsed = uuid.UUID(cid)
        assert parsed.version == 4

    def test_each_request_gets_unique_correlation_id(self, client: TestClient) -> None:
        cid1 = client.get("/ok").headers[CORRELATION_ID_HEADER]
        cid2 = client.get("/ok").headers[CORRELATION_ID_HEADER]
        assert cid1 != cid2

    def test_error_response_still_has_correlation_id(self, client: TestClient) -> None:
        resp = client.get("/http-err")
        assert CORRELATION_ID_HEADER in resp.headers


# ---------------------------------------------------------------------------
# RequestLoggingMiddleware — log output
# ---------------------------------------------------------------------------


class TestRequestLogging:
    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(_make_app())

    def test_logs_request_started(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="prickncare.request"):
            client.get("/ok")
        messages = [r.message for r in caplog.records if r.name == "prickncare.request"]
        assert any("request_started" in m for m in messages)

    def test_logs_request_finished(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="prickncare.request"):
            client.get("/ok")
        messages = [r.message for r in caplog.records if r.name == "prickncare.request"]
        assert any("request_finished" in m for m in messages)

    def test_log_record_contains_method_and_path(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="prickncare.request"):
            client.get("/ok")
        records = [r for r in caplog.records if r.name == "prickncare.request"]
        started = next(r for r in records if r.message == "request_started")
        assert started.__dict__["method"] == "GET"
        assert started.__dict__["path"] == "/ok"

    def test_log_record_contains_status_code(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="prickncare.request"):
            client.get("/ok")
        records = [r for r in caplog.records if r.name == "prickncare.request"]
        finished = next(r for r in records if r.message == "request_finished")
        assert finished.__dict__["status_code"] == 200

    def test_log_record_contains_duration_ms(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="prickncare.request"):
            client.get("/ok")
        records = [r for r in caplog.records if r.name == "prickncare.request"]
        finished = next(r for r in records if r.message == "request_finished")
        assert "duration_ms" in finished.__dict__
        assert finished.__dict__["duration_ms"] >= 0


# ---------------------------------------------------------------------------
# Error handler — consistent response envelope
# ---------------------------------------------------------------------------


class TestErrorHandler:
    @pytest.fixture
    def client(self) -> TestClient:
        # raise_server_exceptions=False so 500s don't propagate in TestClient.
        return TestClient(_make_app(), raise_server_exceptions=False)

    def test_http_exception_returns_error_envelope(self, client: TestClient) -> None:
        resp = client.get("/http-err")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "NOT_FOUND"
        assert "message" in body["error"]

    def test_http_exception_includes_correlation_id(self, client: TestClient) -> None:
        resp = client.get("/http-err")
        body = resp.json()
        assert "correlation_id" in body

    def test_unhandled_exception_returns_500(self, client: TestClient) -> None:
        resp = client.get("/boom")
        assert resp.status_code == 500

    def test_unhandled_exception_returns_error_envelope(
        self, client: TestClient
    ) -> None:
        resp = client.get("/boom")
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"

    def test_unhandled_exception_does_not_expose_traceback(
        self, client: TestClient
    ) -> None:
        resp = client.get("/boom")
        body = resp.json()
        # No stack trace in the response body.
        assert "traceback" not in str(body)
        assert "Traceback" not in str(body)

    def test_validation_error_returns_422(self) -> None:
        from fastapi import FastAPI
        from pydantic import BaseModel

        app2 = FastAPI()
        register_exception_handlers(app2)

        class _Body(BaseModel):
            name: str

        @app2.post("/validate")
        async def _ep(body: _Body) -> dict:
            return {"name": body.name}

        c = TestClient(app2, raise_server_exceptions=False)
        resp = c.post("/validate", json={})  # missing 'name'
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "fields" in body["error"]["details"]

    def test_500_log_contains_traceback(self, caplog: pytest.LogCaptureFixture) -> None:
        client = TestClient(_make_app(), raise_server_exceptions=False)
        with caplog.at_level(logging.ERROR, logger="prickncare.error"):
            client.get("/boom")
        records = [r for r in caplog.records if r.name == "prickncare.error"]
        assert records, "Expected at least one error log record"
        assert "traceback" in records[0].__dict__


# ---------------------------------------------------------------------------
# _status_to_code utility
# ---------------------------------------------------------------------------


class TestStatusToCode:
    def test_known_codes(self) -> None:
        assert _status_to_code(400) == "BAD_REQUEST"
        assert _status_to_code(401) == "UNAUTHORIZED"
        assert _status_to_code(403) == "FORBIDDEN"
        assert _status_to_code(404) == "NOT_FOUND"
        assert _status_to_code(422) == "VALIDATION_ERROR"
        assert _status_to_code(429) == "TOO_MANY_REQUESTS"
        assert _status_to_code(500) == "INTERNAL_SERVER_ERROR"

    def test_unknown_code_uses_generic_format(self) -> None:
        assert _status_to_code(418) == "HTTP_418"


# ---------------------------------------------------------------------------
# AuditMiddleware — event selection
# ---------------------------------------------------------------------------


class TestAuditMiddleware:
    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(_make_app())

    def test_post_request_is_audited(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="prickncare.audit"):
            client.post("/mutate")
        records = [r for r in caplog.records if r.name == "prickncare.audit"]
        assert any("audit_event" in r.message for r in records)

    def test_auth_path_get_is_audited(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="prickncare.audit"):
            client.get("/api/v1/auth/login")
        records = [r for r in caplog.records if r.name == "prickncare.audit"]
        assert any("audit_event" in r.message for r in records)

    def test_plain_get_is_not_audited(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="prickncare.audit"):
            client.get("/ok")
        records = [r for r in caplog.records if r.name == "prickncare.audit"]
        assert not records

    def test_audit_record_contains_method_and_path(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="prickncare.audit"):
            client.post("/mutate")
        records = [r for r in caplog.records if r.name == "prickncare.audit"]
        rec = records[0]
        assert rec.__dict__["method"] == "POST"
        assert rec.__dict__["path"] == "/mutate"

    def test_audit_record_contains_status_code(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="prickncare.audit"):
            client.post("/mutate")
        records = [r for r in caplog.records if r.name == "prickncare.audit"]
        assert records[0].__dict__["status_code"] == 200

    def test_always_audit_prefixes_set(self) -> None:
        assert any("auth" in p for p in _ALWAYS_AUDIT_PREFIXES)
