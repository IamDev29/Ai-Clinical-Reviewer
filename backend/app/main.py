"""Main FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.api.v1.endpoints import health
from app.core.config import settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging_config import setup_logging

# Setup structured logging
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

from app.db.base import Base
from app.db.session import engine

# Register global consistent error envelope handlers
register_exception_handlers(app)

@app.on_event("startup")
def on_startup():
    """Auto-create database tables on application startup."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        pass

# Set all CORS enabled origins
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Direct root-level health check for cloud platform liveness probes (Render, Railway, K8s, Docker)
app.include_router(health.router, prefix="/health", tags=["health"])

# Versioned API routes (/api/v1/...)
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint welcoming users and providing documentation path."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/health",
        "api_v1_health": f"{settings.API_V1_STR}/health",
    }
