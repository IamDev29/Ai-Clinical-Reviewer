"""File storage management service."""
import os
import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile
from app.core.config import settings


def get_upload_dir() -> Path:
    """Return upload directory path and ensure it exists."""
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


async def save_upload_file(upload_file: UploadFile) -> str:
    """Save an UploadFile to disk with a unique identifier prefix and return its string path."""
    upload_dir = get_upload_dir()
    original_filename = upload_file.filename or "uploaded_file"
    # Clean filename of unsafe characters
    safe_filename = Path(original_filename).name
    unique_name = f"{uuid.uuid4().hex}_{safe_filename}"
    file_path = upload_dir / unique_name

    content = await upload_file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return str(file_path.resolve())


def save_bytes_to_file(content: bytes, filename: str) -> str:
    """Synchronously save raw bytes to disk and return the path."""
    upload_dir = get_upload_dir()
    unique_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
    file_path = upload_dir / unique_name

    with open(file_path, "wb") as f:
        f.write(content)

    return str(file_path.resolve())
