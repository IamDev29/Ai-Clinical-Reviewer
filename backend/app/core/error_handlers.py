"""Global exception handlers providing consistent JSON error envelopes without leaking stack traces."""
import logging
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    ClinicalProcessingError,
    DocumentQualityError,
    ExtractionRepairFailedError,
    ExtractionSchemaError,
)

logger = logging.getLogger("app.errors")


def map_http_status_to_code(status_code: int) -> str:
    """Map standard HTTP status codes to machine-readable error codes."""
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        413: "FILE_TOO_LARGE",
        415: "UNSUPPORTED_MEDIA_TYPE",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    return mapping.get(status_code, f"HTTP_{status_code}")


def create_error_payload(
    code: str,
    message: str,
    details: Optional[Any] = None,
) -> Dict[str, Any]:
    """Create standard error envelope matching {success: false, error: {code, message, details}}."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Registers all global exception handlers on the FastAPI application."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = map_http_status_to_code(exc.status_code)
        message = str(exc.detail) if exc.detail else "An HTTP error occurred."
        
        # Custom code override if detail specifies unsupported or payload too large
        if "Unsupported file type" in message or "unsupported" in message.lower():
            code = "UNSUPPORTED_FILE_TYPE"
        elif "maximum allowed size" in message or "too large" in message.lower():
            code = "FILE_TOO_LARGE"

        logger.warning(
            f"HTTP {exc.status_code} on {request.method} {request.url.path}: {message}",
            extra={
                "structured_data": {
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": exc.status_code,
                    "error_code": code,
                }
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=create_error_payload(code=code, message=message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        error_msgs = []
        for err in errors:
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            error_msgs.append(f"{loc}: {msg}" if loc else msg)

        formatted_msg = f"Request validation failed: {'; '.join(error_msgs)}"

        logger.warning(
            f"Validation error on {request.method} {request.url.path}: {formatted_msg}",
            extra={
                "structured_data": {
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "error_code": "VALIDATION_ERROR",
                    "details": errors,
                }
            },
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=create_error_payload(
                code="VALIDATION_ERROR",
                message=formatted_msg,
                details=errors,
            ),
        )

    @app.exception_handler(DocumentQualityError)
    async def document_quality_exception_handler(request: Request, exc: DocumentQualityError) -> JSONResponse:
        logger.warning(
            f"Document quality rejection on {request.method} {request.url.path}: {str(exc)}",
            extra={
                "structured_data": {
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "error_code": "DOCUMENT_QUALITY_ERROR",
                }
            },
        )

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=create_error_payload(
                code="DOCUMENT_QUALITY_ERROR",
                message=str(exc),
            ),
        )

    @app.exception_handler(ClinicalProcessingError)
    async def clinical_processing_exception_handler(request: Request, exc: ClinicalProcessingError) -> JSONResponse:
        logger.error(
            f"Clinical processing error on {request.method} {request.url.path}: {str(exc)}",
            extra={
                "structured_data": {
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "error_code": "PROCESSING_FAILURE",
                }
            },
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=create_error_payload(
                code="PROCESSING_FAILURE",
                message=str(exc),
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Structured log with full traceback for diagnostics, but NEVER expose traceback to client
        logger.error(
            f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}",
            exc_info=exc,
            extra={
                "structured_data": {
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "exception_type": type(exc).__name__,
                }
            },
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=create_error_payload(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal error occurred while processing the request.",
            ),
        )
