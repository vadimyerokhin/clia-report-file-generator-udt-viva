import os
import sys
import shutil
import unittest
from unittest.mock import patch

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from main import main

class TestMain(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory for test outputs."""
        self.output_dir = "temp_test_output"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def tearDown(self):
        """Remove the temporary directory after tests."""
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    @patch('builtins.input', side_effect=['2'])  # Simulate user choosing the second option
    def test_conflict_resolution_flow(self, mock_input):
        """Test the full flow with a data file containing a conflict."""
        input_file = "tests/test_data/conflict_data.csv"
        main(input_file, self.output_dir)

        # Check that only one report was generated for the conflict patient
        expected_filename = "Conflict-Patient_MRN006_2023-01-20.pdf"
        output_files = os.listdir(self.output_dir)

        # There should be 3 reports in total: one for MRN001, one for MRN002, and one for MRN006
        self.assertEqual(len(output_files), 3, "Should generate three reports in total.")

        # Check that the specific, user-selected report exists
        self.assertIn(expected_filename, output_files, "The PDF for the selected conflicted sample should be generated.")

if __name__ == '__main__':
    unittest.main()