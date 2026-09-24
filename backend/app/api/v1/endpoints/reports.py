"""Report endpoints supporting multipart text, image, and PDF uploads."""
import os
from pathlib import Path
from typing import Optional
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.report import InputType, ReportStatus
from app.schemas.report import ReportResponse, ReportListResponse
from app.crud.crud_report import create_report, get_report_by_id, list_reports, count_reports
from app.services.storage import save_upload_file
from app.services.report_processor import process_report_task

router = APIRouter()

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/jpg"}
ALLOWED_PDF_EXTENSIONS = {".pdf"}
ALLOWED_PDF_MIMES = {"application/pdf"}


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit clinical document or note for review",
)
async def create_clinical_report(
    background_tasks: BackgroundTasks,
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """
    Accepts multipart input (plain text, image, or PDF).
    Validates file format and size, persists initial report with status=pending,
    and enqueues background processing.
    """
    # 1. Validate that at least one input is provided
    has_text = text is not None and text.strip() != ""
    has_file = file is not None and file.filename is not None and file.filename.strip() != ""

    if not has_text and not has_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a 'text' body or a valid 'file' upload (PDF, JPG, PNG) must be provided.",
        )

    # 2. Handle File upload
    if has_file and file is not None:
        filename = file.filename or ""
        ext = Path(filename).suffix.lower()
        content_type = (file.content_type or "").lower()

        # Classify input type and validate support
        if ext in ALLOWED_PDF_EXTENSIONS or content_type in ALLOWED_PDF_MIMES:
            input_type = InputType.PDF
        elif ext in ALLOWED_IMAGE_EXTENSIONS or content_type in ALLOWED_IMAGE_MIMES:
            input_type = InputType.IMAGE
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unsupported file type '{filename}'. "
                    f"Supported formats: PDF (.pdf) and Images (.jpg, .jpeg, .png)."
                ),
            )

        # Validate file size
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        file_content = await file.read()
        if len(file_content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB} MB.",
            )

        # Rewind file position and save to disk
        await file.seek(0)
        saved_file_path = await save_upload_file(file)
        raw_input_ref = saved_file_path

    # 3. Handle Text input
    else:
        input_type = InputType.TEXT
        raw_input_ref = text.strip() if text else ""

    # 4. Persist row with status=pending immediately
    report_dict = {
        "input_type": input_type,
        "raw_input_ref": raw_input_ref,
        "status": ReportStatus.PENDING,
    }
    db_report = create_report(db, report_in=report_dict)

    # 5. Enqueue background processing
    background_tasks.add_task(process_report_task, db_report.id)

    return db_report


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Get report by ID",
)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Retrieve details and status of a specific clinical report."""
    report = get_report_by_id(db, report_id=report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found.",
        )
    return report


@router.get(
    "",
    response_model=ReportListResponse,
    summary="List reports",
)
def get_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """List clinical reports paginated with newest first."""
    items = list_reports(db, skip=skip, limit=limit)
    total = count_reports(db)
    return ReportListResponse(total=total, skip=skip, limit=limit, items=items)


@router.post(
    "/seed",
    response_model=ReportListResponse,
    summary="Seed demo sample reports",
)
def seed_reports_endpoint(
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """Populates synthetic clinical sample reports into the database."""
    from scripts.seed_reports import seed_sample_reports
    seed_sample_reports(db)
    items = list_reports(db, skip=0, limit=20)
    total = count_reports(db)
    return ReportListResponse(total=total, skip=0, limit=20, items=items)
