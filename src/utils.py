"""This module provides utility functions for the project.

It contains helper functions that are used across different modules, such as
for sanitizing strings to be used as valid filenames and path validation.
"""
import re
import subprocess
import platform
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd

try:
    from src.exceptions import InvalidPathError
    from src.config import MAX_PATH_LENGTH, DATE_FORMAT_DISPLAY, DATE_FORMAT_FILE
except ImportError:
    from exceptions import InvalidPathError
    from config import MAX_PATH_LENGTH, DATE_FORMAT_DISPLAY, DATE_FORMAT_FILE


def sanitize_filename(filename: Optional[str]) -> str:
    """Sanitizes a string to create a valid and safe filename.

    This function takes an input string and removes characters that are invalid
    in most filesystems. It replaces illegal characters and any whitespace
    sequences with a single hyphen. It also removes any leading or trailing
    hyphens that result from the replacement.

    Args:
        filename: The input string to be sanitized.

    Returns:
        The sanitized string, safe to be used as a filename. Returns an
        empty string if the input is empty or None.

    Examples:
        >>> sanitize_filename("John Doe")
        'John-Doe'
        >>> sanitize_filename("Test/User")
        'Test-User'
        >>> sanitize_filename("File\\With?Illegal*Chars")
        'File-With-Illegal-Chars'
    """
    if not filename:
        return ""

    # A regex to find one or more characters that are illegal in filenames or are spaces.
    # Illegal characters are: / \ : * ? " < > |
    illegal_chars_and_spaces = r'[\\/:\*\?"<>\|\s]+'
    sanitized_filename = re.sub(illegal_chars_and_spaces, '-', filename)

    # Remove leading/trailing hyphens that might have been created
    sanitized_filename = sanitized_filename.strip('-')

    # Limit length to prevent filesystem issues
    if len(sanitized_filename) > MAX_PATH_LENGTH:
        sanitized_filename = sanitized_filename[:MAX_PATH_LENGTH]

    return sanitized_filename


def validate_path(path: str, must_exist: bool = False) -> Path:
    """Validates a file path for security and correctness.

    This function checks that a path is safe to use (no path traversal attacks),
    within reasonable length limits, and optionally that it exists.

    Args:
        path: The file path to validate.
        must_exist: If True, raises an error if the path doesn't exist.

    Returns:
        A validated Path object.

    Raises:
        InvalidPathError: If the path is invalid, unsafe, or doesn't exist
            when must_exist is True.

    Examples:
        >>> validate_path("/tmp/output")
        PosixPath('/tmp/output')
    """
    if not path:
        raise InvalidPathError("Path cannot be empty")

    # Convert to Path object for better handling
    try:
        path_obj = Path(path).resolve()
    except (ValueError, OSError) as e:
        raise InvalidPathError(f"Invalid path '{path}': {e}")

    # Check for path traversal attempts
    if ".." in Path(path).parts:
        raise InvalidPathError(f"Path traversal detected in '{path}'")

    # Check length
    if len(str(path_obj)) > MAX_PATH_LENGTH * 10:  # Allow longer for full paths
        raise InvalidPathError(f"Path too long: {len(str(path_obj))} characters")

    # Check existence if required
    if must_exist and not path_obj.exists():
        raise InvalidPathError(f"Path does not exist: '{path_obj}'")

    return path_obj


def validate_output_directory(output_dir: str) -> Path:
    """Validates and creates an output directory if it doesn't exist.

    Args:
        output_dir: The output directory path.

    Returns:
        A validated Path object for the output directory.

    Raises:
        InvalidPathError: If the directory path is invalid or not writable.
    """
    dir_path = validate_path(output_dir, must_exist=False)

    # Create directory if it doesn't exist
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise InvalidPathError(f"Cannot create directory '{output_dir}': {e}")

    # Verify it's a directory
    if not dir_path.is_dir():
        raise InvalidPathError(f"Path exists but is not a directory: '{output_dir}'")

    # Verify write permissions by attempting to create and remove a test file
    test_file = dir_path / ".write_test_temp"
    try:
        test_file.touch()
        test_file.unlink()
    except (OSError, PermissionError) as e:
        raise InvalidPathError(f"Directory '{output_dir}' is not writable: {e}")

    return dir_path


def parse_collection_date(date_str: str) -> Tuple[str, Optional[str]]:
    """Parses a collection date string and returns formatted versions.

    Args:
        date_str: The date string to parse.

    Returns:
        A tuple of (formatted_date_str, error_message).
        If successful, error_message is None.
        If failed, formatted_date_str is the original string and error_message contains the error.
    """
    try:
        date_obj = pd.to_datetime(date_str, format='mixed', dayfirst=False)
        return date_obj.strftime(DATE_FORMAT_FILE), None
    except Exception as e:
        error_msg = f"The date '{date_str}' in the 'Date collected' column could not be parsed."
        return date_str, error_msg


def parse_completion_date(date_series: pd.Series) -> Tuple[str, str, Optional[str]]:
    """Parses test completion dates from a pandas Series.

    Args:
        date_series: A pandas Series containing test completion dates.

    Returns:
        A tuple of (file_format_date, display_format_date, error_message).
        If successful, error_message is None.
        If failed, returns fallback values and an error message.
    """
    try:
        latest_ts = pd.to_datetime(date_series, format='mixed', dayfirst=False).max()
        return (
            latest_ts.strftime(DATE_FORMAT_FILE),
            latest_ts.strftime(DATE_FORMAT_DISPLAY),
            None
        )
    except (ValueError, TypeError) as e:
        raw_date = date_series.iloc[0] if not date_series.empty else "N/A"
        error_msg = f"Could not parse 'Test completed' date ('{raw_date}'). Error: {e}"
        return "unknown-date", str(raw_date).split(' ')[0], error_msg


def open_file_explorer(directory_path: str) -> Optional[str]:
    """Opens the system file explorer at the specified directory.

    Args:
        directory_path: The path to the directory to open.

    Returns:
        None if successful, error message string if failed.
    """
    try:
        if platform.system() == "Windows":
            subprocess.run(["explorer", directory_path], check=True)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", directory_path], check=True)
        else:  # Linux and others
            subprocess.run(["xdg-open", directory_path], check=True)
        return None
    except Exception as e:
        return f"Could not open folder: {e}"


if __name__ == '__main__':  # pragma: no cover
    # Example usage for direct testing
    test_names = [
        "John Doe",
        "Test/User",
        "File\\With?Illegal*Chars",
        'Another:Test<Subject>|Name',
        "Already-Valid-Name",
        "Extra   Spaces",
        "Trailing/Illegal/"
    ]

    print("Testing sanitize_filename function:")
    for name in test_names:
        sanitized = sanitize_filename(name)
        print(f'  Original: "{name}" -> Sanitized: "{sanitized}"')