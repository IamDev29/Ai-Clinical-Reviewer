"""PDF text and image extraction using PyMuPDF (fitz)."""
import os
import uuid
from typing import List, Tuple
from pathlib import Path
import fitz  # PyMuPDF
from app.core.config import settings
from app.services.storage import get_upload_dir


def extract_pdf_content(pdf_path: str) -> Tuple[str, List[str], bool]:
    """
    Extract text from a PDF file using PyMuPDF.

    If extracted text is shorter than settings.MIN_PDF_TEXT_LENGTH_THRESHOLD,
    treats the document as a scanned/image PDF, renders each page as a PNG image,
    and returns:
        (extracted_text, list_of_rendered_image_paths, is_scanned=True)

    Otherwise returns:
        (extracted_text, [], is_scanned=False)
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    doc = fitz.open(pdf_path)
    page_texts: List[str] = []
    total_text_length = 0

    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text() or ""
            clean_text = text.strip()
            if clean_text:
                page_texts.append(f"--- Page {page_num + 1} ---\n{clean_text}")
                total_text_length += len(clean_text)

        extracted_text = "\n\n".join(page_texts)

        # Check threshold for digital vs scanned PDF
        is_scanned = total_text_length < settings.MIN_PDF_TEXT_LENGTH_THRESHOLD

        rendered_image_paths: List[str] = []
        if is_scanned:
            upload_dir = get_upload_dir()
            pdf_stem = Path(pdf_path).stem

            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                img_filename = f"{pdf_stem}_page_{page_num + 1}_{uuid.uuid4().hex[:8]}.png"
                img_path = upload_dir / img_filename
                pix.save(str(img_path))
                rendered_image_paths.append(str(img_path.resolve()))

        return extracted_text, rendered_image_paths, is_scanned

    finally:
        doc.close()
