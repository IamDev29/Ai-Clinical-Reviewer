"""Base database models import for Alembic discovery."""
from app.db.session import Base
from app.models.report import Report, ReportStatus, InputType

__all__ = ["Base", "Report", "ReportStatus", "InputType"]
