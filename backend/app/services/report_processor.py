"""Background processor orchestrating asynchronous clinical document review."""
import logging
from sqlalchemy.orm import Session
from app.db import session as db_session
from app.models.report import Report, ReportStatus, InputType
from app.crud.crud_report import get_report_by_id, update_report_status
from app.core.exceptions import DocumentQualityError, ClinicalProcessingError
from app.services.pdf_extractor import extract_pdf_content
from app.services.vision_pipeline import (
    process_image_vision_pipeline,
    process_rendered_pdf_pages_vision,
)
from app.services.clinical_extractor import process_clinical_document

logger = logging.getLogger(__name__)


def process_report_task(report_id: int) -> None:
    """
    Background worker task to process a report asynchronously.
    Updates status: pending -> processing -> completed / failed.
    """
    db: Session = db_session.SessionLocal()
    try:
        report = get_report_by_id(db, report_id=report_id)
        if not report:
            logger.error(f"Report ID {report_id} not found for processing.")
            return

        # Transition to PROCESSING
        update_report_status(db, report_id=report_id, status=ReportStatus.PROCESSING)

        extracted_text = ""
        image_path = None

        if report.input_type == InputType.TEXT:
            extracted_text = report.raw_input_ref

        elif report.input_type == InputType.PDF:
            pdf_text, rendered_images, is_scanned = extract_pdf_content(report.raw_input_ref)
            if is_scanned:
                # Scanned/image PDF: use vision fallback
                vision_result = process_rendered_pdf_pages_vision(
                    page_image_paths=rendered_images,
                    pdf_path=report.raw_input_ref,
                )
                extracted_text = vision_result.get("extracted_text", "")
                image_path = rendered_images[0] if rendered_images else None
            else:
                extracted_text = pdf_text

        elif report.input_type == InputType.IMAGE:
            image_path = report.raw_input_ref
            vision_result = process_image_vision_pipeline(report.raw_input_ref)
            extracted_text = vision_result.get("extracted_text", "")

        else:
            raise ValueError(f"Unsupported input type: {report.input_type}")

        # Execute AI/ML clinical extraction and summary pipeline
        extraction_result = process_clinical_document(
            extracted_text=extracted_text,
            image_path=image_path,
        )

        # Transition to COMPLETED
        update_report_status(
            db,
            report_id=report_id,
            status=ReportStatus.COMPLETED,
            extracted_text=extraction_result.extracted_text,
            report_summary=extraction_result.report_summary,
            structured_report=extraction_result.structured_report.model_dump(),
            error_message=None,
        )
        logger.info(f"Report #{report_id} processing completed successfully.")

    except DocumentQualityError as dqe:
        logger.warning(f"Document quality rejection for report #{report_id}: {dqe}")
        update_report_status(
            db,
            report_id=report_id,
            status=ReportStatus.FAILED,
            error_message=str(dqe),
        )

    except Exception as e:
        logger.exception(f"Error processing report #{report_id}: {str(e)}")
        update_report_status(
            db,
            report_id=report_id,
            status=ReportStatus.FAILED,
            error_message=str(e),
        )
    finally:
        db.close()
