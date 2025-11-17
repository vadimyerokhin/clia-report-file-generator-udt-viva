"""Configuration module for the CLIA Report File Generator.

This module contains all configurable constants and settings used throughout
the application, making it easy to customize without modifying source code.
"""
from typing import Final

# Laboratory Information
LAB_NAME: Final[str] = "Therapeutic Life Choices, LLC"
LAB_CLIA_ID: Final[str] = "37D2301589"
LAB_ADDRESS: Final[str] = "1728 S Carson Ave"
LAB_CITY_STATE_ZIP: Final[str] = "Tulsa, OK 74119"
LAB_PHONE: Final[str] = "(918) 917-4321"
LAB_EMAIL: Final[str] = "drvadim@abraxaslabs.org"
LAB_DIRECTOR: Final[str] = "Vadim Yerokhin, PhD"

# Report Settings
REPORT_TITLE: Final[str] = "urine drug test results"
SPECIMEN_TYPE: Final[str] = "Urine"
POSITIVES_SUMMARY_FILENAME: Final[str] = "positives_summary.pdf"

# Result Validation
VALID_RESULTS: Final[list[str]] = ['positive', 'negative']

# Required CSV Columns
REQUIRED_COLUMNS: Final[list[str]] = [
    'Type', 'ID', 'Date collected', 'Name', 'MR#', 'Date of Birth',
    'Collected by', 'Test completed', 'Test Name', 'Test result'
]

# Date Formats
DATE_FORMAT_DISPLAY: Final[str] = '%m/%d/%Y'
DATE_FORMAT_FILE: Final[str] = '%Y-%m-%d'
DATE_FORMAT_ISO: Final[str] = '%Y-%m-%d %H:%M:%S'

# PDF Layout Settings (in inches)
PDF_MARGIN: Final[float] = 1.0
PDF_SPACER_SMALL: Final[float] = 0.1
PDF_SPACER_MEDIUM: Final[float] = 0.2
PDF_SPACER_LARGE: Final[float] = 0.5

# Maximum file path length for safety
MAX_PATH_LENGTH: Final[int] = 255

# Logging Settings
LOG_FORMAT: Final[str] = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT: Final[str] = '%Y-%m-%d %H:%M:%S'
