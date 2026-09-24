"""Health check endpoints for deployment platforms and container orchestration."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Overall health status: 'ok' or 'degraded'")
    app: str = Field(..., description="Service application name")
    environment: str = Field(..., description="Deployment environment")
    version: str = Field(..., description="Application release version")
    database: str = Field(..., description="Database connectivity status: 'connected' or 'disconnected'")
    has_api_key: bool = Field(False, description="Whether Gemini API key is configured")
    mode: str = Field("offline_demo_fallback", description="Extraction engine mode: 'gemini_ai' or 'offline_demo_fallback'")
    details: Optional[str] = Field(None, description="Optional diagnostic status message")


@router.get("", response_model=HealthCheckResponse, summary="Service Health and Database Connectivity")
def health_check(db: Session = Depends(get_db)) -> HealthCheckResponse:
    """
    Returns the operational status of the service and validates PostgreSQL database connectivity.
    Ideal for Render, Railway, AWS, and Docker container health probes.
    """
    db_status = "connected"
    details = None
    overall_status = "ok"

    try:
        # Perform quick non-blocking database ping
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning(f"Database health check query failed: {e}")
        db_status = "disconnected"
        overall_status = "degraded"
        details = "Database connection unavailable"

    has_key = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
    mode_str = "gemini_ai" if has_key else "offline_demo_fallback"

    return HealthCheckResponse(
        status=overall_status,
        app=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        version="0.1.0",
        database=db_status,
        has_api_key=has_key,
        mode=mode_str,
        details=details,
    )
