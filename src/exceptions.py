"""Custom exception classes for the CLIA Report File Generator.

This module defines custom exception classes that provide more specific
error information and better error handling throughout the application.
"""


class ReportGeneratorError(Exception):
    """Base exception class for all report generator errors."""
    pass


class DataProcessingError(ReportGeneratorError):
    """Raised when data processing fails."""
    pass


class InvalidCSVFormatError(DataProcessingError):
    """Raised when the CSV file format is invalid."""
    pass


class MissingColumnError(InvalidCSVFormatError):
    """Raised when required CSV columns are missing."""

    def __init__(self, missing_columns: list[str]) -> None:
        self.missing_columns = missing_columns
        super().__init__(
            f"Missing required columns: {', '.join(missing_columns)}"
        )


class PDFGenerationError(ReportGeneratorError):
    """Raised when PDF generation fails."""
    pass


class InvalidResultError(DataProcessingError):
    """Raised when test results contain invalid values."""
    pass


class InvalidPathError(ReportGeneratorError):
    """Raised when a file path is invalid or unsafe."""
    pass


class DateParsingError(DataProcessingError):
    """Raised when date parsing fails."""

    def __init__(self, date_string: str, column_name: str) -> None:
        self.date_string = date_string
        self.column_name = column_name
        super().__init__(
            f"Could not parse date '{date_string}' in column '{column_name}'"
        )
