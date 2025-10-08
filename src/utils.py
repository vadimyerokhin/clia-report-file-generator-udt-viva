"""This module provides utility functions for the project.

It contains helper functions that are used across different modules, such as
for sanitizing strings to be used as valid filenames.
"""
import re

def sanitize_filename(filename):
    """Sanitizes a string to create a valid and safe filename.

    This function takes an input string and removes characters that are invalid
    in most filesystems. It replaces illegal characters and any whitespace
    sequences with a single hyphen. It also removes any leading or trailing
    hyphens that result from the replacement.

    Args:
        filename (str): The input string to be sanitized.

    Returns:
        str: The sanitized string, safe to be used as a filename. Returns an
             empty string if the input is empty or None.
    """
    if not filename:
        return ""

    # A regex to find one or more characters that are illegal in filenames or are spaces.
    # Illegal characters are: / \ : * ? " < > |
    illegal_chars_and_spaces = r'[\\/:\*\?"<>\|\s]+'
    sanitized_filename = re.sub(illegal_chars_and_spaces, '-', filename)

    # Remove leading/trailing hyphens that might have been created
    sanitized_filename = sanitized_filename.strip('-')

    return sanitized_filename

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