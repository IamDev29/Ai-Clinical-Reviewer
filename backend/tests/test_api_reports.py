"""Tests for POST /api/v1/reports and document extraction workflows."""
import io
import fitz  # PyMuPDF
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.report import ReportStatus, InputType
from app.crud.crud_report import get_report_by_id


def create_sample_digital_pdf_bytes() -> bytes:
    """Create a digital PDF with rich text content."""
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "CLINICAL STUDY PROTOCOL: ONCOLOGY PHASE 3 INVESTIGATION\n"
        "Patient: Robert Johnson, 61yo Male. Diagnoses: Metastatic Melanoma.\n"
        "Inclusion Criteria: Patients aged >= 18 with confirmed BRAF V600E mutation.\n"
        "Exclusion Criteria: Prior BRAF-targeted therapy, active autoimmune disease.\n"
        "Endpoints: Primary: Progression Free Survival (PFS); Secondary: Overall Response Rate (ORR)."
    )
    page.insert_text((50, 72), text, fontsize=11)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def create_sample_scanned_pdf_bytes() -> bytes:
    """Create a PDF with minimal text (< 50 chars) resembling a scanned document."""
    doc = fitz.open()
    page = doc.new_page()
    # Minimal text under 50 char threshold
    page.insert_text((50, 72), "Scan #1", fontsize=10)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def create_sample_image_bytes(format_type: str = "PNG") -> bytes:
    """Create a test image in bytes."""
    img = Image.new("RGB", (300, 200), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format=format_type)
    return buf.getvalue()


def test_post_report_plain_text(client: TestClient, db: Session):
    """Test POST /api/v1/reports with plain text clinical note."""
    text_content = (
        "Patient ID 10928: 55-year-old female presenting with newly diagnosed stage II breast cancer. "
        "Candidate for neo-adjuvant chemotherapy trial NCT00998811."
    )
    response = client.post(
        "/api/v1/reports",
        data={"text": text_content},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["input_type"] == "text"
    assert data["status"] in ["pending", "processing", "completed"]
    assert data["raw_input_ref"] == text_content

    # Check that background processing completed the record
    report = get_report_by_id(db, data["id"])
    assert report is not None
    assert report.status == ReportStatus.COMPLETED
    assert report.extracted_text == text_content
    assert report.report_summary is not None
    assert "patient_information" in report.structured_report
    assert "diagnoses" in report.structured_report


def test_post_report_digital_pdf(client: TestClient, db: Session):
    """Test POST /api/v1/reports with digital PDF upload extracted via PyMuPDF."""
    pdf_bytes = create_sample_digital_pdf_bytes()
    response = client.post(
        "/api/v1/reports",
        files={"file": ("protocol_sample.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["input_type"] == "pdf"
    assert "protocol_sample.pdf" in data["raw_input_ref"]

    # Verify background extraction with PyMuPDF
    report = get_report_by_id(db, data["id"])
    assert report is not None
    assert report.status == ReportStatus.COMPLETED
    assert "Metastatic Melanoma" in report.extracted_text
    assert report.report_summary is not None
    assert "patient_information" in report.structured_report


def test_post_report_scanned_pdf_fallback_to_vision(client: TestClient, db: Session):
    """Test POST /api/v1/reports with scanned PDF triggering page image rendering and vision fallback."""
    scanned_pdf_bytes = create_sample_scanned_pdf_bytes()
    response = client.post(
        "/api/v1/reports",
        files={"file": ("scanned_doc.pdf", scanned_pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["input_type"] == "pdf"

    # Verify fallback execution
    report = get_report_by_id(db, data["id"])
    assert report is not None
    assert report.status == ReportStatus.COMPLETED
    assert report.report_summary is not None
    assert "patient_information" in report.structured_report


def test_post_report_image_upload(client: TestClient, db: Session):
    """Test POST /api/v1/reports with JPG/PNG image upload routing to vision pipeline."""
    png_bytes = create_sample_image_bytes("PNG")
    response = client.post(
        "/api/v1/reports",
        files={"file": ("pathology_scan.png", png_bytes, "image/png")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["input_type"] == "image"

    # Verify vision pipeline execution
    report = get_report_by_id(db, data["id"])
    assert report is not None
    assert report.status == ReportStatus.COMPLETED
    assert report.report_summary is not None
    assert "patient_information" in report.structured_report


def test_post_report_unsupported_file_type(client: TestClient):
    """Test POST /api/v1/reports rejects unsupported file extensions with 400 Bad Request."""
    dummy_bytes = b"echo 'malicious or unsupported file content'"
    response = client.post(
        "/api/v1/reports",
        files={"file": ("unsupported_script.sh", dummy_bytes, "application/x-sh")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["error"]["message"]


def test_post_report_empty_request(client: TestClient):
    """Test POST /api/v1/reports rejects empty payload with 400 Bad Request."""
    response = client.post(
        "/api/v1/reports",
        data={"text": "   "},
    )
    assert response.status_code == 400
    assert "Either a 'text' body or a valid 'file'" in response.json()["error"]["message"]


def test_get_report_by_id_api(client: TestClient):
    """Test GET /api/v1/reports/{id}."""
    create_resp = client.post(
        "/api/v1/reports",
        data={"text": "Clinical note for retrieval test"},
    )
    report_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/v1/reports/{report_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == report_id
    assert data["input_type"] == "text"


def test_get_report_not_found(client: TestClient):
    """Test GET /api/v1/reports/999999 returns 404."""
    response = client.get("/api/v1/reports/999999")
    assert response.status_code == 404


def test_get_reports_list_api(client: TestClient):
    """Test GET /api/v1/reports returns paginated items."""
    for i in range(3):
        client.post("/api/v1/reports", data={"text": f"Batch test report {i}"})

    response = client.get("/api/v1/reports?skip=0&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    assert len(data["items"]) == 2
