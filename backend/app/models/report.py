"""Report SQLAlchemy Model."""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SAEnum, JSON
from sqlalchemy.dialects.postgresql import JSONB
from app.db.session import Base


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class InputType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    PDF = "pdf"


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    status = Column(
        SAEnum(
            ReportStatus,
            name="report_status",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
        ),
        default=ReportStatus.PENDING,
        nullable=False,
        index=True,
    )
    input_type = Column(
        SAEnum(
            InputType,
            name="input_type",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )
    raw_input_ref = Column(Text, nullable=False)
    extracted_text = Column(Text, nullable=True)
    report_summary = Column(Text, nullable=True)
    structured_report = Column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    error_message = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, status={self.status}, input_type={self.input_type})>"
