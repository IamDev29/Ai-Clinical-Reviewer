"""Domain exceptions for clinical document processing."""


class ClinicalProcessingError(Exception):
    """Base exception for clinical processing errors."""
    pass


class DocumentQualityError(ClinicalProcessingError):
    """Raised when document quality is too poor, blank, or lacks readable clinical content."""
    pass


class ExtractionSchemaError(ClinicalProcessingError):
    """Raised when LLM output cannot be parsed into the required structured schema."""
    pass


class ExtractionRepairFailedError(ClinicalProcessingError):
    """Raised when the repair prompt fails to produce a valid schema."""
    pass
