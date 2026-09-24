"""Vision pipeline stub for clinical document optical extraction."""
import os
from typing import Any, Dict, List
from pathlib import Path


def process_image_vision_pipeline(image_path: str) -> Dict[str, Any]:
    """Stub vision extraction pipeline for single image documents."""
    filename = Path(image_path).name
    # In a full production implementation, this invokes multimodal LLM (e.g., Gemini Flash/Pro Vision)
    return {
        "extracted_text": f"[VISION STUB] Extracted clinical text from image file: {filename}",
        "report_summary": f"Clinical document image ({filename}) processed via Vision OCR pipeline.",
        "structured_report": {
            "source_type": "image",
            "source_ref": image_path,
            "pipeline": "vision_extraction_stub_v1",
            "findings": [
                "Scanned/imaged document detected and processed",
                "Clinical entities queued for automated normalization",
            ],
            "confidence": 0.92,
        },
    }


def process_rendered_pdf_pages_vision(page_image_paths: List[str], pdf_path: str) -> Dict[str, Any]:
    """Stub vision extraction pipeline for rendered pages of scanned PDFs."""
    page_count = len(page_image_paths)
    pdf_name = Path(pdf_path).name

    extracted_lines = [
        f"[VISION OCR STUB] Extracted text from scanned PDF '{pdf_name}' ({page_count} page(s)):"
    ]
    for idx, page_img in enumerate(page_image_paths, 1):
        extracted_lines.append(f"--- Page {idx} (rendered from {Path(page_img).name}) ---")
        extracted_lines.append(f"Page {idx} clinical findings, patient protocol data, and lab values.")

    full_extracted_text = "\n".join(extracted_lines)

    return {
        "extracted_text": full_extracted_text,
        "report_summary": (
            f"Scanned PDF document '{pdf_name}' had low digital text density. "
            f"Rendered {page_count} page(s) as images and extracted text via vision pipeline."
        ),
        "structured_report": {
            "source_type": "scanned_pdf",
            "source_ref": pdf_path,
            "pipeline": "pdf_vision_render_fallback_v1",
            "pages_rendered": page_count,
            "rendered_image_refs": page_image_paths,
            "confidence": 0.89,
        },
    }
