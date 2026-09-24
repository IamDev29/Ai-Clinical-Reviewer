"""API v1 router registry."""
from fastapi import APIRouter
from app.api.v1.endpoints import health, reports

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
