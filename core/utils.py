"""
core/utils.py
=============
Shared utility functions used across multiple apps.

All functions here are pure (no Django model imports) so they
can be tested without a database and reused anywhere.

Usage:
    from core.utils import detect_file_type, validate_upload, format_file_size
"""

import logging
import mimetypes
from pathlib import Path

from django.core.files.uploadedfile import UploadedFile
from django.http import HttpResponse

from core.constants import (
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_PDF_EXTENSIONS,
    SUPPORTED_IMAGE_MIME_TYPES,
    SUPPORTED_PDF_MIME_TYPES,
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_MB,
    INPUT_TYPE_PDF,
    INPUT_TYPE_IMAGE,
    OUTPUT_FILENAME_TEMPLATE,
)
from core.exceptions import (
    UnsupportedFileTypeError,
    FileTooLargeError,
    EmptyFileError,
)

logger = logging.getLogger(__name__)


# ─── File Type Detection ──────────────────────────────────────────────────────

def detect_file_type(file: UploadedFile) -> str:
    """
    Determine whether an uploaded file is a PDF or image.

    Checks both MIME type and file extension for reliability.
    Extension check is a fallback for browsers that send wrong MIME types.

    Args:
        file: Django UploadedFile instance from request.FILES

    Returns:
        'pdf'   if the file is a PDF
        'image' if the file is a supported image format

    Raises:
        UnsupportedFileTypeError: if neither PDF nor image

    Example:
        input_type = detect_file_type(request.FILES['file'])
    """
    mime_type    = getattr(file, "content_type", "") or ""
    filename     = getattr(file, "name", "")         or ""
    extension    = Path(filename).suffix.lower()

    is_pdf = (
        mime_type in SUPPORTED_PDF_MIME_TYPES
        or extension in SUPPORTED_PDF_EXTENSIONS
    )
    is_image = (
        mime_type in SUPPORTED_IMAGE_MIME_TYPES
        or extension in SUPPORTED_IMAGE_EXTENSIONS
    )

    if is_pdf:
        logger.debug("File detected as PDF: %s (mime: %s)", filename, mime_type)
        return INPUT_TYPE_PDF

    if is_image:
        logger.debug("File detected as image: %s (mime: %s)", filename, mime_type)
        return INPUT_TYPE_IMAGE

    logger.warning(
        "Unsupported file type: %s (mime: %s, ext: %s)",
        filename, mime_type, extension
    )
    raise UnsupportedFileTypeError(
        f"'{extension or mime_type}' is not supported. "
        "Please upload a PDF or image (JPG, PNG, WEBP, BMP)."
    )


def get_mime_type(filename: str) -> str:
    """
    Guess MIME type from filename extension.

    Args:
        filename: File name with extension (e.g. 'fayda.pdf')

    Returns:
        MIME type string (e.g. 'application/pdf')
        Falls back to 'application/octet-stream' if unknown.
    """
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


# ─── File Validation ─────────────────────────────────────────────────────────

def validate_upload(file: UploadedFile) -> str:
    """
    Full validation pipeline for an uploaded file.
    Runs all checks in one call — used in UploadForm.clean_file().

    Checks (in order):
        1. File is not empty (zero bytes)
        2. File size is within MAX_UPLOAD_MB
        3. File type is PDF or supported image

    Args:
        file: Django UploadedFile from request.FILES

    Returns:
        Detected input type: 'pdf' or 'image'

    Raises:
        EmptyFileError:           file has 0 bytes
        FileTooLargeError:        file exceeds MAX_UPLOAD_MB
        UnsupportedFileTypeError: not a PDF or image
    """
    # 1. Empty file check
    if file.size == 0:
        raise EmptyFileError()

    # 2. Size check
    if file.size > MAX_UPLOAD_BYTES:
        raise FileTooLargeError(
            f"Your file is {format_file_size(file.size)}. "
            f"Maximum allowed size is {MAX_UPLOAD_MB}MB."
        )

    # 3. Type check (returns input_type string)
    return detect_file_type(file)


# ─── File Utilities ───────────────────────────────────────────────────────────

