import re

def sanitize_filename(filename):
    """
    Sanitizes a string to be used as a valid filename.

    - Replaces one or more spaces or illegal characters with a single hyphen.
    - Illegal characters: / \\ : * ? " < > |

    Args:
        filename (str): The input string to sanitize.

    Returns:
        str: The sanitized filename.
    """
    if not filename:
        return ""

    # Replace one or more spaces or illegal characters with a single hyphen.
    illegal_chars_and_spaces = r'[\\/:\*\?"<>\|\s]+'
    sanitized_filename = re.sub(illegal_chars_and_spaces, '-', filename)

    return sanitized_filename

if __name__ == '__main__':
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