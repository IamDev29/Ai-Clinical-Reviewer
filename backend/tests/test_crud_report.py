"""Tests for Report CRUD operations."""
import time
from sqlalchemy.orm import Session
from app.crud.crud_report import (
    create_report,
    get_report_by_id,
    list_reports,
    count_reports,
    update_report_status,
)
from app.models.report import ReportStatus, InputType
from app.schemas.report import ReportCreate


def test_create_report_with_schema(db: Session):
    """Test creating a report using Pydantic ReportCreate schema."""
    report_in = ReportCreate(
        input_type=InputType.PDF,
        raw_input_ref="s3://bucket/test_doc.pdf",
        status=ReportStatus.PENDING,
        extracted_text="Sample extracted text",
        report_summary="Sample summary",
        structured_report={"trial_id": "NCT12345", "eligibility": {"min_age": 18}},
    )

    report = create_report(db, report_in=report_in)

    assert report.id is not None
    assert report.input_type == InputType.PDF
    assert report.status == ReportStatus.PENDING
    assert report.raw_input_ref == "s3://bucket/test_doc.pdf"
    assert report.extracted_text == "Sample extracted text"
    assert report.report_summary == "Sample summary"
    assert report.structured_report == {"trial_id": "NCT12345", "eligibility": {"min_age": 18}}
    assert report.created_at is not None
    assert report.error_message is None


def test_create_report_with_dict(db: Session):
    """Test creating a report using a dictionary."""
    report_dict = {
        "input_type": "text",
        "raw_input_ref": "Raw clinical paragraph input",
        "status": "pending",
    }

    report = create_report(db, report_in=report_dict)

    assert report.id is not None
    assert report.input_type == InputType.TEXT
    assert report.status == ReportStatus.PENDING
    assert report.raw_input_ref == "Raw clinical paragraph input"


def test_get_report_by_id(db: Session):
    """Test retrieving a report by primary key."""
    report = create_report(
        db,
        report_in={
            "input_type": InputType.IMAGE,
            "raw_input_ref": "/images/scan_101.png",
            "status": ReportStatus.PROCESSING,
        },
    )

    fetched = get_report_by_id(db, report_id=report.id)
    assert fetched is not None
    assert fetched.id == report.id
    assert fetched.input_type == InputType.IMAGE
    assert fetched.status == ReportStatus.PROCESSING

    # Test non-existent ID
    non_existent = get_report_by_id(db, report_id=999999)
    assert non_existent is None


def test_update_report_status_success(db: Session):
    """Test updating the status and output metadata of a report."""
    report = create_report(
        db,
        report_in={
            "input_type": InputType.TEXT,
            "raw_input_ref": "Patient clinical note #44",
            "status": ReportStatus.PENDING,
        },
    )

    updated = update_report_status(
        db,
        report_id=report.id,
        status=ReportStatus.COMPLETED,
        extracted_text="Parsed patient note content",
        report_summary="Patient meets trial criteria.",
        structured_report={"matched": True, "score": 0.98},
    )

    assert updated is not None
    assert updated.id == report.id
    assert updated.status == ReportStatus.COMPLETED
    assert updated.extracted_text == "Parsed patient note content"
    assert updated.report_summary == "Patient meets trial criteria."
    assert updated.structured_report == {"matched": True, "score": 0.98}
    assert updated.error_message is None


def test_update_report_status_failure(db: Session):
    """Test updating a report to failed state with error message."""
    report = create_report(
        db,
        report_in={
            "input_type": InputType.PDF,
            "raw_input_ref": "/corrupted/doc.pdf",
            "status": ReportStatus.PROCESSING,
        },
    )

    updated = update_report_status(
        db,
        report_id=report.id,
        status=ReportStatus.FAILED,
        error_message="Corrupted PDF stream could not be parsed",
    )

    assert updated is not None
    assert updated.status == ReportStatus.FAILED
    assert updated.error_message == "Corrupted PDF stream could not be parsed"


def test_update_report_non_existent(db: Session):
    """Test updating a non-existent report returns None."""
    result = update_report_status(
        db,
        report_id=888888,
        status=ReportStatus.COMPLETED,
    )
    assert result is None


def test_list_reports_pagination_and_ordering(db: Session):
    """Test list_reports returns reports sorted by newest first (created_at DESC, id DESC)."""
    reports = []
    for i in range(5):
        r = create_report(
            db,
            report_in={
                "input_type": InputType.TEXT,
                "raw_input_ref": f"Report #{i + 1}",
                "status": ReportStatus.PENDING,
            },
        )
        reports.append(r)
        time.sleep(0.01)

    assert count_reports(db) >= 5

    # Fetch first page (3 items)
    page_1 = list_reports(db, skip=0, limit=3)
    assert len(page_1) == 3
    # Newest report (Report #5) should be first
    assert page_1[0].raw_input_ref == "Report #5"
    assert page_1[1].raw_input_ref == "Report #4"
    assert page_1[2].raw_input_ref == "Report #3"

    # Fetch second page
    page_2 = list_reports(db, skip=3, limit=3)
    assert len(page_2) >= 2
    assert page_2[0].raw_input_ref == "Report #2"
    assert page_2[1].raw_input_ref == "Report #1"