def read_uploaded_file(file: UploadedFile) -> bytes:
    """
    Safely read all bytes from an UploadedFile.
    Resets the file pointer after reading so the file
    can be read again if needed.

    Args:
        file: Django UploadedFile

    Returns:
        Raw bytes of the file content
    """
    file.seek(0)
    data = file.read()
    file.seek(0)
    return data


def format_file_size(size_bytes: int) -> str:
    """
    Human-readable file size string.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted string like '4.2 MB', '512 KB', '800 B'

    Examples:
        format_file_size(1_048_576)  → '1.0 MB'
        format_file_size(512_000)    → '500.0 KB'
        format_file_size(800)        → '800 B'
    """
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.1f} MB"
    elif size_bytes >= 1_024:
        return f"{size_bytes / 1_024:.1f} KB"
    return f"{size_bytes} B"


def build_output_filename(job_id: str) -> str:
    """
    Generate the output filename for a completed conversion job.

    Args:
        job_id: UUID string of the ConversionJob

    Returns:
        Filename string like 'fayda_landscape_abc123.jpg'
    """
    short_id = str(job_id).replace("-", "")[:12]
    return OUTPUT_FILENAME_TEMPLATE.format(job_id=short_id)


# ─── HTTP Response Helpers ────────────────────────────────────────────────────

def file_download_response(
    content: bytes,
    filename: str,
    content_type: str = "image/jpeg",
) -> HttpResponse:
    """
    Build an HttpResponse that triggers a file download in the browser.

    Args:
        content:      Raw bytes of the file
        filename:     Suggested filename for the download
        content_type: MIME type (default: image/jpeg for landscape output)

    Returns:
        HttpResponse with Content-Disposition: attachment

    Usage in DownloadView:
        return file_download_response(
            content=job.output_bytes,
            filename=build_output_filename(job.id),
        )
    """
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Content-Length"] = len(content)
    return response


def json_error_response(message: str, status: int = 400) -> HttpResponse:
    """
    Return a JSON error response for AJAX/fetch requests.

    Args:
        message: Human-readable error description
        status:  HTTP status code (default 400)

    Returns:
        HttpResponse with JSON body
    """
    import json
    return HttpResponse(
        json.dumps({"error": message, "ok": False}),
        content_type="application/json",
        status=status,
    )


def json_success_response(data: dict, status: int = 200) -> HttpResponse:
    """
    Return a JSON success response for AJAX/fetch requests.

    Args:
        data:   Dict to serialize as JSON
        status: HTTP status code (default 200)

    Returns:
        HttpResponse with JSON body including 'ok': True
    """
    import json
    return HttpResponse(
        json.dumps({"ok": True, **data}),
        content_type="application/json",
        status=status,
    )
    


# FRONT_ZONES = {
#     # Left Margin Border Elements
#     "vertical_strip_left":  (20, 85, 60, 595), 
#     "photo_main":           (90, 110, 460, 560),    # Beautifully isolated profile slot
#     "vertical_strip_right": (480, 85, 520, 595),   # Balanced second security bar
    
#     # Right-hand Content Stack (Front Side)
#     "name_field":           (550, 130, 1120, 185),  
#     "dob_field":            (550, 210, 1120, 260),
#     "sex_field":            (550, 285, 1120, 330),
#     "expiry_field":         (550, 355, 1120, 405),
    
#     # Lower Anchor Layout Components
#     "barcode_area":         (550, 445, 940, 555),
#     "photo_small":          (970, 435, 1140, 585),  # Secondary ghost photo spot
# }

# BACK_ZONES = {
#     # Left Content Column (Back Side - Coordinates relative to Right Hemisphere start)
#     "phone_field":          (60, 100, 480, 145),
#     "address_field":        (60, 185, 480, 425),   # Expanded block room for multi-line data
#     "fin_value":            (60, 465, 480, 615),   # Kept safely above the 667px canvas ceiling
    
#     # Right Content Column (Back Side)
#     "qr_area":              (540, 55, 1040, 555),  # Perfectly squared high-fidelity scanner zone
#     "sn_field":             (540, 580, 1040, 625), # Serial number clean baseline anchor
# }