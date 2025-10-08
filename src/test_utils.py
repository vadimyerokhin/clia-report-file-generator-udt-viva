import unittest
from utils import sanitize_filename

class TestSanitizeFilename(unittest.TestCase):
    def test_replaces_illegal_characters_and_spaces_with_hyphen(self):
        # Test case with various illegal characters and spaces
        invalid_name = 'Test/User\\ With:Illegal*Chars?"<>| and  spaces'
        expected_name = 'Test-User-With-Illegal-Chars-and-spaces'
        self.assertEqual(sanitize_filename(invalid_name), expected_name)

    def test_handles_clean_string(self):
        # Test case with a name that is already valid
        valid_name = 'John-Doe'
        self.assertEqual(sanitize_filename(valid_name), valid_name)

    def test_handles_empty_string(self):
        # Test case with an empty string
        self.assertEqual(sanitize_filename(''), '')

    def test_collapses_multiple_illegal_chars_and_spaces(self):
        # Test case to ensure multiple spaces and illegal chars are collapsed to a single hyphen
        name_with_multiple = 'Jane   Doe///**More'
        expected_name = 'Jane-Doe-More'
        self.assertEqual(sanitize_filename(name_with_multiple), expected_name)

if __name__ == '__main__':
    unittest.main()