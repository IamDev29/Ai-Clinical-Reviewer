"""Tests for global exception handlers and consistent error responses."""
from fastapi.testclient import TestClient
from app.core.config import settings


def test_error_response_unsupported_file_type(client: TestClient):
    """Trigger unsupported file type and verify consistent error envelope."""
    response = client.post(
        "/api/v1/reports",
        files={"file": ("malicious.exe", b"binary content", "application/x-msdownload")},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert "error" in payload
    assert payload["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert "Unsupported file type" in payload["error"]["message"]
    # Verify no raw traceback leaked
    assert "Traceback" not in str(payload)


def test_error_response_empty_text_and_no_file(client: TestClient):
    """Trigger empty input and verify consistent error envelope."""
    response = client.post(
        "/api/v1/reports",
        data={"text": "   "},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "BAD_REQUEST"
    assert "Either a 'text' body or a valid 'file'" in payload["error"]["message"]
    assert "Traceback" not in str(payload)


def test_error_response_huge_oversized_file(client: TestClient, monkeypatch):
    """Trigger file size limit exceeding and verify consistent error envelope."""
    # Temporarily set MAX_FILE_SIZE_MB to 1 MB for testing
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 1)

    # 1.5 MB payload
    huge_bytes = b"0" * int(1.5 * 1024 * 1024)
    response = client.post(
        "/api/v1/reports",
        files={"file": ("oversized.pdf", huge_bytes, "application/pdf")},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "FILE_TOO_LARGE"
    assert "exceeds maximum allowed size" in payload["error"]["message"]
    assert "Traceback" not in str(payload)


def test_error_response_not_found(client: TestClient):
    """Trigger 404 for non-existent report ID and verify error envelope."""
    response = client.get("/api/v1/reports/9999999")

    assert response.status_code == 404
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "NOT_FOUND"
    assert "not found" in payload["error"]["message"].lower()
    assert "Traceback" not in str(payload)


def test_error_response_validation_error(client: TestClient):
    """Trigger 422 RequestValidationError and verify clean error envelope."""
    # Negative limit is invalid (ge=1)
    response = client.get("/api/v1/reports?limit=-5")

    assert response.status_code == 422
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert "validation failed" in payload["error"]["message"].lower()
    assert "Traceback" not in str(payload)


def test_error_response_unhandled_internal_exception(monkeypatch):
    """Trigger unexpected unhandled server exception and verify no stack trace is leaked."""
    from app.main import app
    from app.api.v1.endpoints import reports

    def broken_list_reports(*args, **kwargs):
        raise RuntimeError("Simulated internal catastrophic database connection failure")

    monkeypatch.setattr(reports, "list_reports", broken_list_reports)

    # Use client with raise_server_exceptions=False to receive the HTTP 500 response
    unhandled_client = TestClient(app, raise_server_exceptions=False)
    response = unhandled_client.get("/api/v1/reports")

    assert response.status_code == 500
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "unexpected internal error" in payload["error"]["message"]
    # Crucial guarantee: no internal exception names or stack traces in client response
    assert "RuntimeError" not in str(payload)
    assert "Simulated internal catastrophic" not in str(payload)
    assert "Traceback" not in str(payload)
