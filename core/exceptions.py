"""
core/exceptions.py
==================
Custom exception hierarchy for the Fayda Converter.

All exceptions inherit from FaydaBaseException so callers
can catch broadly (FaydaBaseException) or narrowly
(QuotaExceededError) depending on context.

Usage in views:
    from core.exceptions import QuotaExceededError, ConversionFailedError

    try:
        result = convert_bytes(...)
    except QuotaExceededError:
        messages.error(request, "You've used all your conversions this month.")
    except ConversionFailedError as e:
        messages.error(request, f"Conversion failed: {e}")
"""


class FaydaBaseException(Exception):
    """
    Root exception for all Fayda Converter errors.
    Catch this to handle any application-level error broadly.
    """
    default_message = "An unexpected error occurred."

    def __init__(self, message: str = ""):
        self.message = message or self.default_message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


# ─── Quota / Billing ──────────────────────────────────────────────────────────

class QuotaExceededError(FaydaBaseException):
    """
    Raised when a user attempts a conversion but has exhausted
    their allowed conversions for the current period.

    Caught by QuotaMixin before the engine is ever called.
    The view should redirect to the upgrade/pricing page.
    """
    default_message = (
        "You have used all your conversions for this period. "
        "Upgrade your plan to continue."
    )


class SubscriptionExpiredError(FaydaBaseException):
    """
    Raised when a user's subscription has passed its expiry date
    and has not been renewed.
    """
    default_message = "Your subscription has expired. Please renew to continue."


class PlanNotFoundError(FaydaBaseException):
    """
    Raised when a requested billing plan does not exist
    or is no longer active.
    """
    default_message = "The requested plan does not exist or is no longer available."


# ─── File / Upload ────────────────────────────────────────────────────────────

class UnsupportedFileTypeError(FaydaBaseException):
    """
    Raised when the uploaded file is not a PDF or supported image format.
    Caught in UploadForm.clean_file() before touching the engine.

    Supported types are defined in core/constants.py:
        SUPPORTED_IMAGE_TYPES, SUPPORTED_PDF_TYPES
    """
    default_message = (
        "Unsupported file type. Please upload a PDF or image "
        "(JPG, PNG, WEBP, BMP)."
    )


class FileTooLargeError(FaydaBaseException):
    """
    Raised when the uploaded file exceeds MAX_UPLOAD_MB.
    Caught in UploadForm.clean_file().
    """
    default_message = "File is too large. Maximum upload size is 10MB."


class EmptyFileError(FaydaBaseException):
    """
    Raised when an uploaded file has zero bytes.
    """
    default_message = "The uploaded file is empty. Please upload a valid file."


# ─── Conversion Engine ────────────────────────────────────────────────────────

class ConversionFailedError(FaydaBaseException):
    """
    Raised when the Fayda conversion engine fails to process a file.
    Wraps lower-level PIL / OpenCV / pdf2image errors with a
    user-friendly message.

    The original exception is stored in self.original for logging.

    Usage:
        try:
            result = convert_bytes(data, filename)
        except Exception as e:
            raise ConversionFailedError(original=e) from e
    """
    default_message = (
        "We could not convert your file. "
        "Please make sure it is a valid Fayda ID card image or PDF."
    )

    def __init__(self, message: str = "", original: Exception = None):
        self.original = original
        super().__init__(message or self.default_message)


class OrientationDetectionError(FaydaBaseException):
    """
    Raised when the engine cannot determine whether the
    uploaded image is portrait or landscape.
    """
    default_message = "Could not detect the orientation of the uploaded ID card."


# ─── Access Control ───────────────────────────────────────────────────────────

class NotOwnerError(FaydaBaseException):
    """
    Raised when a user attempts to access a ConversionJob
    that belongs to another user.
    Caught by OwnerRequiredMixin → returns 403.
    """
    default_message = "You do not have permission to access this resource."