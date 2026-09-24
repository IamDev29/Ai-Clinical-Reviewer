"""Tests for sample reports seeding."""
from sqlalchemy.orm import Session
from scripts.seed_reports import seed_sample_reports, SAMPLE_REPORTS_DATA
from app.crud.crud_report import list_reports, get_report_by_id
from app.models.report import ReportStatus


def test_seed_sample_reports(db: Session):
    """Verify that seed_sample_reports inserts the expected synthetic clinical reports."""
    seeded = seed_sample_reports(db)
    assert len(seeded) == 3

    # Check first seeded report properties (Clean Note)
    report_1 = seeded[0]
    assert report_1.status == ReportStatus.COMPLETED
    assert "John Doe" in report_1.extracted_text

    # Check second seeded report properties (Contradiction Note)
    report_2 = seeded[1]
    assert report_2.status == ReportStatus.COMPLETED
    assert "Penicillin" in report_2.extracted_text

    # Re-running seed should be idempotent
    seeded_again = seed_sample_reports(db)
    assert len(seeded_again) == 3
