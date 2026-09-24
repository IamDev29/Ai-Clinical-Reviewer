"""CRUD operations for Report."""
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.models.report import Report, ReportStatus, InputType
from app.schemas.report import ReportCreate, ReportUpdateStatus


def create_report(
    db: Session,
    report_in: Union[ReportCreate, Dict[str, Any]],
) -> Report:
    """Create a new report in the database."""
    if isinstance(report_in, dict):
        report_data = report_in.copy()
    else:
        report_data = report_in.model_dump()

    # Cast string enums to Enum types if needed
    if "status" in report_data and isinstance(report_data["status"], str):
        report_data["status"] = ReportStatus(report_data["status"])
    if "input_type" in report_data and isinstance(report_data["input_type"], str):
        report_data["input_type"] = InputType(report_data["input_type"])

    db_report = Report(**report_data)
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


def get_report_by_id(db: Session, report_id: int) -> Optional[Report]:
    """Retrieve a single report by its ID."""
    return db.query(Report).filter(Report.id == report_id).first()


def list_reports(
    db: Session,
    skip: int = 0,
    limit: int = 20,
) -> List[Report]:
    """List reports ordered by newest first (created_at DESC, id DESC), paginated."""
    return (
        db.query(Report)
        .order_by(Report.created_at.desc(), Report.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_reports(db: Session) -> int:
    """Get the total count of reports."""
    return db.query(Report).count()


def update_report_status(
    db: Session,
    report_id: int,
    status: Union[ReportStatus, str],
    error_message: Optional[str] = None,
    extracted_text: Optional[str] = None,
    report_summary: Optional[str] = None,
    structured_report: Optional[Dict[str, Any]] = None,
) -> Optional[Report]:
    """Update the status and output fields of a report."""
    db_report = get_report_by_id(db, report_id=report_id)
    if not db_report:
        return None

    if isinstance(status, str):
        status = ReportStatus(status)

    db_report.status = status

    if error_message is not None:
        db_report.error_message = error_message
    if extracted_text is not None:
        db_report.extracted_text = extracted_text
    if report_summary is not None:
        db_report.report_summary = report_summary
    if structured_report is not None:
        db_report.structured_report = structured_report

    db.commit()
    db.refresh(db_report)
    return db_report
